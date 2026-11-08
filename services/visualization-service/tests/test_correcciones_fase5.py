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


def test_registro_guarda_el_plan_del_modelo_y_el_catalogo():
    from services import consulta_planificada, interpretacion

    final = PlanConsulta(intencion="conteo_porcentaje", filtros=[{"pregunta": "p01", "valor": "Trabajo más de 20h"}])
    interp = interpretacion.Interpretacion(plan=final, catalogo="CATÁLOGO…",
                                           crudo='{"intencion": "conteo_porcentaje", "filtros": '
                                                 '[{"pregunta": "p01", "valor": "más de 20"}]}')
    registro = consulta_planificada.Preparada(interp).registro()
    assert registro["plan_modelo"]["filtros"][0]["valor"] == "más de 20"
    assert registro["plan_modelo_sin_cambios"] is False and registro["catalogo"] == "CATÁLOGO…"
    interp.crudo = '{"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p01", "valor": "Trabajo más de 20h"}]}'
    assert consulta_planificada.Preparada(interp).registro()["plan_modelo_sin_cambios"] is True
    assert consulta_planificada.plan_del_modelo("no es json") == "no es json"


def test_redaccion_que_nombra_solo_una_de_las_opciones_del_criterio():
    registro = {"plan": {"filtros": [{"pregunta": "p05", "valor": ["Nada útil", "2 en escala 1–4"]}]}}
    assert rag_service.opciones_omitidas("721 (36.0 %) respondieron «Nada útil».", registro)
    assert not rag_service.opciones_omitidas("721 (36.0 %) respondieron «Nada útil» o 2 en la escala.", registro)
    assert not rag_service.opciones_omitidas("Cualquier texto.", {"plan": {"filtros": [{"pregunta": "p05", "valor": "Nada útil"}]}})


def test_cuantos_marcaron_una_opcion_con_el_reactivo_en_campos_es_una_condicion():
    preguntas = {"r01": catalogo.PreguntaCatalogo("r01", "Guardar en la nube evita perder archivos.", "opcion",
                                                  ["Verdadero", "Falso"]),
                 "r02": catalogo.PreguntaCatalogo("r02", "Una contraseña larga es más segura.", "opcion",
                                                  ["Verdadero", "Falso"])}
    cat = catalogo.Catalogo("9", "Prueba de ejemplo", "prueba_estandarizada", preguntas, ["A001"], {}, [])
    plan = PlanConsulta(intencion="conteo_porcentaje", campos=["r01"])
    anclado, _ = anclaje.anclar(plan, "¿Cuántos marcaron Verdadero en el reactivo de la nube?", [], cat)
    assert [(f.pregunta, f.valor) for f in anclado.filtros] == [("r01", "Verdadero")]


def test_que_conviene_revisar_es_un_ranking_sin_calificar():
    assert anclaje._criterio_ranking("que reactivos convendria revisar por como se respondieron") == "revisar"
    assert rag_service.califica_prueba("Esto indica una falta de comprensión del tema.")
    assert rag_service.califica_prueba("Su respuesta se corresponde con la definición de la prueba.")


def test_la_comprobacion_de_pruebas_reconoce_el_tipo_de_la_tarjeta():
    """El tipo de la fuente es el de la interfaz («Prueba estandarizada»); la primera versión comparaba con «prueba» y
    nunca se activaba (8 nov, corrida final)."""
    from models import FuenteChatOut

    def plan_con(tipo: str) -> rag_service.Plan:
        return rag_service.Plan(fuentes=[FuenteChatOut(numero=1, instrumentoId="9", titulo="X", tipo=tipo,
                                                       investigador="", kpis=[], fragmento="")])
    assert rag_service._es_prueba(plan_con("Prueba estandarizada"))
    assert not rag_service._es_prueba(plan_con("Encuesta"))


def test_ranking_desordenado_reconoce_reactivos():
    anexo = "| Lugar | Pregunta | Dato |\n|---|---|---|\n| 1 | r17 | índice 1.00 |\n| 2 | r12 | índice 0.99 |"
    assert rag_service.ranking_desordenado("La primera es el reactivo r12.", anexo)
    assert not rag_service.ranking_desordenado("La primera es el reactivo r17.", anexo)


def test_numero_de_reactivo_fuera_de_rango_no_existe():
    preguntas = {f"r{n:02d}": catalogo.PreguntaCatalogo(f"r{n:02d}", f"Reactivo {n}", "opcion", ["A) Sí", "B) No"])
                 for n in range(1, 16)}
    cat = catalogo.Catalogo("9", "Prueba de ejemplo", "prueba_estandarizada", preguntas, ["A001"], {}, [])
    plan, notas = anclaje.anclar(PlanConsulta(intencion="resumen_pregunta", preguntas=["r02"]),
                                 "¿Qué respondieron en el reactivo 20?", [], cat)
    assert plan.intencion == "aclaracion" and "15 reactivos" in plan.aclaracion


def test_no_se_resume_una_pregunta_filtrada_por_su_propia_opcion():
    preguntas = {"r01": catalogo.PreguntaCatalogo("r01", "¿Para qué sirve un índice?", "opcion",
                                                  ["A) Para buscar", "B) Para borrar"]),
                 "r02": catalogo.PreguntaCatalogo("r02", "La nube es segura.", "opcion", ["Verdadero", "Falso"])}
    cat = catalogo.Catalogo("9", "Prueba de ejemplo", "prueba_estandarizada", preguntas, ["A001"], {}, [])
    plan = PlanConsulta(intencion="resumen_pregunta", preguntas=["r01"],
                        filtros=[{"pregunta": "r01", "valor": "B) Para borrar"}])
    anclado, _ = anclaje.anclar(plan, "De ellos, ¿qué eligieron en el reactivo del índice?", [], cat)
    assert anclado.filtros == []


def test_contexto_que_acompana_a_la_frase_del_dato():
    plan = rag_service.Plan()
    assert rag_service.contexto_aceptable("La pregunta trata de la carga laboral (p03) [Fuente 1].", plan)
    assert not rag_service.contexto_aceptable("Son 3 de cada 5 [Fuente 1].", plan)       # cifras: ya van en la frase
    assert not rag_service.contexto_aceptable("No tengo información sobre eso.", plan)    # niega el resultado
    assert not rag_service.contexto_aceptable("Criterio: p03 = No trabajo.", plan)
