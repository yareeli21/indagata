"""Genera `casos.json`: los 14 casos de prueba del experimento de modelos, con lo que se espera de cada turno.

Uso (dentro del contenedor del chat, que tiene la base):
    docker compose exec visualization-service python scripts/modelos/generar_casos.py [--instrumento 127]

Los casos son las preguntas de la investigadora (`preguntas prueba.docx`, 28 oct 2026), con sus erratas, en el
orden en que se hicieron; los turnos de un caso van en la misma conversación. Los seguimientos son los que ella
escribió en la corrida con llama3.2:3b (31 oct, consultas 1344–1365), que se repiten tal cual con los demás modelos
aunque se hayan escrito como reacción a las respuestas de llama. Cada turno tiene un tipo:

  dato            se responde con los datos: lleva las cifras correctas, calculadas AQUÍ directo de
                  `respuesta_interpretada`, los metadatos y las decisiones de KPI, sin pasar por el chat.
  inexistente     pregunta por algo que el instrumento no tiene: se espera que lo diga (y, si aplica, las opciones
                  reales) sin dar cifras.
  interpretativo  pide opinar, explicar o fundamentar: no tiene una respuesta única; lleva criterios, y lo califica
                  la persona (más la fidelidad del juez y las cifras con respaldo).
  capacidad       pregunta qué puede hacer el chat: se espera la intención de uso de la plataforma.
  control         caso que ya respondía bien: debe seguir igual.

Las cifras se guardan como alternativas (listas): una respuesta acierta si trae todas las cifras de alguna.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

_SERVICIO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SERVICIO))

from sqlalchemy import func  # noqa: E402

from shared.db.session import SessionLocal  # noqa: E402
from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas  # noqa: E402
from shared.models.respuesta_interpretada import RespuestaInterpretada  # noqa: E402
from shared.models.version_conocimiento import VersionConocimiento  # noqa: E402
from shared.models.kpi import KPI  # noqa: E402

SALIDA = Path(__file__).with_name("casos.json")


def _pct(n: int, total: int) -> float:
    return round(100 * n / total, 1)


def _clave_id(rid: str) -> int:
    return int(re.sub(r"\D", "", rid.rsplit("-", 1)[-1]) or 0)


def cargar(sesion, id_crudo: int) -> dict:
    version = sesion.query(func.max(RespuestaInterpretada.version)).filter_by(id_crudo=id_crudo).scalar()
    filas = sesion.query(RespuestaInterpretada).filter_by(id_crudo=id_crudo, version=version).all()
    por_pregunta: dict[str, list[RespuestaInterpretada]] = defaultdict(list)
    for f in filas:
        por_pregunta[f.pregunta_id.rsplit("-", 1)[-1]].append(f)
    respondentes = sorted({f.respondente_id for f in filas}, key=_clave_id)
    return {"version": version, "por_pregunta": por_pregunta, "respondentes": respondentes, "filas": filas}


def contar(datos: dict, pregunta: str, condicion) -> tuple[int, list[str]]:
    ids = [f.respondente_id for f in datos["por_pregunta"][pregunta]
           if f.estado == "respondida" and f.significado and condicion(f.significado)]
    return len(ids), sorted(ids, key=_clave_id)


def escala(datos: dict, pregunta: str) -> list[int]:
    return [int(m.group(1)) for f in datos["por_pregunta"][pregunta]
            if f.estado == "respondida" and (m := re.match(r"(\d+) en escala", f.significado or ""))]


def calcular(sesion, id_crudo: int) -> dict:
    d = cargar(sesion, id_crudo)
    total = len(d["respondentes"])
    corto = lambda rid: rid.rsplit("-", 1)[-1]  # noqa: E731
    e: dict = {"total": total}

    n, _ = contar(d, "p03", lambda s: "Cargas maxima" in s)
    e["carga_maxima"] = [[n, total, _pct(n, total)]]
    n, ids = contar(d, "p04", lambda s: s == "Mas de la mitad")
    e["doctorado"] = [[n, total, _pct(n, total)]]
    e["doctorado_primero"] = corto(ids[0])
    # «No tienen certificaciones» admite dos lecturas: no han presentado el examen (opciones que empiezan con «No»,
    # como agrupa el sistema) o no lo tienen aprobado (además «Sí, y no lo aprobé»).
    n1, _ = contar(d, "p11", lambda s: s.startswith("No"))
    n2, _ = contar(d, "p11", lambda s: s.startswith("No") or s == "Si, y no lo aprobe")
    e["sin_certificacion"] = [[n1, total, _pct(n1, total)], [n2, total, _pct(n2, total)]]
    e["modalidades"] = sorted({f.significado for f in d["por_pregunta"]["p02"] if f.estado == "respondida" and f.significado})

    vacias = [f for f in d["filas"] if f.estado == "sin_respuesta"]
    n_resp = len({f.respondente_id for f in vacias})
    e["en_blanco"] = [[n_resp], [n_resp, total, _pct(n_resp, total)], [len(vacias)]]

    # Desacuerdo y división en las afirmaciones de acuerdo (escala 1–5): p16, p17 y p18.
    afirmaciones = {}
    for p in ("p16", "p17", "p18"):
        valores = escala(d, p)
        bajos = sum(1 for v in valores if v <= 2)
        afirmaciones[p] = {"validas": len(valores), "bajos": bajos, "pct_bajo": _pct(bajos, len(valores)),
                           "desviacion": round(statistics.pstdev(valores), 2)}
    mas_desacuerdo = max(afirmaciones, key=lambda p: afirmaciones[p]["pct_bajo"])
    mas_dividida = max(afirmaciones, key=lambda p: afirmaciones[p]["desviacion"])
    e["afirmaciones"] = afirmaciones
    a = afirmaciones[mas_desacuerdo]
    e["mas_desacuerdo"] = {"pregunta": mas_desacuerdo, "cifras": [[a["pct_bajo"]], [a["bajos"], a["validas"]]]}
    e["mas_dividida"] = {"pregunta": mas_dividida, "cifras": [[afirmaciones[mas_dividida]["desviacion"]]]}

    valores13 = escala(d, "p13")
    altos = sum(1 for v in valores13 if v >= 4)
    e["p13_alto"] = [[_pct(altos, len(valores13))]]

    meta = sesion.get(MetadatosEnriquecidosEncuestas, id_crudo)
    e["carrera"] = meta.carrera if meta else None
    e["n_preguntas"] = len(d["por_pregunta"])

    vigente = (sesion.query(VersionConocimiento).filter_by(id_crudo=id_crudo)
               .order_by(VersionConocimiento.version.desc()).first())
    aceptados = [x for x in (vigente.decisiones_kpi or []) if x.get("decision") == "aceptado"] if vigente else []
    mejor = max((x["score"] for x in aceptados), default=None)
    nombres = {k.kpi_id: k.nombre for k in sesion.query(KPI).all()}
    e["kpi_mas_relacionado"] = [nombres[x["kpi_id"]] for x in aceptados if x["score"] == mejor]
    e["kpi_puntaje"] = mejor
    e["version_respuestas"] = d["version"]
    return e


def casos(e: dict) -> list[dict]:
    """Los 14 casos. `intenciones`: las de la etapa de interpretación que cuentan como «entendió»."""
    t = e["total"]
    desac, divid = e["mas_desacuerdo"], e["mas_dividida"]
    kpis = " o ".join(f"«{k}»" for k in e["kpi_mas_relacionado"])
    return [
        {"caso": 1, "titulo": "KPI más relacionado", "turnos": [
            {"texto": "qué KPI consideras que está más relacionado con el contenido de la encuesta?", "tipo": "dato",
             "intenciones": ["kpi"], "debe_mencionar_alguno": e["kpi_mas_relacionado"],
             "referencia": f"El KPI más relacionado es {kpis} (puntaje {e['kpi_puntaje']}, el más alto de los aceptados)."},
            {"texto": "Pero me estás regresando una pregunta interesante a tu parecer, y yo quiero el KPI que está más "
                      "relacionado al instrumento, ¿cuál es? fundamentado",
             "tipo": "dato", "intenciones": ["kpi"], "debe_mencionar_alguno": e["kpi_mas_relacionado"],
             "referencia": f"El KPI más relacionado con el instrumento es {kpis}.",
             "criterios": ["Da un KPI, no una pregunta.", "Fundamenta con la justificación o el puntaje de la asociación."]},
            {"texto": "Me sigues dando una pregunta, el instrumento ya tiene KPIs asociados, cuál consideras que es el que "
                      "tiene mayor relevancia con el contenido del instrumento?",
             "tipo": "dato", "intenciones": ["kpi"], "debe_mencionar_alguno": e["kpi_mas_relacionado"],
             "referencia": f"El KPI con mayor relevancia es {kpis} (puntaje {e['kpi_puntaje']})."}]},
        {"caso": 2, "titulo": "Patrones interesantes y su significado", "turnos": [
            {"texto": "qué patrones interesantes encontraste entre los alumnos que respondieron?", "tipo": "interpretativo",
             "intenciones": ["hallazgo"], "criterios": ["Da un patrón con una cifra real del instrumento."]},
            {"texto": "y eso, ¿qué puede significarse?", "tipo": "interpretativo", "intenciones": ["hallazgo", "resumen_pregunta"],
             "criterios": ["Sigue el hilo del patrón anterior.", "Explica qué puede significar, sin inventar datos."]},
            {"texto": "De acuerdo al análisis del instrumento, la relación con todas las preguntas, ¿qué puede significarse "
                      "más a fondo ese patrón interesante que me dices? y ¿por qué?",
             "tipo": "interpretativo", "intenciones": ["hallazgo", "resumen_pregunta"],
             "criterios": ["Profundiza en el patrón anterior relacionándolo con otras preguntas, con cifras reales.",
                           "Fundamenta el porqué sin inventar datos."]}]},
        {"caso": 3, "titulo": "Opinión sobre un dato", "turnos": [
            {"texto": "¿qué opinas de que el 50.4% de respondentes estén dispuesto a volver a estudiar algo más adelante?",
             "tipo": "interpretativo", "intenciones": ["resumen_pregunta", "hallazgo"],
             "debe_mencionar": ["50.4"],
             "criterios": ["Reconoce el dato de p13 (50.4 % en nivel alto).", "Da una opinión controlada basada en los datos."]}]},
        {"caso": 4, "titulo": "Comparaciones", "turnos": [
            {"texto": "compara los primeros 100 respondentes con los siguientes 100, ¿qué observas?", "tipo": "interpretativo",
             "intenciones": ["comparar_grupos"],
             "criterios": ["Compara los dos bloques de respondentes o explica con claridad por qué no puede."],
             "nota": "El plan no puede expresar rangos de respondentes (solo agrupa por variables de contexto)."},
            {"texto": "Haz comparación entre los resultados de los primeros 100 respondentes y los siguientes (101-200), "
                      "porque no estás entendiendo. Y dame un análisis de esos resultados.",
             "tipo": "interpretativo", "intenciones": ["comparar_grupos"],
             "criterios": ["Compara los dos bloques de respondentes con cifras reales o explica con claridad por qué no puede.",
                           "No responde con el mensaje de fuera de dominio."]}]},
        {"caso": 5, "titulo": "Valor inexistente", "turnos": [
            {"texto": "¿cuántos estudian en modalidad nocturna?", "tipo": "inexistente",
             "intenciones": ["aclaracion", "conteo_porcentaje"], "debe_mencionar": e["modalidades"], "sin_cifras": True,
             "referencia": f"No existe la modalidad nocturna; las opciones de p02 son {', '.join(e['modalidades'])}."}]},
        {"caso": 6, "titulo": "Conteo y seguimiento sobre algo que no existe", "turnos": [
            {"texto": "cuántos llevan carga máxima?", "tipo": "dato", "intenciones": ["conteo_porcentaje"],
             "cifras": e["carga_maxima"],
             "referencia": f"Llevan carga máxima {e['carga_maxima'][0][0]} de {t} respondentes ({e['carga_maxima'][0][2]} %)."},
            {"texto": "De ellos que llevan carga máxima, ¿cuántos trabajan?", "tipo": "inexistente", "intenciones": ["aclaracion", "conteo_porcentaje"],
             "sin_cifras": True,
             "referencia": "El instrumento no tiene ninguna pregunta sobre si los estudiantes trabajan."}]},
        {"caso": 7, "titulo": "Sin certificaciones", "turnos": [
            {"texto": "¿cuántos y quiénes son los que no tienen certificaciones?", "tipo": "dato",
             "intenciones": ["filtrar_respondentes", "conteo_porcentaje"], "cifras": e["sin_certificacion"],
             "referencia": (f"Según p11, {e['sin_certificacion'][0][0]} de {t} ({e['sin_certificacion'][0][2]} %) no han "
                            f"presentado un examen de certificación; con quienes no lo aprobaron son "
                            f"{e['sin_certificacion'][1][0]} ({e['sin_certificacion'][1][2]} %)."),
             "nota": "Dos lecturas válidas de «no tienen certificaciones»."}]},
        {"caso": 8, "titulo": "Control: filtro y respondente", "turnos": [
            {"texto": "dime quiénes son los que tienen más de la mitad profesores que tienen doctorado?", "tipo": "control",
             "intenciones": ["filtrar_respondentes"], "cifras": e["doctorado"],
             "referencia": f"Cumplen la condición {e['doctorado'][0][0]} de {t} ({e['doctorado'][0][2]} %)."},
            {"texto": f"y, ¿qué respondió {e['doctorado_primero']} a las demás preguntas?", "tipo": "control",
             "intenciones": ["datos_respondente"], "debe_mencionar": [e["doctorado_primero"]]}]},
        {"caso": 9, "titulo": "Metadato: carrera", "turnos": [
            {"texto": "a qué carrera está aplicada esta encuesta?", "tipo": "dato",
             "intenciones": ["semantica_abierta", "metodologia"], "debe_mencionar": [e["carrera"]],
             "referencia": f"La encuesta está aplicada a la carrera de {e['carrera']}."},
            {"texto": "Del instrumento actual con el que estamos trabajando", "tipo": "dato",
             "intenciones": ["semantica_abierta", "metodologia"], "debe_mencionar": [e["carrera"]],
             "referencia": f"La encuesta está aplicada a la carrera de {e['carrera']}."}]},
        {"caso": 10, "titulo": "Lo más preocupante y por qué", "turnos": [
            {"texto": "qué es lo más preocupante que encuentras en las respuestas?", "tipo": "interpretativo",
             "intenciones": ["hallazgo"],
             "criterios": ["Elige un dato realmente negativo (p. ej., desacuerdo en una afirmación) con su cifra.",
                           "La polaridad es coherente: que casi nunca cambien de profesor (p05) no es preocupante."]},
            {"texto": "¿por qué consideras que es preocupante?, ¿en qué te basas para decir que es preocupante?",
             "tipo": "interpretativo", "intenciones": ["hallazgo", "resumen_pregunta"],
             "criterios": ["Fundamenta con los datos; no repite la pregunta."]},
            {"texto": "te estoy preguntando que por qué consideras que el dato que me dijiste lo crees preocupante, en qué aspecto",
             "tipo": "interpretativo", "intenciones": ["hallazgo", "resumen_pregunta"],
             "criterios": ["Fundamenta el dato anterior; no repite la pregunta."]},
            {"texto": "Tú respóndeme", "tipo": "interpretativo", "intenciones": ["hallazgo", "resumen_pregunta"],
             "criterios": ["Responde el porqué con los datos; no pide aclaración ni responde con un mensaje fijo."]}]},
        {"caso": 11, "titulo": "Desacuerdo y opinión dividida", "turnos": [
            {"texto": "¿en qué pregunta hay más desacuerdo?", "tipo": "dato", "intenciones": ["hallazgo", "resumen_pregunta"],
             "debe_mencionar": [desac["pregunta"]], "cifras": desac["cifras"],
             "referencia": (f"La pregunta con más desacuerdo es {desac['pregunta']}: "
                            f"{e['afirmaciones'][desac['pregunta']]['pct_bajo']} % eligió 1 o 2 en la escala de acuerdo.")},
            {"texto": "¿qué opinión está más dividida?", "tipo": "dato", "intenciones": ["hallazgo", "resumen_pregunta"],
             "debe_mencionar": [divid["pregunta"]], "cifras": divid["cifras"],
             "referencia": (f"La opinión más dividida es {divid['pregunta']} (desviación estándar "
                            f"{e['afirmaciones'][divid['pregunta']]['desviacion']}).")}]},
        {"caso": 12, "titulo": "De qué trata el instrumento", "turnos": [
            {"texto": "¿de qué trata el instrumento?", "tipo": "dato", "intenciones": ["semantica_abierta", "metodologia"],
             "cifras": [[e["n_preguntas"], t]], "debe_mencionar": ["calidad academica"],
             "referencia": (f"Encuesta sobre la percepción de los estudiantes de la calidad académica de su institución: "
                            f"{e['n_preguntas']} preguntas y {t} respondentes, carrera de {e['carrera']}.")},
            {"texto": "pero dame el de qué trata más descriptivo, contextual", "tipo": "interpretativo",
             "intenciones": ["semantica_abierta", "metodologia"],
             "criterios": ["Contextualiza el objetivo y las dimensiones con los metadatos reales; no inventa."]}]},
        {"caso": 13, "titulo": "Secciones (con errata)", "turnos": [
            {"texto": "el instrumento tiene secciones}'", "tipo": "control", "intenciones": ["metodologia", "semantica_abierta"],
             "cifras": [[e["n_preguntas"]]],
             "referencia": f"No tiene secciones en los datos: sus {e['n_preguntas']} preguntas forman un solo bloque.",
             "nota": "La descripción del cuestionario dice «cinco secciones», pero los datos no traen encabezados de sección."},
            {"texto": "qué secciones tiene?", "tipo": "control", "intenciones": ["metodologia", "semantica_abierta"],
             "cifras": [[e["n_preguntas"]]],
             "referencia": f"No tiene secciones en los datos: sus {e['n_preguntas']} preguntas forman un solo bloque."}]},
        {"caso": 14, "titulo": "Respuestas en blanco", "turnos": [
            {"texto": "hay respondentes que dejaron en blanco alugunas preguntas?", "tipo": "dato",
             "intenciones": ["conteo_porcentaje", "resumen_pregunta"], "cifras": e["en_blanco"],
             "referencia": (f"Sí: {e['en_blanco'][0][0]} de {t} respondentes ({e['en_blanco'][1][2]} %) dejaron al "
                            f"menos una pregunta en blanco ({e['en_blanco'][2][0]} respuestas vacías en total).")}]},
    ]


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--instrumento", type=int, default=127)
    a = args.parse_args()
    sesion = SessionLocal()
    try:
        esperado = calcular(sesion, a.instrumento)
    finally:
        sesion.close()
    lista = casos(esperado)
    SALIDA.write_text(json.dumps({"instrumento": a.instrumento, "esperado": esperado, "casos": lista},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    turnos = sum(len(c["turnos"]) for c in lista)
    print(f"{len(lista)} casos, {turnos} turnos → {SALIDA}")
    for c in lista:
        for i, turno in enumerate(c["turnos"], 1):
            print(f"  {c['caso']:>2}.{i} [{turno['tipo']}] {turno['texto'][:70]}")
            if turno.get("referencia"):
                print(f"        → {turno['referencia'][:110]}")


if __name__ == "__main__":
    main()
