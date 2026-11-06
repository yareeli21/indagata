"""Motor de limpieza de encuestas (CSV, XLSX, XLS).

Fase automática (sin decisiones):
  estructura de las filas (acentos rotos, encabezado repetido, fila de totales, segunda fila de encabezado,
  filas corridas; ver `motores/filas.py`) → transformaciones universales → números escritos de otra forma
  (`numeros.py`) → Sí / No y opciones parecidas (`categorias.py`) → columnas ajenas al instrumento
  (propuestas) → roles sugeridos → tipos canónicos provisionales → métricas (Tabla 3) → hallazgos.

Las decisiones que cambian la estructura (fila de totales, segunda fila de encabezado, filas corridas, «1» / «0»
en Sí / No, opciones parecidas) se aplican ANTES de inferir los tipos: la fila «Promedio» convertía una escala
1–5 en una calificación 0–10. En la fase automática se usa la opción sugerida de cada una.

Fase asistida (decide el investigador): columnas ajenas, roles dudosos, columnas
muy incompletas, filas duplicadas, valores fuera de rango, escalas que parecen
Likert pero no están en el diccionario, ítems Likert invertidos, encuestados que
responden en línea recta, encuestados que dejaron casi todo sin responder y respuestas
«No sé / No aplica» (conservarlas marcadas o dejarlas vacías).

Medidas estadísticas (antes y después): descriptivos por columna, frecuencias,
atípicos (±4σ e IQR) y fiabilidad (alfa de Cronbach por bloque de ítems Likert).

`aplicar` repite la preparación (determinista) y aplica las decisiones.
"""
from __future__ import annotations

from collections import Counter

import dataclasses
import re
from dataclasses import dataclass, field
from typing import Any

from shared.parsing import TabularParseError, read_tabular

from services import configuracion
from services.configuracion import normalizar_texto
from services.motores import codificacion
from services.motores import estadistica as est
from services.motores import filas as estructura_filas
from services.motores.base import Entrada, ErrorLimpieza, Hallazgo, ResultadoAutomatico, ResultadoFinal
from services.motores.encuestas import categorias
from services.motores.encuestas import dimensiones as dims
from services.motores.encuestas import numeros
from services.motores.encuestas import universales
from services.motores.encuestas.likert import Likert, equivalente, likert_desde_orden, no_respuestas, numero
from services.motores.encuestas.tipos import InfoTipo, grupo_bloque, grupo_de, inferir, metodo_atipicos

_FILAS_VISTA = 10
_EJEMPLOS = 4
# «2026/10/10 10:00:00», «2026-10-10T10:00», «10/10/2026 10:00 a. m.»: marcas de tiempo de las plataformas.
_FECHA_HORA = re.compile(r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}[ T]\d{1,2}:\d{2}(:\d{2})?( ?[ap]\.? ?m\.?)?", re.IGNORECASE)


@dataclass
class Estado:
    """Todo lo que deciden juntas la fase automática y la aplicación."""

    tabla: universales.TablaPreparada
    tipos: dict[str, InfoTipo]  # por id de columna
    ajenas: set[str]
    rol_auto: dict[str, str]  # roles decididos automáticamente (encabezado > 25 caracteres)
    duplicadas: list[int]  # filas repetidas (se conserva la primera aparición)
    metricas_antes: dict[str, Any]
    linea_recta: list[int] = field(default_factory=list)  # encuestados con la misma respuesta en todo un bloque
    bloques_linea_recta: list[str] = field(default_factory=list)
    incompletos: list[int] = field(default_factory=list)  # encuestados que dejaron casi todo vacío
    # Dimensiones por correlación (sin secciones ni prefijos): propuestas y las confirmadas.
    dimensiones_sugeridas: list[dict[str, Any]] = field(default_factory=list)
    info_dimensiones: dict[str, int] = field(default_factory=dict)
    dimensiones: list[dict[str, Any]] = field(default_factory=list)
    # Selecciones múltiples que marcan «Ninguno» junto con otras opciones: {columna: filas}.
    contradictorias: dict[str, list[int]] = field(default_factory=dict)
    # Estructura de las filas del archivo (antes de las transformaciones universales).
    revision: estructura_filas.RevisionFilas = field(default_factory=estructura_filas.RevisionFilas)
    encabezados_crudos: list[str] = field(default_factory=list)
    filas_crudas: list[list[str]] = field(default_factory=list)  # ya con los acentos reparados
    # Columnas de Sí / No con «1» y «0», y opciones poco frecuentes parecidas a otra.
    si_no: list[categorias.SiNoCodigos] = field(default_factory=list)
    parecidas: list[categorias.Parecida] = field(default_factory=list)
    # Transformaciones que resultan de decisiones (se reportan al aplicar, no en la fase automática).
    aplicado: list[dict] = field(default_factory=list)


def _cfg() -> dict[str, Any]:
    return configuracion.reglas()["encuestas"]


# ── Preparación (común a ambas fases) ──────────────────────────────────────────


def _leer(entrada: Entrada):  # noqa: ANN202
    try:
        tabla = read_tabular(entrada.contenido, entrada.extension)
    except TabularParseError as exc:
        raise ErrorLimpieza(f"No se pudo leer la encuesta: {exc}") from exc
    if not tabla.headers or not any(h.strip() for h in tabla.headers):
        raise ErrorLimpieza("La encuesta no tiene encabezados de columna en la primera fila.")
    if not tabla.rows:
        raise ErrorLimpieza("La encuesta no tiene respuestas (solo encabezados).")
    return tabla


def _es_ajena(etiqueta: str, patrones: list[str]) -> bool:
    texto = normalizar_texto(etiqueta)
    return any(re.search(p, texto) for p in patrones)


_SEPARADOR_OPCIONES = ";"
# Opciones que excluyen a las demás en una selección múltiple.
_EXCLUYENTES = {"ninguno", "ninguna", "ninguno de los anteriores", "ninguna de las anteriores", "no aplica", "nada"}


def _homologar(tabla: universales.TablaPreparada) -> dict | None:
    """Escribe cada respuesta con la forma más frecuente entre las que solo difieren en mayúsculas, acentos o
    signos de borde («PRESENCIAL», «presencial», «Presencial.» → «Presencial»; «3.» → «3»). En las selecciones
    múltiples («A;B») se homologa cada opción. Cambia los valores en sitio y devuelve la transformación con
    cada caso y su ubicación (28 oct: antes solo se homologaban, en silencio, las escalas Likert de texto).

    Va antes de inferir tipos y buscar duplicados: dos filas que solo difieren en «PRESENCIAL» y «Presencial»
    son la misma respuesta.
    """
    total = 0
    casos: list[dict] = []
    por_columna: dict[str, int] = {}
    for c in tabla.columnas:
        presentes = [v for v in c.valores if v is not None]
        if not presentes:
            continue
        multiple = sum(_SEPARADOR_OPCIONES in v for v in presentes) >= max(2, 0.05 * len(presentes))
        partes = [p.strip() for v in presentes for p in (v.split(_SEPARADOR_OPCIONES) if multiple else [v])]
        frecuencia: dict[str, Counter] = {}
        for p in partes:
            if p:
                frecuencia.setdefault(normalizar_texto(p), Counter())[p] += 1
        canon = {clave: max(formas.items(), key=lambda x: (x[1], x[0]))[0] for clave, formas in frecuencia.items() if len(formas) > 1}
        if not canon:
            continue

        def forma(p: str) -> str:
            p = p.strip()
            return canon.get(normalizar_texto(p), p) if p else p

        for i, v in enumerate(c.valores):
            if v is None:
                continue
            nuevo = _SEPARADOR_OPCIONES.join(forma(p) for p in v.split(_SEPARADOR_OPCIONES)) if multiple else forma(v)
            if nuevo != v:
                c.valores[i] = nuevo
                total += 1
                por_columna[c.etiqueta] = por_columna.get(c.etiqueta, 0) + 1
                if len(casos) < universales.MAX_CASOS:
                    casos.append({"fila": i + 1, "columna": c.etiqueta, "antes": v, "despues": nuevo})
    if not total:
        return None
    return {
        "regla": "escritura_homologada",
        "detalle": "Respuestas que solo difieren en mayúsculas, acentos o signos al inicio o al final se escriben igual "
                   "(con su forma más frecuente).",
        "afectados": total,
        "casos": casos,
        "columnas": por_columna,
    }


_TEXTO_SI_NO = {
    "uno_es_si": "1 = Sí, 0 = No",
    "uno_es_no": "1 = No, 0 = Sí",
    "anular": "se dejaron vacíos",
    "conservar": "se conservaron tal cual",
}


def _lista(filas: list[int], maximo: int = 10) -> str:
    return ", ".join(str(i + 1) for i in filas[:maximo]) + ("…" if len(filas) > maximo else "")


def _estructura(crudo, decisiones: dict[str, str]):  # noqa: ANN001, ANN202
    """Acentos rotos y estructura de las filas, con las decisiones del investigador (o las sugeridas).

    Devuelve (tabla cruda ya ordenada, transformaciones automáticas, transformaciones por decisión, revisión,
    filas con los acentos reparados, texto de las preguntas o None).
    """
    filas, casos_acentos = codificacion.reparar_filas(crudo.rows)
    revision = estructura_filas.revisar(crudo.headers, filas, crudo.irregulares)

    def encabezado(j: int) -> str:
        return (crudo.headers[j].strip() if j < len(crudo.headers) else "") or f"Columna {j + 1}"

    automaticas: list[dict] = []
    aplicado: list[dict] = []
    if casos_acentos:
        automaticas.append({
            "regla": "acentos_reparados",
            "detalle": "Acentos rotos al copiar entre programas, reparados («SÃ­» → «Sí»).",
            "afectados": len(casos_acentos),
            "casos": [{"fila": i + 1, "columna": encabezado(j), "antes": a, "despues": d}
                      for i, j, a, d in casos_acentos[: universales.MAX_CASOS]],
        })
    quitar = set(revision.repetidas)
    if revision.repetidas:
        automaticas.append({
            "regla": "encabezado_repetido",
            "detalle": f"Filas iguales al encabezado (dos exportaciones pegadas) descartadas: {_lista(revision.repetidas)}.",
            "afectados": len(revision.repetidas),
        })
    if revision.cortas:
        automaticas.append({
            "regla": "filas_completadas",
            "detalle": f"Filas con menos celdas que el encabezado, completadas con celdas vacías al final: {_lista(revision.cortas)}.",
            "afectados": len(revision.cortas),
        })
    resumen = [i for i in revision.resumen if decisiones.get(f"fila-resumen:{i + 1}", "eliminar") == "eliminar"]
    quitar |= set(resumen)
    if resumen:
        aplicado.append({"regla": "filas_resumen_eliminadas", "detalle": f"Filas de totales o promedios eliminadas: {_lista(resumen)}.",
                         "afectados": len(resumen)})
    textos = None
    if revision.segunda_encabezado and decisiones.get("encabezado-texto", "usar_como_texto") == "usar_como_texto":
        textos = filas[0]
        quitar.add(0)
        aplicado.append({"regla": "texto_de_preguntas", "detalle": "La primera fila (texto de las preguntas) se quitó de los "
                         "encuestados y se guardó como descripción de cada columna.", "afectados": 1})
    ordenadas = list(filas)
    reparadas, eliminadas = [], []
    for fc in revision.corridas:
        decision = decisiones.get(f"fila-corrida:{fc.fila + 1}", "reparar")
        if decision == "reparar":
            ordenadas[fc.fila] = fc.reparada
            reparadas.append(fc.fila)
        elif decision == "eliminar":
            eliminadas.append(fc.fila)
    eliminadas += [i for i, _ in revision.largas if decisiones.get(f"fila-larga:{i + 1}", "recortar") == "eliminar"]
    quitar |= set(eliminadas)
    if reparadas:
        aplicado.append({"regla": "filas_corridas_reparadas", "detalle": f"Filas corridas una columna, devueltas a su lugar: {_lista(reparadas)}.",
                         "afectados": len(reparadas)})
    if eliminadas:
        aplicado.append({"regla": "filas_irregulares_eliminadas", "detalle": f"Filas corridas o con celdas de más, eliminadas: {_lista(sorted(eliminadas))}.",
                         "afectados": len(eliminadas)})
    nuevo_indice: dict[int, int] = {}
    conservadas: list[list[str]] = []
    for i, f in enumerate(ordenadas):
        if i not in quitar:
            nuevo_indice[i] = len(conservadas)
            conservadas.append(f)
    cambiadas = {fc.fila for fc in revision.corridas}
    bordes = [(nuevo_indice[i], j, codificacion.reparar(v)[0]) for i, j, v in crudo.bordes
              if i in nuevo_indice and i not in cambiadas]
    tabla = dataclasses.replace(crudo, rows=conservadas, bordes=bordes, irregulares=[])
    return tabla, automaticas, aplicado, revision, filas, textos


def _id_parecida(p: categorias.Parecida) -> str:
    return f"categoria-parecida:{p.columna}={p.clave}"


def _preparar(entrada: Entrada, decisiones: dict[str, str] | None = None) -> Estado:
    cfg = _cfg()
    decisiones = decisiones or {}
    leido = _leer(entrada)
    metricas_antes = _metricas_crudas(leido, cfg)
    crudo, automaticas, aplicado, revision, filas_crudas, textos = _estructura(leido, decisiones)
    if not crudo.rows:
        raise ErrorLimpieza("Después de revisar la estructura de las filas, la encuesta no tiene respuestas.")
    tabla = universales.preparar(crudo, cfg.get("tokens_vacio", []))
    if not tabla.columnas or tabla.n_filas == 0:
        raise ErrorLimpieza("Después de quitar filas y columnas vacías, la encuesta no tiene datos.")
    tabla.transformaciones[1:1] = automaticas  # después de «Texto en UTF-8»
    if textos:
        for c in tabla.columnas:
            if c.indice_original < len(textos) and textos[c.indice_original].strip():
                c.extra["texto"] = textos[c.indice_original].strip()
    tabla.transformaciones.extend(numeros.normalizar(tabla))
    unificado, si_no = categorias.si_no(tabla)
    if unificado:
        tabla.transformaciones.append(unificado)
    for pendiente in si_no:
        decision = decisiones.get(f"si-no-codigos:{pendiente.columna}", "uno_es_si")
        if n := categorias.aplicar_si_no(tabla, pendiente, decision):
            aplicado.append({"regla": "si_no_codigos", "detalle": f"«1» y «0» en «{pendiente.etiqueta}»: {_TEXTO_SI_NO[decision]}.",
                             "afectados": n})
    if (homologacion := _homologar(tabla)) is not None:
        tabla.transformaciones.append(homologacion)
    parecidas = categorias.parecidas(tabla)
    casos_parecidas = []
    for p in parecidas:
        decision = decisiones.get(_id_parecida(p)) or f"cambiar:{p.destino}"
        if decision.startswith("cambiar:"):
            columna = next(c for c in tabla.columnas if c.id == p.columna)
            destino = decision.split(":", 1)[1]
            for i in p.filas:
                casos_parecidas.append({"fila": i + 1, "columna": p.etiqueta, "antes": columna.valores[i], "despues": destino})
                columna.valores[i] = destino
    if casos_parecidas:
        aplicado.append({"regla": "opciones_parecidas_cambiadas", "detalle": "Opciones poco frecuentes cambiadas por la opción "
                         "frecuente a la que se parecen.", "afectados": len(casos_parecidas), "casos": casos_parecidas})

    tipos = {c.id: inferir(c.etiqueta, c.valores, cfg) for c in tabla.columnas}
    ajenas = {c.id for c in tabla.columnas if _es_ajena(c.etiqueta, cfg.get("columnas_ajenas", []))}
    largo = int(cfg.get("largo_minimo_pregunta", 25))
    rol_auto = {c.id: "pregunta" for c in tabla.columnas if c.id not in ajenas and len(c.etiqueta) > largo}

    # Duplicados: filas idénticas sin contar las columnas ajenas (marcas de tiempo e IDs
    # hacen única cualquier fila aunque las respuestas sean las mismas). Tampoco cuentan las
    # columnas en las que TODOS los valores son distintos: no sirven para distinguir dos envíos
    # iguales y, si no se reconocieron como ajenas, escondían los duplicados (24 oct: con una
    # columna «Dirección IP» no reconocida, 5 duplicados inyectados pasaron sin detectarse).
    # Solo columnas con forma de identificador (sin espacios: IDs, IP, códigos) o de fecha y hora: una
    # pregunta abierta también tiene valores únicos y sí distingue a dos personas.
    def _todos_distintos(c) -> bool:  # noqa: ANN001
        presentes = [v for v in c.valores if v is not None]
        if len(presentes) != tabla.n_filas or len(set(presentes)) != tabla.n_filas or tabla.n_filas < 2:
            return False
        return all(not re.search(r"\s", v) or _FECHA_HORA.fullmatch(v.strip()) for v in presentes)

    instrumento = [c for c in tabla.columnas if c.id not in ajenas and not _todos_distintos(c)] or tabla.columnas
    vistos: set[tuple] = set()
    duplicadas: list[int] = []
    for i in range(tabla.n_filas):
        clave = tuple(c.valores[i] for c in instrumento)
        if clave in vistos:
            duplicadas.append(i)
        vistos.add(clave)

    estado = Estado(tabla, tipos, ajenas, rol_auto, duplicadas, metricas_antes, revision=revision,
                    encabezados_crudos=list(leido.headers), filas_crudas=filas_crudas, si_no=si_no,
                    parecidas=parecidas, aplicado=aplicado)
    todas = list(range(tabla.n_filas))
    propias = [c for c in tabla.columnas if c.id not in ajenas]
    lr, bloques = _linea_recta(estado, propias, todas)
    estado.linea_recta, estado.bloques_linea_recta = sorted(lr), bloques
    estado.incompletos = sorted(_incompletos(propias, todas))
    estado.contradictorias = _contradictorias(propias)
    _sugerir_dimensiones(estado, propias)
    metricas_antes["n_linea_recta"] = len(lr)
    metricas_antes["n_incompletos"] = len(estado.incompletos)
    return estado


# ── Encuestados (filas) ────────────────────────────────────────────────────────


def _est_cfg() -> dict[str, Any]:
    return _cfg().get("estadistica") or {}


def _codigo(info: InfoTipo, valor: str | None, excluir: set[str]) -> float | None:
    """Código numérico de una respuesta Likert (None si falta, se excluye o no es de la escala)."""
    if valor is None or not info.likert:
        return None
    if info.likert.escala == "numerica":
        return numero(valor)
    n = normalizar_texto(valor)
    if n in excluir:
        return None
    codigo = info.likert.codigos.get(n)
    return float(codigo) if codigo is not None else None


def _extremos(info: InfoTipo) -> tuple[float, float]:
    lik = info.likert
    if lik and lik.escala == "numerica":
        return float(lik.etiquetas[0]), float(lik.etiquetas[-1])
    return 1.0, float(lik.puntos if lik else 1)


_TODAS = "Todas las escalas Likert"


def _bloques_likert(estado: Estado, columnas: list) -> list[tuple[str, list]]:  # noqa: ANN001
    """Bloques de ítems Likert: cada cuadrícula «Pregunta [aspecto]» o prefijo numerado
    («Aportación_item1…») y, si hay varias escalas que no forman un solo bloque, el
    conjunto de todas las escalas."""
    likert = [c for c in columnas if estado.tipos[c.id].likert]
    grupos: dict[str, list] = {}
    for c in likert:
        g = grupo_bloque(c.etiqueta)
        if g:
            grupos.setdefault(g[0], []).append(c)
    bloques = [(padre, cols) for padre, cols in grupos.items() if len(cols) >= 2]
    if estado.dimensiones and _sin_dimensiones(bloques, likert):
        # Dimensiones confirmadas por el investigador (sin secciones ni prefijos en el archivo).
        por_id = {c.id: c for c in likert}
        bloques = [(d["nombre"], [por_id[i] for i in d["columnas"] if i in por_id]) for d in estado.dimensiones]
        bloques = [(n, cols) for n, cols in bloques if len(cols) >= 2]
    if len(likert) >= 2 and not (len(bloques) == 1 and len(bloques[0][1]) == len(likert)):
        bloques.append((_TODAS, likert))
    return bloques


def _sin_dimensiones(bloques: list[tuple[str, list]], likert: list) -> bool:  # noqa: ANN001
    """Sin bloques que separen escalas: ninguno, o una sola cuadrícula con todos los ítems."""
    return not bloques or (len(bloques) == 1 and len(bloques[0][1]) == len(likert))


def _sugerir_dimensiones(estado: Estado, columnas: list) -> None:  # noqa: ANN001
    """Propone dimensiones si los ítems Likert no traen bloques por prefijo o cuadrícula."""
    likert = [c for c in columnas if estado.tipos[c.id].likert]
    grupos: dict[str, list] = {}
    for c in likert:
        if g := grupo_bloque(c.etiqueta):
            grupos.setdefault(g[0], []).append(c)
    if not _sin_dimensiones([(k, v) for k, v in grupos.items() if len(v) >= 2], likert) or len(likert) < 6:
        return
    excluir = no_respuestas()
    matriz = [[_codigo(estado.tipos[c.id], c.valores[k], excluir) for c in likert] for k in range(estado.tabla.n_filas)]
    sugerencia = dims.sugerir(matriz)
    estado.info_dimensiones = {"kaiser": sugerencia.kaiser, "horn": sugerencia.horn}
    estado.dimensiones_sugeridas = [
        {"nombre": f"Dimensión {n}", "columnas": [likert[j].id for j in d.indices],
         "etiquetas": [likert[j].etiqueta for j in d.indices], "alfa": round(d.alfa, 4)}
        for n, d in enumerate(sugerencia.dimensiones, start=1)
    ]


def _linea_recta(estado: Estado, columnas: list, filas: list[int]) -> tuple[set[int], list[str]]:  # noqa: ANN001
    """Encuestados que eligieron la MISMA opción en todos los ítems de un bloque Likert
    (respondieron todos y el bloque tiene al menos `linea_recta_min_items` ítems)."""
    minimo = int(_est_cfg().get("linea_recta_min_items", 4))
    excluir = no_respuestas()
    bloques = [(n, cols) for n, cols in _bloques_likert(estado, columnas) if len(cols) >= minimo]
    # Las cuadrículas son el caso clásico; el bloque global solo cuenta si no hay cuadrículas grandes.
    if len(bloques) > 1:
        bloques = [b for b in bloques if b[0] != _TODAS]
    marcadas: set[int] = set()
    usados: list[str] = []
    for nombre, cols in bloques:
        hubo = False
        for i in filas:
            codigos = [_codigo(estado.tipos[c.id], c.valores[i], excluir) for c in cols]
            if all(x is not None for x in codigos) and len(set(codigos)) == 1:
                marcadas.add(i)
                hubo = True
        if hubo:
            usados.append(nombre)
    return marcadas, usados


def _incompletos(columnas: list, filas: list[int]) -> set[int]:  # noqa: ANN001
    """Encuestados que dejaron sin responder más del umbral de las columnas del instrumento."""
    umbral = float(_est_cfg().get("encuestado_incompleto", 0.5))
    if len(columnas) < 2:
        return set()
    return {i for i in filas if sum(1 for c in columnas if c.valores[i] is None) / len(columnas) > umbral}


# ── Estadística descriptiva y fiabilidad ───────────────────────────────────────

_NUMERICOS = ("numerica", "escala_lineal", "calificacion")


def _estadistica(
    estado: Estado,
    columnas: list,  # noqa: ANN001
    valores: dict[str, list[str | None]],
    roles: dict[str, str],
) -> dict[str, Any]:
    """Medidas por columna y fiabilidad por bloque Likert.

    `valores` son las respuestas (antes de codificar las escalas) de las filas que se analizan.
    """
    cfg = _cfg()
    excluir = no_respuestas()
    metodo, _ = metodo_atipicos(cfg)
    k_sigma = float(cfg["umbrales"].get("sigma_fuera_de_rango", 4))
    k_iqr = float(_est_cfg().get("factor_iqr", 1.5))
    minimo_atipicos = int(cfg["umbrales"].get("filas_minimas_sigma", 10))
    separadores = cfg["tipos"].get("separadores_multiple", [",", ";"])
    salida_cols = []
    for c in columnas:
        info = estado.tipos[c.id]
        vals = valores[c.id]
        presentes = [v for v in vals if v is not None]
        n = len(vals)
        fila: dict[str, Any] = {
            "id": c.id,
            "etiqueta": c.etiqueta,
            "tipo": info.tipo,
            "rol": roles.get(c.id),
            "n": len(presentes),
            "n_nulos": n - len(presentes),
            "pct_nulos": round((n - len(presentes)) / n, 4) if n else 0.0,
        }
        if info.likert:
            lik = info.likert
            codigos = [_codigo(info, v, excluir) for v in presentes]
            if lik.escala == "numerica":
                etiqueta_de = {float(e): e for e in lik.etiquetas}
            else:
                etiqueta_de = {float(p): e for p, e in enumerate(lik.etiquetas, start=1)}
            fila["numerico"] = est.descriptivos([x for x in codigos if x is not None])
            fila["frecuencias"] = est.frecuencias(
                [etiqueta_de[x] for x in codigos if x is not None and x in etiqueta_de], orden=lik.etiquetas
            )
            fila["n_excluidos"] = sum(1 for v in presentes if normalizar_texto(v) in excluir)
            fila["escala"] = {"puntos": lik.puntos, "invertido": lik.invertido}
        elif info.tipo in _NUMERICOS:
            xs = [x for x in (numero(v) for v in presentes) if x is not None]
            fila["numerico"] = est.descriptivos(xs)
            if len(xs) >= minimo_atipicos:
                fila["atipicos"] = {
                    "metodo": metodo,
                    "sigma": est.contar_fuera(xs, est.limites_atipicos(xs, "sigma", k_sigma)),
                    "iqr": est.contar_fuera(xs, est.limites_atipicos(xs, "iqr", k_iqr)),
                    "factor_sigma": k_sigma,
                    "factor_iqr": k_iqr,
                }
        elif info.tipo in ("binaria", "categorica"):
            fila["frecuencias"] = est.frecuencias(presentes)
        elif info.tipo == "opcion_multiple_varias":
            patron = "|".join(re.escape(s) for s in separadores)
            opciones = [o.strip() for v in presentes for o in re.split(patron, v) if o.strip()]
            fila["frecuencias"] = est.frecuencias(opciones)
        elif info.tipo in ("texto_corto", "texto_largo"):
            palabras = [len(v.split()) for v in presentes]
            fila["texto"] = {
                "palabras_promedio": round(sum(palabras) / len(palabras), 1) if palabras else 0.0,
                "respuestas_distintas": len({normalizar_texto(v) for v in presentes}),
            }
        salida_cols.append(fila)

    # Fiabilidad: alfa de Cronbach por bloque (los ítems invertidos se recodifican).
    min_casos = int(_est_cfg().get("fiabilidad_min_casos", 3))
    fiabilidad = []
    n_filas = len(next(iter(valores.values()), []))
    for nombre, cols in _bloques_likert(estado, columnas):
        matriz: list[list[float | None]] = []
        for k in range(n_filas):
            fila_codigos = []
            for c in cols:
                info = estado.tipos[c.id]
                x = _codigo(info, valores[c.id][k], excluir)
                if x is not None and info.likert.invertido:
                    lo, hi = _extremos(info)
                    x = lo + hi - x
                fila_codigos.append(x)
            matriz.append(fila_codigos)
        items = [(grupo_bloque(c.etiqueta) or (None, c.etiqueta))[1] for c in cols] if nombre != _TODAS else [c.etiqueta for c in cols]
        resultado = est.cronbach(matriz, items, min_casos) or {
            "n_items": len(cols), "n_casos": 0, "n_excluidos": n_filas, "alfa": None, "interpretacion": None, "por_item": []
        }
        fiabilidad.append(
            {
                "bloque": nombre,
                "items": items,
                "invertidos": [items[j] for j, c in enumerate(cols) if estado.tipos[c.id].likert.invertido],
                **resultado,
            }
        )
    return {"columnas": salida_cols, "fiabilidad": fiabilidad}


# ── Métricas (Tabla 3) ─────────────────────────────────────────────────────────


def _metricas(
    columnas: list[tuple[str, list[str | None]]],
    n_duplicados: int,
    n_imposibles: int,
    grupos: list[dict],
    umbrales: dict[str, Any],
) -> dict[str, Any]:
    n_filas = len(columnas[0][1]) if columnas else 0
    celdas = n_filas * len(columnas)
    nulas = sum(1 for _, vals in columnas for v in vals if v is None)
    pct_nulos = round(nulas / celdas, 4) if celdas else 0.0
    por_columna = sorted(
        ((etq, round(sum(1 for v in vals if v is None) / n_filas, 4) if n_filas else 0.0) for etq, vals in columnas),
        key=lambda x: -x[1],
    )
    metricas = {
        "n_respondentes": n_filas,
        "n_columnas": len(columnas),
        "pct_completitud": round(1 - pct_nulos, 4) if celdas else 0.0,
        "pct_nulos": pct_nulos,
        "n_duplicados": n_duplicados,
        "n_imposibles": n_imposibles,
        "cols_mas_nulos": [{"columna": etq, "pct_nulos": p} for etq, p in por_columna[:5] if p > 0],
        "grupos_detectados": grupos,
    }
    alertas = []
    if metricas["pct_completitud"] < umbrales.get("completitud_minima", 0.6):
        alertas.append("completitud_baja")
    if pct_nulos > umbrales.get("nulos_maximo", 0.4):
        alertas.append("nulos_altos")
    if n_duplicados > 0:
        alertas.append("duplicados")
    if n_imposibles > 0:
        alertas.append("valores_imposibles")
    metricas["alertas"] = alertas
    return metricas


def _metricas_crudas(crudo, cfg: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    """Métricas del archivo tal como llegó (los tokens de vacío cuentan como vacíos)."""
    vacios = {normalizar_texto(t) for t in cfg.get("tokens_vacio", [])}
    columnas = []
    for j, h in enumerate(crudo.headers):
        vals = [None if normalizar_texto(f[j] if j < len(f) else "") in vacios else f[j] for f in crudo.rows]
        columnas.append((h or f"Columna {j + 1}", vals))
    # Duplicados con la misma definición que el hallazgo: sin contar columnas ajenas
    # (una marca temporal distinta no hace distinta una respuesta repetida).
    patrones = cfg.get("columnas_ajenas", [])
    instrumento = [vals for etq, vals in columnas if not _es_ajena(etq, patrones)] or [v for _, v in columnas]
    filas = [tuple(vals[i] for vals in instrumento) for i in range(len(crudo.rows))]
    filas_con_dato = [f for f in filas if any(v is not None for v in f)]
    n_dup = len(filas_con_dato) - len(set(filas_con_dato))
    tipos = {etq: inferir(etq, vals, cfg) for etq, vals in columnas if any(v is not None for v in vals)}
    n_imp = sum(len(t.fuera) for t in tipos.values())
    return _metricas(columnas, n_dup, n_imp, _grupos([(etq, tipos.get(etq)) for etq, _ in columnas]), cfg["umbrales"])


def _grupos(columnas: list[tuple[str, InfoTipo | None]]) -> list[dict]:
    """Grupos padre-hijo («Pregunta [aspecto]») con el tipo más común de sus hijos."""
    grupos: dict[str, dict] = {}
    for etiqueta, info in columnas:
        g = grupo_de(etiqueta)
        if not g:
            continue
        datos = grupos.setdefault(g[0], {"padre": g[0], "hijos": [], "tipos": []})
        datos["hijos"].append(g[1])
        if info:
            datos["tipos"].append(info.tipo)
    salida = []
    for datos in grupos.values():
        if len(datos["hijos"]) < 2:
            continue
        tipos = datos.pop("tipos")
        datos["tipo"] = max(set(tipos), key=tipos.count) if tipos else None
        salida.append(datos)
    return salida


# ── Hallazgos ──────────────────────────────────────────────────────────────────


def _ejemplos(valores: list[str | None]) -> list[str]:
    vistos: list[str] = []
    for v in valores:
        if v is not None and v not in vistos:
            vistos.append(v)
        if len(vistos) >= _EJEMPLOS:
            break
    return vistos


def _no_respuestas_por_columna(estado: Estado) -> dict[str, list[str]]:
    """{id de columna: valores «No sé / No aplica» (tal cual)} en las escalas Likert, de texto o numéricas.

    No son puntos de la escala (no cuentan en promedios ni en la fiabilidad), pero
    tampoco son celdas vacías: el investigador decide si se conservan marcadas. Antes
    solo se buscaban en las escalas de texto: en una escala 1–5, «No sé» quedaba en el
    CSV limpio mezclado con los números y sin aviso (24 oct, errores inyectados).
    """
    excluir = no_respuestas()
    salida: dict[str, list[str]] = {}
    for c in estado.tabla.columnas:
        info = estado.tipos[c.id]
        if c.id in estado.ajenas or not info.likert:
            continue
        valores = [v for v in c.valores if v is not None and normalizar_texto(v) in excluir]
        if valores:
            salida[c.id] = valores
    return salida


def _contradictorias(columnas: list) -> dict[str, list[int]]:
    """{columna: filas} donde una selección múltiple marca «Ninguno» (u otra opción excluyente) junto con otras."""
    salida: dict[str, list[int]] = {}
    for c in columnas:
        presentes = [v for v in c.valores if v is not None]
        if not presentes or sum(_SEPARADOR_OPCIONES in v for v in presentes) < max(2, 0.05 * len(presentes)):
            continue
        filas = [i for i, v in enumerate(c.valores) if v is not None and _SEPARADOR_OPCIONES in v
                 and any(normalizar_texto(p) in _EXCLUYENTES for p in v.split(_SEPARADOR_OPCIONES))]
        if filas:
            salida[c.id] = filas
    return salida


def _celdas(c, filas: list[int]) -> list[dict]:  # noqa: ANN001
    """Ubicación exacta de un hallazgo por celda: fila (desde 1) y valor."""
    return [{"fila": i + 1, "columna": c.etiqueta, "valor": c.valores[i]} for i in filas[: universales.MAX_CASOS]]


def _filas_con_respuestas(estado: "Estado", filas: list[int], columnas: list | None = None, max_columnas: int = 8) -> list[dict]:
    """Ubicación de un hallazgo por fila: fila (desde 1) y sus respuestas en las columnas que importan."""
    cols = columnas or [c for c in estado.tabla.columnas if c.id not in estado.ajenas][:max_columnas]
    return [{"fila": i + 1, "valores": {c.etiqueta: c.valores[i] for c in cols}} for i in filas[: universales.MAX_CASOS]]


# Valores distintos fuera de la escala con tarjeta propia por columna; el resto va en una tarjeta de la columna.
_MAX_VALORES_FUERA = 8


def _aceptados(info: InfoTipo) -> list[str]:
    """Valores de la escala a los que se puede cambiar un valor fuera de rango ([] si no hay un conjunto cerrado)."""
    if info.likert:
        return list(info.likert.etiquetas)
    if info.tipo in ("escala_lineal", "calificacion") and info.rango and info.rango[1] - info.rango[0] <= 10:
        return [str(x) for x in range(int(info.rango[0]), int(info.rango[1]) + 1)]
    return []


def _grupos_fuera(c, info: InfoTipo) -> list[tuple[str, str, list[int]]]:  # noqa: ANN001
    """Valores fuera de rango agrupados por valor: [(clave, valor tal cual, filas)].

    En las escalas cada valor distinto tiene su tarjeta, con su motivo y la opción de cambiarlo a un valor de la
    escala (28 oct). Las numéricas (atípicos) y lo que pasa de `_MAX_VALORES_FUERA` valores distintos quedan en
    una tarjeta de la columna (clave "").
    """
    if not info.fuera:
        return []
    if not _aceptados(info):
        return [("", "", sorted(info.fuera))]
    por_valor: dict[str, tuple[str, list[int]]] = {}
    for i in sorted(info.fuera):
        v = c.valores[i]
        if v is not None:
            por_valor.setdefault(normalizar_texto(v) or v, (v, []))[1].append(i)
    orden = sorted(por_valor.items(), key=lambda kv: (-len(kv[1][1]), kv[0]))
    grupos = [(k, v, filas) for k, (v, filas) in orden[:_MAX_VALORES_FUERA]]
    resto = sorted(i for _, (_, filas) in orden[_MAX_VALORES_FUERA:] for i in filas)
    if resto:
        grupos.append(("", "", resto))
    return grupos


def _id_rango(c, clave: str) -> str:  # noqa: ANN001
    return f"rango:{c.id}={clave}" if clave else f"rango:{c.id}"


def _por_que_fuera(info: InfoTipo, valor: str) -> tuple[str, str]:
    """(por qué `valor` está fuera de la escala, opción sugerida: «anular» o «cambiar:<valor aceptado>»)."""
    aceptados = _aceptados(info)
    numerica = not info.likert or info.likert.escala == "numerica"
    x = numero(valor)
    if numerica:
        lo, hi = aceptados[0], aceptados[-1]
        if x is None:
            texto = f"«{valor}» está escrito con palabras, pero esta pregunta se respondió con números del {lo} al {hi}."
            eq = equivalente(valor, len(aceptados))
            if eq:
                pos, nombre, etiquetas = eq
                destino = aceptados[pos - 1]
                return (texto + f" En la escala de {nombre} («{etiquetas[0]}» … «{etiquetas[-1]}») es la opción {pos} "
                        f"de {len(etiquetas)}, que equivale a {destino}: te sugerimos cambiarlo a {destino}.",
                        f"cambiar:{destino}")
            return texto + " No corresponde a ningún punto de la escala: te sugerimos dejarlo vacío.", "anular"
        if x > float(hi):
            return (f"«{valor}» es mayor que {hi}, el valor más alto de la escala (del {lo} al {hi}). "
                    "Te sugerimos dejarlo vacío.", "anular")
        if x < float(lo):
            return (f"«{valor}» es menor que {lo}, el valor más bajo de la escala (del {lo} al {hi}). "
                    "Te sugerimos dejarlo vacío.", "anular")
        return (f"«{valor}» no es uno de los valores de la escala: solo se aceptan los enteros del {lo} al {hi}. "
                "Te sugerimos dejarlo vacío.", "anular")
    opciones = ", ".join(f"«{e}»" for e in aceptados)
    if x is not None and float(x).is_integer() and 1 <= x <= len(aceptados):
        destino = aceptados[int(x) - 1]
        return (f"«{valor}» es un número, pero esta pregunta se respondió con las opciones de la escala ({opciones}). "
                f"Como posición {int(x)} corresponde a «{destino}»: te sugerimos cambiarlo, si así lo quiso decir el "
                "encuestado.", f"cambiar:{destino}")
    return f"«{valor}» no es ninguna de las opciones de la escala: {opciones}. Te sugerimos dejarlo vacío.", "anular"


def _decision_fuera(c, info: InfoTipo, decisiones: dict[str, str]) -> dict[int, str]:  # noqa: ANN001
    """{fila: decisión} para cada valor fuera de rango (la del investigador o la sugerida)."""
    salida: dict[int, str] = {}
    for clave, valor, filas in _grupos_fuera(c, info):
        sugerida = _por_que_fuera(info, valor)[1] if clave else "anular"
        decision = decisiones.get(_id_rango(c, clave)) or sugerida
        salida.update({i: decision for i in filas})
    return salida


def _fila_con_valores(estado: Estado, celdas: list[str], fila: int, maximo: int = 10) -> dict:
    """Una fila del archivo con sus primeras celdas con dato (para «Ver dónde»)."""
    valores: dict[str, str] = {}
    for j, h in enumerate(estado.encabezados_crudos):
        if j < len(celdas) and celdas[j].strip():
            valores[h or f"Columna {j + 1}"] = celdas[j]
        if len(valores) >= maximo:
            break
    return {"fila": fila, "valores": valores}


def _hallazgos_estructura(estado: Estado) -> list[Hallazgo]:
    """Fila de totales, segunda fila de encabezado, filas corridas o con celdas de más."""
    rev = estado.revision
    encabezados = estado.encabezados_crudos

    def nombre(j: int) -> str:
        return (encabezados[j] if j < len(encabezados) else "") or f"Columna {j + 1}"

    tema = "Estructura del archivo"
    salida: list[Hallazgo] = []
    for i in rev.resumen:
        celdas = estado.filas_crudas[i]
        etiqueta = next(c for c in celdas if c.strip())
        salida.append(Hallazgo(
            id=f"fila-resumen:{i + 1}", tipo="fila_resumen", tema=tema, objetivo=str(i + 1),
            titulo=f"La fila {i + 1} parece de totales («{etiqueta}»), no de un encuestado",
            descripcion=(
                f"Trae «{etiqueta}» en la primera celda y números en las demás. Si se queda, cuenta como un encuestado "
                "más y sus decimales pueden cambiar el tipo de las preguntas (una escala de 1 a 5 parecería una "
                "calificación de 0 a 10). Te sugerimos eliminarla."
            ),
            opciones=["eliminar", "conservar"], sugerida="eliminar",
            detalle={"filas": [i + 1], "total": 1, "ubicacion": [_fila_con_valores(estado, celdas, i + 1)]},
        ))
    if rev.segunda_encabezado:
        primera = estado.filas_crudas[0]
        pares = [(nombre(j), t.strip()) for j, t in enumerate(primera) if t.strip()]
        salida.append(Hallazgo(
            id="encabezado-texto", tipo="segunda_fila_encabezado", tema=tema, objetivo="1",
            titulo="La primera fila trae el texto de las preguntas, no respuestas",
            descripcion=(
                "En las columnas que se respondieron con números trae texto (por ejemplo, "
                + "; ".join(f"«{t}» en «{h}»" for h, t in pares[2:4]) + "). Te sugerimos quitarla de los encuestados y "
                "guardar ese texto como descripción de cada columna; los encabezados del archivo no cambian."
            ),
            opciones=["usar_como_texto", "es_respondente"], sugerida="usar_como_texto",
            detalle={"ejemplos": [f"{h} → {t}" for h, t in pares[:4]], "total": 1,
                     "ubicacion": [_fila_con_valores(estado, primera, 1)]},
        ))
    for fc in rev.corridas:
        n, k = fc.fila + 1, fc.columna
        h = nombre(k)
        if fc.tipo == "falta":
            titulo = f"La fila {n} está corrida una columna: falta el dato de «{h}»"
            explicacion = (
                f"Desde «{h}», cada valor quedó una columna a la izquierda (por ejemplo, «{fc.celdas[k]}» quedó en «{h}» "
                f"y corresponde a «{nombre(k + 1)}»). Si la reparas, «{h}» queda vacía y los demás valores vuelven a su columna."
            )
        else:
            titulo = f"La fila {n} está corrida una columna: sobra una celda en «{h}»"
            explicacion = (
                f"Hay una celda de más en «{h}» («{fc.celdas[k]}»): desde ahí, cada valor quedó una columna a la derecha. "
                "Si la reparas, se quita esa celda y los demás valores vuelven a su columna."
            )
        ubicacion = [{"fila": n, "columna": nombre(j), "antes": fc.celdas[j] if j < len(fc.celdas) else "", "despues": fc.reparada[j]}
                     for j in range(max(0, k - 1), min(len(encabezados), k + 6))]
        salida.append(Hallazgo(
            id=f"fila-corrida:{n}", tipo="fila_corrida", tema=tema, objetivo=str(n), titulo=titulo,
            descripcion=(f"{explicacion} Tal como viene, {fc.fallas_antes} valores no corresponden a su columna; reparada, "
                         f"{fc.fallas_despues}. Así todas las filas quedan con las mismas columnas."),
            opciones=["reparar", "eliminar", "conservar"], sugerida="reparar",
            detalle={"filas": [n], "total": len(ubicacion), "ubicacion": ubicacion},
        ))
    for i, celdas in rev.largas:
        extra = [c for c in celdas[len(encabezados):] if c.strip()]
        salida.append(Hallazgo(
            id=f"fila-larga:{i + 1}", tipo="fila_larga", tema=tema, objetivo=str(i + 1),
            titulo=f"La fila {i + 1} tiene {len(celdas) - len(encabezados)} celda(s) más que el encabezado",
            descripcion=(
                f"No encontramos en qué columna sobra. Si la recortas, se conservan sus primeras {len(encabezados)} "
                f"celdas y se pierden las de más («{' · '.join(extra[:3])}»); también puedes eliminar la fila."
            ),
            opciones=["recortar", "eliminar"], sugerida="recortar",
            detalle={"filas": [i + 1], "total": 1, "ubicacion": [_fila_con_valores(estado, celdas, i + 1)]},
        ))
    return salida


def _hallazgos_categorias(estado: Estado) -> list[Hallazgo]:
    """«1» / «0» en columnas de Sí / No y opciones poco frecuentes parecidas a otra."""
    salida: list[Hallazgo] = []
    for p in estado.si_no:
        salida.append(Hallazgo(
            id=f"si-no-codigos:{p.columna}", tipo="si_no_codigos", tema="Calidad de los datos", objetivo=p.columna,
            titulo=f"«{p.etiqueta}» mezcla «{p.forma_si}» / «{p.forma_no}» con «1» y «0» ({len(p.filas)} respuestas)",
            descripcion=(
                f"Hay {p.unos} «1» y {p.ceros} «0». Lo más común es que 1 signifique «{p.forma_si}» y 0 «{p.forma_no}», "
                "pero depende de cómo se capturó. Elige qué significa cada uno, déjalos vacíos o consérvalos tal cual."
            ),
            opciones=["uno_es_si", "uno_es_no", "anular", "conservar"], sugerida="uno_es_si",
            detalle={"columna": p.etiqueta, "total": len(p.filas),
                     "ubicacion": [{"fila": i + 1, "columna": p.etiqueta, "valor": v} for i, v in zip(p.filas, p.originales)]},
        ))
    for p in estado.parecidas:
        veces = "1 vez" if len(p.filas) == 1 else f"{len(p.filas)} veces"
        salida.append(Hallazgo(
            id=_id_parecida(p), tipo="opcion_parecida", tema="Calidad de los datos", objetivo=p.columna,
            titulo=f"«{p.valor}» se parece a «{p.destino}» en «{p.etiqueta}»",
            descripcion=(
                f"«{p.valor}» aparece {veces} y «{p.destino}», {p.veces_destino}; se parecen en un {round(p.similitud * 100)} %. "
                f"Puede ser un error de escritura: te sugerimos cambiarlo por «{p.destino}». Si es otra opción, consérvalo."
            ),
            opciones=[f"cambiar:{p.destino}", "conservar"], sugerida=f"cambiar:{p.destino}",
            detalle={"columna": p.etiqueta, "valores": [p.valor], "filas": [i + 1 for i in p.filas], "total": len(p.filas),
                     "ubicacion": [{"fila": i + 1, "columna": p.etiqueta, "valor": p.valor} for i in p.filas]},
        ))
    return salida


def _hallazgos(estado: Estado) -> list[Hallazgo]:
    cfg = _cfg()
    umbrales = cfg["umbrales"]
    patron_codigo = re.compile(cfg.get("patron_codigo_corto", r"^[A-Za-z]{1,3}\d+([_.]\d+)*$"))
    invertidas = [normalizar_texto(p).strip() for p in cfg["tipos"].get("palabras_invertido", [])]
    n = estado.tabla.n_filas
    salida: list[Hallazgo] = [*_hallazgos_estructura(estado), *_hallazgos_categorias(estado)]

    for c in estado.tabla.columnas:
        info = estado.tipos[c.id]
        ejemplos = _ejemplos(c.valores)
        pct_nulos = round(sum(1 for v in c.valores if v is None) / n, 4) if n else 0.0
        base = {"columna": c.etiqueta, "ejemplos": ejemplos, "tipo": info.tipo, "pct_nulos": pct_nulos}

        # Columnas que no pertenecen al instrumento (preseleccionadas para eliminar).
        if c.id in estado.ajenas:
            salida.append(
                Hallazgo(
                    id=f"col-ajena:{c.id}", tipo="columna_ajena", tema="Columnas que no son del instrumento",
                    objetivo=c.id, titulo=f"«{c.etiqueta}» no parece parte del instrumento",
                    descripcion="Parece un dato de la plataforma (identificador, fecha u hora, sesión). Te sugerimos eliminarla.",
                    opciones=["eliminar", "conservar"], sugerida="eliminar", detalle=base,
                )
            )
            continue

        # Roles: > 25 caracteres ya es pregunta; códigos cortos los decide el investigador.
        if c.id not in estado.rol_auto:
            es_codigo = bool(patron_codigo.match(c.etiqueta.strip()))
            sugerida = None if es_codigo else ("contexto" if configuracion.es_contexto(c.etiqueta) else "pregunta")
            salida.append(
                Hallazgo(
                    id=f"rol:{c.id}", tipo="rol_columna", tema="Rol de las columnas", objetivo=c.id,
                    titulo=f"¿Qué es «{c.etiqueta}»?",
                    descripcion=(
                        "Es un código corto: revisa sus valores y elige si es una pregunta del instrumento, "
                        "un dato de contexto o una columna a eliminar."
                        if es_codigo
                        else "El encabezado es corto; confirma si es una pregunta del instrumento o un dato de contexto."
                    ),
                    opciones=["pregunta", "contexto", "eliminar"], sugerida=sugerida, obligatoria=es_codigo, detalle=base,
                )
            )

        # Columnas muy incompletas (umbrales de la Tabla 3).
        if pct_nulos > umbrales.get("nulos_maximo", 0.4) or (1 - pct_nulos) < umbrales.get("completitud_minima", 0.6):
            sugerir_eliminar = pct_nulos >= umbrales.get("nulos_sugerir_eliminar", 0.9)
            salida.append(
                Hallazgo(
                    id=f"incompleta:{c.id}", tipo="columna_incompleta", tema="Calidad de los datos", objetivo=c.id,
                    titulo=f"«{c.etiqueta}» está vacía en el {round(pct_nulos * 100)} % de las respuestas",
                    descripcion="Supera el umbral de vacíos (40 %). Puedes conservarla o eliminarla.",
                    opciones=["conservar", "eliminar"], sugerida="eliminar" if sugerir_eliminar else "conservar", detalle=base,
                )
            )

        # Valores fuera de la escala: una tarjeta por valor, con su motivo y la opción de cambiarlo (28 oct).
        for clave, valor, filas_valor in _grupos_fuera(c, info):
            if not clave:
                continue
            motivo, sugerida = _por_que_fuera(info, valor)
            aceptados = _aceptados(info)
            veces = "1 vez" if len(filas_valor) == 1 else f"{len(filas_valor)} veces"
            salida.append(
                Hallazgo(
                    id=_id_rango(c, clave), tipo="fuera_de_rango", tema="Calidad de los datos", objetivo=c.id,
                    titulo=f"«{valor}» está fuera de la escala en «{c.etiqueta}» ({veces})",
                    descripcion=motivo + " También puedes conservarlo tal cual o cambiarlo por otro valor de la escala.",
                    opciones=["anular", "conservar", *(f"cambiar:{a}" for a in aceptados)], sugerida=sugerida,
                    detalle={**base, "valores": [valor], "filas": [i + 1 for i in filas_valor[:20]],
                             "total": len(filas_valor), "rango": info.rango, "aceptados": aceptados, "motivo": motivo,
                             "ubicacion": _celdas(c, filas_valor)},
                )
            )
        # Atípicos de una numérica (o demasiados valores distintos en una escala): una tarjeta para la columna.
        resto = next((filas_valor for clave, _, filas_valor in _grupos_fuera(c, info) if not clave), None)
        if resto:
            filas = resto
            valores = _ejemplos([c.valores[i] for i in filas])
            rango = (
                f"entre {_fmt(info.rango[0])} y {_fmt(info.rango[1])}" if info.rango else "dentro de la escala"
            )
            if info.tipo != "numerica":
                explicacion = f"La escala va {rango}; estos valores no pertenecen a ella."
            elif info.metodo_atipicos == "iqr":
                explicacion = f"Son atípicos según el rango intercuartílico (fuera de {rango})."
            else:
                k = _fmt(float(umbrales.get("sigma_fuera_de_rango", 4)))
                explicacion = f"Están a más de {k} desviaciones estándar del promedio (fuera de {rango})."
            salida.append(
                Hallazgo(
                    id=f"rango:{c.id}", tipo="fuera_de_rango", tema="Calidad de los datos", objetivo=c.id,
                    titulo=f"{len(filas)} valor(es) fuera de rango en «{c.etiqueta}»",
                    descripcion=explicacion + " Te sugerimos dejarlos vacíos.",
                    opciones=["anular", "conservar"], sugerida="anular",
                    detalle={**base, "valores": valores, "filas": [i + 1 for i in filas[:20]], "total": len(filas),
                             "rango": info.rango, "ubicacion": _celdas(c, filas)},
                )
            )

        # Escalas que parecen Likert pero no están en el diccionario.
        if info.dudosa and not info.likert:
            seguro = info.dudosa["cobertura"] >= 0.5
            salida.append(
                Hallazgo(
                    id=f"likert-orden:{c.id}", tipo="likert_orden", tema="Escalas", objetivo=c.id,
                    titulo=f"«{c.etiqueta}» parece una escala",
                    descripcion="No está en el diccionario de escalas. Confirma el orden de sus opciones (de menor a mayor) o indica que no es una escala.",
                    opciones=["usar_orden_propuesto", "invertir_orden", "no_es_likert"],
                    sugerida="usar_orden_propuesto" if seguro else None, obligatoria=not seguro,
                    detalle={**base, "orden_propuesto": info.dudosa["orden_propuesto"]},
                )
            )

        # Ítems Likert invertidos (la pregunta está redactada en negativo).
        if info.likert and info.tipo in ("likert", "cuadricula"):
            # Solo palabras: «[nunca …]» o «¿No …?» también cuentan.
            etq = f" {re.sub(r'[^\w]+', ' ', normalizar_texto(c.etiqueta))} "
            if any(f" {p} " in etq for p in invertidas):
                salida.append(
                    Hallazgo(
                        id=f"invertido:{c.id}", tipo="item_invertido", tema="Escalas", objetivo=c.id,
                        titulo=f"«{c.etiqueta}» podría ser un ítem invertido",
                        descripcion="Está redactado en negativo: un valor alto podría significar lo contrario que en las demás preguntas. Se marca en los metadatos; los datos no se modifican.",
                        opciones=["invertido", "no_invertido"], sugerida="invertido",
                        detalle={**base, "etiquetas": info.likert.etiquetas},
                    )
                )

    no_resp = _no_respuestas_por_columna(estado)
    if no_resp:
        total = sum(len(v) for v in no_resp.values())
        etiquetas = {c.id: c.etiqueta for c in estado.tabla.columnas}
        distintos = sorted({v for vals in no_resp.values() for v in vals})
        salida.append(
            Hallazgo(
                id="no-respuestas", tipo="no_respuestas", tema="Calidad de las respuestas", objetivo="celdas",
                titulo=f"{total} respuesta(s) «{' / '.join(distintos[:3])}» en {len(no_resp)} escala(s)",
                descripcion=(
                    "No son puntos de la escala: no cuentan en promedios ni en la fiabilidad. Te sugerimos "
                    "conservarlas marcadas para distinguirlas de las preguntas que se dejaron en blanco; "
                    "si prefieres, pueden quedar como celdas vacías."
                ),
                opciones=["conservar_marcadas", "vaciar"], sugerida="conservar_marcadas",
                detalle={
                    "ejemplos": distintos[:6],
                    "total": total,
                    "columnas": [{"columna": etiquetas[cid], "n": len(v)} for cid, v in no_resp.items()][:20],
                    "ubicacion": [
                        {"fila": i + 1, "columna": etiquetas[c.id], "valor": c.valores[i]}
                        for c in estado.tabla.columnas if c.id in no_resp
                        for i, v in enumerate(c.valores) if v is not None and normalizar_texto(v) in no_respuestas()
                    ][: universales.MAX_CASOS],
                },
            )
        )
    if estado.duplicadas:
        salida.append(
            Hallazgo(
                id="duplicados", tipo="duplicados", tema="Calidad de los datos", objetivo="filas",
                titulo=f"{len(estado.duplicadas)} fila(s) duplicada(s)",
                descripcion="Tienen exactamente las mismas respuestas que otra fila (sin contar identificadores ni marcas de tiempo). Te sugerimos eliminarlas y conservar la primera.",
                opciones=["eliminar", "conservar"], sugerida="eliminar",
                detalle={"filas": [i + 1 for i in estado.duplicadas[:20]], "total": len(estado.duplicadas),
                         "ubicacion": _filas_con_respuestas(estado, estado.duplicadas)},
            )
        )
    if estado.linea_recta:
        bloques = ", ".join(f"«{b}»" for b in estado.bloques_linea_recta)
        salida.append(
            Hallazgo(
                id="linea-recta", tipo="linea_recta", tema="Calidad de las respuestas", objetivo="filas",
                titulo=f"{len(estado.linea_recta)} encuestado(s) respondieron en línea recta",
                descripcion=(
                    f"Eligieron la misma opción en todos los ítems de {bloques}. Puede indicar que respondieron "
                    "sin leer, aunque también puede ser una opinión genuina. Te sugerimos conservarlos y tenerlo en cuenta en el análisis."
                ),
                opciones=["conservar", "eliminar"], sugerida="conservar",
                detalle={"filas": [i + 1 for i in estado.linea_recta[:20]], "total": len(estado.linea_recta), "bloques": estado.bloques_linea_recta,
                         "ubicacion": _filas_con_respuestas(estado, estado.linea_recta, max_columnas=12)},
            )
        )
    if estado.incompletos:
        umbral = float(_est_cfg().get("encuestado_incompleto", 0.5))
        salida.append(
            Hallazgo(
                id="incompletos", tipo="encuestados_incompletos", tema="Calidad de las respuestas", objetivo="filas",
                titulo=f"{len(estado.incompletos)} encuestado(s) dejaron sin responder más del {round(umbral * 100)} %",
                descripcion="Sus respuestas aportan poca información y pueden sesgar los resultados. Te sugerimos eliminarlos.",
                opciones=["eliminar", "conservar"], sugerida="eliminar",
                detalle={"filas": [i + 1 for i in estado.incompletos[:20]], "total": len(estado.incompletos), "umbral": umbral,
                         "ubicacion": _filas_con_respuestas(estado, estado.incompletos)},
            )
        )
    if estado.contradictorias:
        columnas = {c.id: c for c in estado.tabla.columnas}
        total = sum(len(f) for f in estado.contradictorias.values())
        salida.append(
            Hallazgo(
                id="seleccion-contradictoria", tipo="seleccion_contradictoria", tema="Calidad de las respuestas", objetivo="celdas",
                titulo=f"{total} respuesta(s) marcan «Ninguno» junto con otras opciones",
                descripcion=(
                    "En una pregunta de selección múltiple, «Ninguno» excluye a las demás opciones, así que esas "
                    "respuestas se contradicen. Puedes conservarlas como vienen, quitar «Ninguno» y dejar las otras "
                    "opciones, o dejarlas vacías."
                ),
                opciones=["conservar", "quitar_ninguno", "vaciar"], sugerida="conservar",
                detalle={
                    "total": total,
                    "columnas": [{"columna": columnas[cid].etiqueta, "n": len(f)} for cid, f in estado.contradictorias.items()],
                    "ubicacion": [u for cid, f in estado.contradictorias.items() for u in _celdas(columnas[cid], f)][: universales.MAX_CASOS],
                },
            )
        )
    if estado.dimensiones_sugeridas:
        n_items = sum(len(d["columnas"]) for d in estado.dimensiones_sugeridas)
        salida.append(
            Hallazgo(
                id="dimensiones", tipo="dimensiones_sugeridas", tema="Escalas", objetivo="items",
                titulo=f"{len(estado.dimensiones_sugeridas)} dimensiones sugeridas en {n_items} ítems de escala",
                descripcion=(
                    "El instrumento no tiene secciones ni prefijos que agrupen los ítems. Por cómo se responden "
                    "(correlaciones entre ítems), estos grupos parecen medir lo mismo. Si los usas, el alfa de "
                    "Cronbach se calcula por dimensión en vez de mezclar todas las escalas. Revisa que cada grupo "
                    "tenga sentido con el contenido de las preguntas."
                ),
                opciones=["usar", "ignorar"], sugerida="usar",
                detalle={"grupos": estado.dimensiones_sugeridas, **estado.info_dimensiones},
            )
        )
    return salida


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _especifico(estado: Estado, roles: dict[str, str], eliminadas: dict[str, str]) -> dict[str, Any]:
    columnas = []
    n = estado.tabla.n_filas
    for c in estado.tabla.columnas:
        info = estado.tipos[c.id]
        columnas.append(
            {
                "id": c.id,
                "etiqueta": c.etiqueta,
                "rol": roles.get(c.id),
                "tipo_canonico": info.tipo,
                "pct_nulos": round(sum(1 for v in c.valores if v is None) / n, 4) if n else 0.0,
                "likert": info.likert.a_reporte() if info.likert else None,
                "rango": list(info.rango) if info.rango else None,
                "estadisticos": info.estadisticos or None,
                "estado": "eliminada" if c.id in eliminadas else "conservada",
                "motivo_eliminacion": eliminadas.get(c.id),
                **({"texto": c.extra["texto"]} if c.extra.get("texto") else {}),
            }
        )
    return {
        "columnas": columnas,
        "grupos_detectados": _grupos([(c.etiqueta, estado.tipos[c.id]) for c in estado.tabla.columnas]),
        "dimensiones": [{k: d[k] for k in ("nombre", "columnas", "etiquetas")} for d in estado.dimensiones],
        "columnas_vacias_eliminadas": estado.tabla.columnas_vacias,
        "filas_eliminadas": {"vacias": estado.tabla.filas_vacias, "duplicadas": 0},
        "estructura": {
            "encabezados_repetidos": [i + 1 for i in estado.revision.repetidas],
            "filas_resumen": [i + 1 for i in estado.revision.resumen],
            "segunda_fila_encabezado": estado.revision.segunda_encabezado,
            "filas_corridas": [{"fila": fc.fila + 1, "tipo": fc.tipo, "columna": estado.encabezados_crudos[fc.columna]}
                               for fc in estado.revision.corridas],
            "filas_largas": [i + 1 for i, _ in estado.revision.largas],
            "filas_cortas": [i + 1 for i in estado.revision.cortas],
        },
    }


# ── Motor ──────────────────────────────────────────────────────────────────────


class MotorEncuestas:
    """Limpieza de encuestas tabulares."""

    nombre = "encuestas"

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico:
        estado = _preparar(entrada)
        hallazgos = _hallazgos(estado)
        transformaciones = list(estado.tabla.transformaciones)
        if estado.rol_auto:
            transformaciones.append(
                {
                    "regla": "roles_automaticos",
                    "detalle": "Columnas con encabezado largo (más de 25 caracteres) clasificadas como pregunta.",
                    "afectados": len(estado.rol_auto),
                }
            )
        roles = dict(estado.rol_auto)
        propias = [c for c in estado.tabla.columnas if c.id not in estado.ajenas]
        estadistica = _estadistica(estado, propias, {c.id: c.valores for c in propias}, roles)
        estadistica["encuestados"] = {"linea_recta": len(estado.linea_recta), "incompletos": len(estado.incompletos)}
        avisos = []
        if any(h.obligatoria for h in hallazgos):
            avisos.append("Hay columnas con códigos cortos: revisa su rol antes de continuar.")
        return ResultadoAutomatico(
            hallazgos=hallazgos,
            transformaciones=transformaciones,
            metricas=estado.metricas_antes,
            especifico=_especifico(estado, roles, {}),
            avisos=avisos,
            estadistica=estadistica,
        )

    def aplicar(self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]) -> ResultadoFinal:
        estado = _preparar(entrada, decisiones)
        if decisiones.get("dimensiones", "usar") == "usar":
            estado.dimensiones = estado.dimensiones_sugeridas
        cfg = _cfg()
        excluir = no_respuestas()

        roles: dict[str, str] = dict(estado.rol_auto)
        eliminadas: dict[str, str] = {}
        for c in estado.tabla.columnas:
            if c.id in estado.ajenas:
                if decisiones.get(f"col-ajena:{c.id}", "eliminar") == "eliminar":
                    eliminadas[c.id] = "no pertenece al instrumento"
                else:
                    roles[c.id] = "contexto"
                continue
            rol = decisiones.get(f"rol:{c.id}") or roles.get(c.id) or "pregunta"
            if rol == "eliminar":
                eliminadas[c.id] = "decisión del investigador"
                continue
            roles[c.id] = rol
            if decisiones.get(f"incompleta:{c.id}") == "eliminar":
                eliminadas[c.id] = "demasiados valores vacíos"

        # Escalas: orden confirmado e ítems invertidos (solo metadatos; los datos no se recodifican).
        for c in estado.tabla.columnas:
            info = estado.tipos[c.id]
            decision = decisiones.get(f"likert-orden:{c.id}")
            if info.dudosa and not info.likert and decision in ("usar_orden_propuesto", "invertir_orden"):
                orden = list(info.dudosa["orden_propuesto"])
                if decision == "invertir_orden":
                    orden.reverse()
                info.likert = likert_desde_orden(orden, info.dudosa.get("excluidos", []), c.valores)
                info.tipo = "likert"
                info.rango = (1.0, float(len(orden)))
                info.fuera = set(info.likert.fuera)
            if info.likert and decisiones.get(f"invertido:{c.id}") == "invertido":
                info.likert.invertido = True

        # Filas: duplicadas (se conserva la primera aparición).
        quitar_dup = set(estado.duplicadas) if decisiones.get("duplicados", "eliminar") == "eliminar" else set()
        quitar_lr = set(estado.linea_recta) if decisiones.get("linea-recta", "conservar") == "eliminar" else set()
        quitar_inc = set(estado.incompletos) if decisiones.get("incompletos", "eliminar") == "eliminar" else set()
        quitar_filas = quitar_dup | quitar_lr | quitar_inc
        filas_idx = [i for i in range(estado.tabla.n_filas) if i not in quitar_filas]

        conservadas = [c for c in estado.tabla.columnas if c.id not in eliminadas]
        if not conservadas:
            raise ErrorLimpieza("Con las decisiones tomadas no queda ninguna columna. Conserva al menos una.")

        anulados = 0
        casos_anulados: list[dict] = []
        casos_cambiados: list[dict] = []
        convertidos = 0
        contradictorias_cambiadas = 0
        # «No sé / No aplica»: conservarlas marcadas (texto original) o dejarlas vacías.
        marcar_no_resp = decisiones.get("no-respuestas", "conservar_marcadas") == "conservar_marcadas"
        no_resp_conservadas = 0
        no_resp_vaciadas = 0
        columnas_finales: list[tuple[str, list[str | None]]] = []
        sin_codificar: dict[str, list[str | None]] = {}  # para la estadística (etiquetas originales)
        for c in conservadas:
            info = estado.tipos[c.id]
            decision_fuera = _decision_fuera(c, info, decisiones)
            codigo_etiqueta = (
                {normalizar_texto(e): p for p, e in enumerate(info.likert.etiquetas, start=1)} if info.likert else {}
            )
            contradictorias = set(estado.contradictorias.get(c.id, []))
            decision_contra = decisiones.get("seleccion-contradictoria", "conservar")
            valores: list[str | None] = []
            originales: list[str | None] = []
            for i in filas_idx:
                v = c.valores[i]
                if v is not None and i in contradictorias and decision_contra != "conservar":
                    if decision_contra == "vaciar":
                        v = None
                    else:
                        v = _SEPARADOR_OPCIONES.join(p for p in v.split(_SEPARADOR_OPCIONES) if normalizar_texto(p) not in _EXCLUYENTES) or None
                    contradictorias_cambiadas += 1
                if v is not None and i in decision_fuera:
                    decision = decision_fuera[i]
                    if decision == "anular":
                        casos_anulados.append({"fila": i + 1, "columna": c.etiqueta, "antes": v, "despues": ""})
                        v = None
                        anulados += 1
                    elif decision.startswith("cambiar:"):
                        nuevo = decision.split(":", 1)[1]
                        casos_cambiados.append({"fila": i + 1, "columna": c.etiqueta, "antes": v, "despues": nuevo})
                        v = nuevo
                originales.append(v)
                if v is not None and info.likert:
                    n = normalizar_texto(v)
                    if n in excluir:
                        # No es punto de la escala: queda marcada con su texto original
                        # (distinta de una celda vacía) o vacía, según decidió el investigador.
                        if marcar_no_resp:
                            no_resp_conservadas += 1
                        else:
                            v = None
                            no_resp_vaciadas += 1
                    elif info.likert.escala != "numerica" and (n in info.likert.codigos or n in codigo_etiqueta):
                        v = str(info.likert.codigos.get(n) or codigo_etiqueta[n])
                        convertidos += 1
                valores.append(v)
            columnas_finales.append((c.id, valores))
            sin_codificar[c.id] = originales

        transformaciones = list(estado.aplicado)
        if eliminadas:
            transformaciones.append(
                {"regla": "columnas_eliminadas", "detalle": ", ".join(c.etiqueta for c in estado.tabla.columnas if c.id in eliminadas), "afectados": len(eliminadas)}
            )
        if quitar_dup:
            transformaciones.append({"regla": "duplicados_eliminados", "detalle": "Filas duplicadas eliminadas (se conservó la primera).", "afectados": len(quitar_dup)})
        if quitar_lr:
            transformaciones.append({"regla": "linea_recta_eliminados", "detalle": "Encuestados que respondieron en línea recta eliminados.", "afectados": len(quitar_lr)})
        if quitar_inc:
            transformaciones.append({"regla": "incompletos_eliminados", "detalle": "Encuestados con demasiadas preguntas sin responder eliminados.", "afectados": len(quitar_inc)})
        if anulados:
            transformaciones.append({"regla": "fuera_de_rango_anulados", "detalle": "Valores fuera de rango dejados vacíos.",
                                     "afectados": anulados, "casos": casos_anulados[: universales.MAX_CASOS]})
        if casos_cambiados:
            transformaciones.append({"regla": "fuera_de_rango_cambiados",
                                     "detalle": "Valores fuera de rango cambiados por un valor de la escala.",
                                     "afectados": len(casos_cambiados), "casos": casos_cambiados[: universales.MAX_CASOS]})
        if no_resp_conservadas:
            transformaciones.append({"regla": "no_respuestas_conservadas", "detalle": "Respuestas «No sé / No aplica» conservadas con su texto (no son puntos de la escala).", "afectados": no_resp_conservadas})
        if no_resp_vaciadas:
            transformaciones.append({"regla": "no_respuestas_vaciadas", "detalle": "Respuestas «No sé / No aplica» dejadas como celdas vacías.", "afectados": no_resp_vaciadas})
        if convertidos:
            transformaciones.append({"regla": "likert_a_numeros", "detalle": "Respuestas Likert en texto convertidas a números (ver libro de códigos).", "afectados": convertidos})

        # Métricas después: duplicados e imposibles que quedan tras aplicar las decisiones.
        restantes_dup = len(estado.duplicadas) - len(quitar_dup)
        en_filas = set(filas_idx)
        restantes_imp = sum(
            1 for c in conservadas for i, d in _decision_fuera(c, estado.tipos[c.id], decisiones).items()
            if d == "conservar" and i in en_filas
        )
        etiquetas = {c.id: c.etiqueta for c in conservadas}
        metricas = _metricas(
            [(etiquetas[cid], vals) for cid, vals in columnas_finales],
            restantes_dup,
            restantes_imp,
            _grupos([(c.etiqueta, estado.tipos[c.id]) for c in conservadas]),
            cfg["umbrales"],
        )
        lr_restantes, _ = _linea_recta(estado, conservadas, filas_idx)
        metricas["n_linea_recta"] = len(lr_restantes)
        metricas["n_incompletos"] = len(_incompletos(conservadas, filas_idx))

        estadistica = _estadistica(estado, conservadas, sin_codificar, roles)
        estadistica["encuestados"] = {"linea_recta": metricas["n_linea_recta"], "incompletos": metricas["n_incompletos"]}

        especifico = _especifico(estado, roles, eliminadas)
        especifico["filas_eliminadas"].update(
            {"duplicadas": len(quitar_dup), "linea_recta": len(quitar_lr - quitar_dup), "incompletas": len(quitar_inc - quitar_dup - quitar_lr)}
        )
        especifico["fiabilidad"] = estadistica["fiabilidad"]
        # Cómo quedaron en el CSV las respuestas «No sé / No aplica» de las escalas.
        especifico["no_respuestas"] = "marcadas" if marcar_no_resp else "vacias"

        encabezados = [cid for cid, _ in columnas_finales]
        filas = [[vals[k] or "" for _, vals in columnas_finales] for k in range(len(filas_idx))]
        preguntas = sum(1 for c in conservadas if roles.get(c.id) == "pregunta")
        return ResultadoFinal(
            encabezados=encabezados,
            filas=filas,
            metricas=metricas,
            especifico=especifico,
            transformaciones=transformaciones,
            cifras=[
                {"etiqueta": "Respondentes", "valor": len(filas)},
                {"etiqueta": "Preguntas", "valor": preguntas},
                {"etiqueta": "Columnas eliminadas", "valor": len(eliminadas) + len(estado.tabla.columnas_vacias)},
                {"etiqueta": "Encuestados removidos", "valor": len(quitar_filas)},
            ],
            vista={"forma": "tabla", "columnas": [etiquetas[cid] for cid in encabezados], "filas": filas[:_FILAS_VISTA]},
            estadistica=estadistica,
        )
