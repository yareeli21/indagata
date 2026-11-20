"""Vuelve a medir, con la limpieza actual, el ruido «no contemplado» de los tres tipos de instrumento.

El 2 nov se generaron tres archivos con errores reales que la limpieza no tenía contemplados y se midió qué pasaba
con cada uno (`resultado_medido` en su JSON de verdad):
  - encuesta enc_06 (`ensuciar_enc_06_no_contemplado.py`): números escritos de otra forma, categorías mal escritas o
    con sinónimo, «Otro: …», Sí/No codificado, acentos rotos y errores de estructura (casi duplicados, fila corrida,
    fila de promedios, segunda fila de encabezado);
  - prueba pru_03 (`ensuciar_pru_03.py`): respuestas escritas de otra forma, letras de otro alfabeto, alumno repetido
    con otro ID, reactivo vacío, fila corrida y encabezado repetido;
  - entrevista ent_11 (`ensuciar_ent_11_no_contemplado.py`): encabezados y pies repetidos, anotaciones, etiquetas
    inconsistentes, acentos rotos, minuto en la etiqueta, muletillas no listadas, arranques en falso y errores de
    reconocimiento de voz.
El 5 nov se implementaron reglas para parte de esos casos. Este script corre los motores actuales (puros, sin red ni
base de datos: no crea instrumentos) con las decisiones sugeridas y dice, por cada inyección, si hoy queda bien.
Como esos archivos guiaron las reglas nuevas, esta medición dice qué se cubrió, no cuánto generaliza.

Uso (desde la raíz del repo):
    .venv\\Scripts\\python.exe tools/limpieza/remedir_no_contemplado.py
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ / "services" / "cleaning-service"), str(RAIZ)]

from services.motores import Entrada, obtener  # noqa: E402

SINTETICOS = RAIZ / "storage" / "instrumentos_sinteticos"


def limpiar(ruta: Path, tipo: str) -> tuple[Any, Any]:
    entrada = Entrada(1, tipo, ruta.name, ruta.suffix.lower(), ruta.read_bytes())
    motor = obtener(tipo, ruta.suffix.lower())
    automatico = motor.automatica(entrada)
    return automatico, motor.aplicar(entrada, automatico, {h.id: h.sugerida for h in automatico.hallazgos if h.sugerida})


def _num(valor: str) -> float | None:
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def _igual(a: str, b: str) -> bool:
    na, nb = _num(a), _num(b)
    return (na is not None and na == nb) or str(a).strip() == str(b).strip()


def encuesta(verdad: dict[str, Any]) -> list[dict[str, Any]]:
    base = list(csv.reader(io.StringIO((SINTETICOS / "encuestas" / verdad["base"]).read_text(encoding="utf-8"))))
    columnas = base[0]
    _, final = limpiar(SINTETICOS / "encuestas" / verdad["archivo"], "encuesta")
    # La limpieza quita el ID (columna ajena) y conserva el orden de los respondentes: R0001 es la fila 0.
    desfase = len(columnas) - len(final.encabezados)
    salida = []
    for v in verdad["detalle"]:
        if "columna" not in v:
            continue
        fila = int(v["id"][1:]) - 1
        valor = final.filas[fila][columnas.index(v["columna"]) - desfase]
        if v["tipo"] == "otro_con_texto":
            ok = valor.strip().lower().startswith("otro") and ":" not in valor
        else:
            ok = _igual(valor, v["esperado"])
        salida.append({"tipo": v["tipo"], "inyectado": v["inyectado"], "esperado": v["esperado"], "obtenido": valor, "ok": ok})
    n_base = len(base) - 1
    est = verdad["estructura"]
    fila_corrida = int(est["fila_desplazada"]["id"][1:])
    # La celda que faltaba («genero») no se puede recuperar: la fila está bien si todo lo demás quedó en su columna.
    faltante = columnas.index(re.search(r"«(\w+)»", est["fila_desplazada"]["nota"]).group(1)) - desfase
    # Las escalas ordinales con etiqueta («Muy deficiente» … «Excelente») salen codificadas 1–5 en todas las filas.
    codificadas = {k for k in range(len(final.encabezados))
                   if all(_num(f[k]) is not None for f in final.filas if f[k]) and any(_num(r[k + desfase]) is None for r in base[1:])}
    corrida_ok = all(_igual(a, b) for k, (a, b) in enumerate(zip(final.filas[fila_corrida - 1], base[fila_corrida][desfase:]))
                     if k != faltante and k not in codificadas)
    salida += [
        {"tipo": "casi_duplicado", "inyectado": f"{len(est['casi_duplicado'])} copias con una celda distinta",
         "esperado": f"{n_base} respondentes", "obtenido": f"{len(final.filas)} respondentes", "ok": len(final.filas) == n_base},
        {"tipo": "fila_desplazada", "inyectado": est["fila_desplazada"]["id"],
         "esperado": "cada valor en su columna (la celda faltante queda vacía)",
         "obtenido": "en su columna" if corrida_ok else "corrida", "ok": corrida_ok},
        {"tipo": "fila_de_promedios", "inyectado": "fila «Promedio»", "esperado": "descartada",
         "obtenido": "descartada" if not any(f and "romedio" in " ".join(f) for f in final.filas) else "presente",
         "ok": not any("romedio" in " ".join(f) for f in final.filas)},
        {"tipo": "segunda_fila_de_encabezado", "inyectado": "fila con el texto de las preguntas", "esperado": "usada como texto",
         "obtenido": "descartada" if not any("Pregunta 1" in f for f in final.filas) else "contada como respondente",
         "ok": not any("Pregunta 1" in f for f in final.filas)},
    ]
    return salida


_ALFABETO = {"А": "A", "Ｃ": "C", "В": "B", "С": "C"}


def prueba(verdad: dict[str, Any]) -> list[dict[str, Any]]:
    _, final = limpiar(SINTETICOS / "pruebas" / verdad["archivo"], "prueba_estandarizada")
    celdas = {(f[0], f[1]): f for f in final.filas}
    salida = []
    for v in verdad["detalle"]:
        if "id_alumno" not in v:
            continue
        f = celdas.get((v["id_alumno"], v["pregunta"]))
        respuesta, estado = (f[2], f[3]) if f else ("(sin fila)", "")
        if v["tipo"] == "no_respuesta_escrita_distinto":
            ok = estado == "NR"
        elif v["tipo"] == "letra_parecida_otro_alfabeto":
            ok = estado == "valida" and respuesta == _ALFABETO.get(v["inyectado"], v["inyectado"])
        elif v["tipo"] == "letra_con_signo":
            ok = estado == "valida" and respuesta.upper() == re.sub(r"[^A-Za-z]", "", v["inyectado"]).upper()  # el documento final la escribe en mayúscula
        elif v["tipo"] == "misma_letra_dos_veces":
            ok = estado == "valida" and respuesta == v["inyectado"][0]
        else:
            ok = estado == "valida" and respuesta == v["original"]
        salida.append({"tipo": v["tipo"], "inyectado": v["inyectado"], "esperado": v["esperado"],
                       "obtenido": f"{respuesta} ({estado})", "ok": ok})
    base = list(csv.reader(io.StringIO((SINTETICOS / "pruebas" / verdad["base"]).read_text(encoding="utf-8"))))
    n_base, est = len(base) - 1, verdad["estructura"]
    alumnos = {f[0] for f in final.filas}
    vacio = est["columna_reactivo_vacia"].split(":")[0]
    nr_vacio = [f for f in final.filas if f[1] == vacio]
    corrido = est["fila_desplazada"].split(":")[0]
    fila_base = next(r for r in base if r[0] == corrido)
    reactivos = [c for c in base[0] if c.startswith("pru_")]
    bien_corrido = all(celdas.get((corrido, c), ["", "", ""])[2] == fila_base[base[0].index(c)] for c in reactivos if c != vacio)
    copias = [c["copia"] for c in est["alumno_repetido_con_id_distinto"]]
    copias_vivas = [c for c in copias if any(f[0] == c and f[3] != "nula" for f in final.filas)]
    salida += [
        {"tipo": "columna_reactivo_vacia", "inyectado": vacio, "esperado": "se conserva con 100 % NR",
         "obtenido": f"{len(nr_vacio)} filas: {sum(f[3] == 'NR' for f in nr_vacio)} NR y {sum(f[4] == 'duplicado' for f in nr_vacio)} "
                     "de alumnos duplicados", "ok": bool(nr_vacio) and all(f[3] == "NR" or f[4] == "duplicado" for f in nr_vacio)},
        {"tipo": "fila_desplazada", "inyectado": corrido, "esperado": "respuestas en su reactivo",
         "obtenido": "en su reactivo" if bien_corrido else "corridas", "ok": bien_corrido},
        {"tipo": "alumno_repetido_con_id_distinto", "inyectado": ", ".join(copias), "esperado": "no se cuentan como alumnos nuevos",
         "obtenido": f"siguen contando: {', '.join(copias_vivas) or 'ninguna'}", "ok": not copias_vivas},
        {"tipo": "encabezado_repetido", "inyectado": "fila igual al encabezado", "esperado": "descartada",
         "obtenido": "contada como alumno" if "id_respondente" in alumnos else "descartada", "ok": "id_respondente" not in alumnos},
        {"tipo": "conteo_de_alumnos", "inyectado": "", "esperado": f"{n_base} alumnos",
         "obtenido": f"{len(alumnos)} alumnos ({len(alumnos) - n_base} de más)", "ok": len(alumnos) == n_base, "resumen": True},
    ]
    return salida


_ORIGINAL = re.compile(r"original: «(.+?)»")


def entrevista(verdad: dict[str, Any]) -> list[dict[str, Any]]:
    carpeta = SINTETICOS / "entrevistas"
    _, final = limpiar(carpeta / verdad["archivo_con_ruido"], "entrevista")
    _, control = limpiar(carpeta / verdad["archivo_limpio"], "entrevista")
    texto = "\n".join(f[-1] for f in final.filas)
    roles = {h["nombre"]: h["rol"] for h in final.especifico["hablantes"]}
    salida = []
    for v in verdad["detalle"]:
        original = (m.group(1) if (m := _ORIGINAL.search(v.get("nota", ""))) else None)
        if v["tipo"] in ("encabezado_repetido", "pie_repetido", "marca_de_tiempo_no_contemplada"):
            ok, obtenido = v["inyectado"] not in texto, "quitado" if v["inyectado"] not in texto else "sigue en el texto"
        elif v["tipo"] == "etiqueta_inconsistente":
            etq = v["inyectado"].rstrip(":")
            rol = "entrevistado" if etq.lower().startswith("entrevistad") and not etq.lower().endswith("or") else "entrevistador"
            ok, obtenido = roles.get(etq) == rol, f"«{etq}» → {roles.get(etq)}"
        elif original:
            limpio = original.rstrip(".")
            ok = limpio in texto and v["inyectado"] not in texto
            obtenido = "restaurado" if ok else ("sigue: «" + v["inyectado"] + "»" if v["inyectado"] in texto else "cambiado")
        else:
            ok, obtenido = v["inyectado"] not in texto, ""
        salida.append({"tipo": v["tipo"], "inyectado": v["inyectado"], "esperado": original or "quitado", "obtenido": obtenido, "ok": ok})
    salida.append({"tipo": "turnos", "inyectado": "", "esperado": f"{len(control.filas)} turnos",
                   "obtenido": f"{len(final.filas)} turnos", "ok": len(final.filas) == len(control.filas), "resumen": True})
    return salida


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--salida", type=Path, default=RAIZ / "evidencias" / "limpieza_2026-11-07")
    args = p.parse_args()
    casos = [("encuesta", SINTETICOS / "encuestas" / "enc_06_ruido_no_contemplado.json", encuesta),
             ("prueba", SINTETICOS / "pruebas" / "pru_03_ruido_no_contemplado.json", prueba),
             ("entrevista", SINTETICOS / "entrevistas" / "ent_11_ruido_no_contemplado.json", entrevista)]
    resultado: dict[str, Any] = {}
    for nombre, ruta, funcion in casos:
        verdad = json.loads(ruta.read_text(encoding="utf-8"))
        filas = funcion(verdad)
        por_tipo: dict[str, dict[str, Any]] = {}
        for f in filas:
            if f.get("resumen"):
                continue
            t = por_tipo.setdefault(f["tipo"], {"inyectados": 0, "bien_hoy": 0, "2_nov": (verdad["resultado_medido"]["por_tipo"]
                                                                                       .get(f["tipo"], ""))})
            t["inyectados"] += 1
            t["bien_hoy"] += f["ok"]
        resultado[nombre] = {"archivo": verdad.get("archivo") or verdad.get("archivo_con_ruido"), "por_tipo": por_tipo,
                             "resumen": [f for f in filas if f.get("resumen")], "detalle": filas}
        print(f"\n== {nombre} ({resultado[nombre]['archivo']})")
        for tipo, t in por_tipo.items():
            print(f"  {tipo:32} {t['bien_hoy']}/{t['inyectados']}   (2 nov: {str(t['2_nov'])[:70]})")
        for f in filas:
            if f.get("resumen"):
                print(f"  {f['tipo']:32} {f['obtenido']} (esperado {f['esperado']})")
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "no_contemplado_hoy.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
