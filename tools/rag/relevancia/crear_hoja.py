"""Hoja para que la investigadora marque, sin ver los juicios del autor, qué fragmento de cada instrumento es el
relevante para cada pregunta de `tools/rag/recuperacion_oro.json` (9 nov 2026).

La hoja no trae los juicios del autor («oro»): solo la pregunta del usuario y, en una hoja por instrumento, la lista
de sus preguntas o reactivos (con sección y opciones) más la ficha. Después, `comparar.py` mide el acuerdo entre los
dos juicios (kappa de Cohen) y escribe un archivo con los juicios de la investigadora en el formato de
`recuperacion_oro.json`, para recalcular hit@k y MRR con ellos.

Uso (desde la raíz del repositorio):
    .venv\\Scripts\\python.exe tools\\rag\\relevancia\\crear_hoja.py
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

RAIZ = Path(__file__).resolve().parents[3]
ORO = RAIZ / "tools" / "rag" / "recuperacion_oro.json"
SALIDA = Path(__file__).with_name("juicios_relevancia_para_llenar.xlsx")

# Documento final vigente de cada instrumento (Anexo A, Tabla A.1).
DOCUMENTOS = {
    "127": "storage/json/127/54__v4_documento_final.json",
    "130": "storage/json/130/1__v2_documento_final.json",
    "129": "storage/json/129/49__v8_documento_final.json",
    "61": "storage/json/61/21__v2_documento_final.json",
    "60": "storage/json/60/484__v2_documento_final.json",
}
FICHA = "ficha"
NEGRITA = Font(bold=True)
ENCABEZADO = PatternFill("solid", fgColor="DDEBF7")
LLENAR = PatternFill("solid", fgColor="FFF2CC")
AJUSTE = Alignment(wrap_text=True, vertical="top")


def _corto(id_largo: str) -> str:
    return id_largo.rsplit("-", 1)[-1]


def _lista(valor) -> list:
    if isinstance(valor, str):
        try:
            return ast.literal_eval(valor)
        except (ValueError, SyntaxError):
            return [valor]
    return valor or []


def _opciones(item: dict) -> str:
    opciones = item.get("opciones")
    if isinstance(opciones, str):
        try:
            opciones = ast.literal_eval(opciones)
        except (ValueError, SyntaxError):
            return opciones
    if isinstance(opciones, dict):
        return "; ".join(f"{k}) {v}" for k, v in opciones.items())
    if opciones:
        return "; ".join(str(o) for o in opciones)
    escala = item.get("escala")
    if isinstance(escala, str):
        try:
            escala = ast.literal_eval(escala)
        except (ValueError, SyntaxError):
            return escala
    if isinstance(escala, dict) and escala.get("etiquetas"):
        return "Escala: " + "; ".join(f"{k} = {v}" for k, v in escala["etiquetas"].items())
    return ""


def _elementos(doc: dict) -> tuple[str, list[tuple[str, str, str, str]]]:
    """Título del instrumento y sus elementos buscables: (ID, sección, texto, opciones)."""
    titulo = (doc.get("instrumento") or {}).get("titulo") or ""
    secciones = {s["id"]: s.get("nombre", "") for s in doc.get("secciones") or []}
    filas = [(FICHA, "—", "Ficha del instrumento: título, objetivo, población, secciones, participantes, "
                         "indicaciones y lista de preguntas", "")]
    for item in doc.get("preguntas") or doc.get("reactivos") or []:
        filas.append((_corto(item["id"]), secciones.get(item.get("seccion_id"), ""), " ".join(str(item.get("texto")).split()),
                      _opciones(item)))
    return titulo, filas


def main() -> None:
    casos = json.loads(ORO.read_text(encoding="utf-8"))["casos"]
    libro = Workbook()

    hoja = libro.active
    hoja.title = "Instrucciones"
    texto = [
        "Juicios de relevancia de la recuperación",
        "",
        "Para cada pregunta de la hoja «Juicios», escribe qué fragmento o fragmentos del instrumento contienen lo que se "
        "necesita para responderla. No se califica la respuesta del chat: solo qué parte del instrumento es la relevante.",
        "",
        "Cómo llenarla:",
        "1. Busca el instrumento de la pregunta (columna «Instrumento») en su hoja (por ejemplo, «127»).",
        "2. En la columna amarilla «Fragmentos relevantes», escribe los IDs separados por coma: p17 o r04, p02.",
        "3. Si lo relevante es la descripción del instrumento (de qué trata, a quién se aplicó, cuánto dura), escribe «ficha».",
        "4. Marca todos los que sirvan, pero solo los que de verdad contienen lo necesario.",
        "5. Si ninguno sirve, escribe «ninguno» y explica en «Comentario».",
        "",
        "No consultes los juicios del autor (tools/rag/recuperacion_oro.json) antes de terminar: la comparación mide si "
        "dos personas coinciden por separado.",
    ]
    for i, linea in enumerate(texto, start=1):
        celda = hoja.cell(row=i, column=1, value=linea)
        celda.alignment = AJUSTE
        if i == 1:
            celda.font = Font(bold=True, size=14)
    hoja.column_dimensions["A"].width = 110

    juicios = libro.create_sheet("Juicios")
    columnas = ["Caso", "Instrumento", "Pregunta del usuario", "Fragmentos relevantes", "Comentario"]
    anchos = [11, 12, 80, 26, 40]
    for j, (nombre, ancho) in enumerate(zip(columnas, anchos), start=1):
        celda = juicios.cell(row=1, column=j, value=nombre)
        celda.font, celda.fill = NEGRITA, ENCABEZADO
        juicios.column_dimensions[celda.column_letter].width = ancho
    for i, c in enumerate(casos, start=2):
        for j, valor in enumerate([c["id"], c["instrumento"], c["consulta"], "", ""], start=1):
            celda = juicios.cell(row=i, column=j, value=valor)
            celda.alignment = AJUSTE
        juicios.cell(row=i, column=4).fill = LLENAR
    juicios.freeze_panes = "A2"

    for ins, ruta in DOCUMENTOS.items():
        doc = json.loads((RAIZ / ruta).read_text(encoding="utf-8"))
        titulo, filas = _elementos(doc)
        h = libro.create_sheet(ins)
        h.cell(row=1, column=1, value=f"Instrumento {ins}: {titulo}").font = Font(bold=True, size=12)
        for j, (nombre, ancho) in enumerate(zip(["ID", "Sección", "Texto", "Opciones o escala"], [8, 28, 80, 70]), start=1):
            celda = h.cell(row=3, column=j, value=nombre)
            celda.font, celda.fill = NEGRITA, ENCABEZADO
            h.column_dimensions[celda.column_letter].width = ancho
        for i, fila in enumerate(filas, start=4):
            for j, valor in enumerate(fila, start=1):
                h.cell(row=i, column=j, value=valor).alignment = AJUSTE
        h.freeze_panes = "A4"

    libro.save(SALIDA)
    print(f"{SALIDA} ({len(casos)} preguntas)")


if __name__ == "__main__":
    main()
