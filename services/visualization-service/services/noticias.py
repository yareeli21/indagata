"""Noticias de educación e investigación para el panel del chat.

Lee las fuentes RSS/Atom de `config/noticias.yaml` (sin clave) y, si hay
`NOTICIAS_API_KEY`, además GNews. Normaliza cada entrada a título, resumen sin
HTML, fecha, medio y enlace; quita repetidas, ordena por fecha y guarda el
resultado en memoria `NOTICIAS_CACHE_MIN` minutos para no consultar a los medios
en cada visita. Si no hay red, devuelve la última lista buena (o una vacía con
un aviso): el panel nunca rompe el chat.
"""
from __future__ import annotations

import hashlib
import html
import logging
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from shared.db.core.config import settings

logger = logging.getLogger("visualization-service")

_CONFIG = Path(__file__).resolve().parents[1] / "config" / "noticias.yaml"
_ATOM = "{http://www.w3.org/2005/Atom}"
_GNEWS = "https://gnews.io/api/v4/search"
_TIMEOUT = httpx.Timeout(8.0, connect=5.0)
_MAX_RESUMEN = 220

_cache: dict[str, Any] = {"hasta": 0.0, "datos": None}
_candado = threading.Lock()


def config() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8")) or {}


def _limpiar(texto: str | None) -> str:
    """Sin etiquetas HTML ni entidades, con espacios simples y recortado."""
    sin_html = re.sub(r"<[^>]+>", " ", html.unescape(texto or ""))
    plano = " ".join(html.unescape(sin_html).split())
    return plano if len(plano) <= _MAX_RESUMEN else plano[: _MAX_RESUMEN - 1].rsplit(" ", 1)[0] + "…"


def _fecha(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        fecha = parsedate_to_datetime(texto)  # RSS: RFC 822
    except (TypeError, ValueError):
        try:
            fecha = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))  # Atom: ISO 8601
        except ValueError:
            return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _texto(nodo: ET.Element | None, etiqueta: str) -> str:
    hijo = nodo.find(etiqueta) if nodo is not None else None
    return (hijo.text or "").strip() if hijo is not None and hijo.text else ""


def parsear(xml: bytes | str, medio: str) -> list[dict[str, Any]]:
    """Entradas de un RSS 2.0 o Atom, normalizadas."""
    raiz = ET.fromstring(xml)
    salida: list[dict[str, Any]] = []
    for item in raiz.iter("item"):  # RSS 2.0
        titulo = _limpiar(_texto(item, "title"))
        # Google Noticias trae el medio en <source> y lo agrega al título («… - El Universal»).
        fuente = _texto(item, "source") or medio
        if fuente != medio and titulo.endswith(f" - {fuente}"):
            titulo = titulo[: -len(fuente) - 3]
        salida.append({"titulo": titulo, "resumen": _limpiar(_texto(item, "description")), "url": _texto(item, "link"),
                       "fecha": _fecha(_texto(item, "pubDate")), "medio": fuente})
    for entry in raiz.iter(f"{_ATOM}entry"):  # Atom
        enlace = entry.find(f"{_ATOM}link")
        salida.append({"titulo": _limpiar(_texto(entry, f"{_ATOM}title")),
                       "resumen": _limpiar(_texto(entry, f"{_ATOM}summary") or _texto(entry, f"{_ATOM}content")),
                       "url": enlace.get("href", "") if enlace is not None else "",
                       "fecha": _fecha(_texto(entry, f"{_ATOM}updated") or _texto(entry, f"{_ATOM}published")), "medio": medio})
    return [n for n in salida if n["titulo"] and n["url"].startswith(("https://", "http://"))]


def _de_gnews(cliente: httpx.Client, consulta: str) -> list[dict[str, Any]]:
    r = cliente.get(_GNEWS, params={"q": consulta, "lang": "es", "max": 10, "apikey": settings.NOTICIAS_API_KEY})
    r.raise_for_status()
    return [{"titulo": _limpiar(a.get("title")), "resumen": _limpiar(a.get("description")), "url": a.get("url") or "",
             "fecha": _fecha(a.get("publishedAt")), "medio": (a.get("source") or {}).get("name") or "GNews"}
            for a in r.json().get("articles") or []]


def _recolectar() -> tuple[list[dict[str, Any]], list[str]]:
    cfg = config()
    noticias: list[dict[str, Any]] = []
    fallidas: list[str] = []
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": "Indagata/1.0 (+noticias)"}) as cliente:
        for fuente in cfg.get("fuentes") or []:
            try:
                r = cliente.get(fuente["url"])
                r.raise_for_status()
                noticias += parsear(r.content, fuente["nombre"])
            except (httpx.HTTPError, ET.ParseError, KeyError) as exc:
                logger.warning("Noticias: no se pudo leer %s: %s", fuente.get("nombre"), exc)
                fallidas.append(str(fuente.get("nombre")))
        if settings.NOTICIAS_API_KEY:
            try:
                noticias += _de_gnews(cliente, cfg.get("consulta_api") or "educación")
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("Noticias: GNews no respondió: %s", exc)
                fallidas.append("GNews")
    vistas: set[str] = set()
    unicas = []
    minimo = datetime.min.replace(tzinfo=timezone.utc)
    for n in sorted(noticias, key=lambda n: n["fecha"] or minimo, reverse=True):
        clave = re.sub(r"\W+", "", n["titulo"].lower())[:80]
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(n)
    return unicas[: int(cfg.get("maximo") or 12)], fallidas


def _a_salida(n: dict[str, Any]) -> dict[str, Any]:
    return {"id": hashlib.sha1(n["url"].encode("utf-8")).hexdigest()[:12], "titulo": n["titulo"], "resumen": n["resumen"],
            "fecha": n["fecha"].date().isoformat() if n["fecha"] else "", "medio": n["medio"], "url": n["url"]}


def obtener(forzar: bool = False) -> dict[str, Any]:
    """`{noticias, actualizado, aviso}` desde la caché o recién leídas."""
    with _candado:
        ahora = time.monotonic()
        if not forzar and _cache["datos"] is not None and ahora < _cache["hasta"]:
            return _cache["datos"]
        noticias, fallidas = _recolectar()
        if not noticias and _cache["datos"] is not None:  # sin red: la última lista buena
            previo = dict(_cache["datos"])
            previo["aviso"] = "Sin conexión con las fuentes de noticias; se muestran las últimas obtenidas."
            return previo
        datos = {
            "noticias": [_a_salida(n) for n in noticias],
            "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "aviso": None if noticias else "No se pudieron obtener noticias (sin conexión con las fuentes).",
            "fuentesConError": fallidas,
        }
        if noticias:
            _cache.update(hasta=ahora + settings.NOTICIAS_CACHE_MIN * 60, datos=datos)
        return datos
