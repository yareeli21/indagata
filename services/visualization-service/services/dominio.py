"""Dominio acotado del chat RAG: qué se responde y qué no (antes y después del LLM).

Capas (la definición aprobada está en `config/dominio.yaml`):

  1a. Reglas de intención, sin modelo: privacidad (reidentificar a alguien),
      manipulación (cambiar las reglas, ver el prompt) y tareas fuera del dominio
      (poemas, recetas, traducciones…). Se rechazan al instante.
  1b. Similitud: la pregunta se compara con los chunks del alcance (lo hace
      `rag_service`), con las ANCLAS curadas (glosario metodológico y ayuda de la
      plataforma, embebidas en memoria) y con el catálogo de KPIs (solo lectura).
  1c. Clasificador en la zona gris: si la similitud es ambigua y ninguna regla
      decidió, una llamada corta a Ollama (JSON, temperatura 0) decide si la
      pregunta es del dominio. Si Ollama falla, la pregunta sigue (decide el prompt).
  2.  El prompt del sistema (`prompt.py`) con los datos delimitados como <datos>.
  3.  Después de generar: se tachan correos, teléfonos y matrículas.

La similitud sola no basta: mide de qué TEMA habla la pregunta, no qué PIDE
(«escribe un poema sobre la motivación» se parece mucho al acervo). Por eso las
reglas de intención van primero.
"""
from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_CONFIG = Path(__file__).resolve().parents[1] / "config"

# Decisiones posibles (se guardan en rag_log.decision_dominio).
DENTRO, FUERA, PRIVACIDAD, MANIPULACION, SIN_INFORMACION, AYUDA = (
    "dentro", "fuera", "privacidad", "manipulacion", "sin_informacion", "ayuda",
)


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni signos de apertura y con espacios simples."""
    sin = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().replace("¿", " ").replace("¡", " ").split())


@lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    """`dominio.yaml` + `ayuda.yaml`, con los patrones ya compilados."""
    dominio = yaml.safe_load((_CONFIG / "dominio.yaml").read_text(encoding="utf-8"))
    ayuda = yaml.safe_load((_CONFIG / "ayuda.yaml").read_text(encoding="utf-8"))
    dominio["_patrones"] = {
        clave: [re.compile(p) for p in lista] for clave, lista in (dominio.get("patrones") or {}).items()
    }
    dominio["ayuda"] = ayuda.get("entradas") or []
    return dominio


# ── Capa 1a: reglas de intención ───────────────────────────────────────────────

# Orden de evaluación: lo más grave primero.
_ORDEN = ((PRIVACIDAD, "privacidad"), (MANIPULACION, "manipulacion"), (FUERA, "fuera"))


def reglas(pregunta: str) -> tuple[str, str] | None:
    """(decisión, motivo) si una regla de intención decide la pregunta; si no, None."""
    texto = normalizar(pregunta)
    for decision, clave in _ORDEN:
        for patron in config()["_patrones"].get(clave, []):
            if patron.search(texto):
                return decision, f"regla:{clave}"
    return None


# Preguntas sobre cómo usar la plataforma (van a la base de ayuda, no a Chroma).
_AYUDA = re.compile(
    r"\b(como|donde|en que parte|que pasos|que hago|para que sirve)\b.{0,40}"
    r"\b(subo|subir|cargo|cargar|apruebo|aprobar|descargo|descargar|uso|usar|elijo|elegir|armo|armar|acepto|"
    r"aceptar|rechazo|rechazar|confirmo|confirmar|veo|ver|encuentro|limpio|limpiar|guardo|guardar|registro|"
    r"publico|publicar|edito|editar|selecciono|seleccionar)\b"
    r"|\b(indagata|la plataforma|el asistente de carga|paso [1-7]|el menu|gestion de usuarios|espacio vectorial|"
    r"armar investigacion|mis instrumentos)\b"
    r"|\bno (me )?aparece\b"
)
# Preguntas de definición metodológica (van al glosario, además de a los datos).
_DEFINICION = re.compile(r"\b(que es|que son|que significa|que mide|como se interpreta|como interpreto|para que sirve)\b")


def es_ayuda(pregunta: str) -> bool:
    return bool(_AYUDA.search(normalizar(pregunta)))


def es_definicion(pregunta: str) -> bool:
    return bool(_DEFINICION.search(normalizar(pregunta)))


# ── Capa 1b: anclas curadas (glosario y ayuda) ─────────────────────────────────


@dataclass(frozen=True)
class Ancla:
    tipo: str  # glosario | ayuda | fuente_kpi
    titulo: str
    texto: str
    claves: tuple[str, ...] = ()
    url: str = ""  # fuente_kpi: enlace a la fuente de referencia

    @property
    def cita(self) -> str:
        etiqueta = {"glosario": "Glosario", "ayuda": "Ayuda", "fuente_kpi": "Fuente KPI"}.get(self.tipo, "Ayuda")
        return f"[{etiqueta}: {self.titulo}]"


@lru_cache(maxsize=1)
def anclas() -> tuple[Ancla, ...]:
    cfg = config()
    glosario = [Ancla("glosario", g["termino"], " ".join(g["texto"].split()), tuple(g.get("sinonimos") or []))
                for g in cfg.get("glosario") or []]
    ayuda = [Ancla("ayuda", a["titulo"], " ".join(a["texto"].split()), tuple(a.get("claves") or []))
             for a in cfg.get("ayuda") or []]
    return tuple(glosario + ayuda)


_vectores_anclas: list[list[float]] | None = None


def _vectores() -> list[list[float]]:
    """Embeddings de las anclas (una vez por proceso; nunca se escriben en Chroma)."""
    global _vectores_anclas
    if _vectores_anclas is None:
        from services import vectores

        _vectores_anclas = vectores.embed_texts([f"{a.titulo}. {' '.join(a.claves)}. {a.texto}" for a in anclas()])
    return _vectores_anclas


def _coseno(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def _por_claves(pregunta: str, ancla: Ancla) -> bool:
    texto = normalizar(pregunta)
    return any(re.search(rf"\b{re.escape(normalizar(c))}\b", texto) for c in ancla.claves if len(c) >= 3)


def anclas_cercanas(pregunta: str, vector: list[float] | None, tipo: str | None = None, k: int = 2) -> list[tuple[Ancla, float]]:
    """Las k anclas más parecidas a la pregunta, con su similitud.

    Una coincidencia literal de una clave o sinónimo («alfa», «subir») cuenta como
    similitud alta: los nombres técnicos cortos se vectorizan mal.
    """
    resultados: list[tuple[Ancla, float]] = []
    try:
        vecs = _vectores() if vector is not None else []
    except Exception as exc:  # noqa: BLE001 — sin modelo: solo claves
        logger.warning("No se pudieron vectorizar las anclas del dominio: %s", exc)
        vecs = []
    for i, ancla in enumerate(anclas()):
        if tipo and ancla.tipo != tipo:
            continue
        score = _coseno(vector, vecs[i]) if vecs else 0.0
        if _por_claves(pregunta, ancla):
            score = max(score, 0.75)
        resultados.append((ancla, round(score, 4)))
    resultados.sort(key=lambda par: -par[1])
    return resultados[:k]


def score_kpis(vector: list[float] | None) -> float:
    """Similitud máxima con el catálogo de KPIs (colección `kpis`, solo lectura)."""
    if vector is None:
        return 0.0
    try:
        from services import vectores

        coleccion = vectores.coleccion_existente(settings.CHROMA_COLLECTION_KPIS)
        if coleccion is None:
            return 0.0
        res = coleccion.query(query_embeddings=[vector], n_results=1, include=["distances"])
        distancias = (res.get("distances") or [[]])[0]
        return round(1.0 - float(distancias[0]), 4) if distancias else 0.0
    except Exception as exc:  # noqa: BLE001 — la colección de KPIs es opcional para decidir
        logger.warning("No se pudo consultar la colección de KPIs: %s", exc)
        return 0.0


# ── Capa 1c: clasificador en la zona gris ──────────────────────────────────────

_PROMPT_CLASIFICADOR = (
    "Clasifica si la PREGUNTA pertenece al dominio de un asistente que SOLO responde sobre: "
    "instrumentos de investigación educativa (encuestas, entrevistas, pruebas) y sus respuestas, "
    "KPIs educativos, interpretación metodológica de esos datos, comparaciones entre instrumentos "
    "y el uso de la plataforma Indagata. Fuera del dominio: conocimiento general, opiniones, "
    "tareas creativas, temas ajenos a la educación.\n"
    'Responde solo JSON: {"dentro": true|false, "motivo": "<máximo 12 palabras>"}\n\nPREGUNTA: '
)


def en_zona_gris(score: float) -> bool:
    return settings.RAG_MIN_SCORE <= score < settings.RAG_ZONA_GRIS_MAX


async def clasificar_llm(pregunta: str) -> tuple[bool, str] | None:
    """(dentro, motivo) según Ollama, o None si está desactivado o no responde."""
    if not settings.RAG_CLASIFICADOR_LLM:
        return None
    from services import ollama_client

    modelo = settings.RAG_CLASIFICADOR_MODELO or settings.OLLAMA_MODEL
    texto, degradado = await ollama_client.generar_no_stream(
        _PROMPT_CLASIFICADOR + pregunta, modelo, formato="json", opciones={"temperature": 0, "num_predict": 60}
    )
    if degradado:
        return None
    try:
        datos = json.loads(texto)
        return bool(datos["dentro"]), str(datos.get("motivo") or "")[:200]
    except (ValueError, KeyError, TypeError):
        logger.warning("Clasificador de dominio: respuesta no válida %r", texto[:200])
        return None


# ── Mensajes ───────────────────────────────────────────────────────────────────


def mensaje(decision: str, tipos: set[str] | None = None) -> str:
    """Mensaje breve y amable para una pregunta que no se responde."""
    cfg = config()
    base = " ".join(str(cfg["mensajes"].get(decision, cfg["mensajes"]["fuera"])).split())
    if decision == PRIVACIDAD:
        return base
    ejemplos: list[str] = []
    for tipo in sorted(tipos or set()):
        ejemplos += cfg["ejemplos"].get(tipo, [])
    ejemplos += cfg["ejemplos"].get("general", [])
    vistos: list[str] = []
    for e in ejemplos:
        if e not in vistos:
            vistos.append(e)
    return base + "\n" + "\n".join(f"- {e}" for e in vistos[:4])


# ── Capa 3: después de generar ─────────────────────────────────────────────────

_PII = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[correo omitido]"),
    (re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,3}\)?[\s.-]?)\d{3,4}[\s.-]?\d{4}(?!\d)"), "[teléfono omitido]"),
    # «A03100»; los IDs anónimos del acervo (A001, R0017) son más cortos y no se tachan.
    (re.compile(r"\b[A-Z]\d{5,9}\b"), "[matrícula omitida]"),
]


def tachar_datos_personales(texto: str) -> str:
    """Tacha correos, teléfonos y matrículas que pudieran colarse en la respuesta."""
    for patron, reemplazo in _PII:
        texto = patron.sub(reemplazo, texto)
    return texto
