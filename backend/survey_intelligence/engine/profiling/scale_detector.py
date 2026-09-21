# survey_intelligence/engine/profiling/scale_detector.py
"""
Detector de escalas (determinístico, sin LLM).

Reconoce escalas Likert/ordinales frecuentes en español a partir de los valores
observados en una columna, detecta el nº de puntos, y marca variantes mal escritas
(distancia de edición 1 respecto a una etiqueta canónica) como anomalías con su
canonical_guess.

Las escalas conocidas están ordenadas (índice = código SPSS - 1), lo que permite
más adelante generar value_labels y value_encoding coherentes.
"""
from __future__ import annotations

from survey_intelligence.contracts.canonical import DetectedScale, ScaleAnomaly
from survey_intelligence.contracts.enums import ScaleKind
from survey_intelligence.engine.profiling.edit_distance import levenshtein

# Escalas ordinales conocidas: lista ordenada de etiquetas canónicas (de menor a mayor).
_KNOWN_ORDINAL_SCALES: list[list[str]] = [
    # Acuerdo (5 puntos)
    ["Totalmente desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo",
     "De acuerdo", "Totalmente de acuerdo"],
    # Calidad (5 puntos)
    ["Muy mala", "Mala", "Regular", "Buena", "Muy buena"],
    # Frecuencia (5 puntos)
    ["Nunca", "Casi nunca", "A veces", "Frecuentemente", "Siempre"],
    # Facilidad (5 puntos)
    ["Muy difícil", "Difícil", "Neutral", "Fácil", "Muy fácil"],
    # Intensidad (4 puntos)
    ["Nada", "Poco", "Moderadamente", "Mucho"],
]

# Escalas binarias frecuentes (mezcla es/en observada en las plataformas).
_BINARY_SETS: list[set[str]] = [
    {"sí", "no"}, {"si", "no"}, {"yes", "no"},
]

# Umbral: proporción mínima de valores no vacíos que deben "encajar" en una escala
# conocida (tras corregir typos) para declararla.
_MATCH_THRESHOLD = 0.8
# Distancia máxima para considerar un valor una variante mal escrita de una etiqueta.
_TYPO_MAX_DISTANCE = 2


def _norm(s: str) -> str:
    return s.strip().lower()


def _closest_label(value: str, labels: list[str]) -> tuple[str | None, int]:
    """Etiqueta canónica más cercana al valor y su distancia."""
    best: str | None = None
    best_dist = 10**9
    for label in labels:
        d = levenshtein(_norm(value), _norm(label))
        if d < best_dist:
            best_dist = d
            best = label
    return best, best_dist


def canonical_scale_order(labels: list[str]) -> list[str] | None:
    """
    Dada una lista de etiquetas (posiblemente ya canónicas), devuelve el orden
    canónico completo de la escala conocida a la que pertenecen (menor -> mayor),
    o None si no coincide con ninguna escala conocida.

    Se usa para asignar códigos SPSS consistentes (índice + 1 = código).
    """
    label_set = {_norm(l) for l in labels}
    for scale_labels in _KNOWN_ORDINAL_SCALES:
        known = {_norm(l) for l in scale_labels}
        # La escala coincide si las etiquetas observadas son subconjunto de la conocida.
        if label_set and label_set.issubset(known):
            return list(scale_labels)
    return None


def detect_scale(values: list[str]) -> DetectedScale | None:
    """
    Detecta la escala de una columna a partir de sus valores no vacíos.

    Devuelve None si no reconoce ninguna escala conocida (puede ser nominal libre).
    """
    non_empty = [v for v in values if v and v.strip()]
    if len(non_empty) < 2:
        return None

    distinct = {_norm(v) for v in non_empty}

    # 1) Binaria.
    for bset in _BINARY_SETS:
        if distinct.issubset(bset) or (distinct & bset and len(distinct) <= 3):
            if distinct.issubset(bset):
                return DetectedScale(
                    kind=ScaleKind.BINARY,
                    points=2,
                    labels=sorted({v for v in non_empty}, key=str.lower),
                    consistent=True,
                    anomalies=[],
                )

    # 2) Ordinal conocida: busca la escala cuyas etiquetas cubren mejor los valores.
    for scale_labels in _KNOWN_ORDINAL_SCALES:
        matched = 0
        anomalies_map: dict[str, ScaleAnomaly] = {}
        for value in non_empty:
            label, dist = _closest_label(value, scale_labels)
            if dist == 0:
                matched += 1
            elif label is not None and dist <= _TYPO_MAX_DISTANCE:
                matched += 1
                # Es una variante mal escrita.
                if value not in anomalies_map:
                    count = sum(1 for x in non_empty if x == value)
                    anomalies_map[value] = ScaleAnomaly(
                        value=value, occurrences=count, canonical_guess=label
                    )
        if matched / len(non_empty) >= _MATCH_THRESHOLD:
            anomalies = list(anomalies_map.values())
            return DetectedScale(
                kind=ScaleKind.LIKERT,
                points=len(scale_labels),
                labels=list(scale_labels),
                consistent=len(anomalies) == 0,
                anomalies=anomalies,
            )

    return None
