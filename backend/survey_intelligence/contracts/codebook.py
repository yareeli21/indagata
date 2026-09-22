# survey_intelligence/contracts/codebook.py
"""
Contratos de Codebook (diccionario de datos de microdatos).

Permite mapear identificadores técnicos de columnas (ej. 'P01_1', 'V002', 'EDAD')
a su etiqueta descriptiva real (enunciado de la pregunta), etiquetas de valores
(ej. 1=Sí, 2=No) y tipo de dato, sin depender de LLM ni embeddings.
"""
from __future__ import annotations

import re
import unicodedata
from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")


def _normalize_key(key: str) -> str:
    """Normaliza una clave para búsqueda tolerante (minúsculas, sin acentos, snake_case)."""
    text = key.strip()
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^\w]+", "_", text)
    return text.strip("_")


class CodebookEntry(BaseModel):
    """Definición estructurada de una variable en el codebook."""
    model_config = _FROZEN

    name: str
    label: str
    value_labels: dict[str, str] = Field(default_factory=dict)
    data_type: str | None = None
    missing_values: list[str] = Field(default_factory=list)


class CodebookModel(BaseModel):
    """Diccionario estructurado de variables indexadas por nombre."""
    model_config = _FROZEN

    entries: dict[str, CodebookEntry] = Field(default_factory=dict)

    def lookup(self, identifier: str) -> CodebookEntry | None:
        """
        Búsqueda tolerante de una variable en el codebook.

        Prueba en orden:
          1. Coincidencia exacta de string.
          2. Coincidencia exacta en minúsculas y sin espacios.
          3. Coincidencia de clave normalizada (sin acentos, snake_case).
          4. Tolerancia a prefijos o sufijos si la raíz coincide.
        """
        if not identifier or not self.entries:
            return None

        # 1. Exacto
        if identifier in self.entries:
            return self.entries[identifier]

        # 2. Minúsculas directas
        low = identifier.strip().lower()
        for k, v in self.entries.items():
            if k.strip().lower() == low:
                return v

        # 3. Normalizado
        norm_target = _normalize_key(identifier)
        for k, v in self.entries.items():
            if _normalize_key(k) == norm_target or _normalize_key(v.name) == norm_target:
                return v

        # 4. Tolerancia de sufijo/prefijo
        for k, v in self.entries.items():
            norm_k = _normalize_key(k)
            if (norm_target.endswith(norm_k) or norm_k.endswith(norm_target)) and len(norm_k) >= 3 and len(norm_target) >= 3:
                return v

        return None
