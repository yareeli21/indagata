"""Fase 1 del 7 nov: indicaciones y cierre de la guía de entrevista, análisis de lo que se cuenta y polaridad.

Los textos son de ejemplo (no de los instrumentos de las baterías del chat), para que las reglas sean generales.
"""
from __future__ import annotations

from services.documento import nlp_entrevista, polaridad
from services.estructura import entrevista, es_cierre, partir_turno

RESPUESTA = ("Al principio no quería ir porque me daba vergüenza. Mi asesora me recomendó el taller de escritura y fui "
             "dos veces. Me ayudó mucho, aunque el horario es muy tarde. Sería bueno que hubiera grupos en la mañana.")


def test_las_indicaciones_antes_de_la_pregunta_no_son_parte_de_la_guia():
    assert partir_turno("Bienvenido. Tus datos son anónimos. Para iniciar, ¿qué te motivó a inscribirte?") == (
        "Bienvenido. Tus datos son anónimos.", "Para iniciar, ¿qué te motivó a inscribirte?")
    # Lo que sigue a la pregunta sí es de la pregunta; sin «?» no se parte.
    assert partir_turno("¿Usaste la biblioteca? Platícame cómo te fue.") == ("", "¿Usaste la biblioteca? Platícame cómo te fue.")
    assert partir_turno("Háblame de tu primer semestre en la carrera") == ("", "Háblame de tu primer semestre en la carrera")
    assert es_cierre("Muchas gracias por tu tiempo y tus respuestas.") and not es_cierre("Gracias. ¿Algo más que quieras agregar?")


def test_guia_desde_turnos_separa_indicaciones_y_omite_el_cierre():
    filas = [
        {"rol": "entrevistador", "texto": "Bienvenido. Tus datos son anónimos. Para iniciar, ¿qué te motivó a inscribirte?"},
        {"rol": "entrevistado", "texto": "La beca."},
        {"rol": "entrevistador", "texto": "¿Qué cambiarías del programa?"},
        {"rol": "entrevistado", "texto": "Los horarios."},
        {"rol": "entrevistador", "texto": "Muchas gracias por tu tiempo y tus respuestas."},
    ]
    e = entrevista(7, filas, None)
    assert [p.texto for p in e.preguntas] == ["Para iniciar, ¿qué te motivó a inscribirte?", "¿Qué cambiarías del programa?"]
    assert e.indicaciones == ["Bienvenido. Tus datos son anónimos."]


def test_nlp_solo_acepta_citas_literales_y_marca_el_origen():
    salida = {
        "temas": [{"tema": "apoyo de la asesora", "cita": "Mi asesora me recomendó el taller de escritura"},
                  {"tema": "inventado", "cita": "la asesora la regañó"}],
        "valoracion": {"valor": "mixto", "cita": "Me ayudó mucho, aunque el horario es muy tarde"},
        "actores": [{"actor": "asesora", "cita": "Mi asesora me recomendó el taller de escritura y fui dos veces"}],
        "barreras": ["me daba vergüenza"], "experiencias": [], "propuestas": ["Sería bueno que hubiera grupos en la mañana"],
        "citas_clave": ["Me ayudó mucho", "algo que nunca dijo"],
    }
    esquemas = []
    r = nlp_entrevista.analizar("¿Cómo te fue con el taller?", RESPUESTA, lambda _p, e: esquemas.append(e) or salida)
    # Por partes (7 nov): tres peticiones, cada una con el esquema de solo sus campos.
    assert [sorted(e["properties"]) for e in esquemas] == [["citas_clave", "temas"], ["actores", "valoracion"],
                                                           ["barreras", "experiencias", "propuestas"]]
    assert r["metodo"] == "llm" and r["descartadas"] == 2
    assert [t["tema"] for t in r["temas"]] == ["apoyo de la asesora"] and r["valoracion"]["valor"] == "mixto"
    assert r["citas_clave"] == ["Me ayudó mucho"] and r["barreras"][0]["origen"] == "llm"
    # Las experiencias que el modelo no dio las completan las reglas («fui»), con su origen.
    assert r["experiencias"] and all(x["origen"] == "regla" for x in r["experiencias"])


def test_nlp_sin_modelo_usa_reglas_con_la_oracion_como_cita():
    r = nlp_entrevista.analizar("¿Cómo te fue?", RESPUESTA, lambda _p, _e: None)
    assert r["metodo"] == "reglas" and r["valoracion"]["valor"] == "mixto"
    assert any(a["actor"] == "tutor" and "asesora" in a["cita"] for a in r["actores"])  # «asesora» está en tutor
    assert any("hubiera grupos" in x["texto"] for x in r["propuestas"])
    assert any("vergüenza" in x["texto"] for x in r["barreras"])


def test_polaridad_valida_opciones_existentes_y_sin_cruces():
    p = {"id": "INS-0001-p03", "texto": "¿Con qué frecuencia se cancelan tus clases?", "tipo": "categorica",
         "opciones": ["Nunca", "A veces", "Seguido", "No sé"]}
    r = polaridad.inferir(p, lambda _p: {"favorables": ["nunca", "Inventada"], "desfavorables": ["Seguido", "Nunca"]})
    assert r == {"favorables": [], "desfavorables": ["Seguido"], "origen": "llm", "estado": "propuesto"}
    assert polaridad.inferir(p, lambda _p: None)["origen"] == "sin_determinar"
    escala = {"texto": "Mi profesor explica con claridad", "tipo": "likert",
              "escala": {"etiquetas": {"1": "Totalmente en desacuerdo", "5": "Totalmente de acuerdo"}}}
    assert polaridad.opciones_de(escala) == ["Totalmente en desacuerdo", "Totalmente de acuerdo"]
    assert not polaridad.aplica({"tipo": "texto_largo", "opciones": ["a", "b"]})


def test_polaridad_de_escala_decide_solo_el_extremo_alto():
    p = {"texto": "¿Con qué frecuencia se cancelan tus clases?", "tipo": "likert",
         "escala": {"etiquetas": {"1": "Nunca", "2": "Rara vez", "3": "A veces", "4": "Seguido", "5": "Siempre"},
                    "niveles": {"baja": [1, 2], "media": [3], "alta": [4, 5]}}}
    vistos = []

    def modelo(pr: str) -> dict:
        vistos.append(pr)
        return {"juicio": "malo" if "responde «Siempre»" in pr else "bueno"}

    r = polaridad.inferir(p, modelo)
    assert r["favorables"] == ["Nunca", "Rara vez"] and r["desfavorables"] == ["Seguido", "Siempre"]
    assert len(vistos) == 2  # un juicio por extremo
    # Juicios que no son opuestos (los dos extremos «malos») no se aceptan: consistencia.
    assert polaridad.inferir(p, lambda _p: {"juicio": "malo"})["origen"] == "sin_determinar"


def test_escalas_lineales_de_google_forms_se_asignan_por_palabras():
    from services.estructura import Estructura, Pregunta, _anclas_de_escalas_lineales
    from services.original import leer

    texto = ("Nada útil1 2 3 4 5\nMuy útil  ¿Cuál es tu carrera?\nTotalmente en desacuerdo1 2 3 4 5\n"
             "Totalmente de acuerdoTítulo del formulario\n")
    escalas = leer(texto).escalas_lineales
    assert escalas == [{1: "Nada útil", 5: "Muy útil"}, {1: "Totalmente en desacuerdo", 5: "Totalmente de acuerdo"}]
    e = Estructura(preguntas=[Pregunta("p1", "s", "¿Qué tan útil te parece la tutoría?", tipo="likert"),
                              Pregunta("p2", "s", "Las aulas están limpias.", tipo="likert"),
                              Pregunta("p3", "s", "¿Cuántas horas estudias?", tipo="likert")])
    _anclas_de_escalas_lineales(e, escalas)
    assert e.preguntas[0].anclas == {1: "Nada útil", 5: "Muy útil"}
    assert e.preguntas[1].anclas == {1: "Totalmente en desacuerdo", 5: "Totalmente de acuerdo"}
    assert e.preguntas[2].anclas == {}


def test_una_cita_casi_literal_se_guarda_con_el_texto_exacto_de_la_respuesta():
    # El modelo quitó «aunque» y cambió el acento; se guarda el tramo original.
    assert nlp_entrevista.anclar("Me ayudo mucho el horario es muy tarde", RESPUESTA) == "Me ayudó mucho, aunque el horario es muy tarde"
    assert nlp_entrevista.anclar("la asesora la regañó frente a todos", RESPUESTA) is None



def test_pregunta_descriptiva_no_lleva_polaridad_y_escala_de_acuerdo_usa_sus_niveles():
    p = {"texto": "¿En qué modalidad estudias?", "tipo": "categorica", "opciones": ["Presencial", "En línea"]}
    r = polaridad.inferir(p, lambda _p: {"tipo": "descriptiva", "favorables": ["Presencial"], "desfavorables": []})
    assert (r["favorables"], r["desfavorables"], r["origen"]) == ([], [], "llm")
    acuerdo = {"texto": "Las aulas están limpias.", "tipo": "likert",
               "escala": {"etiquetas": {"1": "Totalmente en desacuerdo", "2": "2", "3": "3", "4": "4", "5": "Totalmente de acuerdo"},
                          "niveles": {"desacuerdo": [1, 2], "neutral": [3], "acuerdo": [4, 5]}}}
    r = polaridad.inferir(acuerdo, lambda pr: {"juicio": "bueno" if "responde «Totalmente de acuerdo»" in pr else "malo"})
    assert r["favorables"] == ["4", "Totalmente de acuerdo"] and r["desfavorables"] == ["Totalmente en desacuerdo", "2"]



def test_opciones_clasificadas_dos_veces_solo_cuenta_lo_que_coincide():
    p = {"texto": "¿Terminaste el servicio social?", "tipo": "categorica", "opciones": ["Sí", "En proceso", "No"]}
    respuestas = iter([{"tipo": "situacion", "favorables": ["Sí", "En proceso"], "desfavorables": ["No"]},
                       {"tipo": "situacion", "favorables": ["Sí"], "desfavorables": ["No", "En proceso"]}])
    r = polaridad.inferir(p, lambda _p: next(respuestas))
    assert (r["favorables"], r["desfavorables"]) == (["Sí"], ["No"])
    dudosa = iter([{"tipo": "descriptiva"}, {"tipo": "situacion", "favorables": ["Sí"], "desfavorables": ["No"]}])
    assert polaridad.inferir(p, lambda _p: next(dudosa))["origen"] == "sin_determinar"
