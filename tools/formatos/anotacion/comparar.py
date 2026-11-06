"""Compara la anotación de la investigadora con la del autor (referencia) y con el sistema.

Lee `anotacion_para_llenar.xlsx` ya llenada, la referencia de cada corpus y el análisis del sistema
(documento final de los instrumentos indicados). Reporta el acuerdo de la postura en cada par
(exactitud y kappa de Cohen) y si la frase que ella copió quedó en el núcleo del sistema.

Uso (con la app levantada): python tools/formatos/anotacion/comparar.py --estudiantes 100 --docentes 105
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parents[1] / "rag"))
import procesar_instrumento as proc  # noqa: E402
from verificar_entrevistas import _kappa, _norm  # noqa: E402

TEMAS = {"Estudiantes: vida universitaria": "entrevistas", "Docentes: evaluación": "entrevistas_docentes"}
_POSTURA = {"sí": "si", "si": "si", "no": "no", "ambivalente": "ambivalente", "no aplica": "no_aplica"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--estudiantes", type=int, required=True)
    ap.add_argument("--docentes", type=int, required=True)
    a = ap.parse_args()
    api = proc.Api("admin@indagata.com", "admin123")
    ids = {"entrevistas": a.estudiantes, "entrevistas_docentes": a.docentes}
    sistema = {}
    for corpus, id_crudo in ids.items():
        doc = api.pedir("GET", f"{proc.GATEWAY}/conocimiento/{id_crudo}/documento/json")
        for e in doc["entrevistas"]:
            for i in e["intercambios"]:
                k = int(re.sub(r"\D", "", i["pregunta_id"].rsplit("-", 1)[-1]))
                sistema[(corpus, e["participante"].rsplit("-", 1)[-1], k)] = i.get("analisis") or {}
    referencia = {(c, r["persona"], r["pregunta"]): r for c in ids
                  for r in json.loads((AQUI.parent / "corpus" / c / "referencia.json").read_text(encoding="utf-8"))}

    filas = list(load_workbook(AQUI / "anotacion_para_llenar.xlsx")["Anotación"].iter_rows(min_row=2, values_only=True))
    ella, autor, sis, frases_en_nucleo, n_frases = [], [], [], 0, 0
    for tema, persona, n, _p, _r, postura, frase, _c in filas:
        if not postura:
            continue
        clave = (TEMAS[tema], persona, int(n))
        ella.append(_POSTURA.get(str(postura).strip().lower(), str(postura)))
        autor.append(referencia[clave]["postura"])
        sis.append(sistema.get(clave, {}).get("postura", "—"))
        if frase:
            n_frases += 1
            frases_en_nucleo += _norm(str(frase)) in _norm(sistema.get(clave, {}).get("nucleo", ""))

    def acuerdo(x: list[str], y: list[str]) -> str:
        return f"{sum(a == b for a, b in zip(x, y))}/{len(x)} ({100 * sum(a == b for a, b in zip(x, y)) / len(x):.1f} %), κ = {_kappa(x, y)}"

    print(f"Respuestas anotadas: {len(ella)} de {len(filas)}")
    print("Investigadora vs autor:  ", acuerdo(ella, autor))
    print("Investigadora vs sistema:", acuerdo(ella, sis))
    print("Autor vs sistema:        ", acuerdo(autor, sis))
    if n_frases:
        print(f"Su frase quedó en el núcleo del sistema: {frases_en_nucleo}/{n_frases}")


if __name__ == "__main__":
    main()
