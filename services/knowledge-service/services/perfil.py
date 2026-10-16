"""Perfil semántico: lo que describe al instrumento, y nada más.

Es lo único que se usa para asociar KPIs, así que deliberadamente NO contiene
métricas, conteos, respuestas, IDs técnicos (columnas), rutas, formatos, fechas
de carga ni tipos técnicos: todo eso mete ruido en la búsqueda semántica.

Se arma con plantillas determinísticas (sin LLM) a partir de:
  - los metadatos revisados por el autor (Dublin Core + específicos del tipo),
  - la estructura del instrumento (secciones y preguntas, ver `estructura.py`).
Antes de devolverlo se valida contra `esquemas/perfil.json`.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from services.estructura import Estructura, id_instrumento

ESQUEMA_VERSION = "1.0"
_ESQUEMAS = Path(__file__).resolve().parents[1] / "esquemas"
NO_ESPECIFICADO = "No especificado"

# Nivel educativo por palabras clave (el orden importa: «media superior» antes que «superior»).
_NIVELES = (
    ("Posgrado", ("posgrado", "maestria", "doctorado", "especialidad")),
    ("Media superior", ("media superior", "bachillerato", "preparatoria", "bachiller")),
    ("Licenciatura", ("licenciatura", "universidad", "universitari", "pregrado", "educacion superior", "ingenieria")),
    ("Secundaria", ("secundaria",)),
    ("Primaria", ("primaria",)),
    ("Preescolar", ("preescolar", "kinder")),
)


@lru_cache
def _validador() -> Draft202012Validator:
    return Draft202012Validator(json.loads((_ESQUEMAS / "perfil.json").read_text(encoding="utf-8")))


class PerfilInvalido(ValueError):
    """El perfil construido no cumple su JSON Schema (error de programación, no del usuario)."""


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return ", ".join(str(v).strip() for v in valor if str(v).strip())
    return " ".join(str(valor).split())


def _lista(valor: Any) -> list[str]:
    """Listas del formulario: vienen como lista o como texto separado por comas/punto y coma."""
    if valor is None:
        return []
    partes = valor if isinstance(valor, (list, tuple)) else re.split(r"[,;\n]", str(valor))
    return [" ".join(str(p).split()) for p in partes if str(p).strip()]


def _sin_repetidos(valores: list[str]) -> list[str]:
    vistos: set[str] = set()
    salida = []
    for v in valores:
        clave = v.casefold()
        if clave not in vistos:
            vistos.add(clave)
            salida.append(v)
    return salida


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def nivel_educativo(dc: dict[str, Any], esp: dict[str, Any]) -> str:
    """El campo del tipo si existe (pruebas); si no, por palabras clave en cobertura, población y carrera."""
    if _texto(esp.get("nivel_educativo")):
        return _texto(esp.get("nivel_educativo"))
    texto = _sin_acentos(" ".join(_texto(x) for x in (dc.get("dc_coverage"), esp.get("poblacion_objetivo"), esp.get("carrera"), esp.get("grado"))))
    for nivel, palabras in _NIVELES:
        if any(p in texto for p in palabras):
            return nivel
    return NO_ESPECIFICADO


# Frases con métricas o conteos (p. ej. las notas automáticas «20 registros con respuesta;
# 3% de respuestas vacías»): no describen el instrumento y meten ruido en los KPIs.
_FRASE_CON_METRICA = re.compile(r"\d+(?:[.,]\d+)?\s*%|\bregistros?\b|\brespuestas? vac[ií]as\b|\bduplicad|\bcompletitud\b", re.IGNORECASE)


def sin_metricas(texto: str) -> str:
    """Quita las frases que reportan métricas o conteos de los datos."""
    frases = re.split(r"(?<=[.;])\s+|;\s*", _texto(texto))
    return " ".join(f for f in frases if f and not _FRASE_CON_METRICA.search(f)).strip(" .;")


def contexto(tipo: str, dc: dict[str, Any], esp: dict[str, Any]) -> str:
    """Contexto en texto legible (plantilla), solo con los datos que existan."""
    partes = [
        ("Institución", esp.get("institucion") or dc.get("dc_publisher")),
        ("Carrera(s)", esp.get("carrera")),
        ("Cobertura", dc.get("dc_coverage")),
        ("Metodología", esp.get("metodologia")),
        ("Unidad de aprendizaje", esp.get("unidad_de_aprendizaje")),
        ("Tipo de prueba", esp.get("tipo_de_prueba")),
        ("Grado", esp.get("grado")),
        ("Ciclo escolar", esp.get("ciclo_escolar")),
        ("Notas", sin_metricas(_texto(esp.get("notas_contextuales")))),
    ]
    return ". ".join(f"{etq}: {_texto(v)}" for etq, v in partes if _texto(v)).strip()


def construir(id_crudo: int, tipo: str, dc: dict[str, Any], esp: dict[str, Any], estructura: Estructura) -> dict[str, Any]:
    """Perfil semántico validado. `dc` usa claves `dc_*`; `esp` son los campos del tipo."""
    temas = _lista(dc.get("dc_subject")) + _lista(esp.get("dimensiones")) + _lista(esp.get("constructo_principal")) + _lista(esp.get("subareas"))
    palabras = _lista(esp.get("palabras_clave")) or _lista(dc.get("dc_subject"))
    poblacion = _texto(esp.get("poblacion_objetivo")) or ", ".join(
        x for x in (_texto(esp.get("grado")), _texto(esp.get("grupo"))) if x
    )
    secciones = []
    for s in estructura.secciones:
        preguntas = []
        for p in estructura.preguntas:
            if p.seccion_id != s.id:
                continue
            item: dict[str, Any] = {"id": p.id, "texto": p.texto}
            if p.opciones:
                item["opciones"] = list(p.opciones)
            preguntas.append(item)
        if preguntas:
            sec: dict[str, Any] = {"id": s.id, "nombre": s.nombre, "preguntas": preguntas}
            if s.descripcion:
                sec["descripcion"] = s.descripcion
            secciones.append(sec)

    perfil = {
        "esquema_version": ESQUEMA_VERSION,
        "instrumento_id": id_instrumento(id_crudo),
        "tipo": tipo,
        "titulo": _texto(dc.get("dc_title")) or "Instrumento sin título",
        "objetivo": _texto(esp.get("objetivo")) or _texto(esp.get("objetivo_de_evaluacion")) or _texto(dc.get("dc_description")),
        "temas": _sin_repetidos(temas),
        "palabras_clave": _sin_repetidos(palabras),
        "nivel_educativo": nivel_educativo(dc, esp),
        "poblacion": poblacion or NO_ESPECIFICADO,
        "contexto": contexto(tipo, dc, esp),
        "secciones": secciones,
        "kpis_asociados": [],
    }
    errores = sorted(_validador().iter_errors(perfil), key=lambda e: list(e.path))
    if errores:
        raise PerfilInvalido("; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errores[:5]))
    return perfil


def n_preguntas(perfil: dict[str, Any]) -> int:
    return sum(len(s.get("preguntas") or []) for s in perfil.get("secciones") or [])
