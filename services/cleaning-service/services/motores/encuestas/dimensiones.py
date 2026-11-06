"""Dimensiones sugeridas para ítems Likert cuando el instrumento no trae secciones ni prefijos.

Sin secciones («EVALUACIÓN DEL APRENDIZAJE») ni prefijos de bloque («Evaluación_item3»),
el alfa de Cronbach solo podía calcularse sobre todos los ítems juntos, mezclando escalas.
Aquí se proponen grupos a partir de cómo se responden los ítems; el investigador los
acepta o los ignora en la fase asistida (nunca se aplican solos):

  1. Correlación de Spearman entre ítems (casos completos).
  2. Número de grupos por el criterio de Kaiser (autovalores de la matriz de correlación
     mayores que 1), con tope de p / `min_items`. Se probó también el análisis paralelo de
     Horn (percentil 95, semilla fija): con un factor general fuerte, como en los datos de
     prueba (enc_04: 8 subescalas, Horn 5 y Kaiser 8; enc_01: 5 dimensiones, Horn 2 y
     Kaiser 5), Horn juntaba escalas distintas. Se reporta como dato informativo.
  3. Agrupamiento jerárquico de enlace promedio con distancia 1 − r hasta ese número.
  4. Se conserva un grupo solo si tiene al menos `min_items` ítems y α ≥ `alfa_min`; si
     quedan menos de dos grupos válidos no se sugiere nada (la escala puede ser una sola).

Solo usa numpy (ya presente para el alfa).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from services.motores import estadistica as est

_ITERACIONES_HORN = 100
_SEMILLA = 20261022


@dataclass
class Dimension:
    indices: list[int]   # posiciones de los ítems en la lista recibida
    alfa: float


@dataclass
class Sugerencia:
    dimensiones: list[Dimension]
    kaiser: int
    horn: int


def _rangos(x: np.ndarray) -> np.ndarray:
    """Rangos promedio por columna (empates con el promedio de sus posiciones)."""
    salida = np.empty_like(x, dtype=float)
    for j in range(x.shape[1]):
        col = x[:, j]
        orden = col.argsort(kind="mergesort")
        r = np.empty(len(col))
        r[orden] = np.arange(1, len(col) + 1)
        for v in np.unique(col):
            m = col == v
            r[m] = r[m].mean()
        salida[:, j] = r
    return salida


def _correlacion(x: np.ndarray) -> np.ndarray:
    c = np.corrcoef(x, rowvar=False)
    return np.nan_to_num(c, nan=0.0)


def factores_horn(x: np.ndarray) -> int:
    """Número de factores a retener por análisis paralelo (percentil 95)."""
    n, p = x.shape
    observados = np.sort(np.linalg.eigvalsh(_correlacion(x)))[::-1]
    rng = np.random.default_rng(_SEMILLA)
    aleatorios = np.array([np.sort(np.linalg.eigvalsh(_correlacion(rng.standard_normal((n, p)))))[::-1]
                           for _ in range(_ITERACIONES_HORN)])
    umbral = np.percentile(aleatorios, 95, axis=0)
    k = 0
    while k < p and observados[k] > umbral[k]:
        k += 1
    return k


def _enlace_promedio(r: np.ndarray, k: int) -> list[list[int]]:
    grupos = [[i] for i in range(r.shape[0])]
    distancia = 1.0 - r
    while len(grupos) > k:
        mejor, par = None, (0, 1)
        for a in range(len(grupos)):
            for b in range(a + 1, len(grupos)):
                d = float(np.mean(distancia[np.ix_(grupos[a], grupos[b])]))
                if mejor is None or d < mejor:
                    mejor, par = d, (a, b)
        a, b = par
        grupos[a] = sorted(grupos[a] + grupos[b])
        del grupos[b]
    return sorted(grupos, key=lambda g: g[0])


def factores_kaiser(r: np.ndarray) -> int:
    return int((np.linalg.eigvalsh(r) > 1.0).sum())


def sugerir(matriz: list[list[float | None]], min_items: int = 3, alfa_min: float = 0.60,
            min_casos: int = 30) -> Sugerencia:
    """Grupos de ítems (columnas de `matriz`) que forman escalas (lista vacía si no hay evidencia)."""
    completos = np.array([f for f in matriz if all(v is not None for v in f)], dtype=float)
    if completos.ndim != 2 or completos.shape[0] < min_casos or completos.shape[1] < 2 * min_items:
        return Sugerencia([], 0, 0)
    rangos = _rangos(completos)
    r = _correlacion(rangos)
    kaiser, horn = factores_kaiser(r), factores_horn(rangos)
    k = min(kaiser, completos.shape[1] // min_items)
    if k < 2:
        return Sugerencia([], kaiser, horn)
    validas = []
    for grupo in _enlace_promedio(r, k):
        if len(grupo) < min_items:
            continue
        sub = [[f[j] for j in grupo] for f in completos.tolist()]
        resultado = est.cronbach(sub, [str(j) for j in grupo], min_casos=3)
        if resultado and resultado["alfa"] is not None and resultado["alfa"] >= alfa_min:
            validas.append(Dimension(indices=grupo, alfa=float(resultado["alfa"])))
    return Sugerencia(validas if len(validas) >= 2 else [], kaiser, horn)
