"""Fórmula de asociación KPI ↔ instrumento a partir de las unidades del perfil.

Para cada KPI k (vector leído de la colección `kpis`, sin reindexar):

    g   = cos(U₀, k)                       similitud con el perfil general
    sᵢ  = cos(Uᵢ, k)                       similitud con cada pregunta
    E_k = {i : sᵢ ≥ τ_e}                   preguntas que lo sustentan (evidencia; τ_e = 0.45)
    p   = media de las 3 sᵢ más altas      (o de las que haya)
    c   = min(1, |E_k| / 3)                cobertura: varias preguntas lo respaldan

    score_k = w_g·g + w_p·p + w_c·c        (por defecto 0.45 / 0.45 / 0.10)
    sin unidades de pregunta:  score_k = g

Por qué así:
  - g captura el propósito declarado del instrumento;
  - p premia que existan preguntas que de verdad miden el KPI, y usar el top 3
    evita que una sola frase casual decida;
  - c desempata a favor de los KPIs con respaldo en varias preguntas.

Candidatos: la unión del top 10 por g y del top 3 de cada pregunta; se devuelven
los de score ≥ umbral, como máximo `max_propuestas`. Pesos y umbrales vienen de
la configuración (shared settings), así que se ajustan sin tocar código.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

_TOP_GENERAL = 10
_TOP_POR_PREGUNTA = 3
_TOP_P = 3
_MAX_EVIDENCIA = 5


@dataclass(frozen=True)
class Pesos:
    general: float = 0.45
    preguntas: float = 0.45
    cobertura: float = 0.10
    umbral_evidencia: float = 0.45
    umbral_score: float = 0.30
    max_propuestas: int = 8


@dataclass
class Evidencia:
    pregunta_id: str
    similitud: float


@dataclass
class Propuesta:
    kpi_id: int
    score: float
    g: float
    p: float
    c: float
    evidencia: list[Evidencia] = field(default_factory=list)

    @property
    def componentes(self) -> dict[str, float]:
        return {"g": self.g, "p": self.p, "c": self.c}


def _normalizar(m: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(m, axis=-1, keepdims=True)
    normas[normas == 0] = 1.0
    return m / normas


def asociar(
    vector_general: list[float],
    vectores_preguntas: list[tuple[str, list[float]]],
    kpis: list[tuple[int, list[float]]],
    pesos: Pesos = Pesos(),
) -> list[Propuesta]:
    """Propuestas de KPI ordenadas por score (desc), ya filtradas por umbral."""
    if not kpis:
        return []
    ids_kpi = [k for k, _ in kpis]
    K = _normalizar(np.asarray([v for _, v in kpis], dtype=float))  # (nk, d)
    g = K @ _normalizar(np.asarray(vector_general, dtype=float))  # (nk,)
    if vectores_preguntas:
        Q = _normalizar(np.asarray([v for _, v in vectores_preguntas], dtype=float))  # (nq, d)
        S = Q @ K.T  # (nq, nk): similitud de cada pregunta con cada KPI
    else:
        S = np.zeros((0, len(kpis)))

    candidatos = set(np.argsort(-g)[:_TOP_GENERAL].tolist())
    for fila in S:
        candidatos.update(np.argsort(-fila)[:_TOP_POR_PREGUNTA].tolist())

    propuestas: list[Propuesta] = []
    for j in candidatos:
        gj = float(np.clip(g[j], 0.0, 1.0))
        if S.shape[0]:
            columna = np.clip(S[:, j], 0.0, 1.0)
            orden = np.argsort(-columna)
            pj = float(columna[orden[:_TOP_P]].mean())
            soporte = [int(i) for i in orden if columna[i] >= pesos.umbral_evidencia]
            cj = min(1.0, len(soporte) / 3)
            score = pesos.general * gj + pesos.preguntas * pj + pesos.cobertura * cj
            # Si ninguna pregunta pasa el umbral se muestran las 2 más cercanas (con su
            # similitud, para que el investigador vea que el respaldo es débil); no suman cobertura.
            mostradas = soporte[:_MAX_EVIDENCIA] or [int(i) for i in orden[:2]]
            evidencia = [Evidencia(vectores_preguntas[i][0], round(float(columna[i]), 4)) for i in mostradas]
        else:
            pj, cj, score, evidencia = 0.0, 0.0, gj, []
        if score < pesos.umbral_score:
            continue
        propuestas.append(
            Propuesta(ids_kpi[j], round(score, 4), round(gj, 4), round(pj, 4), round(cj, 4), evidencia)
        )
    propuestas.sort(key=lambda x: (-x.score, x.kpi_id))
    return propuestas[: pesos.max_propuestas]
