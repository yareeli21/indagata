# app/services/services_compartidos.py
"""
Servicios de infraestructura compartidos por carga y visualización.

  ArchivoService   — operaciones de disco (guardar, leer, eliminar, hash)
  PermissionService — verificación de propietario y acceso

No contienen lógica de negocio específica de ningún flujo.
Se importan desde services_carga.py y services_visualizacion.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.models_instrumentos import InstrumentoProcesado, PermisoInstrumento, Usuario

# Formatos de entrada por tipo de instrumento.
#   - Encuestas:  tabulares (.csv/.xlsx/.xls) -> el SIS genera el .SAV de salida.
#   - Entrevistas / pruebas estandarizadas: documentos (.pdf/.txt/.docx).
FORMATOS_POR_TIPO = {
    "encuesta": {".csv", ".xlsx", ".xls"},
    "entrevista": {".pdf", ".txt", ".docx"},
    "prueba_estandarizada": {".pdf", ".txt", ".docx"},
}
# Formatos aceptados para el codebook opcional (solo encuestas): diccionario de datos.
FORMATOS_CODEBOOK = {".csv", ".pdf"}
# Unión de todos los formatos de entrada admitidos (fallback / validación genérica).
EXTENSIONES_PERMITIDAS = set().union(*FORMATOS_POR_TIPO.values())


class ArchivoService:
    """Todas las operaciones sobre archivos físicos en disco."""

    @staticmethod
    def calcular_hash_md5(contenido: bytes) -> str:
        return hashlib.md5(contenido).hexdigest()

    @staticmethod
    def generar_nombre_unico(instrumento_id: int, nombre_original: str) -> str:
        extension = Path(nombre_original).suffix.lower()
        ts  = int(datetime.now(timezone.utc).timestamp())
        uid = uuid.uuid4().hex[:8]
        return f"{instrumento_id}_{ts}_{uid}{extension}"

    @staticmethod
    def guardar_archivo(contenido: bytes, directorio: Path, nombre: str) -> Path:
        directorio.mkdir(parents=True, exist_ok=True)
        ruta = directorio / nombre
        ruta.write_bytes(contenido)
        return ruta

    @staticmethod
    def ruta_relativa(ruta_abs: Path) -> str:
        return str(ruta_abs.relative_to(settings.PROJECT_ROOT))

    @staticmethod
    def ruta_absoluta(ruta_rel: str) -> Path:
        return settings.PROJECT_ROOT / ruta_rel

    @staticmethod
    def eliminar_archivo(ruta: Path) -> None:
        try:
            ruta.unlink()
        except FileNotFoundError:
            pass

    @staticmethod
    def validar_formato(
        nombre_archivo: str,
        tipo_mime: str | None,
        tipo_instrumento: str | None = None,
    ) -> None:
        """
        Valida la extensión del archivo según el tipo de instrumento.

        - encuesta: .csv, .xlsx, .xls (el .SAV es salida, no entrada).
        - entrevista / prueba_estandarizada: .pdf, .txt, .docx.
        - Sin tipo (validación genérica): cualquiera de los formatos admitidos.
        """
        ext = Path(nombre_archivo).suffix.lower()
        permitidos = FORMATOS_POR_TIPO.get(tipo_instrumento or "", EXTENSIONES_PERMITIDAS)
        if ext not in permitidos:
            legibles = ", ".join(sorted(permitidos))
            sufijo = f" para '{tipo_instrumento}'" if tipo_instrumento else ""
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Formato no permitido{sufijo}: '{ext}'. Se aceptan: {legibles}.",
            )

    @staticmethod
    def validar_formato_codebook(nombre_archivo: str) -> None:
        """Valida la extensión del codebook opcional (encuestas): .csv o .pdf."""
        ext = Path(nombre_archivo).suffix.lower()
        if ext not in FORMATOS_CODEBOOK:
            legibles = ", ".join(sorted(FORMATOS_CODEBOOK))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Formato de codebook no permitido: '{ext}'. Se aceptan: {legibles}.",
            )

    @staticmethod
    def escribir_json_atomico(ruta: Path, datos: dict[str, Any]) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=ruta.parent, suffix=".tmp", delete=False, encoding="utf-8"
        ) as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            nombre_temp = f.name
        os.replace(nombre_temp, ruta)


class PermissionService:
    """Verificación de propietario y acceso a instrumentos."""

    @staticmethod
    def crear_propietario(db: Session, instrumento_id: int, usuario_id: int) -> PermisoInstrumento:
        permiso = PermisoInstrumento(instrumento_id=instrumento_id, usuario_id=usuario_id)
        db.add(permiso)
        db.flush()
        return permiso

    @staticmethod
    def es_propietario(db: Session, instrumento_id: int, usuario_id: int) -> bool:
        return (
            db.query(PermisoInstrumento)
            .filter(
                PermisoInstrumento.instrumento_id == instrumento_id,
                PermisoInstrumento.usuario_id == usuario_id,
            )
            .first()
        ) is not None

    @staticmethod
    def obtener_nombre_propietario(db: Session, instrumento_id: int) -> str | None:
        return (
            db.query(Usuario.usuario)
            .join(PermisoInstrumento, PermisoInstrumento.usuario_id == Usuario.usuario_id)
            .filter(PermisoInstrumento.instrumento_id == instrumento_id)
            .scalar()
        )
