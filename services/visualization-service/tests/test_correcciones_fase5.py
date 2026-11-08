"""Correcciones de la evaluación final del chat (Fase 5, 8 nov 2026), con catálogos inventados."""
from __future__ import annotations

from services import anclaje, catalogo, rag_service, seguimiento
from services.plan_consulta import Filtro, PlanConsulta, validar_contra_catalogo


def _cat() -> catalogo.Catalogo:
    preguntas = {
        "p01": catalogo.PreguntaCatalogo("p01", "¿Cuántas horas trabajas?", "opcion",
                                         ["No trabajo", "Trabajo menos de 10h", "Trabajo 10-20h", "Trabajo más de 20h"]),
        "p02": catalogo.PreguntaCatalogo("p02", "¿Cuándo piensas terminar la carrera?", "opcion",
                                         ["A tiempo", "Con retraso", "Estoy pensando en cambiarme de escuela"]),
        "p03": catalogo.PreguntaCatalogo("p03", "¿Cuántas horas duermes? (número)", "numerica"),
    }
    return catalogo.Catalogo("8", "Encuesta de hábitos", "encuesta", preguntas, ["R001", "R002"], {}, [])


def test_opcion_abreviada_se_empareja_por_sus_palabras():
    plan = PlanConsulta(intencion="conteo_porcentaje", filtros=[{"pregunta": "p02", "valor": "Cambiarme"}])
    validado = validar_contra_catalogo(plan, [_cat()])
    assert validado.plan.intencion == "conteo_porcentaje"
    assert validado.plan.filtros[0].valor == "Estoy pensando en cambiarme de escuela"


def test_mas_de_n_escrito_elige_esa_opcion_y_quita_el_mismo_numero_en_otra_pregunta():
    notas: list[str] = []
    filtros = [Filtro(pregunta="p01", valor=["Trabajo menos de 10h", "Trabajo 10-20h", "Trabajo más de 20h"]),
               Filtro(pregunta="p03", op=">", valor=20)]
    quedan = anclaje._por_cantidad_escrita(filtros, "cuantos trabajan mas de 20 horas", notas)
    assert [(f.pregunta, f.valor) for f in quedan] == [("p01", "Trabajo más de 20h")]


def test_palabras_del_instrumento_no_son_condiciones_ausentes():
    assert "reactivo" not in anclaje._ausentes("¿Cuántos eligieron A en el reactivo de horas?", _cat())


def test_de_ellos_sobre_otra_pregunta_es_un_cruce_con_el_grupo_anterior():
    anterior = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p01", "valor": "No trabajo"}]}
    plan = PlanConsulta(intencion="semantica_abierta", preguntas=["p02"], relacion="continua",
                        consulta_semantica="terminar la carrera")
    pregunta = "De ellos, ¿qué respondieron sobre terminar la carrera?"
    rel = seguimiento.relacion(pregunta, plan, anterior)
    combinado, _ = seguimiento.combinar(plan, anterior, rel, [], pregunta, [_cat()])
    assert combinado.intencion == "resumen_pregunta"
    assert [f.pregunta for f in combinado.filtros] == ["p01"]


def test_de_ellos_cuantos_guarda_el_grupo_anterior_como_base():
    anterior = {"intencion": "conteo_porcentaje",
                "filtros": [{"pregunta": "p01", "valor": ["Trabajo menos de 10h", "Trabajo 10-20h", "Trabajo más de 20h"]}]}
    plan = PlanConsulta(intencion="conteo_porcentaje", filtros=[{"pregunta": "p01", "valor": "Trabajo más de 20h"}])
    pregunta = "¿Y de ellos, cuántos trabajan más de 20h?"
    rel = seguimiento.relacion(pregunta, plan, anterior)
    combinado, _ = seguimiento.combinar(plan, anterior, rel, [], pregunta, [_cat()])
    assert [f.valor for f in combinado.grupo_anterior] == [anterior["filtros"][0]["valor"]]
    # El modelo no lo puede poner por su cuenta.
    propio = PlanConsulta(intencion="conteo_porcentaje", grupo_anterior=[{"pregunta": "p01", "valor": "No trabajo"}])
    assert seguimiento.combinar(propio, None, "nueva")[0].grupo_anterior == []


def test_seguimiento_de_una_persona_interpretado_como_metodologia_sigue_con_ella():
    anterior = {"intencion": "datos_respondente", "respondentes": ["E03"]}
    plan = PlanConsulta(intencion="metodologia", aclaracion="¿Te refieres a las de E03 o en general?")
    pregunta = "¿Y qué hace para organizarse?"
    combinado, _ = seguimiento.combinar(plan, anterior, seguimiento.relacion(pregunta, plan, anterior), [], pregunta)
    assert combinado.intencion == "datos_respondente" and combinado.respondentes == ["E03"]


def test_porcentaje_atribuido_a_otra_opcion_se_detecta():
    anexo = ("**Comparación por p01**\n| Grupo | Personas | p02: respuestas del grupo |\n|---|---|---|\n"
             "| No trabajo | 40 | «A tiempo» 20 (50.0 %); «Con retraso» 12 (30.0 %) |")
    assert rag_service.cifra_mal_atribuida("Los que no trabajan terminan con retraso en un 50.0 %.", anexo, "")
    assert not rag_service.cifra_mal_atribuida("De los que no trabajan, el 50.0 % piensa terminar a tiempo.", anexo, "")
    # Un porcentaje que también está fuera de las tablas (el conteo) no se revisa.
    assert not rag_service.cifra_mal_atribuida("Son 40 personas, el 50.0 %.", anexo, "Cumplen 40 de 80 (50.0 %).")


def test_ranking_redactado_en_otro_orden_se_detecta():
    anexo = "| Lugar | Pregunta | Dato |\n|---|---|---|\n| 1 | p02 | índice 0.99 |\n| 2 | p01 | índice 0.95 |"
    assert rag_service.ranking_desordenado("La más repartida es p01, seguida de p02.", anexo)
    assert not rag_service.ranking_desordenado("La más repartida es p02.", anexo)


def test_lenguaje_de_calificacion_en_pruebas_sin_contar_el_texto_del_reactivo():
    contexto = "r05 «¿Cuál es el paso correcto para guardar un archivo?»"
    assert rag_service.califica_prueba("La mayoría eligió respuestas incorrectas.", contexto)
    assert rag_service.califica_prueba("Muestra una mayor dificultad en esa sección.", contexto)
    assert not rag_service.califica_prueba("Eligió B en la pregunta sobre el paso correcto para guardar.", contexto)
    assert not rag_service.califica_prueba("Eligió «el paso correcto» según el enunciado.", "")
