"""Genera enc_12: la encuesta enc_10 (turno) en formato de MICRODATOS, con su diccionario de datos.

Sirve para probar de punta a punta los microdatos: encabezados en código (P1…P11), respuestas en código
(turno 1/2, género 1/2) y un diccionario de datos con el texto de cada pregunta y el significado de cada
código, SIN instrumento original. Como las respuestas son las de enc_10, lo que debe contestar el chat se
conoce de antemano (p. ej. cuántos respondentes son del turno vespertino).

  - enc_12_microdatos_respondido.csv  folio, P1 (turno), P2 (semestre), P3 (género), P4…P11 (Likert 1–5)
  - enc_12_microdatos_diccionario.csv formato largo: variable, pregunta, valor, etiqueta

Ejecutar desde la raíz del repositorio:
    python tools/data_synthesis/generar_enc_12_microdatos.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[2] / "storage" / "instrumentos_sinteticos" / "encuestas"
ORIGEN = "enc_10_turno"
DESTINO = "enc_12_microdatos"

# Códigos de las columnas de contexto (como en una base de microdatos).
CODIGOS = {
    "turno": {"Matutino": "1", "Vespertino": "2"},
    "genero": {"masculino": "1", "femenino": "2"},
}
ETIQUETAS_GENERO = {"1": "Masculino", "2": "Femenino"}
PREGUNTAS_CONTEXTO = {"turno": "¿En qué turno estudias?", "semestre": "¿Qué semestre cursas?", "genero": "Género"}


def _escala(texto: str) -> dict[str, str]:
    """Leyenda «1 = Totalmente en desacuerdo» del instrumento original."""
    return dict(re.findall(r"^\s*(\d)\s*=\s*(.+?)\s*$", texto, re.M))


def _reactivos(texto: str) -> list[str]:
    return re.findall(r"^\d+\.\s+(.+?)\s*$", texto, re.M)


def main() -> None:
    original = (CARPETA / f"{ORIGEN}_original.txt").read_text(encoding="utf-8")
    escala, reactivos = _escala(original), _reactivos(original)
    with open(CARPETA / f"{ORIGEN}_respondido.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    items = [c for c in filas[0] if "_item" in c]
    assert len(items) == len(reactivos) == 8, (len(items), len(reactivos))

    # Variables: P1 turno, P2 semestre, P3 género y P4…P11 los ítems, en el orden de enc_10.
    contexto = ["turno", "semestre", "genero"]
    variables = {col: f"P{k}" for k, col in enumerate(contexto + items, start=1)}

    with open(CARPETA / f"{DESTINO}_respondido.csv", "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["folio", *variables.values()])
        for i, fila in enumerate(filas, start=1):
            valores = [CODIGOS.get(col, {}).get(fila[col], fila[col]) for col in variables]
            escritor.writerow([i, *valores])

    with open(CARPETA / f"{DESTINO}_diccionario.csv", "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["variable", "pregunta", "valor", "etiqueta"])
        for col in contexto:
            var = variables[col]
            if col == "turno":
                for k, (etq, cod) in enumerate(CODIGOS["turno"].items()):
                    escritor.writerow([var, PREGUNTAS_CONTEXTO[col] if k == 0 else "", cod, etq])
            elif col == "genero":
                for k, (cod, etq) in enumerate(ETIQUETAS_GENERO.items()):
                    escritor.writerow([var, PREGUNTAS_CONTEXTO[col] if k == 0 else "", cod, etq])
            else:
                escritor.writerow([var, PREGUNTAS_CONTEXTO[col], "", ""])
        for col, texto in zip(items, reactivos):
            var = variables[col]
            for k, (cod, etq) in enumerate(escala.items()):
                escritor.writerow([var, texto if k == 0 else "", cod, etq])
    print(f"{DESTINO}: {len(filas)} respondentes, {len(variables)} variables")


if __name__ == "__main__":
    main()
