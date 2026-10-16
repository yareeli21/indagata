"""Pruebas del vector con el que se buscan KPIs para un instrumento."""
from __future__ import annotations

import math

from app.vectorization.core.kpi_search import vector_instrumento
from app.vectorization.core.summary_builder import VENTANA_FRAGMENTO, trocear_instrumento


def test_trocear_quita_lineas_decorativas_y_respeta_la_ventana():
    texto = (
        "======================================================================\n"
        "INSTRUMENTO: Inventario de Estrategias de Aprendizaje\n"
        "----------------------------------------------------------------------\n"
        + "".join(
            f"{n}. Organizo el material de estudio antes de comenzar la sesión número {n}.\n"
            "   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5\n"
            for n in range(1, 30)
        )
        + ("palabra " * 120)
    )
    fragmentos = trocear_instrumento(texto)
    assert len(fragmentos) > 1
    assert all(len(f) <= VENTANA_FRAGMENTO for f in fragmentos)
    unido = "\n".join(fragmentos)
    assert "=====" not in unido and "-----" not in unido and "[ ]" not in unido
    assert fragmentos[0].startswith("INSTRUMENTO: Inventario")


def test_vector_instrumento_mezcla_y_normaliza():
    summary = [1.0, 0.0, 0.0]
    fragmentos = [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    v = vector_instrumento(summary, fragmentos, peso_summary=0.3)
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0)
    # El centroide pesa más que el summary.
    assert v[1] > v[0] and math.isclose(v[1], v[2])


def test_vector_instrumento_sin_fragmentos_es_el_summary():
    assert vector_instrumento([0.6, 0.8], []) == [0.6, 0.8]
