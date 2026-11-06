"""Medidas estadísticas de la limpieza (funciones puras, sin dependencias externas).

- Descriptivos numéricos: n, media, mediana, desviación estándar muestral, mínimo,
  máximo, cuartiles (método inclusivo, como Excel/SPSS), IQR, asimetría (G1) y
  curtosis en exceso (G2), con las fórmulas muestrales de Excel/SPSS.
- Frecuencias y moda de variables categóricas, binarias y Likert.
- Atípicos por ±kσ o por rango intercuartílico (Q1 − k·IQR, Q3 + k·IQR).
- Fiabilidad de las encuestas: alfa de Cronbach (con «alfa si se elimina el ítem» y
  correlación ítem-total corregida), interpretada con George y Mallery (2003).

Las pruebas estandarizadas no se califican (no hay clave de respuestas), así que aquí no
hay KR-20 ni análisis de dificultad o discriminación.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any, Sequence


def _r(x: float | None, d: int = 4) -> float | None:
    return None if x is None or math.isnan(x) else round(x, d)


# ── Descriptivos ───────────────────────────────────────────────────────────────


def asimetria(xs: Sequence[float]) -> float | None:
    """Asimetría muestral G1 (la de Excel `SKEW` y SPSS). Requiere n ≥ 3 y varianza > 0."""
    n = len(xs)
    if n < 3:
        return None
    s = statistics.stdev(xs)
    if s == 0:
        return None
    m = statistics.fmean(xs)
    return n / ((n - 1) * (n - 2)) * sum(((x - m) / s) ** 3 for x in xs)


def curtosis(xs: Sequence[float]) -> float | None:
    """Curtosis en exceso G2 (la de Excel `KURT` y SPSS). Requiere n ≥ 4 y varianza > 0."""
    n = len(xs)
    if n < 4:
        return None
    s = statistics.stdev(xs)
    if s == 0:
        return None
    m = statistics.fmean(xs)
    suma = sum(((x - m) / s) ** 4 for x in xs)
    return n * (n + 1) / ((n - 1) * (n - 2) * (n - 3)) * suma - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))


def cuartiles(xs: Sequence[float]) -> tuple[float, float, float] | None:
    if len(xs) < 2:
        return None
    q1, q2, q3 = statistics.quantiles(xs, n=4, method="inclusive")
    return q1, q2, q3


def descriptivos(xs: Sequence[float]) -> dict[str, Any] | None:
    """Descriptivos de una variable numérica (None si no hay datos)."""
    xs = [float(x) for x in xs]
    if not xs:
        return None
    q = cuartiles(xs)
    return {
        "n": len(xs),
        "media": _r(statistics.fmean(xs)),
        "mediana": _r(statistics.median(xs)),
        "desviacion": _r(statistics.stdev(xs)) if len(xs) > 1 else None,
        "min": _r(min(xs)),
        "max": _r(max(xs)),
        "q1": _r(q[0]) if q else None,
        "q3": _r(q[2]) if q else None,
        "iqr": _r(q[2] - q[0]) if q else None,
        "asimetria": _r(asimetria(xs)),
        "curtosis": _r(curtosis(xs)),
    }


def frecuencias(valores: Sequence[str], orden: Sequence[str] | None = None, maximo: int = 20) -> dict[str, Any]:
    """Frecuencias absolutas y relativas, y moda.

    Con `orden` (p. ej. las etiquetas de una escala) se listan todas sus opciones en
    ese orden, aunque alguna no aparezca; si no, de la más a la menos frecuente.
    """
    conteo = Counter(valores)
    total = sum(conteo.values())
    claves = list(orden) if orden else [v for v, _ in conteo.most_common(maximo)]
    tabla = [{"valor": v, "n": conteo.get(v, 0), "pct": _r(conteo.get(v, 0) / total) if total else 0.0} for v in claves]
    maximo_n = max(conteo.values(), default=0)
    modas = [v for v in claves if conteo.get(v, 0) == maximo_n and maximo_n > 0]
    return {
        "tabla": tabla,
        "moda": modas[0] if len(modas) == 1 else (modas if modas else None),
        "n_categorias": len(conteo),
        "otras": max(0, len(conteo) - len(claves)) if not orden else 0,
    }


# ── Atípicos ───────────────────────────────────────────────────────────────────


def limites_atipicos(xs: Sequence[float], metodo: str, k: float) -> tuple[float, float] | None:
    """Límites fuera de los cuales un valor es atípico (None si no se pueden calcular)."""
    xs = [float(x) for x in xs]
    if metodo == "iqr":
        q = cuartiles(xs)
        if not q:
            return None
        iqr = q[2] - q[0]
        return (q[0] - k * iqr, q[2] + k * iqr) if iqr > 0 else None
    if len(xs) < 2:
        return None
    media, sigma = statistics.fmean(xs), statistics.pstdev(xs)
    return (media - k * sigma, media + k * sigma) if sigma > 0 else None


def contar_fuera(xs: Sequence[float], limites: tuple[float, float] | None) -> int:
    if not limites:
        return 0
    return sum(1 for x in xs if x < limites[0] or x > limites[1])


# ── Correlación ────────────────────────────────────────────────────────────────


def pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) < 3 or len(a) != len(b):
        return None
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


# ── Fiabilidad ─────────────────────────────────────────────────────────────────


def interpretar_alfa(alfa: float | None) -> str | None:
    """George y Mallery (2003)."""
    if alfa is None:
        return None
    for limite, texto in ((0.9, "excelente"), (0.8, "buena"), (0.7, "aceptable"), (0.6, "cuestionable"), (0.5, "pobre")):
        if alfa >= limite:
            return texto
    return "inaceptable"


def _alfa(matriz: list[list[float]]) -> float | None:
    k = len(matriz[0]) if matriz else 0
    if k < 2 or len(matriz) < 2:
        return None
    totales = [sum(f) for f in matriz]
    var_total = statistics.variance(totales)
    if var_total == 0:
        return None
    var_items = sum(statistics.variance([f[j] for f in matriz]) for j in range(k))
    return k / (k - 1) * (1 - var_items / var_total)


def cronbach(matriz: list[list[float | None]], items: list[str], min_casos: int = 3) -> dict[str, Any] | None:
    """Alfa de Cronbach con eliminación por lista (solo casos con todos los ítems).

    Devuelve también, por ítem, el alfa si se elimina y la correlación ítem-total corregida.
    """
    completos = [[float(x) for x in f] for f in matriz if all(x is not None for x in f)]
    if len(items) < 2 or len(completos) < max(2, min_casos):
        return None
    alfa = _alfa(completos)
    por_item = []
    for j, item in enumerate(items):
        resto = [[x for i, x in enumerate(f) if i != j] for f in completos]
        columna = [f[j] for f in completos]
        por_item.append(
            {
                "item": item,
                "media": _r(statistics.fmean(columna)),
                "correlacion_item_total": _r(pearson(columna, [sum(f) for f in resto])),
                "alfa_si_se_elimina": _r(_alfa(resto)) if len(items) > 2 else None,
            }
        )
    return {
        "n_items": len(items),
        "n_casos": len(completos),
        "n_excluidos": len(matriz) - len(completos),
        "alfa": _r(alfa),
        "interpretacion": interpretar_alfa(alfa),
        "por_item": por_item,
    }
