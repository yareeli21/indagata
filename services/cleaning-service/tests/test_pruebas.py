"""Pruebas del motor de pruebas estandarizadas con archivos pequeños y SUCIOS.

La hoja de respuestas de ejemplo incluye a propósito: una fila vacía, un ID de
alumno repetido, respuestas múltiples («AB», «A,C»), ilegibles («*», «?»),
caracteres inválidos («E», «x»), respuestas vacías y «NR» explícito, minúsculas
y espacios, y una columna extra que no está en la clave.
"""
from __future__ import annotations

import csv
import io

import pytest

from shared.models.limpieza_ejecucion import LimpiezaEjecucion

from conftest import ANA, crear_instrumento

RESPUESTAS = """matricula;P1;P2;P3;P4;grupo;observaciones
A001;A;B;C;D;3A;x
A002; b ;B;AB;NR;3A;
A003;*;E;;D;3B;
  ;  ;  ;  ;  ;  ;  
A004;C;?;A,C;x;3B;
A002;A;B;C;D;3A;
"""
CLAVE_LARGA = "pregunta,respuesta\nP1,A\nP2,B\nP3,C\nP4,D\n"
CLAVE_ANCHA = "P1;P2;P3;P4\nA;B;C;D\n"


def _crear(db, storage, respuestas: str = RESPUESTAS, clave: str = CLAVE_LARGA, nombre_clave: str = "clave.csv") -> int:
    return crear_instrumento(
        db, storage, "respuestas.csv", respuestas.encode("utf-8"), tipo="prueba_estandarizada",
        clave=(nombre_clave, clave.encode("utf-8")),
    )


def _limpio(storage, db) -> list[list[str]]:
    fila = db.query(LimpiezaEjecucion).order_by(LimpiezaEjecucion.version.desc()).first()
    return list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("A", (1, "valida", "")),
        (" b ", (0, "valida", "")),
        ("", (0, "NR", "no_respondida")),
        ("NR", (0, "NR", "no_respondida")),
        ("AB", (0, "nula", "respuesta_multiple")),
        ("A,C", (0, "nula", "respuesta_multiple")),
        ("*", (0, "nula", "ilegible")),
        ("A?", (0, "nula", "ilegible")),
        ("E", (0, "nula", "caracter_invalido")),
        ("x", (0, "nula", "caracter_invalido")),
    ],
)
def test_clasificar_respuestas(valor, esperado):
    from services.motores.pruebas.motor import clasificar

    assert clasificar(valor, {"A", "B", "C", "D"}, {"*", "?", "#"}, "A") == esperado


def test_fase_automatica_y_duplicados_en_fase_asistida(cliente, db, storage):
    id_crudo = _crear(db, storage)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones", e
    reglas = {t["regla"]: t["afectados"] for t in e["transformaciones"]}
    assert reglas["filas_vacias"] == 1
    assert reglas["respuestas_nulificadas"] == 6  # múltiples, ilegibles e inválidas (sin el duplicado)
    assert any("observaciones" in a and "no se incluirán" in a for a in e["avisos"])  # columna extra → aviso
    assert any("contexto" in a and "grupo" in a for a in e["avisos"])  # contexto → se conserva
    dup = [h for h in e["hallazgos"] if h["tipo"] == "id_duplicado"]
    assert len(dup) == 1 and dup[0]["objetivo"] == "A002" and dup[0]["sugerida"] == "conservar_primero"
    assert dup[0]["detalle"]["filas"] == [3, 7]
    m = e["metricasAntes"]
    assert m["n_alumnos"] == 4 and m["n_preguntas"] == 4 and m["n_ids_duplicados"] == 1


def test_confirmar_genera_formato_largo_con_correcta_estado_y_motivo(cliente, db, storage):
    id_crudo = _crear(db, storage)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()
    assert r["estado"] == "confirmada"
    filas = _limpio(storage, db)
    # La columna de contexto «grupo» se conserva al final; «observaciones» no.
    assert filas[0] == ["id_alumno", "pregunta", "respuesta", "respuesta_correcta", "correcta", "estado", "motivo", "grupo"]
    datos: dict[tuple[str, str], list[str]] = {}
    for f in filas[1:]:
        datos.setdefault((f[0], f[1]), f[2:7])  # primera aparición de cada alumno
    assert {f[0]: f[7] for f in filas[1:]} == {"A001": "3A", "A002": "3A", "A003": "3B", "A004": "3B"}
    # 5 registros (la fila vacía se eliminó) × 4 preguntas.
    assert len(filas) - 1 == 20
    assert datos[("A001", "P1")] == ["A", "A", "1", "valida", ""]
    assert datos[("A002", "P3")] == ["AB", "C", "0", "nula", "respuesta_multiple"]
    assert datos[("A002", "P4")] == ["NR", "D", "0", "NR", "no_respondida"]
    assert datos[("A003", "P1")] == ["*", "A", "0", "nula", "ilegible"]
    assert datos[("A003", "P2")] == ["E", "B", "0", "nula", "caracter_invalido"]
    assert datos[("A003", "P3")] == ["", "C", "0", "NR", "no_respondida"]
    assert datos[("A004", "P2")] == ["?", "B", "0", "nula", "ilegible"]
    # El segundo registro de A002 queda nulo por duplicado (se conservó el primero).
    segundo = [f for f in filas[1:] if f[0] == "A002"][4:]
    assert {f[5] for f in segundo} == {"nula"} and {f[6] for f in segundo} == {"duplicado"}

    cifras = {c["etiqueta"]: c["valor"] for c in r["vistaFinal"]["cifras"]}
    assert cifras == {"Alumnos": 4, "Preguntas": 4, "Respuestas nulas": 10, "No respondidas": 2}
    rep = db.query(LimpiezaEjecucion).one().reporte
    esp = rep["especifico"]["prueba_estandarizada"]
    assert esp["conteos"] == {"valida": 8, "nula": 10, "NR": 2}
    assert esp["motivos"] == {"duplicado": 4, "no_respondida": 2, "respuesta_multiple": 2, "caracter_invalido": 2, "ilegible": 2}
    assert esp["clave"] == {"P1": "A", "P2": "B", "P3": "C", "P4": "D"}


@pytest.mark.parametrize(("decision", "registros"), [("conservar_todos", 5), ("eliminar_todos", 3)])
def test_decisiones_sobre_ids_duplicados(cliente, db, storage, decision, registros):
    id_crudo = _crear(db, storage)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"id-duplicado:A002": decision}}, headers=ANA)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    filas = _limpio(storage, db)
    assert (len(filas) - 1) // 4 == registros
    assert "duplicado" not in {f[6] for f in filas[1:]}


def test_clave_ancha_en_xlsx(cliente, db, storage):
    import openpyxl

    libro = openpyxl.Workbook()
    libro.active.append(["P1", "P2", "P3", "P4"])
    libro.active.append(["A", "B", "C", "D"])
    buffer = io.BytesIO()
    libro.save(buffer)
    id_crudo = crear_instrumento(
        db, storage, "respuestas.csv", RESPUESTAS.encode("utf-8"), tipo="prueba_estandarizada",
        clave=("clave.xlsx", buffer.getvalue()),
    )
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones", e


@pytest.mark.parametrize(
    ("respuestas", "clave", "mensaje"),
    [
        ("matricula;P1;P2\nA001;A;B\n", CLAVE_LARGA, "no tiene columnas para 2 pregunta(s)"),
        (RESPUESTAS, "pregunta,respuesta\nP1,Z\n", "respuesta no válida"),
        ("matricula P1 P2\nA001 A B\n", CLAVE_LARGA, "delimitador"),
        (RESPUESTAS, "a,b,c\n1,2,3\n4,5,6\n", "formato de la clave"),
    ],
)
def test_errores_de_estructura_fallan_con_mensaje_claro(cliente, db, storage, respuestas, clave, mensaje):
    id_crudo = _crear(db, storage, respuestas, clave)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "fallida" and mensaje in e["error"], e


def test_sin_clave_falla(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "respuestas.csv", RESPUESTAS.encode(), tipo="prueba_estandarizada")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "fallida" and "clave de respuestas" in e["error"]


def test_prueba_en_documento_limpia_texto_por_bloques(cliente, db, storage):
    texto = (
        "Página 1\nExamen de Matemáticas — Primer parcial\n\n1. ¿Cuánto es 2 + 2?\nA) 3   B) 4   C) 5\n\n"
        "2. Resuelve la ecua-\nción x + 1 = 3\n\nPágina 2\n"
    )
    id_crudo = crear_instrumento(db, storage, "examen.txt", texto.encode("utf-8"), tipo="prueba_estandarizada")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones", e
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()
    assert r["estado"] == "confirmada" and r["vistaFinal"]["forma"] == "turnos"
    filas = _limpio(storage, db)
    assert filas[0] == ["n_bloque", "texto"]
    texto_limpio = " ".join(f[1] for f in filas[1:])
    assert "Página" not in texto_limpio and "ecuación" in texto_limpio


# ── Prueba sin clave: clave propuesta y tipos de reactivo ──────────────────────

# Los 4 de mayor puntaje responden la clave «real» (A, B, C, D, V); el resto se equivoca más.
SIN_CLAVE = """id_alumno,turno,r_q1,r_q2,r_q3,r_q4,vf_q1,corta_q1,escala_q1,sino_q1,calc_q1,score
S01,Matutino,A,B,C,D,V,2,5,Sí,12.5,0.95
S02,Vespertino,A,B,C,D,V,2,4,Sí,12.0,0.90
S03,Matutino,A,B,C,A,V,2,4,No,11.8,0.85
S04,Vespertino,A,B,D,D,V,1,3,Sí,12.5,0.80
S05,Matutino,B,B,A,A,F,1,2,No,9.0,0.40
S06,Vespertino,C,A,A,B,F,0,1,No,8.5,0.30
S07,Matutino,B,C,A,A,F,0,2,No,7.0,0.25
S08,Vespertino,C,A,B,B,F,1,1,Sí,6.5,0.20
S09,Matutino,D,C,A,C,F,0,3,No,5.0,0.15
S10,Vespertino,B,A,B,C,V,0,2,No,4.0,0.10
S11,Matutino,C,C,A,A,F,1,1,Sí,3.5,0.05
S12,Vespertino,D,A,B,B,F,0,1,No,3.0,0.02
"""


def test_tipos_de_reactivo_y_clave_propuesta_sin_archivo_de_clave(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "pru.csv", SIN_CLAVE.encode("utf-8"), tipo="prueba_estandarizada")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones", e.get("error")
    hallazgos = {h["id"]: h for h in e["hallazgos"]}
    # Confirmación obligatoria + un hallazgo por reactivo de opción (puntos y no calificables no).
    assert hallazgos["clave-confirmar"]["obligatoria"] and e["pendientesObligatorias"] == 1
    assert {k for k in hallazgos if k.startswith("clave:")} == {"clave:r_q1", "clave:r_q2", "clave:r_q3", "clave:r_q4", "clave:vf_q1"}
    # Grupo de referencia = 27 % de mayor «score»: S01–S03 → propuesta A, B, C, D (2 de 3), V.
    assert [hallazgos[f"clave:r_q{i}"]["sugerida"] for i in range(1, 5)] == ["A", "B", "C", "D"]
    assert hallazgos["clave:vf_q1"]["sugerida"] == "V" and hallazgos["clave:vf_q1"]["opciones"] == ["V", "F"]
    assert any("no trae clave" in a for a in e["avisos"])

    # Sin confirmar la clave no se puede cerrar la limpieza.
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 409
    # El investigador corrige r_q4 (la propuesta era D; la correcta es A) y confirma.
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones",
                  json={"decisiones": {"clave-confirmar": "confirmar", "clave:r_q4": "A"}}, headers=ANA)
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text

    esp = db.query(LimpiezaEjecucion).one().reporte["especifico"]["prueba_estandarizada"]
    assert esp["clave_origen"] == "inferida"
    assert esp["clave"] == {"r_q1": "A", "r_q2": "B", "r_q3": "C", "r_q4": "A", "vf_q1": "V", "corta_q1": "2"}
    assert esp["tipos_reactivo"] == {"r_q1": "opcion_multiple", "r_q2": "opcion_multiple", "r_q3": "opcion_multiple",
                                     "r_q4": "opcion_multiple", "vf_q1": "verdadero_falso", "corta_q1": "puntos",
                                     "escala_q1": "escala", "sino_q1": "si_no", "calc_q1": "numerica"}
    assert esp["puntos_max"] == {"corta_q1": 2, "escala_q1": 5}
    assert [c["id"] for c in esp["columnas_contexto"]] == ["turno", "score"]  # el puntaje global es dato del alumno

    filas = _limpio(storage, db)
    datos = {(f[0], f[1]): f for f in filas[1:]}
    assert datos[("S03", "r_q4")][3:6] == ["A", "1", "valida"]  # con la clave corregida
    assert datos[("S04", "corta_q1")][2:6] == ["1", "2", "0", "valida"]  # parcial: 1 de 2 no es acierto
    assert datos[("S01", "corta_q1")][4] == "1"
    assert datos[("S01", "escala_q1")][3:6] == ["", "", "valida"]  # no calificable: sin clave ni acierto
    assert datos[("S05", "sino_q1")][2:6] == ["No", "", "", "valida"]
    assert datos[("S01", "calc_q1")][2:6] == ["12.5", "", "", "valida"]
    # KR-20 y aciertos solo con los 6 reactivos calificables.
    assert esp["fiabilidad"]["n_reactivos"] == 6


@pytest.mark.parametrize(
    ("valor", "tipo", "maximo", "esperado"),
    [
        ("V", "verdadero_falso", None, (1, "valida", "")),
        ("Falso", "verdadero_falso", None, (0, "valida", "")),
        ("X", "verdadero_falso", None, (0, "nula", "caracter_invalido")),
        ("2", "puntos", 2, (1, "valida", "")),
        ("1", "puntos", 2, (0, "valida", "")),
        ("3", "puntos", 2, (0, "nula", "caracter_invalido")),
        ("4", "escala", 5, (None, "valida", "")),
        ("0", "escala", 5, (None, "nula", "caracter_invalido")),
        ("sí", "si_no", None, (None, "valida", "")),
        ("", "si_no", None, (None, "NR", "no_respondida")),
        ("12,5", "numerica", None, (None, "valida", "")),
    ],
)
def test_clasificar_por_tipo_de_reactivo(valor, tipo, maximo, esperado):
    from services.motores.pruebas.motor import clasificar

    correcta = {"verdadero_falso": "V", "puntos": "2"}.get(tipo, "")
    assert clasificar(valor, {"A", "B", "C", "D"}, {"*", "?", "#"}, correcta, tipo, maximo) == esperado


def test_clave_con_vf_y_puntos_desde_archivo(cliente, db, storage):
    respuestas = "matricula;P1;P2;P3\nA1;A;V;2\nA2;B;F;1\nA3;A;V;0\n"
    id_crudo = _crear(db, storage, respuestas, "pregunta,respuesta\nP1,A\nP2,Verdadero\nP3,2\n")
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    esp = db.query(LimpiezaEjecucion).one().reporte["especifico"]["prueba_estandarizada"]
    assert esp["clave"] == {"P1": "A", "P2": "V", "P3": "2"} and esp["clave_origen"] == "archivo"
    assert esp["tipos_reactivo"] == {"P1": "opcion_multiple", "P2": "verdadero_falso", "P3": "puntos"}
    datos = {(f[0], f[1]): f for f in _limpio(storage, db)[1:]}
    assert datos[("A2", "P2")][4] == "0" and datos[("A1", "P3")][4] == "1" and datos[("A2", "P3")][4] == "0"
