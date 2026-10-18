"""Consultas con filtro del chat: «uno de los estudiantes que sí reprobaron por falta de tiempo».

Los valores esperados se cuentan a mano de `docs_ejemplo.CARGA` (5 respondentes):
reprobaron (cualquier «Sí, …») R001, R002 y R005; trabajan más de 30 h R002 y R005;
estudian más de 20 h R003 (25) y R004 (30); tienen dificultades R001 y R002.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from shared.models.version_conocimiento import VersionConocimiento

import docs_ejemplo
from services import enrutador


def _publicar(db, storage, id_crudo: int, doc: dict) -> None:  # noqa: ANN001
    key = f"documento/{id_crudo}/1__v1_documento_final.json"
    storage.archivos[key] = (json.dumps(doc).encode("utf-8"), "documento.json")
    db.add(VersionConocimiento(id_crudo=id_crudo, version=1, estado="vigente", perfil={}, ruta_documento=key))
    db.commit()


@pytest.fixture()
def acervo(db, storage):
    enrutador._cache_docs.clear()
    _publicar(db, storage, 1, docs_ejemplo.encuesta())
    _publicar(db, storage, 4, docs_ejemplo.encuesta_carga())
    return db


def _lineas(db, pregunta: str, ids=None) -> list[str]:  # noqa: ANN001
    r = enrutador.resolver(pregunta, db, ids)
    assert r is not None and r.consulta == "filtro", pregunta
    [(ins, lineas, _)] = r.partes
    assert ins.id_crudo == "4"
    return lineas


def test_uno_de_los_que_si_reprobaron_trae_todas_sus_respuestas(acervo):
    lineas = _lineas(acervo, "dame todas las respuestas de la encuesta de carga académica de uno de los tantos estudiantes "
                             "que sí han reprobado por falta de tiempo y dame un resumen de las respuestas de ese estudiante")
    # «sí» agrupa todas las opciones que empiezan con «Sí».
    assert lineas[0] == ("Condición: p01 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» = "
                         "«Sí, una vez» o «Sí, varias veces»")
    assert "Cumplen la condición 3 de 5 respondentes (60.0 %)." in lineas
    assert "Respondente elegido como ejemplo: R001 (Turno: Matutino)." in lineas and "Sus respuestas:" in lineas
    assert "p03 «¿Cuál es tu carga laboral actual?»: No trabajo" in lineas and "p04 «¿Cuántas horas por semana dedicas al estudio fuera de clases? (número)»: 12 horas" in lineas
    assert lineas[-1] == "Otros que cumplen la condición: R002, R005."


def test_contar_por_una_opcion_nombrada_con_sus_palabras(acervo):
    lineas = _lineas(acervo, "¿Cuántos estudiantes trabajan más de 30 horas?")
    assert lineas == ["Condición: p03 «¿Cuál es tu carga laboral actual?» = «Trabajo más de 30h»",
                      "Cumplen la condición 2 de 5 respondentes (40.0 %)."]


def test_comparacion_en_una_pregunta_numerica(acervo):
    lineas = _lineas(acervo, "¿Cuántos estudiantes estudian más de 20 horas por semana fuera de clases?")
    assert lineas[0].endswith("> 20") and "Cumplen la condición 2 de 5 respondentes (40.0 %)." in lineas


def test_dos_condiciones_a_la_vez(acervo):
    lineas = _lineas(acervo, "¿cuántos estudiantes que sí reprobaron una vez tienen dificultades para equilibrar trabajo y estudios?")
    assert sorted(lineas[:2]) == [
        "Condición: p01 «¿Has reprobado alguna materia por falta de tiempo para estudiar?» = «Sí, una vez»",
        "Condición: p02 «¿Tienes dificultades para equilibrar trabajo y estudios?» = «Sí»",
    ]
    assert "Cumplen la condición 1 de 5 respondentes (20.0 %)." in lineas


def test_lista_dentro_de_un_grupo_de_contexto(acervo):
    lineas = _lineas(acervo, "¿Quiénes del turno vespertino respondieron que sí han reprobado por falta de tiempo?")
    assert "Grupo: Turno = Vespertino" in lineas and "Cumplen la condición 2 de 3 respondentes (66.7 %)." in lineas
    assert lineas[-1] == "Respondentes que la cumplen: R002, R005."


def test_nadie_cumple_se_dice_sin_inventar(acervo):
    r = enrutador.resolver("¿Cuántos estudiantes del turno matutino trabajan más de 30 horas?", acervo, None)
    assert not r.encontrado and r.partes[0][1][-1] == "Ninguno de los 2 respondentes cumple la condición."


def test_el_instrumento_nombrado_limita_el_alcance(acervo):
    instrumentos = enrutador.cargar_documentos(acervo, None)
    nombrados = enrutador.nombrados(instrumentos, enrutador.normalizar("en la encuesta de carga académica, ¿quiénes…?"))
    assert [i.id_crudo for i in nombrados] == ["4"]
    assert enrutador.nombrados(instrumentos, "quienes reprobaron") == []


def test_sin_condicion_reconocible_otra_intencion_sigue_funcionando(acervo):
    # «cuántos estudiantes…» dispara el filtro; sin opción ni nivel reconocible en la encuesta de
    # carga, la de experiencia responde por nivel (2 de 5 de acuerdo en p04: R001 y R002).
    r = enrutador.resolver("¿Cuántos estudiantes están de acuerdo con p4?", acervo, ["1"])
    assert r is not None and r.encontrado and "2 de 5" in " ".join(r.partes[0][1])


def test_respaldo_del_modelo_validado_contra_el_catalogo(acervo, monkeypatch):
    from services import ollama_client

    respuestas: list[dict] = []

    async def no_stream(prompt, modelo, sistema=None, *, formato=None, opciones=None):  # noqa: ANN001
        assert formato == "json" and "p03 | ¿Cuál es tu carga laboral actual? | opciones: " in prompt
        return json.dumps(respuestas.pop(0)), False

    monkeypatch.setattr(ollama_client, "generar_no_stream", no_stream)
    pregunta = "¿Cuántos estudiantes no tienen empleo?"
    assert enrutador.resolver(pregunta, acervo, ["4"]) is None  # las reglas no hallan la condición

    respuestas.append({"instrumento": "4", "condiciones": [{"pregunta": "p3", "valores": ["No trabajo"]}]})
    r = asyncio.run(enrutador.filtro_llm(pregunta, acervo, ["4"]))
    assert r.encontrado and "Cumplen la condición 2 de 5 respondentes (40.0 %)." in r.partes[0][1]
    assert "(condición interpretada por el modelo)" in r.partes[0][1][0]

    # Una opción que no existe en el catálogo se descarta: no se cuenta nada inventado.
    respuestas.append({"instrumento": "4", "condiciones": [{"pregunta": "p3", "valores": ["Desempleado"]}]})
    assert asyncio.run(enrutador.filtro_llm(pregunta, acervo, ["4"])) is None


def test_respaldo_desactivable(acervo, monkeypatch):
    from shared.db.core.config import settings

    monkeypatch.setattr(settings, "RAG_FILTRO_LLM", False)
    assert asyncio.run(enrutador.filtro_llm("¿Cuántos estudiantes no tienen empleo?", acervo, ["4"])) is None


def test_chat_con_filtro_va_por_la_ruta_estructurada(cliente, acervo, ollama, chroma):
    from conftest import token
    from shared.models.usuario import Usuario

    acervo.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    acervo.commit()
    chroma.crear("instrumentos")
    r = cliente.post("/rag/chat", json={"pregunta": "¿Cuántos estudiantes trabajan más de 30 horas?", "stream": False,
                                        "instrumentoIds": ["4"]}, headers=token(2)).json()
    assert r["ruta"] == "estructurada" and r["decision"] == "dentro"
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in ollama["prompts"][-1]


# ── Calidad de los datos y sugerencias (medidas de la limpieza) ────────────────


def _limpieza(db, id_crudo: int, estadistica: dict) -> None:  # noqa: ANN001
    from shared.models.limpieza_ejecucion import LimpiezaEjecucion
    from shared.models.raw_data import RawData

    if db.get(RawData, id_crudo) is None:
        db.add(RawData(id_crudo=id_crudo, id_owner=2, tipo_instrumento="encuesta", nombre_archivo="x.csv", raw_archivo="raw/x"))
        db.flush()
    db.add(LimpiezaEjecucion(id_crudo=id_crudo, version=1, estado="confirmada",
                             reporte={"vista_final": {"estadistica": estadistica}}))
    db.commit()


def test_calidad_responde_con_las_medidas_y_las_sugerencias(acervo):
    _limpieza(acervo, 4, {"fiabilidad": [{"bloque": "Carga", "alfa": 0.91, "interpretacion": "excelente", "n_items": 4}],
                          "encuestados": {"linea_recta": 1, "incompletos": 0},
                          "columnas": [{"id": "p1", "rol": "pregunta", "tipo": "likert", "n": 5}]})
    r = enrutador.resolver("¿Qué análisis me sugieres para la encuesta de carga académica?", acervo, None)
    assert r.consulta == "calidad" and r.encontrado
    [(ins, lineas, _)] = r.partes
    assert ins.id_crudo == "4"
    assert lineas[0] == "Fiabilidad del bloque «Carga»: α de Cronbach = 0.91 (excelente), 4 ítems."
    assert any(l.startswith("Sugerencia (bien): Puedes promediar los 4 ítems") for l in lineas)


def test_calidad_sin_limpieza_lo_dice_y_definicion_va_al_glosario(acervo):
    r = enrutador.resolver("¿Qué tan confiable es la encuesta de carga académica?", acervo, None)
    assert not r.encontrado and "no tiene medidas de la limpieza" in r.partes[0][1][0]
    assert enrutador.detectar("¿Qué significa un alfa de Cronbach bajo?") is None


def test_uno_incluye_un_resumen_calculado_de_la_persona(acervo):
    acervo_doc = enrutador.resolver("dame uno de los estudiantes que están de acuerdo con p4", acervo, ["1"])
    lineas = acervo_doc.partes[0][1]
    resumen = next(l for l in lineas if l.startswith("Resumen calculado de sus respuestas de escala: "))
    # R001: 4, 4, 3, 5, 4, 4, 5 → «De acuerdo» en p01, p02, p05, p06; «Totalmente de acuerdo» en p04, p07; neutral en p03.
    assert "«De acuerdo» en p01, p02, p05, p06" in resumen and "«Totalmente de acuerdo» en p04, p07" in resumen


def test_negativa_pegada_al_final_se_quita():
    from services.rag_service import quitar_sin_informacion_sobrante

    texto = "37 de 160 estudiantes trabajan más de 30 horas (23.1 %).\n\nNo tengo información relacionada con los instrumentos consultados."
    assert quitar_sin_informacion_sobrante(texto) == "37 de 160 estudiantes trabajan más de 30 horas (23.1 %)."
    assert quitar_sin_informacion_sobrante("No tengo información relacionada con lo que solicitas.").startswith("No tengo")
