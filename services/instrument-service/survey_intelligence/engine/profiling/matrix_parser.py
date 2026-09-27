# survey_intelligence/engine/profiling/matrix_parser.py
"""
Parser de preguntas-matriz (patrón Strategy).

Distintas plataformas marcan el par tronco/ítem de forma distinta:
  - LimeSurvey / Google Forms:  "tronco [ítem]"
  - Microsoft Forms:            "tronco .subítem"  (a veces con salto de línea)

Cada estrategia intenta descomponer un encabezado en (stem, item). Si ninguna
aplica, el encabezado es una pregunta simple (no matriz).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# "tronco [ítem]" — el ítem va entre corchetes al final.
_BRACKET = re.compile(r"^(?P<stem>.*?)\s*\[(?P<item>.+?)\]\s*$")

# "tronco .subítem" — Microsoft Forms; el subítem va tras un punto final.
# El tronco suele terminar antes de un '.' seguido de texto sin más puntos-frase.
_DOT_SUB = re.compile(r"^(?P<stem>.+?)\s*\.\s*(?P<item>[^.]+?)\s*$")


@dataclass(frozen=True)
class MatrixParse:
    is_matrix: bool
    stem: str | None = None
    item: str | None = None


def _try_bracket(header: str) -> MatrixParse | None:
    m = _BRACKET.match(header)
    if m and m.group("stem").strip() and m.group("item").strip():
        return MatrixParse(True, m.group("stem").strip(), m.group("item").strip())
    return None


def _try_dot_sub(header: str) -> MatrixParse | None:
    """
    Aplica solo si el tronco 'parece' un tronco de matriz: contiene una frase larga
    y el subítem es corto. Evita partir preguntas normales que terminan en '.'.
    """
    m = _DOT_SUB.match(header)
    if not m:
        return None
    stem = m.group("stem").strip()
    item = m.group("item").strip()
    # Heurística: el tronco debe ser sustancial (>=4 palabras) y el ítem no vacío,
    # y el tronco NO debe terminar en signo de interrogación (eso es pregunta simple).
    if not stem or not item:
        return None
    if stem.endswith("?"):
        return None
    if len(stem.split()) < 4:
        return None
    return MatrixParse(True, stem, item)


# Orden de estrategias: corchete primero (más inequívoco), luego punto-subítem.
_STRATEGIES = (_try_bracket, _try_dot_sub)


def parse_matrix(header: str) -> MatrixParse:
    """Descompone un encabezado en (stem, item) si es una pregunta matriz."""
    for strategy in _STRATEGIES:
        result = strategy(header)
        if result is not None:
            return result
    return MatrixParse(False)


# ───────────────────────────────────────────────────────────────────────────
# Rediseño v2 — descomposición extendida (N niveles de corchete + Rank/Scale).
# Aditivo: NO cambia parse_matrix (que S2 v1 sigue usando). Estas funciones las
# consumen los motores question_typing / question_grouping (Fase 2).
# ───────────────────────────────────────────────────────────────────────────

# Todos los segmentos entre corchetes al final del encabezado: "stem [a][b][c]".
_ALL_BRACKETS = re.compile(r"\[(?P<seg>[^\[\]]+)\]")
# "[Rank 3]" / "[rank 3]"  → ranking advanced (LimeSurvey).
_RANK = re.compile(r"^\s*rank\s+(?P<k>\d+)\s*$", re.IGNORECASE)
# "[Scale 1]" / "[scale 2]" → eje de escala (array dual scale).
_SCALE = re.compile(r"^\s*scale\s+(?P<k>\d+)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class HeaderParse:
    """
    Descomposición extendida de un encabezado en su tronco y segmentos.

    Attributes:
        stem:      texto de la pregunta sin los segmentos entre corchetes/punto.
        segments:  segmentos entre corchetes al final, en orden (0..N).
        rank:      k si algún segmento era "[Rank k]", si no None.
        scale:     k si algún segmento era "[Scale k]", si no None.
        n_brackets: número de segmentos entre corchetes detectados.
    """
    stem: str
    segments: tuple[str, ...] = ()
    rank: int | None = None
    scale: int | None = None

    @property
    def n_brackets(self) -> int:
        return len(self.segments)


def _strip_trailing_brackets(header: str) -> tuple[str, list[str]]:
    """
    Separa el tronco de los segmentos entre corchetes que aparecen al FINAL.

    "stem [a][b]" -> ("stem", ["a","b"]). Si no hay corchetes finales, ([], stem).
    Conserva corchetes que no estén al final del encabezado (poco común).
    """
    # Tomar la cola contigua de "[...]" al final.
    m = re.search(r"(?:\s*\[[^\[\]]+\])+\s*$", header)
    if not m:
        return header.strip(), []
    cola = m.group(0)
    stem = header[: m.start()].strip()
    segments = [s.strip() for s in _ALL_BRACKETS.findall(cola)]
    return stem, segments


def parse_header(header: str) -> HeaderParse:
    """
    Descompone un encabezado en tronco + segmentos (N niveles de corchete), y
    reconoce marcadores especiales [Rank k] / [Scale k]. Si no hay corchetes al
    final, intenta la vía punto-subítem de Microsoft Forms.

    Determinístico y sin efectos. No decide el tipo (eso es question_typing).
    """
    stem, segments = _strip_trailing_brackets(header)

    if segments:
        rank = scale = None
        item_segments: list[str] = []
        for seg in segments:
            mr = _RANK.match(seg)
            ms = _SCALE.match(seg)
            if mr:
                rank = int(mr.group("k"))
            elif ms:
                scale = int(ms.group("k"))
            else:
                item_segments.append(seg)
        return HeaderParse(stem=stem, segments=tuple(item_segments), rank=rank, scale=scale)

    # Sin corchetes: probar el patrón punto-subítem (Microsoft Forms).
    dot = _try_dot_sub(header)
    if dot is not None and dot.stem and dot.item:
        return HeaderParse(stem=dot.stem, segments=(dot.item,))

    return HeaderParse(stem=header.strip(), segments=())
