"""
verificar_coherencia.py — ¿las preguntas que no son Likert dependen del respondente?

Compara dos generaciones de las encuestas (modelo «uniforme» v1.0 y «coherente» v1.1, misma
semilla) y, para cada pregunta con regla en config/coherencia_encuestas.json, mide si la
relación declarada aparece en los datos:

  - factores: correlación de Spearman entre la respuesta (Sí = 1, posición en «orden»,
    número o cantidad de opciones marcadas) y la suma ponderada de los factores. Con el
    modelo uniforme debe salir ≈ 0; con el coherente, con el signo esperado (positivo).
  - cortes: % de respuestas que caen en el tramo correcto del número (debe ser 100 %).
  - mapa: % de Sí/opción esperada por grupo (p. ej. beca → Sí).
Además comprueba que los ítems Likert y los datos de contexto son idénticos en ambos modelos.

Uso:
  python tools/data_synthesis/quality/verificar_coherencia.py <dir_uniforme> <dir_coherente> [--md salida.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from generators.encuesta_generator import INSTRUMENT_DEFS, TIPOS_ADICIONALES, EncuestaGenerator  # noqa: E402

REGLAS = json.loads((AQUI.parent / "config" / "coherencia_encuestas.json").read_text(encoding="utf-8"))
_BOOL = {"tiene_beca", "primera_generacion"}


def _spearman(a, b) -> float:
    ra, rb = pd.Series(a).rank(), pd.Series(b).rank()
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def _factor(df: pd.DataFrame, defn: dict, nombre: str, columnas_likert: list[str]) -> np.ndarray:
    if nombre == "likert":
        return df[columnas_likert].mean(axis=1).to_numpy()
    if nombre.startswith("dimension:"):
        dim = nombre.removeprefix("dimension:")
        cols = [c for c in columnas_likert if c.startswith(dim[:15].replace(" ", "_") + "_item")]
        return df[cols].mean(axis=1).to_numpy()
    if nombre.startswith("pregunta:"):
        return pd.to_numeric(df[EncuestaGenerator._columna(nombre.removeprefix("pregunta:"))]).to_numpy()
    serie = df[nombre]
    return (serie.astype(str) == "True").astype(float).to_numpy() if nombre in _BOOL else serie.to_numpy(dtype=float)


def _combinado(df, defn, pesos, likert) -> np.ndarray:
    total = np.zeros(len(df))
    for nombre, peso in pesos.items():
        x = _factor(df, defn, nombre, likert)
        total += float(peso) * (x - x.mean()) / (x.std() or 1)
    return total


def _codigo(tipo: str, q: dict, regla: dict, valores: pd.Series) -> np.ndarray:
    if tipo == "si_no":
        return (valores == "Sí").astype(float).to_numpy()
    if tipo == "opcion_multiple":
        orden = regla.get("orden") or q["opciones"]
        return valores.map({o: i for i, o in enumerate(orden)}).to_numpy(dtype=float)
    if tipo == "escala_numerica":
        return pd.to_numeric(valores).to_numpy(dtype=float)
    raise ValueError(tipo)


def evaluar(dir_unif: Path, dir_coh: Path) -> list[dict]:
    filas = []
    for enc_id, defn in INSTRUMENT_DEFS.items():
        if enc_id not in REGLAS:
            continue
        u = pd.read_csv(dir_unif / "encuestas" / f"{enc_id}_respondido.csv")
        c = pd.read_csv(dir_coh / "encuestas" / f"{enc_id}_respondido.csv")
        likert = [col for col in c.columns if "_item" in col]
        extras = {EncuestaGenerator._columna(q["texto"]) for t in TIPOS_ADICIONALES for q in defn["preguntas_adicionales"].get(t, [])}
        comunes = [col for col in c.columns if col not in extras]
        identicos = u[comunes].equals(c[comunes])
        for tipo in TIPOS_ADICIONALES:
            for q in defn["preguntas_adicionales"].get(tipo, []):
                regla = REGLAS[enc_id].get(q["texto"])
                if not regla:
                    continue
                col = EncuestaGenerator._columna(q["texto"])
                fila = {"instrumento": enc_id, "tipo": tipo, "pregunta": q["texto"], "likert_y_contexto_identicos": identicos}
                if "cortes" in regla:
                    num = _factor(c, defn, regla["variable"], likert)
                    orden = regla.get("orden") or q["opciones"]
                    esperado = [orden[sum(1 for k in regla["cortes"] if v >= k)] for v in num]
                    ok_c = float(np.mean(np.array(esperado) == c[col].to_numpy()))
                    ok_u = float(np.mean(np.array(esperado) == u[col].to_numpy()))
                    fila.update(criterio=f"tramo correcto de {regla['variable']}", uniforme=round(ok_u, 3), coherente=round(ok_c, 3))
                elif "mapa" in regla:
                    var = c[regla["variable"]].astype(str)
                    objetivo = "Sí" if tipo == "si_no" or "Sí" in q["opciones"] else None
                    if objetivo:
                        partes = {g: round(float((c[col][var == g] == objetivo).mean()), 3) for g in sorted(var.unique())}
                        partes_u = {g: round(float((u[col][var == g] == objetivo).mean()), 3) for g in sorted(var.unique())}
                        fila.update(criterio=f"% «Sí» por {regla['variable']}", uniforme=partes_u, coherente=partes)
                    else:
                        coincide = lambda df: float(np.mean([  # noqa: E731
                            (regla["mapa"].get(g) or regla["mapa"]["*"]) == r or r in (regla["mapa"].get(g) or regla["mapa"]["*"])
                            for g, r in zip(var, df[col])]))
                        fila.update(criterio=f"respuesta posible según {regla['variable']}", uniforme=round(coincide(u), 3), coherente=round(coincide(c), 3))
                elif tipo == "seleccion_multiple":
                    res = {}
                    for nombre, r in regla["opciones"].items():
                        if not r.get("factores"):
                            continue
                        f = _combinado(c, defn, r["factores"], likert)
                        res[nombre] = (round(_spearman(f, u[col].str.contains(nombre, regex=False)), 3),
                                       round(_spearman(f, c[col].str.contains(nombre, regex=False)), 3))
                    fila.update(criterio="Spearman(factores, opción marcada) por opción",
                                uniforme={k: v[0] for k, v in res.items()}, coherente={k: v[1] for k, v in res.items()})
                elif tipo == "jerarquizacion":
                    res = {}
                    for nombre, r in regla["opciones"].items():
                        f = _combinado(c, defn, r["factores"], likert)
                        pos = lambda df: -df[col].str.split(", ").map(lambda l: l.index(nombre)).to_numpy(dtype=float)  # noqa: E731
                        res[nombre] = (round(_spearman(f, pos(u)), 3), round(_spearman(f, pos(c)), 3))
                    fila.update(criterio="Spearman(factores, lugar en el orden; 1.º = alto)",
                                uniforme={k: v[0] for k, v in res.items()}, coherente={k: v[1] for k, v in res.items()})
                elif tipo == "abierta":
                    f = _combinado(c, defn, regla["factores"], likert)
                    nivel = {t: i for i, n in enumerate(["baja", "media", "alta"]) for t in q["plantillas"][n]}
                    fila.update(criterio="Spearman(factores, tono de la respuesta)",
                                uniforme=round(_spearman(f, u[col].map(nivel)), 3), coherente=round(_spearman(f, c[col].map(nivel)), 3))
                elif regla.get("factores"):
                    f = _combinado(c, defn, regla["factores"], likert)
                    fila.update(criterio="Spearman(factores, respuesta)",
                                uniforme=round(_spearman(f, _codigo(tipo, q, regla, u[col])), 3),
                                coherente=round(_spearman(f, _codigo(tipo, q, regla, c[col])), 3))
                elif tipo == "escala_numerica":  # sin factores: solo media y desviación
                    fila.update(criterio=f"media (objetivo {regla.get('media')})",
                                uniforme=round(float(pd.to_numeric(u[col]).mean()), 1),
                                coherente=round(float(pd.to_numeric(c[col]).mean()), 1))
                else:  # solo proporciones
                    orden = regla.get("orden") or q["opciones"]
                    fila.update(criterio="proporciones por opción (objetivo: " + ", ".join(str(p) for p in regla["proporciones"]) + ")",
                                uniforme=[round(float((u[col] == o).mean()), 2) for o in orden],
                                coherente=[round(float((c[col] == o).mean()), 2) for o in orden])
                filas.append(fila)
    return filas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("uniforme", type=Path)
    ap.add_argument("coherente", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()
    filas = evaluar(a.uniforme, a.coherente)
    lineas = ["| Instrumento | Tipo | Pregunta | Criterio | Uniforme (v1.0) | Coherente (v1.1) |", "|---|---|---|---|---|---|"]
    for f in filas:
        lineas.append(f"| {f['instrumento']} | {f['tipo']} | {f['pregunta'][:70]} | {f['criterio']} | {f['uniforme']} | {f['coherente']} |")
    lineas.append("")
    lineas.append(f"Likert y contexto idénticos en ambos modelos: {all(f['likert_y_contexto_identicos'] for f in filas)}")
    texto = "\n".join(lineas)
    print(texto)
    if a.md:
        a.md.write_text(texto + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
