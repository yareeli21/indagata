"""Router — BORRADO de instrumentos (con regla de propiedad).

  DELETE /instrumentos/{id_crudo}
    - administrador: borra cualquier instrumento.
    - investigador:  borra solo los que él subió (si no, 403).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import DBSession, require_rol
from app.services.delete_service import DeleteService
from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR
from shared.models.usuario import Usuario

router = APIRouter(prefix="/instrumentos", tags=["carga-instrumentos"])

# Borrar requiere, como mínimo, un rol que pueda haber subido instrumentos.
# La regla fina (solo lo propio para investigador) la aplica el servicio.
UsuarioQuePuedeBorrar = Annotated[
    Usuario, Depends(require_rol(ROL_INVESTIGADOR, ROL_ADMINISTRADOR))
]


@router.delete(
    "/{id_crudo}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un instrumento (solo el dueño, o un administrador)",
    description=(
        "Elimina el instrumento crudo y sus archivos. Un **administrador** puede "
        "borrar cualquiera; un **investigador** solo los que él mismo subió "
        "(si intenta borrar uno ajeno recibe 403)."
    ),
)
def eliminar_instrumento(
    usuario_actual: UsuarioQuePuedeBorrar,
    db: DBSession,
    id_crudo: int,
) -> dict:
    return DeleteService.delete(db, usuario_actual, id_crudo)
