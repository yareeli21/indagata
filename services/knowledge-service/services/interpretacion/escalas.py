"""Niveles de las escalas (agrupaciones para consultas), definidos por POSICIÓN.

Con un número impar de puntos, el centro es «medio», lo de abajo «bajo» y lo de arriba
«alto»; con número par no hay «medio» (mitad inferior «bajo», superior «alto»). Los
nombres de cada nivel salen de `niveles` de cada escala en el diccionario compartido
(«desacuerdo» / «neutral» / «acuerdo»; «baja» / «media» / «alta»…).
"""
from __future__ import annotations

from services.interpretacion.config import escalas


def escala_por_anclas(anclas: dict[int, str]) -> str | None:
    """Escala del diccionario a la que pertenecen las anclas de una escala numérica.

    «1 = Totalmente en desacuerdo / Nunca» … → «acuerdo». Regla de desempate: manda la
    primera etiqueta de cada ancla (antes de «/»); si no alcanza, cualquier parte.
    Devuelve None si menos de la mitad de las anclas coincide con alguna escala.
    """
    from services.interpretacion.config import normalizar

    if not anclas:
        return None
    sinonimos = {
        nombre: {normalizar(s) for grupo in (datos.get("etiquetas") or []) for s in grupo}
        for nombre, datos in (escalas().get("escalas") or {}).items()
    }
    partes = [[normalizar(p) for p in str(e).split("/") if p.strip()] for e in anclas.values()]

    def puntaje(nombre: str, solo_primera: bool) -> int:
        return sum(1 for ps in partes if any(p in sinonimos[nombre] for p in (ps[:1] if solo_primera else ps)))

    for solo_primera in (True, False):
        mejor = max(sinonimos, key=lambda n: puntaje(n, solo_primera), default=None)
        if mejor and puntaje(mejor, solo_primera) * 2 >= len(anclas):
            return mejor
    return None


def nombres_niveles(escala: str | None) -> dict[str, str]:
    """{bajo, medio, alto} → nombre del nivel para la escala (o los de por defecto)."""
    datos = escalas()
    por_defecto = datos.get("niveles_por_defecto") or {"bajo": "baja", "medio": "media", "alto": "alta"}
    propia = ((datos.get("escalas") or {}).get(escala or "") or {}).get("niveles")
    return dict(por_defecto, **(propia or {}))


def tramo(posicion: int, puntos: int) -> str | None:
    """«bajo» | «medio» | «alto» de una posición 1..puntos (None si está fuera)."""
    if puntos < 2 or not 1 <= posicion <= puntos:
        return None
    if puntos % 2:
        centro = (puntos + 1) // 2
        return "medio" if posicion == centro else ("bajo" if posicion < centro else "alto")
    return "bajo" if posicion <= puntos // 2 else "alto"


def nivel(posicion: int, puntos: int, escala: str | None) -> str | None:
    """Nombre del nivel de una posición («desacuerdo», «media»…)."""
    t = tramo(posicion, puntos)
    return nombres_niveles(escala)[t] if t else None


def mapa_niveles(valores: list[int | float], escala: str | None) -> dict[str, list[int | float]]:
    """{nivel: [valores]} para describir la escala de una pregunta (en orden ascendente)."""
    salida: dict[str, list[int | float]] = {}
    for posicion, valor in enumerate(valores, start=1):
        n = nivel(posicion, len(valores), escala)
        if n:
            salida.setdefault(n, []).append(valor)
    return salida
