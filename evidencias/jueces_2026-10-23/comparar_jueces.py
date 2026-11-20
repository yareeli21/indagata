"""Compara dos modelos como juez de fidelidad sobre respuestas reales del chat (22 oct) cuya verdad se conoce.

Se ejecuta dentro del contenedor de visualization-service (usa su evaluacion.fidelidad tal cual):
    docker cp comparar_jueces.py indagata_visualization_service:/tmp/
    docker compose exec visualization-service python /tmp/comparar_jueces.py llama3.2:3b qwen2.5:3b
"""
import asyncio
import json
import sys
import time

sys.path[:0] = ["/app"]

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.rag_log import RagLog  # noqa: E402

from services import evaluacion, ollama_client  # noqa: E402

# id → (grupo, qué debería hacer un buen juez)
CASOS = {
    726: ("copia literal", "fidelidad 1.0"),
    727: ("copia literal", "fidelidad 1.0"),
    729: ("copia literal", "fidelidad 1.0"),
    724: ("redacción correcta", "alta (≥ 0.8)"),
    725: ("redacción correcta", "alta (≥ 0.8)"),
    728: ("redacción correcta", "alta (≥ 0.8)"),
    719: ("redacción con error", "marcar «ambos comparten el objetivo/permanencia»"),
    723: ("redacción con error", "marcar «ambos comparten el objetivo de entender cómo…»"),
    722: ("redacción con error", "marcar que en p16 lo más elegido fue «Sí» (fue «No»)"),
}


def juez_con(modelo: str):
    async def juez(prompt: str):
        texto, degradado = await ollama_client.generar_no_stream(prompt, modelo, formato="json", opciones={"temperature": 0})
        if degradado:
            return None
        try:
            datos = json.loads(texto)
        except ValueError:
            return None
        return datos if isinstance(datos, dict) else None
    return juez


async def main(modelos: list[str]) -> None:
    sesion = SessionLocal()
    filas = {f.rag_log_id: f for f in sesion.query(RagLog).filter(RagLog.rag_log_id.in_(list(CASOS))).all()}
    sesion.close()
    resultados = []
    for modelo in modelos:
        juez = juez_con(modelo)
        for cid, (grupo, esperado) in CASOS.items():
            fila = filas[cid]
            contextos = [c.get("texto", "") for c in fila.contexto_usado or [] if c.get("texto")]
            inicio = time.monotonic()
            try:
                valor, detalle = await evaluacion.fidelidad(fila.pregunta, fila.respuesta or "", contextos, juez)
            except ValueError as exc:  # el juez devolvió un JSON que no cuadra (cuenta como fallo del juez)
                valor, detalle = None, {"error": str(exc)}
            resultados.append({"modelo": modelo, "id": cid, "grupo": grupo, "esperado": esperado,
                               "fidelidad": None if valor is None else round(valor, 3),
                               "afirmaciones": detalle.get("afirmaciones"), "no_sustentadas": detalle.get("no_sustentadas", detalle.get("error", [])),
                               "segundos": round(time.monotonic() - inicio, 1)})
            r = resultados[-1]
            print(f"{modelo:12} {cid} {grupo:20} fid={r['fidelidad']} ({r['afirmaciones']} afirm., {r['segundos']} s) "
                  f"no sustentadas: {r['no_sustentadas']}", flush=True)
    with open("/tmp/comparar_jueces.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)


asyncio.run(main(sys.argv[1:] or ["llama3.2:3b", "qwen2.5:3b"]))
