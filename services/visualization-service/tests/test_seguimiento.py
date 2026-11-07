"""A + B (7 nov): interpretar lo que no está literal y sostener el hilo de una conversación con varios temas.

Cada prueba reproduce, sobre catálogos inventados, una consulta que la investigadora calificó mal el 6 nov: «¿cuántos
trabajan?» (2149), «modalidad nocturna» (2147), «¿cuántos estudian ingeniería?» (2195), «¿y los que tienen beca
contra los que no?» (2187), «de esos, ¿cuántos dejaron alguna pregunta sin responder?» (2189), «¿y sobre los
psicólogos?» (2176), «¿por qué nadie la contestó?» (2185) y «¿a qué carrera está aplicada esta encuesta?» (2153).
"""
from __future__ import annotations

from services import anclaje, catalogo, ejecutor, enrutador, rag_service, seguimiento
from services.plan_consulta import PlanConsulta
from tests import docs_ejemplo

_LABORAL = ["Busco empleo", "Trabajo en un area relacionada con mi carrera", "Trabajo en un area no relacionada",
            "No trabajo ni busco empleo por ahora"]


def _cat_127():
    """Como el 127: la carga y la situación laboral; la palabra «trabajo» solo está en las opciones de p12."""
    preguntas = {
        "p02": catalogo.PreguntaCatalogo("p02", "¿En qué modalidad cursas tu programa?", "categorica",
                                         ["Presencial", "Mixta/hibrida", "En linea"]),
        "p03": catalogo.PreguntaCatalogo("p03", "¿Cómo es tu carga académica actual?", "opcion",
                                         ["Carga media/normal", "Cargas maxima", "Carga minima"]),
        "p12": catalogo.PreguntaCatalogo("p12", "¿Cuál es tu situación laboral actual?", "categorica", _LABORAL),
    }
    return catalogo.Catalogo("127", "Indicadores de Experiencia y Calidad Académica", "encuesta", preguntas,
                             ["R001", "R002"], {}, [])


def _cat_130():
    """Como el 130: sin carrera; con nivel de estudio, beca y horas de trabajo como datos de contexto."""
    preguntas = {
        "r04": catalogo.PreguntaCatalogo("r04", "¿Qué es el phishing?", "opcion_multiple",
                                         ["A) Una búsqueda", "B) Un intento fraudulento"]),
        "r10": catalogo.PreguntaCatalogo("r10", "¿Qué es una contraseña segura?", "opcion_multiple",
                                         ["A) Tu mascota", "B) 12 caracteres"]),
    }
    return catalogo.Catalogo("130", "Prueba de Alfabetización Digital", "prueba_estandarizada", preguntas,
                             ["A001", "A002"], {"nivel_estudio": ["pregrado", "posgrado"], "tiene_beca": ["False", "True"],
                                                "tipo_universidad": ["publica", "privada"]},
                             [], {"horas_trabajo_semana": (0.0, 50.0)})


# ── A: lo que no está literal ──────────────────────────────────────────────────


def test_trabajan_se_encuentra_en_las_opciones_de_otra_pregunta():
    cat = _cat_127()
    assert anclaje.opciones_por_raiz("¿cuántos trabajan?", cat) == {"p12": _LABORAL[1:3]}
    assert anclaje.opciones_por_raiz("¿cuántos no trabajan?", cat) == {"p12": [_LABORAL[3]]}
    # «carga» está en TODAS las opciones de p03: no filtra nada.
    assert anclaje.opciones_por_raiz("¿cómo es la carga?", cat) == {}
    # «nocturna» no está en el instrumento: «estudian» no se cambia por la opción «…plan de estudios» (consulta 2204).
    cat.preguntas["p10"] = catalogo.PreguntaCatalogo("p10", "¿Cuándo esperas titularte?", "categorica",
                                                     ["En el tiempo que marca mi plan de estudios", "Con retraso"])
    assert anclaje.opciones_por_raiz("¿cuántos estudian en modalidad nocturna?", cat) == {}
    assert anclaje.opciones_por_raiz("¿cuántos estudian?", cat) == {}


def test_el_anclaje_agrega_la_condicion_de_las_opciones_que_el_modelo_olvido():
    """2149: el modelo puso la carga y un filtro copiado del ejemplo; «trabajan» no tenía condición."""
    cat = _cat_127()
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p03", "valor": "Cargas maxima"}]})
    nuevo, notas = anclaje.anclar(plan, "De ellos que llevan carga máxima, ¿cuántos trabajan?", [], cat,
                                  heredar_texto=False)
    assert [(f.pregunta, f.valor) for f in nuevo.filtros] == [("p03", "Cargas maxima"), ("p12", _LABORAL[1:3])]
    assert any("sus opciones dicen lo que pide la pregunta" in n for n in notas)


def test_sin_condicion_respaldada_se_busca_en_las_opciones_antes_de_aclarar():
    cat = _cat_127()
    # Un valor que no es opción ni se menciona se quita antes de validar; la condición sale de las opciones de p12.
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["127"],
                                        "filtros": [{"pregunta": "p03", "valor": "30"}]})
    nuevo, notas = anclaje.sin_inventos(plan, "¿cuántos trabajan?", [], [cat])
    assert nuevo.intencion == "conteo_porcentaje" and [f.pregunta for f in nuevo.filtros] == ["p12"]
    # Una opción real que la consulta no dice se quita al anclar, y también ahí se busca en las opciones.
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje",
                                        "filtros": [{"pregunta": "p02", "valor": "Mixta/hibrida"}]})
    nuevo, _ = anclaje.anclar(plan, "¿cuántos trabajan?", [], cat)
    assert nuevo.intencion == "conteo_porcentaje" and [f.pregunta for f in nuevo.filtros] == ["p12"]


def test_condicion_inexistente_dice_que_no_existe_con_las_opciones_reales():
    """2147: «modalidad nocturna» no existe; la respuesta lo dice, no pregunta cuál quiere."""
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["127"],
                                        "filtros": [{"pregunta": "p02", "valor": "Mixta/hibrida"}]})
    nuevo, notas = anclaje.anclar(plan, "¿cuántos estudian en modalidad nocturna?", [], _cat_127())
    assert nuevo.intencion == "aclaracion" and anclaje.NINGUNA_CONDICION in notas
    assert nuevo.aclaracion.startswith("«Indicadores de Experiencia y Calidad Académica» no registra «nocturna».")
    assert "Presencial, Mixta/hibrida, En linea" in nuevo.aclaracion and "¿Cuál quieres?" not in nuevo.aclaracion


def test_nombrar_la_variable_no_basta_para_un_grupo_que_la_pregunta_no_dice():
    """2195: «estudian» comparte raíz con nivel_estudio y el modelo filtró «pregrado» para «ingeniería»."""
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "instrumentos": ["130"],
                                        "contexto": {"nivel_estudio": "pregrado"}})
    nuevo, _ = anclaje.sin_inventos(plan, "¿Cuántos estudian ingeniería?", [], [_cat_130()])
    assert nuevo.contexto == {}
    # Con el valor dicho, o una variable de sí/no nombrada, el grupo se sostiene.
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "contexto": {"nivel_estudio": "posgrado"}})
    assert anclaje.sin_inventos(plan, "¿cuántos son de posgrado?", [], [_cat_130()])[0].contexto == {"nivel_estudio": "posgrado"}
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "contexto": {"tiene_beca": "True"}})
    assert anclaje.sin_inventos(plan, "¿cuántos tienen beca?", [], [_cat_130()])[0].contexto == {"tiene_beca": "True"}


def test_condicion_que_no_registra_nada_lista_los_datos_de_contexto():
    cat = _cat_130()
    nuevo = anclaje._aclarar_condicion(PlanConsulta(intencion="conteo_porcentaje"), "¿Cuántos estudian ingeniería?", cat)
    assert "no registra «ingeniería»" in nuevo.aclaracion and "nivel_estudio" in nuevo.aclaracion


def test_dos_valores_de_una_variable_comparan_los_grupos():
    """2239: «los de universidad pública y los de privada» filtraba solo «publica»."""
    plan = PlanConsulta.model_validate({"intencion": "comparar_grupos", "preguntas": ["r04"],
                                        "contexto": {"tipo_universidad": "publica"}})
    nuevo, _ = anclaje.anclar(plan, "En la del phishing, ¿responden distinto los de universidad pública y los de "
                                    "privada?", [], _cat_130())
    assert nuevo.agrupar_por == "tipo_universidad" and nuevo.contexto == {} and nuevo.preguntas == ["r04"]


def test_valor_que_nombra_una_variable_no_es_opcion():
    """2242: el modelo puso «no_beca» como opción de r04 y la validación pedía elegir una opción del phishing."""
    plan = PlanConsulta.model_validate({"intencion": "comparar_grupos", "instrumentos": ["130"],
                                        "filtros": [{"pregunta": "r04", "valor": "no_beca"}]})
    otro = plan.model_copy(update={"filtros": [{"pregunta": "r04", "valor": "tiene_beca"}]})  # 2244
    p04 = plan.model_copy(update={"filtros": [{"pregunta": "p04", "valor": "no_beca"}]})  # 2246: ID de encuesta
    assert anclaje.sin_inventos(PlanConsulta.model_validate(p04.model_dump()), "¿Y los que tienen beca contra los que no?",
                                [], [_cat_130()])[0].intencion != "aclaracion"
    assert anclaje.sin_inventos(PlanConsulta.model_validate(otro.model_dump()), "¿Y los que tienen beca contra los que no?",
                                [], [_cat_130()])[0].intencion != "aclaracion"
    pregunta = "¿Y los que tienen beca contra los que no?"
    limpio, notas = anclaje.sin_inventos(plan, pregunta, [], [_cat_130()])
    assert any("nombra un dato de contexto" in n for n in notas) and limpio.intencion != "aclaracion"
    nuevo, _ = anclaje.anclar(limpio, pregunta, [], _cat_130())
    assert nuevo.agrupar_por == "tiene_beca" and nuevo.filtros == []


def test_contra_los_que_no_compara_los_grupos():
    """2187: «¿y los que tienen beca contra los que no?» se volvía la lista de los que tienen beca."""
    plan = PlanConsulta.model_validate({"intencion": "filtrar_respondentes", "contexto": {"tiene_beca": "True"},
                                        "limite": 5})
    nuevo, notas = anclaje.anclar(plan, "¿Y los que tienen beca contra los que no?", [], _cat_130())
    assert nuevo.intencion == "comparar_grupos" and nuevo.agrupar_por == "tiene_beca" and nuevo.contexto == {}
    plan = PlanConsulta.model_validate({"intencion": "conteo_porcentaje", "contexto": {"tipo_universidad": "publica"}})
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje"), "¿los de publica frente a los demás?", [],
                              _cat_130())
    assert nuevo.agrupar_por == "tipo_universidad"


def test_dejaron_alguna_pregunta_sin_responder_cuenta_personas():
    """2165 y 2189: se contestaba con la pregunta con más omisiones o con el total de respondentes."""
    cat = _cat_127()
    for intencion in ("ranking_preguntas", "conteo_porcentaje"):
        nuevo, notas = anclaje.anclar(PlanConsulta(intencion=intencion, criterio_ranking="no_respuesta"),
                                      "¿hay respondentes que dejaron en blanco algunas preguntas?", [], cat)
        assert nuevo.intencion == "conteo_porcentaje" and nuevo.con_omisiones and nuevo.criterio_ranking is None
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="conteo_porcentaje"),
                              "De esos, ¿cuántos dejaron alguna pregunta sin responder?", [], cat)
    assert nuevo.con_omisiones
    # «¿En qué pregunta hubo más respuestas en blanco?» sigue siendo el ranking de preguntas.
    nuevo, _ = anclaje.anclar(PlanConsulta(intencion="hallazgo"), "¿en qué pregunta hubo más respuestas en blanco?", [], cat)
    assert nuevo.intencion == "ranking_preguntas" and not nuevo.con_omisiones


def test_el_ejecutor_cuenta_a_quien_dejo_alguna_pregunta_sin_responder():
    doc = docs_ejemplo.encuesta_carga()
    doc["respondentes"][1]["respuestas"][2]["estado"] = "sin_respuesta"  # R002 no contestó p03
    ins = enrutador.Instrumento("4", "Encuesta de carga", "encuesta", doc)
    (e,) = ejecutor.ejecutar(PlanConsulta(intencion="conteo_porcentaje", con_omisiones=True), [ins])
    assert e.lineas[0] == "Cumplen la condición 1 de 5 respondentes (20.0 %)."
    assert "dejaron alguna pregunta sin responder" in e.criterio
    (e,) = ejecutor.ejecutar(PlanConsulta(intencion="conteo_porcentaje", con_omisiones=True, excluir_preguntas=["p03"]), [ins])
    assert e.lineas[0].startswith("Cumplen la condición 0 de 5")


def test_preguntas_sobre_el_instrumento_van_a_su_ficha():
    for pregunta in ("¿a qué carrera está aplicada esta encuesta?", "¿de qué trata el instrumento?",
                     "pero dame el de qué trata más descriptivo, contextual", "¿a quiénes se aplicó?"):
        assert enrutador.detectar(pregunta).tipo == "descripcion", pregunta
    assert enrutador.detectar("qué secciones tiene?").tipo == "estructura"
    assert enrutador.detectar("¿de qué trata la pregunta 3?") is None or enrutador.detectar("¿de qué trata la pregunta 3?").tipo != "descripcion"


def test_la_descripcion_lleva_el_contexto_de_la_ficha():
    doc = docs_ejemplo.encuesta()
    doc["instrumento"]["contexto"] = ("Institución: Indagata. Carrera(s): Inteligencia artificial. Notas: alimentan 18 "
                                      "indicadores")
    lineas = enrutador._lineas_descripcion(enrutador.Instrumento("1", "Experiencia", "encuesta", doc))
    assert "Contexto: Institución: Indagata. Carrera(s): Inteligencia artificial." in lineas


def test_saber_en_una_prueba_es_pregunta_de_calificacion():
    """2181: «¿la mayoría sabe para qué sirve una VPN?» se respondía con «eligieron incorrectamente»."""
    assert enrutador.detectar("Entonces, ¿la mayoría sabe para qué sirve una VPN?", solo_pruebas=True).tipo == "sin_calificar"
    regla = enrutador.detectar("¿cuántos conocen la plataforma?")  # en una encuesta es un filtro, no una calificación
    assert regla is None or regla.tipo != "sin_calificar"


def test_las_pistas_del_rag_llevan_las_opciones_sin_cifras():
    fragmento = {"preguntaId": "INS-0127-p12", "respondenteId": "", "seccion": "pregunta", "score": 0.61,
                 "fragmento": "Pregunta p12: ¿Cuál es tu situación laboral actual?\nRespuestas válidas: 1950\n"
                              "Distribución: Busco empleo 30.1 % (n=587); Trabajo en un area relacionada 25.0 % (n=488)"}
    pistas = rag_service._pistas([fragmento])
    assert "→ opciones: Busco empleo; Trabajo en un area relacionada" in pistas and "%" not in pistas


# ── B: el hilo de la conversación ──────────────────────────────────────────────


def _plan(**datos) -> PlanConsulta:
    return PlanConsulta.model_validate(datos)


def test_de_ellos_continua_con_las_condiciones_exactas_del_plan_anterior():
    anterior = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p03", "valor": "Cargas maxima"}]}
    nuevo = _plan(intencion="conteo_porcentaje", filtros=[{"pregunta": "p12", "valor": _LABORAL[1:3]}])
    pregunta = "De ellos que llevan carga máxima, ¿cuántos trabajan?"
    assert seguimiento.relacion(pregunta, nuevo, anterior) == "continua"
    plan, notas = seguimiento.combinar(nuevo, anterior, "continua")
    assert [f.pregunta for f in plan.filtros] == ["p12", "p03"] and plan.relacion == "continua"
    assert "filtro p03 heredado del plan anterior" in notas


def test_de_esos_hereda_el_contexto_numerico():
    anterior = {"intencion": "conteo_porcentaje", "contexto_num": [{"variable": "horas_trabajo_semana", "op": ">", "valor": 20}]}
    nuevo = _plan(intencion="conteo_porcentaje", con_omisiones=True)
    plan, _ = seguimiento.combinar(nuevo, anterior,
                                   seguimiento.relacion("De esos, ¿cuántos dejaron alguna pregunta sin responder?", nuevo, anterior))
    assert plan.con_omisiones and plan.contexto_num[0].variable == "horas_trabajo_semana"


def test_y_contra_los_que_no_conserva_la_pregunta_comparada():
    anterior = {"intencion": "comparar_grupos", "preguntas": ["r04"], "agrupar_por": "tipo_universidad"}
    nuevo = _plan(intencion="comparar_grupos", agrupar_por="tiene_beca")
    pregunta = "¿Y los que tienen beca contra los que no?"
    plan, notas = seguimiento.combinar(nuevo, anterior, seguimiento.relacion(pregunta, nuevo, anterior))
    assert plan.preguntas == ["r04"] and plan.agrupar_por == "tiene_beca"


def test_y_sobre_otro_tema_sigue_con_la_misma_persona():
    """2176: «¿Y sobre los psicólogos?» después de «¿qué dijo sobre su tutor?» se iba a una búsqueda abierta."""
    anterior = {"intencion": "datos_respondente", "respondentes": ["E01"], "campos": ["p09"]}
    nuevo = _plan(intencion="semantica_abierta", consulta_semantica="opinión sobre los psicólogos")
    rel = seguimiento.relacion("¿Y sobre los psicólogos?", nuevo, anterior)
    plan, _ = seguimiento.combinar(nuevo, anterior, rel, recuperadas=["p04", "p07"])
    assert rel == "continua" and plan.intencion == "datos_respondente"
    assert plan.respondentes == ["E01"] and plan.campos == ["p04", "p07"]


def test_por_que_profundiza_en_el_plan_anterior():
    anterior = {"intencion": "resumen_pregunta", "preguntas": ["r10"]}
    nuevo = _plan(intencion="datos_respondente", respondentes=["A001", "A002"])
    rel = seguimiento.relacion("¿Por qué nadie la contestó?", nuevo, anterior)
    plan, notas = seguimiento.combinar(nuevo, anterior, rel)
    assert rel == "profundiza" and plan.intencion == "resumen_pregunta" and plan.preguntas == ["r10"]
    for pregunta in ("¿en qué te basas para decir que es preocupante?", "y eso, ¿qué puede significar?", "¿por qué?"):
        assert seguimiento.relacion(pregunta, _plan(intencion="hallazgo"), {"intencion": "hallazgo"}) == "profundiza"


def test_tema_nuevo_empieza_limpio():
    anterior = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p03", "valor": "Cargas maxima"}]}
    nuevo = _plan(intencion="hallazgo")
    rel = seguimiento.relacion("¿qué patrones interesantes encontraste entre los alumnos?", nuevo, anterior)
    plan, notas = seguimiento.combinar(nuevo, anterior, rel)
    assert rel == "nueva" and plan == nuevo and notas == []
    # Una definición no es profundizar aunque diga «qué significa».
    assert seguimiento.relacion("¿qué significa un alfa de Cronbach bajo?", _plan(intencion="metodologia"), anterior) == "nueva"
    # Sin plan anterior todo es nuevo, aunque el modelo diga otra cosa.
    assert seguimiento.relacion("de ellos, ¿cuántos trabajan?", _plan(intencion="conteo_porcentaje"), None) == "nueva"


def test_y_otra_persona_continua_con_otra_persona():
    anterior = {"intencion": "datos_respondente", "respondentes": ["A057"], "campos": ["r11", "r12"]}
    nuevo = _plan(intencion="datos_respondente", respondentes=["A067"])
    rel = seguimiento.relacion("¿Y A067?", nuevo, anterior)
    plan, _ = seguimiento.combinar(nuevo, anterior, rel)
    assert rel == "continua" and plan.respondentes == ["A067"] and plan.campos == ["r11", "r12"]


def test_resumen_del_plan_anterior_para_la_interpretacion():
    texto = seguimiento.resumen_plan({"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p03", "valor": "Cargas maxima"}],
                                      "contexto_num": [{"variable": "horas", "op": ">", "valor": 20}]})
    assert texto == "Condiciones: p03 = Cargas maxima; horas > 20"


def test_y_sobre_otro_tema_con_resumen_de_pregunta_tambien_sigue_con_la_persona():
    """2219: el modelo devolvió resumen_pregunta sin pregunta y salió «La consulta no indica de qué pregunta se trata»."""
    anterior = {"intencion": "datos_respondente", "respondentes": ["E01"], "campos": ["p09"]}
    nuevo = _plan(intencion="resumen_pregunta")
    plan, _ = seguimiento.combinar(nuevo, anterior, seguimiento.relacion("¿Y sobre los psicólogos?", nuevo, anterior),
                                   recuperadas=["p04"])
    assert plan.intencion == "datos_respondente" and plan.respondentes == ["E01"] and plan.campos == ["p04"]
    # Sin intercambios recuperados ni preguntas propias: todas sus respuestas.
    plan, _ = seguimiento.combinar(nuevo, anterior, "continua")
    assert plan.campos == "todas_las_respuestas"


def test_nivel_en_un_reactivo_de_opcion_multiple_se_quita():
    """2220: «¿cuántos respondieron la de la contraseña?» salía «0 de 0 están de acuerdo (nivel alto)»."""
    plan = _plan(intencion="conteo_porcentaje", preguntas=["r10"], nivel="alto")
    nuevo, notas = anclaje.anclar(plan, "¿Cuántos respondieron la pregunta de la contraseña segura?", [], _cat_130())
    assert nuevo.nivel is None and any("nivel alto quitado" in n for n in notas)


def test_la_descripcion_copiada_del_listado_se_rechaza():
    listado = ("Encuesta X (Encuesta) [Fuente 1]:\n- Tipo: Encuesta.\n- Objetivo: Conocer la percepción de los estudiantes.\n"
               "- Población: Estudiantes universitarios de la institución.\n- Contexto: Carrera(s): Inteligencia artificial.")
    assert rag_service._copia_listado(listado, listado)
    assert not rag_service._copia_listado("La encuesta se aplicó a estudiantes de Inteligencia artificial de posgrado "
                                          "para conocer su percepción de la calidad académica [Fuente 1].", listado)
