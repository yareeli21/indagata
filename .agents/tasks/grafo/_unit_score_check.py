"""Chequeo unitario del score híbrido del grafo (sin Docker, seam client=None).

Verifica a mano:
  - _jaccard sobre sets de KPIs conocidos.
  - El score combinado = w_sem*sim + w_kpi*jaccard.
  - La etiqueta `razon` sobre scores crudos conocidos.
  - El flujo recomendar() con degradación (client=None, Chroma abajo) → solo-KPI.
  - El flujo recomendar() con sim_semantica inyectada (no degradado) → combinado.

Imprime PASS/FAIL por caso y sale con código !=0 si algo no cuadra.
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "services/analysis-service")

from app.vectorization.core import grafo_recomendador as g  # noqa: E402

errores: list[str] = []


def check(nombre: str, obtenido, esperado, tol: float = 1e-9) -> None:
    ok = (
        math.isclose(obtenido, esperado, abs_tol=tol)
        if isinstance(esperado, float)
        else obtenido == esperado
    )
    estado = "PASS" if ok else "FAIL"
    print(f"[{estado}] {nombre}: obtenido={obtenido!r} esperado={esperado!r}")
    if not ok:
        errores.append(nombre)


# ── 1. Jaccard sobre sets conocidos ──────────────────────────────────────────
# union activo = {10, 20}
check("jaccard C2 {20,30} vs {10,20}", g._jaccard({20, 30}, {10, 20}), 1 / 3)
check("jaccard C3 {10,20} vs {10,20}", g._jaccard({10, 20}, {10, 20}), 1.0)
check("jaccard C4 {40}  vs {10,20}", g._jaccard({40}, {10, 20}), 0.0)
check("jaccard union vacia", g._jaccard(set(), set()), 0.0)

# ── 2. Score combinado a mano (w_sem=0.6, w_kpi=0.4) ──────────────────────────
w_sem, w_kpi = 0.6, 0.4
sim_c2, jac_c2 = 0.8, 1 / 3
score_c2 = w_sem * sim_c2 + w_kpi * jac_c2  # 0.48 + 0.13333 = 0.613333
check("score combinado C2", w_sem * sim_c2 + w_kpi * jac_c2, 0.6133333333333)

# ── 3. Etiqueta razon sobre scores crudos ────────────────────────────────────
# alto_sem & alto_kpi (>=0.5 ambos)
check(
    "razon alta afinidad",
    g._etiquetar_razon(0.8, 0.6, ["K20"]),
    "Alta afinidad (contenido + KPIs)",
)
# kpi >= sem y hay compartidos → KPIs compartidos
check(
    "razon kpis compartidos",
    g._etiquetar_razon(0.2, 0.4, ["K20"]),
    "KPIs compartidos: K20",
)
# sem > kpi, sin alcanzar alto ambos → Contenido similar
check(
    "razon contenido similar",
    g._etiquetar_razon(0.45, 0.1, []),
    "Contenido similar",
)
# sem==kpi, sin compartidos → Contenido similar (rama final)
check(
    "razon fallback contenido",
    g._etiquetar_razon(0.3, 0.3, []),
    "Contenido similar",
)

# ── 4. recomendar() degradado (fake client que falla) → solo-KPI ──────────────
# El seam `client` permite inyectar un cliente alterno. Para forzar la
# degradación de forma determinista (RNF-4) usamos un cliente que lanza al
# tocar Chroma, en vez de depender de que el servidor real esté caído.
class _ClienteQueFalla:
    def get_or_create_collection(self, *a, **k):
        raise RuntimeError("Chroma simulado caído")


# Monkeypatch cargar_acervo con un acervo en memoria.
I = g._Instrumento
acervo = [
    I(id_instrumento=1, id_crudo=101, titulo="Activo", tipo_raw="encuesta",
      id_owner=7, autor_nombre="Ana", kpis={10: "K10", 20: "K20"}),
    I(id_instrumento=2, id_crudo=102, titulo="Cand2", tipo_raw="entrevista",
      id_owner=8, autor_nombre="Ben", kpis={20: "K20", 30: "K30"}),
    I(id_instrumento=3, id_crudo=103, titulo="Cand3", tipo_raw="encuesta",
      id_owner=9, autor_nombre="Cid", kpis={10: "K10", 20: "K20"}),
    I(id_instrumento=4, id_crudo=104, titulo="Cand4", tipo_raw="prueba_estandarizada",
      id_owner=10, autor_nombre="Dan", kpis={40: "K40"}),
]
g.cargar_acervo = lambda db: acervo  # type: ignore[assignment]

recs, params, degradado = g.recomendar(
    db=None, instrumento_ids=[1], w_sem=0.6, w_kpi=0.4,
    top_n=10, min_score=0.0, client=_ClienteQueFalla(),
)
# Chroma falla → degradado True, w_sem_eff=0 → score = 0.4*jaccard.
check("degradado True (fake client que falla)", degradado, True)
check("params w_sem_eff=0 en degradado", params["w_sem"], 0.0)
by_id = {r.id: r for r in recs}
# C3 jaccard=1.0 → score 0.4 ; C2 jaccard=1/3 → 0.1333 ; C4 jaccard=0 → 0.0
check("C3 score=0.4 (0.4*1.0)", by_id["3"].score, 0.4)
check("C3 score_kpi=1.0", by_id["3"].score_kpi, 1.0)
check("C3 score_semantico=0 (degradado)", by_id["3"].score_semantico, 0.0)
check("C2 score=0.1333 (0.4*1/3)", by_id["2"].score, round(0.4 * (1 / 3), 4))
check("C4 score=0.0", by_id["4"].score, 0.0)
# Orden desc por score: C3 primero.
check("orden desc: primero C3", recs[0].id, "3")
# razon C3: kpi 1.0 >= sem 0 y compartidos ["K10","K20"]
check("razon C3 kpis compartidos", by_id["3"].razon, "KPIs compartidos: K10, K20")

# ── 5. recomendar() NO degradado: sim_semantica inyectada → combinado ─────────
def _sim_fake(activos, candidatos, *, total_acervo, client=None):
    # id_instrumento → sim conocida.
    tabla = {2: 0.8, 3: 0.2, 4: 0.9}
    return {c.id_instrumento: tabla.get(c.id_instrumento, 0.0) for c in candidatos}, False

g._sim_semantica_por_candidato = _sim_fake  # type: ignore[assignment]

recs2, params2, degradado2 = g.recomendar(
    db=None, instrumento_ids=[1], w_sem=0.6, w_kpi=0.4,
    top_n=10, min_score=0.0, client=None,
)
check("no degradado", degradado2, False)
check("params w_sem_eff=0.6", params2["w_sem"], 0.6)
by_id2 = {r.id: r for r in recs2}
# C2: 0.6*0.8 + 0.4*(1/3) = 0.48 + 0.13333 = 0.61333 → round 4 = 0.6133
check("C2 combinado=0.6133", by_id2["2"].score, round(0.6 * 0.8 + 0.4 * (1 / 3), 4))
# C3: 0.6*0.2 + 0.4*1.0 = 0.12 + 0.4 = 0.52
check("C3 combinado=0.52", by_id2["3"].score, round(0.6 * 0.2 + 0.4 * 1.0, 4))
# C4: 0.6*0.9 + 0.4*0.0 = 0.54
check("C4 combinado=0.54", by_id2["4"].score, round(0.6 * 0.9 + 0.4 * 0.0, 4))
# C2 razon: sem 0.8>=0.5 y kpi 1/3<0.5 → no alta afinidad; kpi(0.333)<sem(0.8) → sem>kpi → "Contenido similar"
check("C2 razon contenido similar", by_id2["2"].razon, "Contenido similar")
# C3 razon: sem 0.2<0.5, kpi 1.0>=0.5 pero no ambos; kpi>=sem y compartidos → KPIs compartidos
check("C3 razon kpis compartidos", by_id2["3"].razon, "KPIs compartidos: K10, K20")

# ── Resultado ─────────────────────────────────────────────────────────────────
print()
if errores:
    print(f"RESULT: FAIL ({len(errores)} casos): {errores}")
    sys.exit(1)
print("RESULT: PASS (toda la matemática del score cuadra)")
