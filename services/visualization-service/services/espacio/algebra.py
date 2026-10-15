"""Álgebra del espacio vectorial con numpy: PCA, k-means esférico y coseno.

Todo lo que mide parecido (vecinos, clusters, asignaciones) se calcula sobre los
embeddings ORIGINALES normalizados; la proyección 2D es solo para dibujar.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def normalizar_filas(matriz: np.ndarray) -> np.ndarray:
    """Normaliza cada fila a norma 1 (las filas nulas se dejan en cero)."""
    normas = np.linalg.norm(matriz, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return matriz / normas


def similitudes(consulta: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    """Coseno entre un vector y cada fila (ambos se normalizan)."""
    if matriz.size == 0:
        return np.zeros(0)
    q = consulta / (np.linalg.norm(consulta) or 1.0)
    return normalizar_filas(matriz) @ q


@dataclass(frozen=True)
class Proyeccion:
    """PCA ajustado: misma transformación para KPIs, instrumentos, chunks y consultas."""

    media: np.ndarray
    componentes: np.ndarray  # (2, d)
    varianza: tuple[float, float]  # proporción de varianza explicada por PC1 y PC2

    @property
    def varianza_total(self) -> float:
        return float(sum(self.varianza))

    def proyectar(self, matriz: np.ndarray) -> np.ndarray:
        if matriz.size == 0:
            return np.zeros((0, 2))
        return (np.atleast_2d(matriz) - self.media) @ self.componentes.T


def ajustar_pca(matriz: np.ndarray) -> Proyeccion:
    """PCA a 2 componentes por SVD del conjunto centrado.

    El signo de cada componente se fija (carga de mayor magnitud positiva) para
    que el mapa no se «voltee» entre recálculos con los mismos datos.
    """
    n, d = matriz.shape
    media = matriz.mean(axis=0)
    componentes = np.zeros((2, d))
    varianza = (0.0, 0.0)
    if n >= 2:
        centrada = matriz - media
        _, s, vt = np.linalg.svd(centrada, full_matrices=False)
        var = (s**2) / (n - 1)
        total = float(var.sum()) or 1.0
        k = min(2, vt.shape[0])
        componentes[:k] = vt[:k]
        for i in range(k):
            if componentes[i, np.argmax(np.abs(componentes[i]))] < 0:
                componentes[i] *= -1
        ratios = [float(var[i] / total) if i < k else 0.0 for i in range(2)]
        varianza = (ratios[0], ratios[1])
    return Proyeccion(media=media, componentes=componentes, varianza=varianza)


def kmeans_esferico(
    matriz: np.ndarray, k: int, semilla: int = 7, iteraciones: int = 60, intentos: int = 10
) -> tuple[np.ndarray, np.ndarray]:
    """k-means con similitud coseno (vectores normalizados), inicialización k-means++.

    Una sola inicialización puede caer en un óptimo local, así que se prueban
    `intentos` semillas y se conserva la solución más cohesiva (mayor suma de
    similitudes con su centroide). Devuelve (etiquetas, centroides normalizados);
    es determinista para una misma `semilla`.
    """
    x = normalizar_filas(matriz)
    mejor: tuple[float, np.ndarray, np.ndarray] | None = None
    for intento in range(max(1, intentos)):
        etiquetas, centroides = _kmeans_una_vez(x, k, semilla + intento, iteraciones)
        cohesion = float(np.sum(np.max(x @ centroides.T, axis=1)))
        if mejor is None or cohesion > mejor[0] + 1e-9:
            mejor = (cohesion, etiquetas, centroides)
    assert mejor is not None
    return mejor[1], mejor[2]


def _kmeans_una_vez(x: np.ndarray, k: int, semilla: int, iteraciones: int) -> tuple[np.ndarray, np.ndarray]:
    n = x.shape[0]
    k = max(1, min(k, n))
    rng = np.random.default_rng(semilla)
    centroides = [x[rng.integers(n)]]
    for _ in range(1, k):
        dist = 1 - np.max(x @ np.asarray(centroides).T, axis=1)
        dist = np.clip(dist, 0, None)
        prob = dist / dist.sum() if dist.sum() > 0 else np.full(n, 1 / n)
        centroides.append(x[rng.choice(n, p=prob)])
    c = np.asarray(centroides)
    etiquetas = np.zeros(n, dtype=int)
    for _ in range(iteraciones):
        nuevas = np.argmax(x @ c.T, axis=1)
        if np.array_equal(nuevas, etiquetas) and _ > 0:
            break
        etiquetas = nuevas
        for j in range(k):
            miembros = x[etiquetas == j]
            if len(miembros):
                c[j] = miembros.mean(axis=0)
        c = normalizar_filas(c)
    return etiquetas, c


def k_sugerido(n: int) -> int:
    """Número de clusters para n KPIs: ≈ √(n/2), acotado a 3–8 (y a n)."""
    if n <= 0:
        return 0
    return int(min(n, max(3, min(8, round((n / 2) ** 0.5)))))
