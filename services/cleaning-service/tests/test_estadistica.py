"""Medidas de limpieza estadística: descriptivos, atípicos, fiabilidad (alfa de
Cronbach y KR-20), análisis de reactivos, respuestas en línea recta y encuestados
incompletos. Los valores de referencia se calcularon a mano o coinciden con Excel
(SKEW, KURT, QUARTILE.INC).
"""
from __future__ import annotations

import csv
import io

import pytest

from conftest import ANA, crear_instrumento
from services.motores import estadistica as est

# ── Funciones puras ────────────────────────────────────────────────────────────


def test_descriptivos_como_excel():
    d = est.descriptivos([2, 4, 4, 4, 5, 5, 7, 9])
    assert d["n"] == 8 and d["media"] == 5 and d["mediana"] == 4.5
    assert d["desviacion"] == pytest.approx(2.1381, abs=1e-4)  # muestral (STDEV.S)
    assert (d["q1"], d["q3"], d["iqr"]) == (4, 5.5, 1.5)  # QUARTILE.INC
    assert d["asimetria"] == pytest.approx(0.8185, abs=1e-4)  # SKEW
    assert d["curtosis"] == pytest.approx(0.9406, abs=1e-4)  # KURT
    assert est.descriptivos([]) is None
    assert est.descriptivos([3])["desviacion"] is None


def test_frecuencias_con_orden_de_escala_y_moda():
    f = est.frecuencias(["Sí", "No", "Sí"], orden=["No", "Sí", "Tal vez"])
    assert [(r["valor"], r["n"]) for r in f["tabla"]] == [("No", 1), ("Sí", 2), ("Tal vez", 0)]
    assert f["moda"] == "Sí" and f["tabla"][1]["pct"] == pytest.approx(0.6667, abs=1e-4)
    assert est.frecuencias(["a", "b"])["moda"] == ["a", "b"]  # bimodal


def test_atipicos_por_sigma_y_por_iqr():
    xs = [10, 11, 12, 11, 10, 12, 11, 13, 10, 11, 12, 60]
    assert est.contar_fuera(xs, est.limites_atipicos(xs, "iqr", 1.5)) == 1
    assert est.contar_fuera(xs, est.limites_atipicos(xs, "sigma", 4)) == 0  # ±4σ es más permisivo
    assert est.limites_atipicos([5, 5, 5], "sigma", 4) is None  # sin variación no hay atípicos


def test_alfa_de_cronbach():
    # var(x) = var(y) = 1.667, var(x + y) = 5.333 → α = 2 · (1 − 3.333 / 5.333) = 0.75
    r = est.cronbach([[1, 2], [2, 1], [3, 4], [4, 3]], ["x", "y"])
    assert r["alfa"] == pytest.approx(0.75) and r["interpretacion"] == "aceptable"
    # Ítems idénticos: consistencia perfecta. Los casos incompletos se excluyen.
    r = est.cronbach([[1, 1, 1], [2, 2, 2], [3, 3, 3], [None, 1, 2]], ["a", "b", "c"])
    assert r["alfa"] == pytest.approx(1.0) and r["n_casos"] == 3 and r["n_excluidos"] == 1
    assert [i["alfa_si_se_elimina"] for i in r["por_item"]] == [1.0, 1.0, 1.0]
    assert est.cronbach([[1, 2]], ["x", "y"]) is None  # muy pocos casos


MATRIZ = [[1, 1, 1], [1, 1, 0], [1, 0, 0], [0, 0, 0]]


def test_kr20_y_analisis_de_reactivos():
    # p = .75, .5, .25 → Σpq = .625; varianza de totales = 1.25 → KR-20 = 1.5 · (1 − .5) = .75
    assert est.kr20(MATRIZ) == pytest.approx(0.75)
    reactivos = est.analisis_reactivos(MATRIZ)
    assert [r["dificultad"] for r in reactivos] == [0.75, 0.5, 0.25]
    assert [r["nivel_dificultad"] for r in reactivos] == ["fácil", "media", "difícil"]
    assert all(r["discriminacion"] == 1 and r["nivel_discriminacion"] == "excelente" for r in reactivos)


# ── Encuestas ──────────────────────────────────────────────────────────────────

ESCALA = ["Totalmente en desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo", "De acuerdo", "Totalmente de acuerdo"]
ASPECTOS = ["Profesores", "Instalaciones", "Materiales", "Horarios"]
CODIGOS = [
    (4, 5, 4, 3), (2, 3, 2, 2), (5, 5, 4, 5), (3, 4, 3, 3),
    (4, 4, 4, 4),  # línea recta
    (1, 2, 2, 1), (4, 3, 5, 4), (2, 2, 3, 2), (5, 4, 5, 5), (3, 3, 2, 4), (4, 5, 5, 4),
    None,  # solo contestó la carrera: encuestado incompleto
    (3, 4, 4, 3),
]
INGRESOS = [8000, 7500, 8400, 8200, 7800, 8100, 7900, 8300, 7700, 8050, 90000, None, 8150]
CARRERAS = ["Pedagogía", "Derecho", "Pedagogía", "Psicología", "Derecho", "Pedagogía", "Psicología",
            "Derecho", "Pedagogía", "Psicología", "Derecho", "Derecho", "Pedagogía"]


def _encuesta() -> bytes:
    encabezados = [f"Satisfacción con la carrera [{a}]" for a in ASPECTOS] + ["Ingreso mensual", "Carrera"]
    filas = []
    for cods, ingreso, carrera in zip(CODIGOS, INGRESOS, CARRERAS):
        likert = [ESCALA[c - 1] for c in cods] if cods else [""] * 4
        filas.append(likert + ["" if ingreso is None else str(ingreso), carrera])
    buffer = io.StringIO()
    csv.writer(buffer).writerows([encabezados, *filas])
    return buffer.getvalue().encode("utf-8")


@pytest.fixture()
def encuesta(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "encuesta.csv", _encuesta())
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert r.status_code == 200, r.text
    return id_crudo, r.json()


def test_hallazgos_de_linea_recta_y_encuestados_incompletos(encuesta):
    _, e = encuesta
    hallazgos = {h["id"]: h for h in e["hallazgos"]}
    lr = hallazgos["linea-recta"]
    assert lr["detalle"]["filas"] == [5] and lr["sugerida"] == "conservar"
    assert lr["detalle"]["bloques"] == ["Satisfacción con la carrera"]
    inc = hallazgos["incompletos"]
    assert inc["detalle"]["filas"] == [12] and inc["sugerida"] == "eliminar"
    assert e["metricasAntes"]["n_linea_recta"] == 1 and e["metricasAntes"]["n_incompletos"] == 1


def test_vista_final_con_descriptivos_fiabilidad_y_comparacion(cliente, encuesta):
    id_crudo, _ = encuesta
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"linea-recta": "eliminar"}}, headers=ANA)
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    vista = r.json()["vistaFinal"]
    cifras = {c["etiqueta"]: c["valor"] for c in vista["cifras"]}
    assert cifras["Respondentes"] == 11 and cifras["Encuestados removidos"] == 2

    columnas = {c["etiqueta"]: c for c in vista["estadistica"]["columnas"]}
    prof = columnas["Satisfacción con la carrera [Profesores]"]
    assert prof["tipo"] == "cuadricula" and prof["n"] == 11
    assert [f["valor"] for f in prof["frecuencias"]["tabla"]] == ESCALA
    assert prof["numerico"]["media"] == pytest.approx(36 / 11, abs=1e-4)  # sin la fila 5 ni la 12
    ingreso = columnas["Ingreso mensual"]
    assert ingreso["tipo"] == "numerica" and ingreso["atipicos"]["iqr"] == 1 and ingreso["atipicos"]["sigma"] == 0
    assert ingreso["numerico"]["asimetria"] > 3  # el ingreso de 90 000 sesga la distribución
    assert columnas["Carrera"]["frecuencias"]["moda"] == "Pedagogía"  # se quitaron dos encuestados de Derecho

    fiab = vista["estadistica"]["fiabilidad"]
    assert len(fiab) == 1 and fiab[0]["bloque"] == "Satisfacción con la carrera"
    assert fiab[0]["items"] == ASPECTOS and fiab[0]["n_casos"] == 11
    assert 0.8 <= fiab[0]["alfa"] <= 1 and fiab[0]["interpretacion"] in ("buena", "excelente")
    assert len(fiab[0]["por_item"]) == 4

    comparacion = {c["metrica"]: c for c in vista["comparacion"]}
    assert (comparacion["Respuestas en línea recta"]["antes"], comparacion["Respuestas en línea recta"]["despues"]) == (1, 0)
    assert (comparacion["Encuestados incompletos"]["antes"], comparacion["Encuestados incompletos"]["despues"]) == (1, 0)
    assert comparacion["Alfa de Cronbach · Satisfacción con la carrera"]["formato"] == "dec"
    assert vista["estadistica_antes"]["columnas"][0]["n"] == 12  # antes: con la línea recta


def test_item_invertido_se_recodifica_para_el_alfa(cliente, db, storage):
    # El 4.º ítem está redactado al revés: sin recodificar, el alfa sería muy bajo.
    encabezados = ["Me gusta la carrera [a]", "Me gusta la carrera [b]", "Me gusta la carrera [c]", "Me gusta la carrera [nunca quiero ir]"]
    filas = [[ESCALA[c - 1] for c in (x, x, x, 6 - x)] for x in (1, 2, 3, 4, 5, 2, 4)]
    filas = [f[:2] + [ESCALA[min(4, ESCALA.index(f[2]) + (i % 2))]] + f[3:] for i, f in enumerate(filas)]  # algo de ruido
    buffer = io.StringIO()
    csv.writer(buffer).writerows([encabezados, *filas])
    id_crudo = crear_instrumento(db, storage, "inv.csv", buffer.getvalue().encode("utf-8"))
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    hid = next(h["id"] for h in e["hallazgos"] if h["tipo"] == "item_invertido")
    vista = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["vistaFinal"]
    fiab = vista["estadistica"]["fiabilidad"][0]
    assert fiab["invertidos"] == ["nunca quiero ir"] and fiab["alfa"] > 0.9
    assert hid.startswith("invertido:")
    antes = vista["estadistica_antes"]["fiabilidad"][0]
    assert antes["alfa"] < fiab["alfa"]  # antes de confirmar el ítem invertido no se recodificaba


# ── Pruebas estandarizadas ─────────────────────────────────────────────────────


def test_prueba_analisis_de_reactivos_y_kr20(cliente, db, storage):
    respuestas = "matricula;P1;P2;P3\nS1;A;B;C\nS2;A;B;D\nS3;A;C;D\nS4;B;C;D\n"
    id_crudo = crear_instrumento(
        db, storage, "respuestas.csv", respuestas.encode("utf-8"), tipo="prueba_estandarizada",
        clave=("clave.csv", b"pregunta,respuesta\nP1,A\nP2,B\nP3,C\n"),
    )
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    vista = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["vistaFinal"]
    e = vista["estadistica"]
    assert e["fiabilidad"]["kr20"] == pytest.approx(0.75) and e["fiabilidad"]["n_alumnos"] == 4
    p1 = e["reactivos"][0]
    assert p1["dificultad"] == 0.75 and p1["nivel_dificultad"] == "fácil" and p1["discriminacion"] == 1
    assert p1["distractores_sin_elegir"] == ["C", "D"]
    dist = {d["opcion"]: d["n"] for d in p1["distribucion"]}
    assert dist["A"] == 3 and dist["B"] == 1 and next(d for d in p1["distribucion"] if d["opcion"] == "A")["correcta"]
    assert e["puntajes"]["media"] == 1.5 and e["puntajes"]["maximo_posible"] == 3
    assert e["resumen_reactivos"] == {"faciles": 1, "medios": 1, "dificiles": 1, "discriminacion_pobre": 0}
    assert {c["metrica"] for c in vista["comparacion"]} >= {"Alumnos", "Fiabilidad KR-20", "Respuestas nulas"}


# ── Entrevistas ────────────────────────────────────────────────────────────────


def test_entrevista_participacion_por_hablante(cliente, db, storage):
    texto = (
        "Entrevistador: ¿Qué te motivó a estudiar?\n"
        "Ana: Siempre me gustó enseñar a los niños.\n"
        "Entrevistador: ¿Y la experiencia en línea?\n"
        "Ana: Fue difícil al principio pero aprendí mucho.\n"
    )
    id_crudo = crear_instrumento(db, storage, "entrevista.txt", texto.encode("utf-8"), tipo="entrevista")
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    pendientes = {h["id"]: h["opciones"][0] for h in e["hallazgos"] if h["obligatoria"]}
    if pendientes:
        cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": pendientes}, headers=ANA)
    vista = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["vistaFinal"]
    hablantes = {h["nombre"]: h for h in vista["estadistica"]["hablantes"]}
    assert hablantes["Ana"]["palabras"] == 14 and hablantes["Entrevistador"]["palabras"] == 10
    assert hablantes["Ana"]["pct_palabras"] == pytest.approx(14 / 24, abs=1e-4)
    assert hablantes["Entrevistador"]["pct_preguntas"] == 1.0
    assert vista["estadistica"]["palabras_por_turno"]["media"] == 6


# ── Bloques numerados y resumen en la vista final ──────────────────────────────


def test_bloques_con_sufijo_numerado_tienen_alfa_propio_y_resumen(cliente, db, storage):
    # Dos dimensiones con encabezados «Prefijo_itemN» (sin corchetes) y las horas de trabajo.
    import random

    azar = random.Random(3)
    encabezados = [f"Aportacion_item{i}" for i in range(1, 4)] + [f"Dedicacion_item{i}" for i in range(1, 4)] + ["horas_trabajo_semana"]
    filas = []
    for _ in range(30):
        a, d = azar.randint(1, 5), azar.randint(1, 5)
        cerca = lambda x: str(max(1, min(5, x + azar.choice((-1, 0, 0, 1)))))  # noqa: E731
        filas.append([cerca(a) for _ in range(3)] + [cerca(d) for _ in range(3)] + [str(azar.choice((5, 10, 14, 20, 28, 40)))])
    buffer = io.StringIO()
    csv.writer(buffer).writerows([encabezados, *filas])
    id_crudo = crear_instrumento(db, storage, "dimensiones.csv", buffer.getvalue().encode("utf-8"))
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    vista = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["vistaFinal"]

    fiab = {b["bloque"]: b for b in vista["estadistica"]["fiabilidad"]}
    assert set(fiab) == {"Aportacion", "Dedicacion", "Todas las escalas Likert"}
    assert fiab["Aportacion"]["items"] == ["ítem 1", "ítem 2", "ítem 3"]
    assert fiab["Aportacion"]["alfa"] > 0.7
    horas = next(c for c in vista["estadistica"]["columnas"] if c["etiqueta"] == "horas_trabajo_semana")
    assert horas["tipo"] == "numerica"

    resumen = vista["resumen"]
    assert resumen and all(f["nivel"] in ("bien", "info", "atencion", "alerta") for f in resumen)
    assert any("bloques de escalas son consistentes" in f["texto"] for f in resumen)
    assert any("«horas_trabajo_semana»: la mitad" in f["texto"] for f in resumen)
