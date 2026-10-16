"""Pruebas del motor de encuestas con archivos pequeños y SUCIOS.

La encuesta de ejemplo incluye a propósito:
  - columnas de plataforma (Marca temporal, ID) y una columna completamente vacía,
  - representaciones de vacío («NA», «-», «sin respuesta») y espacios de más,
  - una fila vacía y una fila duplicada (solo cambia la marca temporal),
  - Likert en texto con «No sé», Likert numérica con un 9 fuera de escala,
  - un código corto (P1_4_1), una columna muy incompleta, un ítem en negativo,
  - una escala que parece Likert pero no está en el diccionario.
"""
from __future__ import annotations

import csv
import io

import pytest

from shared.models.limpieza_ejecucion import LimpiezaEjecucion

from conftest import ANA, crear_instrumento

ENCABEZADOS = [
    "Marca temporal",
    "ID",
    "Edad",
    "¿Qué tan de acuerdo estás con que los profesores explican con claridad?",
    "Califica del 1 al 5 tu satisfacción general con la carrera",
    "P1_4_1",
    "Comentarios adicionales sobre tu experiencia en la universidad",
    "No me siento motivado para asistir a clases presenciales",
    "¿Cuánto te interesa el servicio social en tu formación?",
    "Columna vacía",
]
FILAS = [
    ["2024-05-01 10:00", "1", "19", "De acuerdo", "4", "3", "Todo bien", "En desacuerdo", "Bastante", ""],
    ["2024-05-01 10:05", "2", "20", "Totalmente de acuerdo", "5", "2", "NA", "De acuerdo", "Mucho", ""],
    ["2024-05-01 10:07", "3", "  21 ", "No sé", "9", "3", "-", "Totalmente en desacuerdo", "Poco", ""],
    ["2024-05-01 10:09", "4", "22", "En desacuerdo", "3", "1", "sin respuesta", "De acuerdo", "Muy poco", ""],
    ["2024-05-01 10:11", "5", "19", "De acuerdo", "4", "2", "", "Ni de acuerdo ni en desacuerdo", "Bastante", ""],
    ["2024-05-01 10:13", "6", "23", "Totalmente en desacuerdo", "2", "3", "", "De acuerdo", "Poco", ""],
    ["2024-05-01 10:15", "7", "20", "De acuerdo", "4", "2", "Me  gusta   mucho", "En desacuerdo", "Mucho", ""],
    ["-", "NA", "", "", "", "", "", "", "", ""],  # solo «vacíos»: la elimina la limpieza
    ["2024-05-01 10:20", "8", "21", "Ni de acuerdo ni en desacuerdo", "3", "1", "", "De acuerdo", "Bastante", ""],
    ["2024-05-01 10:25", "9", "24", "De acuerdo", "4", "3", "Todo bien", "En desacuerdo", "Bastante", ""],
]
# Duplicado de la fila 1 (otra marca temporal y otro ID: las respuestas son idénticas).
FILAS.append(["2024-05-01 11:00", "10"] + FILAS[0][2:])


def _csv(encabezados: list[str], filas: list[list[str]], sep: str = ",") -> bytes:
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=sep).writerows([encabezados, *filas])
    return buffer.getvalue().encode("utf-8")


def _limpio(storage, db) -> list[list[str]]:
    fila = db.query(LimpiezaEjecucion).order_by(LimpiezaEjecucion.version.desc()).first()
    return list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))


@pytest.fixture()
def ejecucion(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "encuesta.csv", _csv(ENCABEZADOS, FILAS))
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert r.status_code == 200, r.text
    return id_crudo, r.json()


def _hallazgo(ejec: dict, prefijo: str) -> dict:
    """Hallazgo por prefijo de id (los ids de columna se recortan a 40 caracteres)."""
    return next(h for h in ejec["hallazgos"] if h["id"].startswith(prefijo))


def _hid(ejec: dict, prefijo: str) -> str:
    return _hallazgo(ejec, prefijo)["id"]


def _col(encabezados: list[str], prefijo: str) -> int:
    return next(i for i, h in enumerate(encabezados) if h.startswith(prefijo))


def test_fase_automatica_transformaciones_y_metricas(ejecucion):
    _, e = ejecucion
    assert e["estado"] == "esperando_decisiones"
    reglas = {t["regla"]: t["afectados"] for t in e["transformaciones"]}
    assert reglas["vacios_unificados"] == 5  # NA, -, sin respuesta + la fila de «vacíos»
    assert reglas["filas_vacias"] == 1
    assert reglas["columnas_vacias"] == 1
    assert reglas["espacios_en_valores"] >= 1  # «Me  gusta   mucho»
    assert reglas["roles_automaticos"] == 5  # encabezados de más de 25 caracteres

    m = e["metricasAntes"]
    assert m["n_respondentes"] == 11 and m["n_columnas"] == 10  # archivo tal como llegó
    assert 0 < m["pct_nulos"] < 1 and m["pct_completitud"] == pytest.approx(1 - m["pct_nulos"])
    assert m["n_imposibles"] >= 1  # el 9 de la escala 1–5
    assert m["n_duplicados"] == 1  # misma definición que el hallazgo (sin marca temporal ni ID)
    assert m["cols_mas_nulos"][0]["columna"] == "Columna vacía"


def test_hallazgos_de_la_fase_asistida(ejecucion):
    _, e = ejecucion
    ids = {h["id"] for h in e["hallazgos"]}
    assert {"col-ajena:marca_temporal", "col-ajena:id"} <= ids
    assert _hallazgo(e, "col-ajena:id")["sugerida"] == "eliminar"

    codigo = _hallazgo(e, "rol:p1_4_1")
    assert codigo["obligatoria"] is True and codigo["sugerida"] is None
    assert _hallazgo(e, "rol:edad")["sugerida"] == "contexto"
    # Obligatorias: el código corto y la escala desconocida (sin palabras del diccionario).
    assert e["pendientesObligatorias"] == 2

    assert _hallazgo(e, "incompleta:comentarios_adicionales")["sugerida"] == "conservar"

    rango = _hallazgo(e, "rango:califica_del_1_al_5")
    assert rango["detalle"]["valores"] == ["9"] and rango["sugerida"] == "anular"

    dup = _hallazgo(e, "duplicados")
    assert dup["detalle"]["total"] == 1

    assert _hallazgo(e, "invertido:no_me_siento_motivado")["sugerida"] == "invertido"
    dudosa = _hallazgo(e, "likert-orden:cuanto_te_interesa")
    # Orden propuesto por intensidad (el investigador lo confirma).
    assert dudosa["detalle"]["orden_propuesto"] == ["Muy poco", "Poco", "Bastante", "Mucho"]


def test_confirmar_aplica_decisiones_y_genera_csv(cliente, db, storage, ejecucion):
    id_crudo, e = ejecucion
    dudosa = _hid(e, "likert-orden:cuanto_te_interesa")
    cambios = {"rol:p1_4_1": "eliminar", dudosa: "no_es_likert"}
    r = cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": cambios}, headers=ANA)
    assert r.json()["pendientesObligatorias"] == 0
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["estado"] == "confirmada"

    filas = _limpio(storage, db)
    encabezados = filas[0]
    # Sin columnas de plataforma, sin la vacía y sin el código eliminado; ids seguros.
    assert "marca_temporal" not in encabezados and "id" not in encabezados and "p1_4_1" not in encabezados
    assert encabezados[0] == "edad"
    assert all(h == h.lower() and " " not in h for h in encabezados)
    # 11 filas − 1 vacía − 1 duplicada.
    assert len(filas) - 1 == 9

    acuerdo = _col(encabezados, "que_tan_de_acuerdo")
    valores = [f[acuerdo] for f in filas[1:]]
    assert valores[0] == "4" and valores[1] == "5"  # De acuerdo → 4, Totalmente de acuerdo → 5
    assert valores[2] == "No sé"  # por defecto se conserva marcada (distinta de una celda vacía)
    satisf = _col(encabezados, "califica_del_1_al_5")
    assert "9" not in [f[satisf] for f in filas[1:]]  # fuera de rango anulado
    assert [f[encabezados.index("edad")] for f in filas[1:]][2] == "21"  # espacios quitados

    # Vista final para el investigador.
    cifras = {c["etiqueta"]: c["valor"] for c in e["vistaFinal"]["cifras"]}
    assert cifras["Respondentes"] == 9 and cifras["Encuestados removidos"] == 1
    assert cifras["Columnas eliminadas"] == 4  # marca temporal, ID, P1_4_1 y la vacía
    assert e["vistaFinal"]["columnas"][0] == "Edad"  # la vista usa el texto original

    # Reporte: tipos, roles, libro de códigos Likert y métricas después.
    rep = db.query(LimpiezaEjecucion).one().reporte
    cols = {c["id"]: c for c in rep["especifico"]["encuesta"]["columnas"]}

    def col(prefijo: str) -> dict:
        return next(c for cid, c in cols.items() if cid.startswith(prefijo))

    lik = col("que_tan_de_acuerdo")
    assert lik["tipo_canonico"] == "likert" and lik["rol"] == "pregunta"
    assert lik["likert"]["escala"] == "acuerdo" and lik["likert"]["puntos"] == 5 and lik["likert"]["neutral"] == 3
    assert lik["likert"]["codigos"]["De acuerdo"] == 4 and lik["likert"]["excluidos"] == ["No sé"]
    assert col("no_me_siento_motivado")["likert"]["invertido"] is True
    assert cols["edad"]["rol"] == "contexto"
    assert cols["p1_4_1"]["estado"] == "eliminada"
    assert col("cuanto_te_interesa")["tipo_canonico"] == "categorica"
    assert rep["metricas"]["despues"]["n_duplicados"] == 0 and rep["metricas"]["despues"]["n_imposibles"] == 0
    assert rep["decisiones"]["col-ajena:id"]["origen"] == "sugerida"


def test_escala_no_reconocida_con_orden_confirmado_se_convierte(cliente, db, storage, ejecucion):
    id_crudo, e = ejecucion
    dudosa = _hid(e, "likert-orden:cuanto_te_interesa")
    cliente.patch(
        f"/limpieza/{id_crudo}/ejecuciones/1/decisiones",
        json={"decisiones": {"rol:p1_4_1": "pregunta", dudosa: "usar_orden_propuesto"}},
        headers=ANA,
    )
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    rep = db.query(LimpiezaEjecucion).one().reporte
    col = next(c for c in rep["especifico"]["encuesta"]["columnas"] if c["id"].startswith("cuanto_te_interesa"))
    assert col["tipo_canonico"] == "likert" and col["likert"]["escala"] == "propuesta"
    filas = _limpio(storage, db)
    idx = _col(filas[0], "cuanto_te_interesa")
    assert all(f[idx].isdigit() for f in filas[1:])


def test_conservar_duplicados_y_columnas_ajenas(cliente, db, storage, ejecucion):
    id_crudo, e = ejecucion
    dudosa = _hid(e, "likert-orden:cuanto_te_interesa")
    cambios = {"rol:p1_4_1": "pregunta", dudosa: "no_es_likert", "duplicados": "conservar", "col-ajena:id": "conservar"}
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": cambios}, headers=ANA)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    filas = _limpio(storage, db)
    assert "id" in filas[0] and len(filas) - 1 == 10
    rep = db.query(LimpiezaEjecucion).one().reporte
    assert rep["metricas"]["despues"]["n_duplicados"] == 1
    assert next(c for c in rep["especifico"]["encuesta"]["columnas"] if c["id"] == "id")["rol"] == "contexto"


def test_xlsx_y_punto_y_coma(cliente, db, storage):
    import openpyxl

    libro = openpyxl.Workbook()
    for fila in [ENCABEZADOS, *FILAS]:
        libro.active.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    id_x = crear_instrumento(db, storage, "encuesta.xlsx", buffer.getvalue())
    id_c = crear_instrumento(db, storage, "encuesta_pc.csv", _csv(ENCABEZADOS, FILAS, sep=";"))
    for id_crudo in (id_x, id_c):
        e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
        assert e["estado"] == "esperando_decisiones", e
        assert any(h["id"] == "duplicados" for h in e["hallazgos"])


@pytest.mark.parametrize(
    ("contenido", "mensaje"),
    [
        (b"a,b,c\n", "no tiene respuestas"),
        (b"a,b\nNA,-\n-,\n", "no tiene datos"),
    ],
)
def test_archivos_invalidos_fallan_con_mensaje_claro(cliente, db, storage, contenido, mensaje):
    id_crudo = crear_instrumento(db, storage, "malo.csv", contenido)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "fallida" and mensaje in e["error"]


# ── Tipos canónicos ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("etiqueta", "valores", "tipo"),
    [
        ("Satisfacción [Biblioteca]", ["De acuerdo", "En desacuerdo", "De acuerdo", "Totalmente de acuerdo"], "cuadricula"),
        ("Ordena por prioridad", ["A, B, C", "B, A, C", "C, B, A"], "ranking"),
        ("Servicios que usas", ["Biblioteca, Cafetería", "Cafetería", "Biblioteca, Gimnasio", "Gimnasio, Cafetería"], "opcion_multiple_varias"),
        ("Frecuencia", ["Nunca", "A veces", "Siempre", "Casi siempre"], "likert"),
        ("Satisfacción", ["1", "2", "3", "4", "5", "3"], "likert"),
        ("¿Trabajas?", ["Sí", "No", "Sí", "Sí"], "binaria"),
        ("Horas de estudio (0-10)", ["0", "8", "10", "6", "9", "2"], "escala_lineal"),
        ("Promedio", ["8.5", "9.1", "7.3", "6.8", "9.9"], "calificacion"),
        ("Puntaje", ["55", "78", "92", "61", "88"], "calificacion"),
        ("Ingreso mensual", ["12000", "8500", "25000", "4000", "15000"], "numerica"),
        # Cantidades: aunque caigan en 0–100 o 0–10 no son calificaciones ni escalas.
        ("horas_trabajo_semana", ["0", "48", "14", "7", "28", "20"], "numerica"),
        ("Edad", ["18", "22", "25", "19", "30"], "numerica"),
        ("¿Cuántos hijos tienes?", ["0", "1", "2", "0", "3"], "numerica"),
        ("Carrera", ["Derecho", "Medicina", "Arquitectura", "Derecho", "Medicina"], "categorica"),
        ("Opinión", ["Me parece que la universidad necesita mejorar mucho la infraestructura y los laboratorios"] * 3, "texto_largo"),
        ("Nombre del grupo", ["Grupo A1", "Grupo B2", "Grupo C3", "Grupo D4", "Grupo E5", "Grupo F6", "Grupo G7", "Grupo H8", "Grupo I9", "Grupo J10", "Grupo K11", "Grupo L12", "Grupo M13", "Grupo N14", "Grupo O15", "Grupo P16"], "texto_corto"),
    ],
)
def test_tipos_canonicos(etiqueta, valores, tipo):
    from services import configuracion
    from services.motores.encuestas.tipos import inferir

    assert inferir(etiqueta, valores, configuracion.reglas()["encuestas"]).tipo == tipo


def test_numerica_fuera_de_4_sigma():
    from services import configuracion
    from services.motores.encuestas.tipos import inferir

    valores = [str(v) for v in [100, 102, 98, 101, 99, 100, 103, 97, 100, 101, 99, 100, 102, 98, 101, 99, 100, 5000]]
    info = inferir("Ingreso", valores, configuracion.reglas()["encuestas"])
    assert info.tipo == "numerica" and info.fuera == {17}


def test_escala_numerica_1_a_5_con_pocos_cincos_no_es_1_a_4():
    from services import configuracion
    from services.motores.encuestas.tipos import inferir

    valores = ["1", "2", "3", "4", "3", "2", "4", "3"] * 10 + ["5", "5"]
    info = inferir("Dedicacion_item2", valores, configuracion.reglas()["encuestas"])
    assert info.tipo == "likert" and info.rango == (1.0, 5.0) and not info.fuera



def test_no_se_y_no_aplica_las_decide_el_investigador(cliente, db, storage, ejecucion):
    id_crudo, e = ejecucion
    h = next(h for h in e["hallazgos"] if h["id"] == "no-respuestas")
    assert h["sugerida"] == "conservar_marcadas" and h["opciones"] == ["conservar_marcadas", "vaciar"]
    assert "No sé" in h["detalle"]["ejemplos"] and h["detalle"]["total"] >= 1
    dudosa = _hid(e, "likert-orden:cuanto_te_interesa")
    cambios = {"rol:p1_4_1": "eliminar", dudosa: "no_es_likert", "no-respuestas": "vaciar"}
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": cambios}, headers=ANA)
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    filas = _limpio(storage, db)
    acuerdo = _col(filas[0], "que_tan_de_acuerdo")
    assert filas[3][acuerdo] == ""  # vaciada por decisión del investigador
    rep = db.query(LimpiezaEjecucion).one().reporte
    assert rep["especifico"]["encuesta"]["no_respuestas"] == "vacias"
    assert any(t["regla"] == "no_respuestas_vaciadas" for t in rep["transformaciones"])
