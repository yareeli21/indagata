"""Exportación .sav de microdatos: el texto de la pregunta y la etiqueta de cada código vienen de la limpieza."""
from __future__ import annotations

import os
import tempfile

import pytest

from services import sav_export

pyreadstat = pytest.importorskip("pyreadstat")


def _leer(contenido: bytes, **opciones):
    descriptor, ruta = tempfile.mkstemp(suffix=".sav")
    os.close(descriptor)
    try:
        with open(ruta, "wb") as f:
            f.write(contenido)
        return pyreadstat.read_sav(ruta, **opciones)
    finally:
        os.unlink(ruta)


def test_codigos_conservan_su_numero_con_etiqueta_de_valor():
    significados = {
        "p1": {"pregunta": "¿Cuál es tu sexo?", "valores": {"1": "Hombre", "2": "Mujer"}},
        "p4": {"pregunta": "¿Qué medio usas para estudiar?", "valores": {"A": "Libros", "B": "Videos"}},
    }
    contenido = sav_export.generar_sav(["p1", "p4", "edad"], [["1", "A", "19"], ["2", "B", "21"]], "micro", significados)
    df, meta = _leer(contenido)
    assert list(df["p1"]) == [1.0, 2.0]
    assert meta.variable_value_labels["p1"] == {1.0: "Hombre", 2.0: "Mujer"}
    assert meta.column_names_to_labels["p1"] == "¿Cuál es tu sexo?"
    # Letras: la categoría es su etiqueta.
    assert set(meta.variable_value_labels["p4"].values()) == {"Libros", "Videos"}
    assert "Edad" in meta.column_names_to_labels.values() or "edad" in meta.column_names_to_labels.values()


def _fichas():
    return {
        "frecuencia_tutorias": {"id": "frecuencia_tutorias", "etiqueta": "¿Con qué frecuencia asistes a tutorías?",
                                "tipo_canonico": "likert", "estado": "conservada",
                                "likert": {"escala": "frecuencia", "puntos": 3, "invertido": True,
                                           "codigos": {"Nunca": 1, "A veces": 2, "Siempre": 3},
                                           "etiquetas": ["Nunca", "A veces", "Siempre"]}},
        "ambiente_item1": {"id": "ambiente_item1", "etiqueta": "Ambiente_item1", "tipo_canonico": "likert",
                           "estado": "conservada", "likert": {"escala": "numerica", "puntos": 5, "codigos": {},
                                                              "etiquetas": ["1", "2", "3", "4", "5"]}},
        "beca": {"id": "beca", "etiqueta": "¿Cuentas con una beca?", "tipo_canonico": "binaria", "estado": "conservada"},
        "carga": {"id": "carga", "etiqueta": "¿Cómo es tu carga?", "tipo_canonico": "opcion_multiple_varias",
                  "estado": "conservada"},
        "presion": {"id": "presion", "etiqueta": "Del_1_al_10,_cuánta_presión_sientes", "tipo_canonico": "escala_lineal",
                    "estado": "conservada"},
    }


def test_sav_desde_la_limpieza_escalas_tipos_y_texto_de_pregunta():
    headers = ["frecuencia_tutorias", "ambiente_item1", "beca", "carga", "presion"]
    filas = [["Siempre", "4", "Sí", "Mucha, Exámenes", "7"],
             ["Nunca", "Totalmente en desacuerdo", "No", "Poca", "3"],
             ["No aplica", "Totalmente de acuerdo", "Sí", "Mucha", "10"]]
    contenido = sav_export.generar_sav(headers, filas, "enc", None, _fichas())
    df, meta = _leer(contenido)
    etiquetas = meta.column_names_to_labels
    # Escala con su orden y etiquetas; lo que no es de la escala queda como perdido declarado.
    assert list(df["frecuencia_tutorias"])[:2] == [3.0, 1.0]
    assert meta.variable_value_labels["frecuencia_tutorias"] == {1.0: "Nunca", 2.0: "A veces", 3.0: "Siempre", 97.0: "No aplica"}
    assert df["frecuencia_tutorias"].isna().iloc[2]  # SPSS lo trata como perdido
    _, meta_perdidos = _leer(contenido, user_missing=True)
    assert meta_perdidos.missing_ranges["frecuencia_tutorias"] == [{"lo": 97.0, "hi": 97.0}]
    assert meta.variable_measure["frecuencia_tutorias"] == "ordinal"
    assert etiquetas["frecuencia_tutorias"] == "¿Con qué frecuencia asistes a tutorías? (ítem invertido)"
    # Likert numérica: el número tal cual y los extremos escritos con su punto y su etiqueta.
    assert list(df["ambiente_item1"]) == [4.0, 1.0, 5.0]
    assert meta.variable_measure["ambiente_item1"] == "ordinal"
    assert meta.variable_value_labels["ambiente_item1"] == {1.0: "Totalmente en desacuerdo", 5.0: "Totalmente de acuerdo"}
    assert etiquetas["ambiente_item1"] == "Ambiente item1"
    # Binaria Sí = 1, No = 0; selección múltiple como texto, no como combinaciones codificadas.
    assert list(df["beca"]) == [1.0, 0.0, 1.0] and meta.variable_value_labels["beca"] == {1.0: "Sí", 0.0: "No"}
    assert list(df["carga"]) == ["Mucha, Exámenes", "Poca", "Mucha"]
    assert meta.variable_measure["presion"] == "ordinal"
    assert etiquetas["presion"] == "Del 1 al 10, cuánta presión sientes"


def test_columnas_de_reporte_deja_fuera_las_eliminadas():
    reporte = {"especifico": {"encuesta": {"columnas": [{"id": "a", "estado": "conservada"},
                                                        {"id": "marca_temporal", "estado": "eliminada"}]}}}
    assert set(sav_export.columnas_de_reporte(reporte)) == {"a"}
    assert sav_export.columnas_de_reporte(None) == {}
