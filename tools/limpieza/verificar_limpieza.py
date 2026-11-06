"""Mide la limpieza contra errores inyectados con verdad conocida (salida de inyectar_errores.py).

Diseño con grupo de control: se procesan por la API el archivo original sin cambios (control) y el archivo con
errores. Lo que la limpieza detecta en el segundo y NO en el control se compara con lo inyectado, así no cuentan
las anomalías que ya traían los datos (por ejemplo, los encuestados en línea recta del generador).

Por tipo de error: inyectados, detectados nuevos, verdaderos positivos, precisión, recall (exhaustividad) y F1.
Después confirma la limpieza del archivo con errores con las decisiones sugeridas y guarda la comparación antes
y después (lo que quedó corregido).

Uso (con la app levantada):
    python tools/limpieza/verificar_limpieza.py evidencias/limpieza_2026-10-24/enc_11
    python tools/limpieza/verificar_limpieza.py evidencias/limpieza_2026-10-24/pru_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import httpx

GATEWAY = "http://localhost:8006"
_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)
_TIPO_API = {"encuesta": "encuesta", "prueba": "prueba_estandarizada"}


class Api:
    def __init__(self, email: str, password: str) -> None:
        self.c = httpx.Client(timeout=_TIMEOUT)
        token = self.c.post(f"{GATEWAY}/auth/login", json={"email": email, "password": password}).json()["access_token"]
        self.h = {"Authorization": f"Bearer {token}"}

    def __call__(self, metodo: str, ruta: str, **kw: Any) -> Any:
        r = self.c.request(metodo, f"{GATEWAY}{ruta}", headers=self.h, **kw)
        r.raise_for_status()
        return r.json()


def procesar(api: Api, archivo: Path, tipo: str, confirmar: bool) -> dict[str, Any]:
    carga = api("POST", "/instrumentos/upload", data={"tipo_instrumento": _TIPO_API[tipo]},
                files={"archivo": (archivo.name, archivo.read_bytes())})
    id_crudo = carga.get("id_crudo") or carga.get("idCrudo") or carga["id"]
    ejec = api("POST", f"/limpieza/{id_crudo}/ejecuciones")
    salida = {"id_crudo": id_crudo, "hallazgos": ejec["hallazgos"], "metricas": ejec.get("metricasAntes") or {},
              "transformaciones": ejec.get("transformaciones") or []}
    if confirmar:
        decisiones = {h["id"]: h.get("sugerida") or h["opciones"][0] for h in ejec["hallazgos"]}
        api("PATCH", f"/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/decisiones", json={"decisiones": decisiones})
        api("POST", f"/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/confirmar")
        salida["vista_final"] = api("GET", f"/limpieza/{id_crudo}/ejecuciones/{ejec['version']}/vista-final").get("comparacion")
    return salida


def _de_tipo(r: dict[str, Any], tipo: str) -> list[dict[str, Any]]:
    return [h for h in r["hallazgos"] if h["tipo"] == tipo]


def _filas(r: dict[str, Any], tipo: str) -> tuple[set[int], int]:
    """Filas de un hallazgo y su total (la lista de la interfaz se corta en 20)."""
    filas, total = set(), 0
    for h in _de_tipo(r, tipo):
        d = h.get("detalle") or {}
        filas |= set(d.get("filas") or [])
        total += d.get("total", len(d.get("filas") or []))
    return filas, total


def _celdas(r: dict[str, Any]) -> set[tuple[str, int]]:
    return {((h.get("detalle") or {}).get("columna"), f) for h in _de_tipo(r, "fuera_de_rango")
            for f in (h.get("detalle") or {}).get("filas") or []}


def _metricas(inyectados: int, nuevos: int, tp: int, nota: str = "") -> dict[str, Any]:
    precision = round(tp / nuevos, 3) if nuevos else (1.0 if inyectados == 0 else 0.0)
    recall = round(tp / inyectados, 3) if inyectados else None
    f1 = round(2 * precision * recall / (precision + recall), 3) if recall and precision else 0.0
    return {"inyectados": inyectados, "detectados_nuevos": nuevos, "verdaderos_positivos": tp,
            "precision": precision, "recall": recall, "f1": f1, "nota": nota}


def evaluar_encuesta(verdad: dict, control: dict, errores: dict) -> dict[str, Any]:
    v, res = verdad["errores"], {}
    dup_c, _ = _filas(control, "duplicados")
    dup_e, _ = _filas(errores, "duplicados")
    nuevos = dup_e - dup_c
    res["duplicados"] = _metricas(len(v["duplicados"]), len(nuevos), len(nuevos & set(v["duplicados"])))
    nuevas = _celdas(errores) - _celdas(control)
    verdad_celdas = {(c["columna"], c["fila"]) for c in v["fuera_de_rango"]}
    res["fuera_de_rango"] = _metricas(len(verdad_celdas), len(nuevas), len(nuevas & verdad_celdas))
    # «NA» y «N/A» son datos FALTANTES (tokens_vacio de la configuración): lo correcto es dejarlos vacíos, no
    # tratarlos como «No sé». Solo «No sé» y «No aplica» son no-respuestas que debe reportar el hallazgo.
    reales = [c for c in v["no_respuestas"] if c["valor"].strip().lower() not in ("na", "n/a")]
    total_c = sum((h.get("detalle") or {}).get("total", 0) for h in _de_tipo(control, "no_respuestas"))
    total_e = sum((h.get("detalle") or {}).get("total", 0) for h in _de_tipo(errores, "no_respuestas"))
    nuevos = max(0, total_e - total_c)
    res["no_respuestas"] = _metricas(len(reales), nuevos, min(nuevos, len(reales)),
                                     f"Solo «No sé» y «No aplica» ({len(reales)}); los {len(v['no_respuestas']) - len(reales)} "
                                     "«NA/N/A» son datos faltantes y lo correcto es vaciarlos. Por diferencia de totales.")
    col_c = {(h.get("detalle") or {}).get("columna") for h in _de_tipo(control, "columna_incompleta")}
    col_e = {(h.get("detalle") or {}).get("columna") for h in _de_tipo(errores, "columna_incompleta")}
    esperadas = {c["columna"] for c in v["columna_incompleta"]}
    res["columna_incompleta"] = _metricas(len(esperadas), len(col_e - col_c), len((col_e - col_c) & esperadas))
    inc_c, _ = _filas(control, "encuestados_incompletos")
    inc_e, _ = _filas(errores, "encuestados_incompletos")
    nuevos = inc_e - inc_c
    res["encuestados_incompletos"] = _metricas(len(v["encuestados_incompletos"]), len(nuevos),
                                               len(nuevos & set(v["encuestados_incompletos"])))
    lr_c, total_c = _filas(control, "linea_recta")
    lr_e, total_e = _filas(errores, "linea_recta")
    vistos = len(set(v["linea_recta"]) & lr_e)
    res["linea_recta"] = _metricas(len(v["linea_recta"]), max(0, total_e - total_c), min(max(0, total_e - total_c), len(v["linea_recta"])),
                                   f"Por diferencia de totales ({total_e} contra {total_c} del control): la lista de filas se "
                                   f"corta en 20 y el generador ya trae encuestados en línea recta. {vistos} de las filas "
                                   "inyectadas aparecen en la lista visible.")
    aj_c = {(h.get("detalle") or {}).get("columna") for h in _de_tipo(control, "columna_ajena")}
    aj_e = {(h.get("detalle") or {}).get("columna") for h in _de_tipo(errores, "columna_ajena")}
    res["columnas_ajenas"] = _metricas(len(v["columnas_ajenas"]), len(aj_e - aj_c), len((aj_e - aj_c) & set(v["columnas_ajenas"])))
    return res


def evaluar_prueba(verdad: dict, control: dict, errores: dict) -> dict[str, Any]:
    v, res = verdad["errores"], {}
    mot_c, mot_e = control["metricas"].get("motivos") or {}, errores["metricas"].get("motivos") or {}
    for motivo in ("respuesta_multiple", "ilegible", "caracter_invalido"):
        nuevos = mot_e.get(motivo, 0) - mot_c.get(motivo, 0)
        res[motivo] = _metricas(len(v[motivo]), nuevos, min(nuevos, len(v[motivo])),
                                "Por conteo de respuestas nulificadas con ese motivo (errores − control).")
    ids_c = {h["id"].split(":", 1)[1] for h in _de_tipo(control, "id_duplicado")}
    ids_e = {h["id"].split(":", 1)[1] for h in _de_tipo(errores, "id_duplicado")}
    res["id_duplicado"] = _metricas(len(v["id_duplicado"]), len(ids_e - ids_c), len((ids_e - ids_c) & set(v["id_duplicado"])))
    perdidas = control["metricas"].get("n_filas", 0) - errores["metricas"].get("n_filas", 0)
    reportadas = errores["metricas"].get("n_filas_vacias", 0) - control["metricas"].get("n_filas_vacias", 0)
    res["filas_vacias"] = _metricas(v["filas_vacias"], reportadas, min(reportadas, v["filas_vacias"]),
                                    f"Las filas vacías desaparecen del conteo ({perdidas} filas menos que el control), pero "
                                    f"el reporte registra {reportadas} como vacías.")
    return res


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("prefijo", type=Path, help="ruta sin sufijo: <prefijo>_control.csv, _con_errores.csv y _verdad.json")
    p.add_argument("--email", default="admin@indagata.com")
    p.add_argument("--password", default="admin123")
    args = p.parse_args()
    verdad = json.loads(Path(f"{args.prefijo}_verdad.json").read_text(encoding="utf-8"))
    api = Api(args.email, args.password)
    control = procesar(api, Path(f"{args.prefijo}_control.csv"), verdad["tipo"], confirmar=False)
    errores = procesar(api, Path(f"{args.prefijo}_con_errores.csv"), verdad["tipo"], confirmar=True)
    res = (evaluar_encuesta if verdad["tipo"] == "encuesta" else evaluar_prueba)(verdad, control, errores)
    inyectados = sum(m["inyectados"] for m in res.values())
    tp = sum(m["verdaderos_positivos"] for m in res.values())
    nuevos = sum(m["detectados_nuevos"] for m in res.values())
    global_ = {"inyectados": inyectados, "verdaderos_positivos": tp, "detectados_nuevos": nuevos,
               "precision": round(tp / nuevos, 3) if nuevos else None, "recall": round(tp / inyectados, 3) if inyectados else None}
    salida = {"verdad": str(args.prefijo) + "_verdad.json", "id_control": control["id_crudo"], "id_errores": errores["id_crudo"],
              "por_tipo": res, "global": global_, "antes_despues": errores.get("vista_final"),
              "hallazgos_control": [h["id"] for h in control["hallazgos"]], "hallazgos_errores": [h["id"] for h in errores["hallazgos"]]}
    Path(f"{args.prefijo}_resultado.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{args.prefijo.name} (control {control['id_crudo']}, con errores {errores['id_crudo']})")
    print(f"{'error':25} {'iny':>4} {'det':>4} {'VP':>4} {'prec':>6} {'recall':>6} {'F1':>6}")
    for tipo, m in res.items():
        print(f"{tipo:25} {m['inyectados']:>4} {m['detectados_nuevos']:>4} {m['verdaderos_positivos']:>4} "
              f"{m['precision']!s:>6} {m['recall']!s:>6} {m['f1']!s:>6}")
    print(f"{'GLOBAL':25} {inyectados:>4} {nuevos:>4} {tp:>4} {global_['precision']!s:>6} {global_['recall']!s:>6}")


if __name__ == "__main__":
    main()
