"""Agregación estadística de respuestas por dimensión (diseño §4, §8, §9, §15.3).

Módulo PURO (sin I/O): recibe `respondents` y descripciones de preguntas y
devuelve dataclasses + prosa en español lista para indexar. Nunca genera un
chunk por respondente; agrega sobre todas las respuestas y entrega un objeto por
dimensión (invariante §9).

Reglas clave (§4.2, §4.4):
  - `_num` coacciona a `float|None` excluyendo `bool` explícitamente (bool es
    subclase de int en Python) y aceptando str con coma decimal.
  - Si tras `_num` el conjunto queda vacío (`n == 0`), las `agregar_*` devuelven
    `None` y el orquestador no emite chunk (nunca se formatea `nan`).
  - Toda redacción comprueba que el campo no sea `None` antes de interpolar.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "ResumenItem",
    "HallazgoDimension",
    "HallazgoGrupo",
    "escala_efectiva",
    "agregar_likert",
    "agregar_numerica",
    "agregar_categorica",
    "redactar_hallazgo",
    "redactar_resumen_global",
    "redactar_interpretacion_dimension",
    "agrupar_por_desempeno",
    "redactar_grupo",
]


@dataclass(frozen=True)
class ResumenItem:
    question_id: str
    texto: str  # texto redactado del .txt si existe; si no, etiqueta normalizada
    media: float
    de: float  # desviación estándar poblacional (ddof=0)
    n: int


@dataclass(frozen=True)
class HallazgoDimension:
    dimension: str  # nombre completo de la dimensión
    tipo: str  # "likert" | "numerica" | "categorica"
    n: int  # nº de respondentes con al menos un valor válido
    # Likert:
    media: float | None = None
    de: float | None = None
    pct_alto: float | None = None  # % que respondió en el extremo alto
    item_mas_alto: ResumenItem | None = None
    item_mas_bajo: ResumenItem | None = None
    # Numérica:
    minimo: float | None = None
    maximo: float | None = None
    # Categórica / binaria: top categorías con su %
    distribucion: list[tuple[str, float]] = field(default_factory=list)


@dataclass(frozen=True)
class HallazgoGrupo:
    """Grupo de respondentes por su puntaje global Likert (mejora 3, §6.4)."""

    grupo: str  # "bajo" | "medio" | "alto" (etiqueta de salida)
    n: int  # respondentes en el grupo
    pct: float  # % sobre el total de respondentes clasificados
    puntaje_medio: float  # media de los puntajes globales del grupo
    dim_altas: list[tuple[str, float]]  # 1-2 dims con mayor media del grupo
    dim_bajas: list[tuple[str, float]]  # 1-2 dims con menor media del grupo


# ── Cortes paramétricos de clasificación (§5.1, §16.2) ──────────────────────
# DECISIÓN FIJA: tercios del rango efectivo [scale_min, scale_max].
#   bajo  : media <  scale_min + 1/3*(scale_max - scale_min)
#   medio : entre 1/3 y 2/3 del rango
#   alto  : media >= scale_min + 2/3*(scale_max - scale_min)
# Para la escala por defecto 1..5 da bajo < 2.333, medio 2.333..3.667, alto >= 3.667.
# Se eligen tercios (y no 0.375/0.625) por simetría, independencia de la escala y
# por partir el continuo en tres zonas iguales sin supuestos de distribución.
_FRAC_BAJO: float = 1.0 / 3.0
_FRAC_ALTO: float = 2.0 / 3.0

# Vocabulario de nivel por DIMENSIÓN (mejora 2, §16.2). Fuente de verdad única.
_ETIQUETA_NIVEL = {"bajo": "nivel bajo", "medio": "nivel moderado", "alto": "nivel alto"}
# Etiqueta de salida de GRUPO (mejora 3). Renombrado centralizado (NIT #9).
_ETIQUETA_GRUPO = {"bajo": "bajo", "medio": "medio", "alto": "alto"}


# ── Coacción numérica única (§4.2) ──────────────────────────────────────────
def _num(v) -> float | None:
    """Coacciona `v` a float; excluye bool, acepta str con coma decimal.

    Devuelve `None` para `bool`, `None` y cualquier str no parseable.
    """
    if isinstance(v, bool):  # bool ES subclase de int en Python: excluir explícito
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _answers(respondente) -> dict:
    """Extrae el dict `answers` de un respondente de forma defensiva."""
    if isinstance(respondente, dict):
        ans = respondente.get("answers")
        if isinstance(ans, dict):
            return ans
    return {}


# ── Agregación likert (§4.2) ────────────────────────────────────────────────
def agregar_likert(
    items: list[tuple[str, str, int, int]],
    respondents: list[dict],
    dimension: str,
) -> HallazgoDimension | None:
    """Agrega una dimensión likert.

    `items` = [(question_id, texto_redactado, scale_min, scale_max), ...].
    Devuelve `None` si ningún respondente aportó valores válidos (§4.4).
    """
    if not items:
        return None

    ids_dim = [it[0] for it in items]

    # Vector agregado (todos los ítems × todos los respondentes) y nº de
    # respondentes con >=1 valor válido en la dimensión.
    vector: list[float] = []
    n_respondentes = 0
    for r in respondents:
        answers = _answers(r)
        validos_r = [
            x for qid in ids_dim if (x := _num(answers.get(qid))) is not None
        ]
        if validos_r:
            n_respondentes += 1
            vector.extend(validos_r)

    if n_respondentes == 0 or not vector:
        return None

    arr = np.asarray(vector, dtype=float)
    media = float(np.mean(arr))
    de = float(np.std(arr, ddof=0))

    # Umbral del extremo alto: tercio superior del rango efectivo (§4.2).
    scale_min, scale_max = _escala_efectiva(items)
    umbral = scale_min + 2.0 * (scale_max - scale_min) / 3.0
    pct_alto = float(np.mean(arr >= umbral) * 100.0)

    # ResumenItem por question_id (solo con valores válidos) para extremos.
    resumenes: list[ResumenItem] = []
    for qid, texto, _smin, _smax in items:
        vals = [
            x
            for r in respondents
            if (x := _num(_answers(r).get(qid))) is not None
        ]
        if not vals:
            continue
        iarr = np.asarray(vals, dtype=float)
        resumenes.append(
            ResumenItem(
                question_id=qid,
                texto=texto,
                media=float(np.mean(iarr)),
                de=float(np.std(iarr, ddof=0)),
                n=len(vals),
            )
        )

    item_mas_alto = max(resumenes, key=lambda it: it.media) if resumenes else None
    item_mas_bajo = min(resumenes, key=lambda it: it.media) if resumenes else None

    return HallazgoDimension(
        dimension=dimension,
        tipo="likert",
        n=n_respondentes,
        media=media,
        de=de,
        pct_alto=pct_alto,
        item_mas_alto=item_mas_alto,
        item_mas_bajo=item_mas_bajo,
    )


def escala_efectiva(items: list[tuple[str, str, int, int]]) -> tuple[float, float]:
    """Rango efectivo de la escala del instrumento. ÚNICO punto público (§5.4, §16.1).

    Robustez (F5): toma `scale_min = min` de `it[2]` y `scale_max = max` de `it[3]`
    sobre TODOS los ítems (no solo `items[0]`), para no sesgar la clasificación si
    el instrumento mezclara dimensiones con escalas distintas. Cae a `(1.0, 5.0)`
    si la lista es vacía, los tipos son inválidos (TypeError/ValueError/IndexError)
    o el rango resultante es inválido (`scale_min >= scale_max`).

    Bajo el invariante de escala homogénea (§5.4b, §9), el envolvente coincide con
    el del primer ítem, de modo que `agregar_likert` (que usa `_escala_efectiva`
    para `pct_alto`) obtiene el MISMO rango que las mejoras 2 y 3.
    """
    try:
        mins = [float(it[2]) for it in items]
        maxs = [float(it[3]) for it in items]
    except (TypeError, ValueError, IndexError):
        return 1.0, 5.0
    if not mins or not maxs:
        return 1.0, 5.0
    scale_min, scale_max = min(mins), max(maxs)
    if scale_min >= scale_max:
        return 1.0, 5.0
    return scale_min, scale_max


# Alias para no romper la llamada interna de `agregar_likert` (pct_alto).
_escala_efectiva = escala_efectiva


def _clasificar_nivel(media: float, scale_min: float, scale_max: float) -> str:
    """Clasifica una media en 'bajo'|'medio'|'alto' por tercios del rango efectivo.

    Compartida por las mejoras 2 y 3 (cortes paramétricos, §5.1, §16.2). Defensa:
    si `rango <= 0` (escala inválida) se asume 1..5.
    """
    rango = scale_max - scale_min
    if rango <= 0:  # defensa: escala inválida -> se asume 1..5
        scale_min, scale_max, rango = 1.0, 5.0, 4.0
    corte_bajo = scale_min + _FRAC_BAJO * rango
    corte_alto = scale_min + _FRAC_ALTO * rango
    if media < corte_bajo:
        return "bajo"
    if media >= corte_alto:
        return "alto"
    return "medio"


# ── Agregación numérica (§4.2) ──────────────────────────────────────────────
def agregar_numerica(
    question_id: str, texto: str, respondents: list[dict]
) -> HallazgoDimension | None:
    """Agrega una pregunta numérica continua. `None` si no hay valores (§4.4)."""
    vals = [
        x
        for r in respondents
        if (x := _num(_answers(r).get(question_id))) is not None
    ]
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    return HallazgoDimension(
        dimension=texto or question_id,
        tipo="numerica",
        n=len(vals),
        media=float(np.mean(arr)),
        de=float(np.std(arr, ddof=0)),
        minimo=float(np.min(arr)),
        maximo=float(np.max(arr)),
    )


# ── Agregación categórica / binaria (§4.2) ──────────────────────────────────
def agregar_categorica(
    question_id: str,
    texto: str,
    tipo: str,
    respondents: list[dict],
    top: int = 5,
) -> HallazgoDimension | None:
    """Agrega una pregunta categórica/binaria. `None` si no hay valores (§4.4).

    Para `tipo == "binaria"`, los literales "True"/"False" se redactan sí/no.
    """
    valores: list[str] = []
    for r in respondents:
        bruto = _answers(r).get(question_id)
        if bruto is None:
            continue
        s = str(bruto).strip()
        if not s:
            continue
        valores.append(_etiqueta_categoria(s, tipo))

    n = len(valores)
    if n == 0:
        return None

    conteo = collections.Counter(valores)
    distribucion = [
        (categoria, cuenta / n * 100.0)
        for categoria, cuenta in conteo.most_common(top)
    ]
    return HallazgoDimension(
        dimension=texto or question_id,
        tipo="categorica",
        n=n,
        distribucion=distribucion,
    )


def _etiqueta_categoria(valor: str, tipo: str) -> str:
    """Redacta sí/no para binarias; deja el valor tal cual en otro caso."""
    if tipo == "binaria":
        bajo = valor.strip().lower()
        if bajo in ("true", "1", "sí", "si"):
            return "sí"
        if bajo in ("false", "0", "no"):
            return "no"
    return valor


# ── Redacción en español (§4.3, §4.4) ───────────────────────────────────────
def _fmt(x: float | None) -> str:
    return f"{x:.1f}"


def redactar_hallazgo(h: HallazgoDimension) -> str:
    """Redacta un chunk de prosa para una dimensión (§4.3).

    Omite toda cláusula cuyo campo necesario sea `None` (defensa, §4.4).
    """
    if h.tipo == "likert":
        return _redactar_likert(h)
    if h.tipo == "numerica":
        return _redactar_numerica(h)
    if h.tipo == "categorica":
        return _redactar_categorica(h)
    return ""


def _redactar_likert(h: HallazgoDimension) -> str:
    frases: list[str] = []
    if h.media is not None and h.de is not None:
        inicio = (
            f"En la dimensión {h.dimension}, la media de respuesta fue "
            f"{_fmt(h.media)}/5 (DE {_fmt(h.de)})"
        )
        if h.pct_alto is not None:
            inicio += (
                f" y el {round(h.pct_alto)} % del estudiantado respondió 4 o 5"
            )
        frases.append(inicio + ".")
    elif h.pct_alto is not None:
        frases.append(
            f"En la dimensión {h.dimension}, el {round(h.pct_alto)} % del "
            "estudiantado respondió 4 o 5."
        )

    if h.item_mas_alto is not None and h.item_mas_bajo is not None:
        frases.append(
            f"El ítem con media más alta fue «{h.item_mas_alto.texto}» "
            f"(media {_fmt(h.item_mas_alto.media)}) y el más bajo "
            f"«{h.item_mas_bajo.texto}» (media {_fmt(h.item_mas_bajo.media)})."
        )

    frases.append(f"n = {h.n} respondentes.")
    return " ".join(frases)


def _redactar_numerica(h: HallazgoDimension) -> str:
    partes = f"El promedio general de {h.dimension} de los {h.n} respondentes fue"
    if h.media is not None:
        partes += f" {_fmt(h.media)}"
    detalles: list[str] = []
    if h.de is not None:
        detalles.append(f"DE {_fmt(h.de)}")
    if h.minimo is not None and h.maximo is not None:
        detalles.append(f"mínimo {_fmt(h.minimo)}, máximo {_fmt(h.maximo)}")
    if detalles:
        partes += f" ({'; '.join(detalles)})"
    return partes + "."


def _redactar_categorica(h: HallazgoDimension) -> str:
    if not h.distribucion:
        return f"Respecto a {h.dimension}, n = {h.n}."
    piezas = [
        f"el {round(pct)} % {categoria}" for categoria, pct in h.distribucion
    ]
    return (
        f"Respecto a {h.dimension}, {', '.join(piezas)} (n = {h.n})."
    )


def redactar_resumen_global(
    hallazgos: list[HallazgoDimension], n_respondentes: int, titulo: str
) -> str:
    """Redacta el chunk de resumen global de forma defensiva (§4.4, §15.3-NIT5).

    Sin dimensiones likert omite media alta/baja; sin numéricas omite esa
    cláusula; con `hallazgos` vacío reporta solo `n` y la lista de dimensiones.
    """
    encabezado = titulo.strip() if isinstance(titulo, str) and titulo.strip() else "el instrumento"
    frases: list[str] = [
        f"Resumen global de {encabezado}: {n_respondentes} respondentes."
    ]

    nombres = [h.dimension for h in hallazgos if h.dimension]
    if nombres:
        frases.append("Dimensiones evaluadas: " + ", ".join(nombres) + ".")
    else:
        frases.append("No se registraron dimensiones evaluadas.")

    likert = [h for h in hallazgos if h.tipo == "likert" and h.media is not None]
    if likert:
        mas_alta = max(likert, key=lambda h: h.media)
        mas_baja = min(likert, key=lambda h: h.media)
        if mas_alta is mas_baja:
            frases.append(
                f"La dimensión {mas_alta.dimension} obtuvo una media de "
                f"{_fmt(mas_alta.media)}/5."
            )
        else:
            frases.append(
                f"La dimensión con media más alta fue {mas_alta.dimension} "
                f"({_fmt(mas_alta.media)}/5) y la más baja {mas_baja.dimension} "
                f"({_fmt(mas_baja.media)}/5)."
            )

    numericas = [h for h in hallazgos if h.tipo == "numerica" and h.media is not None]
    if numericas:
        destacada = numericas[0]
        frases.append(
            f"En las medidas numéricas, {destacada.dimension} tuvo un promedio "
            f"de {_fmt(destacada.media)}."
        )

    return " ".join(frases)


# ── Mejora 2 — Interpretación por dimensión (§5.3, §16.2-§16.5, §16.7) ───────
# Implicación educativa GENÉRICA derivada SOLO del nivel (nunca inventa causas, §16.7).
_IMPLICACION_NIVEL = {
    "bajo": "Constituye un área de mejora prioritaria.",
    "medio": (
        "Un nivel moderado señala una competencia parcialmente desarrollada y "
        "constituye un área de mejora recomendable."
    ),
    "alto": "Constituye una fortaleza a sostener.",
}


def redactar_interpretacion_dimension(
    h: HallazgoDimension,
    todos_likert: list[HallazgoDimension],
    scale_min: float,
    scale_max: float,
) -> str | None:
    """Chunk interpretativo para una dimensión Likert (mejora 2, §5.3, §16.2-§16.7).

    `todos_likert` son todas las dimensiones likert del instrumento (para situar
    `h` como la más fuerte / más débil y calcular la brecha). Devuelve `None` si
    `h` no tiene media; `''` si `h` no es likert (defensa para uso directo en
    tests, §16.5; el único llamador de producción ya pre-filtra a Likert).
    """
    # (a) Defensa / casos borde.
    if h.tipo != "likert":  # (§16.5) rama defensiva: no se dispara en runtime.
        return ""
    if h.media is None:
        return None

    # (b) Nivel propio vía la ÚNICA función de clasificación.
    nivel = _clasificar_nivel(h.media, scale_min, scale_max)
    etiqueta = _ETIQUETA_NIVEL[nivel]

    # Denominador NUEVO: "rango de 1 a N" (no "/5"), §16.7.
    rango_txt = f"rango de {scale_min:.0f} a {scale_max:.0f}"
    frases: list[str] = [
        f"«{h.dimension}» se sitúa en {etiqueta} (media {_fmt(h.media)} sobre un "
        f"{rango_txt})."
    ]

    # (c) Comparación SOLO si hay >=2 dims likert con media no None.
    comparables = [d for d in todos_likert if d.tipo == "likert" and d.media is not None]
    comparacion: str | None = None
    if len(comparables) >= 2:
        # Desempate determinista: primer máximo/mínimo en el orden de todos_likert
        # (NIT #3). max/min de Python conservan el primero ante empate.
        mas_fuerte = max(comparables, key=lambda d: d.media)
        mas_debil = min(comparables, key=lambda d: d.media)
        if mas_fuerte.media != mas_debil.media:  # omitir si máx == mín (1 sola dim efectiva)
            brecha = abs(mas_fuerte.media - mas_debil.media)
            comparacion = (
                f"La dimensión más fuerte del instrumento es «{mas_fuerte.dimension}» "
                f"(media {_fmt(mas_fuerte.media)}) y la más débil «{mas_debil.dimension}» "
                f"(media {_fmt(mas_debil.media)}); la brecha entre ambas es de "
                f"{_fmt(brecha)} puntos."
            )

    # (d) Implicación educativa genérica derivada solo del nivel (§16.7).
    implicacion = _IMPLICACION_NIVEL[nivel]
    # (e) Cierre con n (chunk autosuficiente).
    cierre = f"n = {h.n} respondentes."

    # (f/g) Ensamblar acotando a <=~700 chars; recortar implicación antes que
    # comparación si el texto se acerca al límite (§16.4).
    if comparacion:
        frases.append(comparacion)
    cuerpo = " ".join(frases + [implicacion, cierre])
    if len(cuerpo) > 700:
        cuerpo = " ".join(frases + [cierre])  # recorta la implicación primero
    return cuerpo


# ── Mejora 3 — Grupos por desempeño (§6, §16.6) ──────────────────────────────
# Cierre interpretativo breve por grupo (§6.5).
_CIERRE_GRUPO = {
    "bajo": "Este grupo concentra las necesidades de apoyo más urgentes del instrumento.",
    "medio": "Este grupo muestra un desempeño intermedio con áreas por consolidar.",
    "alto": "Este grupo muestra un desempeño sólido y sostenido.",
}


def _media_dim_respondente(
    answers: dict, ids_dim: list[str]
) -> float | None:
    """Media de los `_num` válidos de una dimensión para un respondente.

    Descarta `None`; devuelve `None` si no hay ningún valor válido.
    """
    vals = [x for qid in ids_dim if (x := _num(answers.get(qid))) is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def agrupar_por_desempeno(
    items_por_dim: dict[str, list[tuple[str, str, int, int]]],
    respondents: list[dict],
) -> list[HallazgoGrupo]:
    """Agrupa respondentes por su puntaje global Likert (bajo/medio/alto).

    Recibe el DICT `dim -> [(qid, texto, smin, smax), ...]` (§16.6) y los
    `respondents`. Puntaje global = MEDIA DE LAS MEDIAS POR DIMENSIÓN
    (equiponderado, F6). SOLO Likert; nunca lee 'perfil' ni demográficas
    (invariante duro §6.1, §9). Devuelve un `HallazgoGrupo` por grupo NO vacío.
    """
    # (1) Sin ítems Likert -> [].
    items_plano = [it for its in items_por_dim.values() for it in its]
    if not items_plano:
        return []

    # (2) Rango de escala (lista plana, F1).
    smin, smax = escala_efectiva(items_plano)

    # ids por dimensión (para puntaje equiponderado y medias por dimensión).
    ids_por_dim = {dim: [it[0] for it in its] for dim, its in items_por_dim.items()}

    # (3)+(4)+(5) Clasificar cada respondente y acumular por grupo.
    puntajes_por_grupo: dict[str, list[float]] = {}
    # grupo -> dim -> lista de medias (una por respondente miembro con valor en esa dim)
    dim_medias_por_grupo: dict[str, dict[str, list[float]]] = {}
    total = 0

    for r in respondents:
        answers = _answers(r)
        medias_dim: dict[str, float] = {}
        for dim, ids_dim in ids_por_dim.items():
            m = _media_dim_respondente(answers, ids_dim)
            if m is not None:
                medias_dim[dim] = m
        if not medias_dim:
            continue  # respondente sin ninguna dimensión válida -> excluido del total
        total += 1
        puntaje = sum(medias_dim.values()) / len(medias_dim)  # equiponderado (F6)
        clave = _clasificar_nivel(puntaje, smin, smax)
        grupo = _ETIQUETA_GRUPO[clave]
        puntajes_por_grupo.setdefault(grupo, []).append(puntaje)
        acum_dim = dim_medias_por_grupo.setdefault(grupo, {})
        for dim, m in medias_dim.items():
            acum_dim.setdefault(dim, []).append(m)

    # (6) Construir HallazgoGrupo por grupo no vacío.
    if total == 0:
        return []

    resultado: list[HallazgoGrupo] = []
    for grupo, puntajes in puntajes_por_grupo.items():
        n = len(puntajes)
        if n == 0:
            continue
        puntaje_medio = sum(puntajes) / n
        # Media del grupo por dimensión (equiponderada entre respondentes).
        medias_grupo = [
            (dim, sum(vals) / len(vals))
            for dim, vals in dim_medias_por_grupo.get(grupo, {}).items()
            if vals
        ]
        altas = sorted(medias_grupo, key=lambda t: t[1], reverse=True)[:2]
        bajas = sorted(medias_grupo, key=lambda t: t[1])[:2]
        resultado.append(
            HallazgoGrupo(
                grupo=grupo,
                n=n,
                pct=n / total * 100.0,
                puntaje_medio=puntaje_medio,
                dim_altas=altas,
                dim_bajas=bajas,
            )
        )
    return resultado


def redactar_grupo(g: HallazgoGrupo, scale_max: float) -> str:
    """Redacta el chunk de un grupo por desempeño (§6.5). Nunca `nan`."""
    frases: list[str] = [
        f"Grupo de desempeño {g.grupo} (n = {g.n}, {round(g.pct)} % del total)."
    ]
    frases.append(
        f"Su puntaje global promedio fue {_fmt(g.puntaje_medio)} sobre {scale_max:.0f}."
    )

    # Dimensiones de las debilidades (para detectar redundancia con 1 sola dim).
    dims_bajas = {dim for dim, _ in g.dim_bajas}

    if g.dim_bajas:
        piezas = [f"{dim} (media {_fmt(media)})" for dim, media in g.dim_bajas]
        if len(piezas) == 1:
            frases.append(f"Mayor debilidad en {piezas[0]}.")
        else:
            frases.append(
                f"Mayor debilidad en {piezas[0]} y en {piezas[1]}."
            )

    # Fortaleza relativa: omitir si coincide con una debilidad (grupo de 1 dim).
    altas_no_redundantes = [
        (dim, media) for dim, media in g.dim_altas if dim not in dims_bajas
    ]
    if altas_no_redundantes:
        dim, media = altas_no_redundantes[0]
        frases.append(f"Relativa fortaleza en {dim} (media {_fmt(media)}).")

    frases.append(_CIERRE_GRUPO.get(g.grupo, ""))
    return " ".join(f for f in frases if f)
