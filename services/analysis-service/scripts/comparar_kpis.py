"""Compara la asociación de KPIs: método actual (un resumen) vs. nuevo (unidades del perfil).

Uso (dentro del contenedor, o local con la BD, Chroma y storage accesibles):
    python scripts/comparar_kpis.py <id_crudo> [<id_crudo> …]

  - Método actual: el resumen que construye ProposalService (metadatos clave del JSON
    técnico + el instrumento en Markdown), embebido como UN vector, contra la colección
    `kpis` (top 5). No se indexa nada en `summary_instrument`: solo se calcula.
  - Método nuevo: perfil general + una unidad por pregunta del perfil semántico de la
    versión actual (`version_conocimiento`), con la fórmula de `perfil/asociacion.py`.

Imprime el top de cada método, la coincidencia, la separación entre el 1.º y el 5.º y la
distribución de similitudes pregunta↔KPI (para calibrar el umbral de evidencia).
Solo lee: no modifica la BD, Chroma ni storage.
"""
from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))
if not (_RAIZ / "shared").exists():
    sys.path.insert(1, str(_RAIZ.parents[1]))

import httpx  # noqa: E402
import numpy as np  # noqa: E402

from app.vectorization.config.constants import TipoInstrumento  # noqa: E402
from app.vectorization.core import embeddings  # noqa: E402
from app.vectorization.core.metadata_extractor import extract_key_metadata  # noqa: E402
from app.vectorization.core.summary_builder import build_summary  # noqa: E402
from app.vectorization.perfil import asociacion, servicio, unidades  # noqa: E402
from shared.auth import cabeceras_servicio  # noqa: E402
from shared.db.core.config import settings  # noqa: E402
from shared.db.session import SessionLocal  # noqa: E402
from shared.models.kpi import KPI  # noqa: E402
from shared.models.raw_data import RawData  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402


def _json_tecnico(id_crudo: int) -> dict | None:
    for tipo in ("analysis", "metadata"):
        r = httpx.get(f"{settings.STORAGE_SERVICE_URL}/almacenamiento/artefacto/{tipo}/{id_crudo}", headers=cabeceras_servicio(), timeout=30)
        if r.status_code == 200:
            return r.json().get("contenido")
    return None


def _markdown(data: dict) -> str:
    """Igual que metadata-service `json_estandarizado.texto_instrumento` (entrada del método actual)."""
    instrumento = data.get("instrument") or {}
    lineas = [f"# {instrumento.get('title') or 'Instrumento'}"]
    if instrumento.get("objective"):
        lineas += ["", str(instrumento["objective"])]
    for seccion in instrumento.get("sections") or []:
        lineas += ["", f"## {seccion.get('name') or 'Reactivos'}"]
        for n, pregunta in enumerate(seccion.get("questions") or [], start=1):
            lineas.append(f"{n}. {pregunta.get('text', '')}")
            for opcion in (pregunta.get("options") or [])[:15]:
                lineas.append(f"   - {opcion}")
    if instrumento.get("contenido"):
        lineas += ["", str(instrumento["contenido"])[:20000]]
    return "\n".join(lineas).strip()


def comparar(db, id_crudo: int, kpis: list[tuple[int, list[float]]], nombres: dict[int, str]) -> None:  # noqa: ANN001
    raw = db.get(RawData, id_crudo)
    fila = (
        db.query(VersionConocimiento)
        .filter(VersionConocimiento.id_crudo == id_crudo, VersionConocimiento.estado != "reemplazado")
        .order_by(VersionConocimiento.version.desc())
        .first()
    )
    print(f"\n{'=' * 100}\nInstrumento {id_crudo} ({raw.tipo_instrumento}) — {(fila.perfil if fila else {}).get('titulo', '?')}")
    K = np.asarray([v for _, v in kpis])

    # ── Método actual ──
    data = _json_tecnico(id_crudo)
    actual: list[tuple[int, float]] = []
    if data:
        resumen = build_summary(extract_key_metadata(data, TipoInstrumento(raw.tipo_instrumento)), _markdown(data))
        modelo = embeddings._get_model()
        n_tokens = len(modelo.tokenizer(resumen)["input_ids"])
        v = np.asarray(embeddings.embed_text(resumen))
        sims = K @ v
        actual = [(kpis[i][0], float(sims[i])) for i in np.argsort(-sims)[:5]]
        print(f"  Resumen del método actual: {len(resumen)} caracteres, {n_tokens} tokens "
              f"(el modelo solo lee los primeros {modelo.max_seq_length}).")
    else:
        print("  (sin JSON técnico: no se puede correr el método actual)")

    # ── Método nuevo ──
    nuevo: list[asociacion.Propuesta] = []
    if fila:
        perfil = fila.perfil
        us = unidades.unidades_pregunta(perfil)
        vecs = embeddings.embed_texts([unidades.texto_general(perfil)] + [u.unidad for u in us])
        pesos = servicio.pesos()
        todos = asociacion.asociar(vecs[0], [(u.pregunta_id, x) for u, x in zip(us, vecs[1:])], kpis,
                                   asociacion.Pesos(pesos.general, pesos.preguntas, pesos.cobertura, pesos.umbral_evidencia, 0.0, 99))
        nuevo = todos[:5]
        if us:
            S = np.asarray(vecs[1:]) @ K.T
            print(f"  Unidades de pregunta: {len(us)}. Similitud pregunta↔KPI: mediana {np.median(S):.3f}, "
                  f"p90 {np.percentile(S, 90):.3f}, p99 {np.percentile(S, 99):.3f}, máx {S.max():.3f}")
            for umbral in (0.35, 0.45, 0.5, 0.55):
                print(f"    pares ≥ {umbral}: {(S >= umbral).mean():.1%}")
        texto_de = {u.pregunta_id: u.texto for u in us}
    else:
        print("  (sin perfil semántico: aprueba los metadatos primero)")

    print(f"\n  {'MÉTODO ACTUAL (un resumen)':<52}{'MÉTODO NUEVO (perfil + preguntas)'}")
    for i in range(5):
        a = f"{nombres[actual[i][0]][:42]:<42} {actual[i][1]:.3f}" if i < len(actual) else ""
        n = (f"{nombres[nuevo[i].kpi_id][:40]:<40} {nuevo[i].score:.3f} (g {nuevo[i].g:.2f} p {nuevo[i].p:.2f} c {nuevo[i].c:.2f})"
             if i < len(nuevo) else "")
        print(f"  {a:<52}{n}")
    if actual and nuevo:
        comunes = {k for k, _ in actual} & {p.kpi_id for p in nuevo}
        print(f"\n  Coincidencia en el top 5: {len(comunes)}/5")
        print(f"  Separación 1.º–5.º: actual {actual[0][1] - actual[-1][1]:.3f} · nuevo {nuevo[0].score - nuevo[-1].score:.3f}")
    for p in nuevo[:3]:
        print(f"\n  Evidencia de «{nombres[p.kpi_id]}»:")
        for e in p.evidencia[:3]:
            print(f"    {e.similitud:.3f}  {texto_de.get(e.pregunta_id, e.pregunta_id)[:90]}")


def main(ids: list[int]) -> None:
    db = SessionLocal()
    try:
        kpis = servicio.vectores_kpis()
        nombres = {k.kpi_id: k.nombre for k in db.query(KPI)}
        for id_crudo in ids:
            comparar(db, id_crudo, kpis, nombres)
    finally:
        db.close()


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]])
