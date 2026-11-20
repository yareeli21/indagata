"""Mide la limpieza de entrevistas contra errores inyectados con verdad conocida (Pruebas, Y.2.3).

Mismo diseño que `inyectar_errores.py` + `verificar_limpieza.py` para encuestas y pruebas, pero el motor de
entrevistas se llama directo (es puro: sin red ni base de datos), así que no se crea ningún instrumento.

1. Toma una entrevista limpia con varios participantes (por defecto ent_02, 30 entrevistas, 600 turnos).
2. Inyecta, con semilla fija (7) y en turnos distintos, el ruido que trae una transcripción real:
   marcas de tiempo, números de página, encabezados repetidos, separadores, folios, palabras partidas por guion,
   letras espaciadas (copiado de PDF), caracteres invisibles, acentos rotos (mojibake), minuto pegado a la
   etiqueta, etiquetas de hablante inconsistentes, anotaciones del transcriptor, muletillas y saltos de línea CRLF.
3. Limpia el archivo original (control) y el archivo con errores con las decisiones sugeridas, y compara turno a
   turno contra lo esperado (el control, más las muletillas cuando la decisión es conservarlas).

Mide, por tipo de error, cuántas inyecciones quedaron corregidas (recall), y en global cuántos turnos sin errores
salieron alterados (daño al contenido: la contraparte de la precisión) y cuántas palabras se perdieron o sobraron.
Con `--muletillas quitar` repite la limpieza con esa decisión.

Uso (desde la raíz del repo):
    .venv\\Scripts\\python.exe tools/limpieza/medir_limpieza_entrevista.py
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
SERVICIO = RAIZ / "services" / "cleaning-service"
sys.path[:0] = [str(SERVICIO), str(RAIZ)]

from services.motores import Entrada, obtener  # noqa: E402

SEMILLA = 7
_TURNO = re.compile(r"^(?P<etq>P\d+|R):\s(?P<texto>.*)$")
_BLOQUE = re.compile(r"^RESPONDENTE:\s*(\S+)")
# cp1252 no define estos bytes; un programa «descuidado» los deja como el carácter latin-1 del mismo código.
_SIN_CP1252 = {0x81, 0x8D, 0x8F, 0x90, 0x9D}


def _mojibake(texto: str) -> str:
    """UTF-8 leído como Windows-1252 y guardado otra vez: «educación» → «educaciÃ³n»."""
    return "".join(chr(b) if b in _SIN_CP1252 else bytes([b]).decode("cp1252") for b in texto.encode("utf-8"))


def inyectar(base: str, rng: random.Random) -> tuple[str, list[dict[str, Any]]]:
    lineas = base.split("\n")
    turnos: list[int] = []        # índice de línea de cada turno, en orden
    participante: dict[int, str] = {}
    actual = ""
    for i, l in enumerate(lineas):
        if m := _BLOQUE.match(l):
            actual = m.group(1)
        elif _TURNO.match(l):
            participante[i] = actual
            turnos.append(i)
    k_de_linea = {i: k for k, i in enumerate(turnos)}
    respuestas = [i for i in turnos if lineas[i].startswith("R:")]
    preguntas = [i for i in turnos if not lineas[i].startswith("R:")]
    usadas: set[int] = set()
    verdad: list[dict[str, Any]] = []
    despues: dict[int, list[str]] = {}   # líneas que se insertan después de un turno

    def tomar(pool: list[int], n: int, filtro=lambda i: True) -> list[int]:  # noqa: ANN001
        libres = [i for i in pool if i not in usadas and filtro(i)]
        elegidas = sorted(rng.sample(libres, n))
        usadas.update(elegidas)
        return elegidas

    def anotar(tipo: str, i: int, inyectado: str) -> None:
        verdad.append({"tipo": tipo, "turno": k_de_linea[i] + 1, "participante": participante[i], "inyectado": inyectado})

    def partes(i: int) -> tuple[str, str]:
        m = _TURNO.match(lineas[i])
        return m.group("etq"), m.group("texto")

    # 1. Marcas de tiempo: entre corchetes y al inicio de la línea (exportación de grabadoras y de Word).
    for n, i in enumerate(tomar(turnos, 12)):
        marca = f"[00:{(7 * n + 3) % 60:02d}:{(13 * n) % 60:02d}]" if n < 8 else f"00:{(7 * n) % 60:02d}:{(11 * n) % 60:02d}"
        lineas[i] = f"{marca} {lineas[i]}"
        anotar("marca_de_tiempo", i, marca)
    # 2–5. Líneas sueltas entre turnos: números de página, encabezado repetido, separadores y folios.
    for n, i in enumerate(tomar(turnos, 6)):
        pie = f"Página {n + 2} de 40" if n % 2 else f"- {n + 2} -"
        despues.setdefault(i, []).append(pie)
        anotar("numero_de_pagina", i, pie)
    encabezado = "Universidad del Valle — Transcripción de entrevistas, semestre 2026-1"
    for i in tomar(turnos, 5):
        despues.setdefault(i, []).append(encabezado)
        anotar("encabezado_repetido", i, encabezado)
    for n, i in enumerate(tomar(turnos, 4)):
        sep = "-" * 30 if n % 2 else "*" * 20
        despues.setdefault(i, []).append(sep)
        anotar("separador", i, sep)
    for n, i in enumerate(tomar(turnos, 3)):
        folio = f"Folio: ENT-02-{40 + n:04d}"
        despues.setdefault(i, []).append(folio)
        anotar("identificador", i, folio)

    # 6. Palabras partidas por guion de fin de línea (texto copiado de un PDF o de Word con guiones).
    def palabra(i: int, minimo: int) -> re.Match[str] | None:
        _, texto = partes(i)
        candidatas = [m for m in re.finditer(r"(?<=[a-záéíóúñ] )[a-záéíóúñ]{%d,}\b" % minimo, texto)]
        return rng.choice(candidatas) if candidatas else None

    for i in tomar(respuestas, 6):
        m = palabra(i, 9)
        etq, texto = partes(i)
        corte = len(m.group(0)) // 2
        partida = f"{m.group(0)[:corte]}-\n{m.group(0)[corte:]}"
        lineas[i] = f"{etq}: {texto[:m.start()]}{partida}{texto[m.end():]}"
        anotar("palabra_partida", i, partida.replace("\n", "⏎"))
    # 7. Letras espaciadas (PDF con tipografía espaciada). La palabra anterior nunca es de una letra.
    for i in tomar(respuestas, 4):
        m = palabra(i, 6)
        etq, texto = partes(i)
        espaciada = " ".join(m.group(0))
        lineas[i] = f"{etq}: {texto[:m.start()]}{espaciada}{texto[m.end():]}"
        anotar("letras_espaciadas", i, espaciada)
    # 8. Caracteres invisibles: espacio de ancho cero dentro de una palabra y espacio duro.
    for i in tomar(turnos, 6):
        etq, texto = partes(i)
        m = re.search(r"[a-záéíóúñ]{6,}", texto)
        texto = texto[:m.start() + 3] + "​" + texto[m.start() + 3:]
        texto = texto.replace(" ", " ", 1)
        lineas[i] = f"{etq}: {texto}"
        anotar("invisibles", i, "U+200B y U+00A0")
    # 9. Acentos rotos en una entrevista completa (pegada desde un programa con otra codificación).
    bloques = sorted({participante[i] for i in turnos})
    roto = rng.choice([b for b in bloques if not any(participante[i] == b and i in usadas for i in turnos)])
    for i in turnos:
        if participante[i] == roto and re.search(r"[áéíóúñ¿¡]", lineas[i]):
            usadas.add(i)
            lineas[i] = _mojibake(lineas[i])
            anotar("acentos_rotos", i, lineas[i][:40])
    # 10. Minuto pegado a la etiqueta del hablante («R (min 12):»).
    for n, i in enumerate(tomar(respuestas, 4)):
        _, texto = partes(i)
        etq = f"R (min {12 + 5 * n}):"
        lineas[i] = f"{etq} {texto}"
        anotar("minuto_en_etiqueta", i, etq)
    # 11. Etiquetas inconsistentes: otra persona transcribió algunos turnos con el nombre del rol.
    for i in tomar(preguntas, 2):
        _, texto = partes(i)
        lineas[i] = f"Entrevistador: {texto}"
        anotar("etiqueta_inconsistente", i, "Entrevistador:")
    for i in tomar(respuestas, 3):
        _, texto = partes(i)
        lineas[i] = f"Entrevistado: {texto}"
        anotar("etiqueta_inconsistente", i, "Entrevistado:")
    # 12. Anotaciones del transcriptor dentro de las respuestas.
    notas = ["[inaudible]", "(risas)", "[pausa larga]", "(silencio)", "[hablan al mismo tiempo]", "[inaudible 00:14:05]",
             "(suspira)", "[ruido]"]
    for nota, i in zip(notas, tomar(respuestas, len(notas))):
        etq, texto = partes(i)
        corte = texto.find(". ")
        corte = corte + 1 if corte > 0 else len(texto)
        lineas[i] = f"{etq}: {texto[:corte]} {nota}{texto[corte:]}"
        anotar("anotacion_transcriptor", i, nota)
    # 13. Muletillas al inicio de la respuesta.
    for muletilla, i in zip(["Eh, ", "Mmm... ", "Em, ", "Ehm, ", "Eh, ", "Mmm, "], tomar(respuestas, 6)):
        etq, texto = partes(i)
        lineas[i] = f"{etq}: {muletilla}{texto}"
        anotar("muletilla", i, muletilla.strip())

    salida: list[str] = []
    for i, l in enumerate(lineas):
        salida.append(l)
        for extra in despues.get(i, []):
            salida += ["", extra, ""]
    # 14. Saltos de línea de Windows en todo el archivo.
    return "\r\n".join(salida), verdad


def limpiar(contenido: bytes, nombre: str, decisiones: dict[str, str] | None = None) -> tuple[Any, Any]:
    entrada = Entrada(1, "entrevista", nombre, ".txt", contenido)
    motor = obtener("entrevista", ".txt")
    automatico = motor.automatica(entrada)
    sugeridas = {h.id: h.sugerida for h in automatico.hallazgos if h.sugerida}
    return automatico, motor.aplicar(entrada, automatico, {**sugeridas, **(decisiones or {})})


def _norm(texto: str) -> str:
    return " ".join(texto.split())


def _alinear(esperado: list[list[str]], obtenido: list[list[str]]) -> dict[int, int | None]:
    """Turno esperado (0-based) → turno obtenido; por orden si coinciden en número, si no con difflib."""
    if len(esperado) == len(obtenido):
        return {k: k for k in range(len(esperado))}
    sm = difflib.SequenceMatcher(a=[_norm(f[-1]) for f in esperado], b=[_norm(f[-1]) for f in obtenido], autojunk=False)
    mapa: dict[int, int | None] = {k: None for k in range(len(esperado))}
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and a1 - a0 == b1 - b0):
            for d in range(a1 - a0):
                mapa[a0 + d] = b0 + d
    return mapa


def comparar(control: Any, final: Any, verdad: list[dict[str, Any]], muletillas: str) -> dict[str, Any]:
    esperado = [list(f) for f in control.filas]
    if muletillas == "conservar":
        for v in verdad:
            if v["tipo"] == "muletilla":
                fila = esperado[v["turno"] - 1]
                fila[-1] = f"{v['inyectado']} {fila[-1]}"
    obtenido = final.filas
    mapa = _alinear(esperado, obtenido)

    def correcto(k: int) -> bool:
        j = mapa.get(k)
        return j is not None and _norm(obtenido[j][-1]) == _norm(esperado[k][-1]) and obtenido[j][-2] == esperado[k][-2]

    por_tipo: dict[str, dict[str, Any]] = {}
    for v in verdad:
        k = v["turno"] - 1
        v["corregido"] = correcto(k)
        if not v["corregido"]:
            j = mapa.get(k)
            v["obtenido"] = obtenido[j][-2:] if j is not None else None
            v["esperado"] = esperado[k][-2:]
        t = por_tipo.setdefault(v["tipo"], {"inyectados": 0, "corregidos": 0})
        t["inyectados"] += 1
        t["corregidos"] += v["corregido"]
    for t in por_tipo.values():
        t["recall"] = round(t["corregidos"] / t["inyectados"], 3)

    con_error = {v["turno"] - 1 for v in verdad}
    sin_error = [k for k in range(len(esperado)) if k not in con_error]
    danados = [k for k in sin_error if not correcto(k)]
    perdidas = sobrantes = 0
    for k, j in mapa.items():
        a = _norm(esperado[k][-1]).split()
        b = _norm(obtenido[j][-1]).split() if j is not None else []
        for op, a0, a1, b0, b1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if op in ("delete", "replace"):
                perdidas += a1 - a0
            if op in ("insert", "replace"):
                sobrantes += b1 - b0
    return {
        "turnos_esperados": len(esperado),
        "turnos_obtenidos": len(obtenido),
        "turnos_correctos": sum(correcto(k) for k in range(len(esperado))),
        "turnos_sin_error_alterados": len(danados),
        "ejemplos_alterados": [{"turno": k + 1, "esperado": esperado[k][-1][:160],
                                "obtenido": obtenido[mapa[k]][-1][:160] if mapa.get(k) is not None else None} for k in danados[:5]],
        "palabras_esperadas": sum(len(_norm(f[-1]).split()) for f in esperado),
        "palabras_perdidas": perdidas,
        "palabras_sobrantes": sobrantes,
        "por_tipo": por_tipo,
        "recall_global": round(sum(t["corregidos"] for t in por_tipo.values()) / len(verdad), 3),
    }


def _hallazgo(automatico: Any, tipo: str) -> int:
    return sum((h.detalle or {}).get("total", 0) for h in automatico.hallazgos if h.tipo == tipo)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base", type=Path, default=RAIZ / "storage" / "instrumentos_sinteticos" / "entrevistas" / "ent_02_respondido.txt")
    p.add_argument("--salida", type=Path, default=RAIZ / "evidencias" / "limpieza_2026-11-07")
    args = p.parse_args()
    base = args.base.read_text(encoding="utf-8")
    con_errores, verdad = inyectar(base, random.Random(SEMILLA))
    nombre = args.base.stem.replace("_respondido", "")
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / f"{nombre}_control.txt").write_text(base, encoding="utf-8")
    (args.salida / f"{nombre}_con_errores.txt").write_bytes(con_errores.encode("utf-8"))

    auto_c, control = limpiar(base.encode("utf-8"), f"{nombre}_control.txt")
    auto_e, final = limpiar(con_errores.encode("utf-8"), f"{nombre}_con_errores.txt")
    detalle = json.loads(json.dumps(verdad))  # comparar() anota en cada inyección si quedó corregida
    resultado = comparar(control, final, detalle, "conservar")
    _, final_q = limpiar(con_errores.encode("utf-8"), f"{nombre}_con_errores.txt", {"muletillas": "quitar"})
    _, control_q = limpiar(base.encode("utf-8"), f"{nombre}_control.txt", {"muletillas": "quitar"})
    resultado_q = comparar(control_q, final_q, json.loads(json.dumps(verdad)), "quitar")

    n_notas = sum(v["tipo"] == "anotacion_transcriptor" for v in verdad)
    n_mul = sum(v["tipo"] == "muletilla" for v in verdad)
    deteccion = {
        "anotacion_transcriptor": {"inyectadas": n_notas, "detectadas_nuevas": _hallazgo(auto_e, "anotaciones_transcriptor")
                                   - _hallazgo(auto_c, "anotaciones_transcriptor")},
        "muletilla": {"inyectadas": n_mul, "detectadas_nuevas": _hallazgo(auto_e, "muletillas") - _hallazgo(auto_c, "muletillas")},
        "roles": [{"hablante": h["nombre"], "rol": h["rol"]} for h in final.especifico["hablantes"]],
        "avisos": auto_e.avisos,
        "transformaciones": [{"regla": t["regla"], "afectados": t.get("afectados")} for t in auto_e.transformaciones],
    }
    salida = {"base": str(args.base.relative_to(RAIZ)), "semilla": SEMILLA, "inyecciones": len(verdad),
              "decisiones_sugeridas": resultado, "muletillas_quitadas": {k: resultado_q[k] for k in
              ("turnos_correctos", "turnos_sin_error_alterados", "palabras_perdidas", "palabras_sobrantes", "recall_global")}
              | {"muletilla": resultado_q["por_tipo"].get("muletilla")},
              "deteccion": deteccion, "detalle": detalle}
    (args.salida / f"{nombre}_verdad.json").write_text(json.dumps(verdad, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.salida / f"{nombre}_resultado.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    r = resultado
    print(f"{nombre}: {len(verdad)} inyecciones; turnos {r['turnos_obtenidos']}/{r['turnos_esperados']}, "
          f"correctos {r['turnos_correctos']}, sin error alterados {r['turnos_sin_error_alterados']}, "
          f"palabras perdidas {r['palabras_perdidas']} y sobrantes {r['palabras_sobrantes']} de {r['palabras_esperadas']}")
    print(f"{'error':25} {'iny':>4} {'corr':>5} {'recall':>7}")
    for tipo, t in r["por_tipo"].items():
        print(f"{tipo:25} {t['inyectados']:>4} {t['corregidos']:>5} {t['recall']:>7}")
    print(f"{'GLOBAL':25} {len(verdad):>4} {sum(t['corregidos'] for t in r['por_tipo'].values()):>5} {r['recall_global']:>7}")
    print("Detección:", {k: v for k, v in deteccion.items() if k in ("anotacion_transcriptor", "muletilla", "roles")})
    print("Muletillas quitadas:", salida["muletillas_quitadas"])


if __name__ == "__main__":
    main()
