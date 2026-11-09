"""Búsqueda de elemento conocido (*known-item search*) sobre la recuperación del chat (9 nov 2026).

Cada pregunta o reactivo de un instrumento se usa como consulta, y se mide si la búsqueda devuelve un fragmento de esa
misma pregunta. La respuesta correcta la da el propio instrumento: no hay juicio de nadie. Dos variantes:
  - «texto»: el texto completo de la pregunta;
  - «palabras_clave»: solo sus palabras con contenido (sin signos ni palabras vacías), para que la consulta no sea
    una copia literal del fragmento.
Mismo modelo de embeddings, colección y filtro que el chat (sin chunks de personas; `rag_service._donde`); 8
fragmentos por consulta, como la búsqueda del chat. Reporta hit@1, @3, @5, @8 y MRR por instrumento y por tipo.

Uso, desde la raíz del repositorio:
    .venv\\Scripts\\python.exe tools\\rag\\known_item.py preparar > %TEMP%\\ki.json
    MSYS_NO_PATHCONV=1 docker cp %TEMP%\\ki.json indagata_visualization_service:/tmp/ki.json
    docker compose exec -T visualization-service python - /tmp/ki.json < tools/rag/known_item.py > salida.json
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata

K = (1, 3, 5, 8)
SECCIONES = {"pregunta", "reactivo", "intercambio"}
# Documento final vigente de cada instrumento (Anexo A, Tabla A.1).
DOCUMENTOS = {
    "127": "storage/json/127/54__v4_documento_final.json",
    "130": "storage/json/130/1__v2_documento_final.json",
    "129": "storage/json/129/49__v8_documento_final.json",
    "61": "storage/json/61/21__v2_documento_final.json",
    "60": "storage/json/60/484__v2_documento_final.json",
}
_VACIAS = set("""a al algo algun alguna alguno algunos ante con como cual cuales cuando de del desde donde e el ella
en entre era es esa ese eso esta este esto fue ha han hay la las le les lo los mas me mi mis muy no o para pero por que
qué se sea ser si sin sobre su sus te tu tus un una uno unos y ya yo""".split())


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def palabras_clave(texto: str) -> str:
    palabras = re.findall(r"[\wáéíóúüñ]+", texto.lower())
    return " ".join(p for p in palabras if _sin_acentos(p) not in _VACIAS and len(p) > 2)


def preparar() -> None:
    consultas = []
    for ins, ruta in DOCUMENTOS.items():
        doc = json.load(open(ruta, encoding="utf-8"))
        tipo = "prueba" if "reactivos" in doc else "entrevista" if "entrevistas" in doc else "encuesta"
        for item in doc.get("preguntas") or doc.get("reactivos") or []:
            texto = " ".join(str(item.get("texto") or "").split())
            if texto:
                consultas.append({"instrumento": ins, "tipo": tipo, "id": item["id"].rsplit("-", 1)[-1], "texto": texto,
                                  "palabras_clave": palabras_clave(texto)})
    json.dump(consultas, sys.stdout, ensure_ascii=False, indent=1)


def medir(ruta: str) -> None:
    import chromadb
    from sentence_transformers import SentenceTransformer

    from shared.db.core.config import settings

    consultas = json.load(open(ruta, encoding="utf-8"))
    modelo = SentenceTransformer(settings.EMBEDDING_MODEL)
    col = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT).get_collection("instrumentos")

    def resumen(filas: list[dict]) -> dict:
        n = len(filas) or 1
        return {"n": len(filas), **{f"hit@{k}": round(sum(1 for f in filas if f["lugar"] and f["lugar"] <= k) / n, 3)
                                    for k in K},
                "mrr": round(sum(1 / f["lugar"] for f in filas if f["lugar"]) / n, 3)}

    salida = {}
    for variante in ("texto", "palabras_clave"):
        detalle = []
        for c in consultas:
            vector = modelo.encode([c[variante]], normalize_embeddings=True).tolist()
            where = {"$and": [{"instrumentoId": c["instrumento"]}, {"seccion": {"$nin": ["respondente", "alumno"]}}]}
            r = col.query(query_embeddings=vector, n_results=max(K), where=where, include=["metadatas"])
            metas = r["metadatas"][0]
            lugar = next((n for n, m in enumerate(metas, start=1)
                          if m.get("seccion") in SECCIONES and str(m.get("preguntaId") or "").rsplit("-", 1)[-1] == c["id"]),
                         None)
            detalle.append({**c, "lugar": lugar, "primero": f"{metas[0].get('seccion')}:"
                            f"{str(metas[0].get('preguntaId') or '').rsplit('-', 1)[-1]}" if metas else None})
        grupos = {"todas": detalle}
        for clave in ("tipo", "instrumento"):
            for valor in sorted({f[clave] for f in detalle}):
                grupos[f"{clave}:{valor}"] = [f for f in detalle if f[clave] == valor]
        salida[variante] = {"resumen": {g: resumen(f) for g, f in grupos.items()},
                            "fallas": [f for f in detalle if f["lugar"] != 1]}
    print(json.dumps(salida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preparar":
        preparar()
    else:
        medir(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ki.json")
