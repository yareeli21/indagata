"""Pruebas del motor de entrevistas con transcripciones pequeñas y SUCIAS.

La transcripción de ejemplo incluye a propósito: marcas de tiempo, encabezados de
página, un identificador, una línea separadora, palabras partidas por guion de fin
de línea, una palabra con letras espaciadas, turnos que continúan en la línea
siguiente y espacios de más.
"""
from __future__ import annotations

import csv
import io

import pytest

from shared.models.limpieza_ejecucion import LimpiezaEjecucion

from conftest import ANA, crear_instrumento

SUCIA = """ID: ENT-003
Página 1 de 2
[00:00:05] Entrevistador: Buenos días, gracias por aceptar la entrevista. ¿Cómo te llamas?
[00:00:09] Ana: Me llamo Ana y estudio el quinto semestre de   pedagogía.
Entrevistador: ¿Qué te motivó a elegir la carrera?
Ana: Siempre me gustó enseñar; mi mamá es maestra y la acompañaba a la es-
cuela desde pequeña.
----------
Página 2 de 2
Entrevistador: ¿Cómo describirías tu experiencia con la e d u c a c i ó n en línea?
Ana: Fue difícil al principio, pero aprendí a organizarme
con un horario fijo.
Entrevistador: ¿Algo más que quieras agregar?
Ana: No, eso es todo. Gracias.
"""


def _limpio(storage, db) -> list[list[str]]:
    fila = db.query(LimpiezaEjecucion).order_by(LimpiezaEjecucion.version.desc()).first()
    return list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))


def _ejecutar(cliente, db, storage, nombre: str, contenido: bytes) -> tuple[int, dict]:
    id_crudo = crear_instrumento(db, storage, nombre, contenido, tipo="entrevista")
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert r.status_code == 200, r.text
    return id_crudo, r.json()


# ── Ciclo de ruido (Figura 1) ──────────────────────────────────────────────────


def test_ciclo_quita_ruido_y_reconstruye_palabras():
    from services.motores.texto import limpiar

    r = limpiar(SUCIA)
    assert "00:00" not in r.texto and "Página" not in r.texto and "ENT-003" not in r.texto
    assert "-----" not in r.texto
    assert "escuela" in r.texto and "educación" in r.texto  # guion y letras espaciadas
    assert "de pedagogía" in r.texto  # espacios de más
    assert r.eliminado["marcas_de_tiempo"] == 2
    assert r.eliminado["numeros_de_pagina"] == 2
    assert r.eliminado["identificadores"] == 1
    assert r.residual == [] and 1 <= r.iteraciones <= 3


def test_ciclo_repite_si_la_reconstruccion_deja_ruido_nuevo():
    from services.motores.texto import limpiar

    # «Pá-\ngina 3» solo se reconoce como número de página tras unir la palabra partida.
    texto = "E: Hola.\nPá-\ngina 3\nR: Hola."
    r = limpiar(texto)
    assert "gina" not in r.texto and r.iteraciones == 2
    # Con una sola iteración el ruido queda y se reporta.
    r1 = limpiar(texto, max_iteraciones=1)
    assert r1.residual and r1.residual[0]["tipo"] == "numero_de_pagina"


def test_ciclo_se_detiene_si_no_hay_ruido():
    from services.motores.texto import limpiar

    assert limpiar("E: Hola.\nR: Buenos días.").iteraciones == 1


# ── Motor completo ─────────────────────────────────────────────────────────────


def test_hablantes_roles_y_csv_de_turnos(cliente, db, storage):
    id_crudo, e = _ejecutar(cliente, db, storage, "entrevista.txt", SUCIA.encode("utf-8"))
    assert e["estado"] == "esperando_decisiones" and e["pendientesObligatorias"] == 0
    roles = {h["objetivo"]: h["sugerida"] for h in e["hallazgos"] if h["tipo"] == "rol_hablante"}
    assert roles == {"Entrevistador": "entrevistador", "Ana": "entrevistado"}
    reglas = {t["regla"]: t["afectados"] for t in e["transformaciones"]}
    assert reglas["marcas_de_tiempo"] == 2 and reglas["palabras_reconstruidas"] >= 2
    assert e["metricasAntes"]["ruido_detectado"] > 0

    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()
    assert r["estado"] == "confirmada"
    filas = _limpio(storage, db)
    assert filas[0] == ["n_turno", "hablante", "rol", "texto"]
    assert len(filas) - 1 == 8
    assert filas[1][:3] == ["1", "Entrevistador", "entrevistador"]
    assert filas[4][1:3] == ["Ana", "entrevistado"]
    # El turno que seguía en la línea siguiente quedó completo y sin guion.
    assert filas[4][3] == "Siempre me gustó enseñar; mi mamá es maestra y la acompañaba a la escuela desde pequeña."

    vista = r["vistaFinal"]
    assert vista["forma"] == "turnos" and vista["columnas"] == ["#", "Hablante", "Rol", "Texto"]
    cifras = {c["etiqueta"]: c["valor"] for c in vista["cifras"]}
    assert cifras["Turnos"] == 8 and cifras["Hablantes"] == 2 and cifras["Ruido eliminado"] >= 5

    rep = db.query(LimpiezaEjecucion).one().reporte
    esp = rep["especifico"]["entrevista"]
    assert esp["estructura_reconocida"] is True
    assert {h["nombre"]: h["rol"] for h in esp["hablantes"]} == {"Entrevistador": "entrevistador", "Ana": "entrevistado"}
    assert rep["metricas"]["despues"]["n_turnos"] == 8 and rep["metricas"]["despues"]["ruido_detectado"] == 0


def test_el_investigador_corrige_un_rol(cliente, db, storage):
    id_crudo, e = _ejecutar(cliente, db, storage, "entrevista.txt", SUCIA.encode("utf-8"))
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"rol-hablante:ana": "otro"}}, headers=ANA)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    filas = _limpio(storage, db)
    assert {f[2] for f in filas[1:] if f[1] == "Ana"} == {"otro"}


def test_roles_por_proporcion_de_preguntas_con_nombres(cliente, db, storage):
    texto = (
        "María: ¿Cuántos años tienes?\nLuis: Veinte.\nMaría: ¿Trabajas?\nLuis: Sí, medio tiempo.\n"
        "María: ¿Te alcanza el tiempo para estudiar?\nLuis: A veces no."
    )
    _, e = _ejecutar(cliente, db, storage, "nombres.txt", texto.encode("utf-8"))
    roles = {h["objetivo"]: h["sugerida"] for h in e["hallazgos"] if h["tipo"] == "rol_hablante"}
    assert roles == {"María": "entrevistador", "Luis": "entrevistado"}


def test_sin_estructura_de_hablantes_avisa_y_sigue_por_parrafos(cliente, db, storage):
    texto = (
        "La entrevista se realizó en la biblioteca.\n\nLa estudiante comentó que el transporte es su mayor problema.\n\n"
        "También mencionó que trabaja por las tardes."
    )
    id_crudo, e = _ejecutar(cliente, db, storage, "notas.txt", texto.encode("utf-8"))
    assert any("No reconocimos la estructura de hablantes" in a for a in e["avisos"])
    assert e["pendientesObligatorias"] == 1
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 409
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"sin-hablantes": "continuar_por_parrafos"}}, headers=ANA)
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["estado"] == "confirmada"
    filas = _limpio(storage, db)
    assert len(filas) - 1 == 3 and {f[2] for f in filas[1:]} == {"desconocido"}
    assert db.query(LimpiezaEjecucion).one().reporte["especifico"]["entrevista"]["estructura_reconocida"] is False


def test_docx(cliente, db, storage):
    import docx

    documento = docx.Document()
    for linea in SUCIA.strip().split("\n"):
        documento.add_paragraph(linea)
    buffer = io.BytesIO()
    documento.save(buffer)
    id_crudo, e = _ejecutar(cliente, db, storage, "entrevista.docx", buffer.getvalue())
    assert len([h for h in e["hallazgos"] if h["tipo"] == "rol_hablante"]) == 2
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["estado"] == "confirmada"


def test_pdf_sin_texto_falla_con_mensaje_claro(cliente, db, storage):
    from pypdf import PdfWriter

    escritor = PdfWriter()
    escritor.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    escritor.write(buffer)
    _, e = _ejecutar(cliente, db, storage, "escaneado.pdf", buffer.getvalue())
    assert e["estado"] == "fallida" and "OCR" in e["error"]


@pytest.mark.parametrize("linea", ["Nota: la grabación tiene ruido.", "Objetivo: conocer la experiencia."])
def test_etiquetas_sueltas_no_se_confunden_con_hablantes(linea):
    from services.motores.entrevistas.hablantes import segmentar

    texto = f"{linea}\nEntrevistador: ¿Cómo estás?\nAna: Bien.\nEntrevistador: ¿Y la escuela?\nAna: Bien también."
    estructura = segmentar(texto, {"entrevistador"})
    assert {h.nombre for h in estructura.hablantes} == {"Entrevistador", "Ana"}


# ── Varias entrevistas en un archivo (guion numerado aplicado a N personas) ────

BLOQUES = """======================================================================
INSTRUMENTO: Entrevista sobre permanencia
Tipo: Entrevista semiestructurada
N° de respondentes: 2
======================================================================

RESPONDENTE: R0001
Perfil: P2 — Promedio comprometido
Edad: 23  |  Género: masculino  |  Semestre: 3

P1: ¿Qué factores te han ayudado a continuar tus estudios?
R: El apoyo de mi familia y de mis compañeros de clase.

P2: ¿Has pensado en abandonar la universidad?
R: Sí, en el primer semestre, pero el orientador me ayudó.

RESPONDENTE: R0002
Perfil: P3 — En riesgo
Edad: 21  |  Género: femenino  |  Semestre: 5

P1: ¿Qué factores te han ayudado a continuar tus estudios?
R: Las becas.

P2: ¿Has pensado en abandonar la universidad?
R:

======================================================================
FIN DEL INSTRUMENTO
"""


def test_bloques_de_respondentes_y_preguntas_numeradas():
    from services.motores.entrevistas.hablantes import segmentar, sugerir_roles

    e = segmentar(BLOQUES, {"r", "entrevistador"})
    assert e.reconocida
    # P1, P2 son UN hablante (el entrevistador); los encabezados no son hablantes.
    assert {h.nombre for h in e.hablantes} == {"P", "R"}
    assert [p.id for p in e.participantes] == ["R0001", "R0002"]
    assert e.participantes[0].contexto == {"Perfil": "P2 — Promedio comprometido", "Edad": "23", "Género": "masculino", "Semestre": "3"}
    assert e.preambulo[0].startswith("INSTRUMENTO")
    assert [t.numero for t in e.turnos if t.hablante == "P"] == [1, 2, 1, 2]
    assert {t.participante for t in e.turnos} == {"R0001", "R0002"}
    assert "FIN" not in e.turnos[-1].texto
    roles = sugerir_roles(e.hablantes, {"entrevistador"}, {"r"})
    assert roles["P"][0] == "entrevistador" and roles["R"][0] == "entrevistado"


def test_estadistica_centrada_en_respuestas(cliente, db, storage):
    id_crudo, e = _ejecutar(cliente, db, storage, "bloques.txt", BLOQUES.encode("utf-8"))
    assert e["pendientesObligatorias"] == 0
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()
    filas = _limpio(storage, db)
    assert filas[0] == ["n_turno", "participante", "hablante", "rol", "texto"]
    assert filas[1][1:4] == ["R0001", "P", "entrevistador"]
    est = r["vistaFinal"]["estadistica"]
    assert est["n_participantes"] == 2 and est["n_preguntas"] == 2 and est["n_respuestas"] == 3
    p1, p2 = est["preguntas"]
    assert (p1["pregunta"], p1["n_respuestas"], p1["sin_respuesta"]) == ("P1", 2, 0)
    assert (p2["pregunta"], p2["n_respuestas"], p2["sin_respuesta"]) == ("P2", 1, 1)
    assert {p["id"]: p["respuestas"] for p in est["participantes"]} == {"R0001": 2, "R0002": 1}
    assert est["palabras_por_rol"][0]["rol"] == "entrevistado"
    cifras = {c["etiqueta"]: c["valor"] for c in r["vistaFinal"]["cifras"]}
    assert cifras["Entrevistados"] == 2 and cifras["Hablantes"] == 2
    esp = db.query(LimpiezaEjecucion).one().reporte["especifico"]["entrevista"]
    assert esp["participantes"][1] == {"id": "R0002", "contexto": {"Perfil": "P3 — En riesgo", "Edad": "21", "Género": "femenino", "Semestre": "5"}}
