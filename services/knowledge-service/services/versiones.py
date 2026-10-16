"""Versiones del conocimiento (`tt_rag.version_conocimiento`): una fila por versión.

Ciclo de estados de una fila:
    perfil_aprobado → kpis_confirmados → borrador → vigente
Al crear una versión nueva, las versiones anteriores que NO están vigentes pasan a
`reemplazado` (quedaron a medio camino); la vigente sigue vigente hasta que se
publique otra (fase 5), para que el instrumento nunca se quede sin documento.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.models.usuario import Usuario
from shared.models.version_conocimiento import VersionConocimiento

_EN_CURSO = ("perfil_aprobado", "kpis_confirmados", "borrador")


def _ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def actual(db: Session, id_crudo: int) -> VersionConocimiento | None:
    """La versión más reciente que no fue reemplazada (en curso o vigente)."""
    return (
        db.query(VersionConocimiento)
        .filter(VersionConocimiento.id_crudo == id_crudo, VersionConocimiento.estado != "reemplazado")
        .order_by(VersionConocimiento.version.desc())
        .first()
    )


def crear_con_perfil(
    db: Session,
    id_crudo: int,
    perfil: dict[str, Any],
    usuario: Usuario,
    *,
    id_limpieza: int | None,
    avisos: list[dict[str, Any]],
) -> VersionConocimiento:
    """Versión N+1 con el perfil recién aprobado; las versiones en curso anteriores se reemplazan."""
    ultima = db.query(func.max(VersionConocimiento.version)).filter(VersionConocimiento.id_crudo == id_crudo).scalar() or 0
    (
        db.query(VersionConocimiento)
        .filter(VersionConocimiento.id_crudo == id_crudo, VersionConocimiento.estado.in_(_EN_CURSO))
        .update({"estado": "reemplazado"}, synchronize_session=False)
    )
    fila = VersionConocimiento(
        id_crudo=id_crudo,
        version=ultima + 1,
        estado="perfil_aprobado",
        perfil=perfil,
        decisiones_kpi=[],
        avisos=avisos,
        id_limpieza=id_limpieza,
        id_usuario=usuario.usuario_id,
        fecha_creacion=_ahora(),
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila
