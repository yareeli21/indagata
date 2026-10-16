"""Genera los reportes de limpieza de ejemplo con los motores REALES de cleaning-service.

Los motores se ejecutan en un proceso aparte (desde la carpeta de cleaning-service)
porque ambos servicios tienen un paquete `services` propio y chocarían en el mismo
proceso. Las decisiones de la fase asistida son las sugeridas (y la primera opción
en las obligatorias), igual que «Confirmar limpieza» sin cambios.

Uso (desde cualquier carpeta):  python generar_limpiezas.py
Escribe limpieza_<tipo>.json = {"reporte": {...}, "csv": {"headers": [...], "rows": [...]}}
"""
import json
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
LIMPIEZA = D.parents[2] / "cleaning-service"

_SCRIPT = r'''
import json, sys
from pathlib import Path
sys.path[:0] = [".", "../.."]
from services import motores
from services.motores.base import Entrada

d = Path(sys.argv[1])
casos = [
    ("encuesta", "encuesta.csv", None),
    ("entrevista", "entrevista.txt", None),
    # Varias entrevistas en un archivo (RESPONDENTE + preguntas numeradas), como ent_01.
    ("entrevista_bloques", "entrevista_bloques.txt", None),
    ("prueba_estandarizada", "prueba_respuestas.csv", "prueba_clave.csv"),
    # Sintético real sin clave (opción múltiple + escala + Sí/No): la clave se propone.
    ("prueba_sin_clave", "pru_04_respondido.csv", None),
]
for tipo, archivo, clave in casos:
    ext = Path(archivo).suffix
    tipo_real = {"prueba_sin_clave": "prueba_estandarizada", "entrevista_bloques": "entrevista"}.get(tipo, tipo)
    entrada = Entrada(1, tipo_real, archivo, ext, (d / archivo).read_bytes(),
                      (d / clave).read_bytes() if clave else None, Path(clave).suffix if clave else None)
    motor = motores.obtener(tipo_real, ext)
    auto = motor.automatica(entrada)
    # Como «Confirmar limpieza» sin cambios: la sugerida o, en las obligatorias, la primera opción.
    decisiones = {h.id: (h.sugerida if h.sugerida is not None else h.opciones[0]) for h in auto.hallazgos}
    final = motor.aplicar(entrada, auto, decisiones)
    reporte = {
        "esquema": "reporte_limpieza/1", "tipo_instrumento": tipo_real, "version": 1,
        "metricas": {"antes": auto.metricas, "despues": final.metricas},
        "estadistica": {"antes": auto.estadistica, "despues": final.estadistica},
        "especifico": {tipo_real: final.especifico},
        "decisiones": {k: {"valor": v, "origen": "sugerida"} for k, v in decisiones.items()},
    }
    salida = {"reporte": reporte, "csv": {"headers": final.encabezados, "rows": final.filas}}
    (d / f"limpieza_{tipo}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(tipo, len(final.filas), "filas")
'''

subprocess.run([sys.executable, "-c", _SCRIPT, str(D)], cwd=LIMPIEZA, check=True)
