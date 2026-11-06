"""Compara los reportes de regresión «antes» (solo reglas) y «después» (rediseño en cuatro etapas).

Uso (desde la raíz, después de correr evaluar_regresion.py en los dos modos):
    .venv\\Scripts\\python.exe tools\\rag\\regresion\\comparar.py
Escribe evidencias/rag_rediseno_2026-10-28/regresion_comparacion.md.
"""
from __future__ import annotations

import json
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[3] / "evidencias" / "rag_rediseno_2026-10-28"


def cargar(modo: str) -> dict:
    return json.loads((CARPETA / f"regresion_{modo}.json").read_text(encoding="utf-8"))


def bien(f: dict) -> bool:
    return all(f["respuesta_ok"].values()) and all(f["plan_ok"].values())


def main() -> None:
    antes, despues = cargar("antes"), cargar("despues")
    ra, rd = antes["resumen"], despues["resumen"]
    m_a, m_d = ra.get("metricas_media") or {}, rd.get("metricas_media") or {}
    filas = [
        ("Respuesta correcta", f"{ra['respuesta_correcta_pct']} %", f"{rd['respuesta_correcta_pct']} %"),
        ("Cifras correctas", f"{ra['cifras_correctas_pct']} %", f"{rd['cifras_correctas_pct']} %"),
        ("Decisión de dominio correcta", f"{ra['decision_correcta_pct']} %", f"{rd['decision_correcta_pct']} %"),
        ("Plan completo correcto", "— (sin plan)", f"{rd['plan_completo_pct']} %"),
        ("Tiempo por pregunta (mediana)", f"{ra['segundos_mediana']} s", f"{rd['segundos_mediana']} s"),
        ("Tiempo por pregunta (máximo)", f"{ra['segundos_max']} s", f"{rd['segundos_max']} s"),
    ]
    for clave, nombre in (("fidelidad", "Fidelidad (RAGAS)"), ("relevancia", "Relevancia (RAGAS)"),
                          ("precisionContexto", "Precisión del contexto (RAGAS)")):
        if clave in m_a or clave in m_d:
            filas.append((nombre, str(m_a.get(clave, "—")), str(m_d.get(clave, "—"))))
    lineas = ["# Regresión del chat: antes y después del rediseño", "",
              f"Antes: {antes['fecha']} (solo reglas). Después: {despues['fecha']} (interpretación → ejecución → "
              "redacción → verificación). Mismos 28 casos, mismos instrumentos, sin caché.", "",
              "| Medida | Antes | Después |", "|---|---|---|", *[f"| {a} | {b} | {c} |" for a, b, c in filas], "",
              f"Plan por campo (después): {rd['plan_por_campo_pct']}", "",
              f"Mediana por etapa, después (ms): {rd['ms_por_etapa_mediana']}", "",
              "| Caso | Categoría | Antes | Después |", "|---|---|---|---|"]
    por_id = {f["id"]: f for f in antes["resultados"]}
    for f in despues["resultados"]:
        a = por_id.get(f["id"])
        lineas.append(f"| {f['id']} | {f['categoria']} | {'sí' if a and bien(a) else 'no'} | {'sí' if bien(f) else 'no'} |")
    lineas += ["", f"Fallas antes: {', '.join(ra['fallas']) or 'ninguna'}.", f"Fallas después: {', '.join(rd['fallas']) or 'ninguna'}."]
    (CARPETA / "regresion_comparacion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
