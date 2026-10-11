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
    "agregar_likert",
    "agregar_numerica",
    "agregar_categorica",
    "redactar_hallazgo",
    "redactar_resumen_global",
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


def _escala_efectiva(items: list[tuple[str, str, int, int]]) -> tuple[float, float]:
    """Rango efectivo de la escala likert; cae a 1..5 si es inválido (§8)."""
    try:
        scale_min = float(items[0][2])
        scale_max = float(items[0][3])
    except (TypeError, ValueError, IndexError):
        return 1.0, 5.0
    if scale_min >= scale_max:
        return 1.0, 5.0
    return scale_min, scale_max


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
