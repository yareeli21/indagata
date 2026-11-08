"""Cuántos chunks de cada instrumento pasan del límite del modelo de embeddings (`max_seq_length`, 128 tokens): lo que
pasa de ahí no se embebe (7 nov 2026, Fase 2 del chat).

Corre dentro de visualization-service:
    docker compose exec -T visualization-service python - < tools/rag/contar_truncados.py > truncados.json
"""
import collections, json, chromadb
from transformers import AutoTokenizer
from shared.db.core.config import settings
tok = AutoTokenizer.from_pretrained("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
lim = m.max_seq_length
c = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT).get_collection("instrumentos")
res = {"max_seq_length": lim}
for ins in ["59","60","61","109","127","129","130","131"]:
    d = c.get(where={"instrumentoId": ins}, include=["documents", "metadatas"])
    por = collections.defaultdict(lambda: [0, 0, 0])
    for t, md in zip(d["documents"], d["metadatas"]):
        n = len(tok(t)["input_ids"])
        s = md.get("seccion", "?")
        por[s][0] += 1; por[s][1] += n > lim; por[s][2] = max(por[s][2], n)
    res[ins] = {k: {"chunks": v[0], "truncados": v[1], "max_tokens": v[2]} for k, v in por.items()}
print(json.dumps(res, ensure_ascii=False))
