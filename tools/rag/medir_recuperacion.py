"""Hit rate@k de la recuperación por similitud (Chroma) con las preguntas de las baterías del chat (7 nov 2026).

Para cada caso de `recuperacion_oro.json` busca en la colección `instrumentos`, filtrada al instrumento, los 8
fragmentos más parecidos a la consulta (mismo modelo de embeddings que el chat, sin umbrales) y mira en qué lugar
aparece el primer chunk correcto: el de una de las preguntas de «oro» (sección pregunta, reactivo o intercambio) o la
ficha («encabezado»). Reporta hit@1, @3, @5 y @8 y el MRR (promedio de 1/lugar), por tipo de instrumento, con la
búsqueda sin filtro y con el filtro que usa el chat desde el 7 nov (sin chunks de personas si la consulta no nombra a
nadie; `rag_service._donde`).

Corre dentro de visualization-service (tiene el modelo y la conexión a Chroma):
    MSYS_NO_PATHCONV=1 docker cp tools/rag/recuperacion_oro.json indagata_visualization_service:/tmp/oro.json
    docker compose exec -T visualization-service python - < tools/rag/medir_recuperacion.py > salida.json
"""
from __future__ import annotations

import json
import re
import sys

import chromadb
from sentence_transformers import SentenceTransformer

from shared.db.core.config import settings

K = (1, 3, 5, 8)
SECCIONES = {"pregunta", "reactivo", "intercambio"}


def _acierto(meta: dict, oro: list[str]) -> bool:
    if "encabezado" in oro and meta.get("seccion") == "encabezado":
        return True
    corto = str(meta.get("preguntaId") or "").rsplit("-", 1)[-1]
    return meta.get("seccion") in SECCIONES and corto in oro


def _buscar(col, modelo, casos: list[dict], filtro: bool) -> list[dict]:
    detalle = []
    for c in casos:
        vector = modelo.encode([c["consulta"]], normalize_embeddings=True).tolist()
        where: dict = {"instrumentoId": c["instrumento"]}
        if filtro and not re.search(r"[RAE]\d{2,5}", c["consulta"]):
            where = {"$and": [where, {"seccion": {"$nin": ["respondente", "alumno"]}}]}
        r = col.query(query_embeddings=vector, n_results=max(K), where=where, include=["metadatas", "distances"])
        metas = r["metadatas"][0]
        lugar = next((n for n, m in enumerate(metas, start=1) if _acierto(m, c["oro"])), None)
        detalle.append({"id": c["id"], "instrumento": c["instrumento"], "control": bool(c.get("control")), "lugar": lugar,
                        "recuperados": [f"{m.get('seccion')}:{str(m.get('preguntaId') or '').rsplit('-', 1)[-1]}" for m in metas]})
    return detalle


def main() -> None:
    casos = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/oro.json", encoding="utf-8"))["casos"]
    modelo = SentenceTransformer(settings.EMBEDDING_MODEL)
    col = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT).get_collection("instrumentos")

    def resumen(filas: list[dict]) -> dict:
        n = len(filas) or 1
        return {"n": len(filas), **{f"hit@{k}": round(sum(1 for f in filas if f["lugar"] and f["lugar"] <= k) / n, 3) for k in K},
                "mrr": round(sum(1 / f["lugar"] for f in filas if f["lugar"]) / n, 3)}

    def grupos(detalle: list[dict]) -> dict:
        g = {"baterias": [f for f in detalle if not f["control"]], "control": [f for f in detalle if f["control"]]}
        for prefijo in ("ENC", "PRU", "ENT"):
            g[prefijo] = [f for f in g["baterias"] if f["id"].startswith(prefijo)]
        return {nombre: resumen(f) for nombre, f in g.items()}

    salida = {}
    for nombre, filtro in (("sin_filtro", False), ("filtro_del_chat", True)):
        detalle = _buscar(col, modelo, casos, filtro)
        salida[nombre] = {"resumen": grupos(detalle), "detalle": detalle}
    print(json.dumps(salida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
