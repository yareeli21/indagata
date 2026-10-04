"""Proxy transparente del api-gateway hacia los microservicios.

El gateway es la única puerta HTTP del frontend. Reenvía el path **tal cual**
(sin traducir inglés↔español ni remapear segmentos) al upstream que corresponde
por prefijo, y devuelve el status y el cuerpo del upstream de forma transparente
(sin envoltorio `{status_code, body}`), para que `pedir()` del frontend reciba el
JSON de dominio directo con el status HTTP real (incluye 401/404/409/422).

Prefijos passthrough:
  - /instrumentos/*   → instrument-service :8001   (GET/POST/DELETE)
  - /almacenamiento/* → storage-service :8004      (GET/POST)
  - /rag/*            → visualization-service :8005 (POST; /rag/chat es SSE)

`analysis-service` lo consume el frontend de forma directa (no se proxea aquí) y
`metadata-service` NO se proxea en esta tanda por alcance (ver design.md §5.2).
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
}

# Headers que NO se reenvían al upstream: httpx los recomputa a partir del cuerpo
# y del destino. Se conserva `Authorization` para el passthrough del JWT.
_HEADERS_A_QUITAR = {"host", "content-length"}


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
