"""Etapa 1 del chat (28 oct): esquema del plan, catálogo compacto, validación contra el catálogo e interpretación
con reintento. El LLM se sustituye por respuestas fijas: lo que se prueba es lo que el sistema hace con ellas."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from services import catalogo, interpretacion
from services.plan_consulta import LIMITE_MAX, PlanConsulta, esquema, validar_contra_catalogo
from tests import docs_ejemplo


def _cat_carga():
    return catalogo.construir("4", "Encuesta de carga académica y gestión del tiempo", "encuesta", docs_ejemplo.encuesta_carga())


def _cat_encuesta():
    return catalogo.construir("1", "Experiencia estudiantil", "encuesta", docs_ejemplo.encuesta())


# ── Esquema ────────────────────────────────────────────────────────────────────


def test_los_ejemplos_del_prompt_son_planes_validos():
    for pregunta, plan in interpretacion._EJEMPLOS:
        PlanConsulta.model_validate(plan)  # un ejemplo inválido enseñaría al modelo a equivocarse
    intenciones = {plan["intencion"] for _, plan in interpretacion._EJEMPLOS}
    assert intenciones == set(PlanConsulta.model_fields["intencion"].annotation.__args__)


def test_esquema_rechaza_campos_inventados_e_intenciones_desconocidas():
    with pytest.raises(ValidationError):
        PlanConsulta.model_validate({"intencion": "hallazgo", "sql": "SELECT *"})
    with pytest.raises(ValidationError):
        PlanConsulta.model_validate({"intencion": "borrar_todo"})


def test_limite_se_recorta_al_tope():
    assert PlanConsulta(intencion="filtrar_respondentes", limite=5000).limite == LIMITE_MAX


def test_aclaracion_y_semantica_necesitan_su_texto():
    with pytest.raises(ValidationError):
        PlanConsulta(intencion="aclaracion")
    with pytest.raises(ValidationError):
        PlanConsulta(intencion="semantica_abierta")


def test_esquema_publicado_coincide_con_el_modelo():
    publicado = Path(__file__).resolve().parents[1] / "esquemas" / "plan_consulta.json"
    assert json.loads(publicado.read_text(encoding="utf-8")) == esquema()


# ── Catálogo ───────────────────────────────────────────────────────────────────


def test_catalogo_compacto_con_preguntas_opciones_contexto_y_kpis():
    cat = _cat_encuesta()
    assert cat.respondentes == ["R001", "R002", "R003", "R004", "R005"]
    assert cat.contexto == {"Turno": ["Matutino", "Vespertino"]}
    assert [k.id for k in cat.kpis] == ["KPI-07"] and cat.kpis[0].preguntas == ["p04", "p07"]
    texto = cat.texto()
    assert "Respondentes: 5 (R001 a R005)" in texto and "Turno = Matutino, Vespertino" in texto
    assert "- p01 [likert] Los profesores explican con claridad" in texto and "KPI-07 Satisfacción estudiantil" in texto
    carga = _cat_carga()
    assert carga.preguntas["p03"].opciones == ["No trabajo", "Trabajo más de 30h", "Trabajo menos de 20h"]


# ── Validación contra el catálogo ──────────────────────────────────────────────


def test_opcion_sin_acentos_ni_mayusculas_se_empareja_con_la_real():
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "P3", "op": "=", "valor": "no TRABAJO"}]})
    v = validar_contra_catalogo(plan, [_cat_carga()])
    assert v.plan.filtros[0].pregunta == "p03" and v.plan.filtros[0].valor == "No trabajo"
    assert "pregunta «P3» → «p03»" not in v.correcciones  # el filtro se corrige sin aviso de pregunta…
    assert "p03: «no TRABAJO» → «No trabajo»" in v.correcciones


def test_opcion_parecida_se_corrige_y_una_que_no_existe_pide_aclaracion():
    cat = _cat_carga()
    cercano = validar_contra_catalogo(PlanConsulta.model_validate(
        {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p03", "valor": "Trabajo mas de 30 h"}]}), [cat])
    assert cercano.plan.filtros[0].valor == "Trabajo más de 30h"
    inventado = validar_contra_catalogo(PlanConsulta.model_validate(
        {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p03", "valor": "Desempleado"}]}), [cat])
    assert inventado.plan.intencion == "aclaracion" and "Desempleado" in inventado.plan.aclaracion
    assert "No trabajo" in inventado.plan.aclaracion  # le dice cuáles opciones hay


def test_pregunta_o_respondente_inexistente_pide_aclaracion():
    cat = _cat_encuesta()
    sin_pregunta = validar_contra_catalogo(PlanConsulta(intencion="resumen_pregunta", preguntas=["p40"]), [cat])
    assert sin_pregunta.plan.intencion == "aclaracion"
    sin_persona = validar_contra_catalogo(PlanConsulta(intencion="datos_respondente", respondentes=["R999"]), [cat])
    assert sin_persona.plan.intencion == "aclaracion" and "R001" in sin_persona.plan.aclaracion
    con_persona = validar_contra_catalogo(PlanConsulta(intencion="datos_respondente", respondentes=["r3"]), [cat])
    assert con_persona.plan.respondentes == ["R003"]


def test_contexto_kpi_e_instrumento_fuera_de_la_seleccion():
    cat = _cat_encuesta()
    v = validar_contra_catalogo(PlanConsulta(intencion="comparar_grupos", agrupar_por="turno", instrumentos=["77"],
                                             kpi="satisfaccion estudiantil"), [cat])
    assert v.plan.agrupar_por == "Turno" and v.plan.kpi == "KPI-07" and v.plan.instrumentos == []
    malo = validar_contra_catalogo(PlanConsulta(intencion="comparar_grupos", agrupar_por="carrera"), [cat])
    assert malo.plan.intencion == "aclaracion" and "Turno" in malo.plan.aclaracion


# ── Interpretación con el LLM (respuestas fijas) ───────────────────────────────


def _ollama(monkeypatch, salidas: list[str], degradado: bool = False) -> list[dict]:
    llamadas: list[dict] = []

    async def no_stream(prompt, modelo, sistema=None, *, formato=None, opciones=None):  # noqa: ANN001
        llamadas.append({"prompt": prompt, "sistema": sistema, "formato": formato, "opciones": opciones})
        return salidas[min(len(llamadas), len(salidas)) - 1], degradado

    monkeypatch.setattr(interpretacion.ollama_client, "generar_no_stream", no_stream)
    return llamadas


def test_plan_valido_al_primer_intento_con_esquema_y_temperatura_cero(monkeypatch):
    plan = {"intencion": "filtrar_respondentes", "filtros": [{"pregunta": "p03", "op": "=", "valor": "no trabajo"}],
            "campos": "todas_las_respuestas", "orden": {"por": "id_respondente", "dir": "asc"}, "limite": 5}
    llamadas = _ollama(monkeypatch, [json.dumps(plan)])
    r = asyncio.run(interpretacion.interpretar("dame los primeros 5 que no trabajan con todas sus respuestas", [], [_cat_carga()]))
    assert r.plan is not None and r.intentos == 1 and r.plan.limite == 5 and r.plan.filtros[0].valor == "No trabajo"
    assert llamadas[0]["formato"] == esquema() and llamadas[0]["opciones"]["temperature"] == 0
    assert "INSTRUMENTO 4 | encuesta" in llamadas[0]["prompt"] and "primer respondente" in llamadas[0]["prompt"]


def test_plan_invalido_se_reintenta_una_vez_con_el_error(monkeypatch):
    llamadas = _ollama(monkeypatch, ['{"intencion": "contar_todo"}', '{"intencion": "hallazgo"}'])
    r = asyncio.run(interpretacion.interpretar("dame un dato interesante", [], [_cat_encuesta()]))
    assert r.plan is not None and r.plan.intencion == "hallazgo" and r.intentos == 2
    assert "no es válido" in llamadas[1]["prompt"] and "contar_todo" in llamadas[1]["prompt"]


def test_dos_planes_invalidos_o_ollama_caido_no_dan_plan(monkeypatch):
    _ollama(monkeypatch, ["esto no es json", '{"intencion": "x"}'])
    r = asyncio.run(interpretacion.interpretar("¿algo?", [], [_cat_encuesta()]))
    assert r.plan is None and r.intentos == 2 and r.error.startswith("plan no válido")
    _ollama(monkeypatch, ["Ollama caído"], degradado=True)
    r = asyncio.run(interpretacion.interpretar("¿algo?", [], [_cat_encuesta()]))
    assert r.plan is None and r.intentos == 1 and r.error == "Ollama no disponible"


def test_el_historial_reciente_entra_al_prompt(monkeypatch):
    llamadas = _ollama(monkeypatch, ['{"intencion": "hallazgo"}'])
    historial = [("usuario", f"mensaje {i}") for i in range(6)] + [("asistente", "Cumplen 382 de 2000.")]
    asyncio.run(interpretacion.interpretar("¿y alguno de ellos tiene certificación?", historial, [_cat_encuesta()]))
    prompt = llamadas[0]["prompt"]
    assert "Asistente: Cumplen 382 de 2000." in prompt and "mensaje 5" in prompt and "mensaje 2" not in prompt


def test_opcion_que_existe_en_otra_pregunta_se_reubica():
    # El modelo copió el ID del ejemplo (p02) pero la opción solo existe en p03 de este instrumento.
    plan = PlanConsulta.model_validate({"intencion": "filtrar_respondentes",
                                        "filtros": [{"pregunta": "p02", "valor": "trabajo mas de 30h"}]})
    v = validar_contra_catalogo(plan, [_cat_carga()])
    assert v.plan.filtros[0].pregunta == "p03" and v.plan.filtros[0].valor == "Trabajo más de 30h"
    assert any("p02 → p03" in c for c in v.correcciones)


def test_catalogo_grande_pasa_a_forma_compacta():
    cats = [_cat_encuesta(), _cat_carga()] * 6
    prompt = interpretacion.construir_prompt("¿algo?", [], cats)
    assert len(prompt) < len(interpretacion.construir_prompt("¿algo?", [], cats[:1])) + 6 * 1500
    assert "- p01 [likert] Los profesores explican con claridad" in prompt


def test_alcance_que_no_cabe_lleva_los_instrumentos_recuperados_y_no_pasa_del_contexto():
    # Toda la colección: antes Ollama recortaba el prompt por el inicio (perdía instrucciones y ejemplos).
    from dataclasses import replace

    cats = [replace(_cat_encuesta(), id=str(n), titulo=f"Encuesta de hábitos {n}") for n in range(40)]
    cats.append(replace(_cat_carga(), id="99", titulo="Carga laboral de estudiantes"))
    prompt = interpretacion.construir_prompt("¿cuántos trabajan más de 30 horas?", [], cats, prioridad=["7", "99"])
    assert len(prompt) + len(interpretacion.SISTEMA) <= interpretacion._MAX_CARACTERES_PROMPT
    catalogo = prompt.split("=== CONSULTA REAL ===", 1)[1]
    assert catalogo.index("INSTRUMENTO 7 ") < catalogo.index("INSTRUMENTO 99 ")
    assert "instrumentos más en el alcance" in catalogo
    assert prompt.startswith(interpretacion._ejemplos())  # las instrucciones y ejemplos quedan completos


# ── Anclaje a lo que dice la pregunta ──────────────────────────────────────────

from services import anclaje  # noqa: E402


def test_anclaje_corrige_la_opcion_que_la_pregunta_escribe_tal_cual():
    cat = _cat_carga()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p03", "valor": "Trabajo menos de 20h"}]})
    nuevo, notas = anclaje.anclar(plan, "¿cuántos dicen que no trabajo?", [], cat)
    assert nuevo.filtros[0].valor == "No trabajo" and any("lo que dice la pregunta" in n for n in notas)


def test_anclaje_toma_respondente_y_pregunta_explicitos():
    cat = _cat_encuesta()
    plan = PlanConsulta(intencion="datos_respondente", limite=1)
    nuevo, _ = anclaje.anclar(plan, "¿qué respondió R003 en la pregunta 2?", [], cat)
    assert nuevo.respondentes == ["R003"] and nuevo.campos == ["p02"] and nuevo.limite is None


def test_anclaje_en_seguimiento_conserva_lo_heredado_agrega_lo_nuevo_y_quita_lo_inventado():
    cat = _cat_carga()
    plan = PlanConsulta.model_validate({"intencion": "filtrar_respondentes", "limite": 10, "filtros": [
        {"pregunta": "p01", "valor": "Sí, una vez"},          # heredado del historial: se conserva
        {"pregunta": "p04", "op": ">", "valor": 20}]})        # inventado: nadie habló de horas
    historial = [("usuario", "¿cuántos reprobaron por falta de tiempo una vez?"), ("asistente", "Cumplen 2 de 5.")]
    nuevo, notas = anclaje.anclar(plan, "¿y de ellos cuántos no trabajo?", historial, cat)
    assert [f.pregunta for f in nuevo.filtros] == ["p01", "p03"] and nuevo.filtros[1].valor == "No trabajo"
    assert nuevo.intencion == "conteo_porcentaje" and nuevo.limite is None
    assert any("p04" in n and "descartado" in n for n in notas)


def test_anclaje_conserva_sinonimos_que_comparten_palabras():
    cat = _cat_carga()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p01", "valor": ["Sí, una vez", "Sí, varias veces"]}]})
    nuevo, _ = anclaje.anclar(plan, "¿cuántos han reprobado alguna materia?", [], cat)
    assert nuevo.filtros == plan.filtros


def test_anclaje_nivel_contexto_polaridad_y_posicion():
    enc = _cat_encuesta()
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="comparar_grupos", preguntas=["p01"], agrupar_por="Turno"),
                              "compara el porcentaje de acuerdo en la pregunta 1 por turno", [], enc)
    assert nuevo.nivel == "acuerdo"
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje", preguntas=["p05"], nivel="acuerdo"),
                              "¿qué porcentaje del turno vespertino está de acuerdo con la pregunta 5?", [], enc)
    assert nuevo.contexto == {"Turno": "Vespertino"}
    filtro = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                          "filtros": [{"pregunta": "p01", "valor": "Totalmente de acuerdo"}]})
    nuevo, _ = anclaje.anclar(filtro, "¿cuántos están de acuerdo con que los profesores explican con claridad?", [], enc)
    assert nuevo.filtros[0].nivel == "acuerdo" and nuevo.filtros[0].valor is None
    carga = _cat_carga()
    nuevo, _ = anclaje.anclar(PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "filtros": [
        {"pregunta": "p01", "valor": "Sí, una vez"}]}), "¿cuántos han reprobado alguna materia por falta de tiempo?", [], carga)
    assert nuevo.filtros[0].valor == ["Sí, una vez", "Sí, varias veces"]
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="datos_respondente", campos=["p02"]),
                              "¿qué contestó el último respondente en la pregunta 2?", [], enc)
    assert nuevo.orden.dir == "desc" and nuevo.limite == 1
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="datos_respondente", respondentes=["R002"], campos="todas_las_respuestas"),
                              "¿qué respondió R002 en la pregunta 1?", [], enc)
    assert nuevo.campos == ["p01"]


def test_condicion_que_no_existe_pide_aclaracion_con_las_opciones_reales():
    carga = _cat_carga()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p04", "op": ">", "valor": 20}]})
    nuevo, notas = anclaje.anclar(plan, "¿cuántos tienen carga laboral nocturna?", [], carga)
    assert nuevo.intencion == "aclaracion" and "No trabajo" in nuevo.aclaracion


def test_comparar_ambos_instrumentos_no_es_variable_de_contexto():
    v = validar_contra_catalogo(PlanConsulta(intencion="comparar_grupos", preguntas=["p01"], agrupar_por="instrumento"),
                                [_cat_encuesta(), _cat_carga()])
    assert v.plan.intencion == "comparar_grupos" and v.plan.agrupar_por is None


def test_seguimiento_hereda_las_condiciones_de_la_pregunta_anterior():
    carga = _cat_carga()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p03", "valor": "No trabajo"}]})
    historial = [("usuario", "¿cuántos tienen dificultades para equilibrar trabajo y estudios?"), ("asistente", "Cumplen 2 de 5.")]
    nuevo, notas = anclaje.anclar(plan, "¿y de ellos cuántos no trabajo?", historial, carga)
    assert {f.pregunta for f in nuevo.filtros} == {"p03", "p02"}
    assert next(f for f in nuevo.filtros if f.pregunta == "p02").valor == ["Sí"]
    assert any("heredado" in n for n in notas)


def test_opcion_concreta_que_la_consulta_no_menciona_no_se_sostiene():
    """Regresión C13: «modalidad nocturna» no existe; el modelo filtró otra opción de la misma pregunta."""
    carga = _cat_carga()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p03", "valor": "Trabajo menos de 20h"}]})
    nuevo, _ = anclaje.anclar(plan, "¿cuántos tienen una carga laboral nocturna?", [], carga)
    assert nuevo.intencion == "aclaracion" and "No trabajo" in nuevo.aclaracion


def _cat_vf():
    """Prueba inventada con un reactivo de verdadero o falso cuyo enunciado comparte una palabra con un valor de contexto."""
    preguntas = {
        "r01": catalogo.PreguntaCatalogo("r01", "Usar la biblioteca pública de noche siempre es seguro.", "opcion",
                                         ["Verdadero", "Falso"]),
        "r02": catalogo.PreguntaCatalogo("r02", "¿Qué medio de transporte usas para llegar a la escuela?", "opcion",
                                         ["Autobús", "Bicicleta", "A pie"]),
        "r03": catalogo.PreguntaCatalogo("r03", "¿Con quién consultas tus dudas de orientación vocacional?", "opcion",
                                         ["Tutor", "Familia"]),
    }
    return catalogo.Catalogo("9", "Prueba de movilidad", "prueba_estandarizada", preguntas, ["A001", "A002"],
                             {"tipo_escuela": ["publica", "privada"], "tiene_beca": ["True", "False"]}, [])


def test_valor_de_contexto_que_es_parte_del_reactivo_citado_no_se_toma():
    """Fase 6 (consultas 1490 y 1526): «pública» era parte del enunciado y se filtró por el tipo de escuela; y el
    filtro «Verdadero» se descartaba porque la consulta no escribe «verdadero»."""
    cat = _cat_vf()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "r01", "valor": "Verdadero"}]})
    nuevo, notas = anclaje.anclar(plan, "¿Cuántos piensan que usar la biblioteca pública de noche es seguro?", [], cat)
    assert not nuevo.contexto and [(f.pregunta, f.valor) for f in nuevo.filtros] == [("r01", "Verdadero")]
    assert any("parte del reactivo" in n for n in notas)


def test_valor_de_contexto_se_toma_si_la_consulta_nombra_la_variable():
    cat = _cat_vf()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "r01", "valor": "Verdadero"}]})
    nuevo, _ = anclaje.anclar(plan, "¿Cuántos de escuela pública piensan que usar la biblioteca pública de noche es "
                                    "seguro?", [], cat)
    assert nuevo.contexto == {"tipo_escuela": "publica"} and nuevo.filtros[0].valor == "Verdadero"
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje", preguntas=["r02"]),
                              "¿qué porcentaje de los de la pública llega en autobús?", [], cat)
    assert nuevo.contexto == {"tipo_escuela": "publica"}  # no cita ningún reactivo que diga «pública»


def test_verdadero_sin_relacion_con_la_consulta_no_se_sostiene():
    cat = _cat_vf()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "r01", "valor": "Verdadero"}]})
    nuevo, notas = anclaje.anclar(plan, "¿cuántos consultan a su tutor?", [], cat)
    assert all(f.pregunta != "r01" for f in nuevo.filtros) and any("descartado" in n for n in notas)


def test_del_alcance_con_datos_de_contexto_y_palabras_de_preguntas_distintas():
    from services.consulta_planificada import del_alcance
    cat = _cat_vf()
    assert del_alcance("¿Y los que tienen beca contra los que no?", [cat])        # nombre del contexto
    assert del_alcance("¿y los de la privada?", [cat])                           # valor del contexto
    assert del_alcance("¿hay orientación en la biblioteca?", [cat])           # «bibli» en r01, «orien» en r03
    assert not del_alcance("¿quién ganó el mundial de futbol de 2010?", [cat])
    assert not del_alcance("dame una receta de pastel", [cat])
    assert not del_alcance("¿qué otro tipo de música te gusta?", [cat])          # «otro» y «tipo» no nombran nada


def _cat_numerica():
    """Encuesta inventada con datos de contexto numéricos (edad, semestre) y uno categórico."""
    preguntas = {
        "p01": catalogo.PreguntaCatalogo("p01", "¿Usas la biblioteca del campus?", "opcion", ["Sí", "No"]),
        "p02": catalogo.PreguntaCatalogo("p02", "¿Cuántas veces al mes visitas la cafetería?", "numerica"),
    }
    return catalogo.Catalogo("8", "Encuesta de servicios", "encuesta", preguntas, ["R001", "R002"],
                             {"campus": ["Norte", "Sur"]}, [], {"edad": (17.0, 45.0), "semestre_actual": (1.0, 12.0)})


def test_catalogo_detecta_contexto_numerico_y_lo_muestra():
    doc = docs_ejemplo.encuesta()
    for r, (edad, beca) in zip(doc["respondentes"], [("18", True), ("22", False), ("25", True), ("31", False), ("19", True)]):
        r["contexto"].update(Edad=edad, Beca=beca)
    cat = catalogo.construir("1", "Experiencia estudiantil", "encuesta", doc)
    assert cat.numericas == {"Edad": (18.0, 31.0)}  # «Beca» (True/False) y «Turno» no son numéricas
    assert "Contexto numérico: Edad (18–31)" in cat.texto()


def test_comparacion_de_contexto_se_valida_contra_el_catalogo():
    cat = _cat_numerica()
    v = validar_contra_catalogo(PlanConsulta.model_validate(
        {"intencion": "conteo_porcentaje", "contexto_num": [{"variable": "Edad", "op": ">", "valor": 20}]}), [cat])
    assert v.plan.contexto_num[0].variable == "edad" and any("edad" in c for c in v.correcciones)
    v = validar_contra_catalogo(PlanConsulta.model_validate(
        {"intencion": "conteo_porcentaje", "contexto_num": [{"variable": "ingresos", "op": ">", "valor": 20}]}), [cat])
    assert v.plan.intencion == "aclaracion" and "edad" in v.plan.aclaracion


def test_anclaje_arma_la_comparacion_de_contexto_que_la_consulta_escribe():
    cat = _cat_numerica()
    casos = [("¿cuántos tienen menos de 20 años de edad?", "edad", "<", 20),
             ("¿cuántos tienen más de 25 de edad?", "edad", ">", 25),
             ("¿quiénes van en al menos 6 semestres?", "semestre_actual", ">=", 6),
             ("¿cuántos del campus Norte llevan como máximo 3 semestres?", "semestre_actual", "<=", 3)]
    for consulta, var, op, valor in casos:
        nuevo, notas = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje"), consulta, [], cat)
        assert [(c.variable, c.op, c.valor) for c in nuevo.contexto_num] == [(var, op, valor)], consulta
        assert any("escrito en la pregunta" in n for n in notas)


def test_anclaje_no_adivina_la_variable_ni_duplica_la_del_modelo():
    cat = _cat_numerica()
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje"), "¿cuántos tienen más de 20?", [], cat)
    assert nuevo.contexto_num == []
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "contexto_num": [{"variable": "edad", "op": ">=", "valor": 21}]})
    nuevo, _ = anclaje.anclar(plan, "¿cuántos tienen más de 20 años de edad?", [], cat)
    assert [(c.op, c.valor) for c in nuevo.contexto_num] == [(">=", 21)]


def test_filtro_numerico_mal_ubicado_pasa_a_la_comparacion_de_contexto():
    """gemma puso «r04 > 20» (la pregunta del ejemplo con horas) en lugar de las horas del contexto (consulta 1486)."""
    cat = _cat_numerica()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p01", "op": ">", "valor": 20}]})
    nuevo, notas = anclaje.anclar(plan, "¿cuántos tienen más de 20 años de edad?", [], cat)
    assert nuevo.intencion == "conteo_porcentaje" and nuevo.filtros == []
    assert [(c.variable, c.valor) for c in nuevo.contexto_num] == [("edad", 20)]
    # Una pregunta numérica que la consulta sí cita se queda como filtro de la pregunta.
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p02", "op": ">", "valor": 3}]})
    nuevo, _ = anclaje.anclar(plan, "¿cuántos visitan la cafetería más de 3 veces al mes?", [], cat)
    assert [(f.pregunta, f.valor) for f in nuevo.filtros] == [("p02", 3)] and nuevo.contexto_num == []


def _cat_prueba():
    preguntas = {
        "r01": catalogo.PreguntaCatalogo("r01", "¿Qué es una contraseña segura?", "opcion", ["A) Tu nombre", "B) 12 caracteres"]),
        "r02": catalogo.PreguntaCatalogo("r02", "¿Para qué sirve una VPN?", "opcion", ["A) Navegar", "B) Cifrar"]),
        "r03": catalogo.PreguntaCatalogo("r03", "¿Qué es el phishing por correo?", "opcion", ["A) Fraude", "B) Juego"]),
        "r04": catalogo.PreguntaCatalogo("r04", "El correo electrónico siempre es seguro.", "opcion", ["Verdadero", "Falso"]),
    }
    return catalogo.Catalogo("7", "Prueba de seguridad", "prueba_estandarizada", preguntas, ["A001"], {}, [])


def test_anclaje_pasa_a_ranking_con_criterio_y_exclusion():
    cat = _cat_prueba()
    nuevo, notas = anclaje.anclar(PlanConsulta(intencion="hallazgo"),
                                  "¿En qué pregunta hubo más respuestas nulas o sin contestar, sin contar la de la contraseña?",
                                  [], cat)
    assert (nuevo.intencion, nuevo.criterio_ranking, nuevo.excluir_preguntas) == ("ranking_preguntas", "no_respuesta", ["r01"])
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="hallazgo"), "¿Hay alguna donde casi todos eligieron lo mismo?", [], cat)
    assert (nuevo.intencion, nuevo.criterio_ranking) == ("ranking_preguntas", "coincidencia")
    # Desde una aclaración que armó la validación (consulta 1529).
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="aclaracion", aclaracion="«A» no es una opción de r01. ¿Cuál quieres?"),
                              "¿En qué pregunta hubo más respuestas nulas, sin contar la de la contraseña?", [], cat)
    assert (nuevo.intencion, nuevo.excluir_preguntas, nuevo.aclaracion) == ("ranking_preguntas", ["r01"], "")
    # Una aclaración sin señales de ranking se queda igual.
    plan = PlanConsulta(intencion="aclaracion", aclaracion="¿De qué pregunta hablas?")
    assert anclaje.anclar(plan, "¿y eso qué significa?", [], cat) == (plan, [])
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="hallazgo"), "¿cuál pregunta tiene las respuestas más divididas, "
                                                                   "excepto la pregunta 2?", [], cat)
    assert (nuevo.criterio_ranking, nuevo.excluir_preguntas) == ("repartida", ["r02"])


def test_anclaje_no_adivina_la_exclusion_ni_convierte_sin_criterio():
    cat = _cat_prueba()
    # «correo» está en r03 y en r04: no se adivina cuál.
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="ranking_preguntas", criterio_ranking="no_respuesta"),
                              "¿en qué pregunta hubo más respuestas en blanco, sin contar la del correo?", [], cat)
    assert nuevo.excluir_preguntas == []
    # Sin criterio de ranking («más desacuerdo») sigue siendo hallazgo; «alguna sin responder» de un respondente tampoco.
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="hallazgo"), "¿en qué pregunta hubo más desacuerdo?", [], cat)
    assert nuevo.intencion == "hallazgo"
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje"),
                              "¿cuántos dejaron alguna pregunta sin responder?", [], cat)
    assert nuevo.intencion == "conteo_porcentaje"


def test_exclusion_se_valida_contra_el_catalogo():
    v = validar_contra_catalogo(PlanConsulta(intencion="ranking_preguntas", criterio_ranking="no_respuesta",
                                             excluir_preguntas=["r1", "r99"]), [_cat_prueba()])
    assert v.plan.excluir_preguntas == ["r01"] and any("r99" in c for c in v.correcciones)


def test_anclaje_arma_el_conteo_de_menciones():
    """Fase 6: gemma contó «nivel alto en p02» (1468) y qwen pidió el resumen de p02 (1540)."""
    cat = _cat_encuesta()
    for plan in (PlanConsulta(intencion="conteo_porcentaje", preguntas=["p02"], nivel="alto"),
                 PlanConsulta(intencion="semantica_abierta", consulta_semantica="ansiedad")):
        nuevo, notas = anclaje.anclar(plan, "¿Cuántos entrevistados mencionaron la ansiedad?", [], cat)
        assert (nuevo.intencion, nuevo.menciona, nuevo.preguntas, nuevo.nivel) == ("conteo_porcentaje", "ansiedad", [], None)
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="hallazgo"), "¿quiénes hablaron del estrés en la pregunta 2?", [], cat)
    assert (nuevo.intencion, nuevo.menciona, nuevo.preguntas) == ("filtrar_respondentes", "estres", ["p02"])


def test_anclaje_sin_cuantos_ni_quienes_no_cuenta_menciones():
    cat = _cat_encuesta()
    plan = PlanConsulta(intencion="semantica_abierta", consulta_semantica="biblioteca")
    nuevo, _ = anclaje.anclar(plan, "¿qué mencionaron sobre la biblioteca?", [], cat)
    assert nuevo.intencion == "semantica_abierta" and nuevo.menciona == ""


def _cat_entrevista_con_contexto():
    """Entrevista inventada de una persona con contexto en su encabezado (la corrección 7 lo deja visible al modelo)."""
    preguntas = {
        "p01": catalogo.PreguntaCatalogo("p01", "¿Cuánto tardaste en conseguir una beca?", "guia"),
        "p02": catalogo.PreguntaCatalogo("p02", "¿Qué te frenó al pedirla?", "guia"),
    }
    return catalogo.Catalogo("3", "Becas en la universidad", "entrevista", preguntas, ["E01"],
                             {"Turno": ["vespertino"], "Trabaja": ["sí, 10 horas"], "Edad": ["24"]}, [])


def test_condiciones_que_la_pregunta_no_dice_se_quitan_antes_de_validar(monkeypatch):
    """Fase 6, segunda corrida (1548, 1556): el modelo inventó «Trabaja = sí» y copió «Edad > 25» del ejemplo del
    prompt; la validación los volvía una aclaración absurda."""
    cat = _cat_entrevista_con_contexto()
    _ollama(monkeypatch, [json.dumps({"intencion": "datos_respondente", "respondentes": ["E01"], "contexto": {"Trabaja": "sí"}})])
    r = asyncio.run(interpretacion.interpretar("¿Cuánto tardó en conseguir la beca?", [], [cat]))
    assert r.plan.intencion == "datos_respondente" and r.plan.contexto == {}
    assert any("Trabaja" in c and "descartado" in c for c in r.correcciones)
    _ollama(monkeypatch, [json.dumps({"intencion": "datos_respondente", "respondentes": ["E01"],
                                      "contexto_num": [{"variable": "Edad", "op": ">", "valor": 25}]})])
    r = asyncio.run(interpretacion.interpretar("¿En qué turno estudia?", [], [cat]))
    assert r.plan.intencion == "datos_respondente" and r.plan.contexto_num == []


def test_condiciones_que_la_pregunta_si_dice_se_validan_como_siempre(monkeypatch):
    cat = _cat_entrevista_con_contexto()
    _ollama(monkeypatch, [json.dumps({"intencion": "conteo_porcentaje", "contexto": {"Turno": "nocturno"}})])
    r = asyncio.run(interpretacion.interpretar("¿cuántos del turno nocturno hay?", [], [cat]))
    assert r.plan.intencion == "aclaracion"  # lo dice la pregunta pero no existe: se pregunta, como antes
    _ollama(monkeypatch, [json.dumps({"intencion": "conteo_porcentaje", "contexto": {"Turno": "vespertino"}})])
    r = asyncio.run(interpretacion.interpretar("¿y de ellos cuántos van en la tarde?", [("usuario", "¿cuántos son del vespertino?")], [cat]))
    assert r.plan.contexto == {"Turno": "vespertino"}  # lo dijo la pregunta anterior


def test_mencion_que_la_pregunta_no_pide_se_quita(monkeypatch):
    """1551: «¿Qué la detuvo antes de buscar ayuda?» → mención «detenerse», 0 de 1."""
    cat = _cat_entrevista_con_contexto()
    _ollama(monkeypatch, [json.dumps({"intencion": "conteo_porcentaje", "menciona": "frenar", "preguntas": ["p02"]})])
    r = asyncio.run(interpretacion.interpretar("¿Qué la frenó al pedir la beca?", [], [cat]))
    assert r.plan.menciona == ""
    _ollama(monkeypatch, [json.dumps({"intencion": "conteo_porcentaje", "menciona": "beca"})])
    r = asyncio.run(interpretacion.interpretar("¿Cuántos mencionaron la beca?", [], [cat]))
    assert r.plan.menciona == "beca"


def test_dato_de_contexto_puesto_como_pregunta_pasa_al_contexto():
    """Fase 6 (consultas 1583 y 1594): el modelo puso «horas»/«primera_generacion» en `filtros[].pregunta` y la
    validación respondía «No encontré la pregunta "primera_generacion"»."""
    cat = _cat_numerica()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["8"],
                                        "filtros": [{"pregunta": "edad", "op": ">", "valor": 25}]})
    nuevo, notas = anclaje.sin_inventos(plan, "¿cuántos tienen más de 25 años de edad?", [], [cat])
    assert not nuevo.filtros and [(c.variable, c.op, c.valor) for c in nuevo.contexto_num] == [("edad", ">", 25.0)]
    assert validar_contra_catalogo(nuevo, [cat]).plan.intencion == "conteo_porcentaje"
    vf = _cat_vf()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["9"],
                                        "filtros": [{"pregunta": "tiene_beca", "valor": "sí"}]})
    nuevo, _ = anclaje.sin_inventos(plan, "¿cuántos con beca llegan en bicicleta?", [], [vf])
    assert nuevo.contexto == {"tiene_beca": "True"} and not nuevo.filtros
    # Si la consulta no habla de esa variable, no se toma.
    nuevo, notas = anclaje.sin_inventos(plan, "¿cuántos llegan en bicicleta?", [], [vf])
    assert not nuevo.contexto and any("descartado" in n for n in notas)


def test_valor_que_no_es_opcion_ni_se_menciona_se_descarta_antes_de_validar():
    """Fase 6 (consultas 1600, 1607, 1612): «A)» o «sin contestar» en r01 se volvían «"A)" no es una opción de r01…»."""
    vf = _cat_vf()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["9"],
                                        "filtros": [{"pregunta": "r02", "valor": "A)"}]})
    nuevo, notas = anclaje.sin_inventos(plan, "¿cuántos estudian medicina?", [], [vf])
    assert nuevo.intencion == "aclaracion" and "No encontré esa condición" in nuevo.aclaracion
    assert "no es una opción" in notas[0]
    # Si la consulta sí escribe ese valor, la validación pregunta cuál opción es (como antes).
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["9"],
                                        "filtros": [{"pregunta": "r02", "valor": "metro"}]})
    nuevo, _ = anclaje.sin_inventos(plan, "¿cuántos llegan en metro?", [], [vf])
    assert [f.valor for f in nuevo.filtros] == ["metro"]
    # Una opción reconocible no se toca.
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["9"],
                                        "filtros": [{"pregunta": "r02", "valor": "Bicicleta"}]})
    assert anclaje.sin_inventos(plan, "¿cuántos llegan en bici?", [], [vf])[0].filtros == plan.filtros


def test_valor_que_son_palabras_del_enunciado_queda_como_pregunta():
    """Fase 6 (consulta 1617): «Big Data» es parte del enunciado de r22, no una opción."""
    vf = _cat_vf()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["9"],
                                        "filtros": [{"pregunta": "r03", "valor": "orientación vocacional"}]})
    nuevo, notas = anclaje.sin_inventos(plan, "cuantos con beca contestaron la de orientación vocacional", [], [vf])
    assert not nuevo.filtros and nuevo.preguntas == ["r03"] and "enunciado" in notas[0]


def test_variable_de_si_o_no_nombrada_se_toma_con_su_negacion():
    vf = _cat_vf()
    plan = PlanConsulta(intencion="conteo_porcentaje", preguntas=["r02"])
    nuevo, _ = anclaje.anclar(plan, "¿cuántos de los que tienen beca llegan en autobús?", [], vf)
    assert nuevo.contexto == {"tiene_beca": "True"}
    nuevo, _ = anclaje.anclar(plan, "¿cuántos de los que no tienen beca llegan en autobús?", [], vf)
    assert nuevo.contexto == {"tiene_beca": "False"}
    nuevo, _ = anclaje.anclar(plan, "¿cuántos llegan en autobús?", [], vf)
    assert not nuevo.contexto
    # Agrupar por la variable («los que tienen beca contra los que no») no es filtrar por ella.
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="comparar_grupos", preguntas=["r02"], agrupar_por="tiene_beca"),
                              "¿y los que tienen beca contra los que no?", [], vf)
    assert not nuevo.contexto
