"""Pruebas del motor de pruebas estandarizadas con archivos pequeños y SUCIOS.

Indagata no califica las pruebas: no hay clave de respuestas, solo se limpia y se describe
lo que contestaron los alumnos. La hoja de respuestas de ejemplo incluye a propósito: una
fila vacía, un ID de alumno repetido, respuestas múltiples («AB», «A,C»), ilegibles («*», «?»),
caracteres inválidos («E», «x»), respuestas vacías y «NR» explícito, minúsculas y espacios,
y una columna extra que no es reactivo ni contexto.
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


def _crear(db, storage, respuestas: str = RESPUESTAS, nombre: str = "respuestas.csv") -> int:
    return crear_instrumento(db, storage, nombre, respuestas.encode("utf-8"), tipo="prueba_estandarizada")


def _limpio(storage, db) -> list[list[str]]:
    fila = db.query(LimpiezaEjecucion).order_by(LimpiezaEjecucion.version.desc()).first()
    return list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("A", ("valida", "")),
        (" b ", ("valida", "")),
        ("", ("NR", "no_respondida")),
        ("NR", ("NR", "no_respondida")),
        ("AB", ("nula", "respuesta_multiple")),
        ("A,C", ("nula", "respuesta_multiple")),
        ("*", ("nula", "ilegible")),
        ("A?", ("nula", "ilegible")),
        ("E", ("nula", "caracter_invalido")),
        ("x", ("nula", "caracter_invalido")),
    ],
)
def test_clasificar_respuestas(valor, esperado):
    from services.motores.pruebas.motor import clasificar

    assert clasificar(valor, {"A", "B", "C", "D"}, {"*", "?", "#"}) == esperado


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
    # Sin clave no hay nada que confirmar: la única tarjeta es la del ID repetido.
    assert {h["tipo"] for h in e["hallazgos"]} == {"id_duplicado"}
    assert "kr20" not in m and "pct_correctas_validas" not in m


def test_confirmar_genera_formato_largo_con_estado_y_motivo_sin_calificar(cliente, db, storage):
    id_crudo = _crear(db, storage)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()
    assert r["estado"] == "confirmada"
    filas = _limpio(storage, db)
    # Sin columnas de respuesta correcta ni acierto; «grupo» (contexto) se conserva al final, «observaciones» no.
    assert filas[0] == ["id_alumno", "pregunta", "respuesta", "estado", "motivo", "grupo"]
    datos: dict[tuple[str, str], list[str]] = {}
    for f in filas[1:]:
        datos.setdefault((f[0], f[1]), f[2:5])  # primera aparición de cada alumno
    assert {f[0]: f[5] for f in filas[1:]} == {"A001": "3A", "A002": "3A", "A003": "3B", "A004": "3B"}
    # 5 registros (la fila vacía se eliminó) × 4 preguntas.
    assert len(filas) - 1 == 20
    assert datos[("A001", "P1")] == ["A", "valida", ""]
    assert datos[("A002", "P1")] == ["b", "valida", ""]
    assert datos[("A002", "P3")] == ["AB", "nula", "respuesta_multiple"]
    assert datos[("A002", "P4")] == ["NR", "NR", "no_respondida"]
    assert datos[("A003", "P1")] == ["*", "nula", "ilegible"]
    assert datos[("A003", "P2")] == ["E", "nula", "caracter_invalido"]
    assert datos[("A003", "P3")] == ["", "NR", "no_respondida"]
    assert datos[("A004", "P2")] == ["?", "nula", "ilegible"]
    # El segundo registro de A002 queda nulo por duplicado (se conservó el primero).
    segundo = [f for f in filas[1:] if f[0] == "A002"][4:]
    assert {f[3] for f in segundo} == {"nula"} and {f[4] for f in segundo} == {"duplicado"}

    cifras = {c["etiqueta"]: c["valor"] for c in r["vistaFinal"]["cifras"]}
    assert cifras == {"Alumnos": 4, "Reactivos": 4, "Respuestas nulas": 10, "No respondidas": 2}
    assert r["vistaFinal"]["columnas"] == ["Alumno", "Reactivo", "Respuesta", "Estado", "Motivo"]
    rep = db.query(LimpiezaEjecucion).one().reporte
    esp = rep["especifico"]["prueba_estandarizada"]
    assert esp["conteos"] == {"valida": 8, "nula": 10, "NR": 2}
    assert esp["motivos"] == {"duplicado": 4, "no_respondida": 2, "respuesta_multiple": 2, "caracter_invalido": 2, "ilegible": 2}
    assert "clave" not in esp and "clave_origen" not in esp


def test_descripcion_de_reactivos_opcion_mas_elegida_y_sin_elegir(cliente, db, storage):
    id_crudo = _crear(db, storage)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    est = db.query(LimpiezaEjecucion).one().reporte["estadistica"]["despues"]
    p1 = next(r for r in est["reactivos"] if r["pregunta"] == "P1")
    # P1: A, b, *, C (la copia anulada de A002 no cuenta: es un duplicado, no un alumno).
    assert p1["opcion_mas_elegida"]["opcion"] == "A" and p1["opcion_mas_elegida"]["n"] == 1
    assert p1["opciones_sin_elegir"] == ["D"]
    assert p1["n_nulas"] == 1 and p1["n_no_respondidas"] == 0 and p1["n"] == 4
    assert {d["opcion"]: d["n"] for d in p1["distribucion"]} == {"A": 1, "B": 1, "C": 1, "D": 0, "nula": 1, "NR": 0}
    assert p1["mucha_no_respuesta"] is True  # 1 de 4 > 20 %
    assert not any(k in p1 for k in ("respuesta_correcta", "dificultad", "discriminacion"))
    assert "fiabilidad" not in est and "puntajes" not in est
    assert est["resumen_reactivos"]["con_opciones_sin_elegir"] >= 1
    assert est["respuestas"]["n_reactivos"] == 4


@pytest.mark.parametrize(("decision", "registros"), [("conservar_todos", 5), ("eliminar_todos", 3)])
def test_decisiones_sobre_ids_duplicados(cliente, db, storage, decision, registros):
    id_crudo = _crear(db, storage)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"id-duplicado:A002": decision}}, headers=ANA)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    filas = _limpio(storage, db)
    assert (len(filas) - 1) // 4 == registros
    assert "duplicado" not in {f[4] for f in filas[1:]}


def test_hoja_de_respuestas_en_xlsx(cliente, db, storage):
    import openpyxl

    libro = openpyxl.Workbook()
    libro.active.append(["matricula", "P1", "P2", "P3"])
    for fila in (["A1", "A", "B", "C"], ["A2", "B", "B", "D"], ["A3", "A", "C", "C"]):
        libro.active.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    id_crudo = crear_instrumento(db, storage, "respuestas.xlsx", buffer.getvalue(), tipo="prueba_estandarizada")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones", e
    assert e["metricasAntes"]["n_preguntas"] == 3


@pytest.mark.parametrize(
    ("respuestas", "mensaje"),
    [
        ("matricula P1 P2\nA001 A B\n", "delimitador"),
        ("matricula;nombre;correo\nA001;Ana;a@x.mx\nA002;Luis;l@x.mx\nA003;Eva;e@x.mx\n", "No se encontraron columnas de reactivos"),
    ],
)
def test_errores_de_estructura_fallan_con_mensaje_claro(cliente, db, storage, respuestas, mensaje):
    id_crudo = _crear(db, storage, respuestas)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "fallida" and mensaje in e["error"], e


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


# ── Tipos de reactivo ──────────────────────────────────────────────────────────

MIXTA = """id_alumno,turno,r_q1,r_q2,vf_q1,corta_q1,escala_q1,sino_q1,calc_q1,score
S01,Matutino,A,B,V,2,5,Sí,12.5,0.95
S02,Vespertino,A,B,V,2,4,Sí,12.0,0.90
S03,Matutino,A,C,V,2,4,No,11.8,0.85
S04,Vespertino,A,B,V,1,3,Sí,12.5,0.80
S05,Matutino,B,B,F,1,2,No,9.0,0.40
S06,Vespertino,C,A,F,0,1,No,8.5,0.30
"""


def test_tipos_de_reactivo_se_detectan_y_se_describen_sin_calificar(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "pru.csv", MIXTA.encode("utf-8"), tipo="prueba_estandarizada")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "esperando_decisiones", e.get("error")
    assert e["hallazgos"] == [] and e["pendientesObligatorias"] == 0
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text

    rep = db.query(LimpiezaEjecucion).one().reporte
    esp = rep["especifico"]["prueba_estandarizada"]
    assert esp["tipos_reactivo"] == {"r_q1": "opcion_multiple", "r_q2": "opcion_multiple", "vf_q1": "verdadero_falso",
                                     "corta_q1": "puntos", "escala_q1": "escala", "sino_q1": "si_no", "calc_q1": "numerica"}
    # El orden de la hoja como lista (JSONB reordena las llaves de los diccionarios).
    assert esp["orden_reactivos"] == ["r_q1", "r_q2", "vf_q1", "corta_q1", "escala_q1", "sino_q1", "calc_q1"]
    assert esp["puntos_max"] == {"corta_q1": 2, "escala_q1": 5}
    assert [c["id"] for c in esp["columnas_contexto"]] == ["turno", "score"]  # el puntaje global es dato del alumno

    datos = {(f[0], f[1]): f for f in _limpio(storage, db)[1:]}
    assert datos[("S04", "corta_q1")][2:4] == ["1", "valida"]
    assert datos[("S05", "sino_q1")][2:4] == ["No", "valida"]
    assert datos[("S01", "calc_q1")][2:4] == ["12.5", "valida"]

    por = {r["pregunta"]: r for r in rep["estadistica"]["despues"]["reactivos"]}
    assert por["r_q1"]["opcion_mas_elegida"] == {"opcion": "A", "n": 4, "pct": 0.6667, "pct_validas": 0.6667}
    assert por["vf_q1"]["opcion_mas_elegida"]["opcion"] == "V" and por["vf_q1"]["opciones_sin_elegir"] == []
    assert por["corta_q1"]["descriptivos"]["media"] == pytest.approx(8 / 6, abs=1e-4)
    assert por["sino_q1"]["opcion_mas_elegida"]["opcion"] == "Sí"  # empate 3–3: gana la primera opción


@pytest.mark.parametrize(
    ("valor", "tipo", "maximo", "esperado"),
    [
        ("V", "verdadero_falso", None, ("valida", "")),
        ("Falso", "verdadero_falso", None, ("valida", "")),
        ("X", "verdadero_falso", None, ("nula", "caracter_invalido")),
        ("2", "puntos", 2, ("valida", "")),
        ("3", "puntos", 2, ("nula", "caracter_invalido")),
        ("4", "escala", 5, ("valida", "")),
        ("0", "escala", 5, ("nula", "caracter_invalido")),
        ("sí", "si_no", None, ("valida", "")),
        ("", "si_no", None, ("NR", "no_respondida")),
        ("12,5", "numerica", None, ("valida", "")),
    ],
)
def test_clasificar_por_tipo_de_reactivo(valor, tipo, maximo, esperado):
    from services.motores.pruebas.motor import clasificar

    assert clasificar(valor, {"A", "B", "C", "D"}, {"*", "?", "#"}, tipo, maximo) == esperado


def test_fila_de_solo_separadores_se_cuenta_como_vacia(cliente, db, storage):
    """24 oct, errores inyectados: «;;;;;;» desaparecía en el lector de CSV sin contarse como fila vacía."""
    respuestas = RESPUESTAS.replace("  ;  ;  ;  ;  ;  ;  \n", ";;;;;;\n")
    id_crudo = _crear(db, storage, respuestas=respuestas)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert {t["regla"]: t["afectados"] for t in e["transformaciones"]}["filas_vacias"] == 1
    assert e["metricasAntes"]["n_filas_vacias"] == 1
