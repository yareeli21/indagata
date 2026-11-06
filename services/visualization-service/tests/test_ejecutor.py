"""Etapa 2 del chat (28 oct): ejecutor determinista del plan y candidatos a hallazgo.

Los valores esperados se calculan a mano sobre `docs_ejemplo` (5 respondentes) o sobre documentos armados aquí.
"""
from __future__ import annotations

from services import hallazgos
from services.ejecutor import ejecutar
from services.enrutador import Instrumento
from services.plan_consulta import LIMITE_MAX, PlanConsulta
from tests import docs_ejemplo


def _enc() -> Instrumento:
    return Instrumento("1", "Experiencia estudiantil", "encuesta", docs_ejemplo.encuesta())


def _carga() -> Instrumento:
    return Instrumento("4", "Encuesta de carga académica", "encuesta", docs_ejemplo.encuesta_carga())


def _plan(**datos) -> PlanConsulta:
    return PlanConsulta.model_validate(datos)


def _uno(plan: PlanConsulta, ins: Instrumento):
    (e,) = ejecutar(plan, [ins])
    return e


# ── Respondentes ───────────────────────────────────────────────────────────────


def test_primer_respondente_con_todas_sus_respuestas():
    e = _uno(_plan(intencion="datos_respondente", campos="todas_las_respuestas", orden={"dir": "asc"}, limite=1), _enc())
    (t,) = e.tablas
    assert t.columnas == ["Pregunta", "R001"]
    assert t.filas[0] == ["Contexto: Turno", "Matutino"]
    assert t.filas[1] == ["p01 «Los profesores explican con claridad»", "De acuerdo"]
    assert len(t.filas) == 1 + 7 and e.respondentes == ["INS-0001-R001"] and e.total == 5
    assert e.criterio == "el primero por número de respondente (de 5)"


def test_ultimo_respondente_y_campos_elegidos():
    e = _uno(_plan(intencion="datos_respondente", orden={"dir": "desc"}, limite=1, campos=["p03"]), _enc())
    assert e.tablas[0].columnas == ["Pregunta", "R005"] and e.tablas[0].filas[-1][1] == "En desacuerdo"
    assert e.preguntas == ["INS-0001-p03"]


def test_entrevista_y_prueba_por_participante():
    ent = Instrumento("3", "Entrevistas", "entrevista", docs_ejemplo.entrevista())
    e = _uno(_plan(intencion="datos_respondente", respondentes=["E02"], campos="todas_las_respuestas"), ent)
    assert e.tablas[0].filas[0][1] == "La evaluación es con proyectos y rúbricas claras."
    pru = Instrumento("2", "Diagnóstico", "prueba_estandarizada", docs_ejemplo.prueba())
    e = _uno(_plan(intencion="datos_respondente", respondentes=["A001"], campos="todas_las_respuestas"), pru)
    assert [f[1] for f in e.tablas[0].filas] == ["56", "11"]


# ── Filtros ────────────────────────────────────────────────────────────────────


def test_filtro_con_limite_orden_y_todas_las_respuestas():
    plan = _plan(intencion="filtrar_respondentes", filtros=[{"pregunta": "p03", "valor": "No trabajo"}],
                 campos="todas_las_respuestas", orden={"dir": "asc"}, limite=5)
    e = _uno(plan, _carga())
    assert e.total == 2 and e.mostrados == 2
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in e.lineas
    assert e.tablas[0].columnas == ["Pregunta", "R001", "R004"]
    assert "«No trabajo»" in e.criterio


def test_filtro_limite_uno_dice_cuantos_cumplen_en_total():
    plan = _plan(intencion="filtrar_respondentes", filtros=[{"pregunta": "p03", "valor": "No trabajo"}], limite=1)
    e = _uno(plan, _carga())
    assert e.total == 2 and e.mostrados == 1 and "Respondentes: R001." in e.lineas
    assert any("el primero por número de respondente" in l and "1 de 2" in l for l in e.lineas)


def test_filtro_numerico_distinto_y_vacio():
    assert _uno(_plan(intencion="filtrar_respondentes", filtros=[{"pregunta": "p04", "op": ">", "valor": 20}]), _carga()).total == 2
    assert _uno(_plan(intencion="filtrar_respondentes", filtros=[{"pregunta": "p02", "op": "!=", "valor": "Sí"}]), _carga()).total == 3
    vacio = _uno(_plan(intencion="filtrar_respondentes", filtros=[{"pregunta": "p04", "op": ">", "valor": 99}]), _carga())
    assert vacio.vacio and "Cumplen la condición 0 de 5 respondentes (0.0 %)." in vacio.lineas and not vacio.tablas


def test_limite_de_personas_con_todas_sus_respuestas_tiene_tope():
    doc = _doc_grupos()
    e = _uno(_plan(intencion="filtrar_respondentes", campos="todas_las_respuestas", limite=LIMITE_MAX),
             Instrumento("9", "Grupos", "encuesta", doc))
    assert e.total == 24 and e.mostrados == 10 and len(e.tablas[0].columnas) == 11


def test_contexto_con_datos_personales_no_se_muestra():
    doc = docs_ejemplo.encuesta()
    doc["respondentes"][0]["contexto"]["Nombre completo"] = "Ana López"
    e = _uno(_plan(intencion="datos_respondente", respondentes=["R001"], campos="todas_las_respuestas"),
             Instrumento("1", "x", "encuesta", doc))
    texto = e.texto()
    assert "Ana" not in texto and "Contexto: Turno" in texto


# ── Conteos, comparaciones, resúmenes, KPIs ────────────────────────────────────


def test_conteo_por_nivel_y_por_filtro():
    e = _uno(_plan(intencion="conteo_porcentaje", preguntas=["p01"], nivel="desacuerdo"), _enc())
    assert any("2 de 5 de quienes respondieron están en desacuerdo (nivel bajo) (40.0 %)" in l for l in e.lineas)
    e = _uno(_plan(intencion="conteo_porcentaje", filtros=[{"pregunta": "p02", "valor": "Sí"}]), _carga())
    assert e.lineas == ["Cumplen la condición 2 de 5 respondentes (40.0 %)."] and e.total == 2


def test_comparar_grupos_por_contexto():
    e = _uno(_plan(intencion="comparar_grupos", preguntas=["p01"], nivel="acuerdo", agrupar_por="Turno"), _enc())
    (t,) = e.tablas
    assert t.columnas == ["Turno", "Respondentes", "p01: de acuerdo (nivel alto)"]
    assert t.filas == [["Matutino", "2", "50.0 % (1 de 2)"], ["Vespertino", "3", "33.3 % (1 de 3)"]]


def test_resumen_de_reactivo_sin_calificar():
    pru = Instrumento("2", "Diagnóstico", "prueba_estandarizada", docs_ejemplo.prueba())
    e = _uno(_plan(intencion="resumen_pregunta", preguntas=["r01"]), pru)
    assert "Opción más elegida: «56» (84.6 %, 11 alumnos)." in e.lineas
    assert not any("correct" in l.lower() for l in e.lineas)


def test_kpi_trae_solo_sus_preguntas_y_su_id():
    e = _uno(_plan(intencion="kpi", kpi="KPI-07"), _enc())
    assert e.kpis == ["KPI-07"] and e.preguntas == ["INS-0001-p04", "INS-0001-p07"]
    assert any("Por qué se asoció" in l for l in e.lineas)
    assert _uno(_plan(intencion="kpi"), _carga()).vacio


def test_intenciones_no_estructuradas_no_se_ejecutan():
    assert ejecutar(_plan(intencion="metodologia"), [_enc()]) == []
    assert ejecutar(_plan(intencion="semantica_abierta", consulta_semantica="x"), [_enc()]) == []


# ── Hallazgos ──────────────────────────────────────────────────────────────────


def _doc_grupos() -> dict:
    """24 respondentes: en p01 el turno matutino está 100 % de acuerdo y el vespertino 25 %."""
    respondentes = []
    for i in range(24):
        turno = "Matutino" if i < 12 else "Vespertino"
        acuerdo = turno == "Matutino" or i % 4 == 0
        respondentes.append({"id": f"INS-0009-R{i + 1:03d}", "contexto": {"Turno": turno}, "respuestas": [
            {"pregunta_id": "INS-0009-p01", "pregunta": "Me gusta la carrera", "estado": "respondida",
             "valor": 5 if acuerdo else 1, "significado": "Totalmente de acuerdo" if acuerdo else "Totalmente en desacuerdo",
             "nivel": "acuerdo" if acuerdo else "desacuerdo"}]})
    return {"instrumento": {"id": "INS-0009", "tipo": "encuesta", "titulo": "Grupos"}, "kpis_asociados": [],
            "preguntas": [{"id": "INS-0009-p01", "texto": "Me gusta la carrera", "tipo": "likert", "resumen": {
                "n_validas": 24, "n_sin_respuesta": 0, "por_nivel": {"acuerdo": 62.5, "desacuerdo": 37.5},
                "distribucion": [{"significado": "Totalmente en desacuerdo", "n": 9, "pct": 37.5},
                                 {"significado": "Totalmente de acuerdo", "n": 15, "pct": 62.5}]}}],
            "respondentes": respondentes}


def test_hallazgo_encuentra_la_diferencia_entre_grupos_y_el_acuerdo():
    cands = hallazgos.candidatos("encuesta", _doc_grupos())
    tipos = [c["tipo"] for c in cands]
    assert tipos[0] == "diferencia_grupos"
    assert "«Matutino» (Turno) está en el nivel alto en un 100.0 %" in cands[0]["texto"] and "75.0 puntos" in cands[0]["texto"]
    acuerdo = next(c for c in cands if c["tipo"] == "mayor_acuerdo")
    assert "de acuerdo es p01" in acuerdo["texto"] and "62.5 %" in acuerdo["texto"]


def test_hallazgo_con_fiabilidad_baja_y_en_prueba_sin_calificar():
    cands = hallazgos.candidatos("encuesta", _doc_grupos(), [{"bloque": "Satisfacción", "alfa": 0.41, "n_items": 4}])
    assert any(c["tipo"] == "fiabilidad_baja" and "0.41" in c["texto"] for c in cands)
    prueba = hallazgos.candidatos("prueba_estandarizada", docs_ejemplo.prueba())
    assert {c["tipo"] for c in prueba} == {"reactivo_coincidencia", "reactivo_repartido", "mucha_no_respuesta"}
    assert not any("difícil" in c["texto"] or "correct" in c["texto"] for c in prueba)


def test_ejecutor_de_hallazgo_lista_candidatos_y_sus_fuentes():
    e = _uno(_plan(intencion="hallazgo"), Instrumento("9", "Grupos", "encuesta", _doc_grupos()))
    assert e.lineas[0].startswith("Dato 1: En p01") and e.preguntas == ["INS-0009-p01"]


def test_endpoint_interpretar_devuelve_plan_y_resultado(cliente, storage, db, monkeypatch):
    import json as _json

    from conftest import token
    from services import enrutador, interpretacion
    from tests.test_filtros import _publicar

    from shared.models.usuario import Usuario

    enrutador._cache_docs.clear()
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    _publicar(db, storage, 4, docs_ejemplo.encuesta_carga())

    async def no_stream(prompt, modelo, sistema=None, *, formato=None, opciones=None):  # noqa: ANN001
        return _json.dumps({"intencion": "filtrar_respondentes", "filtros": [{"pregunta": "p03", "valor": "no trabajo"}],
                            "campos": "todas_las_respuestas", "limite": 5}), False

    monkeypatch.setattr(interpretacion.ollama_client, "generar_no_stream", no_stream)
    r = cliente.post("/rag/interpretar", json={"pregunta": "los que no trabajan con todas sus respuestas", "instrumentoIds": ["4"]},
                    headers=token(2))
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["plan"]["filtros"][0]["valor"] == "No trabajo"
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in datos["ejecucion"][0]
    assert "| Pregunta | R001 | R004 |" in datos["ejecucion"][0]


def test_ultimo_respondente_por_numero_no_por_texto():
    """Regresión C10 (28 oct): como texto, «R999» quedaba después de «R2000»."""
    doc = _doc_grupos()
    for i, r in enumerate(doc["respondentes"]):
        r["id"] = f"INS-0009-R{[5, 999, 2000][i % 3] + i:03d}"
    e = _uno(_plan(intencion="datos_respondente", orden={"dir": "desc"}, limite=1, campos=["p01"]),
             Instrumento("9", "Grupos", "encuesta", doc))
    assert e.tablas[0].columnas[1] == "R2023"


def test_filtro_por_nivel_y_por_grupo_de_contexto():
    # p01 en acuerdo: R001 (4), R004 (5) → 2 de 5; del turno vespertino solo R004.
    e = _uno(_plan(intencion="conteo_porcentaje", filtros=[{"pregunta": "p01", "nivel": "acuerdo"}]), _enc())
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in e.lineas
    e = _uno(_plan(intencion="conteo_porcentaje", filtros=[{"pregunta": "p01", "nivel": "acuerdo"}],
                   contexto={"Turno": "Vespertino"}), _enc())
    assert "Cumplen la condición 1 de 5 respondentes (20.0 %)." in e.lineas and "Turno = «Vespertino»" in e.criterio
    # % de acuerdo en p01 dentro del turno vespertino: R002 (2), R003 (3), R004 (5) → 1 de 3.
    e = _uno(_plan(intencion="conteo_porcentaje", preguntas=["p01"], nivel="acuerdo", contexto={"Turno": "Vespertino"}), _enc())
    assert any("1 de 3 de quienes cumplen la condición y respondieron" in l and "33.3 %" in l for l in e.lineas)


def test_comparacion_sobre_contexto_numerico():
    """Fase 6 (consultas 1486 y 1522): «¿cuántos trabajan más de 20 horas?» cuando las horas son un dato de contexto."""
    doc = docs_ejemplo.encuesta()
    for r, edad in zip(doc["respondentes"], ["18", "22", "25", "31", ""]):
        r["contexto"]["Edad"] = edad
    ins = Instrumento("1", "Experiencia estudiantil", "encuesta", doc)
    e = _uno(_plan(intencion="conteo_porcentaje", contexto_num=[{"variable": "Edad", "op": ">", "valor": 20}]), ins)
    assert e.criterio == "Edad > 20" and "Cumplen la condición 3 de 5 respondentes (60.0 %)." in e.lineas
    e = _uno(_plan(intencion="conteo_porcentaje", contexto={"Turno": "Matutino"},
                   contexto_num=[{"variable": "Edad", "op": "<=", "valor": 22}]), ins)
    assert e.criterio.startswith("Turno = «Matutino» y Edad <= 22")
    # Sin el dato (R005) no se cumple ninguna comparación.
    e = _uno(_plan(intencion="filtrar_respondentes", contexto_num=[{"variable": "Edad", "op": "<", "valor": 100}]), ins)
    assert e.total == 4


def _prueba_ranking() -> Instrumento:
    """Prueba inventada de 20 alumnos: r01 vacío, r02 y r03 con 2 sin responder (empate), r04 casi unánime."""
    def reactivo(n: int, texto: str, nulas: int, sin: int, top: tuple[str, int] | None):
        resumen = {"n_alumnos": 20, "n_nulas": nulas, "n_sin_respuesta": sin,
                   "opcion_mas_elegida": {"opcion": "A", "significado": top[0], "n": top[1], "pct": round(100 * top[1] / 20, 1)}
                   if top else None}
        return {"id": f"INS-0009-r{n:02d}", "texto": texto, "resumen": resumen}
    doc = {"reactivos": [reactivo(1, "¿Qué es un firewall?", 0, 20, None),
                         reactivo(2, "¿Qué es una hoja de cálculo?", 1, 1, ("Un programa", 9)),
                         reactivo(3, "¿Qué es la nube?", 0, 2, ("Un servidor remoto", 7)),
                         reactivo(4, "Un PDF se puede editar.", 0, 0, ("Verdadero", 19)),
                         reactivo(5, "¿Qué es un navegador?", 0, 1, ("Un programa", 12))],
           "alumnos": []}
    return Instrumento("9", "Prueba de cómputo", "prueba_estandarizada", doc)


def test_ranking_por_no_respuesta_con_exclusion_y_empate():
    """Fase 6 (consultas 1493, 1498 y 1529): «sin contar la de la contraseña» siempre devolvía el reactivo vacío."""
    ins = _prueba_ranking()
    e = _uno(_plan(intencion="ranking_preguntas", criterio_ranking="no_respuesta"), ins)
    assert e.lineas[0].startswith("1. r01") and "20 nulas o sin responder de 20 (100.0 %)" in e.lineas[0]
    e = _uno(_plan(intencion="ranking_preguntas", criterio_ranking="no_respuesta", excluir_preguntas=["r01"]), ins)
    assert e.criterio.endswith("sin contar r01")
    assert "2 nulas o sin responder de 20 (10.0 %)" in e.lineas[0] and "Empatan en el primer lugar: r02, r03." in e.lineas
    assert all("r01" not in l for l in e.lineas)


def test_ranking_por_coincidencia_y_repartida():
    ins = _prueba_ranking()
    e = _uno(_plan(intencion="ranking_preguntas", criterio_ranking="coincidencia"), ins)
    assert e.lineas[0].startswith("1. r04") and "«Verdadero» con 19 de 20 (95.0 %)" in e.lineas[0]
    e = _uno(_plan(intencion="ranking_preguntas", criterio_ranking="repartida"), ins)
    assert e.lineas[0].startswith("1. r03")  # 35 %: la opción más elegida más baja; r01 (sin respuestas) no entra
    assert all("r01" not in l for l in e.lineas)


def test_ranking_en_una_encuesta_usa_sus_resumenes():
    e = _uno(_plan(intencion="ranking_preguntas", criterio_ranking="no_respuesta"), _enc())
    assert e.lineas and not e.vacio and e.tablas[0].columnas == ["Lugar", "Pregunta", "Dato"]


def _entrevistas_menciones() -> Instrumento:
    """Dos entrevistas inventadas sobre la vida en la residencia."""
    def e(pid: str, respuestas: dict[str, str]):
        return {"participante": f"INS-0006-{pid}", "contexto": {},
                "intercambios": [{"pregunta_id": f"INS-0006-{q}", "pregunta": "", "respuesta": r} for q, r in respuestas.items()]}
    doc = {"preguntas": [{"id": "INS-0006-p01", "texto": "¿Cómo es tu día?", "tipo": "guia"},
                         {"id": "INS-0006-p02", "texto": "¿Qué te preocupa?", "tipo": "guia"}],
           "entrevistas": [e("E01", {"p01": "Me levanto temprano y estudio en la biblioteca.",
                                     "p02": "Me estresa mucho el ruido; el estrés no me deja dormir."}),
                           e("E02", {"p01": "Trabajo por las tardes.", "p02": "Nada en especial, la comida."})]}
    return Instrumento("6", "Entrevistas de residencia", "entrevista", doc)


def test_conteo_de_menciones_en_entrevistas_con_citas():
    """Fase 6 (consultas 1468 y 1540): «¿cuántos mencionaron la ansiedad?» no tenía cómo contarse."""
    ins = _entrevistas_menciones()
    e = _uno(_plan(intencion="conteo_porcentaje", menciona="estrés"), ins)
    assert "Cumplen la condición 1 de 2 respondentes (50.0 %)." in e.lineas
    assert e.criterio == "mencionan «estrés» en sus respuestas abiertas"
    (t,) = e.tablas
    assert t.filas[0][:2] == ["E01", "p02"] and "estresa" in t.filas[0][2]  # misma raíz: «estre»
    assert _uno(_plan(intencion="conteo_porcentaje", menciona="biblioteca", preguntas=["p02"]), ins).total == 0
    e = _uno(_plan(intencion="filtrar_respondentes", menciona="comida"), ins)
    assert e.respondentes == ["INS-0006-E02"] and e.tablas[0].filas[0][1] == "p02"


def test_menciones_en_una_encuesta_solo_en_respuestas_abiertas():
    doc = {"preguntas": [{"id": "INS-0005-p01", "texto": "¿Usas la biblioteca?", "tipo": "categorica"},
                         {"id": "INS-0005-p02", "texto": "Comentarios", "tipo": "texto_largo"}],
           "respondentes": [
               {"id": "INS-0005-R001", "contexto": {}, "respuestas": [
                   {"pregunta_id": "INS-0005-p01", "estado": "respondida", "significado": "Biblioteca central"},
                   {"pregunta_id": "INS-0005-p02", "estado": "respondida", "significado": "Todo bien."}]},
               {"id": "INS-0005-R002", "contexto": {}, "respuestas": [
                   {"pregunta_id": "INS-0005-p02", "estado": "respondida", "significado": "La Biblioteca cierra muy temprano."}]}]}
    e = _uno(_plan(intencion="conteo_porcentaje", menciona="biblioteca"), Instrumento("5", "Servicios", "encuesta", doc))
    assert e.total == 1 and e.tablas[0].filas == [["R002", "p02", "«La Biblioteca cierra muy temprano.»"]]


def test_resumen_de_una_pregunta_de_entrevista_muestra_las_respuestas():
    """Fase 6, segunda corrida (1551): el resumen de una pregunta de entrevista decía «sin resumen calculado»."""
    e = _uno(_plan(intencion="resumen_pregunta", preguntas=["p02"]), _entrevistas_menciones())
    assert e.lineas == ["p02 «¿Qué te preocupa?»: respondieron 2 de 2 participantes."]
    assert e.tablas[0].filas[1] == ["E02", "Nada en especial, la comida."]


def test_hallazgo_pide_varios_patrones_y_el_respaldo_trae_tres():
    """4 nov: la redacción pedía «UNO de los datos» aunque se calculan hasta 6; ahora pide de 3 a 5 y, si la redacción
    no pasa la verificación, el respaldo muestra los 3 primeros."""
    from services import consulta_planificada

    e = _uno(_plan(intencion="hallazgo"), Instrumento("9", "Grupos", "encuesta", _doc_grupos()))
    assert len(e.candidatos) >= 3
    assert "TRES o CUATRO patrones" in consulta_planificada.FORMATO["hallazgo"]
    directa = consulta_planificada.directa([e])
    assert all(c["texto"] in directa for c in e.candidatos[:3])
    assert all(c["texto"] not in directa for c in e.candidatos[3:])
