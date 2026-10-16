"""Construye (SIN guardar) el documento final de un instrumento y muestra un resumen.

Útil para revisar el resultado con datos reales sin crear versiones nuevas.
Uso (dentro del contenedor):  python scripts/vista_documento.py <id_crudo> [--json salida.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))
if not (_RAIZ / "shared").exists():
    sys.path.insert(1, str(_RAIZ.parents[1]))

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.usuario import Usuario  # noqa: E402

from services import documento, fuentes, versiones  # noqa: E402


def main(id_crudo: int, salida: str | None) -> None:
    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter(Usuario.rol == "administrador").first()
        ctx = fuentes.cargar(db, admin, id_crudo)
        fila = versiones.actual(db, id_crudo)
        est = fuentes.estructura_de(ctx)
        reporte = (ctx.limpieza.reporte or {}) if ctx.limpieza else {}
        doc = documento.construir(fila.perfil, est, reporte, fuentes.filas_limpias(ctx), est.avisos)
    finally:
        db.close()
    if salida:
        Path(salida).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    preguntas = doc.get("preguntas") or doc.get("reactivos") or doc.get("preguntas_guia") or []
    print(f"{len(json.dumps(doc)) // 1024} KB · {len(preguntas)} preguntas · sin_datos: {sum(p.get('tipo') == 'sin_datos' for p in preguntas)}")
    for p in preguntas[:8]:
        print(" ", p["id"], p.get("tipo", ""), "|", p["texto"][:70], "|", (p.get("resumen") or {}).get("interpretacion", ""))
    personas = doc.get("respondentes") or doc.get("alumnos") or doc.get("entrevistas") or []
    if personas:
        print(json.dumps(personas[0], ensure_ascii=False, indent=1)[:1500])
    print("avisos:", [a["mensaje"] for a in doc["avisos"]])


if __name__ == "__main__":
    args = sys.argv[1:]
    main(int(args[0]), args[2] if len(args) > 2 and args[1] == "--json" else None)
