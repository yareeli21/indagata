"""Modelo ORM: limpieza_ejecucion — una ejecución (versión) de la limpieza.

La escribe cleaning-service; metadata-service lee la última fila `confirmada`
de cada instrumento. El CSV limpio NO se guarda aquí: vive en storage-service y
`ruta_csv_limpio` es su key. `reporte` es el reporte_limpieza completo (métricas,
transformaciones, hallazgos y decisiones del investigador).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base

# Vocabulario cerrado del CHECK de `estado` (ver shared/schemas/limpieza_ejecucion.py).
ESTADOS_LIMPIEZA = ("esperando_decisiones", "confirmada", "fallida")


class LimpiezaEjecucion(Base):
    __tablename__ = "limpieza_ejecucion"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('esperando_decisiones', 'confirmada', 'fallida')",
            name="ck_limpieza_estado",
        ),
        UniqueConstraint("id_crudo", "version", name="uq_limpieza_version"),
        {"schema": SCHEMA},
    )

    id_limpieza: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="esperando_decisiones")
    id_investigador: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.usuario.usuario_id", ondelete="SET NULL"),
    )
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=func.now())
    fecha_confirmacion: Mapped[datetime | None] = mapped_column()
    ruta_csv_limpio: Mapped[str | None] = mapped_column(String(255))
    # DEFAULT '{}' (sin ::jsonb) para que create_all funcione también en SQLite
    # (pruebas de todos los servicios); Postgres lo convierte a jsonb solo.
    reporte: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'")
    )
    error: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<LimpiezaEjecucion id_crudo={self.id_crudo} v{self.version} "
            f"estado={self.estado!r}>"
        )
