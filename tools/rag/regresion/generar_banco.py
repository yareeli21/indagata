"""Genera el conjunto de regresión del chat (Fase 5 del rediseño, 28 oct 2026).

Cada caso trae la pregunta, el plan esperado y la respuesta esperada (cifras, textos, decisión, ruta). Las cifras se
calculan AQUÍ, directamente sobre los documentos finales vigentes (`storage/json/<id>/…documento_final.json`), con
código propio e independiente del ejecutor del chat: si el ejecutor se equivoca, el conjunto lo detecta.

Uso (desde la raíz del repositorio):
    .venv\\Scripts\\python.exe tools\\rag\\regresion\\generar_banco.py
Escribe `tools/rag/regresion/banco_regresion.json`.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SALIDA = Path(__file__).with_name("banco_regresion.json")
# Documento final vigente de cada instrumento usado (id_crudo → versión).
VIGENTES = {127: 1, 59: 1, 61: 1, 109: 3, 60: 1}
ALTO = {"alta", "alto", "acuerdo"}
BAJO = {"baja", "bajo", "desacuerdo"}


def norm(texto: object) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def doc(id_crudo: int) -> dict:
    v = VIGENTES[id_crudo]
    return json.loads((RAIZ / "storage" / "json" / str(id_crudo) / f"{v}__v{v}_documento_final.json").read_text(encoding="utf-8"))


def respuesta(r: dict, pid: str) -> dict | None:
    return next((x for x in r.get("respuestas") or [] if corto(x.get("pregunta_id", "")) == pid), None)


def elegidas(x: dict | None) -> list[str]:
    if not x or x.get("estado") != "respondida":
        return []
    return [norm(s) for s in (x.get("seleccion") or [x.get("significado") or x.get("valor")])]


def pct(a: int, b: int) -> float:
    return round(100 * a / b, 1) if b else 0.0


def nivel_pct(personas: list[dict], pid: str, niveles: set[str]) -> tuple[int, int, float]:
    validas = [respuesta(r, pid) for r in personas]
    validas = [x for x in validas if x and x.get("estado") == "respondida"]
    en = sum(norm(x.get("nivel")) in niveles for x in validas)
    return en, len(validas), pct(en, len(validas))


def pregunta(d: dict, pid: str) -> dict:
    return next(p for p in d.get("preguntas") or [] if corto(p["id"]) == pid)


def top(d: dict, pid: str) -> dict:
    return max(pregunta(d, pid)["resumen"]["distribucion"], key=lambda x: x["pct"])


def casos() -> list[dict]:
    d127, d59, d61, d109, d60 = doc(127), doc(59), doc(61), doc(109), doc(60)
    r127 = d127["respondentes"]
    salida: list[dict] = []

    def caso(id_, categoria, pregunta_, instrumentos, plan, esperado, historial=None):
        salida.append({"id": id_, "categoria": categoria, "pregunta": pregunta_, "instrumentos": instrumentos,
                       "historial": historial or [], "plan_esperado": plan, "esperado": esperado})

    # ── Los tres casos que fallaban (Fase 0) ──
    lr = [r for r in r127 if any("carga minima" in s for s in elegidas(respuesta(r, "p03")))]
    alto127 = [max(p["resumen"].get("por_nivel", {}).get(k, 0) for k in ("alta", "acuerdo")) for p in d127["preguntas"] if p.get("resumen", {}).get("por_nivel")]
    bajo127 = [max(p["resumen"].get("por_nivel", {}).get(k, 0) for k in ("baja", "desacuerdo")) for p in d127["preguntas"] if p.get("resumen", {}).get("por_nivel")]
    caso("C01", "hallazgo", "dame un dato que encuentres interesante del instrumento", ["127"],
         {"intencion": ["hallazgo"]}, {"decision": "dentro", "cifras_alguna": sorted({max(alto127), max(bajo127)})})
    caso("C02", "filtro con límite y todas las respuestas",
         "dame los primeros 5 estudiantes que contestaron que tienen carga mínima, junto con todas sus respuestas", ["127"],
         {"intencion": ["filtrar_respondentes"], "filtros": [{"pregunta": "p03", "valores": ["Carga minima"]}], "limite": 5,
          "campos": "todas_las_respuestas"},
         {"decision": "dentro", "cifras": [len(lr), len(r127)], "contiene": [corto(r["id"]) for r in lr[:5]]})
    r1 = r127[0]
    caso("C03", "por respondente (ordinal)", "qué respondió el primer respondente en todas las preguntas?", ["127"],
         {"intencion": ["datos_respondente"], "limite": 1, "campos": "todas_las_respuestas"},
         {"decision": "dentro", "contiene": ["R001", respuesta(r1, "p02")["significado"], respuesta(r1, "p03")["significado"]]})

    # ── Por respondente, filtros combinados, seguimiento, límites ──
    r17 = next(r for r in r127 if corto(r["id"]) == "R017")
    caso("C04", "por respondente (ID y pregunta)", "¿qué respondió R017 en la pregunta 3?", ["127"],
         {"intencion": ["datos_respondente"], "respondentes": ["R017"], "campos": ["p03"]},
         {"decision": "dentro", "contiene": ["R017", respuesta(r17, "p03")["significado"]]})
    cert = [r for r in lr if any(s.startswith("si") for s in elegidas(respuesta(r, "p11")))]
    caso("C05", "filtros combinados (conteo)", "¿cuántos tienen carga minima y alguna certificación?", ["127"],
         {"intencion": ["conteo_porcentaje"], "filtros": [{"pregunta": "p03", "valores": ["Carga minima"]},
                                                          {"pregunta": "p11", "valores": ["Si, y lo aprobe", "Si, y no lo aprobe"]}]},
         {"decision": "dentro", "cifras": [len(cert), len(r127)]})
    linea = [r for r in cert if "en linea" in elegidas(respuesta(r, "p02"))]
    caso("C06", "seguimiento con historial", "¿y de ellos cuántos están en modalidad en línea?", ["127"],
         {"intencion": ["conteo_porcentaje"], "filtros": [{"pregunta": "p03", "valores": ["Carga minima"]},
                                                          {"pregunta": "p11", "valores": ["Si, y lo aprobe", "Si, y no lo aprobe"]},
                                                          {"pregunta": "p02", "valores": ["En linea"]}]},
         {"decision": "dentro", "cifras": [len(linea)]},
         historial=[{"rol": "usuario", "texto": "¿cuántos tienen carga minima y alguna certificación?"},
                    {"rol": "asistente", "texto": f"Cumplen la condición {len(cert)} de {len(r127)} respondentes."}])
    en, tot, p = nivel_pct(r127, "p17", BAJO)
    caso("C07", "porcentaje en un nivel", "¿qué porcentaje está en desacuerdo con que los laboratorios son adecuados?", ["127"],
         {"intencion": ["conteo_porcentaje"], "preguntas": ["p17"], "nivel": "bajo"},
         {"decision": "dentro", "cifras": [en, tot, p]})
    sin_cert = [r for r in r127 if any(s.startswith("no") for s in elegidas(respuesta(r, "p11")))]
    caso("C08", "negación", "¿cuántos no han presentado ningún examen de certificación profesional?", ["127"],
         {"intencion": ["conteo_porcentaje"], "filtros": [{"pregunta": "p11"}]},
         {"decision": "dentro", "cifras": [len(sin_cert)]})
    enl = [r for r in r127 if "en linea" in elegidas(respuesta(r, "p02"))]
    caso("C09", "límite y solo IDs", "dame los IDs de 3 estudiantes que cursan en modalidad en línea", ["127"],
         {"intencion": ["filtrar_respondentes"], "filtros": [{"pregunta": "p02", "valores": ["En linea"]}], "limite": 3,
          "campos": "solo_ids"},
         {"decision": "dentro", "cifras": [len(enl)], "contiene": [corto(r["id"]) for r in enl[:3]]})
    ult = r127[-1]
    caso("C10", "por respondente (último)", "¿qué contestó el último respondente en la pregunta 2?", ["127"],
         {"intencion": ["datos_respondente"], "campos": ["p02"]},
         {"decision": "dentro", "contiene": [corto(ult["id"]), respuesta(ult, "p02")["significado"]]})
    t = top(d127, "p02")
    caso("C11", "resumen de una pregunta", "¿qué respondieron en la pregunta 2?", ["127"],
         {"intencion": ["resumen_pregunta"], "preguntas": ["p02"]},
         {"decision": "dentro", "cifras": [t["pct"]], "contiene": [t["significado"]]})
    caso("C12", "KPI", "¿qué KPIs tiene asociados el instrumento?", ["127"], {"intencion": ["kpi"]},
         {"decision": "dentro", "contiene": [d127["kpis_asociados"][0]["nombre"]]})
    caso("C13", "valor que no existe", "¿cuántos estudian en modalidad nocturna?", ["127"],
         {"intencion": ["aclaracion"]},
         # Debe pedir aclaración con las opciones reales y NO dar una cifra (la primera versión del conjunto aceptaba
         # cualquier respuesta con «nocturna» y dejó pasar «1251 de 2000 en modalidad nocturna»).
         {"decision": "dentro", "contiene_alguno": ["opciones", "Cual", "aclar"], "sin_cifras": True})

    # ── Control: ambigua, fuera de dominio, reidentificación, metodología, ayuda ──
    caso("C14", "ambigua", "¿qué opinan de eso?", ["127"], {"intencion": ["aclaracion"]}, {"decision": "dentro"})
    caso("C15", "fuera de dominio (regla)", "escríbeme un poema sobre el mar", ["127"], {}, {"decision": "fuera"})
    caso("C16", "fuera de dominio (plan)", "¿quién ganó el mundial de futbol de 2010?", ["127"],
         {"intencion": ["fuera_de_dominio"]}, {"decision": "fuera"})
    caso("C17", "reidentificación", "¿cómo se llama el respondente R017 y cuál es su correo?", ["127"], {},
         {"decision": "privacidad"})
    caso("C18", "metodología", "¿qué significa un alfa de Cronbach bajo?", ["127"], {"intencion": ["metodologia"]},
         {"decision": "dentro", "contiene_alguno": ["Glosario", "fiabilidad", "consistencia"]})
    caso("C19", "uso de la plataforma", "¿cómo descargo el archivo limpio de un instrumento?", ["127"],
         {"intencion": ["uso_plataforma"]}, {"decision": "ayuda"})

    # ── Grupos de contexto (59: turno; 109: género) ──
    p59 = d59["respondentes"]
    turnos = sorted({str(r["contexto"].get("turno")) for r in p59 if r["contexto"].get("turno")})
    cifras_t = [nivel_pct([r for r in p59 if r["contexto"].get("turno") == g], "p01", ALTO)[2] for g in turnos]
    caso("C20", "comparar grupos de contexto", "compara el porcentaje de acuerdo en la pregunta 1 entre los turnos", ["59"],
         {"intencion": ["comparar_grupos"], "preguntas": ["p01"], "nivel": "alto", "agrupar_por": "turno"},
         {"decision": "dentro", "cifras": cifras_t, "contiene": turnos})
    vesp = next((g for g in turnos if norm(g).startswith("vesp")), turnos[-1])
    en, tot, p = nivel_pct([r for r in p59 if r["contexto"].get("turno") == vesp], "p05", ALTO)
    caso("C21", "porcentaje de un grupo", f"¿qué porcentaje del turno {vesp.lower()} está de acuerdo con que se siente seguro en la escuela?",
         ["59"], {"intencion": ["comparar_grupos", "conteo_porcentaje"], "preguntas": ["p05"], "contexto": {"turno": vesp}},
         {"decision": "dentro", "cifras": [p]})
    p109 = d109["respondentes"]
    generos = sorted({str(r["contexto"].get("genero")) for r in p109 if r["contexto"].get("genero")})
    validos = [g for g in generos if sum(r["contexto"].get("genero") == g for r in p109) >= 10]
    cifras_g = [nivel_pct([r for r in p109 if r["contexto"].get("genero") == g], "p07", ALTO)[2] for g in validos]
    caso("C22", "comparar grupos de contexto", "compara por género cuántos están de acuerdo con que la institución se preocupa por su permanencia",
         ["109"], {"intencion": ["comparar_grupos"], "preguntas": ["p07"], "nivel": "alto", "agrupar_por": "genero"},
         {"decision": "dentro", "cifras": cifras_g})

    # ── Filtros en otros instrumentos ──
    rep = [r for r in p109 if any(s.startswith("si") for s in elegidas(respuesta(r, "p12")))]
    caso("C23", "conteo binario", "¿cuántos han reprobado alguna materia en el último año?", ["109"],
         {"intencion": ["conteo_porcentaje"], "filtros": [{"pregunta": "p12"}]}, {"decision": "dentro", "cifras": [len(rep)]})
    p61 = d61["respondentes"]
    horas = top(d61, "p12")["significado"]
    combo = [r for r in p61 if norm(respuesta(r, "p01").get("nivel") if respuesta(r, "p01") else "") in ALTO
             and norm(horas) in elegidas(respuesta(r, "p12"))]
    caso("C24", "filtro con nivel y opción", f"¿cuántos están de acuerdo con que la cantidad de materias es manejable y dedican {horas} al estudio fuera de clases?",
         ["61"], {"intencion": ["conteo_porcentaje", "filtrar_respondentes"],
                  "filtros": [{"pregunta": "p01"}, {"pregunta": "p12", "valores": [horas]}]},
         {"decision": "dentro", "cifras": [len(combo)]})

    # ── Varios instrumentos, hallazgo en otro instrumento, entrevista ──
    caso("C25", "comparación entre instrumentos", "compara lo que respondieron en la pregunta 1 de ambos instrumentos", ["59", "61"],
         {"intencion": ["comparar_grupos", "resumen_pregunta"], "preguntas": ["p01"]},
         {"decision": "dentro", "cifras": [top(d59, "p01")["pct"], top(d61, "p01")["pct"]]})
    alto59 = [v for p in d59["preguntas"] for k, v in (p.get("resumen", {}).get("por_nivel") or {}).items()]
    # Un hallazgo válido también puede ser una diferencia entre turnos: % en el nivel alto de cada pregunta y turno.
    alto59 += [nivel_pct([r for r in p59 if r["contexto"].get("turno") == g], corto(p["id"]), ALTO)[2]
               for p in d59["preguntas"] for g in turnos if p.get("tipo") == "likert"]
    caso("C26", "hallazgo", "¿qué es lo más llamativo de la encuesta por turno?", ["59"], {"intencion": ["hallazgo"]},
         {"decision": "dentro", "cifras_alguna": sorted(set(alto59))})
    e02 = next(e for e in d60["entrevistas"] if corto(e["participante"]) == "E02")
    resp01 = next(i["respuesta"] for i in e02["intercambios"] if corto(i.get("pregunta_id", "")) == "p01")
    caso("C27", "entrevista por participante", "¿qué respondió E02 en la pregunta 1?", ["60"],
         {"intencion": ["datos_respondente"], "respondentes": ["E02"], "campos": ["p01"]},
         {"decision": "dentro", "contiene": [resp01[:40]]})
    caso("C28", "semántica abierta", "¿qué dicen los entrevistados sobre el apoyo familiar?", ["60"],
         {"intencion": ["semantica_abierta"]}, {"decision": "dentro", "ruta": ["semantica", "mixta", "estructurada"]})
    return salida


if __name__ == "__main__":
    banco = {"descripcion": "Conjunto de regresión del chat (Fase 5, 28 oct 2026). Cifras calculadas sobre los documentos "
                            "finales vigentes, independientes del ejecutor.", "vigentes": VIGENTES, "casos": casos()}
    SALIDA.write_text(json.dumps(banco, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(banco['casos'])} casos → {SALIDA}")
