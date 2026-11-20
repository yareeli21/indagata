"""Intérpretes de respuestas de encuesta, uno por tipo canónico de pregunta.

Entrada por columna (todas las respuestas a la vez, porque algunas reglas dependen
de la columna completa, p. ej. la forma canónica de una categoría):
  - spec:   la columna del reporte de limpieza (`especifico.encuesta.columnas[i]`):
            tipo_canonico, likert {escala, etiquetas, invertido…}, rango, etiqueta.
  - valores: las celdas del CSV limpio, en orden de respondente ("" = vacía).
  - anclas: anclas de la escala tomadas del instrumento original ({1: "Nada", 5: "Mucho"}).
  - spec["etiquetas_valor"]: significado de cada código según el diccionario de datos o lo que escribió la
            investigadora en la limpieza ({"1": "Hombre", "2": "Mujer"}); ver `codificada`.

En el CSV limpio las escalas Likert de texto ya vienen como CÓDIGOS (1..n, en el orden
de la escala) y las Likert numéricas con su número original; la etiqueta se recupera
del libro de códigos del reporte.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from shared.conocimiento import significados

from services.interpretacion import escalas
from services.interpretacion.config import escalas as dic_escalas
from services.interpretacion.config import normalizar, palabras, reglas

SIN_RESPUESTA = {"estado": "sin_respuesta"}


@dataclass
class ColumnaInterpretada:
    """Resultado de interpretar una columna completa."""

    respuestas: list[dict[str, Any]]  # una por respondente, en orden (nunca se omite ninguna)
    escala: dict[str, Any] | None = None  # descripción de la escala/medida de la pregunta
    opciones: list[str] = field(default_factory=list)  # opciones canónicas observadas
    no_interpretadas: int = 0
    tipo: str | None = None  # tipo con el que se interpretó, si no es el de la limpieza (códigos → «categorica»)


def numero(valor: str) -> float | None:
    """«4», «4.0» o «4,5» → float; None si no es un número."""
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return None


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _vacia(valor: str | None) -> bool:
    return valor is None or not str(valor).strip()


def _no_interpretada(valor: str) -> dict[str, Any]:
    return {"estado": "no_interpretada", "valor": valor}


def motivo_no_respuesta(valor: str) -> str | None:
    """Motivo de una respuesta «No sé / No aplica…» (None si no lo es).

    La limpieza puede conservarlas marcadas con su texto: así se distinguen de las celdas
    que el respondente dejó en blanco (que no traen motivo).
    """
    n = normalizar(valor)
    if n not in {normalizar(x) for x in dic_escalas().get("no_respuesta", [])}:
        return None
    if "aplica" in n or n == "n/a":
        return "no_aplica"
    if "prefiero" in n or n == "ns/nc":
        return "prefiere_no_responder"
    if "opinion" in n:
        return "sin_opinion"
    return "no_sabe"


def _formas_canonicas(valores: list[str]) -> dict[str, str]:
    """{forma normalizada: grafía más frecuente} (empate → la primera que apareció)."""
    por_clave: dict[str, Counter] = {}
    for v in valores:
        por_clave.setdefault(normalizar(v), Counter())[v.strip()] += 1
    return {clave: conteo.most_common(1)[0][0] for clave, conteo in por_clave.items()}


# ── Escalas ────────────────────────────────────────────────────────────────────


def likert(spec: dict[str, Any], valores: list[str], anclas: dict[int, str] | None = None) -> ColumnaInterpretada:
    """Código → etiqueta exacta y nivel; en ítems invertidos se agrega el valor recodificado.

    Regla: `significado` y `nivel` describen LO QUE RESPONDIÓ la persona (así «en
    desacuerdo en p3» es literal); el valor recodificado sirve para promediar el constructo.
    """
    lik = spec.get("likert") or {}
    etiquetas = [str(e) for e in lik.get("etiquetas") or []]
    nombre = lik.get("escala")
    numerica = nombre == "numerica"
    anclas = anclas or {}
    # Escala numérica con anclas en el original («1 = Totalmente en desacuerdo…»): los
    # niveles toman el nombre de esa escala (desacuerdo/neutral/acuerdo…), no «baja/alta».
    nombre_niveles = (escalas.escala_por_anclas(anclas) if numerica else nombre)
    try:
        codigos = [int(float(e)) for e in etiquetas] if numerica else list(range(1, len(etiquetas) + 1))
    except ValueError:
        codigos = list(range(1, len(etiquetas) + 1))
    if not codigos:
        return ColumnaInterpretada([SIN_RESPUESTA if _vacia(v) else _no_interpretada(v) for v in valores], None, [],
                                   sum(1 for v in valores if not _vacia(v)))
    lo, hi = codigos[0], codigos[-1]

    def etiqueta(c: int) -> str:
        if not numerica:
            return etiquetas[codigos.index(c)]
        return anclas.get(c) or f"{c} en escala {lo}–{hi}"

    invertido = bool(lik.get("invertido"))
    salida, malas = [], 0
    for v in valores:
        if _vacia(v):
            salida.append(dict(SIN_RESPUESTA))
            continue
        if motivo := motivo_no_respuesta(v):
            # «No sé», «No aplica»…: no es un punto de la escala; queda sin respuesta CON motivo.
            salida.append({"estado": "sin_respuesta", "valor": v.strip(), "significado": v.strip(), "motivo": motivo})
            continue
        x = numero(v)
        if x is None or not x.is_integer() or int(x) not in codigos:
            salida.append(_no_interpretada(v))
            malas += 1
            continue
        c = int(x)
        r: dict[str, Any] = {
            "estado": "respondida",
            "valor": c,
            "significado": etiqueta(c),
            "nivel": escalas.nivel(codigos.index(c) + 1, len(codigos), nombre_niveles),
        }
        if invertido:
            r["valor_recodificado"] = lo + hi - c
        salida.append(r)
    descripcion = {
        "puntos": len(codigos),
        "etiquetas": {str(c): etiqueta(c) for c in codigos},
        "niveles": escalas.mapa_niveles(codigos, nombre_niveles),
        "invertida": invertido,
    }
    if anclas:
        descripcion["anclas"] = {str(k): v for k, v in sorted(anclas.items())}
    return ColumnaInterpretada(salida, descripcion, [], malas)


def escala_lineal(spec: dict[str, Any], valores: list[str], anclas: dict[int, str] | None = None) -> ColumnaInterpretada:
    """«4 en escala 1–5, donde 1 = Nada y 5 = Mucho» si hay anclas; si no, «4 de 5»."""
    anclas = anclas or {}
    xs = [numero(v) for v in valores if not _vacia(v)]
    rango = spec.get("rango") or ([min(x for x in xs if x is not None), max(x for x in xs if x is not None)] if any(x is not None for x in xs) else None)
    if not rango:
        return ColumnaInterpretada([SIN_RESPUESTA if _vacia(v) else _no_interpretada(v) for v in valores])
    lo, hi = int(rango[0]), int(rango[1])
    puntos = list(range(lo, hi + 1))
    con_anclas = lo in anclas and hi in anclas
    salida, malas = [], 0
    for v in valores:
        if _vacia(v):
            salida.append(dict(SIN_RESPUESTA))
            continue
        x = numero(v)
        if x is None or not x.is_integer() or int(x) not in puntos:
            salida.append(_no_interpretada(v))
            malas += 1
            continue
        c = int(x)
        texto = (f"{c} en escala {lo}–{hi}, donde {lo} = {anclas[lo]} y {hi} = {anclas[hi]}" if con_anclas
                 else f"{c} de {hi}")
        salida.append({"estado": "respondida", "valor": c, "significado": texto,
                       "nivel": escalas.nivel(puntos.index(c) + 1, len(puntos), None)})
    descripcion: dict[str, Any] = {
        "puntos": len(puntos),
        "etiquetas": {str(c): anclas.get(c, str(c)) for c in puntos},
        "niveles": escalas.mapa_niveles(puntos, None),
        "invertida": False,
        "rango": [lo, hi],
    }
    if anclas:
        descripcion["anclas"] = {str(k): v for k, v in sorted(anclas.items())}
    return ColumnaInterpretada(salida, descripcion, [], malas)


def _unidad(etiqueta: str) -> str | None:
    texto = palabras(etiqueta)
    for palabra, unidad in (reglas().get("unidades") or {}).items():
        if f" {normalizar(palabra)} " in texto:
            return str(unidad)
    return None


def numerica(spec: dict[str, Any], valores: list[str], calificacion: bool = False) -> ColumnaInterpretada:
    """Calificación: «8.5 (escala 0–10)». Numérica: el valor con su unidad («14 horas»)."""
    rango = spec.get("rango") if calificacion else None
    unidad = None if calificacion else _unidad(spec.get("etiqueta") or "")
    salida, malas = [], 0
    for v in valores:
        if _vacia(v):
            salida.append(dict(SIN_RESPUESTA))
            continue
        x = numero(v)
        if x is None:
            salida.append(_no_interpretada(v))
            malas += 1
            continue
        if rango:
            texto = f"{_fmt(x)} (escala {_fmt(rango[0])}–{_fmt(rango[1])})"
        else:
            texto = f"{_fmt(x)} {unidad}" if unidad else _fmt(x)
        salida.append({"estado": "respondida", "valor": int(x) if x.is_integer() else x, "significado": texto})
    descripcion: dict[str, Any] = {}
    if rango:
        descripcion["rango"] = [rango[0], rango[1]]
    if unidad:
        descripcion["unidad"] = unidad
    return ColumnaInterpretada(salida, descripcion or None, [], malas)


# ── Opciones ───────────────────────────────────────────────────────────────────


def binaria(valores: list[str]) -> ColumnaInterpretada:
    """Sí/No, 1/0, True/False, S/N… → «Sí» / «No». Otras parejas (p. ej. turnos) quedan
    con su forma canónica y sin nivel."""
    si = {normalizar(x) for x in reglas().get("binaria_si", [])}
    no = {normalizar(x) for x in reglas().get("binaria_no", [])}
    presentes = [v for v in valores if not _vacia(v)]
    es_si_no = all(normalizar(v) in si | no for v in presentes)
    canon = _formas_canonicas(presentes)
    salida, opciones = [], []
    for v in valores:
        if _vacia(v):
            salida.append(dict(SIN_RESPUESTA))
            continue
        n = normalizar(v)
        if es_si_no:
            significado, nivel = ("Sí", "si") if n in si else ("No", "no")
            r = {"estado": "respondida", "valor": v.strip(), "significado": significado, "nivel": nivel}
        else:
            significado = canon[n]
            r = {"estado": "respondida", "valor": v.strip(), "significado": significado}
        if significado not in opciones:
            opciones.append(significado)
        salida.append(r)
    if es_si_no:
        opciones = [o for o in ("Sí", "No") if o in opciones]
    return ColumnaInterpretada(salida, None, opciones, 0)


def categorica(valores: list[str]) -> ColumnaInterpretada:
    """Etiqueta normalizada: «  pedagogia», «Pedagogía» → la grafía más frecuente."""
    presentes = [v for v in valores if not _vacia(v)]
    canon = _formas_canonicas(presentes)
    salida = [dict(SIN_RESPUESTA) if _vacia(v) else {"estado": "respondida", "valor": v.strip(), "significado": canon[normalizar(v)]}
              for v in valores]
    frecuencias = Counter(r["significado"] for r in salida if r["estado"] == "respondida")
    return ColumnaInterpretada(salida, None, [o for o, _ in frecuencias.most_common()], 0)


def _partir(valor: str, separadores: list[str]) -> list[str]:
    partes = [valor]
    for sep in separadores:
        partes = [p for parte in partes for p in parte.split(sep)]
    return [p.strip() for p in partes if p.strip()]


def opcion_multiple(valores: list[str], ranking: bool = False) -> ColumnaInterpretada:
    """Lista de opciones seleccionadas (en ranking, ordenada: posición 1 = primera)."""
    clave = "separadores_ranking" if ranking else "separadores_multiple"
    separadores = reglas().get(clave) or [",", ";"]
    # Si alguna parte de una lista con «;» lleva coma, la coma es del texto de la opción.
    coma_dentro = any("," in parte for v in valores if not _vacia(v) and ";" in v for parte in v.split(";"))
    if not ranking and ";" in separadores and coma_dentro:
        separadores = [";"]
    listas = [[] if _vacia(v) else _partir(v, separadores) for v in valores]
    canon = _formas_canonicas([o for lista in listas for o in lista])
    salida = []
    for v, lista in zip(valores, listas):
        if not lista:
            salida.append(dict(SIN_RESPUESTA))
            continue
        seleccion: list[str] = []
        for o in lista:
            c = canon[normalizar(o)]
            if c not in seleccion:
                seleccion.append(c)
        texto = ", ".join(f"{i}.º {o}" for i, o in enumerate(seleccion, start=1)) if ranking else ", ".join(seleccion)
        salida.append({"estado": "respondida", "valor": v.strip(), "seleccion": seleccion, "significado": texto})
    frecuencias = Counter(o for r in salida for o in r.get("seleccion") or [])
    return ColumnaInterpretada(salida, None, [o for o, _ in frecuencias.most_common()], 0)


def texto(valores: list[str]) -> ColumnaInterpretada:
    """Respuestas abiertas: tal cual."""
    return ColumnaInterpretada(
        [dict(SIN_RESPUESTA) if _vacia(v) else {"estado": "respondida", "valor": v.strip(), "texto": v.strip()} for v in valores]
    )


# ── Despacho por tipo ──────────────────────────────────────────────────────────


_ESCALAS = ("likert", "cuadricula", "escala_lineal")


def _es_escala(tipo: str, etiquetas: dict[str, str], valores: list[str]) -> bool:
    """¿Las etiquetas describen una escala (anclas) o categorías sin orden?

    Escala: la columna ya es de escala y las etiquetas son de una escala conocida («Nada … Mucho», «Nunca …
    Siempre») o son solo los extremos («1 = Nada», «5 = Mucho»). Si no, cada código es una categoría
    («1 = Matutino, 2 = Vespertino, 3 = Mixto»), aunque la limpieza la haya tomado por una escala.
    """
    if tipo not in _ESCALAS or not all(k.lstrip("-").isdigit() for k in etiquetas):
        return False
    if escalas.escala_por_anclas({int(k): v for k, v in etiquetas.items()}):
        return True
    observados = {significados.codigo(v) for v in valores if not _vacia(v)}
    return len(etiquetas) <= 2 < len(observados)


def codificada(valores: list[str], etiquetas: dict[str, str]) -> ColumnaInterpretada:
    """Códigos de categoría con su significado: «2» → «Mujer». Un código sin etiqueta se conserva tal cual."""
    salida, vistas = [], []
    for v in valores:
        if _vacia(v):
            salida.append(dict(SIN_RESPUESTA))
            continue
        c = v.strip()
        significado = significados.etiqueta(etiquetas, c) or c
        salida.append({"estado": "respondida", "valor": c, "significado": significado})
        vistas.append(significado)
    # Opciones en el orden del diccionario; después, los códigos que aparecen y no tienen etiqueta.
    opciones = [e for e in etiquetas.values() if e in vistas] + [o for o in dict.fromkeys(vistas) if o not in etiquetas.values()]
    return ColumnaInterpretada(salida, None, opciones, 0, tipo="categorica")


def _con_etiquetas(spec: dict[str, Any], valores: list[str], anclas: dict[int, str] | None) -> ColumnaInterpretada | None:
    """Interpretación con el significado de los códigos, o None si la columna no trae códigos con etiqueta."""
    etiquetas = {significados.codigo(k): v for k, v in (spec.get("etiquetas_valor") or {}).items() if v}
    tipo = spec.get("tipo_canonico") or "texto_corto"
    partes = [p for v in valores if not _vacia(v) for p in (re.split(r"[,;]", v) if tipo in ("opcion_multiple_varias", "ranking") else [v])]
    if not etiquetas or not any(significados.codigo(p) in etiquetas for p in partes):
        return None  # p. ej. una escala de texto («De acuerdo»): sus valores no son los códigos del diccionario
    if _es_escala(tipo, etiquetas, valores):
        anclas = {**(anclas or {}), **{int(k): v for k, v in etiquetas.items()}}
        if tipo in ("likert", "cuadricula") and spec.get("likert"):
            return likert(spec, valores, anclas)
        return escala_lineal(spec, valores, anclas)
    if tipo in ("opcion_multiple_varias", "ranking"):
        # «1,3» → «Libros,Videos»: cada parte es un código.
        mapeados = [v if _vacia(v) else re.sub(r"[^,;]+", lambda m: significados.etiqueta(etiquetas, m.group().strip()) or m.group(), v)
                    for v in valores]
        return opcion_multiple(mapeados, ranking=tipo == "ranking")
    if tipo == "binaria":
        # «1 = Sí, 2 = No»: con la etiqueta, la binaria reconoce Sí/No (y su nivel); el valor sigue siendo el código.
        col = binaria([v if _vacia(v) else (significados.etiqueta(etiquetas, v) or v) for v in valores])
        for r, v in zip(col.respuestas, valores):
            if r.get("estado") == "respondida":
                r["valor"] = v.strip()
        return col
    return codificada(valores, etiquetas)


def interpretar_columna(spec: dict[str, Any], valores: list[str], anclas: dict[int, str] | None = None) -> ColumnaInterpretada:
    """Interpreta todas las respuestas de una columna según su tipo canónico."""
    if (con_etiquetas := _con_etiquetas(spec, valores, anclas)) is not None:
        return con_etiquetas
    tipo = spec.get("tipo_canonico") or "texto_corto"
    if tipo in ("likert", "cuadricula") and spec.get("likert"):
        return likert(spec, valores, anclas)
    if tipo == "escala_lineal":
        return escala_lineal(spec, valores, anclas)
    if tipo in ("numerica", "calificacion"):
        return numerica(spec, valores, calificacion=tipo == "calificacion")
    if tipo == "binaria":
        return binaria(valores)
    if tipo == "categorica":
        return categorica(valores)
    if tipo in ("opcion_multiple_varias", "ranking"):
        return opcion_multiple(valores, ranking=tipo == "ranking")
    return texto(valores)
