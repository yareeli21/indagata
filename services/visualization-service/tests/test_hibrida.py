"""Búsqueda híbrida: significado (Chroma) + palabras (Postgres), combinadas con RRF (services/hibrida.py)."""
from __future__ import annotations

import pytest

from services import hibrida


@pytest.fixture(autouse=True)
def _hibrida_encendida(monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_HIBRIDA", True)


def test_terminos_quita_relleno_y_palabras_de_todo_el_acervo():
    assert hibrida.terminos("¿En qué modalidad cursan su programa?") == ["modalidad", "cursan", "programa"]
    assert hibrida.terminos("¿Cuál es la situación laboral de los estudiantes?") == ["situacion", "laboral"]


def test_cobertura_compara_raices():
    terminos = hibrida.terminos("¿En qué modalidad cursan su programa?")
    cob, halladas = hibrida.cobertura(terminos, "Pregunta p03: ¿En qué modalidad cursas tu programa? Opciones: …")
    assert (cob, halladas) == (1.0, 3)
    cob, halladas = hibrida.cobertura(terminos, "Instrumento: Simulación. Objetivo: evaluar la satisfacción")
    assert halladas == 0


def test_pasa_por_palabras_o_por_significado(monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.65)
    monkeypatch.setattr(settings, "RAG_MIN_COBERTURA", 0.75)
    assert hibrida.relevante({"score": 0.46, "coincidencia": 1.0, "palabras": 3})  # casi literal, coseno bajo
    assert hibrida.relevante({"score": 0.70, "coincidencia": 0.0, "palabras": 0})  # por significado
    assert not hibrida.relevante({"score": 0.46, "coincidencia": 0.5, "palabras": 1})
    assert not hibrida.relevante({"score": 0.46, "coincidencia": 1.0, "palabras": 1})  # una sola palabra no basta


def test_rrf_premia_lo_que_aparece_en_las_dos_listas():
    orden = hibrida.fusionar(["a", "b", "c"], ["c", "d"])
    assert orden[0] == "c" and set(orden) == {"a", "b", "c", "d"}


class _Coleccion:
    """Chroma mínima: tres fragmentos; la búsqueda semántica pone primero la ficha."""

    puntos = {
        "ficha": ({"seccion": "encabezado", "instrumentoId": "1"}, "Instrumento: Simulación. Objetivo: satisfacción",
                  [1.0, 0.0]),
        "p03": ({"seccion": "pregunta", "instrumentoId": "1"}, "Pregunta p03: ¿En qué modalidad cursas tu programa?",
                [0.4, 0.9]),
        "p15": ({"seccion": "pregunta", "instrumentoId": "1"}, "Pregunta p15: ¿Cuál es tu situación laboral actual?",
                [0.5, 0.8]),
    }

    def query(self, query_embeddings, n_results, where=None, include=None):  # noqa: ANN001
        sel = ["ficha", "p15"][:n_results]
        return {"ids": [sel], "metadatas": [[self.puntos[i][0] for i in sel]],
                "documents": [[self.puntos[i][1] for i in sel]], "distances": [[0.3, 0.6]]}

    def get(self, ids, include=None):  # noqa: ANN001
        return {"ids": ids, "metadatas": [self.puntos[i][0] for i in ids], "documents": [self.puntos[i][1] for i in ids],
                "embeddings": [self.puntos[i][2] for i in ids]}


def test_la_busqueda_por_palabras_trae_lo_que_el_embedding_no_ve(monkeypatch):
    monkeypatch.setattr(hibrida, "_lexicos", lambda fabrica, palabras, ids, limite: ["p03"])
    res = hibrida.consultar(_Coleccion(), [1.0, 0.0], "¿En qué modalidad cursan su programa?", 2, None, ["1"],
                            fabrica_sesiones=lambda: None)
    ids = res["ids"][0]
    assert "p03" in ids  # no estaba en la búsqueda semántica
    n = ids.index("p03")
    assert res["coincidencias"][0][n] == 1.0 and res["palabras"][0][n] == 3
    assert res["rangos"][0][n] == {"semantica": None, "palabras": 1}
    assert 0.0 < 1.0 - res["distances"][0][n] < 1.0  # su coseno se calcula con el embedding guardado


def test_sin_postgres_queda_la_busqueda_semantica(monkeypatch):
    def falla(*_a, **_k):  # noqa: ANN002, ANN003
        raise RuntimeError("sin to_tsvector")

    monkeypatch.setattr(hibrida, "_lexicos", falla)
    res = hibrida.consultar(_Coleccion(), [1.0, 0.0], "¿En qué modalidad cursan su programa?", 2, None, [],
                            fabrica_sesiones=lambda: None)
    assert res["ids"][0] == ["ficha", "p15"]


def test_bm25_pesa_mas_la_palabra_rara_que_la_comun():
    palabras = ["modalidad", "programa"]
    filas = [("p03", "Pregunta p03: ¿En qué modalidad cursas tu programa?", "1", "pregunta"),
             ("p01", "Pregunta p01: La oferta de programas y programas de posgrado", "1", "pregunta")]
    puntajes = {i: s for s, i, _, _ in hibrida._bm25(palabras, filas, {"modalidad": 3, "programa": 900}, 1000)}
    assert puntajes["p03"] > puntajes["p01"]


def test_la_ficha_solo_cuenta_si_comparte_palabras(monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.65)
    assert not hibrida.relevante({"seccion": "encabezado", "score": 0.67, "coincidencia": 0.25, "palabras": 1})
    assert hibrida.relevante({"seccion": "encabezado", "score": 0.67, "coincidencia": 0.5, "palabras": 1})
    assert hibrida.relevante({"seccion": "pregunta", "score": 0.67, "coincidencia": 0.0, "palabras": 0})
    # Igual los KPI: «¿En qué modalidad cursan su programa?» traía un KPI con 0.65 y 33 % de las palabras.
    assert not hibrida.relevante({"seccion": "kpi", "score": 0.65, "coincidencia": 0.33, "palabras": 1})
    assert hibrida.relevante({"seccion": "kpi", "score": 0.70, "coincidencia": 0.5, "palabras": 1})


def test_apagada_es_solo_semantica(monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_HIBRIDA", False)
    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.65)
    assert not hibrida.relevante({"score": 0.46, "coincidencia": 1.0, "palabras": 3})
    assert hibrida.relevante({"seccion": "encabezado", "score": 0.67, "coincidencia": 0.0, "palabras": 0})
