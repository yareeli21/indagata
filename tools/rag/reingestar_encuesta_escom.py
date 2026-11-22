"""Reingesta de la encuesta «Indicadores de calidad escolar en la ESCOM» por la API (sin la interfaz).

Usa la lógica de procesar_instrumento.py con tres ajustes pedidos para las pruebas del 20 nov:
  - la columna de comentarios se elimina en la limpieza (todo lo demás, con la opción sugerida);
  - el título es «Encuesta Indicadores de calidad escolar en la ESCOM» (sin «(respuestas)»);
  - se aceptan todos los KPIs sugeridos.

La contraseña se pide en la terminal (no se escribe en el comando ni queda en el historial):
    venv\\Scripts\\python.exe tools\\rag\\reingestar_encuesta_escom.py --email tu_correo
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import procesar_instrumento as pi  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO = RAIZ / "storage" / "Prueba" / "Indicadores de calidad escolar en la ESCOM (respuestas).xlsx"
TITULO = "Encuesta Indicadores de calidad escolar en la ESCOM"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--email", required=True)
    args = p.parse_args()
    api = pi.Api(args.email, getpass.getpass(f"Contraseña de {args.email}: "))

    carga = api.pedir("POST", f"{pi.GATEWAY}/instrumentos/upload", data={"tipo_instrumento": "encuesta"},
                      files={"archivo": (ARCHIVO.name, ARCHIVO.read_bytes())})
    id_crudo = int(carga.get("id_crudo") or carga.get("idCrudo") or carga["id"])
    print(f"1. Archivo: id_crudo={id_crudo}")

    ejec = api.pedir("POST", f"{pi.GATEWAY}/limpieza/{id_crudo}/ejecuciones")
    decisiones: dict[str, str] = {}
    for h in ejec["hallazgos"]:
        columna = str((h.get("detalle") or {}).get("columna") or "")
        comentarios = "coment" in columna.lower() and "eliminar" in h["opciones"]
        decisiones[h["id"]] = "eliminar" if comentarios else (h["sugerida"] or h["opciones"][0])
        print(f"   - {h['tema']}: {h['titulo'][:90]} → {decisiones[h['id']]}")
    if decisiones:
        api.pedir("PATCH", f"{pi.GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/decisiones",
                  json={"decisiones": decisiones})
    api.pedir("POST", f"{pi.GATEWAY}/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/confirmar")
    print(f"2. Limpieza v{ejec['version']} confirmada ({len(decisiones)} decisiones)")

    # Pasos 3–7 como en procesar_instrumento.py, con el título cambiado en la propuesta Dublin Core.
    llenar_original = pi._llenar

    def llenar(propuesta: dict, prefijo: str = "") -> dict[str, str]:
        valores = llenar_original(propuesta, prefijo)
        if prefijo == "dc_":
            valores["dc_title"] = TITULO
        return valores

    pi._llenar = llenar
    pi._desde_metadatos(api, id_crudo, n_kpis=99)
    print(f"Listo: id_crudo={id_crudo}. La vectorización sigue unos minutos en segundo plano.")


if __name__ == "__main__":
    main()
