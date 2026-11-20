"""Fallas de interpretación de la prueba de aritmética (10 nov 2026, Pruebas 6.7.3), con catálogos inventados.

Cada prueba pasa el plan del modelo por los mismos pasos que `interpretacion.interpretar`: quitar lo que la consulta
no dice (`sin_inventos`), validar contra el catálogo y anclar a lo que la consulta dice literalmente.
"""
from __future__ import annotations

from services import anclaje, catalogo
from services.plan_consulta import PlanConsulta, validar_contra_catalogo

_ESCALA = ["Totalmente en desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo", "De acuerdo",
           "Totalmente de acuerdo"]


def _likert(pid: str, texto: str) -> catalogo.PreguntaCatalogo:
    return catalogo.PreguntaCatalogo(pid, texto, "likert", _ESCALA, "escala 1–5; niveles desacuerdo 1/2; neutral 3; acuerdo 4/5")


def _cat() -> catalogo.Catalogo:
    preguntas = {
        "p01": _likert("p01", "Cuento con tiempo suficiente para preparar cada curso."),
        "p02": _likert("p02", "Me siento tranquilo dentro del edificio de la facultad."),
        "p03": catalogo.PreguntaCatalogo("p03", "¿Cuántos cursos llevas este periodo?", "categorica", ["1-2", "3-4", "5 o más"]),
        "p04": catalogo.PreguntaCatalogo("p04", "¿Has abandonado algún curso por falta de tiempo para prepararlo?",
                                         "categorica", ["Sí, una vez", "Sí, varias veces", "No, nunca"]),
        "p05": catalogo.PreguntaCatalogo("p05", "¿Cuántas horas por semana dedicas a leer fuera del aula?", "categorica",
                                         ["Menos de 3h", "3-6h", "Más de 6h"]),
        "p06": catalogo.PreguntaCatalogo("p06", "¿Cuántas horas por semana dedicas a leer fuera del aula? (número)",
                                         "numerica"),
        "p07": catalogo.PreguntaCatalogo("p07", "¿Tu escuela organiza asesorías de técnicas de lectura?", "binaria",
                                         ["Sí", "No"]),
        "p08": catalogo.PreguntaCatalogo("p08", "¿Has presentado algún examen de idioma?", "categorica",
                                         ["Si, y lo aprobe", "Si, y no lo aprobe", "No, pero planeo hacerlo",
                                          "No, y no lo planeo"]),
    }
    return catalogo.Catalogo("9", "Encuesta de hábitos de lectura", "encuesta", preguntas, ["R001", "R002"],
                             {"genero": ["femenino", "masculino"], "sostenimiento": ["publica", "privada"]}, [])


def _anclado(datos: dict, pregunta: str) -> tuple[PlanConsulta, list[str]]:
    cat = _cat()
    plan, notas = anclaje.sin_inventos(PlanConsulta.model_validate(datos), pregunta, [], [cat])
    validado = validar_contra_catalogo(plan, [cat])
    plan, mas = anclaje.anclar(validado.plan, pregunta, [], cat)
    return plan, notas + validado.correcciones + mas


def test_estar_de_acuerdo_con_no_es_segun():
    """A12: «está de acuerdo con que…» se leía como «según…» y salía una comparación por otra pregunta."""
    plan, notas = _anclado({"intencion": "resumen_pregunta", "preguntas": ["p01"],
                            "filtros": [{"pregunta": "p01", "valor": "Totalmente de acuerdo"}]},
                           "¿Qué porcentaje está de acuerdo con que cuenta con tiempo suficiente para preparar cada curso?")
    assert plan.intencion != "comparar_grupos" and not plan.agrupar_por
    assert not any("según" in n for n in notas)
    # …y lo que pide es el porcentaje en el nivel de acuerdo, no la distribución (tercera prueba).
    assert plan.intencion == "conteo_porcentaje" and plan.nivel == "acuerdo" and plan.preguntas == ["p01"]


def test_segun_sigue_comparando():
    plan, _ = _anclado({"intencion": "resumen_pregunta", "preguntas": ["p01"]},
                       "¿Cambia el tiempo suficiente para preparar cada curso según cuántos cursos llevas?")
    assert plan.intencion == "comparar_grupos" and plan.agrupar_por == "p03"


def test_opcion_si_que_la_consulta_distingue_no_se_junta_con_las_demas():
    """A18: «…y lo aprobaron» es «Si, y lo aprobe»; juntar todas las «Sí…» sumaba también «Si, y no lo aprobe»."""
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p08", "valor": "Si, y lo aprobe"}]},
                       "¿Cuántos presentaron un examen de idioma y lo aprobaron?")
    assert [f.valor for f in plan.filtros] == ["Si, y lo aprobe"]


def test_no_que_la_consulta_no_distingue_junta_todas_las_no():
    """Regresión C08: «no han presentado ningún examen» son todas las «No…»."""
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p08", "valor": "No, y no lo planeo"}]},
                       "¿Cuántos no han presentado ningún examen de idioma?")
    assert plan.filtros[0].valor == ["No, pero planeo hacerlo", "No, y no lo planeo"]


def test_mujeres_nombra_el_valor_femenino():
    """A05: el grupo genero = femenino se descartaba porque la consulta dice «mujeres», no «femenino»."""
    plan, notas = _anclado({"intencion": "conteo_porcentaje", "contexto": {"genero": "femenino"},
                            "filtros": [{"pregunta": "p02", "nivel": "acuerdo"}]},
                           "¿Cuántas mujeres están de acuerdo con que se sienten tranquilas dentro del edificio?")
    assert plan.contexto == {"genero": "femenino"}
    # …y si el modelo no lo pone, el anclaje lo toma de la consulta.
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "nivel": "acuerdo"}]},
                       "¿Cuántas mujeres están de acuerdo con que se sienten tranquilas dentro del edificio?")
    assert plan.contexto == {"genero": "femenino"}


def test_grupo_que_no_se_nombra_se_sigue_descartando():
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "contexto": {"genero": "masculino"},
                        "filtros": [{"pregunta": "p02", "nivel": "acuerdo"}]},
                       "¿Cuántos están de acuerdo con que se sienten tranquilos dentro del edificio?")
    assert plan.contexto == {}


def test_mencion_que_es_una_pregunta_de_si_o_no_se_vuelve_filtro():
    """A11: «talleres de gestión del tiempo» como mención se descartaba y quedaba solo el grupo."""
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "menciona": "asesorías de técnicas de lectura"},
                       "¿Cuántos de escuela publica dicen que su escuela organiza asesorías de técnicas de lectura?")
    assert plan.contexto == {"sostenimiento": "publica"} and not plan.menciona
    assert [(f.pregunta, f.valor) for f in plan.filtros] == [("p07", ["Sí"])]
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "menciona": "asesorías de técnicas de lectura"},
                       "¿Cuántos dicen que su escuela no organiza asesorías de técnicas de lectura?")
    assert [(f.pregunta, f.valor) for f in plan.filtros] == [("p07", ["No"])]


def test_mencion_que_es_otra_pregunta_corrige_la_pregunta_elegida():
    """A09: el modelo eligió «¿cuántos cursos llevas?» y la mención «abandonar cursos» era la pregunta correcta."""
    plan, _ = _anclado({"intencion": "conteo_porcentaje", "campos": ["p03"], "menciona": "abandonado curso falta tiempo"},
                       "¿Cuántos han abandonado algún curso por falta de tiempo?")
    assert [(f.pregunta, f.valor) for f in plan.filtros] == [("p04", ["Sí, una vez", "Sí, varias veces"])]


def test_promedio_usa_la_pregunta_numerica():
    """A10: «promedio de horas» sobre la pregunta de rangos daba la distribución; la numérica trae la media."""
    plan, notas = _anclado({"intencion": "resumen_pregunta", "preguntas": ["p05"]},
                           "¿Cuál es el promedio de horas por semana que dedican a leer fuera del aula?")
    assert plan.intencion == "resumen_pregunta" and plan.preguntas == ["p06"]
    assert any("promedio" in n for n in notas)
    # Sin «promedio» se queda la pregunta que eligió el modelo.
    plan, _ = _anclado({"intencion": "resumen_pregunta", "preguntas": ["p05"]},
                       "¿Cuántas horas por semana dedican a leer fuera del aula?")
    assert plan.preguntas == ["p05"]
