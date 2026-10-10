"""Tests de la función pura `leer_kpis_csv` (diseño §1.5).

No requieren base de datos: solo ejercitan el parser/validador del CSV con
fixtures en disco (caso feliz, cabecera incorrecta, campos obligatorios
vacíos).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.seed_kpis import ErrorValidacionCSV, leer_kpis_csv

_CABECERA = (
    "KPI,Polaridad_Rendimiento,Tipo_Objetivo_Estrategico,Formula_Metrica_Calculo,"
    "Descripcion_Ampliada_Educativa,Comportamiento_Direccional_y_Causalidad,"
    "Razon_Estrategica_y_Decisiones,Texto_Contexto_RAG_Vectorial"
)
_FILA_OK = "KPI A,POSITIVO,Aumentar,formula,significado,comportamiento,razon,texto rag"
_FILA_OK_2 = "KPI B,NEGATIVO,Reducir,formula2,significado2,comp2,razon2,texto rag 2"


def _escribir_csv(tmp_path: Path, lineas: list[str]) -> Path:
    ruta = tmp_path / "kpis.csv"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def test_caso_feliz(tmp_path: Path) -> None:
    ruta = _escribir_csv(tmp_path, [_CABECERA, _FILA_OK, _FILA_OK_2])
    filas = leer_kpis_csv(ruta)
    assert len(filas) == 2
    assert filas[0]["KPI"] == "KPI A"
    assert filas[0]["Texto_Contexto_RAG_Vectorial"] == "texto rag"
    assert filas[1]["KPI"] == "KPI B"


def test_cabecera_incorrecta_aborta(tmp_path: Path) -> None:
    cabecera_mala = _CABECERA.replace("KPI,", "nombre_kpi,")
    ruta = _escribir_csv(tmp_path, [cabecera_mala, _FILA_OK])
    with pytest.raises(ErrorValidacionCSV):
        leer_kpis_csv(ruta)


def test_kpi_vacio_aborta(tmp_path: Path) -> None:
    fila_mala = ",POSITIVO,Aumentar,formula,significado,comportamiento,razon,texto rag"
    ruta = _escribir_csv(tmp_path, [_CABECERA, fila_mala])
    with pytest.raises(ErrorValidacionCSV):
        leer_kpis_csv(ruta)


def test_texto_rag_vacio_aborta(tmp_path: Path) -> None:
    fila_mala = "KPI A,POSITIVO,Aumentar,formula,significado,comportamiento,razon,"
    ruta = _escribir_csv(tmp_path, [_CABECERA, fila_mala])
    with pytest.raises(ErrorValidacionCSV):
        leer_kpis_csv(ruta)
