"""Evalúa con el juez Claude Fable 5.2 muchas respuestas a la vez por la Batch API (50 % del precio).

Uso (dentro del contenedor del chat):
    docker compose exec visualization-service python scripts/modelos/juzgar_fable_lote.py --desde 1709 --hasta 1771
    docker compose exec visualization-service python scripts/modelos/juzgar_fable_lote.py --ids 315,322 --rehacer
    docker compose exec visualization-service python scripts/modelos/juzgar_fable_lote.py --continuar <archivo.json>

Para evaluar corridas completas (`correr_casos.py`, `juzgar.py`), no respuestas sueltas: una respuesta suelta se evalúa
con el botón «Evaluar» del panel, que es inmediato pero cuesta el doble. Usa los mismos prompts, esquemas y fórmulas que
el modo inmediato (`services/juez_fable.py`), con el esfuerzo de `RAG_JUEZ_FABLE_ESFUERZO`.

Va en dos rondas, porque los veredictos necesitan la respuesta de referencia:
  1. referencia + preguntas para la relevancia, de todas las respuestas;
  2. veredictos de las que ya tienen referencia.
Cada lote suele terminar en minutos (hasta 24 h como máximo). El avance se guarda en
`storage/evaluacion_modelos/lotes_fable/<fecha>.json`: si el script se corta, `--continuar` retoma los lotes ya
enviados sin volver a pagarlos. Lo ya evaluado por el juez Fable se salta (`--rehacer` lo repite).

Diferencia con el modo inmediato: la Batch API no admite el respaldo del servidor (`fallbacks`), así que si Fable
declina una petición, esa respuesta queda con estado «error» y se puede volver a evaluar desde el panel.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import comun  # noqa: F401  (ajusta sys.path)

from shared.db.core.config import settings
from shared.db.session import SessionLocal
from shared.models.rag_evaluacion import RagMetricaJuez
from shared.models.rag_log import RagLog

from services import juez_fable, vectores

def _carpeta() -> Path:
    """storage/evaluacion_modelos/lotes_fable: /app/storage en el contenedor, <repo>/storage fuera de él."""
    base = Path("/app/storage")
    if not base.is_dir():
        base = Path(__file__).resolve().parents[4] / "storage"
    return base / "evaluacion_modelos" / "lotes_fable"


def _cliente():
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY or None, max_retries=3)


def _guardar_estado(ruta: Path, estado: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    temporal.replace(ruta)


# ── Selección ──────────────────────────────────────────────────────────────────

def _ids(a: argparse.Namespace) -> list[int] | None:
    if a.ids:
        return sorted({int(x) for x in a.ids.split(",") if x.strip()})
    return None


def seleccionar(sesion, a: argparse.Namespace) -> list[RagLog]:
    consulta = sesion.query(RagLog)
    ids = _ids(a)
    if ids:
        consulta = consulta.filter(RagLog.rag_log_id.in_(ids))
    else:
        consulta = consulta.filter(RagLog.rag_log_id >= a.desde)
        if a.hasta:
            consulta = consulta.filter(RagLog.rag_log_id <= a.hasta)
    elegidas = []
    for fila in consulta.order_by(RagLog.rag_log_id).all():
        if not juez_fable.aplica(fila):
            continue  # rechazos, mensajes fijos, copias de la caché
        previa = sesion.query(RagMetricaJuez).filter_by(rag_log_id=fila.rag_log_id,
                                                        modelo_juez=juez_fable.modelo()).one_or_none()
        if previa is not None and (previa.metricas or {}).get("estado") == juez_fable.LISTO and not a.rehacer:
            continue
        elegidas.append(fila)
    return elegidas


# ── Lotes ──────────────────────────────────────────────────────────────────────

def crear_lote(cliente, peticiones: list[tuple[str, str, dict, str]]) -> str:
    """peticiones: (custom_id, prompt, esquema, esfuerzo). Devuelve el id del lote."""
    lote = cliente.messages.batches.create(requests=[
        {"custom_id": cid, "params": juez_fable.parametros(prompt, esquema, esfuerzo)}
        for cid, prompt, esquema, esfuerzo in peticiones
    ])
    return lote.id


def esperar(cliente, lote_id: str, intervalo: int) -> None:
    inicio = time.monotonic()
    while True:
        lote = cliente.messages.batches.retrieve(lote_id)
        c = lote.request_counts
        minutos = (time.monotonic() - inicio) / 60
        print(f"   {lote_id}: {lote.processing_status} — en proceso {c.processing}, listas {c.succeeded}, "
              f"con error {c.errored}, vencidas {c.expired} ({minutos:.1f} min)", flush=True)
        if lote.processing_status == "ended":
            return
        time.sleep(intervalo)


def resultados(cliente, lote_id: str) -> dict[str, tuple[str, Any]]:
    """custom_id → ("ok", (json, meta)) | ("error", motivo)."""
    salida: dict[str, tuple[str, Any]] = {}
    for r in cliente.messages.batches.results(lote_id):
        res = r.result
        if res.type == "succeeded":
            try:
                salida[r.custom_id] = ("ok", juez_fable.leer_mensaje(res.message))
            except Exception as exc:  # noqa: BLE001 — rechazo, sin tokens o JSON inválido
                salida[r.custom_id] = ("error", f"{type(exc).__name__}: {str(exc)[:200]}")
        elif res.type == "errored":
            salida[r.custom_id] = ("error", f"Error en el lote: {getattr(res.error, 'error', res.error)}"[:300])
        else:
            salida[r.custom_id] = ("error", f"Petición {res.type} en el lote (no se cobró).")
    return salida


def _ronda(cliente, estado: dict, ruta: Path, clave: str, peticiones: list[tuple[str, str, dict, str]],
           intervalo: int) -> dict[str, tuple[str, Any]]:
    """Envía (o retoma) una ronda y devuelve sus resultados. El id del lote queda en el estado antes de esperar."""
    if not estado.get(clave):
        if not peticiones:
            return {}
        estado[clave] = crear_lote(cliente, peticiones)
        _guardar_estado(ruta, estado)
        print(f"   lote enviado: {estado[clave]} ({len(peticiones)} peticiones)", flush=True)
    esperar(cliente, estado[clave], intervalo)
    return resultados(cliente, estado[clave])


# ── Principal ──────────────────────────────────────────────────────────────────

def _uso(meta: dict) -> tuple[int, int]:
    u = (meta or {}).get("uso") or {}
    return u.get("entrada", 0), u.get("salida", 0)


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--desde", type=int, help="primer rag_log_id")
    args.add_argument("--hasta", type=int, help="último rag_log_id (opcional)")
    args.add_argument("--ids", help="rag_log_id separados por comas, en lugar de un rango")
    args.add_argument("--rehacer", action="store_true", help="vuelve a evaluar lo que el juez Fable ya evaluó")
    args.add_argument("--continuar", help="archivo de estado de una corrida que se cortó")
    args.add_argument("--intervalo", type=int, default=30, help="segundos entre consultas del estado del lote")
    args.add_argument("--si", action="store_true", help="no pedir confirmación antes de enviar")
    a = args.parse_args()

    if not settings.ANTHROPIC_API_KEY:
        sys.exit("Falta ANTHROPIC_API_KEY en el .env del servicio.")
    cliente = _cliente()
    sesion = SessionLocal()
    try:
        if a.continuar:
            ruta = Path(a.continuar)
            estado = json.loads(ruta.read_text(encoding="utf-8"))
            print(f"Retomando {ruta} ({len(estado['consultas'])} respuestas).")
        else:
            if a.desde is None and not a.ids:
                sys.exit("Indica --desde (y opcionalmente --hasta) o --ids.")
            filas = seleccionar(sesion, a)
            if not filas:
                print("No hay respuestas por evaluar en ese rango.")
                return
            esfuerzo = settings.RAG_JUEZ_FABLE_ESFUERZO
            print(f"{len(filas)} respuestas por evaluar con {juez_fable.modelo()} (esfuerzo {esfuerzo}) por la Batch API.")
            print("Preparando el contexto ampliado de cada una…", flush=True)
            consultas = {}
            for fila in filas:
                usados, ampliado, origen = juez_fable.preparar(fila)
                consultas[str(fila.rag_log_id)] = {"pregunta": fila.pregunta, "respuesta": fila.respuesta or "",
                                                   "usados": usados, "ampliado": ampliado, "origen": origen}
            ruta = _carpeta() / f"{datetime.now():%Y-%m-%d_%H%M%S}.json"
            estado = {"modelo": juez_fable.modelo(), "esfuerzo": esfuerzo, "consultas": consultas}
            if not a.si:
                # ~0.08 USD por respuesta con el 50 % del lote (medido: ~0.16 en el modo inmediato con esfuerzo high).
                respuesta = input(f"Costo aproximado: ~{0.08 * len(consultas):.2f} USD o menos. ¿Enviar? [s/N] ")
                if respuesta.strip().lower() not in ("s", "si", "sí"):
                    print("Cancelado; no se envió nada.")
                    return
            _guardar_estado(ruta, estado)
        esfuerzo = estado["esfuerzo"]
        consultas = estado["consultas"]

        print("Ronda 1: respuestas de referencia y preguntas para la relevancia.", flush=True)
        pet1 = []
        for cid, c in consultas.items():
            pet1.append((f"ref-{cid}", *juez_fable.peticion_referencia(c["pregunta"], c["usados"], c["ampliado"]), esfuerzo))
            pet1.append((f"pre-{cid}", *juez_fable.peticion_preguntas(c["respuesta"]), juez_fable.ESFUERZO_PREGUNTAS))
        r1 = _ronda(cliente, estado, ruta, "lote_1", pet1, a.intervalo)

        print("Ronda 2: veredictos.", flush=True)
        pet2 = []
        for cid, c in consultas.items():
            tipo, valor = r1.get(f"ref-{cid}", ("error", "Sin resultado de la referencia."))
            if tipo == "ok":
                referencia, _ = valor
                pet2.append((f"ver-{cid}", *juez_fable.peticion_veredictos(
                    c["pregunta"], c["respuesta"], c["usados"], juez_fable.afirmaciones_de(referencia)), esfuerzo))
        r2 = _ronda(cliente, estado, ruta, "lote_2", pet2, a.intervalo)

        print("Guardando las métricas…", flush=True)
        lote = f"{estado.get('lote_1')},{estado.get('lote_2')}"
        listas = errores = entrada = salida_t = 0
        for cid, c in consultas.items():
            rid = int(cid)
            ref, ver = r1.get(f"ref-{cid}"), r2.get(f"ver-{cid}")
            for r in (ref, r1.get(f"pre-{cid}"), ver):
                if r and r[0] == "ok":
                    e, s = _uso(r[1][1])
                    entrada, salida_t = entrada + e, salida_t + s
            if not ref or ref[0] != "ok" or not ver or ver[0] != "ok":
                motivo = (ref[1] if ref and ref[0] != "ok" else ver[1] if ver else "Sin resultado de los veredictos.")
                juez_fable.guardar(sesion, rid, {"estado": juez_fable.ERROR, "motivo": motivo,
                                                 "version": juez_fable.VERSION, "lote": lote})
                errores += 1
                continue
            (referencia, meta_ref), (veredictos, meta_ver) = ref[1], ver[1]
            pre = r1.get(f"pre-{cid}")
            if pre and pre[0] == "ok":
                datos, meta_rel = pre[1]
                valor_rel, detalle_rel = juez_fable.relevancia_de(datos, c["pregunta"], vectores.embed_texts)
            else:
                valor_rel, detalle_rel, meta_rel = None, {"error": (pre or ("", "sin resultado"))[1]}, {}
            juez_fable.guardar(sesion, rid, juez_fable.armar(
                referencia, meta_ref, veredictos, meta_ver, valor_rel, detalle_rel, meta_rel,
                c["usados"], c["ampliado"], c["origen"], esfuerzo, lote))
            listas += 1
        sesion.commit()
        estado["terminado"] = datetime.now().isoformat(timespec="seconds")
        _guardar_estado(ruta, estado)
        costo = entrada * 4 / 1e6 + salida_t * 20 / 1e6  # precio del lote de Fable 5.2 (4 / 20 USD por millón); otro modelo cuesta distinto
        print(f"Listo: {listas} evaluadas, {errores} con error. Tokens: {entrada:,} de entrada y {salida_t:,} de salida "
              f"(~{costo:.2f} USD con el precio del lote). Estado: {ruta}")
    finally:
        sesion.close()


if __name__ == "__main__":
    main()
