"""Modelo ORM: rag_log — registro de consultas RAG.

Además de la pregunta y la respuesta guarda:
- la decisión de dominio (`dentro`, `fuera`, `privacidad`, `manipulacion`,
  `sin_informacion`, `ayuda`), su motivo y la similitud máxima con el acervo;
- la ruta del enrutador (`semantica`, `estructurada`, `mixta`, `ayuda`), los
  instrumentos del alcance y los fragmentos que se dieron al LLM;
- las métricas de evaluación automática (RAGAS), que se calculan después de
  responder, con el modelo juez y la fecha.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import SCHEMA, Base


class RagLog(Base):
    __tablename__ = "rag_log"
    __table_args__ = {"schema": SCHEMA}

    rag_log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pregunta: Mapped[str] = mapped_column(Text, nullable=False)
    respuesta: Mapped[str | None] = mapped_column(Text)
    modelo_usado: Mapped[str | None] = mapped_column(String(100))
    chunks_usados: Mapped[int | None] = mapped_column(Integer)
    latencia_ms: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column("timestamp", server_default=func.now())
    decision_dominio: Mapped[str | None] = mapped_column(String(20))
    motivo: Mapped[str | None] = mapped_column(Text)
    score_max: Mapped[float | None] = mapped_column(Float)
    ruta: Mapped[str | None] = mapped_column(String(20))
    instrumentos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    contexto_usado: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    metricas: Mapped[dict | None] = mapped_column(JSONB)
    modelo_juez: Mapped[str | None] = mapped_column(String(100))
    fecha_metricas: Mapped[datetime | None] = mapped_column()
    # Caché: huella de la consulta (una idéntica reutiliza la respuesta) y lo que se mostró.
    clave_cache: Mapped[str | None] = mapped_column(String(64), index=True)
    salida: Mapped[dict | None] = mapped_column(JSONB)
