"""Acuerdo entre los juicios de relevancia del autor (`recuperacion_oro.json`) y los de la investigadora (hoja
llenada de `crear_hoja.py`), 9 nov 2026.

Cada par (pregunta, elemento del instrumento) es una decisión binaria: relevante o no. Sobre todas las decisiones se
calcula el acuerdo observado y la kappa de Cohen; por pregunta, si los dos marcaron exactamente lo mismo y si
comparten al menos un elemento. Escribe además `oro_investigadora.json`, en el formato de `recuperacion_oro.json`,
para recalcular hit@k y MRR con `tools/rag/medir_recuperacion.py`.

Uso (desde la raíz del repositorio):
    .venv\\Scripts\\python.exe tools\\rag\\relevancia\\comparar.py [hoja.xlsx]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[2]
ORO = RAIZ / "tools" / "rag" / "recuperacion_oro.json"
FICHA = "ficha"


def _ids(texto) -> set[str]:
    valores = {v.strip().lower() for v in re.split(r"[,;\s]+", str(texto or "")) if v.strip()}
    valores.discard("ninguno")
    return {"encabezado" if v == FICHA else v for v in valores}


def _kappa(pares: list[tuple[bool, bool]]) -> tuple[float, float]:
    n = len(pares)
    observado = sum(a == b for a, b in pares) / n
    pa = sum(a for a, _ in pares) / n
    pb = sum(b for _, b in pares) / n
    esperado = pa * pb + (1 - pa) * (1 - pb)
    return observado, (observado - esperado) / (1 - esperado) if esperado < 1 else 1.0


def main() -> None:
    hoja = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "juicios_relevancia_para_llenar.xlsx"
    libro = load_workbook(hoja, data_only=True)
    oro = json.loads(ORO.read_text(encoding="utf-8"))
    autor = {c["id"]: {o.lower() for o in c["oro"]} for c in oro["casos"]}

    # Elementos buscables de cada instrumento: las filas de su hoja.
    elementos: dict[str, set[str]] = {}
    for nombre in libro.sheetnames:
        if nombre not in ("Instrucciones", "Juicios"):
            ids = {str(f[0]).strip().lower() for f in libro[nombre].iter_rows(min_row=4, values_only=True) if f[0]}
            elementos[nombre] = {"encabezado" if i == FICHA else i for i in ids}

    investigadora: dict[str, set[str]] = {}
    instrumento: dict[str, str] = {}
    for fila in libro["Juicios"].iter_rows(min_row=2, values_only=True):
        if fila[0]:
            investigadora[str(fila[0])] = _ids(fila[3])
            instrumento[str(fila[0])] = str(fila[1])

    sin_llenar = [c for c, v in investigadora.items() if not v]
    pares, iguales, comparten, diferencias = [], 0, 0, []
    for caso, suyos in investigadora.items():
        if not suyos:
            continue
        mios = autor[caso]
        for e in elementos[instrumento[caso]]:
            pares.append((e in mios, e in suyos))
        iguales += mios == suyos
        comparten += bool(mios & suyos)
        if mios != suyos:
            diferencias.append({"caso": caso, "autor": sorted(mios), "investigadora": sorted(suyos)})

    n = len(investigadora) - len(sin_llenar)
    observado, kappa = _kappa(pares) if pares else (0.0, 0.0)
    resumen = {
        "preguntas_juzgadas": n, "sin_llenar": sin_llenar,
        "decisiones": len(pares), "acuerdo_observado": round(observado, 3), "kappa_cohen": round(kappa, 3),
        "preguntas_identicas": iguales, "preguntas_con_al_menos_uno_en_comun": comparten,
        "diferencias": diferencias,
    }
    (AQUI / "acuerdo.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    suyo = {**oro, "descripcion": "Juicios de relevancia de la investigadora (hoja de tools/rag/relevancia).",
            "casos": [{**c, "oro": sorted(investigadora[c["id"]])} for c in oro["casos"] if investigadora.get(c["id"])]}
    (AQUI / "oro_investigadora.json").write_text(json.dumps(suyo, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Preguntas juzgadas: {n} (sin llenar: {len(sin_llenar)})")
    print(f"Decisiones (pregunta × elemento): {len(pares)}; acuerdo {observado:.1%}; kappa de Cohen {kappa:.3f}")
    print(f"Preguntas con los mismos fragmentos: {iguales} de {n}; con al menos uno en común: {comparten} de {n}")
    print("Detalle en acuerdo.json; juicios de la investigadora en oro_investigadora.json")


if __name__ == "__main__":
    main()
