"""Detección de escalas Likert (texto y números) con el diccionario de `escalas_likert.yaml`.

Reglas:
  - Texto: se comparan los valores normalizados (minúsculas, sin acentos) con cada
    escala del diccionario. Si ≥90 % de los valores no vacíos coinciden con una
    escala, la columna es Likert aunque no aparezcan todas sus opciones.
  - «No sé», «No aplica» y similares NO son puntos de la escala: son faltantes.
  - Números: enteros, mínimo 0 o 1, máximo 4, 5 o 7, pocos valores únicos.
  - El libro de códigos (etiqueta → número) se guarda en el reporte.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.configuracion import escalas_likert, normalizar_texto

# Palabras de intensidad que delatan una escala aunque no esté en el diccionario.
_PALABRAS_ESCALA = ("muy", "poco", "nada", "bastante", "algo", "totalmente", "medianamente", "regular", "casi", "mucho")

# Intensidad aproximada de etiquetas frecuentes, para PROPONER un orden cuando la
# escala no está en el diccionario (el investigador lo confirma). Se busca la frase
# más larga primero («muy poco» antes que «poco»).
_INTENSIDAD = {
    "nada": 1, "ninguno": 1, "ninguna": 1,
    "muy poco": 2, "muy poca": 2, "casi nada": 2,
    "poco": 3, "poca": 3,
    "algo": 4, "regular": 4, "medianamente": 4, "moderadamente": 4, "mas o menos": 4,
    "bastante": 5,
    "mucho": 6, "mucha": 6,
    "muchisimo": 7, "muchisima": 7, "demasiado": 7, "extremadamente": 7, "totalmente": 7,
}


def _intensidad(normalizado: str) -> int | None:
    for frase in sorted(_INTENSIDAD, key=len, reverse=True):
        if f" {frase} " in f" {normalizado} ":
            return _INTENSIDAD[frase]
    return None


@dataclass
class Likert:
    """Metadatos de una columna Likert (van al reporte y orientan la limpieza)."""

    escala: str  # nombre del diccionario, "numerica" o "propuesta"
    etiquetas: list[str]  # en orden, de menor a mayor
    codigos: dict[str, int]  # valor original normalizado → código
    neutral: int | None
    excluidos: list[str] = field(default_factory=list)  # «No sé»… presentes en la columna
    cobertura: float = 1.0
    fuera: set[int] = field(default_factory=set)  # filas con valores fuera de la escala
    invertido: bool = False
    # Libro de códigos: valor TAL COMO aparece en el archivo → código numérico.
    libro: dict[str, int] = field(default_factory=dict)

    @property
    def puntos(self) -> int:
        return len(self.etiquetas)

    def a_reporte(self) -> dict[str, Any]:
        return {
            "escala": self.escala,
            "puntos": self.puntos,
            "etiquetas": self.etiquetas,
            "neutral": self.neutral,
            "excluidos": self.excluidos,
            "invertido": self.invertido,
            "codigos": self.libro,
        }


def casi_todos(dentro: int, total: int, tolerancia: float) -> bool:
    """¿Casi todos los valores cumplen? Se toleran como errores de captura hasta el
    (1−tolerancia) de los valores, y al menos 1 aunque la muestra sea pequeña, siempre
    que cumpla al menos el 80 %. Así un solo «9» no impide reconocer una escala 1–5.
    """
    if total == 0:
        return False
    fuera = total - dentro
    return fuera <= max(1, int((1 - tolerancia) * total)) and dentro / total >= 0.8


def no_respuestas() -> set[str]:
    return {normalizar_texto(v) for v in escalas_likert().get("no_respuesta", [])}


def _diccionario() -> dict[str, tuple[dict[str, int], list[str], int | None]]:
    """{escala: ({sinónimo_normalizado: posición}, etiquetas canónicas, neutral)}."""
    salida = {}
    for nombre, escala in (escalas_likert().get("escalas") or {}).items():
        mapa: dict[str, int] = {}
        canonicas: list[str] = []
        for pos, sinonimos in enumerate(escala.get("etiquetas", []), start=1):
            canonicas.append(str(sinonimos[0]))
            for s in sinonimos:
                mapa[normalizar_texto(str(s))] = pos
        salida[nombre] = (mapa, canonicas, escala.get("neutral"))
    return salida


def detectar_texto(valores: list[str | None], umbral: float) -> tuple[Likert | None, dict | None]:
    """Likert en texto.

    Devuelve (likert, dudosa): `likert` si ≥umbral de coincidencia con una escala
    del diccionario; si no, `dudosa` describe una escala que PARECE Likert (para
    que el investigador confirme su orden), o (None, None).
    """
    excluir = no_respuestas()
    presentes = [(i, v) for i, v in enumerate(valores) if v is not None]
    if not presentes:
        return None, None
    excluidos = sorted({v for _, v in presentes if normalizar_texto(v) in excluir})
    utiles = [(i, normalizar_texto(v), v) for i, v in presentes if normalizar_texto(v) not in excluir]
    if not utiles:
        return None, None
    if any(_es_numero(original) for _, _, original in utiles[:50]):
        return None, None

    mejor: tuple[float, str] | None = None
    for nombre, (mapa, _, _) in _diccionario().items():
        cobertura = sum(1 for _, n, _ in utiles if n in mapa) / len(utiles)
        if mejor is None or cobertura > mejor[0]:
            mejor = (cobertura, nombre)
    unicos = {n: original for _, n, original in utiles}

    if mejor and mejor[0] >= umbral:
        cobertura, nombre = mejor
        mapa, canonicas, neutral = _diccionario()[nombre]
        # Las etiquetas se toman como aparecen en el archivo (primera ocurrencia por posición).
        por_pos: dict[int, str] = {}
        for n, original in unicos.items():
            if n in mapa:
                por_pos.setdefault(mapa[n], original)
        # Las opciones que no aparecen en el archivo toman la etiqueta del diccionario, con mayúscula inicial.
        etiquetas = [
            por_pos.get(p, canonicas[p - 1][:1].upper() + canonicas[p - 1][1:]) for p in range(1, len(canonicas) + 1)
        ]
        codigos = {n: mapa[n] for n in unicos if n in mapa}
        fuera = {i for i, n, _ in utiles if n not in mapa}
        libro = {original: mapa[n] for n, original in unicos.items() if n in mapa}
        return Likert(nombre, etiquetas, codigos, neutral, excluidos, round(cobertura, 4), fuera, libro=libro), None

    # ¿Parece una escala? 3–7 opciones cortas y o bien coincide en parte con el
    # diccionario o usa palabras de intensidad.
    if not 3 <= len(unicos) <= 7 or any(len(o) > 40 for o in unicos.values()):
        return None, None
    cobertura = mejor[0] if mejor else 0.0
    usa_intensidad = sum(1 for n in unicos if any(p in n.split() for p in _PALABRAS_ESCALA)) >= 2
    if cobertura < 0.5 and not usa_intensidad:
        return None, None
    nombre = mejor[1] if mejor else None
    mapa = _diccionario()[nombre][0] if nombre else {}
    # Orden propuesto: las del diccionario por su posición; si no, por intensidad
    # (nada < poco < bastante < mucho…); lo que no se reconoce va al final.
    conocidas = sorted((n for n in unicos if n in mapa), key=lambda n: mapa[n])
    resto = [n for n in unicos if n not in mapa]
    por_intensidad = sorted((n for n in resto if _intensidad(n) is not None), key=lambda n: (_intensidad(n), n))
    sin_pista = sorted(n for n in resto if _intensidad(n) is None)
    orden = [unicos[n] for n in conocidas + por_intensidad + sin_pista]
    return None, {"orden_propuesto": orden, "escala_parecida": nombre, "cobertura": round(cobertura, 4), "excluidos": excluidos}


def likert_desde_orden(orden: list[str], excluidos: list[str], valores: list[str | None]) -> Likert:
    """Likert a partir de un orden confirmado por el investigador."""
    codigos = {normalizar_texto(e): i for i, e in enumerate(orden, start=1)}
    excluir = no_respuestas()
    fuera = {
        i
        for i, v in enumerate(valores)
        if v is not None and normalizar_texto(v) not in excluir and normalizar_texto(v) not in codigos
    }
    n = len(orden)
    libro = {e: i for i, e in enumerate(orden, start=1)}
    return Likert("propuesta", list(orden), codigos, (n + 1) // 2 if n % 2 else None, excluidos, 1.0, fuera, libro=libro)


def detectar_numerica(numeros: list[float | None], tolerancia: float, max_unicos: int) -> Likert | None:
    """Likert numérica: enteros, mínimo 0 o 1, máximo 4, 5 o 7 y pocos valores únicos."""
    presentes = [(i, x) for i, x in enumerate(numeros) if x is not None]
    if not presentes or any(not float(x).is_integer() for _, x in presentes):
        return None
    escalas = ((1, 4), (0, 4), (1, 5), (0, 5), (1, 7), (0, 7))
    for lo, hi in escalas:
        dentro = [x for _, x in presentes if lo <= x <= hi]
        # Unos pocos «5» no son errores de una escala 1–4: es una escala 1–5 poco usada arriba.
        afuera = {x for _, x in presentes if not lo <= x <= hi}
        if afuera and afuera == {hi + 1} and (lo, hi + 1) in escalas:
            continue
        distintos = {int(x) for x in dentro}
        if (
            casi_todos(len(dentro), len(presentes), tolerancia)
            and 3 <= len(distintos) <= max_unicos
            and max(distintos) >= hi - 1
            and min(distintos) <= lo + 1
        ):
            etiquetas = [str(v) for v in range(lo, hi + 1)]
            puntos = len(etiquetas)
            neutral = (lo + hi) // 2 if puntos % 2 else None
            fuera = {i for i, x in presentes if not lo <= x <= hi}
            return Likert("numerica", etiquetas, {e: int(e) for e in etiquetas}, neutral, [], 1.0, fuera)
    return None


def _es_numero(valor: str) -> bool:
    return numero(valor) is not None


def numero(valor: str | None) -> float | None:
    """Convierte «4», «4.5» o «4,5» a float; None si no es un número."""
    if valor is None:
        return None
    texto = valor.strip().replace(" ", "")
    if texto.count(",") == 1 and "." not in texto:
        texto = texto.replace(",", ".")
    try:
        x = float(texto)
    except ValueError:
        return None
    return x if x == x and x not in (float("inf"), float("-inf")) else None
