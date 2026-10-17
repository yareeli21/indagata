"""Router del documento final (prefijo `/conocimiento`, expuesto en el api-gateway).

- POST /conocimiento/{id_crudo}/documento                    genera y guarda el documento (borrador)
- GET  /conocimiento/{id_crudo}/documento                    vista ligera del documento actual
- GET  /conocimiento/{id_crudo}/documento/json               el documento completo («Ver JSON»)
- POST /conocimiento/{id_crudo}/documento/{version}/publicar  lo marca como vigente
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.orm import sessionmaker

from dependencies import DBSession, Investigador
from models import DocumentoOut, PublicadoOut
from services import documentos

router = APIRouter(prefix="/conocimiento", tags=["documento final"])


def _salida(fila, doc: dict[str, Any]) -> DocumentoOut:  # noqa: ANN001
    return DocumentoOut(
        id_crudo=fila.id_crudo,
        version=fila.version,
        estado=fila.estado,
        esquema_version=fila.esquema_version or doc.get("esquema_version", ""),
        sha256=fila.sha256,
        fecha_documento=fila.fecha_documento,
        avisos=[a for a in doc.get("avisos") or []],
        documento=documentos.vista(doc),
    )


@router.post("/{id_crudo}/documento", response_model=DocumentoOut, summary="Genera y guarda el documento final (borrador)")
def generar(id_crudo: int, db: DBSession, usuario: Investigador) -> DocumentoOut:
    fila, doc = documentos.generar(db, usuario, id_crudo)
    return _salida(fila, doc)


@router.get("/{id_crudo}/documento", response_model=DocumentoOut, summary="Documento final de la versión actual")
def obtener(id_crudo: int, db: DBSession, usuario: Investigador) -> DocumentoOut:
    fila, doc = documentos.leer(db, usuario, id_crudo)
    return _salida(fila, doc)


@router.get("/{id_crudo}/documento/json", summary="Documento final completo (JSON)")
def obtener_json(id_crudo: int, db: DBSession, usuario: Investigador) -> dict[str, Any]:
    _, doc = documentos.leer(db, usuario, id_crudo)
    return doc


@router.post("/{id_crudo}/documento/{version}/publicar", response_model=PublicadoOut, summary="Publica el documento final (vigente)")
def publicar(id_crudo: int, version: int, db: DBSession, usuario: Investigador, tareas: BackgroundTasks) -> PublicadoOut:
    fila = documentos.publicar(db, usuario, id_crudo, version)
    # La reingesta al RAG va después de responder (puede tardar minutos en CPU).
    tareas.add_task(documentos.reingerir, sessionmaker(bind=db.get_bind(), future=True), fila.id_crudo, fila.version)
    return PublicadoOut(id_crudo=fila.id_crudo, version=fila.version, estado=fila.estado, fecha_publicacion=fila.fecha_publicacion)
