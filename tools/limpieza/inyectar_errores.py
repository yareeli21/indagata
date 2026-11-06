"""Inyecta errores conocidos en un instrumento y guarda la verdad, para medir la limpieza (Pruebas, Fase 2).

Cada error se inyecta en filas o celdas distintas (sin traslapes) con una semilla fija, así la verdad es exacta:
  - encuesta (CSV): filas duplicadas, valores fuera de escala, «No sé / NA», una columna muy incompleta,
    encuestados casi sin responder, respuestas en línea recta y columnas de plataforma (marca temporal, IP);
  - prueba (CSV): ID repetido, respuestas múltiples («A,B»), caracteres ilegibles («?»), caracteres inválidos
    («Z») y filas vacías.

Las filas se numeran desde 1 (sin el encabezado), igual que los hallazgos de la limpieza. Junto al archivo
con errores se guarda una copia del original sin cambios: la verificación procesa los dos y compara la
diferencia con lo inyectado (grupo de control).

Uso:
    python tools/limpieza/inyectar_errores.py encuesta storage/instrumentos_sinteticos/encuestas/enc_11_respondido.csv
    python tools/limpieza/inyectar_errores.py prueba storage/instrumentos_sinteticos/pruebas/pru_01_respondido.csv
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
SEMILLA = 7


def _tomar(disponibles: list[int], n: int, rng: random.Random) -> list[int]:
    elegidas = sorted(rng.sample(disponibles, n))
    for i in elegidas:
        disponibles.remove(i)
    return elegidas


def encuesta(df: pd.DataFrame, rng: random.Random) -> tuple[pd.DataFrame, dict]:
    df = df.copy().astype(object)
    likert = [c for c in df.columns if c.endswith(tuple(f"_item{i}" for i in range(1, 10)))]
    bloque = [c for c in likert if c.startswith(likert[0].rsplit("_item", 1)[0])]
    preguntas = [c for c in df.columns[12:]]  # después de las columnas de contexto del método A
    libres = list(range(len(df)))
    verdad: dict = {}

    filas = _tomar(libres, 6, rng)
    celdas = []
    for k, i in enumerate(filas):
        col = likert[k % len(likert)]
        valor = [0, 7, 9][k % 3]
        df.at[i, col] = valor
        celdas.append({"fila": i + 1, "columna": col, "valor": valor})
    verdad["fuera_de_rango"] = celdas

    filas = _tomar(libres, 8, rng)
    celdas = []
    for k, i in enumerate(filas):
        col = likert[(k + 3) % len(likert)]
        valor = ["No sé", "NA", "N/A", "No aplica"][k % 4]
        df.at[i, col] = valor
        celdas.append({"fila": i + 1, "columna": col, "valor": valor})
    verdad["no_respuestas"] = celdas

    incompleta = next(c for c in preguntas if c.startswith("Cuál_es_tu_principal_medio"))
    vaciar = rng.sample(range(len(df)), int(0.7 * len(df)))
    df.loc[vaciar, incompleta] = ""
    verdad["columna_incompleta"] = [{"columna": incompleta, "vacias": len(vaciar)}]

    filas = _tomar(libres, 4, rng)
    for i in filas:
        for col in preguntas[int(0.15 * len(preguntas)):]:
            df.at[i, col] = ""
    verdad["encuestados_incompletos"] = [i + 1 for i in filas]

    filas = _tomar(libres, 5, rng)
    for i in filas:
        for col in bloque:
            df.at[i, col] = 3
    verdad["linea_recta"] = [i + 1 for i in filas]

    # Duplicados al final: copias exactas de filas que no recibieron ningún otro error.
    originales = _tomar(libres, 5, rng)
    copias = df.iloc[originales].copy()
    inicio = len(df)
    df = pd.concat([df, copias], ignore_index=True)
    verdad["duplicados"] = [inicio + k + 1 for k in range(len(copias))]

    df.insert(0, "Marca temporal", [f"2026/10/{10 + i % 15:02d} 10:{i % 60:02d}:00" for i in range(len(df))])
    df.insert(1, "Dirección IP", [f"189.203.{i // 250}.{i % 250}" for i in range(len(df))])
    verdad["columnas_ajenas"] = ["Marca temporal", "Dirección IP"]
    return df, verdad


def prueba(df: pd.DataFrame, rng: random.Random) -> tuple[pd.DataFrame, dict]:
    df = df.copy().astype(object)
    reactivos = [c for c in df.columns if c.split("_")[0] == "pru"]
    om = [c for c in reactivos if df[c].astype(str).isin(["A", "B", "C", "D"]).all()]
    libres = list(range(len(df)))
    verdad: dict = {}

    def celdas(n: int, valor_de) -> list[dict]:  # noqa: ANN001
        salida = []
        for k, i in enumerate(_tomar(libres, n, rng)):
            col = om[(k * 3) % len(om)]
            valor = valor_de(k)
            df.at[i, col] = valor
            salida.append({"fila": i + 1, "columna": col, "valor": valor})
        return salida

    verdad["respuesta_multiple"] = celdas(6, lambda k: ["A,B", "BC", "A/D"][k % 3])
    verdad["ilegible"] = celdas(5, lambda k: ["?", "#", "*"][k % 3])
    verdad["caracter_invalido"] = celdas(4, lambda k: ["Z", "E"][k % 2])

    repetidas = _tomar(libres, 3, rng)
    fuentes = _tomar(libres, 3, rng)
    for r, f in zip(repetidas, fuentes):
        df.at[r, "id_respondente"] = df.at[f, "id_respondente"]
    verdad["id_duplicado"] = sorted({str(df.at[f, "id_respondente"]) for f in fuentes})

    filas = _tomar(libres, 2, rng)
    for i in filas:
        df.loc[i, :] = ""
    verdad["filas_vacias"] = len(filas)
    return df, verdad


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("tipo", choices=["encuesta", "prueba"])
    p.add_argument("archivo", type=Path)
    p.add_argument("--salida", type=Path, default=RAIZ / "evidencias" / "limpieza_2026-10-24")
    args = p.parse_args()
    rng = random.Random(SEMILLA)
    base = pd.read_csv(args.archivo, dtype=str, keep_default_na=False)
    con_errores, verdad = (encuesta if args.tipo == "encuesta" else prueba)(base, rng)
    args.salida.mkdir(parents=True, exist_ok=True)
    nombre = args.archivo.stem.replace("_respondido", "")
    base.to_csv(args.salida / f"{nombre}_control.csv", index=False)
    con_errores.to_csv(args.salida / f"{nombre}_con_errores.csv", index=False)
    verdad = {"tipo": args.tipo, "base": str(args.archivo.relative_to(RAIZ)) if args.archivo.is_absolute() else str(args.archivo),
              "semilla": SEMILLA, "filas_base": len(base), "filas_con_errores": len(con_errores), "errores": verdad}
    (args.salida / f"{nombre}_verdad.json").write_text(json.dumps(verdad, ensure_ascii=False, indent=1), encoding="utf-8")
    resumen = {k: (len(v) if isinstance(v, list) else v) for k, v in verdad["errores"].items()}
    print(f"{nombre}: {resumen} → {args.salida.relative_to(RAIZ) if args.salida.is_absolute() else args.salida}")


if __name__ == "__main__":
    main()
