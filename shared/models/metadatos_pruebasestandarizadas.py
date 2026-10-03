"""Modelo ORM: metadatos_enriquecidos_pruebas — hija de raw_data."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class MetadatosEnriquecidosPruebas(Base):
    __tablename__ = "metadatos_enriquecidos_pruebas"
    __table_args__ = {"schema": SCHEMA}

    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"),
        primary_key=True,
    )
    unidad_de_aprendizaje: Mapped[str | None] = mapped_column(Text)
    mapeo_de_reactivos_por_seccion: Mapped[dict | None] = mapped_column(JSONB)
    institucion: Mapped[str | None] = mapped_column(Text)
    campus: Mapped[str | None] = mapped_column(Text)
    grado: Mapped[str | None] = mapped_column(Text)
    grupo: Mapped[str | None] = mapped_column(Text)
    ciclo_escolar: Mapped[str | None] = mapped_column(Text)
    tipo_de_prueba: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(Text)
    taxonomia_bloom: Mapped[str | None] = mapped_column(Text)
    nivel_educativo: Mapped[str | None] = mapped_column(Text)
    objetivo_de_evaluacion: Mapped[str | None] = mapped_column(Text)
    subareas: Mapped[str | None] = mapped_column(Text)
    competencias: Mapped[str | None] = mapped_column(Text)
