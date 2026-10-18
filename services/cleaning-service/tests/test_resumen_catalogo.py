"""Resumen de la limpieza después de guardar (catálogo) y sugerencias de análisis (`/limpieza/{id}/resumen`)."""
from __future__ import annotations

from datetime import datetime

from shared.conocimiento import sugerencias
from shared.models.instrumento_procesado import InstrumentoProcesado

from conftest import ADMIN, ANA, LUIS, crear_instrumento
from tests.test_estadistica import _encuesta


def _confirmada(cliente, db, storage) -> int:  # noqa: ANN001
    id_crudo = crear_instrumento(db, storage, "encuesta.csv", _encuesta())
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA).status_code == 200
    assert cliente.post(f"/limpieza/{id_crudo}/ejecuciones/1/confirmar", headers=ANA).status_code == 200
    return id_crudo


def test_resumen_trae_medidas_y_sugerencias_sin_filas(cliente, db, storage):
    id_crudo = _confirmada(cliente, db, storage)
    r = cliente.get(f"/limpieza/{id_crudo}/resumen", headers=ANA)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["version"] == 1 and datos["estadistica"]["fiabilidad"][0]["bloque"] == "Satisfacción con la carrera"
    assert "filas" not in datos and "columnas" not in datos  # sin datos de respondentes
    textos = " ".join(s["texto"] for s in datos["sugerencias"])
    assert "Puedes promediar los 4 ítems del bloque «Satisfacción con la carrera»" in textos
    assert "Mann-Whitney" in textos  # hay una columna de contexto (Carrera)
    assert "mediana y rango intercuartílico" in textos  # el ingreso está sesgado


def test_resumen_de_otro_investigador_solo_si_esta_aprobado(cliente, db, storage):
    id_crudo = _confirmada(cliente, db, storage)
    assert cliente.get(f"/limpieza/{id_crudo}/resumen", headers=LUIS).status_code == 403
    assert cliente.get(f"/limpieza/{id_crudo}/resumen", headers=ADMIN).status_code == 200
    procesado = db.query(InstrumentoProcesado).filter_by(id_crudo=id_crudo).one()
    procesado.fecha_aprobado = datetime.now()
    db.commit()
    assert cliente.get(f"/limpieza/{id_crudo}/resumen", headers=LUIS).status_code == 200


def test_sin_limpieza_confirmada_es_404(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, "encuesta.csv", _encuesta())
    assert cliente.get(f"/limpieza/{id_crudo}/resumen", headers=ANA).status_code == 404
    cliente.post(f"/limpieza/{id_crudo}/ejecuciones", headers=ANA)  # esperando decisiones: aún no cuenta
    assert cliente.get(f"/limpieza/{id_crudo}/resumen", headers=ANA).status_code == 404


def _bloque(alfa: float, por_item: list[dict] | None = None) -> dict:
    return {"bloque": "B", "alfa": alfa, "n_items": 3, "items": ["i1", "i2", "i3"], "por_item": por_item or []}


def test_reglas_de_fiabilidad_por_bloque():
    def niveles(alfa: float) -> list[str]:
        return [s["nivel"] for s in sugerencias.sugerir("encuesta", {"fiabilidad": [_bloque(alfa)]})]

    assert niveles(0.97) == ["atencion"] and niveles(0.82) == ["bien"]
    assert niveles(0.65) == ["atencion"] and niveles(0.4) == ["alerta"]
    flojo = sugerencias.sugerir("encuesta", {"fiabilidad": [_bloque(0.75, [
        {"item": "i2", "correlacion_item_total": 0.1, "alfa_si_se_elimina": 0.85}])]})
    assert any("Revisa en «B»: i2" in s["texto"] for s in flojo)


def test_linea_recta_y_vacios_piden_cautela_y_van_primero():
    e = {"columnas": [{"id": "p1", "etiqueta": "P1", "rol": "pregunta", "tipo": "likert", "n": 100, "pct_nulos": 35.0}],
         "encuestados": {"linea_recta": 20, "incompletos": 0}}
    salida = sugerencias.sugerir("encuesta", e)
    assert [s["nivel"] for s in salida][:2] == ["atencion", "atencion"]
    assert any("20 de 100 encuestados (20.0 %)" in s["texto"] for s in salida)
    assert any("«P1»" in s["texto"] and "20 %" in s["texto"] for s in salida)


def test_prueba_kr20_y_reactivos_que_no_discriminan():
    e = {"fiabilidad": {"kr20": 0.62, "interpretacion": "cuestionable", "n_alumnos": 40, "n_reactivos": 10},
         "reactivos": [{"pregunta": "q1", "discriminacion": 0.45, "distractores_sin_elegir": []},
                       {"pregunta": "q7", "discriminacion": -0.1, "distractores_sin_elegir": ["D"]}],
         "resumen_reactivos": {"faciles": 1, "medios": 1, "dificiles": 0}}
    salida = sugerencias.sugerir("prueba_estandarizada", e)
    assert salida[0]["nivel"] == "alerta" and "q7 (D = -0.1)" in salida[0]["texto"]
    assert any("KR-20 = 0.62" in s["texto"] for s in salida)
    assert any("1 reactivos tienen distractores" in s["texto"] for s in salida)


def test_entrevista_participacion_desigual():
    e = {"n_preguntas": 3, "participantes": [{"id": "E01", "palabras": 900}, {"id": "E02", "palabras": 100}]}
    salida = sugerencias.sugerir("entrevista", e)
    assert salida[0]["nivel"] == "atencion" and "E01: 900 palabras" in salida[0]["texto"]
    assert sugerencias.sugerir("encuesta", None) == []
