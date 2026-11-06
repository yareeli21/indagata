"""Errores frecuentes en archivos reales que la limpieza antes no contemplaba (2 nov).

Cada prueba reproduce, en pequeño, un error medido con los generadores de `tools/limpieza/`
(enc_06, pru_03 y ent_11 «no contemplados»): acentos rotos, encabezado repetido, fila de
totales, segunda fila de encabezado, filas corridas, números escritos de otra forma, Sí / No
en otro formato, opciones mal escritas, reactivos vacíos, respuestas con signos, IDs escritos
distinto, encabezados de página, minuto en la etiqueta y anotaciones del transcriptor.
"""
from __future__ import annotations

import csv
import io

import pytest

from services.motores import Entrada, obtener
from services.motores import codificacion, filas
from services.motores.pruebas import tipos as tp


def _csv(encabezados: list[str], datos: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows([encabezados, *datos])
    return buffer.getvalue().encode("utf-8")


def _correr(tipo: str, contenido: bytes, extension: str = ".csv", decisiones: dict[str, str] | None = None):
    entrada = Entrada(1, tipo, f"archivo{extension}", extension, contenido)
    motor = obtener(tipo, extension)
    auto = motor.automatica(entrada)
    elegidas = {h.id: h.sugerida for h in auto.hallazgos if h.sugerida}
    elegidas.update(decisiones or {})
    return auto, motor.aplicar(entrada, auto, elegidas)


def _hallazgo(auto, prefijo: str):
    return next(h for h in auto.hallazgos if h.id.startswith(prefijo))


def _reglas(auto, final=None) -> dict[str, int]:
    todas = auto.transformaciones + (final.transformaciones if final else [])
    return {t["regla"]: t["afectados"] for t in todas}


# ── Generales ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("roto", "esperado"),
    [
        ("Sí".encode().decode("latin-1"), "Sí"),
        ("educación — niño ¿qué?".encode().decode("cp1252"), "educación — niño ¿qué?"),
        ("Bien escrito: educación, niño, ÑANDÚ", "Bien escrito: educación, niño, ÑANDÚ"),
        ("Mitad: acción y " + "acción".encode().decode("latin-1"), "Mitad: acción y acción"),
    ],
)
def test_acentos_rotos_se_reparan_sin_tocar_el_texto_bien_escrito(roto, esperado):
    assert codificacion.reparar(roto)[0] == esperado


def test_encabezado_repetido_se_detecta():
    encabezados = ["id", "edad", "P1"]
    datos = [["R1", "20", "A"], ["id", "edad", "P1"], ["R2", "21", "B"]]
    assert filas.revisar(encabezados, datos).repetidas == [1]


# ── Encuestas ──────────────────────────────────────────────────────────────────

ENCABEZADO = ["id", "genero", "edad", "semestre", "Servicio_item1", "Servicio_item2", "Servicio_item3",
              "Servicio_item4", "Con qué frecuencia usas la biblioteca", "Has usado la bolsa de trabajo"]
FRECUENCIAS = ["Semanalmente", "Nunca", "Una vez al mes"]


def _encuesta(n: int = 40) -> list[list[str]]:
    datos = []
    for i in range(n):
        datos.append([f"R{i:03d}", ["Femenino", "Masculino"][i % 2], str(18 + i % 8), str(1 + i % 9),
                      *(str(1 + (i + k) % 5) for k in range(4)), FRECUENCIAS[i % 3], ["Sí", "No"][i % 2]])
    return datos


def test_encuesta_limpia_no_genera_hallazgos_nuevos():
    auto, final = _correr("encuesta", _csv(ENCABEZADO, _encuesta()))
    nuevos = {"fila_resumen", "segunda_fila_encabezado", "fila_corrida", "fila_larga", "si_no_codigos", "opcion_parecida"}
    assert not [h for h in auto.hallazgos if h.tipo in nuevos]
    assert len(final.filas) == 40


def test_fila_de_promedios_se_elimina_antes_de_inferir_tipos():
    datos = _encuesta()
    datos.append(["Promedio", "", "21.5", "5.0", "3.02", "2.95", "3.10", "3.00", "", ""])
    auto, final = _correr("encuesta", _csv(ENCABEZADO, datos))
    h = _hallazgo(auto, "fila-resumen:")
    assert h.id == "fila-resumen:41" and h.sugerida == "eliminar"
    assert len(final.filas) == 40
    # Sin la fila, los ítems siguen siendo una escala 1–5 (antes, sus decimales los volvían calificación 0–10).
    tipos = {c["id"]: c["tipo_canonico"] for c in final.especifico["columnas"]}
    assert tipos["servicio_item1"] == "likert"
    # Si el investigador la conserva, cuenta como un encuestado más.
    _, conservada = _correr("encuesta", _csv(ENCABEZADO, datos), decisiones={"fila-resumen:41": "conservar"})
    assert len(conservada.filas) == 41


def test_segunda_fila_de_encabezado_se_guarda_como_texto_de_la_pregunta():
    texto = ["ID", "Género", "Edad", "Semestre", "Atención", "Rapidez", "Trato", "Horario", "Frecuencia", "Bolsa"]
    auto, final = _correr("encuesta", _csv(ENCABEZADO, [texto, *_encuesta()]))
    assert _hallazgo(auto, "encabezado-texto").sugerida == "usar_como_texto"
    assert len(final.filas) == 40
    edad = next(c for c in final.especifico["columnas"] if c["id"] == "edad")
    assert edad["texto"] == "Edad" and edad["tipo_canonico"] == "numerica"


def test_fila_corrida_se_repara_y_queda_uniforme():
    datos = _encuesta()
    original = list(datos[10])
    datos[10] = datos[10][:1] + datos[10][2:] + [""]  # falta «genero»
    auto, final = _correr("encuesta", _csv(ENCABEZADO, datos))
    h = _hallazgo(auto, "fila-corrida:")
    assert h.id == "fila-corrida:11" and "genero" in h.titulo and h.sugerida == "reparar"
    fila = next(f for f in final.filas if f[0] == "R010") if final.encabezados[0] == "id" else final.filas[10]
    assert fila[final.encabezados.index("edad")] == original[2]
    assert fila[final.encabezados.index("genero")] == ""
    assert all(len(f) == len(final.encabezados) for f in final.filas)


def test_fila_con_una_celda_de_mas_se_repara():
    datos = _encuesta()
    contenido = _csv(ENCABEZADO, datos).decode("utf-8").split("\n")
    partes = contenido[6].split(",")
    contenido[6] = ",".join(partes[:2] + ["xx"] + partes[2:])  # línea 7 = fila 6: una celda de más tras «genero»
    auto, final = _correr("encuesta", "\n".join(contenido).encode("utf-8"))
    h = _hallazgo(auto, "fila-corrida:")
    assert h.id == "fila-corrida:6" and "sobra" in h.titulo
    assert final.filas[5][final.encabezados.index("edad")] == datos[5][2]


@pytest.mark.parametrize(
    ("valor", "esperado", "regla"),
    [("4,5", "4.5", "coma_decimal"), ("4 (De acuerdo)", "4", "numero_con_etiqueta"), ("4 - De acuerdo", "4", "numero_con_etiqueta"),
     ("cuatro", "4", "numero_en_palabras"), ("19 años", "19", "unidad_quitada"), ("25 hrs", "25", "unidad_quitada")],
)
def test_numeros_escritos_de_otra_forma(valor, esperado, regla):
    from services.motores.encuestas import numeros

    assert numeros._convertir(valor) == (regla, esperado)


def test_numero_con_etiqueta_que_no_coincide_no_se_adivina():
    from services.motores.encuestas import numeros

    assert numeros._convertir("2 (De acuerdo)") is None  # «De acuerdo» es la opción 4, no la 2


def test_numeros_en_columnas_numericas_se_convierten_sin_anularse():
    datos = _encuesta()
    datos[3][2], datos[4][4], datos[5][5] = "19 años", "4 (De acuerdo)", "cuatro"
    auto, final = _correr("encuesta", _csv(ENCABEZADO, datos))
    reglas = _reglas(auto)
    assert reglas["unidad_quitada"] == 1 and reglas["numero_con_etiqueta"] == 1 and reglas["numero_en_palabras"] == 1
    assert not [h for h in auto.hallazgos if h.tipo == "fuera_de_rango"]
    assert final.filas[3][final.encabezados.index("edad")] == "19"


def test_si_no_en_ingles_se_unifica_y_los_codigos_se_preguntan():
    datos = _encuesta()
    datos[2][9], datos[3][9], datos[4][9] = "Yes", "1", "0"
    auto, final = _correr("encuesta", _csv(ENCABEZADO, datos))
    assert _reglas(auto)["si_no_unificado"] == 1
    h = _hallazgo(auto, "si-no-codigos:")
    assert h.sugerida == "uno_es_si" and "uno_es_no" in h.opciones
    col = final.encabezados.index("has_usado_la_bolsa_de_trabajo")
    assert [final.filas[i][col] for i in (2, 3, 4)] == ["Sí", "Sí", "No"]
    _, invertido = _correr("encuesta", _csv(ENCABEZADO, datos), decisiones={h.id: "uno_es_no"})
    assert [invertido.filas[i][col] for i in (3, 4)] == ["No", "Sí"]


def test_opcion_mal_escrita_se_propone_cambiar():
    datos = _encuesta()
    datos[7][8] = "Una vez al mse"
    auto, final = _correr("encuesta", _csv(ENCABEZADO, datos))
    h = _hallazgo(auto, "categoria-parecida:")
    assert h.sugerida == "cambiar:Una vez al mes"
    col = final.encabezados.index("con_que_frecuencia_usas_la_biblioteca")
    assert final.filas[7][col] == "Una vez al mes"
    _, conservada = _correr("encuesta", _csv(ENCABEZADO, datos), decisiones={h.id: "conservar"})
    assert conservada.filas[7][col] == "Una vez al mse"


def test_opciones_que_solo_cambian_en_un_numero_no_se_unen():
    from services.motores.encuestas import categorias, universales
    from shared.parsing import read_tabular

    datos = [[f"R{i}", "Grupo 1" if i < 30 else "Grupo 2"] for i in range(31)]
    tabla = universales.preparar(read_tabular(_csv(["id", "grupo"], datos), ".csv"), [])
    assert categorias.parecidas(tabla) == []


# ── Pruebas estandarizadas ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("B)", ("B", "letra_con_signos")), ("(C)", ("C", "letra_con_signos")), ("c.", ("c", "letra_con_signos")),
     ("D-", ("D", "letra_con_signos")), ("AA", ("A", "misma_letra_repetida")), ("А", ("A", "letra_parecida")),
     ("Ｃ", ("C", "letra_parecida")), ("N/R", ("", "no_respondida_escrita")), ("Sin respuesta", ("", "no_respondida_escrita")),
     ("-", ("", "no_respondida_escrita")), ("AB", ("AB", None)), ("0", ("0", None)), ("X)", ("X)", None))],
)
def test_normalizar_respuesta(valor, esperado):
    tokens = {"n/r", "sin respuesta", "-", "n/a"}
    assert tp.normalizar_respuesta(valor, {"A", "B", "C", "D"}, tokens) == esperado


ENCABEZADO_PRUEBA = ["id_alumno", "genero", "edad", "P1", "P2", "P3", "P4", "P5"]


def _prueba(n: int = 20) -> list[list[str]]:
    letras = "ABCD"
    return [[f"R{i:04d}", ["F", "M"][i % 2], str(18 + i % 6), *(letras[(i + k) % 4] for k in range(5))] for i in range(n)]


def test_reactivo_sin_respuestas_se_conserva_con_100_por_ciento_nr():
    datos = _prueba()
    for f in datos:
        f[5] = ""  # nadie respondió P3
    auto, final = _correr("prueba_estandarizada", _csv(ENCABEZADO_PRUEBA, datos))
    h = _hallazgo(auto, "reactivo-vacio:")
    assert h.id == "reactivo-vacio:P3" and h.sugerida == "conservar"
    assert not any("no parecen reactivos" in a for a in auto.avisos)
    p3 = [f for f in final.filas if f[1] == "P3"]
    assert len(p3) == 20 and {f[3] for f in p3} == {"NR"}
    _, sin_p3 = _correr("prueba_estandarizada", _csv(ENCABEZADO_PRUEBA, datos), decisiones={h.id: "eliminar"})
    assert not [f for f in sin_p3.filas if f[1] == "P3"]


def test_respuestas_con_signos_cuentan_como_validas():
    datos = _prueba()
    datos[0][3], datos[1][3], datos[2][3], datos[3][3] = "B)", "N/R", "AA", "А"
    auto, final = _correr("prueba_estandarizada", _csv(ENCABEZADO_PRUEBA, datos))
    assert _reglas(auto)["respuestas_normalizadas"] == 4
    p1 = {f[0]: (f[2], f[3]) for f in final.filas if f[1] == "P1"}
    assert p1["R0000"] == ("B", "valida") and p1["R0002"] == ("A", "valida") and p1["R0003"] == ("A", "valida")
    assert p1["R0001"][1] == "NR"


def test_id_escrito_distinto_con_mismas_respuestas_es_el_mismo_alumno():
    datos = _prueba()
    copia = list(datos[5])
    copia[0] = "r005"  # «R0005» en minúscula y sin ceros
    datos.append(copia)
    auto, final = _correr("prueba_estandarizada", _csv(ENCABEZADO_PRUEBA, datos))
    h = _hallazgo(auto, "id-parecido:")
    assert h.sugerida == "conservar_primero" and "R0005" in h.titulo and "r005" in h.titulo
    assert final.metricas["n_alumnos"] == 20
    assert final.metricas["motivos"]["duplicado"] == 5


def test_prueba_con_encabezado_repetido_y_fila_corrida():
    datos = _prueba()
    datos[8] = datos[8][:1] + datos[8][2:] + [""]  # falta «genero»: las respuestas quedan en el reactivo equivocado
    datos.insert(12, list(ENCABEZADO_PRUEBA))
    auto, final = _correr("prueba_estandarizada", _csv(ENCABEZADO_PRUEBA, datos))
    assert _reglas(auto)["encabezado_repetido"] == 1
    h = _hallazgo(auto, "fila-corrida:")
    assert "genero" in h.titulo and h.sugerida == "reparar"
    assert final.metricas["n_alumnos"] == 20
    esperado = _prueba()[8]
    r8 = {f[1]: f[2] for f in final.filas if f[0] == "R0008"}
    assert [r8[p] for p in ("P1", "P2", "P3", "P4", "P5")] == esperado[3:]


# ── Entrevistas ────────────────────────────────────────────────────────────────

ENTREVISTA = """Universidad Tecnológica — Transcripción confidencial — Proyecto 2026

Entrevistadora: Hola, gracias por venir. ¿Cómo te sientes este semestre?
Entrevistada: Bien, aunque con estrés [risas] por los parciales y la ansiedad que me dan.
Entrevistadora: ¿Has buscado apoyo?
Entrevistada (min 12): Sí, fui a orientación (silencio) dos veces.
Documento de uso interno.
Universidad Tecnológica — Transcripción confidencial — Proyecto 2026
Entrevistadora: ¿Qué cambiarías?
Entrevistada: Que hubiera más horarios [inaudible 00:05:41] para pedir cita, o a n s i e d a d menos.
Documento de uso interno.
Universidad Tecnológica — Transcripción confidencial — Proyecto 2026
Entrevistadora: Gracias.
Entrevistada: A ti.
Documento de uso interno.
"""


def test_entrevista_con_encabezados_minuto_en_etiqueta_y_anotaciones():
    auto, final = _correr("entrevista", ENTREVISTA.encode("utf-8"), ".txt")
    reglas = _reglas(auto, final)
    assert reglas["encabezados_repetidos"] == 6
    assert reglas["transcripcion_minutos_en_etiqueta"] == 1
    h = _hallazgo(auto, "anotaciones")
    assert h.sugerida == "quitar" and "[risas]" in h.detalle["ejemplos"] and h.detalle["total"] == 3
    hablantes = {f[1] for f in final.filas}
    assert hablantes == {"Entrevistadora", "Entrevistada"}  # sin «Universidad Tecnológica» como hablante
    textos = [f[-1] for f in final.filas]
    assert len(final.filas) == 8
    assert "Sí, fui a orientación dos veces." in textos  # el turno del minuto 12 ya no se pega a la pregunta
    assert not any("[" in t or "(silencio)" in t or "Documento de uso" in t for t in textos)
    assert any("o ansiedad menos" in t for t in textos)  # «ansiedad» aparece en el documento: «o» es palabra aparte


def test_anotaciones_se_conservan_si_el_investigador_lo_decide():
    _, final = _correr("entrevista", ENTREVISTA.encode("utf-8"), ".txt", {"anotaciones": "conservar"})
    assert any("[risas]" in f[-1] for f in final.filas)


def test_preguntas_repetidas_del_guion_no_se_quitan():
    from services.motores.texto import quitar_lineas_repetidas

    texto = "\n".join(["RESPONDENTE: R1", "P1: ¿Cuál es tu carrera?", "R: Pedagogía.",
                       "RESPONDENTE: R2", "P1: ¿Cuál es tu carrera?", "R: Derecho.",
                       "RESPONDENTE: R3", "P1: ¿Cuál es tu carrera?", "R: Medicina.",
                       "-------------------", "-------------------", "-------------------"])
    assert quitar_lineas_repetidas(texto) == (texto, 0)


def test_letras_espaciadas_ambiguas_se_unen_y_se_reportan():
    from services.motores.texto import limpiar

    r = limpiar("E: ¿Qué estudias?\nR: Estudio e d u c a c i ó n en la normal.")
    assert "educación" in r.texto and r.dudosas == ["educación"]
