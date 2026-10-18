"""Fuentes de referencia verificadas de los KPIs (tabla kpi_fuente): en el chat y en el catálogo."""
from __future__ import annotations

import json

import pytest

from shared.models.kpi import KPI
from shared.models.kpi_fuente import KPIFuente
from shared.models.usuario import Usuario
from shared.models.version_conocimiento import VersionConocimiento

import docs_ejemplo
from conftest import token
from services import enrutador

ANA = token(2)


@pytest.fixture()
def acervo(db, storage, chroma):
    enrutador._cache_docs.clear()
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    db.add(KPI(kpi_id=7, nombre="Satisfacción estudiantil", texto_contexto_rag_vectorial="Satisfacción estudiantil"))
    db.flush()
    db.add(KPIFuente(kpi_id=7, organismo="Bain & Company", titulo="Measuring Your Net Promoter Score",
                     url="https://www.netpromotersystem.com/about/measuring-your-net-promoter-score/", nota="Cálculo del NPS."))
    key = "documento/1/1__v1_documento_final.json"
    storage.archivos[key] = (json.dumps(docs_ejemplo.encuesta()).encode("utf-8"), "documento.json")
    db.add(VersionConocimiento(id_crudo=1, version=1, estado="vigente", perfil={}, ruta_documento=key))
    db.commit()
    chroma.crear("instrumentos")
    return db


def test_chat_de_kpi_cita_la_fuente_de_referencia(cliente, acervo, ollama):
    r = cliente.post("/rag/chat", json={"pregunta": "¿Por qué el KPI Satisfacción estudiantil está relacionado y qué mide?",
                                        "stream": False}, headers=ANA).json()
    [ref] = [x for x in r["referencias"] if x["tipo"] == "fuente_kpi"]
    assert ref["titulo"] == "Bain & Company" and ref["url"].startswith("https://www.netpromotersystem.com")
    prompt = ollama["prompts"][-1]
    assert "FUENTES DE REFERENCIA DEL KPI" in prompt and "[Fuente KPI: Bain & Company]" in prompt


def test_se_conserva_la_cita_real_y_se_quita_la_inventada():
    from services import dominio
    from services.rag_service import quitar_citas_inventadas

    real = dominio.Ancla("fuente_kpi", "Bain & Company", "NPS", url="https://x")
    texto = "Mide la satisfacción [Fuente KPI: Bain & Company] según la OCDE [Fuente KPI: OCDE]."
    assert quitar_citas_inventadas(texto, [real]) == "Mide la satisfacción [Fuente KPI: Bain & Company] según la OCDE."


def test_catalogo_de_kpis_incluye_sus_fuentes(cliente, acervo):
    cat = {k["id"]: k for k in cliente.get("/visualizacion/kpis/catalogo", headers=ANA).json()}
    [kpi] = [k for k in cat.values() if k["nombre"] == "Satisfacción estudiantil"]
    assert kpi["fuentes"] == [{"organismo": "Bain & Company", "titulo": "Measuring Your Net Promoter Score",
                               "url": "https://www.netpromotersystem.com/about/measuring-your-net-promoter-score/",
                               "anio": None, "nota": "Cálculo del NPS."}]
