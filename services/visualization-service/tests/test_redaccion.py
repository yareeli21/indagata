"""Bloque D (7 nov): la redacción contextualiza, y la verificación rechaza lo que contradice sus cifras.

Cada prueba usa el texto que escribió gemma3:4b en una consulta que la investigadora calificó mal: la comparación al
revés del phishing (2186, 2247), «preferencia significativa» (2248), el porcentaje sin su número (2193), «no se
encontró risa» (2170) y las cifras deducibles que antes caían al cálculo literal.
"""
from __future__ import annotations

from services import consulta_planificada, ejecutor, rag_service
from services.enrutador import Instrumento
from services.plan_consulta import PlanConsulta
from tests import docs_ejemplo

_PHISHING = ("Los estudiantes de universidades privadas muestran una mayor preferencia por la opción «Un tipo de "
             "búsqueda en Google» (37.9%) en comparación con los estudiantes de universidades mixtas (44.4%) y "
             "públicas (40.7%) [Fuente 1].")


def test_comparacion_invertida_se_detecta():
    assert rag_service.comparacion_invertida(_PHISHING)
    bien = "En las mixtas la opción más elegida tiene un porcentaje mayor (44.4 %) que en las privadas (37.9 %)."
    assert not rag_service.comparacion_invertida(bien)
    assert not rag_service.comparacion_invertida("El menor porcentaje fue 12.0 %, frente a 30.5 % y 40.1 %.")
    assert not rag_service.comparacion_invertida("La mayoría de las privadas (37.9 %) eligió A; en las mixtas, 44.4 %.")


def test_inferencia_sin_prueba_estadistica():
    texto = "Los estudiantes con beca muestran una preferencia significativa por la edición de imágenes (50.0 %)."
    assert rag_service.inferencia_sin_respaldo(texto, "Comparación por tiene_beca | True | 14 | 50.0 % (7 de 14)")
    assert not rag_service.inferencia_sin_respaldo("Con beca, 7 de 14 (50.0 %) eligieron C.", "50.0 % (7 de 14)")


def test_porcentaje_va_con_su_numero():
    resultado = "Opción más elegida: «Verdadero» (75.3 %, 73 alumnos).\n| Verdadero | 73 | 75.3 % |"
    assert rag_service.porcentajes_sin_n("75.3% de los alumnos respondieron «Verdadero» [Fuente 1].", resultado)
    assert not rag_service.porcentajes_sin_n("73 de 97 alumnos (75.3 %) respondieron «Verdadero».", resultado)
    # «nadie» y «todos» se dicen con palabras: 0 % y 100 % no exigen su número.
    assert not rag_service.porcentajes_sin_n("El 100 % quedó sin respuesta.", "| NR | 97 | 100.0 % |")


def test_cifras_deducibles_del_resultado():
    contexto = "| True | 14 | «Edición» 50.0 % (7 de 14) |\n| privada | 29 | 37.9 % |\n| mixta | 9 | 44.4 % |"
    assert rag_service.cifras_fieles("La mitad de los becados, 50 % (7 de 14).", contexto)
    assert rag_service.cifras_fieles("Las mixtas superan a las privadas por 6.5 puntos.", contexto)  # 44.4 − 37.9
    assert rag_service.cifras_fieles("En las mixtas, cerca del 44 %.", contexto)
    assert not rag_service.cifras_fieles("Son 21 personas.", contexto)  # 7 + 14: una suma de conteos no se acepta


def test_negacion_de_algo_que_no_esta_en_los_datos():
    contexto = "| p04 | Fui a orientación psicológica, tuve tres sesiones con una psicóloga |"
    assert rag_service.negacion_cierta("En la entrevista no se menciona ninguna risa de E01 [Fuente 1].", contexto)
    assert not rag_service.negacion_cierta("No se menciona la orientación psicológica.", contexto)


def test_formato_adicional_segun_la_pregunta():
    assert consulta_planificada.FORMATO_PROFUNDIZA in consulta_planificada.formato_adicional(
        "¿Por qué nadie la contestó?", "profundiza", None)
    assert "«lo mas preocupante»" in consulta_planificada.formato_adicional(
        "¿Qué es lo más preocupante que encuentras?", "nueva", None)
    assert "solo una participante(s)" in consulta_planificada.formato_adicional(
        "¿Los estudiantes sufren ansiedad?", "nueva", 1)
    assert consulta_planificada.formato_adicional("¿Cuántos trabajan?", "nueva", 40) == ""


def test_sin_etiquetas_internas_del_prompt():
    texto = ("Según el RESULTADO CALCULADO, ninguno de los 97 respondió. El TEXTO RECUPERADO indica que nadie eligió A; "
             "esto, de acuerdo con el TEXTO RECUPERADO, sugiere revisar r10.")
    assert rag_service._sin_etiquetas_internas(texto) == (
        "Ninguno de los 97 respondió. El texto del instrumento indica que nadie eligió A; esto, sugiere revisar r10.")


def test_opinion_pide_interpretacion():
    assert consulta_planificada.FORMATO_OPINION in consulta_planificada.formato_adicional(
        "¿qué opinas de que el 50.4% esté dispuesto a volver a estudiar?", "nueva", None)


def test_seguimiento_no_cambia_la_pregunta_por_una_que_no_se_nombra():
    """2259: «¿Y los que tienen beca contra los que no?» → el modelo puso r01 y se perdió r04 (phishing)."""
    from services import catalogo, seguimiento
    preguntas = {"r01": catalogo.PreguntaCatalogo("r01", "¿Cuál es la extensión de una hoja de cálculo?", "opcion_multiple",
                                                  ["A) .xlsx"]),
                 "r04": catalogo.PreguntaCatalogo("r04", "¿Qué es el phishing?", "opcion_multiple", ["A) Pesca"])}
    cat = catalogo.Catalogo("130", "Prueba", "prueba_estandarizada", preguntas, ["A001"], {"tiene_beca": ["True"]}, [])
    anterior = {"intencion": "comparar_grupos", "preguntas": ["r04"], "agrupar_por": "tipo_universidad"}
    plan = PlanConsulta(intencion="comparar_grupos", preguntas=["r01"], agrupar_por="tiene_beca")
    nuevo, _ = seguimiento.combinar(plan, anterior, "continua", [], "¿Y los que tienen beca contra los que no?", [cat])
    assert nuevo.preguntas == ["r04"]
    nuevo, _ = seguimiento.combinar(plan, anterior, "continua", [], "¿Y en la de la hoja de cálculo?", [cat])
    assert nuevo.preguntas == ["r01"]


def test_conteo_con_omisiones_dice_que_preguntas_las_explican():
    """2233: «38 de 38 dejaron alguna sin responder» sin decir que nadie respondió r10."""
    doc = docs_ejemplo.prueba()
    doc["alumnos"][0]["respuestas"][1]["estado"] = "sin_respuesta"
    pru = Instrumento("2", "Diagnóstico", "prueba_estandarizada", doc)
    [e] = ejecutor.ejecutar(PlanConsulta(intencion="conteo_porcentaje", con_omisiones=True), [pru])
    linea = next(l for l in e.lineas if l.startswith(ejecutor.MAS_OMITIDAS))
    assert "r02" in linea and "(1 de 1)" in linea
    assert consulta_planificada.cifras_clave([e]) == {1.0, 100.0}  # la línea de omisiones no es obligatoria


def test_grupos_de_si_o_no_se_muestran_legibles():
    """2264: con «True | 14» y «False | 83» la redacción dio a los becados las cifras de los no becados."""
    doc = docs_ejemplo.prueba()
    doc["alumnos"][0]["contexto"] = {"tiene_beca": "True"}
    pru = Instrumento("2", "Diagnóstico", "prueba_estandarizada", doc)
    [e] = ejecutor.ejecutar(PlanConsulta(intencion="comparar_grupos", preguntas=["r01"], agrupar_por="tiene_beca"), [pru])
    assert e.tablas[0].filas[0][0] == "Sí"
