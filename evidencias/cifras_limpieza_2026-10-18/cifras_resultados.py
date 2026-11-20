"""Cifras reales de la limpieza (motores de cleaning-service, en proceso) para el capítulo de Resultados.
Correr desde services/cleaning-service."""
import json
import sys
from pathlib import Path

sys.path[:0] = [".", "../.."]
from services import motores  # noqa: E402
from services.motores.base import Entrada  # noqa: E402
from services.motores.resumen import resumir  # noqa: E402

S = Path("../../storage/instrumentos_sinteticos")
casos = [
    ("encuesta", S / "encuestas/enc_01_respondido.csv"),
    ("encuesta", S / "encuestas/enc_09_respondido.csv"),
    ("encuesta", S / "encuestas/enc_10_turno_respondido.csv"),
    ("prueba_estandarizada", S / "pruebas/pru_01_respondido.csv"),
    ("encuesta", S / "encuestas/enc_04_respondido.csv"),
    ("prueba_estandarizada", S / "pruebas/pru_04_respondido.csv"),
    ("entrevista", S / "entrevistas/ent_01_respondido.txt"),
]
salida = {}
for tipo, ruta in casos:
    ext = ruta.suffix
    entrada = Entrada(1, tipo, ruta.name, ext, ruta.read_bytes(), None, None)
    motor = motores.obtener(tipo, ext)
    auto = motor.automatica(entrada)
    decisiones = {h.id: (h.sugerida if h.sugerida is not None else h.opciones[0]) for h in auto.hallazgos}
    final = motor.aplicar(entrada, auto, decisiones)
    est = final.estadistica or {}
    tipos_h = {}
    for h in auto.hallazgos:
        tipos_h[h.tipo] = tipos_h.get(h.tipo, 0) + 1
    r = {
        "archivo": ruta.name,
        "filas_csv": len(final.filas),
        "columnas_csv": len(final.encabezados),
        "metricas_antes": auto.metricas,
        "metricas_despues": final.metricas,
        "transformaciones": [(t["regla"], t.get("afectados")) for t in (auto.transformaciones or []) + (final.transformaciones or [])],
        "hallazgos": tipos_h,
        "obligatorios": sum(1 for h in auto.hallazgos if h.obligatoria),
        "cifras": final.cifras,
        "resumen": [f["texto"] for f in resumir(tipo, est)],
    }
    if tipo == "encuesta":
        r["fiabilidad"] = [(b.get("bloque"), b.get("alfa"), b.get("interpretacion"), b.get("n_items")) for b in est.get("fiabilidad") or []]
        r["encuestados"] = est.get("encuestados")
        cols = est.get("columnas") or []
        r["n_columnas_est"] = len(cols)
    elif tipo == "prueba_estandarizada":
        r["fiabilidad"] = est.get("fiabilidad")
        r["resumen_reactivos"] = est.get("resumen_reactivos")
        r["puntajes"] = est.get("puntajes")
        esp = final.especifico
        r["clave_origen"] = esp.get("clave_origen")
        tr = esp.get("tipos_reactivo") or {}
        cuenta = {}
        for v in tr.values():
            cuenta[v] = cuenta.get(v, 0) + 1
        r["tipos_reactivo"] = cuenta
    else:
        r.update({k: est.get(k) for k in ("n_participantes", "n_preguntas", "n_respuestas", "palabras_por_respuesta", "palabras_por_rol")})
    salida[ruta.stem] = r
print(json.dumps(salida, ensure_ascii=False, indent=1, default=str))
