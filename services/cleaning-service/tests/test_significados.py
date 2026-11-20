"""Microdatos: texto de las preguntas en código y significado de sus códigos (diccionario de datos o a mano).

La encuesta de ejemplo trae encabezados en código (P1…P4) y respuestas en código: P1 es sexo (1/2), P2 turno
(1/2/3), P3 una escala 1–5 y P4 una pregunta con letras (A–D). El diccionario de datos explica P1, P2 y P4 y
trae una variable que no está en el archivo.
"""
from __future__ import annotations

import csv
import io

import pytest

from shared.conocimiento.significados import DiccionarioInvalido, de_reporte, etiqueta, leer_diccionario
from shared.models.limpieza_ejecucion import LimpiezaEjecucion
from shared.models.raw_data import RawData

from conftest import ANA, crear_instrumento

ENCABEZADOS = ["folio", "P1", "P2", "P3", "P4"]
FILAS = [
    [str(i + 1), ["1", "2"][i % 2], ["1", "2", "3"][i % 3], str(1 + i % 5), "ABCD"[i % 4]]
    for i in range(30)
]
DICCIONARIO = (
    "variable,pregunta,valor,etiqueta\n"
    "P1,¿Cuál es tu sexo?,1,Hombre\n"
    ",,2,Mujer\n"
    "P2,¿En qué turno estudias?,1,Matutino\n"
    "P2,,2,Vespertino\n"
    "P2,,3,Mixto\n"
    "P4,¿Qué medio usas para estudiar?,A,Libros\n"
    ",,B,Videos\n"
    "P9,Variable que no está en el archivo,1,Sí\n"
).encode("utf-8")


def _csv(encabezados: list[str], filas: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    csv.writer(buffer).writerows([encabezados, *filas])
    return buffer.getvalue().encode("utf-8")


def _con_diccionario(db, storage, id_crudo: int, contenido: bytes = DICCIONARIO) -> None:
    ruta = f"raw/_/{len(storage.archivos) + 1}__diccionario.csv"
    storage.archivos[ruta] = contenido
    db.get(RawData, id_crudo).raw_archivo_diccionario = ruta
    db.commit()


def _columna(ejec: dict, clave: str) -> dict:
    return next(c for c in ejec["codigos"]["columnas"] if c["clave"] == clave)


def _confirmar(cliente, id_crudo: int, ejec: dict, version: int = 1) -> dict:
    roles = {h["id"]: "pregunta" for h in ejec["hallazgos"] if h["tipo"] == "rol_columna"}
    r = cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/{version}/decisiones", json={"decisiones": roles}, headers=ANA)
    assert r.status_code == 200, r.text
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/{version}/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    return r.json()


# ── Diccionario de datos ───────────────────────────────────────────────────────


def test_diccionario_formato_largo_y_ancho():
    d = leer_diccionario(DICCIONARIO, ".csv")
    assert d.buscar("p1").pregunta == "¿Cuál es tu sexo?"
    assert d.buscar("P1").valores == {"1": "Hombre", "2": "Mujer"}  # la segunda fila hereda la variable
    ancho = 'Variable;Etiqueta de la variable;Valores\nP1_4_1;Edad;\nQ3;Turno;"1 = Matutino; 2 = Vespertino"\n'
    d = leer_diccionario(ancho.encode("utf-8"), ".csv")
    assert d.buscar("p1.4.1").pregunta == "Edad"  # «P1_4_1» y «p1.4.1» son la misma variable
    assert d.buscar("Q3").valores == {"1": "Matutino", "2": "Vespertino"}
    assert etiqueta(d.buscar("Q3").valores, "01") == "Matutino"  # «01» y «1» son el mismo código


def test_diccionario_sin_columna_variable_se_rechaza():
    with pytest.raises(DiccionarioInvalido, match="variable"):
        leer_diccionario(b"pregunta,valor\nSexo,1\n", ".csv")


# ── Limpieza ───────────────────────────────────────────────────────────────────


def test_columnas_en_codigo_se_ofrecen_sin_diccionario(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "micro.csv", _csv(ENCABEZADOS, FILAS))
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    claves = [c["clave"] for c in e["codigos"]["columnas"]]
    assert claves == ["p1", "p2", "p3", "p4"]  # «folio» es de la plataforma: no se ofrece
    assert [c["codigo"] for c in _columna(e, "p4")["codigos"]] == ["A", "B", "C", "D"]
    assert _columna(e, "p1")["pregunta"] is None and e["codigos"]["diccionario"] is None


def test_diccionario_precarga_texto_y_etiquetas(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "micro.csv", _csv(ENCABEZADOS, FILAS))
    _con_diccionario(db, storage, id_crudo)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    p1 = _columna(e, "p1")
    assert p1["pregunta"] == "¿Cuál es tu sexo?" and p1["etiquetas"] == {"1": "Hombre", "2": "Mujer"}
    assert p1["origen"] == "diccionario"
    assert _columna(e, "p3")["etiquetas"] == {}  # P3 no está en el diccionario
    dic = e["codigos"]["diccionario"]
    assert dic["nombre"] == "diccionario.csv" and dic["emparejadas"] == 3 and dic["sin_columna"] == ["P9"]
    # «¿Qué es P2?»: con el texto del diccionario se sugiere el rol y ya no es obligatorio decidirlo.
    rol = {h["objetivo"]: h for h in e["hallazgos"] if h["tipo"] == "rol_columna"}
    assert rol["p2"]["sugerida"] == "contexto" and rol["p2"]["obligatoria"] is False  # «¿En qué turno estudias?»
    assert rol["p4"]["sugerida"] == "pregunta" and "medio usas para estudiar" in rol["p4"]["descripcion"]
    assert rol["p3"]["obligatoria"] is True  # P3 no está en el diccionario


def test_lo_escrito_a_mano_se_guarda_y_pasa_al_reporte(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "micro.csv", _csv(ENCABEZADOS, FILAS))
    _con_diccionario(db, storage, id_crudo)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    cambios = {"p3": {"pregunta": "  ¿Qué tan satisfecho  estás?", "valores": {"1": "Nada", "5": "Mucho", "3": " "}}}
    r = cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/significados", json={"significados": cambios}, headers=ANA)
    assert r.status_code == 200, r.text
    p3 = _columna(r.json(), "p3")
    assert p3["pregunta"] == "¿Qué tan satisfecho estás?" and p3["etiquetas"] == {"1": "Nada", "5": "Mucho"}
    assert p3["origen"] == "investigador"
    r = cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/significados",
                      json={"significados": {"no_existe": {"pregunta": "x"}}}, headers=ANA)
    assert r.status_code == 422

    final = _confirmar(cliente, id_crudo, e)
    assert final["estado"] == "confirmada" and final["codigos"] is None
    rep = db.query(LimpiezaEjecucion).one().reporte
    sig = de_reporte(rep, "encuesta")
    assert sig["p1"] == {"pregunta": "¿Cuál es tu sexo?", "valores": {"1": "Hombre", "2": "Mujer"}}
    assert sig["p3"]["valores"] == {"1": "Nada", "5": "Mucho"}
    assert sig["p4"]["valores"] == {"A": "Libros", "B": "Videos"}


def test_repetir_la_limpieza_conserva_lo_confirmado(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "micro.csv", _csv(ENCABEZADOS, FILAS))
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/significados",
                  json={"significados": {"p1": {"pregunta": "Sexo", "valores": {"1": "Hombre", "2": "Mujer"}}}}, headers=ANA)
    _confirmar(cliente, id_crudo, e)
    e2 = cliente.post(f"/limpieza/{id_crudo}/ejecuciones?nueva=true", headers=ANA).json()
    assert e2["version"] == 2
    p1 = _columna(e2, "p1")
    assert p1["pregunta"] == "Sexo" and p1["etiquetas"]["2"] == "Mujer" and p1["origen"] == "anterior"


def test_diccionario_ilegible_no_detiene_la_limpieza(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "micro.csv", _csv(ENCABEZADOS, FILAS))
    _con_diccionario(db, storage, id_crudo, b"pregunta,valor\nSexo,1\n")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones"
    assert any("diccionario de datos" in a for a in e["avisos"])


def test_reactivos_de_una_prueba_se_ofrecen(cliente, db, storage):
    encabezados = ["id_alumno", "P1", "P2"]
    filas = [[f"A{i}", "ABCD"[i % 4], "ABC"[i % 3]] for i in range(12)]
    id_crudo = crear_instrumento(db, storage, "prueba.csv", _csv(encabezados, filas), tipo="prueba_estandarizada")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert [c["clave"] for c in e["codigos"]["columnas"]] == ["P1", "P2"]
    # Todas las opciones válidas, aunque nadie haya elegido una (D en P2): también se les puede dar significado.
    assert [c["codigo"] for c in _columna(e, "P2")["codigos"]] == ["A", "B", "C", "D"]


def test_texto_largo_del_diccionario_es_pregunta_aunque_nombre_la_escuela(cliente, db, storage):
    # «escuela» es una palabra de contexto, pero en una afirmación larga es parte de la pregunta.
    dic = "variable,pregunta\nP1,Me siento seguro dentro de las instalaciones de la escuela.\nP2,Escuela\n".encode("utf-8")
    id_crudo = crear_instrumento(db, storage, "micro.csv", _csv(ENCABEZADOS, FILAS))
    _con_diccionario(db, storage, id_crudo, dic)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    rol = {h["objetivo"]: h for h in e["hallazgos"] if h["tipo"] == "rol_columna"}
    assert rol["p1"]["sugerida"] == "pregunta" and rol["p2"]["sugerida"] == "contexto"
