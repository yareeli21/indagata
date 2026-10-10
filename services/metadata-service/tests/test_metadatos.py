"""Pruebas del flujo de metadatos: propuesta → aprobación del autor → ingesta → KPIs."""
from __future__ import annotations

from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.kpi import KPI
from shared.models.kpi_inferido import KPIInferido
from shared.models.metadatos_dc import MetadatosDC
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas
from shared.models.metadatos_pruebasestandarizadas import MetadatosEnriquecidosPruebas

BLOQUE_A = "Indica qué tan de acuerdo estás con las siguientes afirmaciones sobre tu escuela"
BLOQUE_B = "Indica qué tan de acuerdo estás con las siguientes afirmaciones sobre cómo estudias"
ENCUESTA_CSV = (
    f'Marca temporal,Carrera,"{BLOQUE_A} [Me gusta mi escuela]","{BLOQUE_A} [Me siento orgulloso]",'
    f'"{BLOQUE_B} [Relaciono lo nuevo con lo que sé]",Edad\n'
    "2024-09-01,Pedagogía,De acuerdo,Totalmente de acuerdo,En desacuerdo,21\n"
    "2024-09-01,Derecho,Totalmente de acuerdo,De acuerdo,De acuerdo,22\n"
    "2024-09-02,Pedagogía,Ni de acuerdo ni en desacuerdo,De acuerdo,Totalmente en desacuerdo,20\n"
    "2024-09-02,Pedagogía,De acuerdo,,De acuerdo,23\n"
)


def _dc_completo(**cambios):
    dc = {
        "dc_title": "Compromiso escolar",
        "dc_creator": "Ana Beltrán",
        "dc_subject": "compromiso, escuela",
        "dc_description": "Mide el compromiso escolar de estudiantes universitarios.",
        "dc_type": "Encuesta",
        "dc_date": "2024-09-01",
        "dc_language": "es",
        "dc_coverage": "Licenciatura — Estudiantes de Pedagogía y Derecho",
        "dc_publisher": "Indagata",
        "dc_rights": "Uso académico",
        "dc_format": "text/csv",
        "dc_source": "compromiso.csv",
        "dc_relation": "",
    }
    dc.update(cambios)
    return dc


ENCUESTA_ESPECIFICOS = {
    "n_respondentes": "4",
    "n_poblacion": "120",
    "objetivo": "Medir el compromiso escolar.",
    "carrera": "Pedagogía, Derecho",
    "poblacion_objetivo": "Estudiantes de licenciatura",
    "constructo_principal": "Compromiso escolar",
    "palabras_clave": "compromiso, escuela, estudio",
    "dimensiones": "Tu escuela, Cómo estudias",
}


def test_propuesta_dublin_core_de_una_encuesta(cliente, ana, crear_instrumento):
    id_crudo = crear_instrumento("compromiso_escolar.csv", ENCUESTA_CSV)
    r = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    v, origen = cuerpo["valores"], cuerpo["origen"]
    assert cuerpo["aprobado"] is False and cuerpo["tabla"] == "metadatos_dc"
    assert v["dc_creator"] == "Ana Beltrán" and origen["dc_creator"] == "automatico"
    assert v["dc_type"] == "Encuesta"
    assert v["dc_format"] == "text/csv"
    assert v["dc_source"] == "compromiso_escolar.csv"
    assert v["dc_title"] == "Compromiso escolar"
    assert v["dc_language"] == "es"
    assert v["dc_coverage"].startswith("Licenciatura")
    assert "4 respondentes" in v["dc_description"]
    assert v["dc_subject"]
    assert "dc_relation" not in cuerpo["obligatorios"] and "dc_title" in cuerpo["obligatorios"]
    assert len(cuerpo["campos"]) == 13


def test_propuesta_enriquecida_de_encuesta(cliente, ana, crear_instrumento, llm):
    id_crudo = crear_instrumento("compromiso.csv", ENCUESTA_CSV)
    llm["respuesta"] = {"constructo_principal": "Compromiso escolar", "objetivo": "Conocer el compromiso."}
    r = cliente.get(f"/api/enrichment/{id_crudo}/propuesta", params={"usar_llm": "true"}, headers=ana)
    assert r.status_code == 200, r.text
    v, origen = r.json()["valores"], r.json()["origen"]
    assert v["n_respondentes"] == 4
    assert v["dimensiones"] == ["Tu escuela", "Cómo estudias"]
    assert v["carrera"] == "Pedagogía, Derecho"
    assert v["poblacion_objetivo"] == "Estudiantes de Pedagogía, Derecho"
    assert "Calidad de los datos" in v["notas_contextuales"]
    assert v["constructo_principal"] == "Compromiso escolar" and origen["constructo_principal"] == "llm"
    assert origen["n_respondentes"] == "inferido"
    # El LLM solo recibe campos vacíos o de plantilla (no los ya inferidos).
    assert "dimensiones" not in llm["llamadas"][0]
    assert "constructo_principal" in llm["llamadas"][0]


def test_solo_el_autor_o_un_admin(cliente, ana, luis, admin, crear_instrumento):
    id_crudo = crear_instrumento("a.csv", ENCUESTA_CSV)
    assert cliente.get(f"/api/metadata/{id_crudo}/propuesta").status_code == 401
    r = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=luis)
    assert r.status_code == 403
    assert cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=admin).status_code == 200
    assert cliente.get("/api/metadata/999/propuesta", headers=ana).status_code == 404


def test_no_se_aprueba_con_campos_faltantes(cliente, ana, crear_instrumento, db):
    id_crudo = crear_instrumento("a.csv", ENCUESTA_CSV)
    payload = {"dublin_core": _dc_completo(dc_description="  "), "enriquecidos": {**ENCUESTA_ESPECIFICOS, "objetivo": ""}}
    r = cliente.post(f"/api/metadata/{id_crudo}/aprobar", json=payload, headers=ana)
    assert r.status_code == 422
    assert "Descripción" in r.json()["detail"] and "Objetivo" in r.json()["detail"]
    assert db.get(MetadatosDC, id_crudo) is None

    vista = cliente.post(f"/api/metadata/{id_crudo}/vista-previa", json=payload, headers=ana).json()
    assert vista["valido"] is False
    assert set(vista["errores"]["dublin_core"]) == {"dc_description"}
    assert set(vista["errores"]["enriquecidos"]) == {"objetivo"}


def test_aprobacion_persiste_genera_json_e_ingesta(cliente, ana, crear_instrumento, db, storage):
    id_crudo = crear_instrumento("compromiso.csv", ENCUESTA_CSV)
    payload = {"dublin_core": _dc_completo(), "enriquecidos": ENCUESTA_ESPECIFICOS}
    r = cliente.post(f"/api/metadata/{id_crudo}/aprobar", json=payload, headers=ana)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["aprobado"] is True
    assert cuerpo["ingesta"] == {"indexado": True, "chunks": 7, "motivo": None}
    assert storage.indexados == [id_crudo]

    db.expire_all()
    dc = db.get(MetadatosDC, id_crudo)
    assert dc.dc_title == "Compromiso escolar" and dc.dc_relation is None
    esp = db.get(MetadatosEnriquecidosEncuestas, id_crudo)
    assert esp.n_respondentes == 4 and esp.n_poblacion == 120
    assert esp.palabras_clave == ["compromiso", "escuela", "estudio"]
    procesado = db.query(InstrumentoProcesado).filter_by(id_crudo=id_crudo).one()
    assert procesado.estado == "estandarizado"
    assert procesado.fecha_aprobado is not None
    assert procesado.ruta_json == f"/app/storage/json/{id_crudo}/1__x.json"

    data = storage.json[(id_crudo, "metadata")][-1]
    assert data["metadata"]["dublin_core"]["dc:title"] == "Compromiso escolar"
    assert data["metadata"]["survey_specific"]["constructo_principal"] == "Compromiso escolar"
    secciones = data["instrument"]["sections"]
    assert [s["name"] for s in secciones] == ["Reactivos", BLOQUE_A, BLOQUE_B]
    q2 = secciones[1]["questions"][0]
    assert q2["text"] == "Me gusta mi escuela" and q2["type"] == "likert"
    assert q2["options"][-1] == "Totalmente de acuerdo"
    assert data["statistics"]["per_question"]["q2"]["distribution"]["De acuerdo"] == 2
    assert data["approval"]["aprobado_por"] == "Ana Beltrán"
    assert "Me gusta mi escuela" in cuerpo["texto_instrumento"]

    # Después de aprobar, la propuesta devuelve lo aprobado.
    prop = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana).json()
    assert prop["aprobado"] is True and prop["origen"]["dc_title"] == "aprobado"


def test_reaprobar_sobrescribe(cliente, ana, crear_instrumento, db, storage):
    id_crudo = crear_instrumento("a.csv", ENCUESTA_CSV)
    payload = {"dublin_core": _dc_completo(), "enriquecidos": ENCUESTA_ESPECIFICOS}
    cliente.post(f"/api/metadata/{id_crudo}/aprobar", json=payload, headers=ana)
    payload["dublin_core"]["dc_title"] = "Compromiso escolar 2024"
    r = cliente.post(f"/api/metadata/{id_crudo}/aprobar", json=payload, headers=ana)
    assert r.status_code == 200
    db.expire_all()
    assert db.get(MetadatosDC, id_crudo).dc_title == "Compromiso escolar 2024"
    assert len(storage.json[(id_crudo, "metadata")]) == 2


def test_aprobacion_sobrevive_a_fallo_de_ingesta(cliente, ana, crear_instrumento, storage):
    storage.fallar_indice = True
    id_crudo = crear_instrumento("a.csv", ENCUESTA_CSV)
    payload = {"dublin_core": _dc_completo(), "enriquecidos": ENCUESTA_ESPECIFICOS}
    r = cliente.post(f"/api/metadata/{id_crudo}/aprobar", json=payload, headers=ana).json()
    assert r["aprobado"] is True
    assert r["ingesta"]["indexado"] is False
    assert "pendiente" in r["mensaje"]


ENTREVISTA_TXT = """Guía de entrevista: experiencia docente
Universidad Pedagógica Nacional, campus Ajusco
Objetivo: comprender cómo los docentes viven la evaluación formativa.
Entrevista semiestructurada aplicada en el ciclo escolar 2023-2024.
Entrevistador: ¿Cómo describe su experiencia evaluando a sus estudiantes?
Docente: Ha sido retadora.
Entrevistador: ¿Qué apoyos institucionales recibe?
Docente: Pocos.
"""


def test_propuesta_de_entrevista(cliente, ana, crear_instrumento):
    id_crudo = crear_instrumento("guia_docentes.txt", ENTREVISTA_TXT, tipo="entrevista")
    v = cliente.get(f"/api/enrichment/{id_crudo}/propuesta", headers=ana).json()["valores"]
    assert v["metodologia"] == "Entrevista semiestructurada"
    assert v["institucion"].startswith("Universidad Pedagógica Nacional")
    assert v["objetivo"].startswith("comprender cómo los docentes")
    assert v["identificador_propio"] == "guia_docentes"
    dc = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana).json()["valores"]
    assert dc["dc_title"] == "Guía de entrevista: experiencia docente"
    assert dc["dc_publisher"].startswith("Universidad Pedagógica Nacional")


PRUEBA_TXT = """Examen diagnóstico de Cálculo Diferencial
Asignatura: Cálculo Diferencial
Ciclo escolar 2024-2025, 1er semestre, Grupo 1A
SECCIÓN A: LÍMITES
1. Calcule el límite de f(x) cuando x tiende a 2.
a) 1
b) 2
2. Explique qué es una asíntota.
SECCIÓN B: DERIVADAS
3. Determine la derivada de x^2.
"""


def test_propuesta_y_aprobacion_de_prueba(cliente, ana, crear_instrumento, db):
    id_crudo = crear_instrumento("diagnostico.txt", PRUEBA_TXT, tipo="prueba_estandarizada")
    v = cliente.get(f"/api/enrichment/{id_crudo}/propuesta", headers=ana).json()["valores"]
    assert v["unidad_de_aprendizaje"] == "Cálculo Diferencial"
    assert v["ciclo_escolar"] == "2024-2025"
    assert v["grupo"] == "1A"
    assert v["grado"] == "1° semestre"
    assert v["tipo_de_prueba"] == "Diagnóstico"
    assert v["mapeo_de_reactivos_por_seccion"] == {"SECCIÓN A: LÍMITES": 2, "SECCIÓN B: DERIVADAS": 1}
    assert v["taxonomia_bloom"] == "Comprender (1), Aplicar (2)"

    especificos = {
        "unidad_de_aprendizaje": "Cálculo Diferencial",
        "mapeo_de_reactivos_por_seccion": "Límites: 2\nDerivadas: 1",
        "tipo_de_prueba": "Diagnóstica",
        "nivel_educativo": "Licenciatura",
        "objetivo_de_evaluacion": "Identificar conocimientos previos.",
    }
    r = cliente.post(
        f"/api/metadata/{id_crudo}/aprobar",
        json={"dublin_core": _dc_completo(dc_type="Prueba estandarizada"), "enriquecidos": especificos},
        headers=ana,
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.get(MetadatosEnriquecidosPruebas, id_crudo).mapeo_de_reactivos_por_seccion == {"Límites": 2, "Derivadas": 1}

    malo = {**especificos, "mapeo_de_reactivos_por_seccion": "sin formato"}
    vista = cliente.post(
        f"/api/metadata/{id_crudo}/vista-previa",
        json={"dublin_core": _dc_completo(), "enriquecidos": malo},
        headers=ana,
    ).json()
    assert "mapeo_de_reactivos_por_seccion" in vista["errores"]["enriquecidos"]


def test_finalizar_agrega_kpis_aceptados(cliente, ana, crear_instrumento, db, storage):
    id_crudo = crear_instrumento("a.csv", ENCUESTA_CSV)
    assert cliente.post(f"/api/metadata/{id_crudo}/finalizar", headers=ana).status_code == 409

    cliente.post(
        f"/api/metadata/{id_crudo}/aprobar",
        json={"dublin_core": _dc_completo(), "enriquecidos": ENCUESTA_ESPECIFICOS},
        headers=ana,
    )
    procesado = db.query(InstrumentoProcesado).filter_by(id_crudo=id_crudo).one()
    db.add(KPI(kpi_id=5, nombre_kpi="Compromiso académico"))
    db.add(KPIInferido(id_procesado=procesado.id_instrumento, kpi_id=5, razon="Aceptado"))
    db.commit()

    r = cliente.post(f"/api/metadata/{id_crudo}/finalizar", headers=ana)
    assert r.status_code == 200, r.text
    assert r.json()["kpis"] == [{"kpi_id": 5, "nombre_kpi": "Compromiso académico", "score": None}]
    final = storage.json[(id_crudo, "analysis")][-1]
    assert final["inferred_kpis"][0]["kpi_id"] == 5
    assert "Compromiso académico" in final["design_reference"]["kpi_hints"]
    db.expire_all()
    assert db.query(InstrumentoProcesado).filter_by(id_crudo=id_crudo).one().ruta_json.endswith("1__x.json")
    assert storage.indexados == [id_crudo, id_crudo]


def test_retirar_metadatos(cliente, ana, crear_instrumento, db, storage):
    id_crudo = crear_instrumento("a.csv", ENCUESTA_CSV)
    cliente.post(
        f"/api/metadata/{id_crudo}/aprobar",
        json={"dublin_core": _dc_completo(), "enriquecidos": ENCUESTA_ESPECIFICOS},
        headers=ana,
    )
    assert cliente.get(f"/api/metadata/{id_crudo}", headers=ana).json()["aprobado"] is True
    r = cliente.delete(f"/api/metadata/{id_crudo}", headers=ana)
    assert r.status_code == 200
    db.expire_all()
    assert db.get(MetadatosDC, id_crudo) is None
    procesado = db.query(InstrumentoProcesado).filter_by(id_crudo=id_crudo).one()
    assert procesado.fecha_aprobado is None and procesado.estado == "recibido"
    assert storage.desindexados == [id_crudo]
    assert cliente.get(f"/api/metadata/{id_crudo}", headers=ana).status_code == 404


def test_instrumento_json_de_la_demo_reutiliza_sus_metadatos(cliente, ana, crear_instrumento):
    import json

    data = {
        "instrument": {
            "title": "Calidad académica",
            "objective": "Explorar la percepción de exigencia.",
            "sections": [{"name": "Reactivos", "questions": [{"question_id": "q1", "text": "¿Es claro?"}]}],
        },
        "metadata": {
            "dublin_core": {"dc:title": "Calidad académica", "dc:creator": "Equipo", "dc:coverage": "Estudiantes"},
            "survey_specific": {"n_respondentes": 250, "palabras_clave": ["calidad"], "constructo_principal": "Calidad"},
        },
        "design_reference": {"kpi_hints": ["Satisfacción"]},
    }
    id_crudo = crear_instrumento("inst_01.v1.json", json.dumps(data))
    dc = cliente.get(f"/api/metadata/{id_crudo}/propuesta", headers=ana).json()
    assert dc["valores"]["dc_creator"] == "Equipo" and dc["origen"]["dc_creator"] == "archivo"
    esp = cliente.get(f"/api/enrichment/{id_crudo}/propuesta", headers=ana).json()["valores"]
    assert esp["n_respondentes"] == 250 and esp["objetivo"] == "Explorar la percepción de exigencia."


def test_campos_del_tipo(cliente, ana):
    r = cliente.get("/api/enrichment/campos/entrevista", headers=ana).json()
    assert [c["clave"] for c in r] == ["identificador_propio", "objetivo", "metodologia", "institucion", "derechos"]
    assert cliente.get("/api/enrichment/campos/otro", headers=ana).status_code == 404
