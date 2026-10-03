"""Borrado de instrumentos con regla de propiedad.

Regla de autorización:
  - administrador  → puede borrar CUALQUIER instrumento.
  - investigador   → solo puede borrar los instrumentos que ÉL subió
                     (raw_data.id_owner == su usuario_id). Si no, 403.

Al borrar se elimina la fila `raw_data` (que arrastra en cascada a
`instrumento_procesado` y descendientes vía ON DELETE CASCADE) y los archivos
físicos de `storage/raw` (respondido y original).
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import raw_storage
from shared.auth import ROL_ADMINISTRADOR, ROL_INVESTIGADOR
from shared.models.raw_data import RawData
from shared.models.usuario import Usuario

logger = logging.getLogger(__name__)


def _puede_eliminar(usuario: Usuario, instrumento: RawData) -> bool:
    """Aplica la regla: admin borra todo; investigador solo lo suyo."""
    if usuario.rol == ROL_ADMINISTRADOR:
        return True
    if usuario.rol == ROL_INVESTIGADOR:
        return instrumento.id_owner == usuario.usuario_id
    return False


class DeleteService:
    """Caso de uso: eliminar un instrumento crudo y sus archivos."""

    @staticmethod
    def delete(db: Session, usuario: Usuario, id_crudo: int) -> dict:
        """Elimina el instrumento `id_crudo` si el usuario tiene permiso.

        Returns:
            dict con el id eliminado y los archivos removidos.

        Raises:
            HTTPException 404 si no existe; 403 si no es su dueño (y no es admin).
        """
        instrumento = db.get(RawData, id_crudo)
        if instrumento is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrumento (id_crudo={id_crudo}) no encontrado.",
            )

        if not _puede_eliminar(usuario, instrumento):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes eliminar instrumentos que tú subiste.",
            )

        # Rutas de los archivos a limpiar tras el commit.
        rutas = [instrumento.raw_archivo, instrumento.raw_archivo_original]

        try:
            db.delete(instrumento)  # cascada a instrumento_procesado y descendientes
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Error al eliminar el instrumento %s.", id_crudo)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo eliminar el instrumento.",
            ) from exc

        # Borrar archivos físicos (best-effort: la fila ya se eliminó).
        archivos_borrados: list[str] = []
        for ruta in rutas:
            if ruta:
                raw_storage.delete(ruta)
                archivos_borrados.append(ruta)

        return {
            "id_crudo": id_crudo,
            "archivos_borrados": archivos_borrados,
            "mensaje": "Instrumento eliminado.",
        }
