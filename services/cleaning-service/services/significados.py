"""Significado de los códigos en la limpieza (microdatos).

Qué columnas lo necesitan, qué trae el diccionario de datos y qué escribe la persona investigadora. Se
guarda en el reporte mientras la versión espera decisiones (`reporte.codigos`) y, al confirmar, pasa a
`reporte.especifico.<tipo>.significados`, que leen metadata-service y knowledge-service
(`shared/conocimiento/significados.py`).

Una columna lo necesita si su encabezado es un código («P5», «Q12_3») o si sus respuestas son pocos
códigos cortos («1», «2», «A»). En las pruebas, cada reactivo (sus opciones son letras o números).
Nada de esto es obligatorio: sin significado, la pregunta conserva su encabezado y el código su valor.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from shared.conocimiento.significados import Diccionario, clave_variable, codigo
from shared.parsing.formato import es_codigo as encabezado_en_codigo

from services.motores import ResultadoAutomatico

_MAX_PREGUNTA = 500
_MAX_ETIQUETA = 200
_NO_SON_OPCION = {"nula", "NR"}


def _de_encuesta(automatico: ResultadoAutomatico, dic: Diccionario | None) -> list[dict[str, Any]]:
    ajenas = {h.objetivo for h in automatico.hallazgos if h.tipo == "columna_ajena"}
    salida = []
    for c in (automatico.estadistica or {}).get("columnas") or []:
        if c["id"] in ajenas:
            continue
        codigos = c.get("codigos") or []
        en_codigo = encabezado_en_codigo(c["etiqueta"])
        en_diccionario = dic is not None and dic.buscar(c["etiqueta"], c["id"]) is not None
        if not (codigos or en_codigo or en_diccionario):
            continue
        n_de = {str(f["valor"]): f["n"] for f in (c.get("frecuencias") or {}).get("tabla") or []}
        salida.append({
            "clave": c["id"], "etiqueta": c["etiqueta"], "tipo": c.get("tipo"), "encabezado_codigo": en_codigo,
            "codigos": [{"codigo": v, "n": n_de.get(v)} for v in codigos],
        })
    return salida


def _de_prueba(automatico: ResultadoAutomatico) -> list[dict[str, Any]]:
    salida = []
    for r in (automatico.estadistica or {}).get("reactivos") or []:
        opciones = [d for d in r.get("distribucion") or [] if d.get("opcion") not in _NO_SON_OPCION]
        salida.append({
            "clave": r["pregunta"], "etiqueta": r["pregunta"], "tipo": r.get("tipo_reactivo"),
            "encabezado_codigo": encabezado_en_codigo(r["pregunta"]),
            "codigos": [{"codigo": str(d["opcion"]), "n": d.get("n")} for d in opciones],
        })
    return salida


def candidatos(tipo: str, automatico: ResultadoAutomatico, dic: Diccionario | None = None) -> list[dict[str, Any]]:
    """Columnas (encuesta) o reactivos (prueba) a los que se les puede dar texto y significado."""
    if tipo == "encuesta":
        return _de_encuesta(automatico, dic)
    if tipo == "prueba_estandarizada":
        return _de_prueba(automatico)
    return []


def desde_diccionario(dic: Diccionario, cands: list[dict[str, Any]], nombre: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Significados que trae el diccionario para cada candidata, y el resumen del emparejamiento."""
    sig: dict[str, Any] = {}
    usadas: set[str] = set()
    for c in cands:
        e = dic.buscar(c["etiqueta"], c["clave"])
        if e is None:
            continue
        usadas.add(clave_variable(e.variable))
        sig[c["clave"]] = {"pregunta": e.pregunta, "valores": dict(e.valores), "origen": "diccionario"}
    sin_columna = [e.variable for k, e in dic.entradas.items() if k not in usadas]
    return sig, {"nombre": nombre, "emparejadas": len(sig), "sin_columna": sin_columna[:20], "n_sin_columna": len(sin_columna)}


def aplicar_cambios(
    actuales: dict[str, Any], cambios: dict[str, dict[str, Any] | None], cands: list[dict[str, Any]]
) -> dict[str, Any]:
    """Mezcla lo que escribe la persona investigadora; `None` en una clave borra su significado."""
    validas = {c["clave"]: c for c in cands}
    salida = dict(actuales)
    for clave, cambio in cambios.items():
        if clave not in validas:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Columna desconocida: {clave}")
        if cambio is None:
            salida.pop(clave, None)
            continue
        pregunta = " ".join(str(cambio.get("pregunta") or "").split())[:_MAX_PREGUNTA] or None
        valores = {}
        for k, v in (cambio.get("valores") or {}).items():
            etiqueta = " ".join(str(v or "").split())[:_MAX_ETIQUETA]
            if str(k).strip() and etiqueta:
                valores[codigo(k)] = etiqueta
        if pregunta or valores:
            salida[clave] = {"pregunta": pregunta, "valores": valores, "origen": "investigador"}
        else:
            salida.pop(clave, None)
    return salida


def para_especifico(sig: dict[str, Any], cands: list[dict[str, Any]]) -> dict[str, Any]:
    """Lo que queda en el reporte confirmado: solo columnas que existen y con algo que decir."""
    claves = {c["clave"] for c in cands}
    return {k: {"pregunta": v.get("pregunta"), "valores": v.get("valores") or {}}
            for k, v in sig.items() if k in claves and (v.get("pregunta") or v.get("valores"))}


def vista(codigos: dict[str, Any] | None) -> dict[str, Any] | None:
    """Para la interfaz: cada candidata con lo que ya tiene (del diccionario o escrito a mano)."""
    if not codigos or not codigos.get("columnas"):
        return None
    sig = codigos.get("significados") or {}
    return {
        "columnas": [
            {**c, "pregunta": (sig.get(c["clave"]) or {}).get("pregunta"),
             "etiquetas": (sig.get(c["clave"]) or {}).get("valores") or {},
             "origen": (sig.get(c["clave"]) or {}).get("origen")}
            for c in codigos["columnas"]
        ],
        "diccionario": codigos.get("diccionario"),
    }
