"""Re-seed del catálogo de KPIs desde el CSV (diseño §1.3).

Reemplaza por completo `tt_rag.kpi` con las filas de
`infrastructure/postgres/seed/kpis_ampliados.csv` (fuente única de verdad):
en una sola transacción hace `TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE` y
re-inserta las filas en el orden del CSV, de modo que los `kpi_id` quedan
contiguos 1..N. El conteo NO se hardcodea: se recuenta al ejecutar.

El `TRUNCATE ... CASCADE` es destructivo y AUTORIZADO (reemplazo completo del
catálogo): vacía también `kpi_variable`, `kpi_inferido`,
`valor_variable_inferido` y `kpi_inferido_chunk`. Las constraints FK NO se
eliminan; solo se vacían las filas hijas.

Ruta del CSV: variable de entorno `KPIS_CSV_PATH` si está definida; si no,
`<raíz del repo>/infrastructure/postgres/seed/kpis_ampliados.csv`.

Códigos de salida:
  0  éxito (imprime n_insertados)
  2  no se pudo abrir el CSV (OSError)
  3  cabecera/columna inválida o campo obligatorio vacío
  4  error de base de datos (SQLAlchemyError); se hace rollback

NOTA: `infrastructure/postgres/init/*.sql` solo corre al crear un volumen de
Postgres vacío. En una BD ya levantada la nueva forma de la tabla se aplica
recreando el volumen (`docker compose down -v && docker compose up -d`); este
script re-siembra los datos y es re-ejecutable. Tras sembrar hay que ejecutar
el reindex: `POST /vectorizacion/kpis/reindex`.

Ejecutar desde la carpeta del servicio:
    python scripts/seed_kpis.py
"""
from __future__ import annotations

import csv
import logging
import os
import sys
from pathlib import Path

# ── Resolver import de `shared` también en ejecución local ────────────────────
# scripts/seed_kpis.py -> parents[3] = raíz del repo (donde vive `shared/`).
if not (Path(__file__).resolve().parents[1] / "shared" / "__init__.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.kpi import KPI  # noqa: E402

logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_kpis")

# Cabecera esperada del CSV, en orden exacto (diseño §Confirmación del CSV).
_COLUMNAS_CSV: tuple[str, ...] = (
    "KPI",
    "Polaridad_Rendimiento",
    "Tipo_Objetivo_Estrategico",
    "Formula_Metrica_Calculo",
    "Descripcion_Ampliada_Educativa",
    "Comportamiento_Direccional_y_Causalidad",
    "Razon_Estrategica_y_Decisiones",
    "Texto_Contexto_RAG_Vectorial",
)


class ErrorValidacionCSV(Exception):
    """Cabecera inválida o campo obligatorio vacío en el CSV."""


def ruta_csv_por_defecto() -> Path:
    """`KPIS_CSV_PATH` si está definida; si no, la ruta por defecto en el repo."""
    env = os.environ.get("KPIS_CSV_PATH")
    if env:
        return Path(env)
    return (
        Path(__file__).resolve().parents[3]
        / "infrastructure"
        / "postgres"
        / "seed"
        / "kpis_ampliados.csv"
    )


def leer_kpis_csv(path: str | os.PathLike[str]) -> list[dict]:
    """Lee y valida el CSV de KPIs; devuelve las filas como `list[dict]`.

    Validaciones (diseño §1.3): la cabecera trae exactamente las 8 columnas
    esperadas y en el orden esperado; ninguna fila con `KPI` vacío; ninguna
    fila con `Texto_Contexto_RAG_Vectorial` vacío. El conteo se recalcula.

    Lanza `OSError` si no se puede abrir el archivo y `ErrorValidacionCSV` si
    la cabecera o alguna fila no cumplen.
    """
    with open(path, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        cabecera = tuple(lector.fieldnames or ())
        if cabecera != _COLUMNAS_CSV:
            raise ErrorValidacionCSV(
                "Cabecera del CSV inválida. "
                f"Esperada: {list(_COLUMNAS_CSV)}. Hallada: {list(cabecera)}."
            )
        filas: list[dict] = []
        # enumerate desde 2: fila 1 = cabecera; la primera de datos es la 2.
        for n_fila, fila in enumerate(lector, start=2):
            if not (fila.get("KPI") or "").strip():
                raise ErrorValidacionCSV(
                    f"Fila {n_fila}: la columna 'KPI' no puede estar vacía."
                )
            if not (fila.get("Texto_Contexto_RAG_Vectorial") or "").strip():
                raise ErrorValidacionCSV(
                    f"Fila {n_fila}: la columna 'Texto_Contexto_RAG_Vectorial' "
                    "no puede estar vacía."
                )
            filas.append(fila)
    return filas


def _a_kpi(fila: dict) -> KPI:
    """Construye un objeto ORM `KPI` a partir de una fila del CSV."""
    return KPI(
        nombre=fila["KPI"],
        polaridad_rendimiento=fila["Polaridad_Rendimiento"],
        tipo_objetivo_estrategico=fila["Tipo_Objetivo_Estrategico"],
        formula_metrica_calculo=fila["Formula_Metrica_Calculo"],
        descripcion_ampliada_educativa=fila["Descripcion_Ampliada_Educativa"],
        comportamiento_direccional_causalidad=fila[
            "Comportamiento_Direccional_y_Causalidad"
        ],
        razon_estrategica_decisiones=fila["Razon_Estrategica_y_Decisiones"],
        texto_contexto_rag_vectorial=fila["Texto_Contexto_RAG_Vectorial"],
    )


def main() -> int:
    ruta = ruta_csv_por_defecto()

    try:
        filas = leer_kpis_csv(ruta)
    except OSError as exc:
        logger.error("No se pudo abrir el CSV %s: %s", ruta, exc)
        return 2
    except ErrorValidacionCSV as exc:
        logger.error(
            "CSV inválido. Columnas esperadas %s. Detalle: %s",
            list(_COLUMNAS_CSV),
            exc,
        )
        return 3

    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE"))
        db.add_all(_a_kpi(fila) for fila in filas)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error de base de datos al sembrar los KPIs; rollback.")
        return 4
    finally:
        db.close()

    n_insertados = len(filas)
    logger.info("Seed de KPIs completo: %d insertados.", n_insertados)
    logger.info(
        "Recuerda ejecutar el reindex de Chroma: POST /vectorizacion/kpis/reindex"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
