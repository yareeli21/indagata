"""Exporta a CSV las consultas del chat con su calificación humana y las métricas de cada juez.

Sirve para revisar en Excel lo que cada persona calificó y para juntar los resultados del equipo: cada quien guarda
sus calificaciones en su propia base, así que cada quien exporta su CSV y lo comparte. Lee `rag_log`,
`rag_calificacion`, `rag_metrica_juez` y `usuario`; no cambia nada.

Uso (dentro del contenedor del chat):
    docker compose exec visualization-service python scripts/modelos/exportar.py                  # todo lo calificado
    docker compose exec visualization-service python scripts/modelos/exportar.py --desde 1845 --hasta 1910
    docker compose exec visualization-service python scripts/modelos/exportar.py --todas          # también sin calificar

Escribe `storage/evaluacion_modelos/exportes/<fecha-hora>_calificaciones.csv` (separado por «;», UTF-8 con BOM, para
que Excel lo abra con acentos). Una fila por consulta; las métricas van en columnas por juez (`<juez> fidelidad`…).
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

import comun  # noqa: F401  (ajusta sys.path y silencia el SQL)
from sqlalchemy import text

from shared.db.session import engine

_RAIZ_SALIDA = Path(__file__).resolve().parents[2] / "storage" / "evaluacion_modelos" / "exportes"
_CALIFICACION = {0: "Mal", 1: "Parcial", 2: "Bien"}
_METRICAS = ("fidelidad", "relevancia", "precision_contexto")

_CONSULTAS = text("""
    SELECT l.rag_log_id, l.timestamp, l.modelo_usado, l.instrumentos, l.pregunta, l.respuesta, l.ruta, l.motivo,
           l.decision_dominio, l.latencia_ms, l.plan, l.contexto_usado,
           c.calificacion, c.entendio, c.fundamenta, c.comentario, c.fecha AS fecha_calificacion, u.email
    FROM tt_rag.rag_log l
    LEFT JOIN tt_rag.rag_calificacion c ON c.rag_log_id = l.rag_log_id
    LEFT JOIN tt_rag.usuario u ON u.usuario_id = c.usuario_id
    WHERE l.rag_log_id BETWEEN :desde AND :hasta AND (:todas OR c.rag_log_id IS NOT NULL)
    ORDER BY l.rag_log_id
""")
_JUECES = text("""
    SELECT rag_log_id, modelo_juez, metricas FROM tt_rag.rag_metrica_juez
    WHERE rag_log_id BETWEEN :desde AND :hasta
""")


def _si_no(valor: bool | None) -> str:
    return "" if valor is None else ("sí" if valor else "no")


def _recuperado(contexto: list | None) -> str:
    """Qué partes recuperó el RAG («E01 en p04, r03»), como la línea «Recuperado del RAG» del panel."""
    etiquetas = [c.get("etiqueta") or c.get("seccion") or "fragmento" for c in contexto or []
                 if c.get("tipo") == "fragmento"]
    return ", ".join(dict.fromkeys(etiquetas))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--desde", type=int, default=0, help="primer rag_log_id")
    p.add_argument("--hasta", type=int, default=2**31 - 1, help="último rag_log_id")
    p.add_argument("--todas", action="store_true", help="incluye las consultas sin calificación humana")
    p.add_argument("--salida", default="", help="archivo CSV (por defecto storage/evaluacion_modelos/exportes/)")
    a = p.parse_args()

    parametros = {"desde": a.desde, "hasta": a.hasta, "todas": a.todas}
    with engine.connect() as con:
        filas = con.execute(_CONSULTAS, parametros).mappings().all()
        jueces: dict[int, dict[str, dict]] = {}
        for j in con.execute(_JUECES, parametros).mappings():
            jueces.setdefault(j["rag_log_id"], {})[j["modelo_juez"]] = j["metricas"] or {}
    nombres_jueces = sorted({juez for por_juez in jueces.values() for juez in por_juez})

    destino = Path(a.salida) if a.salida else _RAIZ_SALIDA / f"{datetime.now():%Y-%m-%d_%H%M}_calificaciones.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    columnas = ["consulta", "fecha", "redactor", "instrumentos", "pregunta", "respuesta", "intencion", "ruta",
                "motivo", "recuperado_del_rag", "latencia_s", "calificacion", "calificacion_texto", "entendio",
                "fundamenta", "comentario", "califico", "fecha_calificacion",
                *(f"{juez} {m}" for juez in nombres_jueces for m in _METRICAS)]
    with destino.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(columnas)
        for f in filas:
            plan = (f["plan"] or {}).get("plan") or {}
            metricas = jueces.get(f["rag_log_id"], {})
            escritor.writerow([
                f["rag_log_id"], f"{f['timestamp']:%Y-%m-%d %H:%M}" if f["timestamp"] else "", f["modelo_usado"] or "",
                ", ".join(str(i) for i in f["instrumentos"] or []), f["pregunta"], f["respuesta"] or "",
                plan.get("intencion", ""), f["ruta"] or f["decision_dominio"] or "", f["motivo"] or "",
                _recuperado(f["contexto_usado"]), round((f["latencia_ms"] or 0) / 1000, 1),
                "" if f["calificacion"] is None else f["calificacion"], _CALIFICACION.get(f["calificacion"], ""),
                _si_no(f["entendio"]), _si_no(f["fundamenta"]), f["comentario"] or "", f["email"] or "",
                f"{f['fecha_calificacion']:%Y-%m-%d %H:%M}" if f["fecha_calificacion"] else "",
                *(metricas.get(juez, {}).get(m, "") for juez in nombres_jueces for m in _METRICAS),
            ])
    calificadas = sum(f["calificacion"] is not None for f in filas)
    print(f"{len(filas)} consultas ({calificadas} calificadas, {len(nombres_jueces)} jueces) → {destino}")


if __name__ == "__main__":
    main()
