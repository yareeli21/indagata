"""Compara tres formas de pedirle al modelo el análisis de lo que se cuenta en una entrevista (7 nov 2026).

Con una sola petición en formato JSON libre, gemma3:4b devolvió `{}` en 7 de 12 respuestas de la entrevista 129.
Antes de cambiar nada se miden, sobre las mismas respuestas:

  a) libre      una petición, `format: "json"` (como está hoy);
  b) esquema    una petición, `format: <esquema JSON>` (Ollama solo deja escribir esos campos; el contenido lo decide
                el modelo);
  c) partes     tres peticiones cortas con esquema: temas y citas clave · valoración y actores · barreras,
                experiencias y propuestas.

Por respuesta y forma: si dio un análisis válido (`nlp_entrevista.validar`), cuántos temas, cuántas citas se
descartaron por no estar en la respuesta, si vino vacío y los segundos. Imprime un JSON con el detalle y el resumen.

Uso (dentro del contenedor, con Ollama libre):
    docker compose exec -T knowledge-service python scripts/comparar_formato_nlp.py 129 > comparacion.json
    docker compose exec -T knowledge-service python scripts/comparar_formato_nlp.py 129 llama3.2:3b > comparacion_llama.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from shared.db.core.config import settings  # noqa: E402
from shared.db.session import SessionLocal  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

from services import storage_client  # noqa: E402
from services.documento import nlp_entrevista  # noqa: E402

# Los esquemas y las instrucciones por parte son los del módulo (la forma «partes» quedó en uso el 7 nov).
CAMPOS, PARTES = nlp_entrevista.CAMPOS, nlp_entrevista.PARTES
_esquema, _prompt_parte = nlp_entrevista.esquema, nlp_entrevista.prompt_parte


MODELO = sys.argv[2] if len(sys.argv) > 2 else settings.OLLAMA_MODEL


def _ollama(prompt: str, formato: Any) -> tuple[dict[str, Any] | None, float]:
    inicio = time.monotonic()
    try:
        r = httpx.post(f"{settings.OLLAMA_HOST.rstrip('/')}/api/generate", timeout=600,
                       json={"model": MODELO, "prompt": prompt, "stream": False, "format": formato,
                             "keep_alive": -1, "options": {"temperature": 0.0, "num_ctx": 4096}})
        r.raise_for_status()
        datos = json.loads(r.json().get("response") or "{}")
    except (httpx.HTTPError, ValueError):
        datos = None
    return (datos if isinstance(datos, dict) else None), round(time.monotonic() - inicio, 1)


def _medir(respuesta: str, salida: dict[str, Any] | None, segundos: float) -> dict[str, Any]:
    v = nlp_entrevista.validar(respuesta, salida) if salida else None
    return {"valido": v is not None, "vacio": not salida, "temas": len((v or {}).get("temas") or []),
            "citas_clave": len((v or {}).get("citas_clave") or []), "descartadas": (v or {}).get("descartadas"),
            "segundos": segundos}


def main() -> None:
    id_crudo = int(sys.argv[1])
    db = SessionLocal()
    fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo, estado="vigente").one()
    doc = storage_client.descargar_json(fila.ruta_documento)
    detalle = []
    for e in doc.get("entrevistas") or []:
        for i in e.get("intercambios") or []:
            pregunta, respuesta = i.get("pregunta") or "", i.get("respuesta") or ""
            fila_r: dict[str, Any] = {"participante": e["participante"], "pregunta_id": i.get("pregunta_id")}
            fila_r["a_libre"] = _medir(respuesta, *_ollama(nlp_entrevista.prompt(pregunta, respuesta), "json"))
            fila_r["b_esquema"] = _medir(respuesta, *_ollama(nlp_entrevista.prompt(pregunta, respuesta), _esquema(tuple(CAMPOS))))
            unido: dict[str, Any] = {}
            segundos = 0.0
            for campos in PARTES:
                salida, s = _ollama(_prompt_parte(pregunta, respuesta, campos), _esquema(campos))
                unido.update(salida or {})
                segundos += s
            fila_r["c_partes"] = _medir(respuesta, unido or None, round(segundos, 1))
            detalle.append(fila_r)
            print(json.dumps(fila_r, ensure_ascii=False), file=sys.stderr, flush=True)
    resumen = {}
    for forma in ("a_libre", "b_esquema", "c_partes"):
        xs = [d[forma] for d in detalle]
        resumen[forma] = {"respuestas": len(xs), "validas": sum(x["valido"] for x in xs), "vacias": sum(x["vacio"] for x in xs),
                          "temas": sum(x["temas"] for x in xs), "descartadas": sum(x["descartadas"] or 0 for x in xs),
                          "segundos_total": round(sum(x["segundos"] for x in xs), 1)}
    print(json.dumps({"id_crudo": id_crudo, "modelo": MODELO, "resumen": resumen, "detalle": detalle},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
