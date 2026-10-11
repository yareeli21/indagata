"""Visor read-only de ChromaDB.

Se conecta por HTTP a la instancia Chroma del stack (host `chromadb`, puerto 8000,
API v2 vía chromadb.HttpClient), lee TODAS las colecciones, apila sus embeddings,
los proyecta a 2D con PCA y los expone para pintar un dispersograma coloreado por
colección. NO escribe en Chroma. No toca ningún microservicio.
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from sklearn.decomposition import PCA

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

app = FastAPI(title="Indagata · Visor de vectores Chroma", docs_url=None, redoc_url=None)


def _client():
    import chromadb

    return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)


def _label_for(coleccion: str, meta: dict[str, Any] | None, doc: str | None, pid: str) -> str:
    meta = meta or {}
    if coleccion == "kpis":
        return str(meta.get("nombre") or doc or pid)
    # summary_instrument u otras
    for k in ("titulo", "Título", "nombre_archivo", "id_instrumento"):
        if meta.get(k):
            return str(meta[k])
    return str(pid)


def _gather() -> list[dict[str, Any]]:
    """Lee todas las colecciones, aplica PCA conjunto y devuelve puntos 2D."""
    client = _client()
    puntos: list[dict[str, Any]] = []
    vectores: list[list[float]] = []

    for col in client.list_collections():
        nombre = col.name
        data = col.get(include=["embeddings", "metadatas", "documents"])
        ids = data.get("ids") or []
        embs = data.get("embeddings")
        metas = data.get("metadatas") or [None] * len(ids)
        docs = data.get("documents") or [None] * len(ids)
        if embs is None:
            continue
        for i, pid in enumerate(ids):
            emb = embs[i]
            if emb is None:
                continue
            vectores.append(list(emb))
            puntos.append({
                "id": str(pid),
                "coleccion": nombre,
                "label": _label_for(nombre, metas[i] if i < len(metas) else None,
                                    docs[i] if i < len(docs) else None, str(pid)),
            })

    if not vectores:
        return []

    arr = np.asarray(vectores, dtype=float)
    n_comp = 2 if arr.shape[0] >= 2 and arr.shape[1] >= 2 else 1
    coords = PCA(n_components=n_comp).fit_transform(arr)
    for j, p in enumerate(puntos):
        p["x"] = float(coords[j, 0])
        p["y"] = float(coords[j, 1]) if n_comp == 2 else 0.0
    return puntos


@app.get("/api/points")
def api_points() -> JSONResponse:
    try:
        pts = _gather()
    except Exception as exc:  # noqa: BLE001 -- visor de diagnóstico, reporta el error tal cual
        return JSONResponse({"error": str(exc), "points": []}, status_code=502)
    resumen: dict[str, int] = {}
    for p in pts:
        resumen[p["coleccion"]] = resumen.get(p["coleccion"], 0) + 1
    return JSONResponse({"count": len(pts), "collections": resumen, "points": pts})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


INDEX_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Indagata · Mapa de vectores (ChromaDB)</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <style>
    body { margin:0; font-family: system-ui, sans-serif; background:#0f1116; color:#e8e8ea; }
    header { padding:14px 20px; border-bottom:1px solid #262a35; }
    header h1 { margin:0; font-size:16px; font-weight:600; }
    header p { margin:4px 0 0; font-size:12px; color:#9aa0ad; }
    #plot { width:100%; height:calc(100vh - 110px); }
    #status { padding:8px 20px; font-size:12px; color:#9aa0ad; }
  </style>
</head>
<body>
  <header>
    <h1>Mapa de vectores · ChromaDB</h1>
    <p>Proyección PCA 2D de los embeddings (768-dim) por colección. Visor read-only.</p>
  </header>
  <div id="status">Cargando puntos…</div>
  <div id="plot"></div>
  <script>
    async function load() {
      const status = document.getElementById('status');
      try {
        const res = await fetch('./api/points');
        const data = await res.json();
        if (data.error) { status.textContent = 'Error leyendo Chroma: ' + data.error; return; }
        const byCol = {};
        for (const p of data.points) {
          (byCol[p.coleccion] = byCol[p.coleccion] || {x:[],y:[],text:[]});
          byCol[p.coleccion].x.push(p.x);
          byCol[p.coleccion].y.push(p.y);
          byCol[p.coleccion].text.push(p.label + '  (' + p.id + ')');
        }
        const traces = Object.keys(byCol).map(name => ({
          x: byCol[name].x, y: byCol[name].y, text: byCol[name].text,
          mode: 'markers', type: 'scattergl', name: name,
          marker: { size: 9, opacity: 0.85 },
          hovertemplate: '<b>%{text}</b><br>' + name + '<extra></extra>'
        }));
        const summary = Object.entries(data.collections).map(([k,v]) => k+': '+v).join('  ·  ');
        status.textContent = 'Total ' + data.count + ' puntos  ·  ' + summary;
        Plotly.newPlot('plot', traces, {
          paper_bgcolor:'#0f1116', plot_bgcolor:'#0f1116',
          font:{color:'#e8e8ea'}, legend:{orientation:'h'},
          margin:{l:40,r:20,t:20,b:40},
          xaxis:{title:'PC1', gridcolor:'#262a35', zeroline:false},
          yaxis:{title:'PC2', gridcolor:'#262a35', zeroline:false}
        }, {responsive:true});
      } catch (e) { status.textContent = 'Error: ' + e; }
    }
    load();
  </script>
</body>
</html>
"""
