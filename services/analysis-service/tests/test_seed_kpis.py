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


# ── Fuentes de referencia (seed/KPI_Fuentes.csv → tt_rag.kpi_fuente) ──────────


def _sesion():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from shared.db.base import Base
    from shared.models.kpi import KPI
    from shared.models.kpi_fuente import KPIFuente

    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(motor, "connect")
    def _adjuntar(dbapi_conn, _):  # noqa: ANN001
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS tt_rag")

    Base.metadata.create_all(motor, tables=[KPI.__table__, KPIFuente.__table__])
    return sessionmaker(bind=motor)()


def test_csv_de_fuentes_del_repo_es_valido_y_liga_con_el_catalogo() -> None:
    from scripts.seed_kpis import leer_fuentes_csv, ruta_csv_por_defecto, ruta_fuentes_por_defecto

    fuentes = leer_fuentes_csv(ruta_fuentes_por_defecto())
    catalogo = {f["KPI"] for f in leer_kpis_csv(ruta_csv_por_defecto())}
    assert fuentes and {f["KPI"] for f in fuentes} <= catalogo
    assert all(f["URL"].startswith("https://") for f in fuentes)


def test_cargar_fuentes_reemplaza_y_reporta_kpis_inexistentes() -> None:
    from scripts.seed_kpis import cargar_fuentes
    from shared.models.kpi import KPI
    from shared.models.kpi_fuente import KPIFuente

    db = _sesion()
    db.add(KPI(nombre="Tasa de Retención", texto_contexto_rag_vectorial="x"))
    db.commit()
    fila = {"KPI": "Tasa de Retención", "Organismo": "NCES", "Titulo": "COE", "URL": "https://nces.ed.gov", "Anio": "2024", "Nota": ""}
    assert cargar_fuentes(db, [fila, {**fila, "KPI": "No existe"}]) == (1, ["No existe"])
    db.commit()
    assert cargar_fuentes(db, [fila]) == (1, [])  # se reemplaza, no se duplica
    db.commit()
    [f] = db.query(KPIFuente).all()
    assert f.anio == 2024 and f.nota is None


def test_fuente_sin_https_aborta(tmp_path: Path) -> None:
    from scripts.seed_kpis import leer_fuentes_csv

    p = tmp_path / "f.csv"
    p.write_text("KPI,Organismo,Titulo,URL,Anio,Nota\nX,O,T,http://a.b,,\n", encoding="utf-8")
    with pytest.raises(ErrorValidacionCSV):
        leer_fuentes_csv(p)
