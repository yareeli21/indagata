"""Vuelve a registrar en el manifiesto los artefactos que la BD cita y el manifiesto perdió (26 nov 2026).

Síntoma: `GET /almacenamiento/...` responde «Archivo no encontrado en el almacenamiento» para una clave que la BD
guarda (documento final vigente, CSV limpio, archivo crudo) aunque el archivo SÍ está en disco. Pasa cuando
`<JSON_PATH>/_index/artefactos.json` se sobrescribe (p. ej. un merge de git o una copia desde otra máquina) y pierde
entradas. Consecuencia en el chat: sin documento vigente el ejecutor no calcula nada (conteos, filtros, respondentes)
y toda pregunta cae a la ruta semántica.

Para cada clave citada por la BD (`version_conocimiento.ruta_documento`, `instrumento_procesado.ruta_de_archivo_limpio`,
`raw_data.raw_archivo`) que falte en el manifiesto:
  * si el archivo existe en la ruta de esa clave, calcula su SHA-256;
  * lo compara con el hash de referencia: el de `version_conocimiento.sha256` o el de la misma clave en algún respaldo
    del manifiesto (`_index/*.json`). Si no coincide, NO lo registra y lo reporta;
  * sin hash de referencia lo registra marcado `reparado_sin_referencia`.
Las rutas heredadas (absolutas o sin forma de clave) se resuelven sin manifiesto y se ignoran.

Por defecto solo informa. `--aplicar` respalda el manifiesto (`artefactos.antes-reparacion-<fecha>.json`) y escribe.

Ejecutar dentro del contenedor:
    docker compose exec storage-service python scripts/reparar_manifiesto.py [--aplicar]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SERVICIO))
if not (_SERVICIO / "shared").exists():  # ejecución local: `shared` vive en la raíz del repo
    sys.path.insert(1, str(_SERVICIO.parents[1]))

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.instrumento_procesado import InstrumentoProcesado  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

from services import file_manager  # noqa: E402

_CLAVE = re.compile(r"^(?P<tipo>[a-z]+)/(?P<ins>[^/]+)/(?P<version>\d+)__(?P<nombre>[^/]+)$")


def _referencias() -> list[tuple[str, str | None]]:
    """(clave, sha256 de la BD o None) de todo artefacto que la BD cita."""
    with SessionLocal() as s:
        filas: list[tuple[str, str | None]] = [
            (v.ruta_documento, v.sha256) for v in s.query(VersionConocimiento) if v.ruta_documento]
        filas += [(p.ruta_de_archivo_limpio, None) for p in s.query(InstrumentoProcesado) if p.ruta_de_archivo_limpio]
        filas += [(r.raw_archivo, None) for r in s.query(RawData) if r.raw_archivo]
    return filas


def _hashes_de_respaldos(actual: Path) -> dict[str, dict]:
    """Entradas por clave de los otros JSON de `_index/` (respaldos del manifiesto)."""
    entradas: dict[str, dict] = {}
    for ruta in sorted(actual.parent.glob("*.json")):
        if ruta == actual:
            continue
        try:
            for e in json.loads(ruta.read_text(encoding="utf-8")):
                entradas.setdefault(e.get("key"), e)
        except (json.JSONDecodeError, OSError, AttributeError):
            continue
    return entradas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aplicar", action="store_true", help="escribe el manifiesto (antes lo respalda)")
    a = ap.parse_args()

    ruta_manifiesto = file_manager._ruta_manifiesto()
    entradas = file_manager._leer_manifiesto()
    claves = {e.get("key") for e in entradas}
    respaldos = _hashes_de_respaldos(ruta_manifiesto)

    nuevas, conflictos, ausentes, vistas = [], [], [], set()
    for clave, sha_bd in _referencias():
        m = _CLAVE.match(clave.strip())
        if not m or clave in claves or clave in vistas or m["tipo"] not in file_manager.TIPOS_VALIDOS:
            continue
        vistas.add(clave)
        destino = file_manager._ruta_de_key(m["tipo"], clave)
        if not destino.is_file():
            ausentes.append(clave)
            continue
        contenido = destino.read_bytes()
        sha = file_manager.sha256(contenido)
        previa = respaldos.get(clave) or {}
        referencia = sha_bd or previa.get("sha256")
        if referencia and referencia != sha:
            conflictos.append(clave)
            continue
        entrada = {
            "key": clave,
            "tipo": m["tipo"],
            "instrumentoId": m["ins"],
            "version": int(m["version"]),
            "ruta_absoluta": str(destino),
            "ruta_relativa": file_manager.ruta_relativa(destino),
            "size_bytes": len(contenido),
            "nombre_original": previa.get("nombre_original") or Path(m["nombre"]).stem,
            "creado": previa.get("creado")
            or datetime.fromtimestamp(destino.stat().st_mtime, timezone.utc).isoformat(),
            "sha256": sha,
            "mime_type": previa.get("mime_type") or file_manager.mime_de(m["nombre"]),
        }
        if not referencia:
            entrada["reparado_sin_referencia"] = True
        nuevas.append(entrada)

    por_tipo: dict[str, int] = {}
    for e in nuevas:
        por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
    print(f"Manifiesto: {len(entradas)} entradas. Faltantes recuperables: {len(nuevas)} {por_tipo}")
    print(f"  sin hash de referencia: {sum(1 for e in nuevas if e.get('reparado_sin_referencia'))}")
    print(f"  hash distinto (no se registran): {len(conflictos)} {conflictos[:5]}")
    print(f"  archivo ausente en disco: {len(ausentes)} {ausentes[:5]}")
    if not a.aplicar:
        print("Modo informe. Usa --aplicar para escribir.")
        return
    if not nuevas:
        return
    respaldo = ruta_manifiesto.with_name(f"artefactos.antes-reparacion-{datetime.now():%Y%m%d-%H%M%S}.json")
    with file_manager._lock:
        shutil.copy2(ruta_manifiesto, respaldo)
        actuales = file_manager._leer_manifiesto()  # releído bajo el lock por si cambió
        presentes = {e.get("key") for e in actuales}
        file_manager._escribir_manifiesto(actuales + [e for e in nuevas if e["key"] not in presentes])
    print(f"Escrito. Respaldo: {respaldo.name}")


if __name__ == "__main__":
    main()
