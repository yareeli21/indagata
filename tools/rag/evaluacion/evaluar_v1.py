"""Evaluación del chat RAG sobre el banco congelado (banco_v1.json), 11 nov 2026.

Tres pasos, cada uno guarda su JSON en tools/rag/evaluacion/resultados/ y escribe un reporte en Markdown:

  recuperacion   Hit@k, MRR@8, nDCG@8 y Recall@8 sobre el ranking de la búsqueda (antes del umbral), búsqueda semántica
                 frente a híbrida, por alcance (instrumento / colección) y con paráfrasis; aceptaciones falsas de las
                 preguntas sin respuesta. Corre dentro del contenedor (scripts/evaluar_recuperacion.py). Gratis.
  chat           Las preguntas al chat de punta a punta (sin caché): decisión (responder / sin información / fuera),
                 falsas aceptaciones y falsos rechazos, exactitud de cifras contra la respuesta esperada (calculada con
                 SQL, sin el chat) y latencia p50/p95. Gratis.
  ragas          RAGAS 0.4.3 sobre las respuestas del paso «chat»: fidelidad, relevancia de la respuesta, precisión del
                 contexto y recall del contexto (este último solo con referencia). Juez: Claude por la API de Anthropic
                 (--juez claude-…, clave en ANTHROPIC_API_KEY del .env) u Ollama (--juez llama3.2:3b). Embeddings:
                 nomic-embed-text en Ollama. Corre en el entorno aislado .venv-ragas (requirements-ragas.txt).

Uso (con la app levantada):
    venv\\Scripts\\python.exe tools\\rag\\evaluacion\\evaluar_v1.py recuperacion
    venv\\Scripts\\python.exe tools\\rag\\evaluacion\\evaluar_v1.py chat [--conjunto prueba|desarrollo|todo]
    .venv-ragas\\Scripts\\python.exe tools\\rag\\evaluacion\\evaluar_v1.py ragas --chat resultados\\chat_<fecha>.json --juez claude-haiku-5-5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
RESULTADOS = AQUI / "resultados"
GATEWAY = os.environ.get("INDAGATA_API", "http://localhost:8006")
OLLAMA = "http://localhost:11434"
EMBEDDINGS = "nomic-embed-text"
CONTENEDOR = "indagata_visualization_service"


def _banco() -> dict[str, Any]:
    return json.loads((AQUI / "banco_v1.json").read_text(encoding="utf-8"))


def _guardar(nombre: str, datos: Any, markdown: str) -> Path:
    RESULTADOS.mkdir(exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M")
    ruta = RESULTADOS / f"{nombre}_{marca}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    ruta.with_suffix(".md").write_text(markdown, encoding="utf-8")
    return ruta


def _f(x: Any, pct: bool = False) -> str:
    if x is None:
        return "—"
    if isinstance(x, (list, tuple)):
        return f"[{_f(x[0])}, {_f(x[1])}]"
    return f"{x * 100:.1f} %" if pct else f"{x:.3f}"


# ── 1. Recuperación ──────────────────────────────────────────────────────────────

def recuperacion(_: argparse.Namespace) -> None:
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    subprocess.run(["docker", "cp", str(AQUI / "banco_v1.json"), f"{CONTENEDOR}:/tmp/banco.json"], check=True, env=env)
    print("Midiendo la recuperación dentro del contenedor (unos minutos)…", flush=True)
    r = subprocess.run(["docker", "exec", "-w", "/app", "-e", "PYTHONPATH=/app", "-e", "HF_HUB_OFFLINE=1", CONTENEDOR,
                        "python", "scripts/evaluar_recuperacion.py", "/tmp/banco.json"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode != 0:
        sys.exit(f"Falló la medición:\n{r.stderr[-2000:]}")
    datos = json.loads(r.stdout)
    print(f"Guardado: {_guardar('recuperacion', datos, reporte_recuperacion(datos))}")


def calibrar(_: argparse.Namespace) -> None:
    """Barrido del umbral de similitud y de la cobertura por palabras con el conjunto de DESARROLLO (no toca el de
    prueba). Corre dentro del contenedor."""
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    subprocess.run(["docker", "cp", str(AQUI / "banco_v1.json"), f"{CONTENEDOR}:/tmp/banco.json"], check=True, env=env)
    print("Calibrando con el conjunto de desarrollo dentro del contenedor…", flush=True)
    r = subprocess.run(["docker", "exec", "-w", "/app", "-e", "PYTHONPATH=/app", "-e", "HF_HUB_OFFLINE=1", CONTENEDOR,
                        "python", "scripts/evaluar_recuperacion.py", "/tmp/banco.json", "--calibrar"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode != 0:
        sys.exit(f"Falló la calibración:\n{r.stderr[-2000:]}")
    datos = json.loads(r.stdout)
    print(f"Guardado: {_guardar('calibracion', datos, reporte_calibracion(datos))}")


def reporte_calibracion(d: dict[str, Any]) -> str:
    act = d["actual"]
    lineas = [f"# Calibración del filtro de relevancia — conjunto de {d['conjunto']}", "",
              f"Valores actuales: `RAG_MIN_SCORE` = {act['umbral']}, `RAG_MIN_COBERTURA` = {act['cobertura']}. Búsqueda "
              "híbrida con el alcance del chat (el instrumento en las preguntas con respuesta; la colección en las demás). "
              "Solo la compuerta de la recuperación: no incluye el planificador ni el clasificador de la zona gris.", "",
              "| Umbral | Cobertura | Con respuesta aceptadas | Fragmento correcto pasa | Falsas aceptaciones | "
              "Decisiones correctas |", "|---|---|---|---|---|---|"]
    for f in sorted(d["tabla"], key=lambda f: (-f["decisiones_correctas"], -f["umbral"], -f["cobertura"])):
        marca = " ← actual" if (f["umbral"], f["cobertura"]) == (act["umbral"], act["cobertura"]) else ""
        lineas.append(f"| {f['umbral']} | {f['cobertura']} | {f['acepta_con_respuesta']}/{f['con_respuesta']} | "
                      f"{f['fragmento_correcto_pasa']}/{f['con_respuesta']} | {f['falsas_aceptaciones']}/{f['sin_respuesta']} "
                      f"| {f['decisiones_correctas']}/{f['total']}{marca} |")
    return "\n".join(lineas) + "\n"


def reporte_recuperacion(d: dict[str, Any]) -> str:
    res = d["resumen"]
    lineas = [f"# Recuperación — banco v1 ({datetime.now():%d/%m/%Y})", "",
              f"Ranking de la búsqueda antes del umbral (umbral del chat: {d['umbral']}; cobertura mínima por palabras: "
              f"{d['cobertura_minima']}). k = {d['k']}. IC 95 %: bootstrap.", ""]
    for conjunto in ("prueba", "desarrollo"):
        lineas += [f"## Conjunto de {conjunto}", "",
                   "| Alcance | Búsqueda | n | Hit@1 | Hit@3 | Hit@5 | Hit@8 (IC 95 %) | MRR@8 (IC 95 %) | nDCG@8 | Recall@8 |",
                   "|---|---|---|---|---|---|---|---|---|---|"]
        for alcance in ("instrumento", "coleccion"):
            for modo in ("semantica", "hibrida"):
                o = res[f"{conjunto}|{alcance}|{modo}"]["originales"]
                if not o:
                    continue
                lineas.append(f"| {alcance} | {modo} | {o['preguntas']} | {_f(o['hit@1'])} | {_f(o['hit@3'])} | "
                              f"{_f(o['hit@5'])} | {_f(o['hit@8'])} {_f(o['ic95_hit@8'])} | {_f(o['rr'])} {_f(o['ic95_mrr'])} | "
                              f"{_f(o['ndcg'])} | {_f(o['recall'])} |")
        lineas += ["", "**Por tipo de instrumento (colección completa):**", "",
                   "| Tipo | Búsqueda | n | Hit@8 | MRR@8 |", "|---|---|---|---|---|"]
        for modo in ("semantica", "hibrida"):
            for tipo, o in res[f"{conjunto}|coleccion|{modo}"]["por_tipo"].items():
                if o:
                    lineas.append(f"| {tipo} | {modo} | {o['preguntas']} | {_f(o['hit@8'])} | {_f(o['rr'])} |")
        lineas += ["", "**Consistencia ante paráfrasis (colección completa):**", "",
                   "| Búsqueda | consultas | Hit@8 | MRR@8 |", "|---|---|---|---|"]
        for modo in ("semantica", "hibrida"):
            o = res[f"{conjunto}|coleccion|{modo}"].get("parafrasis") or {}
            if o:
                lineas.append(f"| {modo} | {o['preguntas']} | {_f(o['hit@8'])} | {_f(o['rr'])} |")
        lineas += ["", "**Preguntas sin respuesta: aceptaciones falsas de la recuperación** (algún fragmento pasaría el filtro):", ""]
        for modo in ("semantica", "hibrida"):
            s = res[f"{conjunto}|sin_respuesta|{modo}"]
            lineas.append(f"- {modo}: {s['aceptaciones_falsas']} de {s['preguntas']} {s['ids'] or ''}")
        lineas.append("")
    return "\n".join(lineas)


# ── 2. Chat de punta a punta ──────────────────────────────────────────────────────

class _Respuesta:
    def __init__(self, status_code: int, texto: str):
        self.status_code, self.text = status_code, texto

    def json(self) -> Any:
        return json.loads(self.text)


class _Cliente:
    """Cliente HTTP mínimo con la biblioteca estándar (el servidor no tiene httpx fuera de los contenedores)."""

    def __init__(self) -> None:
        self.token: str | None = None

    def _pedir(self, metodo: str, url: str, datos: Any = None) -> _Respuesta:
        import urllib.error
        import urllib.request

        cuerpo = json.dumps(datos).encode() if datos is not None else None
        req = urllib.request.Request(url, data=cuerpo, method=metodo, headers={"Content-Type": "application/json"})
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return _Respuesta(r.status, r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return _Respuesta(e.code, e.read().decode("utf-8", "replace"))

    def post(self, url: str, json: Any = None) -> _Respuesta:  # noqa: A002 — misma firma que httpx
        return self._pedir("POST", url, json)

    def get(self, url: str) -> _Respuesta:
        return self._pedir("GET", url)


def _cliente() -> _Cliente:
    """Sesión en el chat. Usuario: INDAGATA_EMAIL / INDAGATA_PASSWORD (por defecto, el investigador de desarrollo)."""
    c = _Cliente()
    r = c.post(f"{GATEWAY}/auth/login", json={"email": os.environ.get("INDAGATA_EMAIL", "investigador@indagata.com"),
                                              "password": os.environ.get("INDAGATA_PASSWORD", "investigador123")})
    if r.status_code != 200:
        sys.exit(f"No se pudo iniciar sesión ({r.status_code}). Define INDAGATA_EMAIL e INDAGATA_PASSWORD.")
    c.token = r.json()["access_token"]
    return c


def _modelo(c: _Cliente) -> str:
    """El redactor que usa el servidor (OLLAMA_MODEL); la evaluación no elige modelo."""
    r = c.get(f"{GATEWAY}/rag/modelo")
    return (r.json().get("modelo") if r.status_code == 200 else None) or "desconocido"


_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _cifras_presentes(respuesta: str, cifras: list[str]) -> bool | None:
    if not cifras:
        return None
    vistas = {float(n.replace(",", ".")) for n in _NUMERO.findall(respuesta or "")}
    return all(any(abs(float(c) - v) <= 0.05 for v in vistas) for c in cifras)


def chat(a: argparse.Namespace) -> None:
    banco = _banco()
    preguntas = [p for p in banco["preguntas"] if a.conjunto == "todo" or p["conjunto"] == a.conjunto]
    c = _cliente()
    redactor = _modelo(c)
    print(f"Redactor del servidor: {redactor}; {len(preguntas)} preguntas ({a.conjunto}).", flush=True)
    filas = []
    for n, p in enumerate(preguntas, 1):
        inicio = time.monotonic()
        try:
            r = c.post(f"{GATEWAY}/rag/chat", json={"pregunta": p["pregunta"], "instrumentoIds": p["alcance"], "stream": False,
                                                     "usarCache": False, "calcularMetricas": False})
            datos = r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as exc:  # noqa: BLE001 — una consulta caída no tumba la corrida
            datos = {"error": f"{type(exc).__name__}: {exc}"}
        segundos = round(time.monotonic() - inicio, 1)
        decision = datos.get("decision")
        if p["tipo"] == "con_respuesta":
            correcta = decision == "dentro"
        else:  # sin respuesta o fuera de dominio: rechazar (sin información o fuera) es lo correcto
            correcta = decision in ("sin_informacion", "fuera")
        fila = {"id": p["id"], "conjunto": p["conjunto"], "tipo": p["tipo"], "tipo_instrumento": p.get("tipo_instrumento"),
                "pregunta": p["pregunta"], "esperada": p.get("esperada"), "decision": decision, "decision_correcta": correcta,
                "ruta": datos.get("ruta"), "consultaId": datos.get("consultaId"), "respuesta": datos.get("respuesta"),
                "cifras_correctas": _cifras_presentes(datos.get("respuesta", ""), p.get("cifras_clave") or [])
                if decision == "dentro" else None, "segundos": segundos, "error": datos.get("error")}
        filas.append(fila)
        print(f"[{n}/{len(preguntas)}] {p['id']} {decision} ({segundos} s) cifras={fila['cifras_correctas']}", flush=True)
    datos = {"banco": banco["version"], "conjunto": a.conjunto, "redactor": redactor, "filas": filas,
             "resumen": resumen_chat(filas)}
    print(f"Guardado: {_guardar('chat', datos, reporte_chat(datos))}")


def _percentil(valores: list[float], p: float) -> float | None:
    if not valores:
        return None
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(p * (len(v) - 1))))]


def resumen_chat(filas: list[dict[str, Any]]) -> dict[str, Any]:
    con = [f for f in filas if f["tipo"] == "con_respuesta"]
    sin = [f for f in filas if f["tipo"] != "con_respuesta"]
    con_cifras = [f for f in con if f["cifras_correctas"] is not None]
    tiempos = [f["segundos"] for f in filas if not f["error"]]
    return {
        "preguntas": len(filas),
        "decision_correcta": round(sum(f["decision_correcta"] for f in filas) / len(filas), 3) if filas else None,
        "falsos_rechazos": sum(not f["decision_correcta"] for f in con),
        "con_respuesta": len(con),
        "falsas_aceptaciones": sum(not f["decision_correcta"] for f in sin),
        "sin_respuesta": len(sin),
        "ids_falsas_aceptaciones": [f["id"] for f in sin if not f["decision_correcta"]],
        "exactitud_cifras": round(sum(f["cifras_correctas"] for f in con_cifras) / len(con_cifras), 3) if con_cifras else None,
        "con_cifras": len(con_cifras),
        "latencia_p50": _percentil(tiempos, 0.5),
        "latencia_p95": _percentil(tiempos, 0.95),
        "errores": [f["id"] for f in filas if f["error"]],
    }


def reporte_chat(d: dict[str, Any]) -> str:
    s = d["resumen"]
    return "\n".join([
        f"# Chat de punta a punta — banco v{d['banco']}, conjunto {d['conjunto']} ({datetime.now():%d/%m/%Y})", "",
        f"Redactor {d['redactor']}, sin caché.", "",
        "| Medida | Resultado |", "|---|---|",
        f"| Decisión correcta | {_f(s['decision_correcta'], pct=True)} ({s['preguntas']} preguntas) |",
        f"| Falsos rechazos (había respuesta y dijo que no) | {s['falsos_rechazos']} de {s['con_respuesta']} |",
        f"| Falsas aceptaciones (no había respuesta y contestó) | {s['falsas_aceptaciones']} de {s['sin_respuesta']} "
        f"{s['ids_falsas_aceptaciones'] or ''} |",
        f"| Exactitud de cifras (contra SQL) | {_f(s['exactitud_cifras'], pct=True)} ({s['con_cifras']} con cifra) |",
        f"| Latencia p50 / p95 | {s['latencia_p50']} s / {s['latencia_p95']} s |",
        f"| Errores | {s['errores'] or 'ninguno'} |", ""])


# ── 3. RAGAS ─────────────────────────────────────────────────────────────────────

def _clave_anthropic() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("ANTHROPIC_API_KEY="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def _preparar_ragas(juez: str) -> dict[str, Any]:
    try:
        from openai import AsyncOpenAI
        from ragas.embeddings.base import embedding_factory
        from ragas.llms import llm_factory
        from ragas.metrics.collections import AnswerRelevancy, ContextRecall, ContextUtilization, Faithfulness
    except ImportError as exc:
        sys.exit(f"RAGAS no está instalado ({exc}). Usa el entorno .venv-ragas (tools/rag/requirements-ragas.txt).")
    ollama = AsyncOpenAI(base_url=f"{OLLAMA}/v1", api_key="ollama")
    if juez.startswith("claude"):
        from anthropic import AsyncAnthropic

        clave = _clave_anthropic()
        if not clave:
            sys.exit("Falta ANTHROPIC_API_KEY (en el .env de la raíz o como variable de entorno).")
        llm = llm_factory(juez, provider="anthropic", client=AsyncAnthropic(api_key=clave), temperature=0,
                          max_tokens=2048)
    else:  # Ollama local (el juez de la Fase 4; poco confiable con 3B)
        llm = llm_factory(juez, client=ollama, temperature=0)
    embeddings = embedding_factory("openai", EMBEDDINGS, client=ollama)
    return {"fidelidad": Faithfulness(llm=llm), "relevancia": AnswerRelevancy(llm=llm, embeddings=embeddings),
            "precision_contexto": ContextUtilization(llm=llm), "recall_contexto": ContextRecall(llm=llm)}


async def _ragas_una(metricas: dict[str, Any], pregunta: str, respuesta: str, contextos: list[str],
                     referencia: str | None) -> dict[str, Any]:
    llamadas = {
        "fidelidad": lambda m: m.ascore(user_input=pregunta, response=respuesta, retrieved_contexts=contextos),
        "relevancia": lambda m: m.ascore(user_input=pregunta, response=respuesta),
        "precision_contexto": lambda m: m.ascore(user_input=pregunta, response=respuesta, retrieved_contexts=contextos),
        "recall_contexto": lambda m: m.ascore(user_input=pregunta, retrieved_contexts=contextos, reference=referencia),
    }
    salida: dict[str, Any] = {}
    for nombre, metrica in metricas.items():
        if nombre == "recall_contexto" and not referencia:
            salida[nombre] = None  # sin respuesta de referencia (entrevistas): no aplica
            continue
        try:
            valor = float((await llamadas[nombre](metrica)).value)
            salida[nombre] = None if math.isnan(valor) else round(valor, 3)
        except Exception as exc:  # noqa: BLE001
            salida[nombre] = None
            salida.setdefault("errores", {})[nombre] = f"{type(exc).__name__}: {str(exc)[:200]}"
    return salida


def ragas(a: argparse.Namespace) -> None:
    datos_chat = json.loads(Path(a.chat).read_text(encoding="utf-8"))
    filas = [f for f in datos_chat["filas"] if f["tipo"] == "con_respuesta" and f["decision"] == "dentro" and f["consultaId"]]
    if a.limite:
        filas = filas[: a.limite]
    metricas = _preparar_ragas(a.juez)
    c = _cliente()
    salida = []
    for n, f in enumerate(filas, 1):
        consulta = c.get(f"{GATEWAY}/rag/consultas/{f['consultaId']}").json()
        contextos = [x.get("texto", "") for x in consulta.get("contexto") or [] if x.get("texto")]
        valores = asyncio.run(_ragas_una(metricas, f["pregunta"], f["respuesta"] or "", contextos, f.get("esperada")))
        salida.append({"id": f["id"], "tipo_instrumento": f["tipo_instrumento"], "consultaId": f["consultaId"],
                       "contextos": len(contextos), **valores})
        print(f"[{n}/{len(filas)}] {f['id']} {valores}", flush=True)
    claves = ("fidelidad", "relevancia", "precision_contexto", "recall_contexto")
    resumen = {k: (round(statistics.mean(v), 3) if (v := [s[k] for s in salida if s.get(k) is not None]) else None,
                   len(v)) for k in claves}
    datos = {"juez": a.juez, "embeddings": EMBEDDINGS, "chat": str(a.chat), "filas": salida, "resumen": resumen}
    md = "\n".join([f"# RAGAS — juez {a.juez} ({datetime.now():%d/%m/%Y})", "",
                    f"RAGAS 0.4.3 sobre {len(salida)} respuestas del chat ({a.chat}). Embeddings: {EMBEDDINGS}.", "",
                    "| Dimensión (tríada RAG) | Métrica RAGAS | Media | n |", "|---|---|---|---|",
                    f"| Fundamentación | Fidelidad | {_f(resumen['fidelidad'][0])} | {resumen['fidelidad'][1]} |",
                    f"| Relevancia de la respuesta | Relevancia de la respuesta | {_f(resumen['relevancia'][0])} | {resumen['relevancia'][1]} |",
                    f"| Relevancia del contexto | Precisión del contexto | {_f(resumen['precision_contexto'][0])} | {resumen['precision_contexto'][1]} |",
                    f"| (con referencia) | Recall del contexto | {_f(resumen['recall_contexto'][0])} | {resumen['recall_contexto'][1]} |",
                    "", "Validez del juez: contrastar con la calificación humana (kappa de Cohen) antes de reportar.", ""])
    print(f"Guardado: {_guardar('ragas', datos, md)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="paso", required=True)
    sub.add_parser("recuperacion").set_defaults(funcion=recuperacion)
    sub.add_parser("calibrar").set_defaults(funcion=calibrar)
    p_chat = sub.add_parser("chat")
    p_chat.add_argument("--conjunto", choices=("prueba", "desarrollo", "todo"), default="prueba")
    p_chat.set_defaults(funcion=chat)
    p_ragas = sub.add_parser("ragas")
    p_ragas.add_argument("--chat", required=True, help="JSON del paso «chat»")
    p_ragas.add_argument("--juez", default="claude-haiku-5-5", help="modelo de Claude (API) o de Ollama")
    p_ragas.add_argument("--limite", type=int, default=0, help="solo las primeras N respuestas (prueba de costo)")
    p_ragas.set_defaults(funcion=ragas)
    a = ap.parse_args()
    a.funcion(a)


if __name__ == "__main__":
    main()
