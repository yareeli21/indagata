"""Análisis del instrumento a partir de su LIMPIEZA confirmada (cleaning-service).

metadata-service ya no lee el archivo crudo de los instrumentos nuevos: usa el CSV
limpio (vía storage-service) y el reporte_limpieza de la última versión confirmada
(tabla `tt_rag.limpieza_ejecucion`):

  - Encuesta: el CSV usa identificadores seguros como encabezados; el reporte da la
    etiqueta original, el rol (pregunta / contexto / eliminada) y el tipo canónico
    provisional de cada columna. Solo las columnas «pregunta» son reactivos.
  - Entrevista: un turno por fila (n_turno, hablante, rol, texto); las preguntas son
    los turnos del entrevistador.
  - Prueba estandarizada (tabla): una fila por alumno y pregunta; los reactivos salen
    de la clave de respuestas, con sus estadísticas (aciertos, nulas, no respondidas).
  - Prueba en documento: un bloque de texto por fila; se analiza como documento.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from services import storage_client
from services.analizador import (
    SECCION_GENERAL,
    Analisis,
    Pregunta,
    _desde_documento,
    _desde_tabla,
    es_columna_carrera,
    extraer_preguntas,
)


def _resumen_limpieza(limpieza: dict[str, Any]) -> dict[str, Any]:
    """Bloque `cleaning` del JSON estandarizado (trazabilidad de la limpieza usada)."""
    reporte = limpieza.get("reporte") or {}
    return {
        "esquema": reporte.get("esquema"),
        "version": limpieza.get("version"),
        "fecha_confirmacion": reporte.get("fecha_confirmacion"),
        "archivo_limpio": limpieza.get("ruta"),
        "version_servicio": reporte.get("version_servicio"),
        "metricas": reporte.get("metricas") or {},
        "avisos": reporte.get("avisos") or [],
        # Medidas globales (fiabilidad, encuestados, puntajes, hablantes); las de cada
        # columna o reactivo van en `statistics.per_question`.
        "estadistica": {k: v for k, v in _estadistica(limpieza).items() if k not in ("columnas", "reactivos")},
    }


def _estadistica(limpieza: dict[str, Any]) -> dict[str, Any]:
    """Medidas estadísticas de la limpieza confirmada (después de aplicar las decisiones)."""
    return ((limpieza.get("reporte") or {}).get("estadistica") or {}).get("despues") or {}


def _especifico(limpieza: dict[str, Any], tipo: str) -> dict[str, Any]:
    return ((limpieza.get("reporte") or {}).get("especifico") or {}).get(tipo) or {}


# ── Encuestas ──────────────────────────────────────────────────────────────────


def _encuesta(tabla: dict[str, Any], limpieza: dict[str, Any], nombre: str, texto_original: str) -> Analisis:
    columnas = {c["id"]: c for c in _especifico(limpieza, "encuesta").get("columnas", []) if c.get("estado") != "eliminada"}
    headers: list[str] = tabla.get("headers") or []
    filas: list[list[str]] = tabla.get("rows") or []

    # Tabla equivalente con las ETIQUETAS originales y solo las columnas «pregunta».
    indices = [j for j, h in enumerate(headers) if (columnas.get(h) or {}).get("rol", "pregunta") == "pregunta"]
    etiquetada = dict(tabla)
    etiquetada["headers"] = [columnas.get(headers[j], {}).get("etiqueta") or headers[j] for j in indices]
    etiquetada["rows"] = [[f[j] if j < len(f) else "" for j in indices] for f in filas]
    analisis = _desde_tabla(etiquetada, "encuesta", nombre, texto_original)

    # Tipo canónico provisional y opciones Likert del reporte (en vez de reinferirlos).
    specs = [columnas.get(headers[j]) or {} for j in indices]
    descriptivos = {c["id"]: c for c in _estadistica(limpieza).get("columnas", [])}
    for pregunta, spec in zip(analisis.preguntas, specs):
        medidas = descriptivos.get(spec.get("id")) or {}
        for clave in ("numerico", "frecuencias", "atipicos", "texto"):
            if medidas.get(clave):
                pregunta.estadisticas[clave] = medidas[clave]
        if spec.get("tipo_canonico"):
            pregunta.tipo = spec["tipo_canonico"]
            pregunta.estadisticas["type"] = spec["tipo_canonico"]
            pregunta.estadisticas["tipo_canonico_provisional"] = True
        likert = spec.get("likert")
        if likert:
            pregunta.opciones = list(likert.get("etiquetas") or pregunta.opciones)
            pregunta.estadisticas["likert"] = likert
        pregunta.estadisticas["columna"] = spec.get("id")

    # Población desde las columnas de contexto (carrera, programa…).
    for j, h in enumerate(headers):
        spec = columnas.get(h) or {}
        valores_col = [f[j] for f in filas if j < len(f) and f[j].strip()]
        if spec.get("rol") == "contexto" and es_columna_carrera(spec.get("etiqueta") or "", valores_col):
            analisis.carreras = [c for c, _ in Counter(valores_col).most_common(8)]
            if analisis.carreras:
                analisis.hallazgos["poblacion"] = f"Estudiantes de {', '.join(analisis.carreras[:5])}"
            break

    metricas = (limpieza.get("reporte") or {}).get("metricas") or {}
    antes, despues = metricas.get("antes") or {}, metricas.get("despues") or {}
    # Duplicados: los que tenía el archivo (en el limpio ya se quitaron, si así se decidió).
    analisis.n_duplicados = int(antes.get("n_duplicados") or 0)
    if despues.get("pct_nulos") is not None:
        analisis.pct_vacios = despues["pct_nulos"]
    return analisis


# ── Entrevistas ────────────────────────────────────────────────────────────────


def _entrevista(tabla: dict[str, Any], nombre: str, texto_original: str) -> Analisis:
    headers = [h.lower() for h in tabla.get("headers") or []]
    filas = tabla.get("rows") or []
    i_h, i_r, i_t = (headers.index(c) if c in headers else None for c in ("hablante", "rol", "texto"))
    if i_t is None:
        return _desde_documento("\n".join(" ".join(f) for f in filas), "entrevista", nombre)
    turnos = [
        (f[i_h] if i_h is not None and i_h < len(f) else "", f[i_r] if i_r is not None and i_r < len(f) else "", f[i_t])
        for f in filas
        if i_t < len(f) and f[i_t].strip()
    ]
    texto = "\n".join(f"{h}: {t}" if h else t for h, _, t in turnos)
    if texto_original and texto_original not in texto:
        texto = f"{texto_original}\n\n{texto}"
    analisis = _desde_documento(texto, "entrevista", nombre)

    # Preguntas = turnos del entrevistador (si la limpieza reconoció hablantes).
    # Sin repetir: un guion aplicado a 40 personas tiene 40 veces cada pregunta.
    del_entrevistador = list(dict.fromkeys(" ".join(t.split()) for _, r, t in turnos if r == "entrevistador"))
    if del_entrevistador:
        analisis.preguntas = [
            Pregunta(id=f"q{k}", texto=t[:500], tipo="abierta", seccion=SECCION_GENERAL)
            for k, t in enumerate(del_entrevistador, start=1)
        ]
    analisis.n_registros = len(turnos)
    return analisis


# ── Pruebas estandarizadas ─────────────────────────────────────────────────────


def _prueba_tabular(tabla: dict[str, Any], limpieza: dict[str, Any], nombre: str, texto_original: str) -> Analisis:
    esp = _especifico(limpieza, "prueba_estandarizada")
    clave: dict[str, str] = esp.get("clave") or {}
    opciones = [o for o in esp.get("opciones_validas") or ["A", "B", "C", "D"] if o != "NR"]
    headers = [h.lower() for h in tabla.get("headers") or []]
    filas = tabla.get("rows") or []
    idx = {c: headers.index(c) for c in ("id_alumno", "pregunta", "correcta", "estado") if c in headers}

    por_pregunta: dict[str, Counter] = defaultdict(Counter)
    alumnos: set[str] = set()
    if len(idx) == 4:
        for f in filas:
            p = f[idx["pregunta"]]
            alumnos.add(f[idx["id_alumno"]])
            por_pregunta[p]["n"] += 1
            por_pregunta[p][f[idx["estado"]]] += 1
            por_pregunta[p]["aciertos"] += 1 if f[idx["correcta"]] == "1" else 0

    # Si el examen original trae las preguntas en el mismo número, se usa su texto.
    del_examen = extraer_preguntas(texto_original) if texto_original else []
    usar_examen = len(del_examen) == len(clave) and bool(clave)
    reactivos = {r["pregunta"]: r for r in _estadistica(limpieza).get("reactivos", [])}
    preguntas = []
    for k, (pregunta, correcta) in enumerate(clave.items()):
        c = por_pregunta.get(pregunta, Counter())
        analisis_reactivo = {
            clave_r: v for clave_r, v in (reactivos.get(pregunta) or {}).items() if clave_r not in ("pregunta", "respuesta_correcta")
        }
        n = c["n"] or 1
        preguntas.append(
            Pregunta(
                id=pregunta,
                texto=del_examen[k].texto if usar_examen else f"Reactivo {pregunta}",
                tipo="opcion_multiple",
                opciones=del_examen[k].opciones if usar_examen and del_examen[k].opciones else opciones,
                seccion=SECCION_GENERAL,
                estadisticas={
                    "type": "opcion_multiple",
                    "respuesta_correcta": correcta,
                    "n": c["n"],
                    "pct_correctas": round(c["aciertos"] / n, 4),
                    "pct_nulas": round(c["nula"] / n, 4),
                    "pct_no_respondidas": round(c["NR"] / n, 4),
                    **analisis_reactivo,  # dificultad, discriminación, punto-biserial, distractores
                },
            )
        )
    texto = texto_original or "\n".join(p.texto for p in preguntas)
    base = _desde_documento(texto, "prueba_estandarizada", nombre)
    base.preguntas = preguntas
    base.familia = "tabular"
    base.n_registros = len(alumnos) or esp.get("n_alumnos")
    base.descripcion = (
        f"Prueba estandarizada de {len(preguntas)} reactivos de opción múltiple aplicada a {base.n_registros} alumnos."
    )
    conteos = esp.get("conteos") or {}
    total = sum(conteos.values()) or 0
    base.pct_vacios = round((conteos.get("NR", 0)) / total, 4) if total else None
    return base


# ── Punto de entrada ───────────────────────────────────────────────────────────


def analizar(raw: Any, limpieza: dict[str, Any], texto_original: str) -> Analisis:
    """Análisis del instrumento desde su CSV limpio y su reporte de limpieza."""
    tipo = (raw.tipo_instrumento or "encuesta").lower()
    nombre = raw.nombre_archivo or ""
    tabla = storage_client.tabla(limpieza["ruta"])
    encabezados = [h.lower() for h in tabla.get("headers") or []]

    if tipo == "encuesta":
        analisis = _encuesta(tabla, limpieza, nombre, texto_original)
    elif tipo == "entrevista":
        analisis = _entrevista(tabla, nombre, texto_original)
    elif "id_alumno" in encabezados:
        analisis = _prueba_tabular(tabla, limpieza, nombre, texto_original)
    else:  # prueba en documento: n_bloque; texto
        i_t = encabezados.index("texto") if "texto" in encabezados else len(encabezados) - 1
        texto = "\n\n".join(f[i_t] for f in tabla.get("rows") or [] if i_t < len(f))
        if texto_original and texto_original not in texto:
            texto = f"{texto_original}\n\n{texto}"
        analisis = _desde_documento(texto, tipo, nombre)

    analisis.limpieza = _resumen_limpieza(limpieza)
    analisis.notas.append(f"Metadatos propuestos con el archivo limpio (limpieza v{limpieza.get('version')}).")
    return analisis
