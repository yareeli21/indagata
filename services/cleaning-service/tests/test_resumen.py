"""Resumen «En pocas palabras»: reglas fijas sobre las medidas estadísticas."""
from __future__ import annotations

from services.motores.resumen import resumir


def _textos(frases: list[dict]) -> str:
    return " | ".join(f"{f['nivel']}: {f['texto']}" for f in frases)


def _bloque(nombre: str, alfa: float | None, por_item: list[dict] | None = None, n_items: int = 4) -> dict:
    interp = None if alfa is None else ("excelente" if alfa >= 0.9 else "aceptable" if alfa >= 0.7 else "pobre")
    return {"bloque": nombre, "alfa": alfa, "interpretacion": interp, "n_items": n_items, "por_item": por_item or []}


def _likert(etiqueta: str, media: float, desviacion: float = 1.1, pct_nulos: float = 0.0) -> dict:
    return {
        "etiqueta": etiqueta, "tipo": "cuadricula", "pct_nulos": pct_nulos,
        "numerico": {"media": media, "desviacion": desviacion},
        "frecuencias": {"tabla": [{"valor": e} for e in ("Nada", "Poco", "Algo", "Bastante", "Mucho")]},
        "escala": {"puntos": 5, "invertido": False},
    }


def test_sin_estadistica_no_hay_resumen():
    assert resumir("encuesta", None) == []
    assert resumir("encuesta", {}) == []


def test_encuesta_fiabilidad_por_bloque_e_items_problematicos():
    est = {
        "fiabilidad": [
            _bloque("Aportación", 0.86),
            _bloque("Dedicación", 0.55, [
                {"item": "ítem 2", "correlacion_item_total": -0.2, "alfa_si_se_elimina": 0.7},
                {"item": "ítem 3", "correlacion_item_total": 0.1, "alfa_si_se_elimina": 0.6},
                {"item": "ítem 1", "correlacion_item_total": 0.5, "alfa_si_se_elimina": 0.4},
            ]),
            _bloque("Todas las escalas Likert", 0.97, n_items=8),
        ],
        "columnas": [_likert("A1", 3.1), _likert("A2", 3.0), _likert("B1", 2.9)],
    }
    frases = resumir("encuesta", est, {"n_respondentes": 100}, {"n_respondentes": 98})
    texto = _textos(frases)
    assert frases[0]["nivel"] == "alerta" and "1 de 2 bloques" in frases[0]["texto"] and "«Dedicación» (α = 0.55)" in frases[0]["texto"]
    assert "«ítem 2» va en sentido contrario" in texto  # correlación negativa: invertido sin marcar
    assert "atencion: «ítem 3» se relaciona poco" in texto
    assert "redundantes" not in texto  # el 0.97 es del bloque global, que no se comenta si hay dimensiones
    assert "Todas las preguntas tienen respuesta" in texto
    assert "Se quitaron 2 encuestados" in texto and "bien: Se quitaron" in texto
    assert "cerca del punto neutral" in texto and "escala de 1 a 5" in texto
    assert "no hay un consenso claro" in texto


def test_encuesta_solo_global_avisa_que_faltan_dimensiones_y_redundancia():
    est = {"fiabilidad": [_bloque("Todas las escalas Likert", 0.96, n_items=26)], "columnas": [_likert("A", 4.5, 0.5, 0.3)]}
    texto = _textos(resumir("encuesta", est))
    assert "bien: Las escalas Likert, en conjunto, son consistentes: α = 0.96" in texto
    assert "sobre las 26 escalas juntas" in texto
    assert "ítems redundantes" in texto
    assert "atencion: «A» tiene más del 20 % sin responder" in texto
    assert "claramente hacia los valores altos" in texto and "bastante consenso" in texto


def test_encuesta_columna_numerica_asimetrica_con_atipicos():
    col = {
        "etiqueta": "horas_trabajo_semana", "tipo": "numerica", "pct_nulos": 0,
        "numerico": {"media": 17.69, "mediana": 14, "q1": 7, "q3": 28, "min": 0, "max": 48, "asimetria": 0.8},
        "atipicos": {"metodo": "iqr", "sigma": 0, "iqr": 2},
    }
    frase = next(f for f in resumir("encuesta", {"columnas": [col]}) if "horas" in f["texto"])
    assert frase["nivel"] == "atencion"
    assert frase["texto"].startswith("«horas_trabajo_semana»: la mitad de las respuestas está entre 7 y 28 (mediana 14)")
    assert "suben el promedio a 17.7" in frase["texto"] and "Hay 2 valores atípicos" in frase["texto"]


def test_prueba_kr20_dificultad_y_discriminacion():
    reactivos = [
        {"pregunta": "P1", "discriminacion": 0.5, "nivel_discriminacion": "excelente", "distractores_sin_elegir": []},
        {"pregunta": "P2", "discriminacion": -0.25, "nivel_discriminacion": "pobre", "distractores_sin_elegir": ["D"]},
        {"pregunta": "P3", "discriminacion": 0.1, "nivel_discriminacion": "pobre", "distractores_sin_elegir": []},
    ]
    est = {
        "fiabilidad": {"kr20": 0.42, "interpretacion": "inaceptable", "n_alumnos": 30, "n_reactivos": 3},
        "puntajes": {"media": 1.5, "mediana": 1, "maximo_posible": 3},
        "reactivos": reactivos,
        "resumen_reactivos": {"faciles": 2, "medios": 1, "dificiles": 0},
    }
    texto = _textos(resumir("prueba_estandarizada", est))
    assert "alerta: La prueba tiene poca consistencia interna: KR-20 = 0.42" in texto and "pocos reactivos" in texto
    assert "acertaron 1.5 de 3 reactivos (50 %" in texto
    assert "2 fáciles, 1 de dificultad media y 0 difíciles. La prueba resultó fácil" in texto
    assert "alerta: En «P2» aciertan más los alumnos con peor puntaje" in texto
    assert "atencion: «P3» casi no distingue" in texto
    assert "1 reactivo tiene opciones que ningún alumno eligió («P2»)" in texto


def test_entrevista_participacion():
    est = {
        "hablantes": [
            {"nombre": "E", "rol": "entrevistador", "turnos": 5, "pct_palabras": 0.62, "palabras_por_turno": {"media": 20}},
            {"nombre": "Ana", "rol": "entrevistado", "turnos": 5, "pct_palabras": 0.38, "palabras_por_turno": {"media": 6}},
        ]
    }
    texto = _textos(resumir("entrevista", est))
    assert "info: 10 turnos de palabra entre 2 hablantes" in texto
    assert "atencion: El entrevistador dice el 62 % de las palabras" in texto
    assert "«Ana» son cortas (6 palabras por turno" in texto


def test_entrevista_resumen_centrado_en_respuestas():
    est = {
        "n_participantes": 40, "n_preguntas": 3, "n_respuestas": 118,
        "palabras_por_respuesta": {"media": 32.5},
        "preguntas": [
            {"pregunta": "P1", "texto": "¿Qué factores te ayudan?", "n_respuestas": 40, "sin_respuesta": 0, "palabras": {"media": 40}},
            {"pregunta": "P2", "texto": "¿Pensaste en abandonar?", "n_respuestas": 38, "sin_respuesta": 2, "palabras": {"media": 20}},
            {"pregunta": "P3", "texto": "¿Qué cambiarías?", "n_respuestas": 40, "sin_respuesta": 0, "palabras": {"media": 35}},
        ],
        "palabras_por_rol": [{"rol": "entrevistado", "pct_palabras": 0.8}, {"rol": "entrevistador", "pct_palabras": 0.2}],
    }
    texto = _textos(resumir("entrevista", est))
    assert "info: 40 entrevistados y 3 preguntas del entrevistador: 118 respuestas en total." in texto
    assert "bien: Las respuestas tienen 32.5 palabras en promedio." in texto
    assert "«P2: ¿Pensaste en abandonar?» quedó sin respuesta en 2 entrevistas." in texto
    assert "más breves son las de «P2" in texto
    assert "revisa que los roles" not in texto
