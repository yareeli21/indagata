"""Inferencia del tipo canónico provisional de cada columna (Tabla 2 + likert).

Orden de prioridad (el primero que aplica gana):
    cuadricula → ranking → opcion_multiple_varias → likert → binaria →
    escala_lineal → calificacion → numerica → categorica → texto_corto / texto_largo

El tipo es PROVISIONAL: orienta la limpieza (p. ej. qué es un valor fuera de
rango) y viaja a metadata-service, donde el investigador lo confirma.

Valores fuera de rango (`fuera`, índices de fila):
  - numerica:                     atípicos por ±4σ o por rango intercuartílico (según
                                  `estadistica.metodo_atipicos`; solo con suficientes respuestas).
  - likert/escala_lineal/calificacion: fuera del rango de la escala.
  Las escalas se reconocen si casi todos los valores caen en su rango (ver
  `likert.casi_todos`), para que unos pocos errores de captura no impidan detectarlas.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Any

from services.configuracion import normalizar_texto
from services.motores import estadistica
from services.motores.encuestas.likert import Likert, casi_todos, detectar_numerica, detectar_texto, numero

# «Pregunta [aspecto]»: grupos padre-hijo (cuadrículas, opción múltiple tipo LimeSurvey).
PATRON_GRUPO = re.compile(r"^(?P<padre>.+?)\s*\[(?P<hijo>[^\]]+)\]\s*$")
# «Aportación_en_a_item1», «Dedicacion 2», «SAT.3»: prefijo + número final (bloques de ítems).
PATRON_SUFIJO = re.compile(r"^(?P<padre>.*?[^\W\d_].*?)[\s_.\-]*(?:[ií]tem|reactivo)?[\s_.\-]*(?P<hijo>\d{1,3})$", re.IGNORECASE)
_RANGO_EXPLICITO = re.compile(r"\d+\s*(?:-|–|a|al)\s*\d+|\bescala\b", re.IGNORECASE)
_SEPARADORES = re.compile(r"[_.\-/()¿?¡!,:;]+")
_SI_NO = {"si", "no", "yes", "y", "n", "s", "true", "false", "verdadero", "falso"}


@dataclass
class InfoTipo:
    tipo: str
    likert: Likert | None = None
    dudosa: dict | None = None  # escala que parece Likert pero no está en el diccionario
    rango: tuple[float, float] | None = None  # rango válido (escalas y calificaciones)
    fuera: set[int] = field(default_factory=set)  # filas con valores fuera de rango
    estadisticos: dict[str, Any] = field(default_factory=dict)
    metodo_atipicos: str | None = None  # "sigma" | "iqr" (solo numéricas)


def grupo_de(etiqueta: str) -> tuple[str, str] | None:
    """(padre, hijo) si el encabezado sigue el patrón «Pregunta [aspecto]»."""
    m = PATRON_GRUPO.match(etiqueta)
    return (m.group("padre").strip(), m.group("hijo").strip()) if m else None


def grupo_bloque(etiqueta: str) -> tuple[str, str] | None:
    """Bloque de ítems para la fiabilidad: «Pregunta [aspecto]» o un prefijo con número
    final («Aportación_item1», «Dedicacion_2», «SAT.3»). Solo para agrupar escalas: el
    tipo de la columna se sigue infiriendo con `grupo_de`."""
    g = grupo_de(etiqueta)
    if g:
        return g
    m = PATRON_SUFIJO.match(etiqueta.strip())
    if not m:
        return None
    padre = " ".join(m.group("padre").replace("_", " ").split()).strip(" -.")
    return (padre, f"ítem {int(m.group('hijo'))}") if padre else None


def es_cantidad(etiqueta: str, palabras: list[str]) -> bool:
    """¿El encabezado habla de una cantidad (horas, edad, años…)? Palabra completa."""
    texto = " " + " ".join(_SEPARADORES.sub(" ", normalizar_texto(etiqueta)).split()) + " "
    return any(f" {normalizar_texto(p)} " in texto for p in palabras)


def _separados(presentes: list[str], separadores: list[str]) -> bool:
    """¿Los valores son listas («A, B; C») de opciones que se repiten entre filas?"""
    con_sep = [v for v in presentes if any(s in v for s in separadores) and numero(v) is None]
    if len(con_sep) < max(2, 0.3 * len(presentes)):
        return False
    tokens: dict[str, int] = {}
    for v in presentes:
        for t in re.split("|".join(re.escape(s) for s in separadores), v):
            t = normalizar_texto(t)
            if t:
                tokens[t] = tokens.get(t, 0) + 1
    repetidos = [t for t, n in tokens.items() if n >= 2]
    return bool(repetidos) and len(tokens) <= 40 and statistics.mean(len(t) for t in tokens) < 40


def inferir(etiqueta: str, valores: list[str | None], cfg: dict[str, Any]) -> InfoTipo:
    """Tipo canónico provisional de una columna (los valores ya pasaron por las transformaciones universales)."""
    tipos_cfg = cfg["tipos"]
    umbrales = cfg["umbrales"]
    tolerancia = float(umbrales.get("tolerancia_escala", 0.95))
    presentes = [v for v in valores if v is not None]
    if not presentes:
        return InfoTipo("texto_corto")
    etiqueta_n = f" {normalizar_texto(etiqueta)} "
    unicos = {normalizar_texto(v) for v in presentes}
    numeros = [numero(v) for v in valores]
    n_numeros = sum(1 for v, x in zip(valores, numeros) if v is not None and x is not None)
    es_numerica = casi_todos(n_numeros, len(presentes), tolerancia)
    grupo = grupo_de(etiqueta)
    # Cantidades (horas, edad, hijos…): ni Likert numérica, ni escala, ni calificación,
    # aunque caigan en 0–10 o 0–100. Si el encabezado declara su rango
    # («Horas de estudio (0-10)»), sí es una escala.
    cantidad = es_cantidad(etiqueta, tipos_cfg.get("palabras_numerica", [])) and not _RANGO_EXPLICITO.search(etiqueta)

    lik_texto, dudosa = detectar_texto(valores, float(tipos_cfg.get("likert_coincidencia_minima", 0.9)))
    lik_num = (
        detectar_numerica(numeros, tolerancia, int(tipos_cfg.get("likert_max_unicos", 7)))
        if es_numerica and not cantidad
        else None
    )
    likert = lik_texto or lik_num

    # 1. Cuadrícula: «Pregunta [aspecto]» con valores de escala evaluativa.
    if grupo and likert:
        return InfoTipo("cuadricula", likert=likert, rango=_rango(likert), fuera=set(likert.fuera))
    # 2. Ranking: la pregunta pide ordenar.
    if any(normalizar_texto(p) in etiqueta_n for p in tipos_cfg.get("palabras_ranking", [])):
        return InfoTipo("ranking")
    # 3. Opción múltiple (varias): listas separadas por , o ;, o «Pregunta [opción]» con Sí/No.
    if (grupo and unicos <= _SI_NO) or _separados(presentes, tipos_cfg.get("separadores_multiple", [",", ";"])):
        return InfoTipo("opcion_multiple_varias")
    # 4. Likert (texto del diccionario o números 0/1–4/5/7).
    if likert:
        return InfoTipo("likert", likert=likert, rango=_rango(likert), fuera=set(likert.fuera))
    # 5. Binaria: exactamente dos valores distintos.
    if len(unicos) == 2:
        return InfoTipo("binaria", dudosa=dudosa)

    if es_numerica:
        xs = [(i, x) for i, x in enumerate(numeros) if x is not None and valores[i] is not None]
        no_numericos = {i for i, v in enumerate(valores) if v is not None and numeros[i] is None}
        enteros = all(float(x).is_integer() for _, x in xs)
        en_0_10 = [x for _, x in xs if 0 <= x <= 10]
        # 6. Escala lineal: enteros, rango ≤ 20, máximo ≤ 10.
        if not cantidad and enteros and casi_todos(len(en_0_10), len(xs), tolerancia):
            lo, hi = min(en_0_10), max(en_0_10)
            if hi - lo <= 20:
                # Fuera de la escala solo lo que excede 0–10: el rango observado puede
                # no llegar al máximo posible de la escala (nadie eligió el 10).
                fuera = {i for i, x in xs if not 0 <= x <= 10} | no_numericos
                return InfoTipo("escala_lineal", rango=(lo, hi), fuera=fuera, estadisticos=_estadisticos(xs))
        # 7. Calificación: 0–10 o 0–100.
        if not cantidad and casi_todos(len(en_0_10), len(xs), tolerancia):
            fuera = {i for i, x in xs if not 0 <= x <= 10} | no_numericos
            return InfoTipo("calificacion", rango=(0, 10), fuera=fuera, estadisticos=_estadisticos(xs))
        en_0_100 = [x for _, x in xs if 0 <= x <= 100]
        if not cantidad and en_0_100 and casi_todos(len(en_0_100), len(xs), tolerancia) and max(en_0_100) > 10:
            fuera = {i for i, x in xs if not 0 <= x <= 100} | no_numericos
            return InfoTipo("calificacion", rango=(0, 100), fuera=fuera, estadisticos=_estadisticos(xs))
        # 8. Numérica: atípicos (±4σ o IQR) con suficientes respuestas.
        info = InfoTipo("numerica", estadisticos=_estadisticos(xs), fuera=set(no_numericos))
        valores_x = [x for _, x in xs]
        if len(valores_x) >= int(umbrales.get("filas_minimas_sigma", 10)):
            metodo, k = metodo_atipicos(cfg)
            limites = estadistica.limites_atipicos(valores_x, metodo, k)
            if limites:
                info.metodo_atipicos = metodo
                info.rango = (round(limites[0], 4), round(limites[1], 4))
                info.fuera |= {i for i, x in xs if x < limites[0] or x > limites[1]}
        return info

    promedio = statistics.mean(len(v) for v in presentes)
    # 9. Categórica: 3–15 valores distintos de texto corto.
    if tipos_cfg.get("categorica_min_unicos", 3) <= len(unicos) <= tipos_cfg.get("categorica_max_unicos", 15) and promedio < tipos_cfg.get("texto_largo_min_promedio", 60):
        return InfoTipo("categorica", dudosa=dudosa)
    # 10. Texto libre.
    largo = promedio >= tipos_cfg.get("texto_largo_min_promedio", 60)
    return InfoTipo("texto_largo" if largo else "texto_corto", dudosa=dudosa)


def metodo_atipicos(cfg: dict[str, Any]) -> tuple[str, float]:
    """(método, factor) para detectar atípicos en columnas numéricas."""
    est = cfg.get("estadistica") or {}
    metodo = str(est.get("metodo_atipicos", "sigma")).lower()
    if metodo == "iqr":
        return "iqr", float(est.get("factor_iqr", 1.5))
    return "sigma", float(cfg["umbrales"].get("sigma_fuera_de_rango", 4))


def _rango(likert: Likert) -> tuple[float, float] | None:
    if likert.escala == "numerica":
        return float(likert.etiquetas[0]), float(likert.etiquetas[-1])
    return 1.0, float(likert.puntos)


def _estadisticos(xs: list[tuple[int, float]]) -> dict[str, Any]:
    valores = [x for _, x in xs]
    if not valores:
        return {}
    return {
        "min": min(valores),
        "max": max(valores),
        "media": round(statistics.mean(valores), 4),
        "desviacion": round(statistics.pstdev(valores), 4),
    }
