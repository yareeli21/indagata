"""Agrega el encabezado de la transcripción (reporte de limpieza) al documento VIGENTE de una entrevista (7 nov 2026).

Sin regenerar el conocimiento (eso volvería a correr el análisis con el modelo): se guarda el documento con
`instrumento.encabezado` como otro artefacto y la fila vigente apunta a él. Después hay que reindexar el instrumento
para que la ficha lo incluya.

Uso:  docker compose exec -T knowledge-service python scripts/agregar_encabezado.py 129
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.limpieza_ejecucion import LimpiezaEjecucion  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402

from services import documento, storage_client  # noqa: E402
from services.documento.entrevista import encabezado_de  # noqa: E402

for id_crudo in map(int, sys.argv[1:]):
    db = SessionLocal()
    try:
        fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo, estado="vigente").one()
        doc = storage_client.descargar_json(fila.ruta_documento)
        limpieza = (db.query(LimpiezaEjecucion).filter(LimpiezaEjecucion.id_crudo == id_crudo,
                                                       LimpiezaEjecucion.estado == "confirmada")
                    .order_by(LimpiezaEjecucion.version.desc()).first())
        encabezado = encabezado_de((limpieza.reporte or {}) if limpieza else {})
        if doc.get("entrevistas") is None or not encabezado:
            print(f"{id_crudo}: sin encabezado que agregar")
            continue
        doc["instrumento"]["encabezado"] = encabezado
        documento.validar(doc)
        ref = storage_client.guardar_json(id_crudo, "documento", doc, f"v{fila.version}_documento_final")
        fila.ruta_documento, fila.sha256 = ref["key"], ref.get("sha256")
        db.commit()
        print(f"{id_crudo}: {encabezado} → {ref['key']}")
    finally:
        db.close()
