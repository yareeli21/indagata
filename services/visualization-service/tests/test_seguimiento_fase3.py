"""Fase 3 (7 nov): «muéstrame N de ellos», «muéstrame los datos tal cual» y la persona de la que se habla."""
from __future__ import annotations

from services import seguimiento
from services.plan_consulta import PlanConsulta

GRUPO = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Mixta"},
                                                         {"pregunta": "p10", "valor": "Estoy considerando abandonar"}]}
AMBIGUO = PlanConsulta(intencion="aclaracion", aclaracion="¿De qué pregunta?")


def _combinar(pregunta: str, anterior: dict, plan: PlanConsulta = AMBIGUO) -> tuple[PlanConsulta, list[str]]:
    rel = seguimiento.relacion(pregunta, plan, anterior)
    return seguimiento.combinar(plan, anterior, rel, [], pregunta, [])


def test_muestrame_n_de_ellos_lista_n_del_grupo_anterior_con_sus_respuestas():
    for pregunta, n in (("Muéstrame 5 de ellos", 5), ("Muéstrame 5", 5), ("dame tres", 3)):
        plan, notas = _combinar(pregunta, GRUPO)
        assert plan.intencion == "filtrar_respondentes" and plan.limite == n, pregunta
        assert [f.pregunta for f in plan.filtros] == ["p02", "p10"] and plan.campos == "todas_las_respuestas"
        assert notas and notas[0].startswith("listar")
    # Sin un grupo anterior no hay a quién listar: sigue el plan del modelo.
    plan, _ = _combinar("Muéstrame 5", {"intencion": "kpi"})
    assert plan.intencion == "aclaracion"


def test_muestrame_los_datos_tal_cual_tras_un_ranking_da_la_distribucion_de_la_primera():
    ranking = {"intencion": "ranking_preguntas", "criterio_ranking": "repartida",
               "_respuesta": "La pregunta p07 «¿En qué actividades…?» es la más repartida. | 1 | p07 | … | 2 | p04 |"}
    plan, notas = _combinar("Muéstrame los datos tal cual", ranking)
    assert plan.intencion == "resumen_pregunta" and plan.preguntas == ["p07"] and "p07" in notas[0]
    plan, _ = _combinar("Muéstrame cómo se repartieron las respuestas",
                        {"intencion": "conteo_porcentaje", "preguntas": ["r16"]})
    assert plan.intencion == "resumen_pregunta" and plan.preguntas == ["r16"]


def test_una_persona_en_singular_sin_nombrarla_es_la_ultima_de_la_conversacion():
    plan = PlanConsulta(intencion="semantica_abierta", consulta_semantica="phishing", preguntas=["r04"])
    nuevo, notas = seguimiento.persona_activa("¿Su respuesta al reactivo de phishing es la más común?", plan, ["A001"])
    assert nuevo.intencion == "datos_respondente" and nuevo.respondentes == ["A001"] and nuevo.campos == ["r04"]
    assert notas and "A001" in notas[0]
    # En plural habla de un grupo, no de la persona.
    igual, _ = seguimiento.persona_activa("¿Cuántos alumnos dejaron alguno en blanco?", plan, ["A001"])
    assert igual is plan
    # Sin persona en la conversación no cambia nada.
    assert seguimiento.persona_activa("¿Dejó alguno en blanco?", plan, [])[0] is plan


def test_de_ellos_con_una_opcion_nombrada_acota_el_grupo_anterior():
    from services import catalogo

    preguntas = {
        "p14": catalogo.PreguntaCatalogo("p14", "¿Has realizado prácticas profesionales?", "categorica",
                                         ["Si, pero la consegui por mi cuenta", "Si, en una empresa con convenio de mi institucion",
                                          "Aun no, pero planeo hacerlo", "No"]),
        "p03": catalogo.PreguntaCatalogo("p03", "¿Cuál es tu carga laboral?", "categorica",
                                         ["No trabajo", "Trabajo menos de 20h", "Trabajo más de 30h"]),
    }
    cat = catalogo.Catalogo("5", "Encuesta de egreso", "encuesta", preguntas, ["R001"], {}, [])
    anterior = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p14", "valor": [
        "Si, pero la consegui por mi cuenta", "Si, en una empresa con convenio de mi institucion"]}]}
    plan = PlanConsulta(intencion="conteo_porcentaje")
    nuevo, notas = seguimiento.combinar(plan, anterior, "continua", [], "¿Y de ellos, cuántos la consiguieron por convenio?", [cat])
    assert [(f.pregunta, f.valor) for f in nuevo.filtros] == [("p14", "Si, en una empresa con convenio de mi institucion")]
    nuevo, _ = seguimiento.combinar(plan, anterior, "continua", [], "¿Y de ellos, cuántos no trabajan?", [cat])
    assert ("p03", "No trabajo") in [(f.pregunta, f.valor) for f in nuevo.filtros] and len(nuevo.filtros) == 2


def test_de_ellos_conserva_la_condicion_anterior_que_la_pregunta_no_menciona():
    from services import catalogo

    preguntas = {
        "p15": catalogo.PreguntaCatalogo("p15", "¿Tienes dificultades para equilibrar trabajo y estudios?", "binaria", ["Sí", "No"]),
        "p14": catalogo.PreguntaCatalogo("p14", "¿Cuál es tu carga laboral actual?", "categorica", ["No trabajo", "Trabajo 20-30h"]),
    }
    cat = catalogo.Catalogo("6", "Encuesta de carga", "encuesta", preguntas, ["R001"], {}, [])
    anterior = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p15", "valor": "Sí"}]}
    plan = PlanConsulta(intencion="conteo_porcentaje", filtros=[{"pregunta": "p15", "valor": "No"},
                                                                 {"pregunta": "p14", "valor": "No trabajo"}])
    nuevo, notas = seguimiento.combinar(plan, anterior, "continua", [], "¿Y de ellos, cuántos no trabajan?", [cat])
    assert {(f.pregunta, f.valor) for f in nuevo.filtros} == {("p15", "Sí"), ("p14", "No trabajo")}
    # Si la consulta habla de esa pregunta, el cambio se respeta.
    plan = PlanConsulta(intencion="conteo_porcentaje", filtros=[{"pregunta": "p15", "valor": "No"}])
    nuevo, _ = seguimiento.combinar(plan, anterior, "continua", [], "¿Y los que no tienen dificultades?", [cat])
    assert [(f.pregunta, f.valor) for f in nuevo.filtros] == [("p15", "No")]
