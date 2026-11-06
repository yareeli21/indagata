"""Evalúa con UN juez las respuestas de una o varias corridas (experimento redactor × juez).

Uso (dentro del contenedor del chat):
    docker compose exec visualization-service python scripts/modelos/juzgar.py --juez qwen2.5:3b \
        --corrida llama3.2:3b=1328-1370 --corrida qwen2.5:3b=1371-1410 ...

Conviene correrlo agrupado por juez (un juez evalúa todas las corridas seguidas): Ollama carga ese modelo una sola
vez. Cada evaluación queda en `rag_metrica_juez` (y la del juez por defecto, también en `rag_log.metricas`). Lo que ese
juez ya evaluó se salta (`--rehacer` lo repite); los rechazos y mensajes fijos no se evalúan. Muestra el avance en la
terminal; los resultados se leen con `reporte.py`.
"""
from __future__ import annotations

import argparse
import asyncio
import time

import comun  # noqa: F401  (ajusta sys.path)
from comun import CASOS, emparejar, leer_casos, parsear_corrida

from shared.db.session import SessionLocal
from shared.models.rag_evaluacion import RagMetricaJuez
from shared.models.rag_log import RagLog

from services import evaluacion

_TERMINADAS = (evaluacion.LISTO, evaluacion.CALCULADA)


def _ya_evaluada(sesion, fila: RagLog, juez: str) -> bool:
    previa = sesion.query(RagMetricaJuez).filter_by(rag_log_id=fila.rag_log_id, modelo_juez=juez).one_or_none()
    if previa is not None and (previa.metricas or {}).get("estado") in _TERMINADAS:
        return True
    metricas = fila.metricas or {}
    if fila.modelo_juez == juez and metricas.get("estado") in _TERMINADAS:
        # Evaluada antes de que existiera rag_metrica_juez (botón del panel): se copia a la tabla.
        evaluacion._guardar_por_juez(sesion, fila.rag_log_id, juez, metricas)
        sesion.commit()
        return True
    return False


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--juez", required=True, help="modelo de Ollama que juzga, p. ej. qwen2.5:3b")
    args.add_argument("--corrida", action="append", required=True, help="modelo=INICIO-FIN (rag_log_id)")
    args.add_argument("--casos", default="casos.json", help="archivo de casos junto a este script (p. ej. casos_pru03.json)")
    args.add_argument("--rehacer", action="store_true", help="vuelve a evaluar lo que ese juez ya evaluó")
    a = args.parse_args()

    casos = leer_casos(CASOS.with_name(a.casos))
    sesion = SessionLocal()
    pendientes: list[tuple[str, str, int]] = []
    try:
        for texto in a.corrida:
            corrida = parsear_corrida(texto)
            faltan = emparejar(sesion, corrida, casos)
            print(f"{corrida.nombre}: {len(corrida.filas)} turnos encontrados" + (f", faltan {len(faltan)}" if faltan else ""))
            for f in faltan:
                print(f"   falta {f}")
            for (caso, turno), fila in sorted(corrida.filas.items()):
                if (fila.metricas or {}).get("estado") == evaluacion.OMITIDA or not fila.metricas:
                    continue
                if not a.rehacer and _ya_evaluada(sesion, fila, a.juez):
                    continue
                pendientes.append((corrida.modelo, f"{caso}.{turno}", fila.rag_log_id))
    finally:
        sesion.close()

    print(f"\nJuez {a.juez}: {len(pendientes)} respuestas por evaluar.")
    inicio_total = time.perf_counter()
    for n, (redactor, turno, rid) in enumerate(pendientes, 1):
        inicio = time.perf_counter()
        evaluacion._cerrojo = None  # el candado del servicio se crea en el bucle de cada asyncio.run
        asyncio.run(evaluacion._evaluar_consulta(rid, SessionLocal, a.juez))
        s = SessionLocal()
        try:
            m = (s.query(RagMetricaJuez).filter_by(rag_log_id=rid, modelo_juez=a.juez).one().metricas or {})
        finally:
            s.close()
        valores = " / ".join("—" if m.get(k) is None else f"{m[k]:.2f}" for k in ("fidelidad", "relevancia", "precision_contexto"))
        print(f"  [{n}/{len(pendientes)}] {redactor} {turno} (consulta {rid}): {m.get('estado')} "
              f"fid/rel/prec {valores} · {time.perf_counter() - inicio:.0f} s", flush=True)
    print(f"\nListo en {(time.perf_counter() - inicio_total) / 60:.1f} min.")


if __name__ == "__main__":
    main()
