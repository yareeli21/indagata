"""Lo que el diccionario de datos dice de los códigos, antes de inferir los tipos (microdatos).

  - Un código que el diccionario define como no respuesta («9» = «No sé») no es un punto de la escala: se escribe
    con su etiqueta, para que se trate como cualquier «No sé» (la persona investigadora decide si se conserva).
  - Una columna cuyos códigos son opciones sin orden («1» = «Presencial», «2» = «En línea») es categórica aunque
    sus códigos sean pocos números: no se promedia ni entra en el α de Cronbach.

Sin diccionario no cambia nada.
"""
from __future__ import annotations

from typing import Any

from shared.conocimiento.significados import codigo

from services.configuracion import normalizar_texto
from services.motores.encuestas import universales
from services.motores.encuestas.likert import _intensidad, no_respuestas, posiciones


def _sin_orden(etiquetas: list[str]) -> bool:
    """¿Son opciones sin orden? Ninguna etiqueta es de una escala del diccionario ni dice una intensidad."""
    return len(etiquetas) >= 2 and not any(posiciones(e) or _intensidad(normalizar_texto(e)) for e in etiquetas) \
        and not any(numero_en(e) for e in etiquetas)


def numero_en(etiqueta: str) -> bool:
    return any(ch.isdigit() for ch in etiqueta)


def aplicar(tabla: universales.TablaPreparada, dic: Any) -> tuple[dict | None, set[str]]:
    """Escribe los códigos de no respuesta con su etiqueta; devuelve la transformación y las columnas categóricas."""
    if dic is None:
        return None, set()
    excluir = no_respuestas()
    total, casos, categoricas = 0, [], set()
    for c in tabla.columnas:
        e = dic.buscar(c.etiqueta, c.id)
        if e is None or not e.valores:
            continue
        sin_respuesta = {cod: etq for cod, etq in e.valores.items() if normalizar_texto(etq) in excluir}
        if _sin_orden([etq for cod, etq in e.valores.items() if cod not in sin_respuesta]):
            categoricas.add(c.id)
        for i, v in enumerate(c.valores):
            if v is not None and codigo(v) in sin_respuesta:
                nuevo = sin_respuesta[codigo(v)]
                if len(casos) < universales.MAX_CASOS:
                    casos.append({"fila": i + 1, "columna": c.etiqueta, "antes": v, "despues": nuevo})
                c.valores[i] = nuevo
                total += 1
    transformacion = (
        {"regla": "codigos_no_respuesta", "detalle": "Códigos que el diccionario de datos define como no respuesta "
         "(«9» = «No sé») escritos con su etiqueta: no son puntos de la escala.", "afectados": total, "casos": casos}
        if total else None
    )
    return transformacion, categoricas
