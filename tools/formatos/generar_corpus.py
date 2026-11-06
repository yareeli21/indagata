"""Corpus SINTÉTICO de formatos para la matriz de aceptación (`documentación/02_Desarrollo.md`, X.5).

Parte de enc_10_turno (60 respondentes, 8 ítems Likert en 2 dimensiones) y genera la
misma encuesta en cada formato aceptado o rechazado. Las respuestas son idénticas en
todas las variantes; solo cambia la forma, así que las respuestas del chat deben ser
las mismas.

Uso: python tools/formatos/generar_corpus.py   → tools/formatos/corpus/encuestas/
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
BASE = RAIZ / "storage" / "instrumentos_sinteticos" / "encuestas"
DESTINO = Path(__file__).resolve().parent / "corpus" / "encuestas"

ESCALA = {"1": "Totalmente en desacuerdo", "2": "En desacuerdo", "3": "Ni de acuerdo ni en desacuerdo",
          "4": "De acuerdo", "5": "Totalmente de acuerdo"}
INSTRUCCION_CUADRICULA = "Indica qué tan de acuerdo estás con las siguientes afirmaciones"


def _leer() -> tuple[str, list[str], list[list[str]], list[str]]:
    original = (BASE / "enc_10_turno_original.txt").read_text(encoding="utf-8")
    with (BASE / "enc_10_turno_respondido.csv").open(encoding="utf-8", newline="") as f:
        filas = list(csv.reader(f))
    preguntas = re.findall(r"^\d+\.\s+(.+)$", original, re.MULTILINE)
    assert len(preguntas) == 8 and len(filas) == 61
    return original, filas[0], filas[1:], preguntas


def _sin_secciones(original: str) -> str:
    texto = "\n".join(l for l in original.splitlines() if not re.match(r"^---.*---\s*$", l))
    return re.sub(r"\n{3,}", "\n\n", texto)


def _csv(encabezados: list[str], filas: list[list[str]], *, sep: str = ",", bom: bool = False) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=sep, lineterminator="\n")
    w.writerow(encabezados)
    w.writerows(filas)
    return buf.getvalue().encode("utf-8-sig" if bom else "utf-8")


def _xlsx(encabezados: list[str], filas: list[list[str]]) -> bytes:
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(encabezados)
    for f in filas:
        hoja.append([int(c) if c.isdigit() else c for c in f])
    buf = io.BytesIO()
    libro.save(buf)
    return buf.getvalue()


def generar() -> list[dict]:
    original, cab, datos, preguntas = _leer()
    contexto, items = cab[:4], cab[4:]          # id_respondente, turno, semestre, genero | 8 ítems
    ctx = [f[:4] for f in datos]
    resp = [f[4:] for f in datos]
    sin_sec = _sin_secciones(original)
    textos = [p.rstrip(".") for p in preguntas]
    variantes: list[dict] = []

    def agregar(clave: str, descripcion: str, nivel: str, archivo: tuple[str, bytes], orig: str | None, **esperado) -> None:
        variantes.append({"clave": clave, "descripcion": descripcion, "nivel": nivel,
                          "archivo": archivo[0], "original": f"{clave}_original.txt" if orig else None, **esperado})
        (DESTINO / archivo[0]).write_bytes(archivo[1])
        if orig:
            (DESTINO / f"{clave}_original.txt").write_text(orig.replace("ID: enc_10", f"ID: {clave}"), encoding="utf-8")

    filas = lambda cols: [c + r for c, r in zip(ctx, cols)]  # noqa: E731
    agregar("E01", "Con secciones; encabezados con prefijo de sección (Evaluación_item1…)", "ideal",
            ("E01_respuestas.csv", _csv(cab, datos)), original, dimensiones=2)
    agregar("E02", "Google Forms: marca temporal + texto completo de la pregunta; original con secciones", "ideal",
            ("E02_respuestas.csv", _csv(["Marca temporal", *contexto[1:], *textos],
                                        [["2026/10/01 10:%02d:00" % (i % 60), *c[1:], *r] for i, (c, r) in enumerate(zip(ctx, resp))])),
            original, dimensiones=2)
    agregar("E03", "Sin secciones; encabezado = texto de la pregunta", "aceptado",
            ("E03_respuestas.csv", _csv(contexto + textos, filas(resp))), sin_sec, dimensiones=2)
    agregar("E04", "Sin secciones; encabezados con prefijo (Evaluación_item1…)", "aceptado",
            ("E04_respuestas.csv", _csv(cab, datos)), sin_sec, dimensiones=2)
    agregar("E05", "Sin secciones; encabezados en código P1…P8 con original", "aceptado",
            ("E05_respuestas.csv", _csv(contexto + [f"P{i}" for i in range(1, 9)], filas(resp))), sin_sec, dimensiones=2)
    agregar("E06", "Google Forms con cuadrícula «Instrucción [afirmación]» y etiquetas de la escala", "ideal",
            ("E06_respuestas.csv", _csv(["Marca temporal", *contexto[1:], *[f"{INSTRUCCION_CUADRICULA} [{t}]" for t in textos]],
                                        [["2026/10/01", *c[1:], *[ESCALA[v] for v in r]] for c, r in zip(ctx, resp)])),
            original, dimensiones=2)
    qualtrics_sis = ["StartDate", "EndDate", "Status", "IPAddress", "Progress", "Duration (in seconds)", "Finished",
                     "RecordedDate", "ResponseId", "LocationLatitude", "LocationLongitude"]
    qualtrics_txt = ["Start Date", "End Date", "Response Type", "IP Address", "Progress", "Duration (in seconds)",
                     "Finished", "Recorded Date", "Response ID", "Location Latitude", "Location Longitude"]
    codigos_q = [f"Q{i}" for i in range(1, 9)]
    q_filas = [qualtrics_txt + ["turno", "semestre", "genero"] + textos,
               [json.dumps({"ImportId": c}) for c in qualtrics_sis + ["turno", "semestre", "genero"] + [f"QID{i}" for i in range(1, 9)]]]
    q_filas += [["2026-10-01 10:00:00", "2026-10-01 10:05:00", "IP Address", f"10.0.0.{i % 250}", "100", "300", "True",
                 "2026-10-01 10:05:00", f"R_{i:05d}", "19.43", "-99.13", *c[1:], *r] for i, (c, r) in enumerate(zip(ctx, resp))]
    agregar("E07", "Exporte de Qualtrics (3 filas de encabezado, columnas de sistema, IP y ubicación)", "aceptado",
            ("E07_respuestas.csv", _csv(qualtrics_sis + ["turno", "semestre", "genero"] + codigos_q, q_filas)), original, dimensiones=2)
    lime = [f"G01Q{i:02d}" for i in range(1, 5)] + [f"G02Q{i:02d}" for i in range(5, 9)]
    agregar("E08", "Exporte de LimeSurvey con códigos G01Q01…G02Q08 y columnas de sistema", "aceptado",
            ("E08_respuestas.csv", _csv(["id", "submitdate", "lastpage", "startlanguage", "seed", "turno", "semestre", "genero", *lime],
                                        [[str(i + 1), "2026-10-01 10:00:00", "3", "es", "12345", *c[1:], *r]
                                         for i, (c, r) in enumerate(zip(ctx, resp))])),
            original, dimensiones=2)
    agregar("E09", "XLSX sin secciones con texto de la pregunta", "ideal",
            ("E09_respuestas.xlsx", _xlsx(contexto + textos, filas(resp))), sin_sec, dimensiones=2)
    agregar("E10", "CSV con «;» y BOM UTF-8, encabezados con prefijo, original con secciones", "ideal",
            ("E10_respuestas.csv", _csv(cab, datos, sep=";", bom=True)), original, dimensiones=2)
    agregar("E11", "Códigos P1…P8 SIN original", "rechazado",
            ("E11_respuestas.csv", _csv(contexto + [f"P{i}" for i in range(1, 9)], filas(resp))), None, rechazo="instrumento original")
    largo = [[c[0], f"P{j + 1}", v] for c, r in zip(ctx, resp) for j, v in enumerate(r)]
    agregar("E12", "Formato largo (respondente, pregunta, respuesta)", "rechazado",
            ("E12_respuestas.csv", _csv(["respondente", "pregunta", "respuesta"], largo)), original, rechazo="formato largo")
    agregar("E13", "Sin fila de encabezados", "rechazado",
            ("E13_respuestas.csv", _csv(datos[0], datos[1:])), original, rechazo="encabezados")
    return variantes


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    v = generar()
    (DESTINO / "variantes.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    for x in v:
        print(x["clave"], x["nivel"], x["descripcion"])
