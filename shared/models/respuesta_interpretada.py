"""Modelo ORM: respuesta_interpretada — respuestas del documento final en formato largo.

Una fila por respuesta (respondente × pregunta) del documento final VIGENTE de un
instrumento. La escribe knowledge-service al publicar el documento (reemplaza las
filas del instrumento) y la lee visualization-service para conteos y porcentajes
exactos del chat, también entre varios instrumentos.

- encuesta:   `valor`/`significado`/`nivel` de la escala (acuerdo, desacuerdo…)
- prueba:     opción elegida, su significado y `nivel` correcta/incorrecta
- entrevista: la respuesta (texto) de cada participante a cada pregunta
`contexto` guarda los datos del respondente (turno, carrera…) para filtrar por grupo.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class RespuestaInterpretada(Base):
    __tablename__ = "respuesta_interpretada"
    __table_args__ = (
        Index("idx_respuesta_crudo_pregunta", "id_crudo", "pregunta_id"),
        Index("idx_respuesta_crudo_respondente", "id_crudo", "respondente_id"),
        {"schema": SCHEMA},
    )

    id_respuesta: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_crudo: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.raw_data.id_crudo", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    respondente_id: Mapped[str] = mapped_column(String(40), nullable=False)
    pregunta_id: Mapped[str] = mapped_column(String(40), nullable=False)
    valor: Mapped[str | None] = mapped_column(Text)
    significado: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[str | None] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    contexto: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'"))
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=func.now())
