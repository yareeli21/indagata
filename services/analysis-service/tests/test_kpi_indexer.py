"""Pruebas de la colección `kpis`: qué se vectoriza y qué viaja como metadata."""
from __future__ import annotations

from shared.models.kpi import KPI

from app.vectorization.core import kpi_indexer

_KPI = KPI(
    kpi_id=7,
    nombre="Tasa de retención",
    polaridad_rendimiento="POSITIVO (Maximizar)",
    tipo_objetivo_estrategico="Aumentar / Mejorar",
    formula_metrica_calculo="(Reinscritos / Inscritos) * 100",
    descripcion_ampliada_educativa="Porcentaje de estudiantes que continúan.",
    comportamiento_direccional_causalidad="SI AUMENTA: mayor estabilidad.",
    razon_estrategica_decisiones="Orienta programas de tutoría.",
    texto_contexto_rag_vectorial="El KPI Tasa de retención mide la permanencia estudiantil.",
)


def test_solo_se_vectoriza_el_texto_contexto_rag():
    assert kpi_indexer.build_kpi_text(_KPI) == _KPI.texto_contexto_rag_vectorial


def test_las_demas_columnas_van_como_metadata():
    meta = kpi_indexer.build_kpi_metadata(_KPI)
    assert meta == {
        "kpi_id": 7,
        "nombre": "Tasa de retención",
        "polaridad_rendimiento": "POSITIVO (Maximizar)",
        "tipo_objetivo_estrategico": "Aumentar / Mejorar",
        "formula_metrica_calculo": "(Reinscritos / Inscritos) * 100",
        "descripcion_ampliada_educativa": "Porcentaje de estudiantes que continúan.",
        "comportamiento_direccional_causalidad": "SI AUMENTA: mayor estabilidad.",
        "razon_estrategica_decisiones": "Orienta programas de tutoría.",
    }
    assert "texto_contexto_rag_vectorial" not in meta
