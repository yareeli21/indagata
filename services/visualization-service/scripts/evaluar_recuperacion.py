"""Métricas de recuperación del chat sobre el banco de evaluación (tools/rag/evaluacion/banco_v1.json), 11 nov 2026.

Se corre DENTRO del contenedor (necesita Chroma, Postgres y el modelo de embeddings); lo orquesta
tools/rag/evaluacion/evaluar_v1.py:
    docker compose exec -T -e PYTHONPATH=/app visualization-service python scripts/evaluar_recuperacion.py /tmp/banco.json

Qué mide, sobre el RANKING de la búsqueda (antes del umbral de similitud, que es otra decisión):
  - Hit@k (k = 1, 3, 5, 8): proporción de preguntas con un fragmento correcto entre los k primeros.
  - MRR@8: promedio de 1/posición del primer fragmento correcto (0 si no está entre los 8 primeros).
  - nDCG@8: ganancia acumulada descontada normalizada, relevancia binaria; el ideal pone min(8, relevantes) arriba.
  - Recall@8 acotado: fragmentos correctos entre los 8 primeros / min(8, fragmentos correctos que existen). Una pregunta
    guía de entrevista tiene hasta 43 fragmentos correctos (un intercambio por persona); sin acotar, el recall sería
    bajo por construcción.
Un fragmento es correcto si es del instrumento esperado y trae el preguntaId esperado (pregunta, reactivo o intercambio).

Se comparan dos modos (búsqueda semántica sola y búsqueda híbrida) y dos alcances (el instrumento de la pregunta, como
lo usa un investigador en su investigación, y toda la colección, más difícil). Con intervalos de confianza al 95 %
(bootstrap, 2000 remuestreos). Las preguntas sin respuesta miden la «aceptación falsa» de la recuperación: si algún
fragmento pasaría el filtro de relevancia del chat.
"""
from __future__ import annotations

import json
import logging
import math
import random
import sys
import time
from typing import Any

logging.disable(logging.WARNING)

from sqlalchemy import text  # noqa: E402

from shared.db.core.config import settings  # noqa: E402

from services import hibrida, vectores  # noqa: E402
from services import rag_service as r  # noqa: E402

K_MAX = 8
KS = (1, 3, 5, 8)
CANDIDATOS = 32  # resultados semánticos que se piden (la lista por palabras trae los suyos)


def _relevantes_totales(relevantes: list[dict[str, str]]) -> int:
    sesion = r.fabrica_sesiones()
    try:
        total = 0
        for g in relevantes:
            total += int(sesion.execute(text(
                "SELECT count(*) FROM tt_rag.documento_vectorizado d JOIN tt_rag.instrumento_procesado p "
                "ON p.id_instrumento = d.instrumento_id WHERE p.id_crudo = :i AND d.chunk_metadata->>'fuente' = 'documento' "
                "AND d.chunk_metadata->>'preguntaId' = :q"), {"i": int(g["instrumentoId"]), "q": g["preguntaId"]}).scalar() or 0)
        return total
    finally:
        sesion.close()


def _ranking(coleccion: Any, pregunta: str, alcance: list[str], hibrida_on: bool) -> dict[str, Any]:
    settings.RAG_HIBRIDA = hibrida_on
    where = {"instrumentoId": {"$in": alcance}} if alcance else None
    return hibrida.consultar(coleccion, r._vector(pregunta), pregunta, CANDIDATOS, where, alcance, r.fabrica_sesiones)


def _es_correcto(meta: dict[str, Any], relevantes: list[dict[str, str]]) -> bool:
    return any(str(meta.get("instrumentoId")) == g["instrumentoId"] and meta.get("preguntaId") == g["preguntaId"]
               for g in relevantes)


def _metricas(res: dict[str, Any], relevantes: list[dict[str, str]], total: int) -> dict[str, Any]:
    metas = (res.get("metadatas") or [[]])[0][:K_MAX]
    marcas = [_es_correcto(m or {}, relevantes) for m in metas]
    primero = next((n for n, ok in enumerate(marcas, start=1) if ok), None)
    dcg = sum(1 / math.log2(n + 1) for n, ok in enumerate(marcas, start=1) if ok)
    ideal = sum(1 / math.log2(n + 1) for n in range(1, min(K_MAX, total) + 1))
    return {
        "rango": primero,
        **{f"hit@{k}": int(primero is not None and primero <= k) for k in KS},
        "rr": 1 / primero if primero else 0.0,
        "ndcg": dcg / ideal if ideal else 0.0,
        "recall": sum(marcas) / min(K_MAX, total) if total else 0.0,
    }


def _aceptaria(res: dict[str, Any], hibrida_on: bool) -> bool:
    """¿Algún fragmento pasaría el filtro de relevancia del chat (umbral o palabras)?"""
    settings.RAG_HIBRIDA = hibrida_on
    for n, (meta, dist) in enumerate(zip((res.get("metadatas") or [[]])[0], (res.get("distances") or [[]])[0])):
        frag = {"score": round(1 - float(dist), 4), "seccion": str((meta or {}).get("seccion", "")),
                "coincidencia": (res.get("coincidencias") or [[]])[0][n] if res.get("coincidencias") else None,
                "palabras": (res.get("palabras") or [[]])[0][n] if res.get("palabras") else None}
        if hibrida.relevante(frag):
            return True
    return False


def _bootstrap(valores: list[float], veces: int = 2000, semilla: int = 7) -> tuple[float, float]:
    if not valores:
        return (0.0, 0.0)
    azar = random.Random(semilla)
    medias = sorted(sum(azar.choice(valores) for _ in valores) / len(valores) for _ in range(veces))
    return (round(medias[int(0.025 * veces)], 3), round(medias[int(0.975 * veces) - 1], 3))


def _resumen(filas: list[dict[str, Any]]) -> dict[str, Any]:
    if not filas:
        return {}
    salida: dict[str, Any] = {"preguntas": len(filas)}
    for clave in [f"hit@{k}" for k in KS] + ["rr", "ndcg", "recall"]:
        salida[clave] = round(sum(f[clave] for f in filas) / len(filas), 3)
    salida["ic95_hit@8"] = _bootstrap([f["hit@8"] for f in filas])
    salida["ic95_mrr"] = _bootstrap([f["rr"] for f in filas])
    return salida


UMBRALES = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
COBERTURAS = (0.50, 0.60, 0.75, 0.90)


def _fragmentos(res: dict[str, Any], relevantes: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Los K_MAX primeros del ranking con lo que mira el filtro del chat (hibrida.relevante) y si son correctos."""
    salida = []
    metas = (res.get("metadatas") or [[]])[0]
    for n, (meta, dist) in enumerate(zip(metas[:K_MAX], (res.get("distances") or [[]])[0])):
        meta = meta or {}
        salida.append({"score": round(1 - float(dist), 4), "seccion": str(meta.get("seccion", "")),
                       "coincidencia": (res.get("coincidencias") or [[]])[0][n] if res.get("coincidencias") else None,
                       "palabras": (res.get("palabras") or [[]])[0][n] if res.get("palabras") else None,
                       "correcto": _es_correcto(meta, relevantes)})
    return salida


def calibrar(banco: dict[str, Any], conjunto: str) -> dict[str, Any]:
    """Barrido de RAG_MIN_SCORE × RAG_MIN_COBERTURA sobre el filtro de relevancia del chat (búsqueda híbrida, alcance
    del chat: el instrumento en las preguntas con respuesta, toda la colección en las demás). Solo la compuerta de la
    recuperación: no incluye el planificador ni el clasificador de la zona gris."""
    coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
    original = (settings.RAG_HIBRIDA, settings.RAG_MIN_SCORE, settings.RAG_MIN_COBERTURA)
    preguntas = []
    try:
        for p in banco["preguntas"]:
            if p["conjunto"] != conjunto:
                continue
            relevantes = p.get("relevantes") or []
            res = _ranking(coleccion, p["pregunta"], p["alcance"], True)
            preguntas.append({"id": p["id"], "tipo": p["tipo"], "fragmentos": _fragmentos(res, relevantes)})
            print(f"{p['id']} listo", file=sys.stderr, flush=True)
        tabla = []
        for umbral in UMBRALES:
            for cobertura in COBERTURAS:
                settings.RAG_MIN_SCORE, settings.RAG_MIN_COBERTURA = umbral, cobertura
                con = [q for q in preguntas if q["tipo"] == "con_respuesta"]
                sin = [q for q in preguntas if q["tipo"] != "con_respuesta"]
                acepta = {q["id"]: any(hibrida.relevante(f) for f in q["fragmentos"]) for q in preguntas}
                util = {q["id"]: any(f["correcto"] and hibrida.relevante(f) for f in q["fragmentos"]) for q in con}
                aciertos = sum(acepta[q["id"]] for q in con) + sum(not acepta[q["id"]] for q in sin)
                tabla.append({"umbral": umbral, "cobertura": cobertura,
                              "acepta_con_respuesta": sum(acepta[q["id"]] for q in con), "con_respuesta": len(con),
                              "fragmento_correcto_pasa": sum(util.values()),
                              "falsas_aceptaciones": sum(acepta[q["id"]] for q in sin), "sin_respuesta": len(sin),
                              "decisiones_correctas": aciertos, "total": len(preguntas),
                              "rechazadas": [q["id"] for q in con if not acepta[q["id"]]],
                              "aceptadas_sin_respuesta": [q["id"] for q in sin if acepta[q["id"]]]})
    finally:
        settings.RAG_HIBRIDA, settings.RAG_MIN_SCORE, settings.RAG_MIN_COBERTURA = original
    return {"conjunto": conjunto, "actual": {"umbral": original[1], "cobertura": original[2]}, "tabla": tabla,
            "preguntas": preguntas}


def main() -> None:
    banco = json.load(open(sys.argv[1], encoding="utf-8"))
    if "--calibrar" in sys.argv:
        json.dump(calibrar(banco, "desarrollo"), sys.stdout, ensure_ascii=False)
        return
    coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_INSTRUMENTOS)
    original = settings.RAG_HIBRIDA
    detalle: list[dict[str, Any]] = []
    inicio = time.monotonic()
    try:
        for p in banco["preguntas"]:
            if p["tipo"] == "con_respuesta":
                total = _relevantes_totales(p["relevantes"])
                consultas = [("original", p["pregunta"], ["instrumento", "coleccion"])]
                consultas += [(f"parafrasis{n}", t, ["coleccion"]) for n, t in enumerate(p.get("parafrasis") or [], 1)]
                for variante, texto, alcances in consultas:
                    for alcance in alcances:
                        for modo in ("semantica", "hibrida"):
                            res = _ranking(coleccion, texto, p["alcance"] if alcance == "instrumento" else [], modo == "hibrida")
                            detalle.append({"id": p["id"], "conjunto": p["conjunto"], "tipo_instrumento": p["tipo_instrumento"],
                                            "variante": variante, "alcance": alcance, "modo": modo, "relevantes_totales": total,
                                            **_metricas(res, p["relevantes"], total)})
            else:
                for modo in ("semantica", "hibrida"):
                    res = _ranking(coleccion, p["pregunta"], [], modo == "hibrida")
                    detalle.append({"id": p["id"], "conjunto": p["conjunto"], "tipo": p["tipo"], "variante": "original",
                                    "alcance": "coleccion", "modo": modo, "aceptaria": _aceptaria(res, modo == "hibrida")})
            print(f"{p['id']} listo ({time.monotonic() - inicio:.0f} s)", file=sys.stderr, flush=True)
    finally:
        settings.RAG_HIBRIDA = original

    resumen: dict[str, Any] = {}
    for conjunto in ("prueba", "desarrollo"):
        for alcance in ("instrumento", "coleccion"):
            for modo in ("semantica", "hibrida"):
                base = [d for d in detalle if d["conjunto"] == conjunto and d["alcance"] == alcance and d["modo"] == modo
                        and "hit@8" in d]
                originales = [d for d in base if d["variante"] == "original"]
                clave = f"{conjunto}|{alcance}|{modo}"
                resumen[clave] = {"originales": _resumen(originales),
                                  "por_tipo": {t: _resumen([d for d in originales if d["tipo_instrumento"] == t])
                                               for t in ("encuesta", "prueba_estandarizada", "entrevista")}}
                if alcance == "coleccion":
                    resumen[clave]["parafrasis"] = _resumen([d for d in base if d["variante"] != "original"])
        for modo in ("semantica", "hibrida"):
            sin = [d for d in detalle if d["conjunto"] == conjunto and d["modo"] == modo and "aceptaria" in d]
            resumen[f"{conjunto}|sin_respuesta|{modo}"] = {
                "preguntas": len(sin), "aceptaciones_falsas": sum(d["aceptaria"] for d in sin),
                "ids": [d["id"] for d in sin if d["aceptaria"]]}
    json.dump({"umbral": settings.RAG_MIN_SCORE, "cobertura_minima": settings.RAG_MIN_COBERTURA, "k": K_MAX,
               "segundos": round(time.monotonic() - inicio), "resumen": resumen, "detalle": detalle},
              sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
