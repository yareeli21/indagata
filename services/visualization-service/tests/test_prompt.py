"""Tests del prompt de fundamentación (FEAT-002, §4.1-§4.2).

Verifica que `construir` conserva firma y formato exactos y que el nuevo
`_INSTRUCCION` habilita la interpretación como diagnóstico pedagógico sin perder
la cláusula de alcance de la comparación ni la regla anti-invención de cifras.
Se afirma contenido mínimo (palabras clave), no el texto literal completo, para
no ser frágil.
"""
from __future__ import annotations

from app.core import prompt


def test_construir_conserva_formato():
    """`construir` mantiene el bloque de fuentes y el orden CONTEXTO/PREGUNTA/RESPUESTA."""
    salida = prompt.construir(
        "¿cuáles son las fortalezas?",
        [
            {
                "titulo": "Inventario IEAE",
                "tipo": "Encuesta",
                "investigador": "Fernández Liporace, M.",
                "fragmento": "En la dimensión Motivación la media fue 4.5 sobre 5.",
            }
        ],
    )
    assert "[Fuente 1 — Inventario IEAE (Encuesta, Fernández Liporace, M.)]" in salida
    assert "CONTEXTO:" in salida
    assert "PREGUNTA: ¿cuáles son las fortalezas?" in salida
    assert salida.rstrip().endswith("RESPUESTA:")
    # El orden CONTEXTO -> PREGUNTA -> RESPUESTA se preserva.
    assert salida.index("CONTEXTO:") < salida.index("PREGUNTA:") < salida.index(
        "RESPUESTA:"
    )
    # El fragmento se incrusta tal cual bajo su fuente.
    assert "En la dimensión Motivación la media fue 4.5 sobre 5." in salida


def test_construir_fuente_str_simple():
    """Un chunk str (sin dict) sigue produciendo el encabezado [Fuente i]."""
    salida = prompt.construir("p", ["fragmento suelto"])
    assert "[Fuente 1]" in salida
    assert "fragmento suelto" in salida


def test_instruccion_habilita_interpretacion():
    """El nuevo _INSTRUCCION pide interpretar como diagnóstico pedagógico."""
    texto = prompt._INSTRUCCION.lower()
    assert "diagnóstico" in texto or "diagnostico" in texto
    assert "fortaleza" in texto
    assert "debilidad" in texto
    assert "interpreta" in texto or "interpretar" in texto


def test_instruccion_tiene_clausula_de_alcance():
    """Conserva la cláusula de alcance de la comparación (F2)."""
    assert "ALCANCE DE LA COMPARACIÓN" in prompt._INSTRUCCION


def test_instruccion_conserva_regla_anti_invencion():
    """Conserva la regla dura anti-invención de cifras."""
    texto = prompt._INSTRUCCION
    assert "EXCLUSIVAMENTE" in texto
    assert "No inventes" in texto or "no inventes" in texto
