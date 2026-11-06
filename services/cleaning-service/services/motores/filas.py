"""Estructura de las filas de una tabla (encuestas y pruebas), antes de interpretar las respuestas.

  - Encabezado repetido a mitad del archivo (dos exportaciones pegadas): se descarta y se reporta.
  - Fila de totales o promedios al final («Promedio», «Total»): se propone eliminarla ANTES de inferir los
    tipos, porque sus decimales convertían una escala 1–5 en una calificación 0–10.
  - Segunda fila de encabezado con el texto de las preguntas (Qualtrics, SurveyMonkey): se propone quitarla
    y guardar su texto como descripción de cada columna.
  - Filas con más o menos celdas que el encabezado y filas corridas una columna (falta o sobra una celda):
    se comparan los valores de la fila con lo que suele traer cada columna; si al mover la fila desde una
    columna todos encajan, se propone repararla para que todas las filas tengan las mismas columnas.

Las filas se numeran desde 1 sin el encabezado, como en el archivo.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from services.configuracion import normalizar_texto

# Primera celda de una fila de resumen (exportaciones de Excel con totales al final).
_RESUMEN = re.compile(
    r"^(promedio|promedios|media|medias|total|totales|suma|sumas|subtotal|mediana|moda|desviaci[oó]n( est[aá]ndar)?|"
    r"m[ií]nimo|m[aá]ximo|conteo|average|mean|sum|totals?|std|median)$",
    re.I,
)
_MIN_VALORES_PERFIL = 5
_MAX_CATEGORIAS = 25


def _numero(v: str) -> float | None:
    texto = v.strip().replace(" ", "")
    if texto.count(",") == 1 and "." not in texto:
        texto = texto.replace(",", ".")
    try:
        x = float(texto)
    except ValueError:
        return None
    return x if x == x and abs(x) != float("inf") else None


# ── Encabezado repetido, fila de resumen y segunda fila de encabezado ──────────


def es_encabezado(celdas: list[str], encabezados: list[str]) -> bool:
    """¿La fila repite el encabezado (al menos el 80 % de las columnas con nombre)?"""
    pares = [(normalizar_texto(c), normalizar_texto(h)) for c, h in zip(celdas, encabezados) if h.strip()]
    return bool(pares) and sum(1 for c, h in pares if c == h) >= 0.8 * len(pares)


def es_resumen(celdas: list[str]) -> bool:
    """«Promedio», «Total»… en la primera celda con texto y el resto números o vacío (al menos 2 números)."""
    con_dato = [c.strip() for c in celdas if c.strip()]
    if len(con_dato) < 3 or not _RESUMEN.match(normalizar_texto(con_dato[0])):
        return False
    resto = con_dato[1:]
    return sum(1 for c in resto if _numero(c) is not None) >= max(2, 0.9 * len(resto))


def segunda_fila_encabezado(encabezados: list[str], filas: list[list[str]]) -> bool:
    """¿La primera fila de datos es el texto de las preguntas?

    Se reconoce porque, en las columnas que en el resto de las filas son números, ella trae texto, y porque sus
    valores no se repiten en las demás filas de su columna.
    """
    if len(filas) < 5:
        return False
    primera, resto = filas[0], filas[1:]
    n = len(encabezados)
    con_texto = [j for j in range(n) if j < len(primera) and primera[j].strip()]
    if len(con_texto) < max(3, 0.6 * n):
        return False
    numericas = []
    nuevas = 0
    for j in con_texto:
        valores = [f[j].strip() for f in resto if j < len(f) and f[j].strip()]
        if not valores:
            continue
        if sum(1 for v in valores if _numero(v) is not None) >= 0.9 * len(valores):
            numericas.append(j)
        if normalizar_texto(primera[j]) not in {normalizar_texto(v) for v in valores}:
            nuevas += 1
    if len(numericas) < 3:
        return False
    texto_en_numericas = sum(1 for j in numericas if _numero(primera[j]) is None)
    return texto_en_numericas >= 0.8 * len(numericas) and nuevas >= 0.8 * len(con_texto)


# ── Filas corridas ─────────────────────────────────────────────────────────────


@dataclass
class _Perfil:
    """Lo que suele traer una columna: números en un rango o un conjunto de categorías."""

    tipo: str  # numero | categoria
    lo: float = 0.0
    hi: float = 0.0
    enteros: bool = False
    categorias: frozenset[str] = frozenset()

    def encaja(self, valor: str) -> bool | None:
        """True/False si el valor corresponde a la columna; None si está vacío (no cuenta)."""
        if not valor.strip():
            return None
        if self.tipo == "numero":
            x = _numero(valor)
            if x is None or (self.enteros and not float(x).is_integer()):
                return False
            margen = 0.1 * (self.hi - self.lo)
            return self.lo - margen <= x <= self.hi + margen
        return normalizar_texto(valor) in self.categorias


def _perfil(valores: list[str]) -> _Perfil | None:
    presentes = [v.strip() for v in valores if v.strip()]
    if len(presentes) < _MIN_VALORES_PERFIL:
        return None
    numeros = sorted(x for x in (_numero(v) for v in presentes) if x is not None)
    if len(numeros) >= 0.9 * len(presentes):
        # Sin el 1 % de cada extremo: un atípico no debe ensanchar lo que «encaja».
        k = len(numeros) // 100
        centrales = numeros[k: len(numeros) - k] or numeros
        enteros = sum(1 for x in numeros if float(x).is_integer()) >= 0.98 * len(numeros)
        return _Perfil("numero", centrales[0], centrales[-1], enteros)
    conteo = Counter(normalizar_texto(v) for v in presentes)
    frecuentes = frozenset(k for k, c in conteo.items() if c >= 2)
    if len(conteo) <= _MAX_CATEGORIAS and sum(conteo[k] for k in frecuentes) >= 0.9 * len(presentes):
        return _Perfil("categoria", categorias=frecuentes)
    return None  # identificadores y texto libre: no sirven para saber si un valor está en su lugar


def _fallas(celdas: list[str], perfiles: list[_Perfil | None]) -> tuple[int, int]:
    """(valores que no encajan en su columna, valores comparables)."""
    fallas = comparables = 0
    for valor, perfil in zip(celdas, perfiles):
        if perfil is None:
            continue
        encaja = perfil.encaja(valor)
        if encaja is None:
            continue
        comparables += 1
        fallas += not encaja
    return fallas, comparables


@dataclass
class FilaCorrida:
    """Una fila que, movida desde una columna, encaja con las demás."""

    fila: int  # índice en las filas de datos (0 = primera fila después del encabezado)
    tipo: str  # falta | sobra
    columna: int  # columna donde falta (o sobra) la celda
    celdas: list[str]  # la fila tal como venía
    reparada: list[str]  # la fila con la celda vacía insertada (o la sobrante quitada), al ancho del encabezado
    fallas_antes: int
    fallas_despues: int


@dataclass
class RevisionFilas:
    repetidas: list[int] = field(default_factory=list)  # filas iguales al encabezado
    resumen: list[int] = field(default_factory=list)  # filas de totales o promedios
    segunda_encabezado: bool = False  # la fila 0 es el texto de las preguntas
    corridas: list[FilaCorrida] = field(default_factory=list)
    largas: list[tuple[int, list[str]]] = field(default_factory=list)  # más celdas que el encabezado, sin reparación
    cortas: list[int] = field(default_factory=list)  # menos celdas que el encabezado (se completan con vacías)


def _mejor_desplazamiento(celdas: list[str], n: int, perfiles: list[_Perfil | None], tipo: str, d: int) -> tuple[int, list[str], int] | None:
    """(columna, fila reparada, fallas) del mejor punto donde insertar (falta) o quitar (sobra) `d` celdas."""
    mejor: tuple[int, list[str], int] | None = None
    for k in range(1, n):
        if tipo == "falta":
            reparada = (celdas[:k] + [""] * d + celdas[k:])[:n]
        else:
            reparada = (celdas[:k] + celdas[k + d:])[:n]
        reparada += [""] * (n - len(reparada))
        fallas, _ = _fallas(reparada, perfiles)
        if mejor is None or fallas < mejor[2]:
            mejor = (k, reparada, fallas)
    return mejor


def revisar(encabezados: list[str], filas: list[list[str]], irregulares: list[tuple[int, list[str]]] | None = None,
            buscar_resumen: bool = True, buscar_segunda: bool = True) -> RevisionFilas:
    """Revisa la estructura de las filas (sin cambiarlas)."""
    n = len(encabezados)
    revision = RevisionFilas()
    revision.repetidas = [i for i, f in enumerate(filas) if es_encabezado(f, encabezados)]
    if buscar_resumen:
        revision.resumen = [i for i, f in enumerate(filas) if i not in revision.repetidas and es_resumen(f)]
    apartadas = set(revision.repetidas) | set(revision.resumen)
    datos = [(i, f) for i, f in enumerate(filas) if i not in apartadas]
    if buscar_segunda and datos and datos[0][0] == 0:
        revision.segunda_encabezado = segunda_fila_encabezado(encabezados, [f for _, f in datos])
        if revision.segunda_encabezado:
            apartadas.add(0)
            datos = datos[1:]

    originales = dict(irregulares or [])
    perfiles = [_perfil([f[j] for _, f in datos if j < len(f)]) for j in range(n)]
    for i, f in datos:
        celdas = originales.get(i, f)
        if len(celdas) > n:
            tipo, d = "sobra", len(celdas) - n
        elif len(celdas) < n:
            tipo, d = "falta", n - len(celdas)
        elif not celdas[-1].strip():
            tipo, d = "falta", 1  # la fila trae todas las celdas, pero la última vacía: puede faltar una antes
        else:
            continue
        fallas, comparables = _fallas(f, perfiles)
        mejor = _mejor_desplazamiento(celdas, n, perfiles, tipo, d) if fallas >= 2 and comparables >= 4 else None
        if mejor and mejor[2] <= fallas // 4 and fallas - mejor[2] >= 2:
            revision.corridas.append(FilaCorrida(i, tipo, mejor[0], list(celdas), mejor[1], fallas, mejor[2]))
        elif len(celdas) > n:
            revision.largas.append((i, list(celdas)))
        elif len(celdas) < n:
            revision.cortas.append(i)
    return revision
