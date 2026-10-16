"""Pruebas del esqueleto: salud, permisos y ciclo de vida de una ejecución.

Usan un motor FALSO (registrado solo en estas pruebas) para ejercitar el flujo
crear → decidir → confirmar → vista final sin depender de las reglas de cada tipo.
"""
from __future__ import annotations

import csv
import io

import pytest

from shared.models.instrumento_procesado import InstrumentoProcesado
from shared.models.limpieza_ejecucion import LimpiezaEjecucion
from shared.parsing import read_tabular

from conftest import ADMIN, ANA, LUIS, crear_instrumento


class MotorFalso:
    """Encuesta mínima: propone eliminar la columna `id` y exige decidir el rol de `P1`."""

    nombre = "falso"

    def __init__(self, fallar: bool = False) -> None:
        self.fallar = fallar

    def automatica(self, entrada):  # noqa: ANN001, ANN201
        from services.motores import ErrorLimpieza, Hallazgo, ResultadoAutomatico

        if self.fallar:
            raise ErrorLimpieza("El archivo no tiene encabezados reconocibles.")
        tabla = read_tabular(entrada.contenido, entrada.extension)
        return ResultadoAutomatico(
            hallazgos=[
                Hallazgo(
                    id="col-ajena:id", tipo="columna_ajena", tema="Columnas", objetivo="id",
                    titulo="«id» no parece parte del instrumento", descripcion="Identificador de plataforma.",
                    opciones=["eliminar", "conservar"], sugerida="eliminar",
                ),
                Hallazgo(
                    id="rol:P1", tipo="rol_columna", tema="Columnas", objetivo="P1",
                    titulo="¿Qué es «P1»?", descripcion="Código corto: revisa su rol.",
                    opciones=["pregunta", "contexto", "eliminar"], obligatoria=True,
                ),
            ],
            transformaciones=[{"regla": "espacios", "detalle": "Se quitaron espacios extra.", "afectados": 1}],
            metricas={"n_respondentes": len(tabla.rows), "n_columnas": len(tabla.headers)},
            especifico={"columnas": tabla.headers},
        )

    def aplicar(self, entrada, automatico, decisiones):  # noqa: ANN001, ANN201
        from services.motores import ResultadoFinal

        tabla = read_tabular(entrada.contenido, entrada.extension)
        quitar = {"id"} if decisiones.get("col-ajena:id") == "eliminar" else set()
        if decisiones.get("rol:P1") == "eliminar":
            quitar.add("P1")
        idx = [i for i, h in enumerate(tabla.headers) if h not in quitar]
        encabezados = [tabla.headers[i] for i in idx]
        filas = [[f[i] for i in idx] for f in tabla.rows]
        return ResultadoFinal(
            encabezados=encabezados,
            filas=filas,
            metricas={"n_respondentes": len(filas), "n_columnas": len(encabezados)},
            especifico={"columnas": encabezados},
            transformaciones=[{"regla": "columnas_eliminadas", "detalle": ", ".join(sorted(quitar)), "afectados": len(quitar)}],
            cifras=[{"etiqueta": "Respondentes", "valor": len(filas)}, {"etiqueta": "Columnas", "valor": len(encabezados)}],
            vista={"forma": "tabla", "columnas": encabezados, "filas": filas[:20]},
        )


CSV = "id,P1,Comentario\n1,5,Bien\n2,4,Regular\n".encode()


@pytest.fixture()
def motor_falso():
    from services import motores

    previo = motores._REGISTRO.copy()
    motor = MotorFalso()
    motores.registrar("encuesta", "tabular", motor)
    yield motor
    motores._REGISTRO.clear()
    motores._REGISTRO.update(previo)


def test_health(cliente):
    assert cliente.get("/health").json() == {"status": "ok", "service": "cleaning-service"}


def test_requiere_token_y_autoria(cliente, db, storage, motor_falso):
    id_crudo = crear_instrumento(db, storage, "e.csv", CSV)
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones").status_code == 401
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=LUIS).status_code == 403
    assert cliente.post("/limpieza/999/ejecuciones", headers=ANA).status_code == 404
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ADMIN).status_code == 200


def test_formato_sin_motor_responde_501_y_no_crea_version(cliente, db, storage):
    # Una entrevista en tabla no tiene motor (las entrevistas son documentos).
    id_crudo = crear_instrumento(db, storage, "entrevista.csv", b"id,P1\n1,A\n", tipo="entrevista")
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert r.status_code == 501
    assert "aún no está disponible" in r.json()["detail"]
    assert db.query(LimpiezaEjecucion).count() == 0


def test_ciclo_completo(cliente, db, storage, motor_falso):
    id_crudo = crear_instrumento(db, storage, "e.csv", CSV)

    # 1. Fase automática: versión 1 esperando decisiones; el instrumento pasa a limpieza_en_proceso.
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert r.status_code == 200, r.text
    e = r.json()
    assert (e["version"], e["estado"], e["pendientesObligatorias"]) == (1, "esperando_decisiones", 1)
    assert e["metricasAntes"] == {"n_respondentes": 2, "n_columnas": 3}
    assert {h["id"]: h["sugerida"] for h in e["hallazgos"]} == {"col-ajena:id": "eliminar", "rol:P1": None}
    assert db.query(InstrumentoProcesado).one().estado == "limpieza_en_proceso"

    # 2. Retomar: sin `nueva` devuelve la misma versión.
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()["version"] == 1

    # 3. No se puede confirmar con decisiones obligatorias pendientes.
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 409

    # 4. Decisiones parciales: se validan y se guardan.
    bad = cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"rol:P1": "x"}}, headers=ANA)
    assert bad.status_code == 422
    r = cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"rol:P1": "pregunta"}}, headers=ANA)
    assert r.json()["pendientesObligatorias"] == 0
    assert next(h for h in r.json()["hallazgos"] if h["id"] == "rol:P1")["decision"] == "pregunta"
    # Retomar tras "cerrar la página": la decisión sigue ahí.
    actual = cliente.get(f"/limpieza/{id_crudo}/ejecuciones/actual", headers=ANA).json()
    assert next(h for h in actual["hallazgos"] if h["id"] == "rol:P1")["decision"] == "pregunta"

    # 5. Confirmar: la sugerida (eliminar id) se aplica; CSV `;` UTF-8 con BOM en storage.
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["estado"] == "confirmada"
    assert e["vistaFinal"]["columnas"] == ["P1", "Comentario"]
    assert e["vistaFinal"]["cifras"][0] == {"etiqueta": "Respondentes", "valor": 2}

    fila = db.query(LimpiezaEjecucion).one()
    contenido = storage.archivos[fila.ruta_csv_limpio]
    assert contenido.startswith(b"\xef\xbb\xbf")
    filas = list(csv.reader(io.StringIO(contenido.decode("utf-8-sig")), delimiter=";"))
    assert filas == [["P1", "Comentario"], ["5", "Bien"], ["4", "Regular"]]
    assert fila.ruta_csv_limpio.startswith(f"clean/{id_crudo}/") and "v1_encuesta_limpio.csv" in fila.ruta_csv_limpio

    # Reporte: decisiones con su origen, métricas antes/después y archivos.
    rep = fila.reporte
    assert rep["esquema"] == "reporte_limpieza/1" and rep["version_servicio"]
    assert rep["decisiones"]["col-ajena:id"]["origen"] == "sugerida"
    assert rep["decisiones"]["rol:P1"]["origen"] == "investigador"
    assert rep["metricas"]["despues"] == {"n_respondentes": 2, "n_columnas": 2}
    assert rep["archivos"]["limpio"] == fila.ruta_csv_limpio
    procesado = db.query(InstrumentoProcesado).one()
    assert procesado.estado == "limpio"
    # metadata-service y las descargas leen el CSV limpio desde aquí.
    assert procesado.ruta_de_archivo_limpio == fila.ruta_csv_limpio

    # 6. La versión confirmada ya no admite cambios; la vista final se puede consultar.
    assert cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"rol:P1": "contexto"}}, headers=ANA).status_code == 409
    vf = cliente.get(f"/limpieza/{id_crudo}/ejecuciones/1/vista-final", headers=ANA)
    assert vf.status_code == 200 and vf.json()["total_filas"] == 2

    # 7. "Volver a ajustar": versión 2 con las decisiones del investigador precargadas.
    r = cliente.post(f"/limpieza/{id_crudo}/ejecuciones?nueva=true", headers=ANA).json()
    assert r["version"] == 2 and r["pendientesObligatorias"] == 0
    assert next(h for h in r["hallazgos"] if h["id"] == "rol:P1")["decision"] == "pregunta"


def test_fallo_de_limpieza_queda_registrado_con_mensaje_claro(cliente, db, storage, motor_falso):
    motor_falso.fallar = True
    id_crudo = crear_instrumento(db, storage, "e.csv", CSV)
    e = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()
    assert e["estado"] == "fallida"
    assert e["error"] == "El archivo no tiene encabezados reconocibles."
    # No avanzó el instrumento (no se envía nada a metadata).
    assert db.query(InstrumentoProcesado).one().estado == "recibido"


def test_fallo_de_storage_al_confirmar_permite_reintentar(cliente, db, storage, motor_falso):
    id_crudo = crear_instrumento(db, storage, "e.csv", CSV)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"rol:P1": "pregunta"}}, headers=ANA)
    storage.fallar_guardado = True
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 502
    assert db.query(LimpiezaEjecucion).one().estado == "esperando_decisiones"
    storage.fallar_guardado = False
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).json()["estado"] == "confirmada"


def test_lectores_compartidos_csv_punto_y_coma_y_xls_ooxml():
    tabla = read_tabular("a;b\n1;2\n".encode("utf-8-sig"), ".csv")
    assert tabla.headers == ["a", "b"] and tabla.rows == [["1", "2"]]
    # Un ".xls" que en realidad es OOXML se lee como XLSX (no falla).
    import openpyxl

    libro = openpyxl.Workbook()
    libro.active.append(["x", "y"])
    libro.active.append([1, 2])
    buffer = io.BytesIO()
    libro.save(buffer)
    tabla = read_tabular(buffer.getvalue(), ".xls")
    assert tabla.headers == ["x", "y"] and tabla.rows == [["1", "2"]]


def test_peticiones_simultaneas_no_duplican_la_version(cliente, db, storage, motor_falso, monkeypatch):
    """Dos POST a la vez calculan la misma versión: la segunda retoma la primera."""
    from services import ejecuciones

    id_crudo = crear_instrumento(db, storage, "e.csv", CSV)
    primera = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).json()

    # Simula la carrera: la segunda petición no ve la primera al empezar y calcula
    # la misma versión; la base de datos rechaza el duplicado y se retoma la ganadora.
    original_ultima = ejecuciones.ultima
    llamadas = {"n": 0}

    def ultima_en_carrera(db, i):  # noqa: ANN001, ANN202
        llamadas["n"] += 1
        return None if llamadas["n"] == 1 else original_ultima(db, i)

    monkeypatch.setattr(ejecuciones, "ultima", ultima_en_carrera)
    monkeypatch.setattr(ejecuciones, "_siguiente_version", lambda db, i: 1)
    segunda = cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["version"] == primera["version"] == 1
    assert db.query(LimpiezaEjecucion).count() == 1


def test_no_retrocede_el_estado_de_un_instrumento_ya_estandarizado(cliente, db, storage, motor_falso):
    id_crudo = crear_instrumento(db, storage, "e.csv", CSV)
    procesado = db.query(InstrumentoProcesado).one()
    procesado.estado = "estandarizado"
    db.commit()
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)
    cliente.patch(f"/limpieza/{id_crudo}/ejecuciones/1/decisiones", json={"decisiones": {"rol:P1": "pregunta"}}, headers=ANA)
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA)
    db.refresh(procesado)
    assert procesado.estado == "estandarizado"
