"""API del documento final: generar (borrador), leer, publicar (vigente) y versiones."""
from __future__ import annotations

from conftest import ANA, LUIS, crear_instrumento


def _con_kpis(db, id_crudo: int) -> None:
    """Simula la confirmación de KPIs de analysis-service sobre la misma fila."""
    from shared.models.version_conocimiento import VersionConocimiento

    fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo).order_by(VersionConocimiento.version.desc()).first()
    perfil = dict(fila.perfil)
    pid = perfil["secciones"][0]["preguntas"][0]["id"]
    perfil["kpis_asociados"] = [{
        "kpi_id": "KPI-07", "nombre": "Satisfacción", "definicion": "…", "dimension": "Mejorar", "que_mide": "Mide…",
        "similitud": 0.6, "evidencia": [{"pregunta_id": pid, "similitud": 0.5}], "justificacion": "Porque…",
        "justificacion_origen": "llm", "aceptado_por": "Ana", "fecha": "2026-10-15T10:00:00+00:00",
    }]
    fila.perfil = perfil
    fila.decisiones_kpi = [{"kpi_id": 7, "decision": "aceptado"}, {"kpi_id": 9, "decision": "rechazado"}]
    fila.estado = "kpis_confirmados"
    db.commit()


def test_generar_leer_y_publicar(cliente, db, storage):
    from shared.models.version_conocimiento import VersionConocimiento

    id_crudo = crear_instrumento(db, storage, original="encuesta_original.txt", aprobado=True)
    assert cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA).status_code == 200
    _con_kpis(db, id_crudo)

    r = cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert (datos["version"], datos["estado"], datos["esquema_version"]) == (1, "borrador", "1.0")
    vista = datos["documento"]
    assert "respondentes" not in vista and vista["n_respondentes"] == 20 and len(vista["muestra_respondentes"]) == 3
    assert vista["kpis_asociados"][0]["kpi_id"] == "KPI-07" and vista["preguntas"][0]["kpis_relacionados"] == ["KPI-07"]
    assert any(a["codigo"] == "datos_personales_excluidos" for a in datos["avisos"])

    fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo).one()
    assert fila.ruta_documento.startswith(f"documento/{id_crudo}/1__v1_documento_final") and fila.sha256
    assert fila.fecha_documento is not None and fila.decisiones_kpi[1]["decision"] == "rechazado"
    assert {a["origen"] for a in fila.avisos} == {"perfil", "documento"}
    completo = cliente.get(f"/conocimiento/{id_crudo}/documento/json", headers=ANA).json()
    assert len(completo["respondentes"]) == 20 and completo == storage.guardados[fila.ruta_documento]
    assert cliente.get(f"/conocimiento/{id_crudo}/documento", headers=ANA).json()["documento"]["n_respondentes"] == 20

    # Regenerar en borrador crea un artefacto nuevo; publicar lo vuelve vigente.
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).status_code == 200
    db.refresh(fila)
    assert fila.ruta_documento.startswith(f"documento/{id_crudo}/2__")
    p = cliente.post(f"/conocimiento/{id_crudo}/documento/1/publicar", headers=ANA)
    assert p.status_code == 200 and p.json()["estado"] == "vigente"
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).status_code == 409  # ya publicada

    # Nueva versión (re-aprobación): la vigente sigue vigente hasta publicar la nueva.
    assert cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA).json()["version"] == 2
    assert cliente.post(f"/conocimiento/{id_crudo}/documento/2/publicar", headers=ANA).status_code == 409  # sin documento
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).json()["version"] == 2
    estados = {v.version: v.estado for v in db.query(VersionConocimiento).filter_by(id_crudo=id_crudo)}
    assert estados == {1: "vigente", 2: "borrador"}
    cliente.post(f"/conocimiento/{id_crudo}/documento/2/publicar", headers=ANA)
    db.expire_all()
    estados = {v.version: v.estado for v in db.query(VersionConocimiento).filter_by(id_crudo=id_crudo)}
    assert estados == {1: "reemplazado", 2: "vigente"}


def test_documento_sin_kpis_y_de_cada_tipo(cliente, db, storage):
    for tipo, original in (("prueba_estandarizada", "prueba_original.txt"), ("entrevista", None)):
        id_crudo = crear_instrumento(db, storage, tipo=tipo, original=original, aprobado=True)
        cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
        r = cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA)  # sin confirmar KPIs: también vale
        assert r.status_code == 200, r.text
        vista = r.json()["documento"]
        assert vista["kpis_asociados"] == []
        assert vista.get("n_alumnos", vista.get("n_entrevistas")) > 0


def test_instrumento_anterior_a_la_limpieza_documento_sin_respuestas(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, con_limpieza=False, aprobado=True)
    storage.jsons[(id_crudo, "metadata")] = {"instrument": {"sections": [{"name": "Reactivos", "questions": [
        {"question_id": "q1", "text": "¿Te gusta leer?", "type": "binaria", "options": ["Sí", "No"]}]}]}}
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    datos = cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).json()
    assert datos["documento"]["n_respondentes"] == 0
    assert datos["documento"]["preguntas"][0]["tipo"] == "sin_datos"
    assert datos["avisos"][0]["codigo"] == "sin_limpieza"


def test_errores(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, aprobado=True)
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).status_code == 409  # sin perfil
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    assert cliente.get(f"/conocimiento/{id_crudo}/documento", headers=ANA).status_code == 404  # aún sin documento
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=LUIS).status_code == 403
    assert cliente.post(f"/conocimiento/{id_crudo}/documento/9/publicar", headers=ANA).status_code == 404
    storage.caido = True
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).status_code == 503


def test_publicar_escribe_respuestas_en_formato_largo_y_reingiere(cliente, db, storage):
    from shared.models.respuesta_interpretada import RespuestaInterpretada

    id_crudo = crear_instrumento(db, storage, original="encuesta_original.txt", aprobado=True)
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    doc = storage.guardados  # se llena al generar
    cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA)
    completo = next(iter(doc.values()))
    assert cliente.post(f"/conocimiento/{id_crudo}/documento/1/publicar", headers=ANA).status_code == 200

    filas = db.query(RespuestaInterpretada).filter_by(id_crudo=id_crudo).all()
    esperadas = sum(len(r["respuestas"]) for r in completo["respondentes"])
    assert len(filas) == esperadas and {f.version for f in filas} == {1}
    r001 = [f for f in filas if f.respondente_id.endswith("-R001")]
    assert r001 and all(f.contexto == completo["respondentes"][0]["contexto"] for f in r001)
    likert = next(f for f in r001 if f.nivel)
    original = next(x for x in completo["respondentes"][0]["respuestas"] if x["pregunta_id"] == likert.pregunta_id)
    assert (likert.significado, likert.nivel, likert.estado) == (original["significado"], original["nivel"], original["estado"])
    assert storage.indexados == [id_crudo]

    # Una nueva versión publicada reemplaza las filas (no se acumulan).
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA)
    cliente.post(f"/conocimiento/{id_crudo}/documento/2/publicar", headers=ANA)
    db.expire_all()
    assert {f.version for f in db.query(RespuestaInterpretada).filter_by(id_crudo=id_crudo)} == {2}
    assert db.query(RespuestaInterpretada).filter_by(id_crudo=id_crudo).count() == esperadas


def test_si_falla_la_reingesta_la_publicacion_queda_con_aviso(cliente, db, storage):
    from shared.models.version_conocimiento import VersionConocimiento

    id_crudo = crear_instrumento(db, storage, original="encuesta_original.txt", aprobado=True)
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA)
    storage.indice_caido = True
    r = cliente.post(f"/conocimiento/{id_crudo}/documento/1/publicar", headers=ANA)
    assert r.status_code == 200 and r.json()["estado"] == "vigente"
    fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo).one()
    db.refresh(fila)
    assert any(a["codigo"] == "reingesta_pendiente" for a in fila.avisos)


def test_filas_de_prueba_y_entrevista():
    from services import respuestas

    prueba = {"alumnos": [{"id": "INS-1-A001", "contexto": {"turno": "Vespertino"}, "respuestas": [
        {"reactivo_id": "INS-1-r01", "respuesta": "B", "correcta": False, "estado": "valida", "significado": "54"}]}]}
    [f] = respuestas.filas(prueba, 1, 3)
    assert (f["respondente_id"], f["pregunta_id"], f["valor"], f["nivel"], f["contexto"]) == ("INS-1-A001", "INS-1-r01", "B", "incorrecta", {"turno": "Vespertino"})
    entrevista = {"entrevistas": [{"participante": "INS-1-E02", "intercambios": [
        {"pregunta_id": "INS-1-p01", "pregunta": "¿Cómo te evalúan?", "respuesta": "Con proyectos."}, {"pregunta": "Otra", "respuesta": "x"}]}]}
    filas = respuestas.filas(entrevista, 1, 1)
    assert [(f["respondente_id"], f["pregunta_id"], f["valor"]) for f in filas] == [("INS-1-E02", "INS-1-p01", "Con proyectos."), ("INS-1-E02", "", "x")]
