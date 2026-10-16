"""Transformaciones universales de encuestas (no requieren decisión del investigador).

Sobre la tabla ya leída por `shared.parsing` (que ya detecta la codificación y
normaliza saltos de línea y espacios de borde en encabezados y celdas):

  1. Texto en UTF-8 (se registra la codificación de origen).
  2. Espacios internos repetidos en valores → uno solo.
  3. Representaciones de vacío ("", "NA", "N/A", "-", "null", "sin respuesta"…) → nulo.
  4. Filas y columnas completamente vacías → se eliminan.
  5. Cada columna conserva su encabezado original como ETIQUETA y recibe un
     IDENTIFICADOR seguro (minúsculas, sin acentos, [a-z0-9_], único) que es el
     encabezado del CSV limpio.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from shared.parsing import RawTable

from services.configuracion import normalizar_texto

_NO_ALFANUM = re.compile(r"[^a-z0-9]+")
_LARGO_ID = 40


@dataclass
class Columna:
    """Una columna de la encuesta tras las transformaciones universales."""

    id: str
    etiqueta: str
    valores: list[str | None]
    indice_original: int
    extra: dict = field(default_factory=dict)


@dataclass
class TablaPreparada:
    columnas: list[Columna]
    n_filas: int
    transformaciones: list[dict]
    columnas_vacias: list[str]  # etiquetas eliminadas por estar vacías
    filas_vacias: int


def identificador(etiqueta: str, usados: set[str]) -> str:
    """Identificador seguro y único para una columna (p. ej. «¿Qué edad tienes?» → que_edad_tienes)."""
    base = _NO_ALFANUM.sub("_", normalizar_texto(etiqueta)).strip("_")[:_LARGO_ID].strip("_") or "columna"
    if base[0].isdigit():
        base = f"c_{base}"
    candidato, n = base, 2
    while candidato in usados:
        candidato = f"{base}_{n}"
        n += 1
    usados.add(candidato)
    return candidato


def preparar(tabla: RawTable, tokens_vacio: list[str]) -> TablaPreparada:
    """Aplica las transformaciones universales y devuelve las columnas resultantes."""
    vacios = {normalizar_texto(t) for t in tokens_vacio}
    transformaciones: list[dict] = []

    origen = tabla.encoding or ("Excel" if tabla.sheet else "desconocida")
    transformaciones.append(
        {"regla": "codificacion_utf8", "detalle": f"Texto convertido a UTF-8 (origen: {origen}).", "afectados": None}
    )
    transformaciones.append(
        {
            "regla": "encabezados_normalizados",
            "detalle": "Encabezados sin saltos de línea ni espacios repetidos o de borde.",
            "afectados": len(tabla.headers),
        }
    )

    n_cols = len(tabla.headers)
    espacios = 0
    unificados = 0
    columnas_valores: list[list[str | None]] = [[] for _ in range(n_cols)]
    for fila in tabla.rows:
        for j in range(n_cols):
            crudo = fila[j] if j < len(fila) else ""
            limpio = " ".join(crudo.split())
            if limpio != crudo.strip():
                espacios += 1
            if normalizar_texto(limpio) in vacios:
                if limpio:
                    unificados += 1
                columnas_valores[j].append(None)
            else:
                columnas_valores[j].append(limpio)
    if espacios:
        transformaciones.append(
            {"regla": "espacios_en_valores", "detalle": "Espacios repetidos dentro de los valores.", "afectados": espacios}
        )
    if unificados:
        transformaciones.append(
            {
                "regla": "vacios_unificados",
                "detalle": "Respuestas como «NA», «N/A», «-» o «sin respuesta» se tratan como vacías.",
                "afectados": unificados,
            }
        )

    # Filas completamente vacías.
    n_filas = len(tabla.rows)
    conservar = [i for i in range(n_filas) if any(columnas_valores[j][i] is not None for j in range(n_cols))]
    filas_vacias = n_filas - len(conservar)
    if filas_vacias:
        columnas_valores = [[col[i] for i in conservar] for col in columnas_valores]
        transformaciones.append(
            {"regla": "filas_vacias", "detalle": "Filas completamente vacías eliminadas.", "afectados": filas_vacias}
        )

    # Columnas completamente vacías (y encabezados vacíos con nombre de respaldo).
    usados: set[str] = set()
    columnas: list[Columna] = []
    vacias: list[str] = []
    for j, encabezado in enumerate(tabla.headers):
        etiqueta = encabezado.strip() or f"Columna {j + 1}"
        if all(v is None for v in columnas_valores[j]):
            vacias.append(etiqueta)
            continue
        columnas.append(Columna(identificador(etiqueta, usados), etiqueta, columnas_valores[j], j))
    if vacias:
        transformaciones.append(
            {
                "regla": "columnas_vacias",
                "detalle": "Columnas sin ningún dato eliminadas: " + ", ".join(vacias[:5]) + ("…" if len(vacias) > 5 else ""),
                "afectados": len(vacias),
            }
        )
    transformaciones.append(
        {
            "regla": "identificadores_seguros",
            "detalle": "Cada columna conserva su texto original como etiqueta y recibe un identificador seguro.",
            "afectados": len(columnas),
        }
    )
    return TablaPreparada(columnas, len(conservar), transformaciones, vacias, filas_vacias)
