"""Comprobación del Anexo G: el mismo levantamiento guardado como cada plataforma da los mismos resultados.

Sube cada archivo de `corpus/plataformas/` (generado con `generar_plataformas.py`), corre la limpieza, la confirma
con las decisiones sugeridas y compara, por formato: tipo de cada pregunta, media de cada escala, «No sé»
excluidos y α de Cronbach. Con las mismas respuestas, las medias y el α deben coincidir en todas las formas que el
sistema puede leer como escala.

Escribe `evidencias/formatos_plataformas/plataformas.json` y `plataformas.md`.

Uso (con la app levantada):
    python tools/formatos/verificar_plataformas.py [--borrar]   # --borrar quita los instrumentos de prueba al final
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

GATEWAY = "http://localhost:8006"
AQUI = Path(__file__).resolve().parent
CORPUS = AQUI / "corpus" / "plataformas"
SALIDA = AQUI.parents[1] / "evidencias" / "formatos_plataformas"
CASOS = {
    "Google Forms": ("google_forms.csv", None, None),
    "Microsoft Forms": ("microsoft_forms.xlsx", None, None),
    "LimeSurvey (respuestas completas)": ("limesurvey_completas.csv", None, None),
    "LimeSurvey (códigos)": ("limesurvey_codigos.csv", "original.txt", None),
    "Microdatos con diccionario": ("microdatos.csv", None, "microdatos_diccionario.csv"),
}


def pedir(cliente: httpx.Client, metodo: str, url: str, **kw):  # noqa: ANN201
    r = cliente.request(metodo, f"{GATEWAY}{url}", **kw)
    r.raise_for_status()
    return r.json() if r.content else None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--borrar", action="store_true", help="borra los instrumentos de prueba al terminar")
    args = p.parse_args()
    c = httpx.Client(timeout=600)
    tok = pedir(c, "POST", "/auth/login", json={"email": "investigador@indagata.com", "password": "investigador123"})
    c.headers["Authorization"] = f"Bearer {tok['access_token']}"
    resultado = {}
    for nombre, (archivo, original, diccionario) in CASOS.items():
        files = {"archivo": (archivo, (CORPUS / archivo).read_bytes())}
        if original:
            files["archivo_original"] = (original, (CORPUS / original).read_bytes())
        if diccionario:
            files["archivo_diccionario"] = (diccionario, (CORPUS / diccionario).read_bytes())
        carga = pedir(c, "POST", "/instrumentos/upload", data={"tipo_instrumento": "encuesta"}, files=files)
        idc = int(carga.get("id_crudo") or carga.get("idCrudo") or carga["id"])
        e = pedir(c, "POST", f"/limpieza/{idc}/ejecuciones")
        decisiones = {h["id"]: h["sugerida"] or h["opciones"][0] for h in e["hallazgos"]}
        if decisiones:
            pedir(c, "PATCH", f"/limpieza/{idc}/ejecuciones/{e['version']}/decisiones", json={"decisiones": decisiones})
        f = pedir(c, "POST", f"/limpieza/{idc}/ejecuciones/{e['version']}/confirmar")
        est = f["vistaFinal"]["estadistica"]
        resultado[nombre] = {
            "id_crudo": idc,
            "hallazgos": [{"tipo": h["tipo"], "titulo": h["titulo"], "sugerida": h["sugerida"]} for h in e["hallazgos"]],
            "transformaciones": [t["regla"] for t in f["transformaciones"]],
            "columnas": [{"columna": col["etiqueta"], "tipo": col["tipo"], "media": (col.get("numerico") or {}).get("media"),
                          "no_se_excluidos": col.get("n_excluidos")} for col in est["columnas"]],
            "fiabilidad": [{"bloque": b["bloque"], "items": len(b["items"]), "alfa": b["alfa"]} for b in est["fiabilidad"]],
        }
        print(nombre, "→ id_crudo", idc)
        if args.borrar:
            c.delete(f"{GATEWAY}/instrumentos/{idc}")

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "plataformas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    lineas = ["# El mismo levantamiento guardado como cada plataforma", "",
              "| Formato | Tipos de las preguntas | Medias de las escalas | «No sé» excluidos | α de Cronbach |", "|---|---|---|---|---|"]
    for nombre, r in resultado.items():
        tipos = ", ".join(col["tipo"] for col in r["columnas"])
        medias = " · ".join(f"{col['media']:.2f}" for col in r["columnas"] if col["media"] is not None)
        excl = sum(col["no_se_excluidos"] or 0 for col in r["columnas"])
        alfas = "; ".join(f"{b['bloque'][:30]} ({b['items']} ítems): {b['alfa']:.3f}" for b in r["fiabilidad"] if b["alfa"] is not None)
        lineas.append(f"| {nombre} | {tipos} | {medias} | {excl} | {alfas or '—'} |")
    (SALIDA / "plataformas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
