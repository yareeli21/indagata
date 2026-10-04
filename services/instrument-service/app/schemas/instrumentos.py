"""Schemas Pydantic v2 del listado/consulta de instrumentos.

`InstrumentoDTO` espeja el tipo `Instrumento` del frontend
(`pixel-perfect-pixel/src/types/index.ts`): sus 12 campos de dominio con el `id`
canónico = `str(id_crudo)` (diseño §2.1), más el campo informativo `idProcesado`
(= `str(id_instrumento)`), que el frontend ignora al mapear a `Instrumento`.

Los literales de `tipo` (§2.4), `estado` (§2.5) y `nivel` (§2.3a) son uniones
cerradas idénticas a las del frontend, de modo que la respuesta siempre es
asignable al contrato de tipos de la UI.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Uniones cerradas espejadas del frontend (TipoInstrumento / EstadoInstrumento /
# NivelEducativo). Mantener en sincronía con src/types/index.ts.
TipoInstrumentoDTO = Literal["Encuesta", "Entrevista", "Prueba estandarizada"]
EstadoInstrumentoDTO = Literal["Borrador", "En revisión", "Estandarizado"]
NivelEducativoDTO = Literal["Licenciatura", "Posgrado"]


class InstrumentoDTO(BaseModel):
    """Representación de un instrumento para el frontend (map DB + JSON)."""

    id: str
    titulo: str
    tipo: TipoInstrumentoDTO
    nivel: NivelEducativoDTO
    autorId: str
    anio: int
    # Fecha ISO AAAA-MM-DD.
    fecha: str
    kpis: list[str]
    reactivos: int
    estado: EstadoInstrumentoDTO
    descripcion: str
    etiquetas: list[str]
    # Campo informativo = str(id_instrumento); el frontend lo descarta al mapear.
    idProcesado: str | None = None
