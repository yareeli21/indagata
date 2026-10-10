"""Tests del motor de score híbrido del grafo de recomendación.

Cubre:
  (a) `_jaccard` puro (incluye unión vacía → 0.0).
  (b) `_etiquetar_razon` sobre las 5 ramas de design §2.3.
  (c) combinación de score y clamp de `top_n`.
  (d) integración de `sim_semantica` con un cliente Chroma efímero sembrado.
  (e) degradación: cliente cuyo `query` lanza → `degradado_semantico is True` y
      aún devuelve recomendaciones por KPI.

Para no depender de Postgres, `cargar_acervo` se sustituye por un stub que
devuelve `_Instrumento` conocidos (monkeypatch), que es la frontera entre el IO de
BD y la lógica pura del motor.
"""
from __future__ import annotations

import chromadb
import pytest

from app.vectorization.core import grafo_recomendador as gr
from app.vectorization.core.grafo_recomendador import (
    UMBRAL_ALTO,
    _etiquetar_razon,
    _jaccard,
    _Instrumento,
)
from shared.db.core.config import settings


# ── (a) Jaccard ───────────────────────────────────────────────────────────────


def test_jaccard_union_vacia_es_cero() -> None:
    assert _jaccard(set(), set()) == 0.0


def test_jaccard_sin_interseccion() -> None:
    assert _jaccard({1, 2}, {3, 4}) == 0.0


def test_jaccard_valor_conocido() -> None:
    # |∩| = 1 (el 2), |∪| = 3 (1,2,3) → 1/3.
    assert _jaccard({1, 2}, {2, 3}) == pytest.approx(1 / 3)


def test_jaccard_conjuntos_iguales() -> None:
    assert _jaccard({1, 2, 3}, {1, 2, 3}) == 1.0


# ── (b) Etiquetado de razón (design §2.3) ───────────────────────────────────────


def test_razon_alta_afinidad() -> None:
    # Ambos scores >= UMBRAL_ALTO.
    assert _etiquetar_razon(0.8, 0.7, ["A"]) == "Alta afinidad (contenido + KPIs)"


def test_razon_kpis_compartidos_cuando_kpi_domina_o_empata() -> None:
    # Hay compartidos y score_kpi >= score_semantico (sin ambos altos).
    assert _etiquetar_razon(0.2, 0.4, ["A", "B"]) == "KPIs compartidos: A, B"
    # Empate con compartidos → prefiere KPIs compartidos (evita falso "contenido").
    assert _etiquetar_razon(0.3, 0.3, ["A"]) == "KPIs compartidos: A"


def test_razon_contenido_similar_cuando_semantico_domina() -> None:
    # Semántico estrictamente mayor y por debajo del umbral alto.
    assert _etiquetar_razon(0.4, 0.1, ["A"]) == "Contenido similar"


def test_razon_kpis_compartidos_rama_final() -> None:
    # score_semantico == score_kpi == 0 pero hay compartidos → KPIs compartidos.
    assert _etiquetar_razon(0.0, 0.0, ["X"]) == "KPIs compartidos: X"


def test_razon_contenido_similar_sin_compartidos() -> None:
    assert _etiquetar_razon(0.0, 0.0, []) == "Contenido similar"


def test_umbral_alto_es_medio_punto() -> None:
    assert UMBRAL_ALTO == 0.5


# ── Infraestructura compartida para (c), (d), (e) ───────────────────────────────


def _instrumento(id_inst: int, id_crudo: int, kpis: dict[int, str], owner: int = 1) -> _Instrumento:
    return _Instrumento(
        id_instrumento=id_inst,
        id_crudo=id_crudo,
        titulo=f"Instrumento {id_inst}",
        tipo_raw="encuesta",
        id_owner=owner,
        autor_nombre="Autor",
        kpis=dict(kpis),
    )


def _sembrar_acervo(monkeypatch, acervo: list[_Instrumento]) -> None:
    monkeypatch.setattr(gr, "cargar_acervo", lambda _db: list(acervo))


# ── (c) Combinación de score y clamp de top_n ───────────────────────────────────


def test_score_combinado_solo_kpi(monkeypatch) -> None:
    # Dos candidatos con distinto solape de KPIs; sin Chroma (w_sem=0) para aislar.
    activo = _instrumento(1, 10, {100: "A", 101: "B"})
    cand_alto = _instrumento(2, 20, {100: "A", 101: "B"})  # Jaccard = 1.0
    cand_bajo = _instrumento(3, 30, {100: "A", 999: "Z"})  # Jaccard = 1/3
    _sembrar_acervo(monkeypatch, [activo, cand_alto, cand_bajo])

    recos, _params, degradado = gr.recomendar(
        db=None, instrumento_ids=[1], w_sem=0.0, w_kpi=1.0, min_score=0.0
    )
    assert degradado is False  # sin vectores sembrados, sim=0 pero no "falla"
    assert [r.id for r in recos] == ["2", "3"]  # ordenado por score desc
    assert recos[0].score_kpi == pytest.approx(1.0)
    assert recos[1].score_kpi == pytest.approx(1 / 3, abs=1e-3)  # redondeado a 4 decimales
    assert recos[0].kpis_compartidos == ["A", "B"]


def test_min_score_filtra(monkeypatch) -> None:
    activo = _instrumento(1, 10, {100: "A", 101: "B", 102: "C"})
    # Candidato con Jaccard = 1/3 ≈ 0.333.
    cand = _instrumento(2, 20, {100: "A", 777: "Z", 888: "Y"})
    _sembrar_acervo(monkeypatch, [activo, cand])

    recos, _p, _d = gr.recomendar(
        db=None, instrumento_ids=[1], w_sem=0.0, w_kpi=1.0, min_score=0.5
    )
    assert recos == []  # 0.333 < 0.5 → filtrado


def test_top_n_clamp(monkeypatch) -> None:
    activo = _instrumento(1, 10, {100: "A"})
    candidatos = [_instrumento(i, i * 10, {100: "A"}) for i in range(2, 8)]
    _sembrar_acervo(monkeypatch, [activo, *candidatos])

    recos, params, _d = gr.recomendar(
        db=None, instrumento_ids=[1], w_sem=0.0, w_kpi=1.0, min_score=0.0, top_n=999
    )
    assert params["top_n"] == 100  # clamp superior
    assert len(recos) == 6  # pero no hay más de 6 candidatos

    recos2, params2, _d2 = gr.recomendar(
        db=None, instrumento_ids=[1], w_sem=0.0, w_kpi=1.0, min_score=0.0, top_n=0
    )
    assert params2["top_n"] == 1  # clamp inferior
    assert len(recos2) == 1


def test_excluir_propios(monkeypatch) -> None:
    activo = _instrumento(1, 10, {100: "A"}, owner=5)
    propio = _instrumento(2, 20, {100: "A"}, owner=5)
    ajeno = _instrumento(3, 30, {100: "A"}, owner=9)
    _sembrar_acervo(monkeypatch, [activo, propio, ajeno])

    recos, _p, _d = gr.recomendar(
        db=None,
        instrumento_ids=[1],
        autor_id=5,
        w_sem=0.0,
        w_kpi=1.0,
        min_score=0.0,
        excluir_propios=True,
    )
    assert [r.id for r in recos] == ["3"]  # el propio (owner=5) queda excluido


# ── (d) Integración semántica con Chroma efímero ────────────────────────────────


def test_sim_semantica_con_cliente_efimero(monkeypatch) -> None:
    cliente = chromadb.EphemeralClient()
    coleccion = cliente.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_SUMMARY, metadata={"hnsw:space": "cosine"}
    )
    # Vectores conocidos: el activo (id=1) es idéntico al candidato 2 (dist≈0 → sim≈1)
    # y ortogonal al candidato 3 (dist≈1 → sim≈0).
    coleccion.upsert(
        ids=["1", "2", "3"],
        embeddings=[[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
        documents=["a", "b", "c"],
        metadatas=[
            {"id_instrumento": 1},
            {"id_instrumento": 2},
            {"id_instrumento": 3},
        ],
    )

    activo = _instrumento(1, 10, {})
    cand_igual = _instrumento(2, 20, {})
    cand_ortogonal = _instrumento(3, 30, {})
    _sembrar_acervo(monkeypatch, [activo, cand_igual, cand_ortogonal])

    recos, _p, degradado = gr.recomendar(
        db=None,
        instrumento_ids=[1],
        w_sem=1.0,
        w_kpi=0.0,
        min_score=0.0,
        client=cliente,
    )
    assert degradado is False
    por_id = {r.id: r for r in recos}
    assert por_id["2"].score_semantico == pytest.approx(1.0, abs=1e-3)
    assert por_id["3"].score_semantico == pytest.approx(0.0, abs=1e-3)
    assert por_id["2"].razon == "Contenido similar"


# ── (e) Degradación semántica ───────────────────────────────────────────────────


class _ClienteQueFalla:
    """Cliente Chroma cuyo acceso a colección lanza (simula Chroma caído)."""

    def get_or_create_collection(self, *_args, **_kwargs):
        raise RuntimeError("Chroma no disponible")


def test_degradacion_responde_solo_kpi(monkeypatch) -> None:
    activo = _instrumento(1, 10, {100: "A", 101: "B"})
    cand = _instrumento(2, 20, {100: "A", 101: "B"})  # Jaccard = 1.0
    _sembrar_acervo(monkeypatch, [activo, cand])

    recos, params, degradado = gr.recomendar(
        db=None,
        instrumento_ids=[1],
        w_sem=0.6,
        w_kpi=0.4,
        min_score=0.0,
        client=_ClienteQueFalla(),
    )
    assert degradado is True
    assert params["w_sem"] == 0.0  # peso semántico forzado a 0
    assert len(recos) == 1
    assert recos[0].score_semantico == 0.0
    # Solo-KPI: score == w_kpi * jaccard == 0.4 * 1.0.
    assert recos[0].score == pytest.approx(0.4)
    assert recos[0].razon == "KPIs compartidos: A, B"
