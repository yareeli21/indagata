"""Modelo ORM: version_conocimiento — una versión del conocimiento de un instrumento.

La escribe knowledge-service (perfil semántico y documento final) y analysis-service
(decisiones de KPIs). Avanza por el wizard:

    perfil_aprobado → kpis_confirmados → borrador → vigente   (la anterior → reemplazado)

- `perfil`: perfil semántico (título, objetivo, temas, preguntas por sección…).
  Al confirmar los KPIs incluye `kpis_asociados` (solo los aceptados).
- `decisiones_kpi`: todos los KPIs propuestos, aceptados y rechazados.
- `ruta_documento`: key en storage-service del documento final (no va en la base).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base

# Vocabulario cerrado del CHECK de `estado` (ver shared/schemas/version_conocimiento.py).
ESTADOS_CONOCIMIENTO = ("perfil_aprobado", "kpis_confirmados", "borrador", "vigente", "reemplazado")


class VersionConocimiento(Base):
    __tablename__ = "version_conocimiento"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('perfil_aprobado', 'kpis_confirmados', 'borrador', 'vigente', 'reemplazado')",
            name="ck_version_conocimiento_estado",
        ),
        UniqueConstraint("id_crudo", "version", name="uq_version_conocimiento"),
        {"schema": SCHEMA},
    )

    id_version: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="perfil_aprobado")
    perfil: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # DEFAULT '[]' (sin ::jsonb) para que create_all funcione también en SQLite (pruebas).
    decisiones_kpi: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    ruta_documento: Mapped[str | None] = mapped_column(String(255))
    esquema_version: Mapped[str | None] = mapped_column(String(10))
    avisos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    sha256: Mapped[str | None] = mapped_column(String(64))
    id_limpieza: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.limpieza_ejecucion.id_limpieza", ondelete="SET NULL")
    )
    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="SET NULL")
    )
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=func.now())
    fecha_kpis: Mapped[datetime | None] = mapped_column()
    fecha_documento: Mapped[datetime | None] = mapped_column()
    fecha_publicacion: Mapped[datetime | None] = mapped_column()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VersionConocimiento id_crudo={self.id_crudo} v{self.version} estado={self.estado!r}>"
