"""Limpieza visible (28 oct, encuesta de 2000 respondentes): todo lo que la limpieza cambia o pregunta se muestra
con su ubicación exacta; «Nunca.» no es un valor fuera de la escala; «Ninguno» junto con otras opciones se señala."""
from __future__ import annotations

import csv
import io

from shared.models.limpieza_ejecucion import LimpiezaEjecucion

from conftest import ANA, crear_instrumento

FRECUENCIA = ["Nunca", "Rara vez", "Algunas veces", "Frecuentemente", "Siempre"]


def _encuesta() -> bytes:
    filas = []
    for i in range(30):
        modalidad = ["Presencial", "En linea", "Mixta"][i % 3]
        frecuencia = FRECUENCIA[i % 5]
        cooperacion = ["Movilidad;Doble titulacion", "Ninguno", "Movilidad"][i % 3]
        filas.append([modalidad, frecuencia, cooperacion])
    # Suciedad conocida (filas 1 a 6 desde 1, sin contar el encabezado).
    filas[0][0] = "PRESENCIAL"
    filas[1][0] = "  En linea "        # espacios de borde
    filas[2][0] = "Mixta."
    filas[3][1] = "Frecuentemente."   # antes: fuera de rango
    filas[4][1] = "SIEMPRE"
    filas[5][2] = "Ninguno;Movilidad"  # contradictoria
    buffer = io.StringIO()
    csv.writer(buffer).writerows([["¿En qué modalidad cursas tu programa?", "¿Con qué frecuencia te ha tocado un cambio de profesor?",
                                   "¿En qué programas de cooperación has participado?"], *filas])
    return buffer.getvalue().encode("utf-8")


def _automatica(cliente, db, storage) -> tuple[int, dict]:  # noqa: ANN001
    id_crudo = crear_instrumento(db, storage, "encuesta.csv", _encuesta())
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert r.status_code == 200, r.text
    return id_crudo, r.json()


def test_punto_final_no_es_fuera_de_rango(cliente, db, storage):
    _, e = _automatica(cliente, db, storage)
    assert not [h for h in e["hallazgos"] if h["tipo"] == "fuera_de_rango"]


def test_espacios_de_borde_y_escritura_homologada_se_reportan_con_su_ubicacion(cliente, db, storage):
    _, e = _automatica(cliente, db, storage)
    t = {x["regla"]: x for x in e["transformaciones"]}
    assert {"fila": 2, "columna": "¿En qué modalidad cursas tu programa?", "antes": "  En linea ", "despues": "En linea"} in t["espacios_en_valores"]["casos"]
    casos = {(c["fila"], c["antes"], c["despues"]) for c in t["escritura_homologada"]["casos"]}
    assert {(1, "PRESENCIAL", "Presencial"), (3, "Mixta.", "Mixta"), (4, "Frecuentemente.", "Frecuentemente"), (5, "SIEMPRE", "Siempre")} <= casos
    assert t["escritura_homologada"]["afectados"] == len(t["escritura_homologada"]["casos"])
    assert t["escritura_homologada"]["columnas"]["¿En qué modalidad cursas tu programa?"] == 2


def test_csv_limpio_queda_con_la_escritura_homologada(cliente, db, storage):
    id_crudo, _ = _automatica(cliente, db, storage)
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 200
    fila = db.query(LimpiezaEjecucion).one()
    filas = list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))
    modalidades = {f[0] for f in filas[1:]}
    assert modalidades == {"Presencial", "En linea", "Mixta"}


def test_seleccion_contradictoria_con_su_ubicacion_y_decisiones(cliente, db, storage):
    id_crudo, e = _automatica(cliente, db, storage)
    h = next(h for h in e["hallazgos"] if h["tipo"] == "seleccion_contradictoria")
    assert h["detalle"]["ubicacion"] == [{"fila": 6, "columna": "¿En qué programas de cooperación has participado?", "valor": "Ninguno;Movilidad"}]
    assert h["sugerida"] == "conservar" and h["opciones"] == ["conservar", "quitar_ninguno", "vaciar"]
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"seleccion-contradictoria": "quitar_ninguno"}}, headers=ANA)
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 200
    fila = db.query(LimpiezaEjecucion).one()
    filas = list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))
    assert filas[6][2] == "Movilidad"


def test_hallazgos_por_fila_traen_las_respuestas_de_cada_fila(cliente, db, storage):
    datos = "P1,P2,P3,P4\n" + "\n".join(f"{a},{b},{c},{d}" for a, b, c, d in
                                         [(1, 2, 3, 4), (1, 2, 3, 4), (5, 4, 2, 1), (3, 3, 3, 3)] * 3)
    id_crudo = crear_instrumento(db, storage, "dup.csv", datos.encode("utf-8"))
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    dup = next(h for h in e["hallazgos"] if h["tipo"] == "duplicados")
    assert dup["detalle"]["ubicacion"][0]["fila"] == dup["detalle"]["filas"][0]
    assert set(dup["detalle"]["ubicacion"][0]["valores"]) <= {"P1", "P2", "P3", "P4"}


def test_opcion_unica_con_coma_no_es_seleccion_multiple():
    """«Sí, y no lo aprobé» es UNA opción: antes se partía en «Sí» y «y no lo aprobé» (28 oct)."""
    from services.motores.encuestas.tipos import _separados

    valores = (["Sí, y lo aprobé"] * 30 + ["Sí, y no lo aprobé"] * 20 + ["No, pero planeo hacerlo"] * 40
               + ["No, y no lo planeo"] * 25)
    assert not _separados(valores, [",", ";"])


def test_seleccion_multiple_poco_usada_se_reconoce():
    """Solo el 10 % eligió más de una opción, pero esas opciones también aparecen solas."""
    from services.motores.encuestas.tipos import _separados

    valores = ["Carga mínima"] * 40 + ["Carga media"] * 45 + ["Carga mínima;Carga media"] * 10
    assert _separados(valores, [",", ";"])


def _escala_con_texto() -> bytes:
    """Escala 1–5 con «Totalmente de acuerdo» (fila 2), «Totalmente en desacuerdo» (fila 4) y un «9» (fila 6)."""
    valores = [str(1 + i % 5) for i in range(60)]
    valores[1] = "Totalmente de acuerdo"
    valores[3] = "Totalmente en desacuerdo"
    valores[5] = "9"
    return ("Los laboratorios de la institución son adecuados\n" + "\n".join(valores) + "\n").encode("utf-8")


def test_texto_en_una_escala_numerica_tiene_tarjeta_por_valor_con_motivo_y_cambio(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "escala.csv", _escala_con_texto())
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    fuera = {h["detalle"]["valores"][0]: h for h in e["hallazgos"] if h["tipo"] == "fuera_de_rango"}
    assert set(fuera) == {"Totalmente de acuerdo", "Totalmente en desacuerdo", "9"}

    acuerdo = fuera["Totalmente de acuerdo"]
    assert acuerdo["sugerida"] == "cambiar:5"
    assert acuerdo["opciones"] == ["anular", "conservar", "cambiar:1", "cambiar:2", "cambiar:3", "cambiar:4", "cambiar:5"]
    assert "escrito con palabras" in acuerdo["descripcion"] and "números del 1 al 5" in acuerdo["descripcion"]
    assert acuerdo["detalle"]["ubicacion"] == [{"fila": 2, "columna": "Los laboratorios de la institución son adecuados",
                                                "valor": "Totalmente de acuerdo"}]
    assert fuera["Totalmente en desacuerdo"]["sugerida"] == "cambiar:1"
    assert fuera["9"]["sugerida"] == "anular" and "mayor que 5" in fuera["9"]["descripcion"]

    # El investigador conserva el «9» y cambia «Totalmente en desacuerdo» a 2 (en lugar del 1 sugerido).
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", headers=ANA, json={"decisiones": {
        fuera["9"]["id"]: "conservar", fuera["Totalmente en desacuerdo"]["id"]: "cambiar:2"}})
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    fila = db.query(LimpiezaEjecucion).one()
    filas = list(csv.reader(io.StringIO(storage.archivos[fila.ruta_csv_limpio].decode("utf-8-sig")), delimiter=";"))
    assert [filas[2][0], filas[4][0], filas[6][0]] == ["5", "2", "9"]
    t = {x["regla"]: x for x in fila.reporte["transformaciones"]}
    assert {(c["fila"], c["antes"], c["despues"]) for c in t["fuera_de_rango_cambiados"]["casos"]} == {
        (2, "Totalmente de acuerdo", "5"), (4, "Totalmente en desacuerdo", "2")}
