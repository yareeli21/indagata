"""Service proxy endpoints - forward requests to microservices"""

from fastapi import APIRouter, Request, HTTPException
import httpx
import os
import logging

router = APIRouter(tags=["Proxy"])
logger = logging.getLogger(__name__)

SERVICES = {
    "instruments": os.getenv("INSTRUMENT_SERVICE_URL", "http://instrument-service:8001"),
    "analysis": os.getenv("ANALYSIS_SERVICE_URL", "http://analysis-service:8002"),
    "metadata": os.getenv("METADATA_SERVICE_URL", "http://metadata-service:8003"),
    "storage": os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8004"),
    "visualization": os.getenv("VISUALIZATION_SERVICE_URL", "http://visualization-service:8005"),
}

async def proxy_request(service: str, path: str, request: Request, method: str = "GET"):
    """Forward request to microservice"""
    try:
        url = f"{SERVICES[service]}{path}"
        async with httpx.AsyncClient() as client:
            # Forward headers (keep auth tokens, etc.)
            headers = dict(request.headers)
            
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                body = await request.body()
                response = await client.post(url, content=body, headers=headers)
            elif method == "PUT":
                body = await request.body()
                response = await client.put(url, content=body, headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return {
                "status_code": response.status_code,
                "body": response.json() if response.text else {}
            }
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"Service unavailable: {service}")

# Example: Forward instrument endpoints
@router.post("/instruments/upload")
async def upload_instrument(request: Request):
    return await proxy_request("instruments", "/instruments/upload", request, "POST")

@router.get("/instruments/{instrument_id}")
async def get_instrument(instrument_id: int, request: Request):
    return await proxy_request("instruments", f"/instruments/{instrument_id}", request, "GET")

# Add more endpoints as needed...


async def proxy_to_service(service_name: str, endpoint: str):
    url = f"http://{service_name}:PORT/api{endpoint}"
    response = httpx.get(url)
    return response.json()