"""Significado de los códigos de un instrumento: texto de las preguntas en código y etiqueta de cada valor.

Los microdatos traen encabezados como «P5» y respuestas como «1» o «B». Su significado viene en un
**diccionario de datos** (el libro de códigos que acompaña a los microdatos) o lo escribe la persona
investigadora en la limpieza. Lo confirmado queda en el reporte de limpieza:

    reporte_limpieza.especifico.<tipo>.significados = {
        "<columna o reactivo>": {"pregunta": "¿Cuál es tu sexo?", "valores": {"1": "Hombre", "2": "Mujer"}},
    }

Lo leen metadata-service (texto y opciones de cada pregunta) y knowledge-service (texto de la pregunta y
significado de cada respuesta en el documento final), por eso vive en `shared`.

Formatos del diccionario (CSV, XLSX o XLS), con encabezados en español o en inglés:
  - largo: una fila por valor — variable · pregunta · valor · etiqueta (la variable y la pregunta pueden ir
    solo en la primera fila de cada variable);
  - ancho: una fila por variable — variable · pregunta · valores («1 = Hombre; 2 = Mujer»).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from shared.parsing.tabular_parser import TabularParseError, read_tabular

# Encabezados reconocidos de cada columna del diccionario (normalizados: minúsculas, sin acentos, «_» = espacio).
_COL_VARIABLE = {"variable", "nombre variable", "nombre de la variable", "columna", "campo", "var", "codigo variable",
                 "clave", "name", "variable name", "item", "reactivo"}
_COL_PREGUNTA = {"pregunta", "texto", "texto de la pregunta", "enunciado", "etiqueta variable", "etiqueta de la variable",
                 "descripcion", "descripcion de la variable", "label", "variable label", "question"}
_COL_VALOR = {"valor", "codigo", "código", "codigo valor", "categoria", "value", "code", "opcion"}
_COL_ETIQUETA = {"etiqueta", "etiqueta valor", "etiqueta del valor", "significado", "descripcion valor",
                 "descripcion del valor", "value label", "categoria descripcion"}
_COL_VALORES = {"valores", "codigos", "categorias", "etiquetas de valor", "value labels", "opciones"}

# Valor que parece código: entero corto («1», «02», «-9», «3.0») o una sola letra.
_RE_CODIGO = re.compile(r"^(?:-?\d{1,3}(?:\.0+)?|[A-Za-z])$")
# «1 = Hombre», «2: Mujer», «3 - Otro», «A) Sí»
_RE_PAR = re.compile(r"^\s*(-?\d{1,3}(?:\.0+)?|[A-Za-z])\s*(?:=|:|\)|-|–)\s*(.+?)\s*$")


class DiccionarioInvalido(ValueError):
    """El archivo no se pudo leer como diccionario de datos (mensaje para la persona investigadora)."""


def _norm(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().replace("_", " ").replace("-", " ").split())


def clave_variable(nombre: str) -> str:
    """Nombre de variable comparable: «P1_4_1», «p1.4.1» y «P1 4 1» son la misma."""
    return re.sub(r"[^a-z0-9]", "", _norm(nombre))


def codigo(valor: Any) -> str:
    """Código comparable: «01», «1.0» y «1» son el mismo; las letras van en mayúscula."""
    t = str(valor or "").strip()
    if re.fullmatch(r"-?\d+(?:\.0+)?", t):
        return str(int(float(t)))
    return t.upper() if len(t) == 1 else t


def es_codigo(valor: Any) -> bool:
    return bool(_RE_CODIGO.match(str(valor or "").strip()))


@dataclass
class EntradaDiccionario:
    variable: str
    pregunta: str | None = None
    valores: dict[str, str] = field(default_factory=dict)


@dataclass
class Diccionario:
    entradas: dict[str, EntradaDiccionario] = field(default_factory=dict)  # por clave_variable

    def buscar(self, *nombres: str) -> EntradaDiccionario | None:
        for n in nombres:
            if n and (e := self.entradas.get(clave_variable(n))):
                return e
        return None


def _indice(encabezados: list[str], nombres: set[str]) -> int | None:
    for i, h in enumerate(encabezados):
        if _norm(h) in nombres:
            return i
    return None


def _pares(texto: str) -> dict[str, str]:
    """«1 = Hombre; 2 = Mujer» (también con «|» o saltos de línea) → {"1": "Hombre", "2": "Mujer"}."""
    salida = {}
    for parte in re.split(r"[;|\n]+", texto or ""):
        if m := _RE_PAR.match(parte):
            salida[codigo(m.group(1))] = m.group(2)
    return salida


def leer_diccionario(contenido: bytes, extension: str) -> Diccionario:
    """Lee un diccionario de datos en formato largo o ancho. Lanza DiccionarioInvalido con el motivo."""
    try:
        tabla = read_tabular(contenido, extension)
    except TabularParseError as exc:
        raise DiccionarioInvalido(f"No se pudo leer el diccionario de datos: {exc}") from exc
    enc = tabla.headers or []
    i_var = _indice(enc, _COL_VARIABLE)
    if i_var is None:
        raise DiccionarioInvalido(
            "El diccionario de datos necesita una columna «variable» con el nombre de cada columna del archivo "
            "(y, opcionalmente, «pregunta», «valor» y «etiqueta»)."
        )
    i_preg, i_val, i_etq, i_vals = (_indice(enc, s) for s in (_COL_PREGUNTA, _COL_VALOR, _COL_ETIQUETA, _COL_VALORES))
    celda = lambda fila, i: (fila[i].strip() if i is not None and i < len(fila) else "")  # noqa: E731

    dic = Diccionario()
    actual: EntradaDiccionario | None = None
    for fila in tabla.rows:
        variable = celda(fila, i_var)
        if variable:
            actual = dic.entradas.setdefault(clave_variable(variable), EntradaDiccionario(variable=variable))
        if actual is None:
            continue
        if (pregunta := celda(fila, i_preg)) and not actual.pregunta:
            actual.pregunta = pregunta
        valor, etiqueta = celda(fila, i_val), celda(fila, i_etq)
        if valor and etiqueta:
            actual.valores[codigo(valor)] = etiqueta
        if i_vals is not None:
            actual.valores.update(_pares(celda(fila, i_vals)))
    if not dic.entradas:
        raise DiccionarioInvalido("El diccionario de datos no tiene ninguna variable.")
    return dic


# ── Lectura desde el reporte de limpieza ──────────────────────────────────────


def de_reporte(reporte: dict[str, Any] | None, tipo: str) -> dict[str, dict[str, Any]]:
    """{columna o reactivo: {"pregunta": str | None, "valores": {código: etiqueta}}} de la limpieza confirmada."""
    esp = ((reporte or {}).get("especifico") or {}).get(tipo) or {}
    salida = {}
    for clave, s in (esp.get("significados") or {}).items():
        valores = {codigo(k): str(v).strip() for k, v in (s.get("valores") or {}).items() if str(v or "").strip()}
        pregunta = " ".join(str(s.get("pregunta") or "").split()) or None
        if pregunta or valores:
            salida[clave] = {"pregunta": pregunta, "valores": valores}
    return salida


def etiqueta(valores: dict[str, str] | None, valor: Any) -> str | None:
    """Etiqueta del código `valor` (o None si no está en el diccionario)."""
    if not valores:
        return None
    return valores.get(codigo(valor))
