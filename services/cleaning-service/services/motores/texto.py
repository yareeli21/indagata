"""Limpieza de texto (Figura 1 del documento de reglas).

    normalización → eliminación de ruido (marcas de tiempo, IDs, números de página)
    → reconstrucción de palabras → normalización de espacios → ¿queda ruido?

El ciclo se repite como máximo `max_iteraciones` veces (3 por defecto) y se detiene
antes si ya no se detecta ruido o si una iteración no cambió nada. El ruido que
quede se reporta (no se inventa una corrección).

Antes del ciclo se reparan los acentos rotos («educaciÃ³n» → «educación», `codificacion.py`).
Las letras espaciadas que empiezan con una palabra de una letra («o a n s i e d a d») son ambiguas:
pueden ser «o ansiedad» u «oansiedad» («y a n o» puede ser «ya no»). Se decide con el vocabulario del
propio documento; si no alcanza, se unen como antes («e d u c a c i ó n» → «educación») y la palabra se
reporta como unión dudosa para que el investigador la revise.

Lo usan las entrevistas y las pruebas estandarizadas entregadas como documento.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from services.motores import codificacion

# ── Patrones de ruido ──────────────────────────────────────────────────────────
# Marcas de tiempo: [00:12:31], (01:02), 00:00:05,120 --> 00:00:08,000 (subtítulos).
_TIEMPO = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?"
_RANGO_SUBTITULO = re.compile(rf"^\s*{_TIEMPO}\s*-->\s*{_TIEMPO}\s*$", re.M)
_TIEMPO_ENTRE_SIGNOS = re.compile(rf"[\[(]\s*{_TIEMPO}\s*[\])]")
_TIEMPO_INICIO_LINEA = re.compile(rf"^(\s*){_TIEMPO}(\s*[-–—]\s*|\s+)", re.M)
# Números de página: «Página 3», «Pág. 3 de 10», «Page 2/9», «- 4 -» o un número solo en su línea.
_PAGINA = re.compile(
    r"^\s*(?:p[aá]gina|p[aá]g\.?|page|p\.)\s*\d+(?:\s*(?:de|/|of)\s*\d+)?\s*$|^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$",
    re.M | re.I,
)
# Líneas que solo contienen un identificador: «ID: ENT-003», «Folio 0045», «[ID 12]».
_LINEA_ID = re.compile(
    r"^\s*\[?\s*(?:id|folio|c[oó]digo|registro|clave)\s*[:#-]?\s*[\w-]+\s*\]?\s*$", re.M | re.I
)
_ID_ENTRE_CORCHETES = re.compile(r"\[\s*(?:id|folio)\s*[:#-]?\s*[\w-]+\s*\]", re.I)
# Separadores decorativos: «-----», «*****», «=====».
_SEPARADOR = re.compile(r"^\s*[-_=*~#.·•]{3,}\s*$", re.M)
# Palabras partidas: guion al final de línea («educa-\nción») y letras espaciadas («e d u c a c i ó n»).
_GUION_FIN_LINEA = re.compile(r"(\w)[-‐]\n\s*(\w)")
_LETRAS_ESPACIADAS = re.compile(r"\b(?:[A-Za-zÁÉÍÓÚÑáéíóúñ] ){3,}[A-Za-zÁÉÍÓÚÑáéíóúñ]\b")
# «FIN DE LA ENTREVISTA» se repite en cada bloque de un archivo con varias entrevistas: no es encabezado.
_FIN = re.compile(r"^\s*fin\b", re.I)
_INVISIBLES = re.compile(r"[​-‏⁠﻿]")


@dataclass
class ResultadoTexto:
    texto: str
    iteraciones: int
    eliminado: dict[str, int] = field(default_factory=dict)  # tipo de ruido → cuántos
    residual: list[dict] = field(default_factory=list)  # [{tipo, linea, texto}]
    transformaciones: list[dict] = field(default_factory=list)
    dudosas: list[str] = field(default_factory=list)  # letras espaciadas unidas sin poder confirmarlo («oansiedad»)


def normalizar(texto: str) -> str:
    """Unicode NFC, saltos de línea uniformes, sin caracteres invisibles ni de control."""
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    texto = texto.replace(" ", " ").replace(" ", " ")
    texto = _INVISIBLES.sub("", texto)
    texto = "".join(c for c in texto if c == "\n" or unicodedata.category(c)[0] != "C")
    # Negritas de Markdown alrededor de etiquetas («**E:**»): estorban para leer hablantes.
    return re.sub(r"\*\*([^*\n]{1,40})\*\*", r"\1", texto)


def _contar_y_quitar(patron: re.Pattern, texto: str, reemplazo: str = "") -> tuple[str, int]:
    nuevo, n = patron.subn(reemplazo, texto)
    return nuevo, n


def eliminar_ruido(texto: str) -> tuple[str, dict[str, int]]:
    """Quita marcas de tiempo, números de página, IDs y separadores."""
    conteo: dict[str, int] = {}
    texto, conteo["marcas_de_tiempo"] = _contar_y_quitar(_RANGO_SUBTITULO, texto)
    texto, n = _contar_y_quitar(_TIEMPO_ENTRE_SIGNOS, texto)
    conteo["marcas_de_tiempo"] += n
    texto, n = _contar_y_quitar(_TIEMPO_INICIO_LINEA, texto, r"\1")
    conteo["marcas_de_tiempo"] += n
    texto, conteo["numeros_de_pagina"] = _contar_y_quitar(_PAGINA, texto)
    texto, conteo["identificadores"] = _contar_y_quitar(_LINEA_ID, texto)
    texto, n = _contar_y_quitar(_ID_ENTRE_CORCHETES, texto)
    conteo["identificadores"] += n
    texto, conteo["separadores"] = _contar_y_quitar(_SEPARADOR, texto)
    return texto, {k: v for k, v in conteo.items() if v}


_PALABRAS_DE_UNA_LETRA = {"y", "o", "a", "e", "u"}


def _vocabulario(texto: str) -> set[str]:
    """Palabras del documento (sin las letras espaciadas), en minúsculas."""
    return {p.lower() for p in re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]{2,}", _LETRAS_ESPACIADAS.sub(" ", texto))}


def reconstruir_palabras(texto: str, dudosas: list[str] | None = None) -> tuple[str, int]:
    """Une palabras partidas por guion de fin de línea o con letras separadas por espacios.

    Las uniones que el vocabulario del documento no pudo confirmar se agregan a `dudosas`.
    """
    texto, n_guion = _GUION_FIN_LINEA.subn(r"\1\2", texto)
    vocabulario: set[str] | None = None
    n_letras = 0

    def unir(m: re.Match[str]) -> str:
        nonlocal vocabulario, n_letras
        letras = m.group(0).split(" ")
        todo = "".join(letras)
        if letras[0].lower() in _PALABRAS_DE_UNA_LETRA and len(letras) >= 5:
            # «o a n s i e d a d»: ¿«o ansiedad» u «oansiedad»? Lo dice el resto del documento.
            vocabulario = vocabulario if vocabulario is not None else _vocabulario(texto)
            resto = "".join(letras[1:])
            con_resto, con_todo = resto.lower() in vocabulario, todo.lower() in vocabulario
            if con_resto and not con_todo:
                n_letras += 1
                return f"{letras[0]} {resto}"
            if con_todo == con_resto and dudosas is not None:
                dudosas.append(todo)  # el documento no lo resuelve: se une como antes y se reporta
        n_letras += 1
        return todo

    texto = _LETRAS_ESPACIADAS.sub(unir, texto)
    return texto, n_guion + n_letras


def normalizar_espacios(texto: str) -> str:
    """Espacios simples, sin espacios antes de signos, a lo sumo una línea en blanco seguida."""
    lineas = [" ".join(l.split()) for l in texto.split("\n")]
    texto = "\n".join(lineas)
    texto = re.sub(r" +([,.;:!?)\]])", r"\1", texto)
    texto = re.sub(r"([(\[¿¡]) +", r"\1", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def detectar_ruido(texto: str) -> list[dict]:
    """Ruido que aún queda (para decidir si repetir el ciclo y para reportarlo)."""
    hallado: list[dict] = []
    patrones = [
        ("marca_de_tiempo", _RANGO_SUBTITULO),
        ("marca_de_tiempo", _TIEMPO_ENTRE_SIGNOS),
        ("numero_de_pagina", _PAGINA),
        ("identificador", _LINEA_ID),
        ("separador", _SEPARADOR),
        ("palabra_partida", _GUION_FIN_LINEA),
        ("letras_espaciadas", _LETRAS_ESPACIADAS),
    ]
    for tipo, patron in patrones:
        for m in patron.finditer(texto):
            fragmento = m.group(0).strip()
            if not fragmento:
                continue
            linea = texto.count("\n", 0, m.start()) + 1
            hallado.append({"tipo": tipo, "linea": linea, "texto": fragmento[:80]})
    return hallado


def quitar_lineas_repetidas(texto: str, minimo: int = 3) -> tuple[str, int]:
    """Quita encabezados y pies de página: líneas idénticas que se repiten al menos `minimo` veces.

    No se tocan las líneas cortas («Sí.», «Ajá.»), las que empiezan con una etiqueta seguida de «:»
    («P1: ¿Cuál es tu edad?» se repite en cada entrevista de un mismo guion), las líneas sin letras ni números
    («-----», «────»: separadores, con su propia regla) ni «FIN DE LA ENTREVISTA». Devuelve (texto, líneas quitadas).
    """
    lineas = texto.split("\n")
    conteo = Counter(l.strip() for l in lineas if l.strip())
    repetidas = {l for l, n in conteo.items() if n >= minimo and len(l) >= 12 and ":" not in l[:40]
                 and any(ch.isalnum() for ch in l) and not _FIN.match(l)}
    if not repetidas:
        return texto, 0
    quitadas = sum(1 for l in lineas if l.strip() in repetidas)
    return "\n".join(l for l in lineas if l.strip() not in repetidas), quitadas


def limpiar(texto: str, max_iteraciones: int = 3) -> ResultadoTexto:
    """Ejecuta el ciclo de la Figura 1 y devuelve el texto limpio con su bitácora."""
    texto, acentos = codificacion.reparar(texto)
    actual = normalizar(texto)
    eliminado: dict[str, int] = {}
    dudosas: list[str] = []
    reconstruidas = 0
    iteraciones = 0
    while iteraciones < max_iteraciones:
        iteraciones += 1
        anterior = actual
        actual, conteo = eliminar_ruido(actual)
        for k, v in conteo.items():
            eliminado[k] = eliminado.get(k, 0) + v
        actual, n = reconstruir_palabras(actual, dudosas)
        reconstruidas += n
        actual = normalizar_espacios(actual)
        # Se detiene si ya no hay ruido o si la iteración no cambió nada.
        if not detectar_ruido(actual) or actual == anterior:
            break

    transformaciones = [{"regla": "texto_normalizado", "detalle": "Texto en UTF-8 normalizado (saltos de línea, caracteres invisibles).", "afectados": None}]
    if acentos:
        transformaciones.append({"regla": "acentos_reparados", "detalle": "Acentos rotos al copiar entre programas, reparados («educaciÃ³n» → «educación»).", "afectados": acentos})
    nombres = {
        "marcas_de_tiempo": "Marcas de tiempo eliminadas",
        "numeros_de_pagina": "Números de página eliminados",
        "identificadores": "Identificadores eliminados",
        "separadores": "Líneas separadoras eliminadas",
    }
    for clave, n in eliminado.items():
        transformaciones.append({"regla": clave, "detalle": nombres.get(clave, clave), "afectados": n})
    if reconstruidas:
        transformaciones.append({"regla": "palabras_reconstruidas", "detalle": "Palabras partidas por guion o espacios reconstruidas.", "afectados": reconstruidas})
    transformaciones.append({"regla": "espacios_normalizados", "detalle": "Espacios y líneas en blanco normalizados.", "afectados": None})
    transformaciones.append({"regla": "ciclo_de_ruido", "detalle": f"Ciclo de limpieza de ruido: {iteraciones} iteración(es).", "afectados": iteraciones})
    if reconstruidas:
        eliminado["palabras_reconstruidas"] = reconstruidas
    return ResultadoTexto(actual, iteraciones, eliminado, detectar_ruido(actual), transformaciones, list(dict.fromkeys(dudosas)))


def quitar_lineas(texto: str, numeros: set[int]) -> str:
    """Elimina las líneas indicadas (1-indexadas); se usa para el ruido residual."""
    return "\n".join(l for i, l in enumerate(texto.split("\n"), start=1) if i not in numeros)
