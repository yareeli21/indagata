"""Proxy transparente del api-gateway hacia los microservicios.

El gateway es la única puerta HTTP del frontend. Reenvía el path **tal cual**
(sin traducir inglés↔español ni remapear segmentos) al upstream que corresponde
por prefijo, y devuelve el status y el cuerpo del upstream de forma transparente
(sin envoltorio `{status_code, body}`), para que `pedir()` del frontend reciba el
JSON de dominio directo con el status HTTP real (incluye 401/404/409/422).

Prefijos passthrough:
  - /instrumentos/*     → instrument-service :8001    (GET/POST/DELETE)
  - /almacenamiento/*   → storage-service :8004       (GET/POST/DELETE; interno: solo administradores)
  - /rag/*              → visualization-service :8005 (POST; /rag/chat es SSE)
  - /visualizacion/*    → visualization-service :8005 (GET/POST: catálogo, KPIs, descargas)
  - /api/metadata/*     → metadata-service :8003      (GET/POST/DELETE)
  - /api/enrichment/*   → metadata-service :8003      (GET/POST/DELETE)
  - /limpieza/*         → cleaning-service :8007      (GET/POST/PATCH: limpieza asistida)
  - /conocimiento/*     → knowledge-service :8009     (GET/POST: perfil semántico y documento final)

`analysis-service` lo consume el frontend de forma directa (no se proxea aquí).
Las cabeceras de descarga del upstream (Content-Disposition, huella SHA-256) se
reenvían para que el navegador conserve el nombre original del archivo.
"""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse

router = APIRouter(tags=["Proxy"])
logger = logging.getLogger(__name__)

SERVICES = {
    "instruments": os.getenv("INSTRUMENT_SERVICE_URL", "http://instrument-service:8001"),
    "analysis": os.getenv("ANALYSIS_SERVICE_URL", "http://analysis-service:8002"),
    "metadata": os.getenv("METADATA_SERVICE_URL", "http://metadata-service:8003"),
    "storage": os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004"),
    "visualization": os.getenv("VISUALIZATION_SERVICE_URL", "http://visualization-service:8005"),
    "cleaning": os.getenv("CLEANING_SERVICE_URL", "http://cleaning-service:8007"),
    "knowledge": os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-service:8009"),
}

# Headers que NO se reenvían al upstream: httpx los recomputa a partir del cuerpo
# y del destino. Se conserva `Authorization` para el passthrough del JWT.
_HEADERS_A_QUITAR = {"host", "content-length"}

# Headers de la respuesta del upstream que sí se devuelven al cliente (descargas).
_HEADERS_RESPUESTA = ("content-disposition", "x-checksum-sha256", "x-nombre-archivo")


def _headers_reenvio(request: Request) -> dict[str, str]:
    """Headers del request original sin `host`/`content-length` (conserva Authorization)."""
    return {k: v for k, v in request.headers.items() if k.lower() not in _HEADERS_A_QUITAR}


async def proxy_request(service: str, path: str, request: Request, method: str) -> Response:
    """Reenvía el request al upstream y devuelve su status+body de forma transparente."""
    url = f"{SERVICES[service]}{path}"
    headers = _headers_reenvio(request)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            method,
            url,
            content=body,
            headers=headers,
            params=request.query_params,
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=120.0, pool=5.0),
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
        headers={h: upstream.headers[h] for h in _HEADERS_RESPUESTA if h in upstream.headers},
    )


def _ruta_upstream(prefijo: str, path: str) -> str:
    """Reconstruye el path para el upstream SIN forzar barra final.

    `path` es el remanente capturado por `{path:path}` (vacío para la ruta base,
    p. ej. `GET /instrumentos`). Se evita añadir un `/` extra para que el upstream
    reciba el path exacto (`/instrumentos`, no `/instrumentos/`).
    """
    return f"{prefijo}/{path}" if path else prefijo


# ---------------------------------------------------------------------------
# Instrumentos → instrument-service :8001 (passthrough del path tal cual).
# Rutas base (`/instrumentos`) y por sub-path (`/instrumentos/...`) explícitas:
# la ruta base evita el redirect 307 de FastAPI y preserva el path exacto.
# ---------------------------------------------------------------------------
@router.get("/instrumentos")
@router.get("/instrumentos/{path:path}")
async def instrumentos_get(request: Request, path: str = "") -> Response:
    return await proxy_request("instruments", _ruta_upstream("/instrumentos", path), request, "GET")


@router.post("/instrumentos")
@router.post("/instrumentos/{path:path}")
async def instrumentos_post(request: Request, path: str = "") -> Response:
    return await proxy_request("instruments", _ruta_upstream("/instrumentos", path), request, "POST")


@router.delete("/instrumentos")
@router.delete("/instrumentos/{path:path}")
async def instrumentos_delete(request: Request, path: str = "") -> Response:
    return await proxy_request("instruments", _ruta_upstream("/instrumentos", path), request, "DELETE")


# ---------------------------------------------------------------------------
# Almacenamiento → storage-service :8004
# ---------------------------------------------------------------------------
@router.get("/almacenamiento")
@router.get("/almacenamiento/{path:path}")
async def almacenamiento_get(request: Request, path: str = "") -> Response:
    return await proxy_request("storage", _ruta_upstream("/almacenamiento", path), request, "GET")


@router.post("/almacenamiento")
@router.post("/almacenamiento/{path:path}")
async def almacenamiento_post(request: Request, path: str = "") -> Response:
    return await proxy_request("storage", _ruta_upstream("/almacenamiento", path), request, "POST")


@router.delete("/almacenamiento/{path:path}")
async def almacenamiento_delete(request: Request, path: str) -> Response:
    return await proxy_request("storage", _ruta_upstream("/almacenamiento", path), request, "DELETE")


# ---------------------------------------------------------------------------
# Visualización (catálogo, KPIs, relacionados, descargas) → visualization-service
# ---------------------------------------------------------------------------
@router.get("/visualizacion/{path:path}")
async def visualizacion_get(request: Request, path: str) -> Response:
    return await proxy_request("visualization", _ruta_upstream("/visualizacion", path), request, "GET")


@router.post("/visualizacion/{path:path}")
async def visualizacion_post(request: Request, path: str) -> Response:
    return await proxy_request("visualization", _ruta_upstream("/visualizacion", path), request, "POST")


# ---------------------------------------------------------------------------
# RAG / visualización → visualization-service :8005
# `/rag/chat` es SSE: se streamea sin bufferizar preservando text/event-stream.
# ---------------------------------------------------------------------------
@router.post("/rag/chat")
async def rag_chat(request: Request) -> StreamingResponse:
    url = f"{SERVICES['visualization']}/rag/chat"
    headers = _headers_reenvio(request)
    body = await request.body()

    async def flujo():
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=None, write=120.0, pool=5.0),
        )
        try:
            async with client.stream(
                "POST", url, content=body, headers=headers, params=request.query_params
            ) as upstream:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
        finally:
            await client.aclose()

    return StreamingResponse(flujo(), media_type="text/event-stream")


@router.post("/rag")
@router.post("/rag/{path:path}")
async def rag_post(request: Request, path: str = "") -> Response:
    return await proxy_request("visualization", _ruta_upstream("/rag", path), request, "POST")


# Métricas automáticas de cada respuesta y consulta registrada (GET /rag/consultas/…).
@router.get("/rag")
@router.get("/rag/{path:path}")
async def rag_get(request: Request, path: str = "") -> Response:
    return await proxy_request("visualization", _ruta_upstream("/rag", path), request, "GET")


# ---------------------------------------------------------------------------
# Metadatos (Dublin Core + aprobación) → metadata-service :8003
# El path se reenvía TAL CUAL (p. ej. `/api/metadata/{id_crudo}/aprobar`). Rutas
# base (`/api/metadata`) y por sub-path explícitas para evitar el redirect 307.
# ---------------------------------------------------------------------------
@router.get("/api/metadata")
@router.get("/api/metadata/{path:path}")
async def metadata_get(request: Request, path: str = "") -> Response:
    return await proxy_request("metadata", _ruta_upstream("/api/metadata", path), request, "GET")


@router.post("/api/metadata")
@router.post("/api/metadata/{path:path}")
async def metadata_post(request: Request, path: str = "") -> Response:
    return await proxy_request("metadata", _ruta_upstream("/api/metadata", path), request, "POST")


@router.delete("/api/metadata")
@router.delete("/api/metadata/{path:path}")
async def metadata_delete(request: Request, path: str = "") -> Response:
    return await proxy_request("metadata", _ruta_upstream("/api/metadata", path), request, "DELETE")


# ---------------------------------------------------------------------------
# Enriquecimiento → metadata-service :8003 (mismo patrón que /api/metadata).
# ---------------------------------------------------------------------------
@router.get("/api/enrichment")
@router.get("/api/enrichment/{path:path}")
async def enrichment_get(request: Request, path: str = "") -> Response:
    return await proxy_request("metadata", _ruta_upstream("/api/enrichment", path), request, "GET")


@router.post("/api/enrichment")
@router.post("/api/enrichment/{path:path}")
async def enrichment_post(request: Request, path: str = "") -> Response:
    return await proxy_request("metadata", _ruta_upstream("/api/enrichment", path), request, "POST")


@router.delete("/api/enrichment")
@router.delete("/api/enrichment/{path:path}")
async def enrichment_delete(request: Request, path: str = "") -> Response:
    return await proxy_request("metadata", _ruta_upstream("/api/enrichment", path), request, "DELETE")


# ---------------------------------------------------------------------------
# Limpieza → cleaning-service :8007 (fase automática, decisiones, confirmación).
# PATCH guarda las decisiones parciales del investigador conforme las toma.
# ---------------------------------------------------------------------------


@router.get("/limpieza")
@router.get("/limpieza/{path:path}")
async def limpieza_get(request: Request, path: str = "") -> Response:
    return await proxy_request("cleaning", _ruta_upstream("/limpieza", path), request, "GET")


@router.post("/limpieza")
@router.post("/limpieza/{path:path}")
async def limpieza_post(request: Request, path: str = "") -> Response:
    return await proxy_request("cleaning", _ruta_upstream("/limpieza", path), request, "POST")


@router.patch("/limpieza")
@router.patch("/limpieza/{path:path}")
async def limpieza_patch(request: Request, path: str = "") -> Response:
    return await proxy_request("cleaning", _ruta_upstream("/limpieza", path), request, "PATCH")


# ---------------------------------------------------------------------------
# Conocimiento → knowledge-service :8009 (perfil semántico, documento final).
# ---------------------------------------------------------------------------


@router.get("/conocimiento")
@router.get("/conocimiento/{path:path}")
async def conocimiento_get(request: Request, path: str = "") -> Response:
    return await proxy_request("knowledge", _ruta_upstream("/conocimiento", path), request, "GET")


@router.post("/conocimiento")
@router.post("/conocimiento/{path:path}")
async def conocimiento_post(request: Request, path: str = "") -> Response:
    return await proxy_request("knowledge", _ruta_upstream("/conocimiento", path), request, "POST")
