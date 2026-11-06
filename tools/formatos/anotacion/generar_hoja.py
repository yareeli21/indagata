"""Hoja para que la investigadora anote, SIN ver la anotación de referencia, su interpretación
de las 32 respuestas de los corpus de entrevistas (dos temas).

Columnas a llenar: postura (lista: sí / no / ambivalente / no aplica) y la frase que responde
la pregunta (copiada de la respuesta). Después, `comparar.py` mide el acuerdo entre su
anotación, la del autor y el sistema.

Uso: python tools/formatos/anotacion/generar_hoja.py → tools/formatos/anotacion/anotacion_para_llenar.xlsx
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import corpus_docentes as doc  # noqa: E402
import corpus_entrevistas as est  # noqa: E402

libro = Workbook()
hoja = libro.active
hoja.title = "Anotación"
instrucciones = libro.create_sheet("Instrucciones", 0)
for fila in [
    ["Cómo anotar"],
    [""],
    ["1. Lee la PREGUNTA y la RESPUESTA de cada fila. Fíjate en el momento que pide la pregunta (casi todas preguntan por AHORA)."],
    ["2. En «Tu postura» elige: sí / no / ambivalente / no aplica, según lo que la persona responde a la pregunta."],
    ["   Lo que cuenta de otro momento (por ejemplo, «cuando iba en la primaria…») es contexto: no decide la postura."],
    ["3. En «Frase que responde» copia, tal cual, la parte de la respuesta que contesta la pregunta."],
    ["4. «Comentario» es opcional (por ejemplo, si la respuesta te parece ambigua)."],
    [""],
    ["No hay respuestas correctas de antemano: se compara tu interpretación con la del autor y la del sistema."],
]:
    instrucciones.append(fila)
instrucciones["A1"].font = Font(bold=True, size=13)
instrucciones.column_dimensions["A"].width = 120

encabezados = ["Tema", "Persona", "N.º", "Pregunta", "Respuesta", "Tu postura", "Frase que responde (copiada)", "Comentario"]
hoja.append(encabezados)
for c in hoja[1]:
    c.font = Font(bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="2F5597")
    c.alignment = Alignment(wrap_text=True, vertical="center")

for tema, m in (("Estudiantes: vida universitaria", est), ("Docentes: evaluación", doc)):
    for n, persona in enumerate(m.PERSONAS, start=1):
        for i, (respuesta, *_ref) in enumerate(m.RESPUESTAS[persona]):
            hoja.append([tema, f"E{n:02d}", i + 1, m.PREGUNTAS[i], respuesta, "", "", ""])

lista = DataValidation(type="list", formula1='"sí,no,ambivalente,no aplica"', allow_blank=True)
lista.error, lista.errorTitle = "Elige sí, no, ambivalente o no aplica.", "Postura"
hoja.add_data_validation(lista)
lista.add(f"F2:F{hoja.max_row}")
for col, ancho in zip("ABCDEFGH", (22, 9, 5, 45, 70, 14, 45, 30)):
    hoja.column_dimensions[col].width = ancho
for fila in hoja.iter_rows(min_row=2):
    for c in fila:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    fila[5].fill = PatternFill("solid", fgColor="FFF2CC")
    fila[6].fill = PatternFill("solid", fgColor="FFF2CC")
hoja.freeze_panes = "F2"
destino = AQUI / "anotacion_para_llenar.xlsx"
libro.save(destino)
print(destino, hoja.max_row - 1, "respuestas")
