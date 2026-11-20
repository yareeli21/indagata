"""Evaluación del chat con las baterías de la investigadora (7 nov 2026): antes y después de cada fase.

Corre `baterias_chat.json` contra el chat (los turnos de un caso en la misma conversación, cada caso en una
conversación nueva) y guarda, por turno: la pregunta, la respuesta, la intención o plan, las fuentes y los fragmentos
recuperados, el tiempo, si cayó a plantilla y dos medidas de fidelidad sin modelo juez:

  K-Precision        proporción de las palabras con contenido de la respuesta que aparecen en el contexto que recibió
                     el modelo (Adlakha et al., 2024, TACL 12:681–699, doi:10.1162/tacl_a_00667). 1 = todo lo que dice
                     está en los datos; baja si agrega palabras que no están (o si parafrasea con sinónimos).
  Cifras con respaldo  de las cifras de la respuesta, cuántas aparecen en el contexto.

Con `--desde-log` no pregunta nada: arma la corrida con consultas ya hechas en el chat (por ejemplo, la prueba manual
de la investigadora), emparejando cada turno con la primera consulta de ese instrumento con el mismo texto. Así la
línea base usa sus respuestas reales y sus calificaciones, sin volver a cargar el modelo.

La calificación contra el «Debe» de cada caso (cumple / parcial / no cumple) se lee de `--calificacion` (JSON
{"ENC-01": {"cumple": "parcial", "nota": "…"}}), que se llena revisando las respuestas; el resumen la cruza con la
calificación humana guardada en `rag_calificacion`.

Memoria (7 nov): con gemma3:4b, en un equipo de 8 GB para Docker, la memoria de Ollama crece con cada consulta hasta que
el sistema mata el proceso del modelo (cada una o dos horas). `--reiniciar-ollama-cada N` reinicia el contenedor de Ollama
cada N casos (y lo calienta con una consulta corta antes de seguir); un caso cuyo turno salió «modelo no disponible» se
repite una vez después de reiniciar. Los reinicios quedan en `reinicios.log` de la carpeta de salida.

Uso (con la app levantada):
    python tools/rag/evaluar_chat.py --ids enc=127,pru=130,ent=129 --salida evidencias/chat_2026-11-07_antes --desde-log 2271-2371
    python tools/rag/evaluar_chat.py --ids enc_control=61,ent_control=60 --conjunto control --salida evidencias/chat_2026-11-07_control_antes
    python tools/rag/evaluar_chat.py --ids enc=127,pru=130,ent=129 --salida evidencias/chat_2026-11-08_despues --reiniciar-ollama-cada 15
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
GATEWAY = "http://localhost:8006"

_PALABRA = re.compile(r"[a-zñ]+|\d+(?:[.,]\d+)?")
_CITA = re.compile(r"\[(?:Fuente|Glosario|Ayuda|Fuente KPI)[^\]]*\]")
_CIFRA = re.compile(r"\d+(?:[.,]\d+)?")
# Palabras funcionales y de la redacción que no dicen nada sobre los datos (K-Precision cuenta solo contenido).
_VACIAS = set("""
para como pero porque cuando donde desde hasta entre sobre segun según tiene tienen tenia este esta estos estas
ese esa esos esas aquel aquella cual cuales quien quienes cuyo todo todos toda todas otro otra otros otras mismo misma
muy mas más menos tambien también solo sólo ademas además entonces asi así aunque mientras sino cada algun alguna
algunos algunas ningun ninguna nada respondio respondieron respondieron respuesta respuestas pregunta preguntas
datos resultado calculado fuente fuentes indica indican muestra muestran registra registrados registradas segun
hay sido fueron esta están estan será sera puede pueden podria podría seria sería dijo dice menciona mencionan
""".split())


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> list[str]:
    return [w for w in _PALABRA.findall(normalizar(_CITA.sub(" ", texto)))
            if (w[0].isdigit() or len(w) > 3) and w not in _VACIAS]


def k_precision(respuesta: str, contextos: list[str]) -> float | None:
    """Palabras con contenido de la respuesta que están en el contexto / total (None si no hay contexto o palabras)."""
    propias = _palabras(respuesta)
    if not propias or not contextos:
        return None
    vocabulario = set(_palabras("\n".join(contextos)))
    return round(sum(w in vocabulario for w in propias) / len(propias), 3)


def cifras_respaldo(respuesta: str, contextos: list[str]) -> tuple[int, int]:
    def cifras(t: str) -> set[float]:
        return {float(c.replace(",", ".")) for c in _CIFRA.findall(_CITA.sub(" ", t))}
    propias, base = cifras(respuesta), cifras("\n".join(contextos))
    return sum(c in base for c in propias), len(propias)


def plantilla(fila: dict) -> str | None:
    """Mensaje fijo o de respaldo que se mostró en lugar de una redacción (como services/indicadores.py)."""
    motivo = str(fila.get("motivo") or "")
    plan = fila.get("plan") or {}
    verif = (plan.get("verificacion") or {}).get("resultado")
    if motivo.startswith("regla:"):
        return motivo.split(":", 1)[1]
    if "aclaracion_ajena" in motivo:
        return "aclaracion_ajena"
    if fila.get("ruta") == "aclaracion" or motivo == "plan:aclaracion":
        return "aclaracion"
    if verif == "respaldo":
        return "calculo_literal"
    if verif == "frase_dato":  # ronda posterior (8 nov): solo la oración calculada, sin el contexto del modelo
        return "frase_calculada"
    if motivo.endswith(":literal"):
        return "cita_literal"
    if verif == "modelo_no_disponible" or "No se pudo contactar" in str(fila.get("respuesta") or ""):
        return "modelo_no_disponible"
    if fila.get("ruta") == "ayuda":
        return "ayuda"
    if fila.get("decision_dominio") in ("fuera", "privacidad", "manipulacion", "sin_informacion"):
        return fila["decision_dominio"]
    return None


def leer_log(ids: list[int]) -> dict[int, dict]:
    """Filas de rag_log (con la calificación humana) por psql dentro del contenedor de Postgres."""
    if not ids:
        return {}
    sql = ("select coalesce(json_agg(row_to_json(x)), '[]') from (select l.rag_log_id, l.pregunta, l.respuesta, l.ruta, "
           "l.motivo, l.plan, l.tiempos, l.latencia_ms, l.score_max, l.contexto_usado, l.salida, l.decision_dominio, "
           "l.instrumentos, c.calificacion, c.comentario from tt_rag.rag_log l left join tt_rag.rag_calificacion c "
           f"using (rag_log_id) where l.rag_log_id in ({','.join(map(str, ids))})) x")
    salida = subprocess.run(["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "indagata_db",
                             "-At", "-c", sql], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", check=True)
    return {f["rag_log_id"]: f for f in json.loads(salida.stdout.strip() or "[]")}


def _rango_log(rango: str) -> list[dict]:
    desde, hasta = (int(x) for x in rango.split("-"))
    return sorted(leer_log(list(range(desde, hasta + 1))).values(), key=lambda f: f["rag_log_id"])


def _emparejar(casos: list[dict], ids: dict[str, str], filas: list[dict]) -> dict[tuple[str, int], int]:
    """(caso, turno) → rag_log_id: la primera consulta no usada del mismo instrumento con el mismo texto. Si una
    pregunta se repitió (p. ej. porque el modelo se cayó), se usa la última repetición calificada."""
    usadas: set[int] = set()
    pares: dict[tuple[str, int], int] = {}
    for c in casos:
        for t, texto in enumerate(c["turnos"]):
            candidatas = [f for f in filas if f["rag_log_id"] not in usadas and normalizar(f["pregunta"]).strip(" ?¿")
                          == normalizar(texto).strip(" ?¿") and ids[c["instrumento"]] in (f.get("instrumentos") or [])]
            calificadas = [f for f in candidatas if f.get("calificacion") is not None]
            elegida = (calificadas or candidatas or [None])[0]
            if elegida:
                usadas.update(f["rag_log_id"] for f in candidatas if f["rag_log_id"] <= elegida["rag_log_id"])
                pares[(c["id"], t)] = elegida["rag_log_id"]
    return pares


def _entrar(http: httpx.Client, cab: dict, email: str, password: str) -> None:
    """Pone en `cab` un token nuevo (caduca a los 60 minutos; la corrida completa dura más)."""
    token = http.post(f"{GATEWAY}/auth/login", json={"email": email, "password": password}).json()["access_token"]
    cab["Authorization"] = f"Bearer {token}"


def _preguntar(http: httpx.Client, cab: dict, texto: str, alcance: list[str], historial: list[dict],
               entrar=None) -> tuple[dict, float]:
    cuerpo = {"pregunta": texto, "instrumentoIds": alcance, "stream": False, "usarCache": False,
              "calcularMetricas": False, "historial": historial[-8:]}
    inicio = time.monotonic()
    for intento in range(3):
        try:
            r = http.post(f"{GATEWAY}/rag/chat", json=cuerpo, headers=cab)
            r.raise_for_status()
            return r.json(), time.monotonic() - inicio
        except httpx.HTTPError as exc:
            print(f"   reintento {intento + 1}: {exc}", file=sys.stderr)
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401 and entrar:
                entrar()  # el token caducó: se pide otro y se repite sin esperar
                continue
            time.sleep(10)
    return {"respuesta": "", "error": "sin respuesta"}, time.monotonic() - inicio


def reiniciar_ollama(bitacora: Path, motivo: str) -> None:
    """Reinicia el contenedor de Ollama y espera a que el modelo responda (lo carga con una consulta corta)."""
    inicio = time.monotonic()
    subprocess.run(["docker", "compose", "restart", "ollama"], cwd=RAIZ, capture_output=True, check=False)
    modelo = ""
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if linea.startswith("OLLAMA_MODEL="):
            modelo = linea.split("=", 1)[1].strip()
    for _ in range(60):
        try:
            r = httpx.post("http://127.0.0.1:11434/api/generate", timeout=300,
                           json={"model": modelo, "prompt": "hola", "stream": False, "keep_alive": -1,
                                 "options": {"num_predict": 1, "num_ctx": 4096}})
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(5)
    with bitacora.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} reinicio de Ollama ({motivo}), {time.monotonic() - inicio:.0f} s\n")


def _turno(fila: dict | None, texto: str, segundos: float | None) -> dict:
    if not fila:
        return {"pregunta": texto, "respuesta": None, "nota": "no se hizo esta consulta"}
    plan = fila.get("plan") or {}
    contextos = [str(c.get("texto") or "") for c in fila.get("contexto_usado") or []]
    respuesta = str(fila.get("respuesta") or "")
    con, total = cifras_respaldo(respuesta, contextos)
    return {
        "pregunta": texto,
        "rag_log_id": fila["rag_log_id"],
        "respuesta": respuesta,
        "intencion": (plan.get("plan") or {}).get("intencion"),
        "plan": plan.get("plan"),
        # 8 nov: el plan tal como lo escribió el modelo y si el sistema lo dejó igual (desde la Fase 5).
        "plan_modelo": plan.get("plan_modelo"),
        "plan_modelo_sin_cambios": plan.get("plan_modelo_sin_cambios"),
        "correcciones": plan.get("correcciones"),
        "verificacion": (plan.get("verificacion") or {}).get("resultado"),
        "ruta": fila.get("ruta"),
        "motivo": fila.get("motivo"),
        "plantilla": plantilla(fila),
        "fuentes": [f.get("titulo") for f in (fila.get("salida") or {}).get("fuentes") or []],
        "fragmentos": [{"seccion": c.get("seccion"), "etiqueta": c.get("etiqueta"), "score": c.get("score")}
                       for c in fila.get("contexto_usado") or []],
        "segundos": round(segundos if segundos is not None else (fila.get("latencia_ms") or 0) / 1000, 1),
        "tiempos_ms": fila.get("tiempos"),
        "k_precision": k_precision(respuesta, contextos) if not plantilla(fila) else None,
        "cifras_con_respaldo": [con, total],
        "calificacion_humana": fila.get("calificacion"),
        "comentario_humano": fila.get("comentario"),
    }


def _p90(valores: list[float]) -> float:
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(0.9 * (len(v) - 1))))] if v else 0.0


def resumen(casos: list[dict], resultados: dict[str, dict], calificacion: dict, titulo: str) -> str:
    turnos = [t for r in resultados.values() for t in r["turnos"] if t.get("respuesta") is not None]
    planes = [t for t in turnos if t.get("plan") is not None]
    validos = [t for t in planes if t.get("intencion") not in (None, "aclaracion")]
    plantillas = [t for t in turnos if t.get("plantilla")]
    kp = [t["k_precision"] for t in turnos if t.get("k_precision") is not None]
    cif = [t["cifras_con_respaldo"] for t in turnos if t["cifras_con_respaldo"][1]]
    seg = [t["segundos"] for t in turnos if t.get("segundos")]
    con_modelo = [t for t in planes if t.get("plan_modelo_sin_cambios") is not None]
    sin_cambios = [t for t in con_modelo if t["plan_modelo_sin_cambios"]]
    cumple = {k: sum(1 for c in casos if (calificacion.get(c["id"]) or {}).get("cumple") == k) for k in ("cumple", "parcial", "no")}
    lineas = [f"# {titulo}", "",
              f"- Casos: {len(casos)} ({len(turnos)} turnos con respuesta).",
              f"- Contra el «Debe»: **{cumple['cumple']} cumplen**, {cumple['parcial']} parciales, {cumple['no']} no cumplen"
              f"{' (sin calificar: ' + str(len(casos) - sum(cumple.values())) + ')' if len(casos) - sum(cumple.values()) else ''}.",
              f"- Planes válidos (intención distinta de aclaración): {len(validos)} de {len(planes)}"
              f" ({100 * len(validos) / max(1, len(planes)):.1f} %).",
              f"- Caídas a plantilla: {len(plantillas)} de {len(turnos)} ({100 * len(plantillas) / max(1, len(turnos)):.1f} %).",
              *([f"- Plan del modelo usado sin cambios: {len(sin_cambios)} de {len(con_modelo)}"
                 f" ({100 * len(sin_cambios) / len(con_modelo):.1f} %); el resto lo corrigieron la validación, las reglas"
                 " o el hilo de la conversación."] if con_modelo else []),
              f"- K-Precision (sin plantillas): mediana {statistics.median(kp):.2f}, mínimo {min(kp):.2f} (n = {len(kp)})." if kp else "- K-Precision: sin datos.",
              f"- Cifras con respaldo en el contexto: {sum(c[0] for c in cif)} de {sum(c[1] for c in cif)}.",
              f"- Tiempo por turno: mediana {statistics.median(seg):.0f} s, p90 {_p90(seg):.0f} s." if seg else "- Tiempo: sin datos.",
              "", "| Caso | Turno | Pregunta | Intención | Plantilla | K-Prec. | Cifras | s | Humana | Debe |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    humanas = {0: "mal", 1: "parcial", 2: "bien"}
    for c in casos:
        r = resultados.get(c["id"]) or {"turnos": []}
        for i, t in enumerate(r["turnos"], start=1):
            debe = (calificacion.get(c["id"]) or {}).get("cumple", "—") if i == len(r["turnos"]) else ""
            kp_t = "—" if t.get("k_precision") is None else f"{t['k_precision']:.2f}"
            cf = t.get("cifras_con_respaldo") or [0, 0]
            lineas.append(f"| {c['id']} | {i} | {t['pregunta'][:70]} | {t.get('intencion') or '—'} | {t.get('plantilla') or ''} | "
                          f"{kp_t} | {cf[0]}/{cf[1]} | {t.get('segundos', '—')} | "
                          f"{humanas.get(t.get('calificacion_humana'), '—')} | {debe} |")
    notas = [(c["id"], (calificacion.get(c["id"]) or {}).get("nota")) for c in casos if (calificacion.get(c["id"]) or {}).get("nota")]
    if notas:
        lineas += ["", "## Notas de la calificación contra el «Debe»", ""] + [f"- **{i}.** {n}" for i, n in notas]
    return "\n".join(lineas) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", required=True, help="clave=id_crudo, p. ej. enc=127,pru=130,ent=129")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--conjunto", default="casos", choices=["casos", "control", "ciegas"])
    ap.add_argument("--solo", default="", help="IDs de casos separados por coma")
    ap.add_argument("--desde-log", default="", help="rango de rag_log_id ya respondidos, p. ej. 2271-2371")
    ap.add_argument("--calificacion", default="", help="JSON con la calificación contra el «Debe»")
    ap.add_argument("--solo-resumen", action="store_true",
                    help="no pregunta nada: rehace resumen.md con los casos ya guardados en --salida")
    ap.add_argument("--reiniciar-ollama-cada", type=int, default=0,
                    help="reinicia Ollama cada N casos y repite una vez el caso con «modelo no disponible» (0 = nunca)")
    ap.add_argument("--email", default="admin@indagata.com")
    ap.add_argument("--password", default="admin123")
    a = ap.parse_args()

    ids = dict(p.split("=") for p in a.ids.split(","))
    bateria = json.loads((AQUI / "baterias_chat.json").read_text(encoding="utf-8"))
    casos = [c for c in bateria[a.conjunto] if c["instrumento"] in ids and (not a.solo or c["id"] in a.solo.split(","))]
    salida = RAIZ / a.salida
    (salida / "casos").mkdir(parents=True, exist_ok=True)
    resultados: dict[str, dict] = {}

    if a.solo_resumen:
        for c in casos:
            archivo = salida / "casos" / f"{c['id']}.json"
            if archivo.exists():
                resultados[c["id"]] = json.loads(archivo.read_text(encoding="utf-8"))
        casos = [c for c in casos if c["id"] in resultados]
    elif a.desde_log:
        filas = _rango_log(a.desde_log)
        pares = _emparejar(casos, ids, filas)
        por_id = {f["rag_log_id"]: f for f in filas}
        for c in casos:
            resultados[c["id"]] = {**c, "turnos": [_turno(por_id.get(pares.get((c["id"], t), -1)), texto, None)
                                                   for t, texto in enumerate(c["turnos"])]}
    else:
        http = httpx.Client(timeout=httpx.Timeout(connect=10, read=900, write=60, pool=10))
        cab: dict[str, str] = {}

        def entrar() -> None:
            _entrar(http, cab, a.email, a.password)
        entrar()
        bitacora = salida / "reinicios.log"

        def correr_caso(c: dict) -> list[dict]:
            historial: list[dict] = []
            turnos = []
            for texto in c["turnos"]:
                print(f"{c['id']}: {texto[:70]}", flush=True)
                datos, segundos = _preguntar(http, cab, texto, [ids[c["instrumento"]]], historial, entrar)
                fila = leer_log([datos["consultaId"]]).get(datos["consultaId"]) if datos.get("consultaId") else None
                turnos.append(_turno(fila, texto, segundos))
                historial += [{"rol": "usuario", "texto": texto},
                              {"rol": "asistente", "texto": str(datos.get("respuesta") or "")[:4000],
                               "consultaId": datos.get("consultaId")}]
            return turnos

        for n, c in enumerate(casos):
            if a.reiniciar_ollama_cada and n and n % a.reiniciar_ollama_cada == 0:
                reiniciar_ollama(bitacora, f"cada {a.reiniciar_ollama_cada} casos, antes de {c['id']}")
            turnos = correr_caso(c)
            if a.reiniciar_ollama_cada and any(t.get("plantilla") == "modelo_no_disponible" for t in turnos):
                reiniciar_ollama(bitacora, f"{c['id']} salió «modelo no disponible»; se repite")
                turnos = correr_caso(c)
            resultados[c["id"]] = {**c, "turnos": turnos}
            (salida / "casos" / f"{c['id']}.json").write_text(json.dumps(resultados[c["id"]], ensure_ascii=False, indent=1),
                                                              encoding="utf-8")
    for c in casos:
        (salida / "casos" / f"{c['id']}.json").write_text(json.dumps(resultados[c["id"]], ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
    if a.solo:
        # Con --solo se repiten algunos casos; el resumen usa también los que ya estaban en la carpeta.
        casos = [c for c in bateria[a.conjunto] if c["instrumento"] in ids]
        for c in casos:
            archivo = salida / "casos" / f"{c['id']}.json"
            if c["id"] not in resultados and archivo.exists():
                resultados[c["id"]] = json.loads(archivo.read_text(encoding="utf-8"))
        casos = [c for c in casos if c["id"] in resultados]
    calificacion = json.loads((RAIZ / a.calificacion).read_text(encoding="utf-8")) if a.calificacion else {}
    titulo = f"Evaluación del chat: {Path(a.salida).name}"
    (salida / "resumen.md").write_text(resumen(casos, resultados, calificacion, titulo), encoding="utf-8")
    print(f"Listo: {salida / 'resumen.md'}")


if __name__ == "__main__":
    main()
