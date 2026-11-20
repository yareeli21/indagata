"""Variantes SIN SECCIONES de enc_10_turno (sintético) para la prueba de robustez.

Las 60 respuestas son idénticas en las tres variantes; solo cambia la forma:
  A: original sin las líneas «--- SECCIÓN ---»; CSV igual (encabezados «Evaluación_item1…»).
  B: original sin secciones; CSV con el texto completo de cada pregunta como encabezado
     (como lo exporta Google Forms).
  C: original sin secciones; CSV con encabezados codificados P1…P8 (peor caso).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BASE = AQUI.parents[1] / "storage" / "instrumentos_sinteticos" / "encuestas"

original = (BASE / "enc_10_turno_original.txt").read_text(encoding="utf-8")
sin_secciones = "\n".join(l for l in original.splitlines() if not re.match(r"^---.*---\s*$", l))
sin_secciones = re.sub(r"\n{3,}", "\n\n", sin_secciones)
preguntas = re.findall(r"^\d+\.\s+(.+)$", sin_secciones, re.MULTILINE)
assert len(preguntas) == 8, preguntas

with (BASE / "enc_10_turno_respondido.csv").open(encoding="utf-8", newline="") as f:
    filas = list(csv.reader(f))
cab, datos = filas[0], filas[1:]
items = cab[4:]
assert len(items) == 8 and len(datos) == 60

encabezados = {
    "A": items,
    "B": [p.rstrip(".") for p in preguntas],
    "C": [f"P{i}" for i in range(1, 9)],
}
for v, enc in encabezados.items():
    texto = sin_secciones.replace("ID: enc_10", f"ID: enc_10_sinsec_{v}").replace(
        "Fuente: SINTÉTICO", f"Fuente: SINTÉTICO (variante {v} sin secciones de enc_10_turno)")
    (AQUI / f"enc_10_sinsec_{v}_original.txt").write_text(texto, encoding="utf-8")
    with (AQUI / f"enc_10_sinsec_{v}_respondido.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cab[:4] + enc)
        w.writerows(datos)
    print(v, (cab[:4] + enc)[3:7])
