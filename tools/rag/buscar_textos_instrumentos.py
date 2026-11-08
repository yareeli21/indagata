"""¿Hay textos de los instrumentos de prueba en el código cambiado? (8 nov 2026, evaluación final del chat).

Toma del documento final vigente de cada instrumento (`storage/json/<id>/`) los textos de pregunta, opción y ficha de
15 caracteres o más, y los busca, sin acentos ni mayúsculas, en los archivos de código que cambiaron desde un commit.
Las respuestas de las personas, los intercambios y los KPIs no se buscan: no son texto del instrumento.

Una coincidencia no es por sí sola un problema: puede ser un comentario que documenta el caso que motivó una regla,
una etiqueta genérica («Totalmente de acuerdo») o un mensaje del propio sistema («No especificado»). Hay que revisar
cada una; lo que no puede haber es un texto que cambie el comportamiento (en un prompt, un ejemplo o una regla).

Uso, desde la raíz del repositorio:
    python tools/rag/buscar_textos_instrumentos.py --ids 127,129,130 --desde 265246a~1 [--sin-pruebas]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
_OMITIR = {"respuestas", "respondentes", "alumnos", "turnos", "intercambios", "transcripcion", "nlp", "kpis"}
_SUFIJOS = {".py", ".ts", ".tsx", ".yaml", ".yml", ".json"}
_DATOS_DE_LA_EVALUACION = ("baterias_chat", "recuperacion_oro")  # contienen las preguntas a propósito


def normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return " ".join(sin_acentos.split())


def documento_vigente(id_crudo: str) -> Path:
    archivos = sorted((RAIZ / "storage" / "json" / id_crudo).glob("*documento_final.json"),
                      key=lambda p: int(p.name.split("__")[0]))
    if not archivos:
        raise SystemExit(f"No hay documento final del instrumento {id_crudo} en storage/json/{id_crudo}/")
    return archivos[-1]


def textos_de(valor, id_crudo: str, salida: dict[str, tuple[str, str]]) -> None:
    if isinstance(valor, dict):
        for clave, v in valor.items():
            if clave not in _OMITIR:
                textos_de(v, id_crudo, salida)
    elif isinstance(valor, list):
        for v in valor:
            textos_de(v, id_crudo, salida)
    elif isinstance(valor, str) and len(valor) >= 15 and " " in valor.strip():
        salida.setdefault(normalizar(valor), (id_crudo, valor))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", required=True, help="id_crudo de los instrumentos, separados por coma")
    ap.add_argument("--desde", required=True, help="commit de referencia: se revisan los archivos cambiados desde él")
    ap.add_argument("--sin-pruebas", action="store_true", help="no revisar las carpetas tests/")
    a = ap.parse_args()

    textos: dict[str, tuple[str, str]] = {}
    for id_crudo in a.ids.split(","):
        textos_de(json.loads(documento_vigente(id_crudo).read_text(encoding="utf-8")), id_crudo, textos)
    cambiados = subprocess.run(["git", "diff", "--name-only", a.desde, "HEAD", "--", "services", "shared", "tools",
                                "pixel-perfect-pixel/src"], capture_output=True, text=True, cwd=RAIZ, check=True)
    archivos = [RAIZ / f for f in cambiados.stdout.split()
                if (RAIZ / f).exists() and Path(f).suffix in _SUFIJOS and not any(x in f for x in _DATOS_DE_LA_EVALUACION)
                and not (a.sin_pruebas and "/tests/" in f)]
    print(f"{len(textos)} textos de los instrumentos {a.ids}; {len(archivos)} archivos cambiados desde {a.desde}")
    total = 0
    for archivo in archivos:
        contenido = normalizar(archivo.read_text(encoding="utf-8", errors="ignore"))
        for normal, (id_crudo, original) in textos.items():
            if normal in contenido:
                total += 1
                print(f"  {archivo.relative_to(RAIZ).as_posix()}: [{id_crudo}] {original[:80]}")
    print(f"coincidencias: {total}")


if __name__ == "__main__":
    main()
