"""Modelo ORM: tiempo_proceso — tiempo de cómputo de cada paso del procesamiento de un instrumento.

Una fila por operación automática (carga, limpieza, metadatos, aprobación, perfil, KPIs, documento,
indexación…), escrita por el servicio que la hace con `shared.tiempos.medir`. Solo mide el cómputo:
el tiempo que la investigadora tarda en decidir queda fuera, y sirve para estimar cuánto tardaría
el procesamiento en un servidor.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class TiempoProceso(Base):
    __tablename__ = "tiempo_proceso"
    __table_args__ = {"schema": SCHEMA}

    tiempo_proceso_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_crudo: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"), nullable=False)
    servicio: Mapped[str] = mapped_column(String(40), nullable=False)
    paso: Mapped[str] = mapped_column(String(60), nullable=False)
    inicio: Mapped[datetime] = mapped_column(nullable=False)
    fin: Mapped[datetime] = mapped_column(nullable=False)
    duracion_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    detalle: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'"))
