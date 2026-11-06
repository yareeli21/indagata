"""Piezas comunes de los scripts del experimento de modelos: corridas, emparejar consultas con turnos y estadística.

Una **corrida** es lo que la persona preguntó en el chat con un redactor: `--corrida llama3.2:3b=1328-1370` (rango de
`rag_log_id`, el final es opcional). De ese rango se toman las consultas de ese modelo (`modelo_usado`) cuya pregunta
coincide con un turno de `casos.json` (sin mayúsculas, acentos ni signos); si un turno se preguntó varias veces, cuenta
la última. Las preguntas que no son de los casos (p. ej. «hola» para calentar el modelo) se ignoran.
"""
from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[2]
if str(_SERVICIO) not in sys.path:
    sys.path.insert(0, str(_SERVICIO))

import logging  # noqa: E402

from shared.db.session import engine  # noqa: E402
from shared.models.rag_log import RagLog  # noqa: E402

# Los scripts muestran su propio avance: sin el eco de SQL del modo de depuración.
engine.echo = False
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from services.dominio import normalizar  # noqa: E402

CASOS = Path(__file__).with_name("casos.json")


def clave_texto(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalizar(texto)).strip()


def leer_casos(ruta: Path = CASOS) -> dict:
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}: corre antes scripts/modelos/generar_casos.py")
    return json.loads(ruta.read_text(encoding="utf-8"))


@dataclass
class Corrida:
    modelo: str
    desde: int
    hasta: int | None = None
    # (caso, número de turno) → fila de rag_log
    filas: dict[tuple[int, int], RagLog] = field(default_factory=dict)

    @property
    def nombre(self) -> str:
        return f"{self.modelo} ({self.desde}–{self.hasta or '…'})"


def parsear_corrida(texto: str) -> Corrida:
    m = re.fullmatch(r"\s*([^=]+?)\s*=\s*(\d+)\s*(?:-\s*(\d+))?\s*", texto)
    if not m:
        raise SystemExit(f"Corrida no válida: {texto!r}. Formato: modelo=INICIO-FIN (p. ej. llama3.2:3b=1328-1370)")
    return Corrida(m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None)


def emparejar(sesion, corrida: Corrida, casos: dict) -> list[str]:
    """Llena `corrida.filas`; devuelve los turnos que no se encontraron («5.1: ¿cuántos…»)."""
    turnos = {clave_texto(t["texto"]): (c["caso"], i)
              for c in casos["casos"] for i, t in enumerate(c["turnos"], 1)}
    consulta = sesion.query(RagLog).filter(RagLog.modelo_usado == corrida.modelo, RagLog.rag_log_id >= corrida.desde)
    if corrida.hasta:
        consulta = consulta.filter(RagLog.rag_log_id <= corrida.hasta)
    for fila in consulta.order_by(RagLog.rag_log_id):
        if (clave := turnos.get(clave_texto(fila.pregunta))) is not None:
            corrida.filas[clave] = fila  # la última vez que se preguntó
    return [f"{c['caso']}.{i}: {t['texto'][:60]}" for c in casos["casos"] for i, t in enumerate(c["turnos"], 1)
            if (c["caso"], i) not in corrida.filas]


# ── Estadística (a mano, sin dependencias) ─────────────────────────────────────


def kappa(a: list[bool], b: list[bool]) -> float | None:
    """Kappa de Cohen entre dos clasificaciones binarias: 1 = acuerdo total, 0 = el que daría el azar."""
    n = len(a)
    if n < 2:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def _rangos(valores: list[float]) -> list[float]:
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    rangos = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        for k in range(i, j + 1):
            rangos[orden[k]] = (i + j) / 2 + 1  # empates: rango promedio
        i = j + 1
    return rangos


def spearman(x: list[float], y: list[float]) -> float | None:
    """Correlación de Spearman: 1 = ordenan igual, 0 = sin relación, −1 = al revés."""
    if len(x) < 3:
        return None
    rx, ry = _rangos(x), _rangos(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return None if den == 0 else round(num / den, 3)


def media(valores: list[float | None]) -> float | None:
    v = [x for x in valores if x is not None]
    return round(sum(v) / len(v), 3) if v else None
