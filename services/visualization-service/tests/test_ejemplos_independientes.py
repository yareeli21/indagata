"""Los ejemplos del prompt de interpretación no repiten preguntas de evaluación (10 nov 2026).

La regresión del 28 oct compartía 10 de sus 28 preguntas con los ejemplos («dame un dato que encuentres interesante
del instrumento», «escríbeme un poema sobre el mar»…): el modelo veía casi la respuesta y el resultado quedaba
inflado. Esta prueba compara cada ejemplo, y cada frase citada en las instrucciones, con todas las preguntas de los
conjuntos de evaluación del repositorio.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

from services import interpretacion

_RAIZ = Path(__file__).resolve().parents[3]
_UMBRAL = 0.7  # parecido de texto (difflib) a partir del cual dos preguntas cuentan como la misma


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def _preguntas(x, salida: list[str]) -> list[str]:
    """Los textos con forma de pregunta de un JSON de evaluación (campos «pregunta», «consulta», «texto», turnos…)."""
    if isinstance(x, dict):
        for v in x.values():
            _preguntas(v, salida)
    elif isinstance(x, list):
        for v in x:
            _preguntas(v, salida)
    elif isinstance(x, str) and 12 <= len(x) <= 300 and ("?" in x or re.match(r"(?i)(dame|compara|muestra|dime|escribe|lista)", x)):
        salida.append(x)
    return salida


def _evaluacion() -> dict[str, list[str]]:
    archivos = {
        "regresión": "tools/rag/regresion/banco_regresion.json",
        "conjuntos del chat y control": "tools/rag/baterias_chat.json",
        "recuperación": "tools/rag/recuperacion_oro.json",
        "preguntas de referencia": "tools/rag/preguntas_referencia.json",
        "banco": "tools/rag/banco_preguntas.json",
        "modelos": "services/visualization-service/scripts/modelos/casos.json",
    }
    conjuntos = {n: _preguntas(json.loads((_RAIZ / r).read_text(encoding="utf-8")), []) for n, r in archivos.items()
                 if (_RAIZ / r).exists()}
    aritmetica = (_RAIZ / "tools/rag/aritmetica.py").read_text(encoding="utf-8")
    conjuntos["aritmética"] = re.findall(r'"texto": "([^"]+)"', aritmetica)
    return conjuntos


def test_hay_conjuntos_de_evaluacion():
    conjuntos = _evaluacion()
    assert len(conjuntos["regresión"]) >= 28 and len(conjuntos["aritmética"]) == 40  # A01–A20 y la prueba ciega B01–B20
    assert len(conjuntos["conjuntos del chat y control"]) >= 100


def test_ningun_ejemplo_repite_una_pregunta_de_evaluacion():
    ejemplos = [p for p, _ in interpretacion._EJEMPLOS]
    citas = [c for c in re.findall(r"«([^»]{20,})»", interpretacion.SISTEMA)]
    repetidas = [(nombre, e, q) for nombre, preguntas in _evaluacion().items() for q in preguntas
                 for e in ejemplos + citas if difflib.SequenceMatcher(None, _norm(e), _norm(q)).ratio() >= _UMBRAL]
    assert not repetidas, "\n".join(f"{n}: «{e}» ≈ «{q}»" for n, e, q in repetidas)


def test_ejemplos_son_planes_validos():
    from services.plan_consulta import PlanConsulta
    for _, plan in interpretacion._EJEMPLOS:
        PlanConsulta.model_validate(plan)
