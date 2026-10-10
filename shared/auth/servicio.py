"""Tokens de servicio para llamadas internas servicio→servicio.

Los microservicios internos (p. ej. storage-service) exigen un JWT. Cuando un
servicio llama a otro sin un usuario de por medio (p. ej. el instrument-service
guardando el archivo crudo), se identifica con un token de vida corta firmado con
la MISMA SECRET_KEY y con el rol técnico `servicio` (usuario_id = 0).

    from shared.auth.servicio import cabeceras_servicio
    httpx.post(url, headers=cabeceras_servicio(), ...)
"""
from __future__ import annotations

from shared.auth.jwt_handler import TokenData, crear_access_token
from shared.auth.roles import ROL_SERVICIO

# usuario_id reservado para los tokens de servicio (no existe en tt_rag.usuario).
USUARIO_SERVICIO_ID = 0

# Vida corta: el token se genera en cada llamada.
_MINUTOS_VALIDEZ = 5


def crear_token_servicio() -> str:
    """JWT de servicio (rol `servicio`, sub=0) válido unos minutos."""
    return crear_access_token(
        usuario_id=USUARIO_SERVICIO_ID,
        rol=ROL_SERVICIO,
        expires_minutes=_MINUTOS_VALIDEZ,
    )


def cabeceras_servicio() -> dict[str, str]:
    """Cabecera Authorization lista para adjuntar a una petición interna."""
    return {"Authorization": f"Bearer {crear_token_servicio()}"}


def es_token_servicio(datos: TokenData) -> bool:
    """True si el token decodificado pertenece a un servicio interno."""
    return datos.rol == ROL_SERVICIO
