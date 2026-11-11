"""Búsqueda híbrida del chat (11 nov): significado (Chroma) + palabras (texto completo de Postgres).

El modelo de embeddings (paraphrase-multilingual-mpnet, ~128 tokens) ubica mal preguntas casi literales: «¿En qué
modalidad cursan su programa?» daba 0.46 con la pregunta p03 «¿En qué modalidad cursas tu programa?» y la ficha le
ganaba; «¿Cuál es la situación laboral…?» encontraba antes un KPI que la p15. La búsqueda por palabras sí las
encuentra. Las dos listas se combinan con Reciprocal Rank Fusion (RRF, k = 60): cada fragmento suma 1/(k + posición)
en cada lista en que aparece.

Es general: busca sobre el texto de cualquier fragmento indexado (`documento_vectorizado.chunk_texto`), sin
saber de qué instrumento o sección es, así que un instrumento nuevo entra igual. No hace falta reindexar.

Qué llega a la respuesta: un fragmento pasa si su similitud (coseno) alcanza RAG_MIN_SCORE o si contiene la mayor
parte de las palabras con contenido de la pregunta (`cobertura` ≥ RAG_MIN_COBERTURA, al menos 2). La similitud que
se muestra en las tarjetas sigue siendo el coseno del embedding.
"""
from __future__ import annotations

import logging
import math
import re
import unicodedata
from typing import Any, Callable

from sqlalchemy import text

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_K_RRF = 60
_LARGO_RAIZ = 5
# Palabras sin contenido para decidir de qué trata la pregunta: interrogativos, verbos de relleno y palabras que
# aparecen en casi todos los fragmentos de un acervo de instrumentos educativos (sin IDF, pesarían como las demás).
_VACIAS = {
    "cual", "cuales", "cuanto", "cuanta", "cuantos", "cuantas", "como", "donde", "cuando", "quien", "quienes", "porque",
    "para", "sobre", "segun", "entre", "desde", "hacia", "hasta", "este", "esta", "estos", "estas", "eso", "esos", "esas",
    "aquel", "todos", "todas", "todo", "toda", "mucho", "muchos", "mucha", "muchas", "algun", "alguno", "alguna",
    "algunos", "algunas", "otro", "otra", "otros", "otras", "mismo", "misma", "ellos", "ellas", "nuestro", "nuestra",
    "tienen", "tiene", "tener", "hacen", "hace", "hacer", "usan", "usar", "dicen", "dice", "decir", "estan", "esta",
    "son", "ser", "fue", "eran", "hay", "puede", "pueden", "podria", "debe", "deben", "sus", "les", "los", "las", "del",
    "que", "una", "unos", "unas", "mas", "menos", "muy", "tan", "tambien", "solo", "cada", "favor", "dame", "dime",
    "quiero", "saber", "conocer", "informacion", "datos", "dato",
    # Del dominio: están en casi cualquier fragmento.
    "estudiante", "estudiantes", "alumno", "alumnos", "alumna", "alumnas", "instrumento", "instrumentos", "encuesta",
    "encuestas", "encuestados", "pregunta", "preguntas", "respuesta", "respuestas", "respondieron", "respondio",
    "respondente", "respondentes", "participante", "participantes", "persona", "personas",
}


def _plano(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def terminos(pregunta: str) -> list[str]:
    """Palabras con contenido de la pregunta (sin acentos, sin repetir, en orden)."""
    vistos: dict[str, None] = {}
    for p in re.findall(r"[a-zñ0-9]+", _plano(pregunta)):
        if len(p) >= 4 and p not in _VACIAS and not p.isdigit():
            vistos.setdefault(p, None)
    return list(vistos)


def _raiz(palabra: str) -> str:
    return palabra[:_LARGO_RAIZ]


def cobertura(terminos_pregunta: list[str], texto: str) -> tuple[float, int]:
    """(proporción de las palabras de la pregunta que están en el texto, cuántas). Compara raíces de 5 letras:
    «cursan» = «cursas», «laboral» = «laborales»."""
    if not terminos_pregunta:
        return 0.0, 0
    raices = {_raiz(p) for p in re.findall(r"[a-zñ0-9]+", _plano(texto)) if len(p) >= 4}
    hallados = sum(1 for t in terminos_pregunta if _raiz(t) in raices)
    return hallados / len(terminos_pregunta), hallados


def pasa_por_palabras(coincidencia: float | None, halladas: int | None) -> bool:
    return bool(coincidencia is not None and halladas is not None and halladas >= 2
                and coincidencia >= settings.RAG_MIN_COBERTURA)


_MIN_COBERTURA_FICHA = 0.5
# Textos generales que se parecen a casi cualquier pregunta del dominio sin responderla: la ficha (describe el
# instrumento entero) y los KPI (la definición de un indicador; 0.65 con «¿En qué modalidad cursan su programa?»).
_GENERALES = {"encabezado", "kpi"}


def relevante(fragmento: dict[str, Any]) -> bool:
    """¿Llega a la respuesta? Por significado (coseno) o por palabras (cobertura). Los textos generales (`_GENERALES`)
    se parecen a casi cualquier pregunta del dominio (la ficha, 0.67 con «¿qué estrategias usan para mejorar su
    rendimiento?» en un instrumento que no trata eso): por significado solo cuentan si además comparten la mitad de las
    palabras de la pregunta."""
    score = fragmento.get("score")
    if not settings.RAG_HIBRIDA:  # solo semántica: el comportamiento anterior al 11 nov
        return score is not None and score >= settings.RAG_MIN_SCORE
    coincidencia = fragmento.get("coincidencia")
    if pasa_por_palabras(coincidencia, fragmento.get("palabras")):
        return True
    if score is None or score < settings.RAG_MIN_SCORE:
        return False
    if fragmento.get("seccion") in _GENERALES and coincidencia is not None:
        return coincidencia >= _MIN_COBERTURA_FICHA
    return True


# Secciones que repiten el texto de las preguntas (una por persona): sin tope, miles de respondentes empatan con la
# pregunta del instrumento y la desplazan de la lista de palabras.
_POR_PERSONA = {"respondente", "alumno", "intercambio"}
_MAX_POR_PERSONA = 2  # por instrumento, en la lista de palabras
# Candidatos por palabra: primero lo que describe el instrumento (preguntas, reactivos, ficha, KPIs) y después lo de
# cada persona; si no, «laboral» traía 80 de los 2,000 respondentes que repiten la p15 y nunca la p15.
_POR_TERMINO = 80
_K1, _B = 1.2, 0.75  # BM25


def _bm25(palabras: list[str], filas: list[tuple[str, str, str, str]], df: dict[str, int], total: int
          ) -> list[tuple[float, str, str, str]]:
    """(puntaje BM25, id, instrumento, sección) de cada candidato. IDF con la frecuencia real de cada palabra en el
    alcance (Postgres no la usa al ordenar: «programa», que está en casi todo, pesaba igual que «modalidad»)."""
    largos = {i: max(1, len(t.split())) for i, t, _, _ in filas}
    promedio = sum(largos.values()) / len(largos) if largos else 1.0
    idf = {p: math.log(1 + (total - df.get(p, 0) + 0.5) / (df.get(p, 0) + 0.5)) for p in palabras}
    salida = []
    for i, texto_frag, inst, seccion in filas:
        raices = [_raiz(w) for w in re.findall(r"[a-zñ0-9]+", _plano(texto_frag)) if len(w) >= 4]
        puntaje = 0.0
        for p in palabras:
            tf = raices.count(_raiz(p))
            if tf:
                puntaje += idf[p] * tf * (_K1 + 1) / (tf + _K1 * (1 - _B + _B * largos[i] / promedio))
        salida.append((puntaje, i, inst, seccion))
    return salida


def _lexicos(fabrica_sesiones: Callable[[], Any], palabras: list[str], ids: list[str], limite: int) -> list[str]:
    """IDs de Chroma de los fragmentos que mejor coinciden por palabras (texto completo de Postgres en español para
    encontrarlos, BM25 para ordenarlos, con tope de fragmentos por persona)."""
    filtro = "AND p.id_crudo = ANY(:ids)" if ids else ""
    base = f"""
        FROM tt_rag.documento_vectorizado d
        JOIN tt_rag.instrumento_procesado p ON p.id_instrumento = d.instrumento_id
        WHERE d.chroma_vector_id IS NOT NULL {filtro}"""
    candidatos_sql = text(f"""
        SELECT d.chroma_vector_id, d.chunk_texto, p.id_crudo::text, coalesce(d.seccion, '') {base}
          AND to_tsvector('spanish', d.chunk_texto) @@ plainto_tsquery('spanish', :palabra)
        ORDER BY coalesce(d.seccion, '') IN ('respondente', 'alumno', 'intercambio'),
                 ts_rank_cd(to_tsvector('spanish', d.chunk_texto), plainto_tsquery('spanish', :palabra), 1) DESC
        LIMIT :n""")
    df_sql = text(f"SELECT count(*) {base} AND to_tsvector('spanish', d.chunk_texto) @@ plainto_tsquery('spanish', :palabra)")
    total_sql = text(f"SELECT count(*) {base}")
    parametros: dict[str, Any] = {}
    if ids:
        parametros["ids"] = [int(i) for i in ids if str(i).isdigit()]
    sesion = fabrica_sesiones()
    try:
        total = int(sesion.execute(total_sql, parametros).scalar() or 0)
        filas: dict[str, tuple[str, str, str, str]] = {}
        df: dict[str, int] = {}
        for palabra in palabras:
            df[palabra] = int(sesion.execute(df_sql, {**parametros, "palabra": palabra}).scalar() or 0)
            for fila in sesion.execute(candidatos_sql, {**parametros, "palabra": palabra, "n": _POR_TERMINO}):
                filas.setdefault(fila[0], (fila[0], fila[1], fila[2], fila[3]))
    finally:
        sesion.close()
    ordenados = sorted(_bm25(palabras, list(filas.values()), df, total), key=lambda x: -x[0])
    salida: list[str] = []
    por_persona: dict[str, int] = {}
    for puntaje, i, inst, seccion in ordenados:
        if puntaje <= 0:
            break
        if seccion in _POR_PERSONA:
            if por_persona.get(inst, 0) >= _MAX_POR_PERSONA:
                continue
            por_persona[inst] = por_persona.get(inst, 0) + 1
        salida.append(i)
        if len(salida) >= limite:
            break
    return salida


def _coseno(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def fusionar(semanticos: list[str], lexicos: list[str]) -> list[str]:
    """Reciprocal Rank Fusion de dos rankings de IDs."""
    puntos: dict[str, float] = {}
    for lista in (semanticos, lexicos):
        for posicion, ident in enumerate(lista, start=1):
            puntos[ident] = puntos.get(ident, 0.0) + 1.0 / (_K_RRF + posicion)
    return sorted(puntos, key=lambda i: -puntos[i])


def consultar(coleccion: Any, vector: list[float], pregunta: str, n_results: int, where: dict[str, Any] | None,
              ids: list[str], fabrica_sesiones: Callable[[], Any] | None) -> dict[str, Any]:
    """Como `coleccion.query`, pero con la lista de palabras fusionada. Devuelve la misma forma (listas dentro de
    una lista) más `coincidencias` y `palabras` (cobertura de la pregunta en cada fragmento) y `rangos` (posición en la
    búsqueda semántica y en la de palabras, None si no apareció)."""
    res = coleccion.query(query_embeddings=[vector], n_results=n_results, where=where,
                          include=["metadatas", "documents", "distances"])
    metadatas = (res.get("metadatas") or [[]])[0]
    sem_ids = list((res.get("ids") or [[]])[0]) or [f"_semantico_{n}" for n in range(len(metadatas))]
    datos: dict[str, tuple[Any, Any, float]] = {
        i: (m, d, round(1.0 - float(dist), 4))
        for i, m, d, dist in zip(sem_ids, (res.get("metadatas") or [[]])[0], (res.get("documents") or [[]])[0],
                                  (res.get("distances") or [[]])[0])
    }
    palabras = terminos(pregunta)
    lex_ids: list[str] = []
    if settings.RAG_HIBRIDA and palabras and fabrica_sesiones is not None:
        try:
            lex_ids = _lexicos(fabrica_sesiones, palabras, ids, settings.RAG_LEXICOS_MAX)
        except Exception as exc:  # noqa: BLE001 — sin Postgres (o SQLite en pruebas) queda solo la semántica
            logger.debug("Búsqueda por palabras no disponible: %s", exc)
            lex_ids = []
    faltan = [i for i in lex_ids if i not in datos]
    if faltan:
        try:
            extra = coleccion.get(ids=faltan, include=["metadatas", "documents", "embeddings"])
            for i, m, d, e in zip(extra.get("ids") or [], extra.get("metadatas") or [], extra.get("documents") or [],
                                  extra.get("embeddings") if extra.get("embeddings") is not None else []):
                datos[i] = (m, d, round(_coseno(vector, [float(x) for x in e]), 4))
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudieron leer los fragmentos de la búsqueda por palabras: %s", exc)
    orden = [i for i in fusionar(sem_ids, lex_ids) if i in datos]
    rango_sem = {i: n for n, i in enumerate(sem_ids, start=1)}
    rango_lex = {i: n for n, i in enumerate(lex_ids, start=1)}
    salida: dict[str, Any] = {"ids": [[]], "metadatas": [[]], "documents": [[]], "distances": [[]],
                              "coincidencias": [[]], "palabras": [[]], "rangos": [[]]}
    for i in orden:
        meta, doc, score = datos[i]
        cob, halladas = cobertura(palabras, str(doc or ""))
        salida["ids"][0].append(i)
        salida["metadatas"][0].append(meta)
        salida["documents"][0].append(doc)
        salida["distances"][0].append(1.0 - score)
        salida["coincidencias"][0].append(round(cob, 3))
        salida["palabras"][0].append(halladas)
        salida["rangos"][0].append({"semantica": rango_sem.get(i), "palabras": rango_lex.get(i)})
    return salida
