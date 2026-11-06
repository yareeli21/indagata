"""Análisis de respuestas de entrevista: unidades literales, núcleo, postura y revisión."""
from __future__ import annotations

from conftest import ANA, crear_instrumento
from services.documento import analisis_entrevista as ae

PREGUNTA = "¿Consideras que las actividades extracurriculares actualmente tienen impacto en tus calificaciones?"
RESPUESTA = (
    "Cuando iba en la primaria no lo pensaba así, yo las practicaba porque me gustaba jugar y me divertía, "
    "pero ahora creo que sí, me llenan de energía por querer seguir manteniendo la beca deportiva, "
    "entonces diría que sí, aunque antes no porque antes lo veía como juego."
)


def test_reglas_separan_el_relato_del_pasado_de_lo_que_responde():
    a = ae.analizar_reglas(PREGUNTA, RESPUESTA)
    assert a["marco_pregunta"] == "actual" and a["metodo"] == "reglas" and a["postura"] == "si"
    primera, segunda = a["unidades"][0], a["unidades"][1]
    assert primera["marco_temporal"] == "pasado" and primera["funcion"] == "contexto"
    assert segunda["marco_temporal"] == "actual" and segunda["funcion"] == "responde"
    assert "beca deportiva" in a["nucleo"] and "primaria" not in a["nucleo"]


def test_llm_valido_se_usa_y_las_unidades_inventadas_se_descartan():
    salida = {
        "unidades": [
            {"texto": "Cuando iba en la primaria no lo pensaba así", "marco_temporal": "pasado", "funcion": "contexto", "postura": "no"},
            {"texto": "pero ahora creo que sí", "marco_temporal": "actual", "funcion": "responde", "postura": "si"},
            {"texto": "las extracurriculares mejoran mi promedio", "marco_temporal": "actual", "funcion": "responde", "postura": "si"},
        ],
        "postura": "si",
        "motivo": "mantener la beca deportiva",
    }
    a = ae.analizar(PREGUNTA, RESPUESTA, lambda _p: salida)
    assert a["metodo"] == "llm" and a["descartadas"] == 1 and len(a["unidades"]) == 2
    assert a["nucleo"] == "pero ahora creo que sí" and a["motivo"] == "mantener la beca deportiva"


def test_motivo_no_anclado_se_omite_y_llm_sin_nucleo_usa_reglas():
    salida = {"unidades": [{"texto": "pero ahora creo que sí", "marco_temporal": "actual", "funcion": "responde", "postura": "si"}],
              "postura": "si", "motivo": "le gusta competir en torneos nacionales"}
    assert ae.analizar(PREGUNTA, RESPUESTA, lambda _p: salida)["motivo"] == ""
    sin_nucleo = {"unidades": [{"texto": "Cuando iba en la primaria no lo pensaba así", "marco_temporal": "pasado",
                                "funcion": "contexto", "postura": "no"}], "postura": "no"}
    assert ae.analizar(PREGUNTA, RESPUESTA, lambda _p: sin_nucleo)["metodo"] == "reglas"
    assert ae.analizar(PREGUNTA, RESPUESTA, lambda _p: None)["metodo"] == "reglas"


def _entrevista_en_borrador(cliente, db, storage) -> int:
    id_crudo = crear_instrumento(db, storage, tipo="entrevista", aprobado=True)
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    assert cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA).status_code == 200
    return id_crudo


def test_api_analiza_corrige_y_no_reanaliza_lo_revisado(cliente, db, storage, monkeypatch):
    from services import ollama

    llamadas = []
    monkeypatch.setattr(ollama, "generar_json", lambda p: llamadas.append(p) or None)  # sin LLM: reglas
    id_crudo = _entrevista_en_borrador(cliente, db, storage)

    r = cliente.post(f"/conocimiento/{id_crudo}/documento/analisis", headers=ANA)
    assert r.status_code == 202 and r.json()["estado"] == "en_curso"
    datos = cliente.get(f"/conocimiento/{id_crudo}/documento/analisis", headers=ANA).json()
    assert datos["estado"] == "listo" and datos["hechos"] == datos["total"] == len(datos["intercambios"]) > 0
    assert all(x["analisis"]["estado"] == "propuesto" for x in datos["intercambios"]) and llamadas

    primero = datos["intercambios"][0]
    fragmento = primero["respuesta"].split(".")[0].strip()
    corregido = cliente.patch(
        f"/conocimiento/{id_crudo}/documento/analisis/{primero['participante']}/{primero['n']}", headers=ANA,
        json={"postura": "ambivalente", "unidades": [{"texto": fragmento, "marco_temporal": "actual", "funcion": "responde", "postura": "ambivalente"}]},
    )
    assert corregido.status_code == 200 and corregido.json()["analisis"]["estado"] == "revisado"
    assert corregido.json()["analisis"]["nucleo"] == fragmento

    inventado = cliente.patch(
        f"/conocimiento/{id_crudo}/documento/analisis/{primero['participante']}/{primero['n']}", headers=ANA,
        json={"unidades": [{"texto": "esto nunca lo dijo", "marco_temporal": "actual", "funcion": "responde", "postura": "si"}]},
    )
    assert inventado.status_code == 422

    llamadas.clear()
    cliente.post(f"/conocimiento/{id_crudo}/documento/analisis", headers=ANA)
    datos = cliente.get(f"/conocimiento/{id_crudo}/documento/analisis", headers=ANA).json()
    assert datos["revisados"] == 1 and len(llamadas) == datos["total"] == len(datos["intercambios"]) - 1  # lo revisado no se reanaliza
    doc = cliente.get(f"/conocimiento/{id_crudo}/documento/json", headers=ANA).json()
    assert doc["esquema_version"] == "2.1"


def test_api_solo_para_entrevistas_en_borrador(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, original="encuesta_original.txt", aprobado=True)
    cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    cliente.post(f"/conocimiento/{id_crudo}/documento", headers=ANA)
    assert cliente.post(f"/conocimiento/{id_crudo}/documento/analisis", headers=ANA).status_code == 409


def test_la_postura_global_sale_de_lo_que_responde_y_lo_explicito_manda():
    # El modelo dice «ambivalente» porque mezcla el «no» del pasado con el «sí» de ahora.
    salida = {"unidades": [
        {"texto": "Cuando iba en la primaria no lo pensaba así", "marco_temporal": "pasado", "funcion": "contexto", "postura": "no"},
        {"texto": "pero ahora creo que sí", "marco_temporal": "actual", "funcion": "responde", "postura": "ambivalente"}],
        "postura": "ambivalente"}
    assert ae.analizar(PREGUNTA, RESPUESTA, lambda _p: salida)["postura"] == "si"
    # «ya no» explícito en lo que responde gana al «sí» del modelo.
    r = "En primer semestre iba cada semana porque reprobé cálculo, pero ahora ya no voy, ya no lo necesito."
    salida = {"unidades": [{"texto": "pero ahora ya no voy, ya no lo necesito", "marco_temporal": "actual",
                            "funcion": "responde", "postura": "si"}], "postura": "si"}
    assert ae.analizar("¿Hoy en día usas el servicio de tutorías?", r, lambda _p: salida)["postura"] == "no"


def test_preambulo_sin_hablante_no_es_otra_persona():
    from services.documento import entrevista
    from services.estructura import Estructura

    filas = [{"hablante": "", "rol": "desconocido", "texto": "Entrevista realizada en la biblioteca."},
             {"hablante": "Entrevistador", "rol": "entrevistador", "texto": "¿Trabajas actualmente?"},
             {"hablante": "Entrevistado", "rol": "entrevistado", "texto": "No, solo estudio."}]
    perfil = {"instrumento_id": "INS-0009", "tipo": "entrevista", "titulo": "T", "kpis_asociados": []}
    doc = entrevista.construir(perfil, Estructura(), {}, filas)
    assert [e["participante"] for e in doc["entrevistas"]] == ["INS-0009-E01"]
    assert doc["entrevistas"][0]["intercambios"][0]["respuesta"] == "No, solo estudio."
    assert any(a["codigo"] == "texto_sin_hablante" for a in doc["avisos"])


def test_depende_al_inicio_es_ambivalente_y_a_veces_en_medio_no():
    salida = {"unidades": [{"texto": "en matemáticas sí", "marco_temporal": "actual", "funcion": "responde", "postura": "si"}],
              "postura": "si"}
    r = "Depende de la materia; en matemáticas sí, pero en las materias de redacción no tanto."
    assert ae.analizar("¿Hoy consideras que los exámenes reflejan lo que aprenden?", r, lambda _p: salida)["postura"] == "ambivalente"
    assert ae.analizar_reglas("¿Usas rúbricas actualmente?", "Más o menos; en laboratorio sí, en exámenes no.")["postura"] == "ambivalente"
    # «a veces» en medio de una respuesta clara no la vuelve ambivalente.
    clara = {"unidades": [{"texto": "Sí, a veces voy al gimnasio de la escuela", "marco_temporal": "actual",
                           "funcion": "responde", "postura": "si"}], "postura": "si"}
    assert ae.analizar("¿Usas las instalaciones actualmente?", "Sí, a veces voy al gimnasio de la escuela.", lambda _p: clara)["postura"] == "si"
    assert not ae.empieza_ambivalente("No del todo; un examen te dice si memorizaron")
