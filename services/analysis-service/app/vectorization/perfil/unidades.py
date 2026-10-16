"""Unidades de texto del perfil semántico que se embeben para asociar KPIs.

Nunca se embebe el JSON: cada unidad es texto legible con plantilla, en el mismo
estilo que el `texto_contexto_rag_vectorial` de los KPIs.

  U₀  perfil general:  «Instrumento: … / Tipo: … / Objetivo: … / Temas: … / …»
  Uᵢ  una por pregunta: «Sección: … / Pregunta: … / Opciones: …»

Se eligen preguntas (no secciones) porque la evidencia de cada KPI debe nombrar
preguntas concretas; una sección promedia temas y diluye la similitud. Los
reactivos sin texto real («Reactivo P1») no forman unidad: no dicen nada.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TIPO_UI = {"encuesta": "Encuesta", "entrevista": "Entrevista", "prueba_estandarizada": "Prueba estandarizada"}
_SIN_TEXTO = re.compile(r"^reactivo\s+\S+$", re.IGNORECASE)
_MAX_OPCIONES = 12


@dataclass(frozen=True)
class UnidadPregunta:
    pregunta_id: str
    seccion: str
    texto: str  # texto de la pregunta (para mostrar)
    unidad: str  # texto completo que se embebe


def _lista(valores: Any) -> str:
    return ", ".join(str(v) for v in valores or [] if str(v).strip())


def texto_general(perfil: dict[str, Any]) -> str:
    """U₀: el perfil general en texto legible (solo los campos con valor)."""
    lineas = [
        ("Instrumento", perfil.get("titulo")),
        ("Tipo", _TIPO_UI.get(perfil.get("tipo") or "", perfil.get("tipo"))),
        ("Objetivo", perfil.get("objetivo")),
        ("Temas", _lista(perfil.get("temas"))),
        ("Palabras clave", _lista(perfil.get("palabras_clave"))),
        ("Nivel educativo", perfil.get("nivel_educativo")),
        ("Población", perfil.get("poblacion")),
        ("Contexto", perfil.get("contexto")),
    ]
    return "\n".join(f"{etq}: {valor}" for etq, valor in lineas if valor and str(valor).strip() and valor != "No especificado")


def unidades_pregunta(perfil: dict[str, Any]) -> list[UnidadPregunta]:
    """Uᵢ: una unidad por pregunta con texto real, con su sección y opciones."""
    salida: list[UnidadPregunta] = []
    for seccion in perfil.get("secciones") or []:
        nombre = str(seccion.get("nombre") or "")
        for p in seccion.get("preguntas") or []:
            texto = " ".join(str(p.get("texto") or "").split())
            if not texto or _SIN_TEXTO.match(texto):
                continue
            partes = []
            if nombre and nombre.lower() not in {"general", "reactivos"}:
                partes.append(f"Sección: {nombre}")
            partes.append(f"Pregunta: {texto}")
            opciones = (p.get("opciones") or [])[:_MAX_OPCIONES]
            if opciones:
                partes.append(f"Opciones: {_lista(opciones)}")
            salida.append(UnidadPregunta(str(p.get("id")), nombre, texto, "\n".join(partes)))
    return salida
