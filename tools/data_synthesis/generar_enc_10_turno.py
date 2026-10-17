"""Genera enc_10: encuesta sintética con la columna `turno` (matutino/vespertino).

Sirve para probar de punta a punta las preguntas por grupo del chat («¿qué porcentaje
del turno vespertino está de acuerdo con la pregunta 4?»), que ninguna de las
encuestas enc_01…enc_09 permite porque no traen turno.

Diseño (reproducible con la semilla):
  - 60 respondentes (R0001…R0060), 30 por turno, con semestre y género.
  - 8 ítems Likert 1–5 en dos dimensiones de 4 ítems: «Evaluación del aprendizaje»
    y «Ambiente escolar». Cada persona tiene un rasgo latente por dimensión, así los
    ítems de un bloque son consistentes entre sí (α alto, como en enc_01…09).
  - El turno vespertino tiene, a propósito, menos acuerdo en la dimensión de
    evaluación (media latente más baja): así la comparación por turno da cifras
    distintas y verificables.

Ejecutar desde la raíz del repositorio:
    python tools/data_synthesis/generar_enc_10_turno.py
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

SEMILLA = 2026_10_17
SALIDA = Path(__file__).resolve().parents[2] / "storage" / "instrumentos_sinteticos" / "encuestas"

DIMENSIONES = {
    "Evaluación": ("EVALUACIÓN DEL APRENDIZAJE", [
        "Los criterios de evaluación se explican con claridad al inicio del curso.",
        "Las calificaciones reflejan lo que realmente aprendí.",
        "Recibo retroalimentación sobre mis trabajos a tiempo para mejorar.",
        "Las evaluaciones están relacionadas con lo que se ve en clase.",
    ]),
    "Ambiente": ("AMBIENTE ESCOLAR", [
        "Me siento seguro dentro de las instalaciones de la escuela.",
        "Las relaciones entre compañeros son respetuosas.",
        "Los profesores están disponibles para resolver dudas.",
        "Me siento parte de la comunidad escolar.",
    ]),
}
# Media del rasgo latente (escala 1–5) por turno y dimensión.
MEDIAS = {("Matutino", "Evaluación"): 3.9, ("Vespertino", "Evaluación"): 2.7,
          ("Matutino", "Ambiente"): 3.6, ("Vespertino", "Ambiente"): 3.4}


def _likert(latente: float, rng: random.Random) -> int:
    return max(1, min(5, round(latente + rng.gauss(0, 0.6))))


def main() -> None:
    rng = random.Random(SEMILLA)
    columnas = ["id_respondente", "turno", "semestre", "genero"]
    columnas += [f"{dim}_item{k}" for dim, (_, items) in DIMENSIONES.items() for k in range(1, len(items) + 1)]
    filas = []
    for i in range(1, 61):
        turno = "Matutino" if i % 2 else "Vespertino"
        fila = [f"R{i:04d}", turno, str(rng.randint(1, 9)), rng.choice(["femenino", "masculino"])]
        for dim, (_, items) in DIMENSIONES.items():
            latente = rng.gauss(MEDIAS[(turno, dim)], 0.8)
            fila += [str(_likert(latente, rng)) for _ in items]
        filas.append(fila)

    with (SALIDA / "enc_10_turno_respondido.csv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([columnas, *filas])

    lineas = [
        "=" * 70,
        "INSTRUMENTO: Encuesta de evaluación y ambiente escolar por turno",
        "ID: enc_10",
        "Fuente: SINTÉTICO — generado con tools/data_synthesis/generar_enc_10_turno.py",
        "=" * 70,
        "",
        "INSTRUCCIONES:",
        "Lee cada afirmación y marca la opción que mejor describe tu experiencia",
        "utilizando la siguiente escala:",
        "",
        "  1 = Totalmente en desacuerdo",
        "  2 = En desacuerdo",
        "  3 = Ni de acuerdo ni en desacuerdo",
        "  4 = De acuerdo",
        "  5 = Totalmente de acuerdo",
        "",
        "DATOS GENERALES: turno (matutino o vespertino), semestre y género.",
        "",
    ]
    n = 0
    for _dim, (seccion, items) in DIMENSIONES.items():
        lineas += [f"--- {seccion} ---", ""]
        for texto in items:
            n += 1
            lineas += [f"{n}. {texto}", "   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5", ""]
    (SALIDA / "enc_10_turno_original.txt").write_text("\n".join(lineas), encoding="utf-8")

    metadata = {
        "titulo": "Encuesta de evaluación y ambiente escolar por turno",
        "tipo": "encuesta",
        "fuente": "sintetico",
        "n_respondentes": len(filas),
        "n_items": n,
        "tipo_escala": "likert_1_5",
        "dimensiones": ["Evaluación del aprendizaje", "Ambiente escolar"],
        "variables_contexto": ["turno", "semestre", "genero"],
        "parametros_estadisticos": {"semilla": SEMILLA, "medias_latentes": {f"{t}/{d}": m for (t, d), m in MEDIAS.items()},
                                    "ruido_item": 0.6, "dispersion_latente": 0.8},
        "proposito": "Probar consultas por grupo (turno) en el chat RAG.",
    }
    (SALIDA / "enc_10_turno_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"enc_10 generado en {SALIDA}")


if __name__ == "__main__":
    main()
