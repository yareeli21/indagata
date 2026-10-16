"""Motor de limpieza de pruebas estandarizadas.

TABULAR (respuestas de los alumnos + clave de respuestas OPCIONAL), en el orden de la Tabla 5:
  1. Validación del archivo: formato admisible, delimitador (, o ;) y estructura
     (columnas = preguntas, filas = alumnos); lo mismo para la clave.
  2. Normalización a UTF-8.
  3. Validación estructural: columnas faltantes → error; columnas extra → aviso;
     IDs duplicados → fase asistida; filas vacías → se eliminan.
  4. Validación de respuestas: opciones válidas (por defecto A, B, C, D, NR).
  5. Nulificación: varias respuestas, caracteres inválidos o ilegibles → nula;
     vacía → NR.
  6. Inferencia por pregunta: correcta (1/0), estado (valida / nula / NR) y
     motivo (duplicado / no_respondida / respuesta_multiple / caracter_invalido / ilegible).

Reactivos de opción múltiple (A–D), verdadero/falso (V/F) y de puntos (respuesta ya
calificada 0..máx; acierto = puntaje máximo). Si la prueba NO trae clave, se propone una
(ver `clave.py`) y el investigador la confirma o corrige en la fase asistida.

Análisis de reactivos (antes y después de las decisiones): índice de dificultad,
índice de discriminación (grupos extremos del 27 %), correlación punto-biserial,
distribución de opciones (distractores), puntajes y fiabilidad KR-20. Las
respuestas nulas y no respondidas cuentan como incorrectas.

Salida (formato largo, una fila por alumno y pregunta):
  id_alumno; pregunta; respuesta; respuesta_correcta; correcta; estado; motivo[; contexto…]
  (las columnas de contexto del alumno —turno, semestre…— se conservan al final)

DOCUMENTO (el examen en texto): limpieza de texto de la Figura 1, sin hablantes;
salida n_bloque; texto (un párrafo por fila).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from shared.parsing import DocumentParseError, RawTable, TabularParseError, read_document, read_tabular

from services import configuracion
from services.configuracion import normalizar_texto
from services.motores import estadistica as estad
from services.motores import texto as limpieza_texto
from services.motores.base import Entrada, ErrorLimpieza, Hallazgo, ResultadoAutomatico, ResultadoFinal
from services.motores.encuestas.universales import identificador
from services.motores.pruebas import clave as cl

_FILAS_VISTA = 12
_COLUMNAS_SALIDA = ["id_alumno", "pregunta", "respuesta", "respuesta_correcta", "correcta", "estado", "motivo"]
# Palabras que delatan una clave en formato largo (columna de pregunta y de respuesta).
_COL_PREGUNTA = re.compile(r"^(pregunta|reactivo|item|ítem|no\.?|n[uú]mero|id[_ ]?pregunta)$", re.I)
_COL_RESPUESTA = re.compile(r"^(respuesta|clave|correcta|respuesta[_ ]?correcta|opci[oó]n[_ ]?correcta)$", re.I)


def _cfg() -> dict[str, Any]:
    return configuracion.reglas()["pruebas"]


def _opciones() -> set[str]:
    """Letras válidas de opción múltiple (sin «NR»)."""
    return {o.upper() for o in _cfg().get("opciones_validas", [])} - {"NR"}


def _clave_pregunta(nombre: str) -> str:
    """Forma comparable de un id de pregunta (P1, p1, «P 1» y «Pregunta 1» coinciden)."""
    n = normalizar_texto(nombre).replace(" ", "")
    return re.sub(r"^pregunta", "p", n)


# ── 1. Validación del archivo ──────────────────────────────────────────────────


def _leer_tabla(contenido: bytes, extension: str, que: str) -> RawTable:
    if extension not in (".csv", ".xlsx", ".xls"):
        raise ErrorLimpieza(f"La {que} debe ser un archivo .csv, .xlsx o .xls (recibido: {extension or 'sin extensión'}).")
    try:
        tabla = read_tabular(contenido, extension)
    except TabularParseError as exc:
        raise ErrorLimpieza(f"No se pudo leer la {que}: {exc}") from exc
    if extension == ".csv" and len(tabla.headers) < 2:
        raise ErrorLimpieza(f"La {que} no usa un delimitador reconocido: separa las columnas con coma (,) o punto y coma (;).")
    if not tabla.rows:
        raise ErrorLimpieza(f"La {que} no tiene filas de datos.")
    return tabla


def _leer_clave(entrada: Entrada) -> dict[str, tuple[str, str]] | None:
    """Clave de respuestas: {pregunta_comparable: (pregunta, respuesta_correcta)}, o None si no se subió.

    Acepta dos formas:
      - larga: una fila por pregunta (columnas «pregunta» y «respuesta», o 2 columnas);
      - ancha: encabezados = preguntas y una fila con las respuestas correctas.
    Respuestas válidas: una letra de `opciones_validas`, V/F, o el puntaje máximo (entero).
    """
    if entrada.clave is None:
        return None
    tabla = _leer_tabla(entrada.clave, entrada.extension_clave or "", "clave de respuestas")
    encabezados = [h.strip() for h in tabla.headers]
    i_preg = next((i for i, h in enumerate(encabezados) if _COL_PREGUNTA.match(h)), None)
    i_resp = next((i for i, h in enumerate(encabezados) if _COL_RESPUESTA.match(h)), None)
    pares: list[tuple[str, str]]
    if i_preg is not None and i_resp is not None:
        pares = [(f[i_preg].strip(), f[i_resp].strip()) for f in tabla.rows if f[i_preg].strip()]
    elif len(tabla.rows) == 1:
        pares = [(h, tabla.rows[0][j].strip()) for j, h in enumerate(encabezados) if h]
    elif len(encabezados) == 2:
        # Dos columnas sin nombres reconocibles: la primera fila también es dato.
        pares = [(encabezados[0], encabezados[1])] + [(f[0].strip(), f[1].strip()) for f in tabla.rows if f[0].strip()]
    else:
        raise ErrorLimpieza(
            "No se reconoció el formato de la clave: usa una fila por pregunta (columnas «pregunta» y "
            "«respuesta») o una sola fila con las preguntas como encabezados. Si no tienes la clave, "
            "sube la prueba sin ella y te propondremos una a partir de las respuestas."
        )
    validas = _opciones()
    clave: dict[str, tuple[str, str]] = {}
    for pregunta, respuesta in pares:
        respuesta = respuesta.strip().upper()
        tipo = cl.tipo_de_respuesta_correcta(respuesta, validas)
        if tipo is None:
            raise ErrorLimpieza(
                f"La clave tiene una respuesta no válida para «{pregunta}»: «{respuesta}». "
                f"Usa {', '.join(sorted(validas))}, V/F o el puntaje máximo (p. ej. 2)."
            )
        clave[_clave_pregunta(pregunta)] = (pregunta, cl.normalizar_vf(respuesta) if tipo[0] == cl.VERDADERO_FALSO else respuesta)
    if not clave:
        raise ErrorLimpieza("La clave de respuestas está vacía.")
    return clave


# ── 3. Validación estructural ──────────────────────────────────────────────────


@dataclass
class Estructura:
    id_col: int
    preguntas: list[tuple[str, str, int]]  # (pregunta de la clave, respuesta correcta, columna)
    extras: list[str]  # columnas que no son preguntas ni contexto: no se incluyen
    filas: list[tuple[int, str, list[str]]]  # (fila original 1-indexada, id_alumno, celdas)
    filas_vacias: int
    sin_id: int
    duplicados: dict[str, list[int]] = field(default_factory=dict)  # id → filas (1-indexadas)
    encoding: str | None = None
    # Columnas de contexto del alumno (turno, semestre…): (id en el CSV limpio, encabezado, columna).
    contexto: list[tuple[str, str, int]] = field(default_factory=list)
    # Tipo de cada reactivo: {pregunta: (opcion_multiple | verdadero_falso | puntos, puntaje máximo)}.
    tipos: dict[str, tuple[str, int | None]] = field(default_factory=dict)
    clave_origen: str = "archivo"  # archivo | inferida
    propuesta: list[cl.Detectado] = field(default_factory=list)  # solo si la clave es inferida
    criterio_propuesta: str = ""

    def con_clave(self, decisiones: dict[str, str]) -> "Estructura":
        """La misma estructura con la clave que decidió el investigador (clave inferida)."""
        if self.clave_origen != "inferida":
            return self
        preguntas = [(p, decisiones.get(f"clave:{p}", c) or c, col) for p, c, col in self.preguntas]
        return Estructura(self.id_col, preguntas, self.extras, self.filas, self.filas_vacias, self.sin_id, self.duplicados,
                          self.encoding, self.contexto, self.tipos, self.clave_origen, self.propuesta, self.criterio_propuesta)


_SEPARADORES = re.compile(r"[_.\-/()]+")


def _es_contexto(encabezado: str) -> bool:
    """¿La columna es un dato de contexto del alumno? Palabra completa de `palabras_contexto`
    (las mismas de las encuestas). Nombres, correos y similares NO son contexto."""
    palabras = [normalizar_texto(x) for x in configuracion.reglas()["encuestas"].get("palabras_contexto", [])]
    texto = " " + " ".join(_SEPARADORES.sub(" ", normalizar_texto(encabezado)).split()) + " "
    return any(f" {p} " in texto for p in palabras)


def _estructura(entrada: Entrada, clave: dict[str, tuple[str, str]] | None) -> Estructura:
    tabla = _leer_tabla(entrada.contenido, entrada.extension, "hoja de respuestas")
    encabezados = [h.strip() for h in tabla.headers]
    comparables = [_clave_pregunta(h) for h in encabezados]
    opciones = _opciones()

    patrones = [re.compile(p, re.I) for p in _cfg().get("columna_id", [])]
    id_col = next((i for i, h in enumerate(encabezados) if any(p.match(normalizar_texto(h)) for p in patrones)), None)
    if id_col is None and clave is not None:
        # Respaldo: la primera columna que no es una pregunta de la clave.
        id_col = next((i for i, c in enumerate(comparables) if c not in clave), None)
    if id_col is None and clave is None:
        id_col = 0  # sin clave: la primera columna identifica al alumno
    if id_col is None:
        raise ErrorLimpieza("No se encontró la columna con el identificador del alumno (por ejemplo «id_alumno» o «matrícula»).")

    tipos: dict[str, tuple[str, int | None]] = {}
    propuesta: list[cl.Detectado] = []
    criterio = ""
    puntaje_col: int | None = None
    if clave is not None:
        faltantes = [clave[c][0] for c in clave if c not in comparables]
        if faltantes:
            lista = ", ".join(faltantes[:10]) + ("…" if len(faltantes) > 10 else "")
            raise ErrorLimpieza(f"La hoja de respuestas no tiene columnas para {len(faltantes)} pregunta(s) de la clave: {lista}.")
        preguntas = [(clave[c][0], clave[c][1], comparables.index(c)) for c in clave]
        for nombre, correcta, _ in preguntas:
            tipos[nombre] = cl.tipo_de_respuesta_correcta(correcta, opciones) or (cl.OPCION_MULTIPLE, None)
        origen = "archivo"
    else:
        # Sin clave: se detectan los reactivos por sus valores y se propone la clave.
        filas_crudas = [[c.strip() for c in f] for f in tabla.rows if any(c.strip() for c in f)]
        excluidas = {id_col} | {i for i, h in enumerate(encabezados) if _es_contexto(h)}
        propuesta, puntaje_col = cl.detectar(encabezados, filas_crudas, excluidas, opciones)
        if not propuesta:
            raise ErrorLimpieza(
                "No se encontraron columnas de reactivos (letras A–D, V/F o puntos) en la hoja de respuestas. "
                "Sube la prueba junto con su clave de respuestas."
            )
        criterio = cl.proponer(propuesta, filas_crudas, puntaje_col, opciones)
        preguntas = [(d.nombre, d.propuesta, d.columna) for d in propuesta]
        tipos = {d.nombre: (d.tipo, d.puntos_max) for d in propuesta}
        origen = "inferida"
    usadas = {id_col} | {p[2] for p in preguntas}
    # Las columnas de contexto se conservan al final del CSV largo (para consultas como
    # «¿qué porcentaje del turno vespertino acertó…?»); el resto de columnas extra no.
    ids = set(_COLUMNAS_SALIDA)
    contexto = [
        (identificador(encabezados[i], ids), encabezados[i], i)
        for i in range(len(encabezados))
        # El puntaje global (score_estimado…) también es un dato del alumno, no un reactivo.
        if i not in usadas and encabezados[i] and (_es_contexto(encabezados[i]) or i == puntaje_col)
    ]
    usadas |= {i for _, _, i in contexto}
    extras = [encabezados[i] or f"Columna {i + 1}" for i in range(len(encabezados)) if i not in usadas]

    filas: list[tuple[int, str, list[str]]] = []
    vacias = 0
    sin_id = 0
    for n, fila in enumerate(tabla.rows, start=2):  # fila 1 = encabezados
        celdas = [c.strip() for c in fila]
        if not any(celdas):
            vacias += 1
            continue
        alumno = celdas[id_col] if id_col < len(celdas) else ""
        if not alumno:
            sin_id += 1
            alumno = f"sin_id_fila_{n}"
        filas.append((n, alumno, celdas))
    if not filas:
        raise ErrorLimpieza("La hoja de respuestas no tiene alumnos (todas las filas están vacías).")
    por_id: dict[str, list[int]] = {}
    for n, alumno, _ in filas:
        por_id.setdefault(alumno, []).append(n)
    duplicados = {a: ns for a, ns in por_id.items() if len(ns) > 1}
    return Estructura(id_col, preguntas, extras, filas, vacias, sin_id, duplicados, tabla.encoding, contexto,
                      tipos, origen, propuesta, criterio)


# ── 4–6. Respuestas ────────────────────────────────────────────────────────────


def clasificar(
    valor: str,
    validas: set[str],
    ilegibles: set[str],
    correcta: str,
    tipo: str = cl.OPCION_MULTIPLE,
    puntos_max: int | None = None,
) -> tuple[int | None, str, str]:
    """(correcta 1/0 —None si el reactivo no es calificable—, estado, motivo) de una respuesta."""
    texto = valor.strip().upper()
    calificable = tipo in cl.CALIFICABLES
    if not texto or texto == "NR":
        return (0 if calificable else None), "NR", "no_respondida"
    if any(c in texto for c in ilegibles):
        return (0 if calificable else None), "nula", "ilegible"
    if tipo == cl.VERDADERO_FALSO:
        vf = cl.normalizar_vf(texto)
        if vf is None:
            return 0, "nula", "caracter_invalido"
        return (1 if vf == correcta else 0), "valida", ""
    if tipo == cl.PUNTOS:
        # Respuesta ya calificada: acierto = puntaje máximo; el parcial queda en la respuesta.
        if not texto.isdigit() or puntos_max is None or int(texto) > puntos_max:
            return 0, "nula", "caracter_invalido"
        return (1 if int(texto) == puntos_max else 0), "valida", ""
    # No calificables: se valida el formato, pero no hay acierto (None).
    if tipo == cl.ESCALA:
        ok = texto.isdigit() and puntos_max is not None and 1 <= int(texto) <= puntos_max
        return (None, "valida", "") if ok else (None, "nula", "caracter_invalido")
    if tipo == cl.SI_NO:
        return (None, "valida", "") if cl.normalizar_si_no(texto) else (None, "nula", "caracter_invalido")
    if tipo == cl.NUMERICA:
        return (None, "valida", "") if cl._es_numero(texto) else (None, "nula", "caracter_invalido")
    letras = [c for c in re.split(r"[\s,;/|+-]+", texto) if c]
    # «AB» o «A,B»: varias opciones marcadas.
    if len(letras) == 1 and len(letras[0]) > 1 and all(ch in validas for ch in letras[0]):
        letras = list(letras[0])
    if len(letras) > 1 and all(l in validas for l in letras):
        return 0, "nula", "respuesta_multiple"
    if texto not in validas:
        return 0, "nula", "caracter_invalido"
    return (1 if texto == correcta else 0), "valida", ""


def _evaluar(est: Estructura, decisiones: dict[str, str]) -> tuple[list[list[str]], dict[str, Any]]:
    cfg = _cfg()
    est = est.con_clave(decisiones)
    validas = _opciones()
    ilegibles = set(cfg.get("caracteres_ilegibles", []))
    filas_salida: list[list[str]] = []
    vistos: Counter = Counter()
    eliminadas = 0
    matriz: list[list[int]] = []  # aciertos por alumno (sin los registros anulados por duplicado)
    elegidas: list[Counter] = [Counter() for _ in est.preguntas]
    for n, alumno, celdas in est.filas:
        vistos[alumno] += 1
        repetida = alumno in est.duplicados and vistos[alumno] > 1
        decision = decisiones.get(f"id-duplicado:{alumno}", "conservar_primero")
        if alumno in est.duplicados and decision == "eliminar_todos":
            eliminadas += 1
            continue
        anulado = repetida and decision == "conservar_primero"
        aciertos_alumno: list[int] = []
        valores_contexto = [celdas[c] if c < len(celdas) else "" for _, _, c in est.contexto]
        for j, (pregunta, correcta, col) in enumerate(est.preguntas):
            valor = celdas[col] if col < len(celdas) else ""
            if anulado:
                acierto, estado, motivo = 0, "nula", "duplicado"
            else:
                tipo, puntos_max = est.tipos.get(pregunta, (cl.OPCION_MULTIPLE, None))
                acierto, estado, motivo = clasificar(valor, validas, ilegibles, correcta, tipo, puntos_max)
                if tipo == cl.VERDADERO_FALSO:
                    elegida = cl.normalizar_vf(valor) or valor.strip().upper()
                elif tipo == cl.SI_NO:
                    elegida = cl.normalizar_si_no(valor) or valor.strip()
                else:
                    elegida = valor.strip().upper()
                elegidas[j][elegida if estado == "valida" else ("NR" if estado == "NR" else "nula")] += 1
            if est.tipos.get(pregunta, (cl.OPCION_MULTIPLE, None))[0] in cl.CALIFICABLES:
                aciertos_alumno.append(acierto or 0)
            # No calificables: sin respuesta correcta ni acierto (celdas vacías en el CSV).
            filas_salida.append([alumno, pregunta, valor, correcta if acierto is not None else "",
                                 "" if acierto is None else str(acierto), estado, motivo, *valores_contexto])
        if not anulado:
            matriz.append(aciertos_alumno)
    estados = Counter(f[5] for f in filas_salida)
    motivos = Counter(f[6] for f in filas_salida if f[6])
    validas_n = estados.get("valida", 0)
    aciertos = sum(int(f[4]) for f in filas_salida if f[4])
    calificadas = sum(1 for f in filas_salida if f[4] != "" and f[5] == "valida")
    alumnos = {f[0] for f in filas_salida}
    resumen = {
        "n_alumnos": len(alumnos),
        "n_preguntas": len(est.preguntas),
        "n_respuestas": len(filas_salida),
        "conteos": {"valida": validas_n, "nula": estados.get("nula", 0), "NR": estados.get("NR", 0)},
        "motivos": {m: motivos.get(m, 0) for m in ("duplicado", "no_respondida", "respuesta_multiple", "caracter_invalido", "ilegible")},
        "pct_correctas_validas": round(aciertos / calificadas, 4) if calificadas else 0.0,
        "aciertos_promedio": round(aciertos / len(alumnos), 2) if alumnos else 0.0,
        "filas_eliminadas_por_duplicado": eliminadas,
        "estadistica": _estadistica(est, matriz, elegidas, sorted(validas)),
        "clave_final": {p: c for p, c, _ in est.preguntas if est.tipos.get(p, (cl.OPCION_MULTIPLE, None))[0] in cl.CALIFICABLES},
    }
    return filas_salida, resumen


def _estadistica(est: Estructura, matriz: list[list[int]], elegidas: list[Counter], opciones: list[str]) -> dict[str, Any]:
    """Análisis de reactivos, puntajes y KR-20 de la prueba."""
    grupo = float(_cfg().get("grupo_extremo", 0.27))
    # La matriz de aciertos solo tiene los reactivos calificables (en su orden).
    calificables = [j for j, (p, _, _) in enumerate(est.preguntas) if est.tipos.get(p, (cl.OPCION_MULTIPLE, None))[0] in cl.CALIFICABLES]
    analisis_cal = estad.analisis_reactivos(matriz, grupo) if matriz and calificables else [{} for _ in calificables]
    analisis: list[dict[str, Any]] = [{} for _ in est.preguntas]
    for k, j in enumerate(calificables):
        analisis[j] = analisis_cal[k] if k < len(analisis_cal) else {}
    reactivos = []
    for j, (pregunta, correcta, _) in enumerate(est.preguntas):
        total = sum(elegidas[j].values())
        tipo, puntos_max = est.tipos.get(pregunta, (cl.OPCION_MULTIPLE, None))
        if tipo == cl.VERDADERO_FALSO:
            opciones_item = ["V", "F"]
        elif tipo == cl.PUNTOS:
            opciones_item = [str(i) for i in range(0, (puntos_max or 0) + 1)]
        elif tipo == cl.ESCALA:
            opciones_item = [str(i) for i in range(1, (puntos_max or 0) + 1)]
        elif tipo == cl.SI_NO:
            opciones_item = ["Sí", "No"]
        elif tipo == cl.NUMERICA:
            opciones_item = []
        else:
            opciones_item = opciones
        distribucion = [
            {"opcion": o, "n": elegidas[j].get(o, 0), "pct": round(elegidas[j].get(o, 0) / total, 4) if total else 0.0, "correcta": o == correcta}
            for o in [*opciones_item, "nula", "NR"]
        ]
        # Distractores que nadie eligió: no están funcionando como opción plausible (no aplica a puntos).
        sin_elegir = [o for o in opciones_item if o != correcta and elegidas[j].get(o, 0) == 0] if tipo in (cl.OPCION_MULTIPLE, cl.VERDADERO_FALSO) else []
        reactivos.append({"pregunta": pregunta, "tipo_reactivo": tipo, "calificable": tipo in cl.CALIFICABLES,
                          "respuesta_correcta": correcta if tipo in cl.CALIFICABLES else None, **analisis[j],
                          "distribucion": distribucion, "distractores_sin_elegir": sin_elegir})
    k = len(calificables)
    totales = [sum(f) for f in matriz]
    puntajes = estad.descriptivos(totales) or {}
    kr = estad.kr20(matriz) if matriz else None
    return {
        "reactivos": reactivos,
        "puntajes": {**puntajes, "maximo_posible": k},
        "fiabilidad": {"kr20": round(kr, 4) if kr is not None else None, "interpretacion": estad.interpretar_alfa(kr), "n_alumnos": len(matriz), "n_reactivos": k},
        "resumen_reactivos": {
            "faciles": sum(1 for r in reactivos if r.get("nivel_dificultad") == "fácil"),
            "medios": sum(1 for r in reactivos if r.get("nivel_dificultad") == "media"),
            "dificiles": sum(1 for r in reactivos if r.get("nivel_dificultad") == "difícil"),
            "discriminacion_pobre": sum(1 for r in reactivos if r.get("nivel_discriminacion") == "pobre"),
        },
    }


def _hallazgos_clave(est: Estructura) -> list[Hallazgo]:
    """Clave propuesta: una confirmación obligatoria y un hallazgo por reactivo para corregirlo."""
    criterio = {
        "puntaje_global": "el 27 % de alumnos con mayor puntaje global",
        "acuerdo_entre_alumnos": "el 27 % de alumnos que más coincide con las respuestas más frecuentes",
    }.get(est.criterio_propuesta, "los alumnos de mejor desempeño")
    clave = [f"{d.nombre} → {d.propuesta}" for d in est.propuesta if d.tipo in cl.CALIFICABLES]
    no_calif = [d.nombre for d in est.propuesta if d.tipo not in cl.CALIFICABLES]
    salida = [
        Hallazgo(
            id="clave-confirmar", tipo="clave_propuesta", tema="Clave de respuestas propuesta", objetivo="clave",
            titulo=f"La prueba no trae clave: revisa la propuesta para {len(clave)} reactivo(s)",
            descripcion=(
                f"Para cada reactivo proponemos la respuesta más elegida por {criterio}. Puede fallar en "
                "reactivos muy difíciles: corrige abajo los que no estén bien y luego confírmala. Los "
                "reactivos de puntos usan el puntaje máximo como respuesta correcta."
                + (f" {len(no_calif)} reactivo(s) de autoinforme o respuesta abierta (escala, Sí/No, número) no se califican." if no_calif else "")
            ),
            opciones=["confirmar"], sugerida=None, obligatoria=True,
            detalle={"ejemplos": clave[:40], "criterio": est.criterio_propuesta},
        )
    ]
    for d in est.propuesta:
        if d.tipo not in (cl.OPCION_MULTIPLE, cl.VERDADERO_FALSO):
            continue  # puntos: correcta = puntaje máximo; no calificables: sin respuesta correcta
        opciones = ["V", "F"] if d.tipo == cl.VERDADERO_FALSO else sorted(_opciones())
        salida.append(
            Hallazgo(
                id=f"clave:{d.nombre}", tipo="clave_reactivo", tema="Clave de respuestas propuesta", objetivo=d.nombre,
                titulo=f"Respuesta correcta de «{d.nombre}»",
                descripcion=f"Propuesta: «{d.propuesta or '—'}», elegida por el {round(d.confianza * 100)} % del grupo de referencia.",
                opciones=opciones, sugerida=d.propuesta or None, obligatoria=not d.propuesta,
                detalle={"ejemplos": [f"{o}: {round(pct * 100)} %" for o, pct in d.alternativas[:4]]},
            )
        )
    return salida


# ── Motores ────────────────────────────────────────────────────────────────────


class MotorPruebasTabular:
    """Limpieza de pruebas estandarizadas en tabla (respuestas + clave)."""

    nombre = "pruebas_tabular"

    def _preparar(self, entrada: Entrada) -> tuple[Estructura, dict]:
        clave = _leer_clave(entrada)
        return _estructura(entrada, clave), clave

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        est, _ = self._preparar(entrada)
        cfg = _cfg()
        _, resumen = _evaluar(est, {})
        transformaciones = [
            {"regla": "validacion_archivo", "detalle": "Formato, delimitador y estructura (preguntas en columnas, alumnos en filas) válidos.", "afectados": None},
            {"regla": "codificacion_utf8", "detalle": f"Texto convertido a UTF-8 (origen: {est.encoding or 'Excel'}).", "afectados": None},
        ]
        if est.filas_vacias:
            transformaciones.append({"regla": "filas_vacias", "detalle": "Filas vacías eliminadas.", "afectados": est.filas_vacias})
        transformaciones.append({"regla": "respuestas_validadas", "detalle": f"Respuestas comparadas con las opciones válidas ({', '.join(cfg.get('opciones_validas', []))}).", "afectados": resumen["n_respuestas"]})
        # Las nulas por ID duplicado dependen de la decisión del investigador: no son automáticas.
        nulas = resumen["conteos"]["nula"] - resumen["motivos"]["duplicado"]
        if nulas:
            transformaciones.append({"regla": "respuestas_nulificadas", "detalle": "Respuestas múltiples, ilegibles o con caracteres inválidos marcadas como nulas.", "afectados": nulas})
        if resumen["conteos"]["NR"]:
            transformaciones.append({"regla": "no_respondidas", "detalle": "Respuestas vacías marcadas como NR (no respondida).", "afectados": resumen["conteos"]["NR"]})

        avisos = []
        if est.clave_origen == "inferida":
            transformaciones.append({"regla": "clave_propuesta", "detalle": "La prueba no trae clave: se propuso una a partir de las respuestas (confírmala o corrígela).", "afectados": len(est.propuesta)})
            avisos.append("La prueba no trae clave de respuestas: te proponemos una a partir de las respuestas de los alumnos de mejor desempeño. Revísala antes de confirmar.")
        if est.contexto:
            avisos.append(f"Se conservan como datos de contexto del alumno: {', '.join(e for _, e, _ in est.contexto)}.")
        if est.extras:
            avisos.append(f"La hoja de respuestas tiene {len(est.extras)} columna(s) que no están en la clave y no se incluirán: {', '.join(est.extras[:6])}.")
        if est.sin_id:
            avisos.append(f"{est.sin_id} fila(s) no tienen identificador de alumno; se les asignó uno con su número de fila.")

        hallazgos = [
            Hallazgo(
                id=f"id-duplicado:{alumno}", tipo="id_duplicado", tema="Identificadores repetidos", objetivo=alumno,
                titulo=f"El alumno «{alumno}» aparece {len(filas)} veces",
                descripcion="Te sugerimos conservar la primera aparición y marcar las demás como nulas (motivo «duplicado»).",
                opciones=["conservar_primero", "conservar_todos", "eliminar_todos"], sugerida="conservar_primero",
                detalle={"filas": filas},
            )
            for alumno, filas in est.duplicados.items()
        ]
        if est.clave_origen == "inferida":
            hallazgos = _hallazgos_clave(est) + hallazgos
        metricas = {
            "n_alumnos": len({a for _, a, _ in est.filas}),
            "n_filas": len(est.filas) + est.filas_vacias,
            "n_preguntas": len(est.preguntas),
            "n_filas_vacias": est.filas_vacias,
            "n_ids_duplicados": len(est.duplicados),
            "columnas_extra": est.extras,
            "conteos": resumen["conteos"],
            "motivos": resumen["motivos"],
        }
        especifico = {
            "opciones_validas": cfg.get("opciones_validas", []),
            "ilegibles": cfg.get("caracteres_ilegibles", []),
            "clave": {p: c for p, c, _ in est.preguntas},
            "ids_duplicados": list(est.duplicados),
            "columnas_extra": est.extras,
            "columnas_contexto": [{"id": i, "etiqueta": e} for i, e, _ in est.contexto],
            "clave_origen": est.clave_origen,
            "tipos_reactivo": {p: t for p, (t, _) in est.tipos.items()},
            "puntos_max": {p: m for p, (t, m) in est.tipos.items() if t in (cl.PUNTOS, cl.ESCALA)},
        }
        metricas["pct_correctas_validas"] = resumen["pct_correctas_validas"]
        metricas["kr20"] = resumen["estadistica"]["fiabilidad"]["kr20"]
        return ResultadoAutomatico(hallazgos, transformaciones, metricas, especifico, avisos, resumen["estadistica"])

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        est, _ = self._preparar(entrada)
        filas, resumen = _evaluar(est, decisiones)
        transformaciones = []
        if resumen["motivos"]["duplicado"]:
            transformaciones.append({"regla": "duplicados_nulificados", "detalle": "Respuestas de alumnos repetidos marcadas como nulas (motivo «duplicado»).", "afectados": resumen["motivos"]["duplicado"]})
        if resumen["filas_eliminadas_por_duplicado"]:
            transformaciones.append({"regla": "duplicados_eliminados", "detalle": "Registros de alumnos repetidos eliminados.", "afectados": resumen["filas_eliminadas_por_duplicado"]})
        especifico = dict(automatico.especifico)
        especifico.update({k: resumen[k] for k in ("n_alumnos", "n_preguntas", "conteos", "motivos", "pct_correctas_validas", "aciertos_promedio")})
        especifico["clave"] = resumen["clave_final"]  # con las correcciones del investigador, si la clave fue propuesta
        metricas = {
            "n_alumnos": resumen["n_alumnos"],
            "n_preguntas": resumen["n_preguntas"],
            "n_respuestas": resumen["n_respuestas"],
            "n_ids_duplicados": sum(1 for a in est.duplicados if decisiones.get(f"id-duplicado:{a}") == "conservar_todos"),
            "conteos": resumen["conteos"],
            "motivos": resumen["motivos"],
            "pct_correctas_validas": resumen["pct_correctas_validas"],
            "kr20": resumen["estadistica"]["fiabilidad"]["kr20"],
        }
        especifico["fiabilidad"] = resumen["estadistica"]["fiabilidad"]
        return ResultadoFinal(
            encabezados=_COLUMNAS_SALIDA + [i for i, _, _ in est.contexto],
            filas=filas,
            metricas=metricas,
            especifico=especifico,
            transformaciones=transformaciones,
            cifras=[
                {"etiqueta": "Alumnos", "valor": resumen["n_alumnos"]},
                {"etiqueta": "Preguntas", "valor": resumen["n_preguntas"]},
                {"etiqueta": "Respuestas nulas", "valor": resumen["conteos"]["nula"]},
                {"etiqueta": "No respondidas", "valor": resumen["conteos"]["NR"]},
            ],
            vista={
                "forma": "tabla",
                "columnas": ["Alumno", "Pregunta", "Respuesta", "Clave", "Correcta", "Estado", "Motivo"],
                "filas": [[f[0], f[1], f[2] or "—", f[3], f[4], f[5], f[6].replace("_", " ")] for f in filas[:_FILAS_VISTA]],
            },
            estadistica=resumen["estadistica"],
        )


class MotorPruebasDocumento:
    """Limpieza de pruebas entregadas como documento (el examen en texto)."""

    nombre = "pruebas_documento"

    def _preparar(self, entrada: Entrada) -> limpieza_texto.ResultadoTexto:
        try:
            doc = read_document(entrada.contenido, entrada.extension)
        except DocumentParseError as exc:
            raise ErrorLimpieza(f"No se pudo leer la prueba: {exc}") from exc
        if not doc.text.strip():
            raise ErrorLimpieza("No se pudo extraer texto del archivo (si es un PDF escaneado, necesita OCR).")
        maximo = int(configuracion.reglas()["entrevistas"].get("max_iteraciones_ruido", 3))
        resultado = limpieza_texto.limpiar(doc.text, maximo)
        if not resultado.texto.strip():
            raise ErrorLimpieza("Después de quitar el ruido, la prueba quedó sin texto.")
        return resultado

    @staticmethod
    def _bloques(texto: str) -> list[str]:
        bloques = [" ".join(b.split()) for b in re.split(r"\n\s*\n", texto) if b.strip()]
        return bloques if len(bloques) > 1 else [l.strip() for l in texto.split("\n") if l.strip()]

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        resultado = self._preparar(entrada)
        hallazgos = []
        if resultado.residual:
            hallazgos.append(
                Hallazgo(
                    id="ruido-residual", tipo="ruido_residual", tema="Ruido", objetivo="texto",
                    titulo=f"{len(resultado.residual)} fragmento(s) de ruido sin resolver",
                    descripcion="Puedes eliminar esas líneas o conservarlas.",
                    opciones=["eliminar", "conservar"], sugerida="conservar",
                    detalle={"ejemplos": [r["texto"] for r in resultado.residual[:4]]},
                )
            )
        metricas = {"n_palabras": len(resultado.texto.split()), "ruido_detectado": len(resultado.residual) + sum(resultado.eliminado.values())}
        especifico = {"formato": "documento", "iteraciones_ruido": resultado.iteraciones, "ruido_eliminado": resultado.eliminado, "ruido_residual": resultado.residual}
        return ResultadoAutomatico(hallazgos, resultado.transformaciones, metricas, especifico, [])

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        resultado = self._preparar(entrada)
        texto = resultado.texto
        if resultado.residual and decisiones.get("ruido-residual") == "eliminar":
            texto = limpieza_texto.quitar_lineas(texto, {r["linea"] for r in resultado.residual})
        bloques = self._bloques(texto)
        filas = [[str(i), b] for i, b in enumerate(bloques, start=1)]
        palabras = sum(len(b.split()) for b in bloques)
        ruido = sum(v for k, v in resultado.eliminado.items() if k != "palabras_reconstruidas")
        return ResultadoFinal(
            encabezados=["n_bloque", "texto"],
            filas=filas,
            metricas={"n_bloques": len(bloques), "n_palabras": palabras, "ruido_detectado": len(limpieza_texto.detectar_ruido(texto))},
            especifico={**automatico.especifico, "n_bloques": len(bloques)},
            transformaciones=[],
            cifras=[
                {"etiqueta": "Bloques de texto", "valor": len(bloques)},
                {"etiqueta": "Palabras", "valor": palabras},
                {"etiqueta": "Ruido eliminado", "valor": ruido},
            ],
            vista={"forma": "turnos", "columnas": ["#", "Texto"], "filas": [[f[0], f[1][:280] + ("…" if len(f[1]) > 280 else "")] for f in filas[:_FILAS_VISTA]]},
        )
