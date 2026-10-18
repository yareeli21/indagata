"""Evaluación fuera de línea del chat RAG con preguntas de referencia (y RAGAS real).

Para cada pregunta de `preguntas_referencia.json`:
  1. La hace al chat (API del gateway) con su alcance y guarda respuesta, decisión de
     dominio, ruta y el contexto que vio el modelo (`GET /rag/consultas/{id}`).
  2. Espera las métricas PROPIAS del servicio (fidelidad, relevancia, precisión del
     contexto; las mismas que ve la interfaz).
  3. Calcula el RECALL DEL CONTEXTO (necesita la respuesta esperada): fracción de las
     afirmaciones de la respuesta esperada que el contexto sustenta.
  4. Si RAGAS está instalado (entorno aislado, `requirements-ragas.txt`), calcula con
     RAGAS 0.4.3 real Faithfulness, AnswerRelevancy, ContextUtilization y ContextRecall
     con el MISMO juez, para comparar lado a lado con la implementación propia.
Además mide si la DECISIÓN de dominio fue la esperada (dentro, fuera, privacidad,
sin_informacion, ayuda). Guarda `reporte_<fecha>.json` y `reporte_<fecha>.md`.

Uso (con la app levantada; IDs de esta instalación):
    .venv-ragas\\Scripts\\python.exe tools\\rag\\evaluar_ragas.py --ids enc_10=59,pru_01=55,ent_01=60,enc_04=50
    python tools/rag/evaluar_ragas.py --ids … --sin-ragas        # solo métricas propias + recall
Opciones: --juez llama3.2:3b (modelo de Ollama para el recall y RAGAS), --solo Q05,Q09.

Nota: RAGAS habla con Ollama por su API compatible con OpenAI (`/v1`), que no envía
`num_ctx`; para que no recorte el contexto, levanta Ollama con OLLAMA_CONTEXT_LENGTH=4096.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

AQUI = Path(__file__).resolve().parent
GATEWAY = "http://localhost:8006"
OLLAMA = "http://localhost:11434"
# Embeddings de RAGAS: un modelo ligero servido por Ollama (`ollama pull nomic-embed-text`),
# para no cargar torch en el equipo. El chat usa paraphrase-multilingual-mpnet-base-v2, así que
# la relevancia de RAGAS y la propia no son idénticas por construcción (ver el reporte).
EMBEDDINGS = "nomic-embed-text"
_RESPONDIDAS = {"dentro", "ayuda"}

_P_AFIRMACIONES_REF = (
    "Divide la RESPUESTA ESPERADA en afirmaciones simples y autónomas.\n"
    'Responde solo JSON: {{"afirmaciones": ["..."]}}\n\nRESPUESTA ESPERADA: {referencia}'
)
_P_ATRIBUCION = (
    "Para cada AFIRMACIÓN decide si el CONTEXTO la sustenta (1) o no (0). No uses conocimiento propio.\n"
    'Responde solo JSON: {{"veredictos": [{{"afirmacion": "...", "veredicto": 0 o 1}}]}}\n\n'
    "CONTEXTO:\n{contexto}\n\nAFIRMACIONES:\n{afirmaciones}"
)


# ── Chat ───────────────────────────────────────────────────────────────────────


class Chat:
    def __init__(self, email: str, password: str) -> None:
        self.http = httpx.Client(timeout=httpx.Timeout(connect=10, read=600, write=60, pool=10))
        r = self.http.post(f"{GATEWAY}/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        self.cab = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def _pedir(self, metodo: str, ruta: str, **kwargs: Any) -> dict[str, Any]:
        """Petición con reintentos: en Windows, Docker a veces corta la conexión (WinError 10054)."""
        for intento in range(4):
            try:
                r = self.http.request(metodo, f"{GATEWAY}{ruta}", headers=self.cab, **kwargs)
                r.raise_for_status()
                return r.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if intento == 3:
                    raise
                print(f"  reintento {intento + 1} ({type(exc).__name__})", flush=True)
                time.sleep(5 * (intento + 1))
        raise RuntimeError("inalcanzable")

    def preguntar(self, pregunta: str, ids: list[str]) -> dict[str, Any]:
        return self._pedir("POST", "/rag/chat", json={"pregunta": pregunta, "stream": False, "instrumentoIds": ids})

    def consulta(self, consulta_id: int) -> dict[str, Any]:
        return self._pedir("GET", f"/rag/consultas/{consulta_id}")

    def esperar_metricas(self, consulta_id: int, limite_s: int = 420) -> dict[str, Any]:
        inicio = time.monotonic()
        while True:
            m = self._pedir("GET", f"/rag/consultas/{consulta_id}/metricas")
            if m.get("estado") != "calculando" or time.monotonic() - inicio > limite_s:
                return m
            time.sleep(4)


# ── Recall del contexto (implementación propia, mismas definiciones que RAGAS) ─


def _juez(prompt: str, modelo: str) -> dict[str, Any] | None:
    """Juez (Ollama, JSON, temperatura 0) con reintentos; None si no responde o no es JSON.

    Comparte Ollama con el juez del servicio: en Windows la conexión a veces se corta
    (WinError 10054), por eso se reintenta en lugar de abortar la evaluación.
    """
    for intento in range(4):
        try:
            r = httpx.post(f"{OLLAMA}/api/generate", timeout=300, json={
                "model": modelo, "prompt": prompt, "stream": False, "format": "json",
                "options": {"temperature": 0, "num_ctx": 4096}})
            return json.loads(r.json().get("response") or "")
        except ValueError:
            return None
        except httpx.HTTPError as exc:
            if intento == 3:
                print(f"  juez sin respuesta ({type(exc).__name__})", flush=True)
                return None
            time.sleep(5 * (intento + 1))
    return None


def recall_contexto(referencia: str, contextos: list[str], modelo: str) -> float | None:
    """Afirmaciones de la respuesta esperada sustentadas por el contexto / total."""
    datos = _juez(_P_AFIRMACIONES_REF.format(referencia=referencia), modelo) or {}
    afirmaciones = [str(a) for a in datos.get("afirmaciones") or [] if str(a).strip()]
    if not afirmaciones or not contextos:
        return None if not afirmaciones else 0.0
    lista = "\n".join(f"{i}. {a}" for i, a in enumerate(afirmaciones, start=1))
    datos = _juez(_P_ATRIBUCION.format(contexto="\n".join(contextos)[:6000], afirmaciones=lista), modelo) or {}
    veredictos = [str((v or {}).get("veredicto")).strip() in ("1", "True", "true") for v in datos.get("veredictos") or []]
    return round(sum(veredictos) / len(afirmaciones), 3) if veredictos else None


# ── RAGAS real (opcional) ──────────────────────────────────────────────────────


def preparar_ragas(modelo: str):  # noqa: ANN201
    """Métricas de RAGAS 0.4.3 con Ollama como juez, o None si RAGAS no está instalado."""
    try:
        import instructor
        import ragas.llms.base as ragas_llms
        from openai import AsyncOpenAI
        from ragas.embeddings.base import embedding_factory
        from ragas.llms import llm_factory
        from ragas.metrics.collections import AnswerRelevancy, ContextRecall, ContextUtilization, Faithfulness
    except ImportError:
        return None

    # RAGAS 0.4.3 crea el cliente de instructor con Mode.JSON (el esquema va en el prompt).
    # Con un juez local de 3B eso falla siempre: el modelo devuelve el ESQUEMA en vez de
    # llenarlo (comprobado en la Fase 4). Con Mode.JSON_SCHEMA, Ollama restringe la
    # generación al esquema y el modelo solo puede producir una instancia válida. Solo
    # cambia el formato de salida; los prompts y las fórmulas de RAGAS quedan intactos.
    original = ragas_llms._get_instructor_client

    def _cliente_con_esquema(client, provider):  # noqa: ANN001, ANN202
        if provider == "openai":
            return instructor.from_openai(client, mode=instructor.Mode.JSON_SCHEMA)
        return original(client, provider)

    ragas_llms._get_instructor_client = _cliente_con_esquema
    cliente = AsyncOpenAI(base_url=f"{OLLAMA}/v1", api_key="ollama")
    llm = llm_factory(modelo, client=cliente, temperature=0)
    embeddings = embedding_factory("openai", EMBEDDINGS, client=cliente)
    return {
        "fidelidad": Faithfulness(llm=llm),
        "relevancia": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "precision_contexto": ContextUtilization(llm=llm),
        "recall_contexto": ContextRecall(llm=llm),
    }


async def _ragas_una(metricas: dict, pregunta: str, respuesta: str, contextos: list[str], referencia: str) -> dict[str, Any]:
    salida: dict[str, Any] = {}
    llamadas = {
        "fidelidad": lambda m: m.ascore(user_input=pregunta, response=respuesta, retrieved_contexts=contextos),
        "relevancia": lambda m: m.ascore(user_input=pregunta, response=respuesta),
        "precision_contexto": lambda m: m.ascore(user_input=pregunta, response=respuesta, retrieved_contexts=contextos),
        "recall_contexto": lambda m: m.ascore(user_input=pregunta, retrieved_contexts=contextos, reference=referencia),
    }
    for nombre, metrica in metricas.items():
        try:
            valor = float((await llamadas[nombre](metrica)).value)
            salida[nombre] = None if math.isnan(valor) else round(valor, 3)
        except Exception as exc:  # noqa: BLE001 — el juez pequeño falla a veces en el JSON de RAGAS
            salida[nombre] = None
            salida.setdefault("errores", {})[nombre] = f"{type(exc).__name__}: {str(exc)[:160]}"
    return salida


# ── Reporte ────────────────────────────────────────────────────────────────────

_CLAVES = ("fidelidad", "relevancia", "precision_contexto", "recall_contexto")


def _media(valores: list[float | None]) -> float | None:
    v = [x for x in valores if x is not None]
    return round(sum(v) / len(v), 3) if v else None


def _fmt(x: Any) -> str:
    return "—" if x is None else f"{x:.2f}"


def escribir_reporte(resultados: list[dict[str, Any]], juez: str, con_ragas: bool) -> Path:
    respondidas = [r for r in resultados if r["decision"] in _RESPONDIDAS and r["decision_esperada"] in _RESPONDIDAS]
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "juez": juez,
        "n_preguntas": len(resultados),
        "decision_correcta": round(sum(r["decision"] == r["decision_esperada"] for r in resultados) / len(resultados), 3),
        "propias": {k: _media([r["propias"].get(k) for r in respondidas]) for k in _CLAVES},
        "ragas": {k: _media([(r.get("ragas") or {}).get(k) for r in respondidas]) for k in _CLAVES} if con_ragas else None,
    }
    sello = datetime.now().strftime("%Y%m%d_%H%M")
    destino = AQUI / "reportes"
    destino.mkdir(exist_ok=True)
    (destino / f"reporte_{sello}.json").write_text(json.dumps({"resumen": resumen, "resultados": resultados}, ensure_ascii=False, indent=1),
                                                   encoding="utf-8")
    lineas = [
        f"# Evaluación del chat RAG ({resumen['fecha']})", "",
        f"- Juez: `{juez}` (modelo pequeño: valores aproximados).",
        f"- Preguntas: {resumen['n_preguntas']}; decisión de dominio correcta: {resumen['decision_correcta']:.0%}.", "",
        "| Métrica | Propia (servicio) | RAGAS 0.4.3 |", "|---|---|---|",
    ]
    for k in _CLAVES:
        lineas.append(f"| {k} | {_fmt(resumen['propias'][k])} | {_fmt((resumen['ragas'] or {}).get(k))} |")
    lineas += ["", "| ID | Tipo | Decisión (esperada) | Ruta | Fid. | Rel. | Prec. | Recall | RAGAS fid/rel/prec/recall |",
               "|---|---|---|---|---|---|---|---|---|"]
    for r in resultados:
        p, g = r["propias"], r.get("ragas") or {}
        lineas.append(f"| {r['id']} | {r['tipo']} | {r['decision']} ({r['decision_esperada']}) | {r['ruta'] or '—'} | "
                      f"{_fmt(p.get('fidelidad'))} | {_fmt(p.get('relevancia'))} | {_fmt(p.get('precision_contexto'))} | "
                      f"{_fmt(p.get('recall_contexto'))} | {'/'.join(_fmt(g.get(k)) for k in _CLAVES) if g else '—'} |")
    lineas += ["", "## Respuestas", ""]
    for r in resultados:
        lineas += [f"**{r['id']}. {r['pregunta']}**", "", f"> {r['respuesta'].strip()[:600]}", "",
                   f"Esperada: {r['esperada']}", ""]
    md = destino / f"reporte_{sello}.md"
    md.write_text("\n".join(lineas), encoding="utf-8")
    return md


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", required=True, help="clave=id_crudo separados por comas (enc_10=59,…)")
    ap.add_argument("--juez", default="llama3.2:3b")
    ap.add_argument("--sin-ragas", action="store_true")
    ap.add_argument("--solo", default="", help="IDs de preguntas separados por comas")
    ap.add_argument("--continuar", action="store_true",
                    help="retoma la última corrida interrumpida (reportes/parcial.json) sin repetir preguntas")
    ap.add_argument("--email", default="admin@indagata.com")
    ap.add_argument("--password", default="admin123")
    a = ap.parse_args()

    ids = dict(par.split("=") for par in a.ids.split(","))
    datos = json.loads((AQUI / "preguntas_referencia.json").read_text(encoding="utf-8"))
    preguntas = [q for q in datos["preguntas"] if not a.solo or q["id"] in a.solo.split(",")]
    ragas = None if a.sin_ragas else preparar_ragas(a.juez)
    if not a.sin_ragas and ragas is None:
        print("RAGAS no está instalado: solo métricas propias (usa el entorno de requirements-ragas.txt).")
    chat = Chat(a.email, a.password)

    # Cada pregunta se guarda al terminar: si el equipo se queda sin memoria a la mitad
    # (pasó en la Fase 4), `--continuar` retoma sin perder lo ya evaluado.
    parcial = AQUI / "reportes" / "parcial.json"
    parcial.parent.mkdir(exist_ok=True)
    resultados: list[dict[str, Any]] = []
    if a.continuar and parcial.exists():
        resultados = json.loads(parcial.read_text(encoding="utf-8"))
        print(f"Retomando: {len(resultados)} pregunta(s) ya evaluadas.", flush=True)
    hechas = {r["id"] for r in resultados}
    for q in preguntas:
        if q["id"] in hechas:
            continue
        alcance = [ids[k] for k in q["alcance"]]
        try:
            r = chat.preguntar(q["pregunta"], alcance)
            detalle = chat.consulta(r["consultaId"]) if r.get("consultaId") else {}
            m = chat.esperar_metricas(r["consultaId"]) if r.get("consultaId") else {}
        except (httpx.HTTPError, RuntimeError) as exc:  # una pregunta fallida no detiene la evaluación
            print(f"{q['id']} ERROR: {exc}", flush=True)
            r, detalle, m = {"respuesta": f"(error: {exc})", "decision": "error"}, {}, {}
        contextos = [c.get("texto", "") for c in detalle.get("contexto") or [] if c.get("texto")]
        fila = {
            "id": q["id"], "tipo": q["tipo"], "pregunta": q["pregunta"], "esperada": q["esperada"],
            "decision_esperada": q["decision_esperada"], "decision": r.get("decision"), "ruta": r.get("ruta"),
            "respuesta": r.get("respuesta", ""), "fuentes": [f["titulo"] for f in r.get("fuentes") or []],
            "propias": {"fidelidad": m.get("fidelidad"), "relevancia": m.get("relevancia"),
                        "precision_contexto": m.get("precisionContexto"), "estado": m.get("estado")},
        }
        if r.get("decision") in _RESPONDIDAS and contextos:
            fila["propias"]["recall_contexto"] = recall_contexto(q["esperada"], contextos, a.juez)
            if ragas:
                fila["ragas"] = asyncio.run(_ragas_una(ragas, q["pregunta"], fila["respuesta"], contextos, q["esperada"]))
        resultados.append(fila)
        parcial.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{q['id']} {fila['decision']:>15} (esperada {q['decision_esperada']}) propias={fila['propias']} "
              f"ragas={fila.get('ragas')}", flush=True)

    print(f"\nReporte: {escribir_reporte(resultados, a.juez, ragas is not None)}")


if __name__ == "__main__":
    main()
