# survey_intelligence/engine/profiling/edit_distance.py
"""
Distancia de edición (Levenshtein) para detectar variantes mal escritas de una
etiqueta de escala (p. ej. "En deesacuerdo" vs "En desacuerdo").

Implementación iterativa O(n*m) sin dependencias externas.
"""
from __future__ import annotations


def levenshtein(a: str, b: str) -> int:
    """Distancia de edición entre dos cadenas."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(min(
                previous[j] + 1,       # borrado
                current[j - 1] + 1,    # inserción
                previous[j - 1] + cost # sustitución
            ))
        previous = current
    return previous[-1]
