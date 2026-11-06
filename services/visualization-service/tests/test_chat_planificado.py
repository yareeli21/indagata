"""Fase 3 del rediseño (28 oct): el chat con interpretación → ejecución → redacción por intención.

Ollama simulado: la llamada con JSON Schema (`formato` dict) devuelve el plan que pone cada prueba; la de texto
devuelve la redacción que pone cada prueba. Los valores esperados salen de `docs_ejemplo.CARGA` (5 respondentes):
no trabajan R001 y R004; dicen «Sí» a las dificultades R001 y R002.
"""
from __future__ import annotations

import json

import pytest

from shared.db.core.config import settings
from shared.models.rag_log import RagLog
from shared.models.usuario import Usuario

import docs_ejemplo
from conftest import token
from services import enrutador
from tests.test_filtros import _publicar


@pytest.fixture()
def chat(cliente, db, storage, chroma, monkeypatch):
    """Cliente con la interpretación encendida y un Ollama que responde lo que diga `estado`."""
    from services import ollama_client

    monkeypatch.setattr(settings, "RAG_INTERPRETACION_LLM", True)
    monkeypatch.setattr(settings, "RAG_MIN_SCORE", 0.0)
    base = {"titulo": "Encuesta de carga académica y gestión del tiempo", "tipo": "Encuesta", "investigador": "Ana",
            "kpis": "[]", "instrumentoId": "4", "preguntaId": "", "pregunta": ""}
    chroma.crear("instrumentos").agregar("inst-4-1", "Respondente R002: carga laboral, trabajo más de 30h",
                                         {**base, "seccion": "respondente"})
    enrutador._cache_docs.clear()
    db.add(Usuario(usuario_id=2, nombre="Ana", email="ana@x.com", password_hash="x", rol="investigador"))
    _publicar(db, storage, 1, docs_ejemplo.encuesta())
    _publicar(db, storage, 4, docs_ejemplo.encuesta_carga())
    estado = {"plan": None, "redaccion": "", "planes": 0, "redacciones": [], "interpretaciones": []}

    async def no_stream(prompt, modelo, sistema=None, *, formato=None, opciones=None):  # noqa: ANN001
        if isinstance(formato, dict):
            estado["planes"] += 1
            estado["interpretaciones"].append(prompt)
            return json.dumps(estado["plan"]) if estado["plan"] is not None else "no es json", False
        if formato == "json":  # clasificador de la zona gris o filtro de las reglas
            return json.dumps({"dentro": True, "motivo": "prueba"}), False
        estado["redacciones"].append(prompt)
        r = estado["redaccion"]
        return (r.pop(0) if len(r) > 1 else r[0]) if isinstance(r, list) else r, False

    async def stream(prompt, modelo, sistema=None):  # noqa: ANN001
        estado["redacciones"].append(prompt)
        yield "Respuesta semántica [Fuente 1]."

    monkeypatch.setattr(ollama_client, "generar_no_stream", no_stream)
    monkeypatch.setattr(ollama_client, "generar_stream", stream)

    def preguntar(pregunta: str, ids: list[str], historial: list[dict] | None = None) -> tuple[dict, RagLog]:
        r = cliente.post("/rag/chat", headers=token(2), json={
            "pregunta": pregunta, "instrumentoIds": ids, "stream": False, "historial": historial or []})
        assert r.status_code == 200, r.text
        datos = r.json()
        db.expire_all()
        return datos, db.get(RagLog, datos["consultaId"])

    estado["preguntar"] = preguntar
    return estado


_FILTRO = {"intencion": "filtrar_respondentes", "filtros": [{"pregunta": "p03", "valor": "no trabajo"}],
           "campos": "todas_las_respuestas", "orden": {"dir": "asc"}, "limite": 5}


def test_filtro_con_todas_las_respuestas_presentacion_fija_y_tabla_del_calculo(chat):
    """La tabla de respondentes no pasa por el modelo: el de 3B inventó una tabla con respuestas falsas (28 oct)."""
    chat["plan"] = _FILTRO
    datos, fila = chat["preguntar"]("dame los primeros 5 que no trabajan con todas sus respuestas", ["4"])
    assert datos["respuesta"].startswith("Criterio: p03 «¿Cuál es tu carga laboral actual?» = «No trabajo».")
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in datos["respuesta"]
    assert "| Pregunta | R001 | R004 |" in datos["respuesta"] and "[Fuente 1]**" in datos["respuesta"]
    (fuente,) = datos["fuentes"]
    assert fuente["kpis"] == [] and "Respondentes: R001, R004" in fuente["fragmento"]
    assert fila.ruta == "estructurada" and fila.motivo == "plan:filtrar_respondentes:tabla"
    assert fila.plan["plan"]["intencion"] == "filtrar_respondentes"
    assert "p03: «no trabajo» → «No trabajo»" in fila.plan["correcciones"]
    assert set(fila.tiempos) == {"interpretacion", "ejecucion", "recuperacion"} and chat["redacciones"] == []
    assert fila.metricas["fidelidad"] == 1.0 and fila.metricas["estado"] in ("calculando", "calculada")


def test_primer_respondente_con_sus_respuestas(chat):
    """4 nov: lo que respondió una persona lo interpreta el modelo (con la tabla en el prompt) y la tabla va debajo."""
    chat["plan"] = {"intencion": "datos_respondente", "campos": "todas_las_respuestas", "orden": {"dir": "asc"}, "limite": 1}
    chat["redaccion"] = "R001 no trabaja y dedica 12 horas por semana al estudio (p04) [Fuente 1]."
    datos, fila = chat["preguntar"]("qué respondió el primer respondente en todas las preguntas?", ["4"])
    assert datos["respuesta"].startswith("R001 no trabaja y dedica 12 horas")
    assert "| Pregunta | R001 |" in datos["respuesta"] and fila.motivo == "plan:datos_respondente"
    assert "| p04 «¿Cuántas horas" in chat["redacciones"][0]  # el modelo lee la tabla para interpretarla
    chat["redaccion"] = ""  # una redacción vacía no se muestra: sale la presentación calculada
    datos, fila = chat["preguntar"]("qué respondió el primero en todas las preguntas?", ["4"])
    assert datos["respuesta"].startswith("Respuestas interpretadas de R001 (el primero por número de respondente (de 5)).")
    assert fila.plan["verificacion"]["primer_fallo"] == "vacia"


def test_redaccion_con_cifra_inventada_se_reemplaza_por_el_resultado(chat):
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = "Cumplen 3 de 5 respondentes (60 %) [Fuente 1]."
    datos, fila = chat["preguntar"]("¿cuántos tienen dificultades?", ["4"])
    assert fila.motivo == "plan:conteo_porcentaje:cifras_corregidas"
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in datos["respuesta"]
    assert fila.metricas["fidelidad"] == 1.0 and fila.metricas["estado"] in ("calculando", "calculada")
    assert set(fila.tiempos) == {"interpretacion", "ejecucion", "recuperacion", "redaccion", "verificacion"}
    assert "FORMATO DE LA RESPUESTA" in chat["redacciones"][0]


def test_redaccion_con_id_o_tabla_inventados_se_descarta(chat):
    chat["plan"] = {"intencion": "kpi", "kpi": "KPI-07"}
    chat["redaccion"] = "El KPI se sustenta en p04 y en lo que dijo R099 [Fuente 1]."
    _, fila = chat["preguntar"]("¿qué preguntas miden la satisfacción estudiantil?", ["1"])
    assert fila.motivo == "plan:kpi:inventada"
    chat["redaccion"] = "Así quedan:\n| Pregunta | Respuesta |\n|---|---|\n| p04 | Sí |"
    _, fila = chat["preguntar"]("¿qué preguntas miden la satisfacción?", ["1"])
    assert fila.motivo == "plan:kpi:inventada"


def test_conteo_que_omite_el_total_se_completa(chat):
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = "Son 2 personas [Fuente 1]."
    datos, fila = chat["preguntar"]("¿cuántos tienen dificultades para equilibrar trabajo y estudios?", ["4"])
    assert fila.motivo.endswith(":cifras_completadas") and "2 de 5 respondentes (40.0 %)" in datos["respuesta"]


def test_resultado_vacio_se_dice_sin_redaccion(chat):
    chat["plan"] = {"intencion": "filtrar_respondentes", "filtros": [{"pregunta": "p04", "op": ">", "valor": 99}]}
    datos, fila = chat["preguntar"]("¿quiénes estudian más de 99 horas?", ["4"])
    assert "Cumplen la condición 0 de 5 respondentes (0.0 %)." in datos["respuesta"]
    assert fila.motivo == "plan:filtrar_respondentes:vacio" and chat["redacciones"] == []


def test_kpis_como_fuente_solo_si_la_consulta_trata_de_kpis(chat):
    chat["plan"] = {"intencion": "kpi", "kpi": "KPI-07"}
    chat["redaccion"] = "El KPI Satisfacción estudiantil se sustenta en p04 y p07 [Fuente 1]."
    datos, _ = chat["preguntar"]("¿qué preguntas miden la satisfacción estudiantil?", ["1"])
    assert datos["fuentes"][0]["kpis"] == ["Satisfacción estudiantil"] and "| KPI |" in datos["respuesta"]
    chat["plan"] = {"intencion": "datos_respondente", "respondentes": ["R001"], "campos": "todas_las_respuestas"}
    chat["redaccion"] = "Estas son las respuestas de R001 [Fuente 1]."
    datos, _ = chat["preguntar"]("¿qué respondió R001?", ["1"])
    assert datos["fuentes"][0]["kpis"] == [] and "| Pregunta | R001 |" in datos["respuesta"]


def test_aclaracion_y_fuera_de_dominio(chat):
    chat["plan"] = {"intencion": "aclaracion", "aclaracion": "¿De qué pregunta quieres saber?"}
    datos, fila = chat["preguntar"]("¿y eso?", ["4"])
    assert datos["respuesta"] == "¿De qué pregunta quieres saber?" and fila.ruta == "aclaracion"
    chat["plan"] = {"intencion": "fuera_de_dominio"}
    datos, fila = chat["preguntar"]("háblame de los dinosaurios", ["4"])
    assert fila.decision_dominio == "fuera" and fila.motivo == "plan:fuera_de_dominio"


def test_fuera_de_dominio_que_habla_del_instrumento_no_se_rechaza(chat):
    chat["plan"] = {"intencion": "fuera_de_dominio"}
    _, fila = chat["preguntar"]("¿qué dijeron los respondentes sobre su carga laboral?", ["4"])
    assert fila.decision_dominio != "fuera" and fila.ruta == "semantica"


def test_sin_plan_valido_siguen_las_reglas(chat):
    chat["plan"] = None  # el modelo devuelve algo que no es JSON (dos veces)
    _, fila = chat["preguntar"]("¿Cuántos estudiantes trabajan más de 30 horas?", ["4"])
    assert chat["planes"] == 2 and fila.plan["plan"] is None and fila.plan["error"].startswith("plan no válido")
    assert fila.motivo.startswith("estructurada:filtro")  # respondió el enrutador de reglas


def test_el_historial_cambia_la_huella_de_la_cache(monkeypatch):
    from models import ChatRequest
    from services import rag_service

    monkeypatch.setattr(settings, "RAG_CACHE_HORAS", 24)

    class _Sesion:
        def query(self, *a):  # noqa: ANN002
            return self

        def filter(self, *a):  # noqa: ANN002
            return self

        def all(self):
            return []

        def close(self):
            pass

    monkeypatch.setattr(rag_service, "fabrica_sesiones", lambda: _Sesion())
    sola = ChatRequest(pregunta="¿y de ellos cuántos?", instrumentoIds=["4"])
    con = ChatRequest(pregunta="¿y de ellos cuántos?", instrumentoIds=["4"],
                      historial=[{"rol": "usuario", "texto": "¿cuántos no trabajan?"}])
    assert rag_service.clave_cache(sola, "m") != rag_service.clave_cache(con, "m")


def test_redaccion_invalida_se_regenera_una_vez_con_el_motivo(chat):
    """Fase 4: antes de responder con el resultado calculado se le da al modelo una segunda oportunidad."""
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = ["Son 7 personas [Fuente 1].", "Cumplen la condición 2 de 5 respondentes (40.0 %) [Fuente 1]."]
    datos, fila = chat["preguntar"]("¿cuántos tienen dificultades para equilibrar?", ["4"])
    assert fila.motivo == "plan:conteo_porcentaje:regenerada"
    assert datos["respuesta"] == "Cumplen la condición 2 de 5 respondentes (40.0 %) [Fuente 1]."
    assert fila.plan["verificacion"] == {"intentos": 2, "primer_fallo": "cifras_corregidas", "resultado": "regenerada"}
    assert "No es válida porque usa cifras que no están" in chat["redacciones"][1]


def test_dos_redacciones_invalidas_dan_el_resultado_calculado(chat):
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = ["Son 7 personas [Fuente 1].", "Son 9 personas [Fuente 1]."]
    datos, fila = chat["preguntar"]("¿cuántos tienen dificultades para equilibrar el trabajo?", ["4"])
    assert fila.motivo == "plan:conteo_porcentaje:cifras_corregidas"
    assert "Cumplen la condición 2 de 5 respondentes (40.0 %)." in datos["respuesta"]
    assert fila.plan["verificacion"]["resultado"] == "respaldo" and fila.metricas["fidelidad"] == 1.0


def test_semantica_anota_cifras_sin_respaldo(chat):
    chat["plan"] = {"intencion": "semantica_abierta", "consulta_semantica": "carga laboral de los respondentes"}
    _, fila = chat["preguntar"]("¿qué dicen sobre su carga laboral?", ["4"])
    assert fila.ruta == "semantica" and fila.plan["verificacion"]["resultado"] == "aceptada"


def test_semantica_con_regla_determinista_usa_la_regla(chat):
    """«¿los instrumentos tienen secciones?» lo resuelve la regla de estructura aunque el plan diga semántica."""
    chat["plan"] = {"intencion": "semantica_abierta", "consulta_semantica": "secciones de los instrumentos"}
    _, fila = chat["preguntar"]("los instrumentos tienen secciones?", ["4"])
    assert fila.motivo == "estructurada:estructura" and fila.ruta == "estructurada"


def test_aclaracion_de_una_pregunta_ajena_es_fuera_de_dominio(chat):
    """Regresión C16: «¿quién ganó el mundial?» recibía una pregunta de aclaración en lugar del mensaje de dominio."""
    chat["plan"] = {"intencion": "aclaracion", "aclaracion": "¿De qué pregunta hablas?"}
    _, fila = chat["preguntar"]("¿quién ganó el mundial de futbol de 2010?", ["4"])
    assert fila.decision_dominio == "fuera" and fila.motivo == "plan:aclaracion_ajena"
    _, fila = chat["preguntar"]("¿qué opinan de eso?", ["4"])  # se refiere a algo anterior: sí es ambigua
    assert fila.decision_dominio == "dentro" and fila.motivo == "plan:aclaracion"


def test_aclaracion_en_un_seguimiento_se_muestra(chat):
    """Fase 6 (consultas 1519 y 1537): «¿Le parecieron suficientes?» sigue a la pregunta anterior sin repetir sus
    palabras y recibía el mensaje de fuera de dominio."""
    chat["plan"] = {"intencion": "aclaracion", "aclaracion": "¿A qué te refieres con suficientes?"}
    historial = [{"rol": "usuario", "texto": "¿cuántos trabajan más de 30 horas?"},
                 {"rol": "asistente", "texto": "Cumplen la condición 1 de 5 respondentes."}]
    datos, fila = chat["preguntar"]("¿Le parecieron suficientes?", ["4"], historial)
    assert fila.decision_dominio == "dentro" and fila.motivo == "plan:aclaracion"
    assert datos["respuesta"] == "¿A qué te refieres con suficientes?"


def test_pregunta_de_calidad_gana_a_uso_de_la_plataforma(chat):
    """Fase 6 (consulta 1495): «¿Qué se corrigió en la limpieza?» se respondía con la ayuda de la plataforma."""
    chat["plan"] = {"intencion": "uso_plataforma"}
    chat["redaccion"] = "La encuesta no tiene medidas de la limpieza [Fuente 1]."
    _, fila = chat["preguntar"]("¿Qué se corrigió en la limpieza?", ["4"])
    assert fila.ruta != "ayuda" and fila.motivo.startswith("estructurada:calidad")
    chat["plan"] = {"intencion": "uso_plataforma"}
    _, fila = chat["preguntar"]("¿Cómo limpio un instrumento en la plataforma?", ["4"])
    assert fila.ruta == "ayuda"


def test_calificacion_en_una_prueba_la_responde_la_regla(chat, db, storage):
    """Fase 6 (consultas 1577, 1600, 1618): sin clave no hay aprobados ni reactivo «más difícil». El plan inventaba un
    filtro («A» en r01) y pedía aclaración, o respondía con un ranking de no respuesta."""
    _publicar(db, storage, 2, docs_ejemplo.prueba())
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "r01", "valor": "A"}]}
    for pregunta in ("¿Cuántos alumnos aprobaron la prueba?", "Entonces dime quién sacó la calificación más alta",
                     "¿Qué pregunta te parece más difícil para los alumnos?"):
        datos, fila = chat["preguntar"](pregunta, ["2"])
        assert fila.motivo.startswith("estructurada:sin_calificar"), pregunta
        assert "Indagata no califica las pruebas" in datos["respuesta"]
    # En una encuesta, «reprobaron» es una respuesta del cuestionario: sigue el plan.
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = "Cumplen la condición 2 de 5 respondentes (40.0 %) [Fuente 1]."
    _, fila = chat["preguntar"]("¿Cuántos reprobaron la prueba de admisión y tienen dificultades?", ["4"])
    assert fila.motivo.startswith("plan:conteo_porcentaje")


def test_redaccion_con_lenguaje_de_calificacion_se_descarta(chat, db, storage):
    """Fase 6 (consulta 1575): «0 de 97 eligieron la opción correcta» en una prueba que no se califica."""
    _publicar(db, storage, 2, docs_ejemplo.prueba())
    chat["plan"] = {"intencion": "resumen_pregunta", "preguntas": ["r01"]}
    chat["redaccion"] = "En r01 el 84.6 % eligió la opción correcta, «A) 56» [Fuente 1]."
    datos, fila = chat["preguntar"]("¿qué eligieron en el reactivo 1?", ["2"])
    assert fila.motivo.endswith(":calificada")
    assert "correcta" not in datos["respuesta"] and "84.6 %" in datos["respuesta"]
    chat["redaccion"] = "En r01 la mayoría (84.6 %) eligió «A) 56» [Fuente 1]."
    _, fila = chat["preguntar"]("¿qué opción eligieron más en el reactivo 1?", ["2"])
    assert fila.motivo == "plan:resumen_pregunta"


# ── RAG + cálculo (4 nov) ──────────────────────────────────────────────────────


def _fragmento(chroma, pid: str, texto: str, ins: str, seccion: str, pregunta: str = "", persona: str = "") -> None:
    chroma.crear("instrumentos").agregar(pid, texto, {
        "titulo": "Instrumento", "tipo": "Entrevista" if ins == "3" else "Encuesta", "investigador": "Ana", "kpis": "[]",
        "instrumentoId": ins, "seccion": seccion, "preguntaId": f"INS-000{ins}-{pregunta}" if pregunta else "",
        "respondenteId": f"INS-000{ins}-{persona}" if persona else ""})


@pytest.fixture()
def entrevista(chat, chroma, db, storage):
    """La entrevista de ejemplo (id 3, sin análisis de posturas) con sus intercambios en Chroma."""
    _publicar(db, storage, 3, docs_ejemplo.entrevista())
    _fragmento(chroma, "e-1", "Participante E02, pregunta p01: ¿Cómo te evalúan tus profesores? Respuesta: La evaluación "
               "es con proyectos y rúbricas claras.", "3", "intercambio", "p01", "E02")
    _fragmento(chroma, "e-2", "Participante E02, pregunta p02: ¿Qué servicios usas? Respuesta: La biblioteca.",
               "3", "intercambio", "p02", "E02")
    _fragmento(chroma, "e-3", "Participante E01, pregunta p01: ¿Cómo te evalúan tus profesores? Respuesta: Con exámenes.",
               "3", "intercambio", "p01", "E01")
    return chat


def test_respuesta_calculada_lleva_el_texto_recuperado_del_rag(chat, chroma):
    """Antes la ruta del plan no consultaba Chroma: el modelo solo veía el cálculo. Ahora el texto más parecido a la
    pregunta, del mismo instrumento, entra como TEXTO RECUPERADO y se ve en la ruta, la fuente y el contexto usado."""
    _fragmento(chroma, "c-1", "Pregunta p02: ¿Tienes dificultades para equilibrar trabajo y estudios?\nDistribución: Sí "
               "40.0 %; No 60.0 %", "4", "pregunta", "p02")
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = "Cumplen la condición 2 de 5 respondentes (40.0 %), que dicen tener dificultades [Fuente 1]."
    datos, fila = chat["preguntar"]("¿cuántos tienen dificultades para equilibrar trabajo y estudios?", ["4"])
    recuperado = chat["redacciones"][0].split("TEXTO RECUPERADO")[1]
    assert "Pregunta p02: ¿Tienes dificultades" in recuperado and "Distribución" not in recuperado  # sin sus cifras
    assert fila.ruta == "mixta" and fila.motivo == "plan:conteo_porcentaje"
    assert any(c["tipo"] == "fragmento" and c["etiqueta"] == "p02" for c in fila.contexto_usado)
    assert "Texto recuperado del RAG: p02" in datos["fuentes"][0]["fragmento"]


def test_en_un_conteo_la_cifra_de_un_fragmento_no_vale(chat, chroma):
    """Fase 3: el modelo tomó el % de toda la muestra de un fragmento. En los conteos solo valen las del cálculo."""
    _fragmento(chroma, "c-2", "Pregunta p02: ¿Tienes dificultades para equilibrar trabajo y estudios?\nEn otra muestra "
               "73.5 % dijo que sí", "4", "pregunta", "p02")
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = "Cumplen la condición 2 de 5 respondentes (40.0 %); en general, 73.5 % [Fuente 1]."
    _, fila = chat["preguntar"]("¿cuántos tienen dificultades para equilibrar trabajo y estudios?", ["4"])
    assert fila.plan["verificacion"]["primer_fallo"] == "cifras_corregidas"
    assert "73.5" not in chat["redacciones"][0]  # en un conteo el fragmento llega sin sus cifras


def test_en_una_entrevista_el_rag_agrega_la_pregunta_que_trata_el_tema(entrevista):
    """Consulta 1676: «¿cuántas sesiones le dieron?» está en una pregunta que no nombra el tema y el plan eligió otra.
    Los intercambios más parecidos de esa persona se suman a la tabla, y el modelo interpreta lo que dijo."""
    entrevista["plan"] = {"intencion": "datos_respondente", "respondentes": ["E02"], "campos": ["p01"]}
    entrevista["redaccion"] = "E02 dice que usa la biblioteca (p02) [Fuente 1]."
    datos, fila = entrevista["preguntar"]("¿Qué servicios usas?", ["3"])
    assert "RAG: se agregó p02 (intercambio más parecido a la pregunta)" in fila.plan["correcciones"]
    assert datos["respuesta"].startswith("E02 dice que usa la biblioteca")
    assert "La biblioteca." in datos["respuesta"]  # la tabla va debajo, con la pregunta recuperada
    assert fila.ruta == "mixta" and "E02 en p02" in [c.get("etiqueta") for c in fila.contexto_usado]


def test_cita_textual_que_la_persona_no_dijo_se_descarta(entrevista):
    entrevista["plan"] = {"intencion": "datos_respondente", "respondentes": ["E02"], "campos": ["p02"]}
    entrevista["redaccion"] = "E02 dijo: «la biblioteca es mi lugar favorito para estudiar» (p02) [Fuente 1]."
    datos, fila = entrevista["preguntar"]("¿Qué servicios usas?", ["3"])
    assert fila.plan["verificacion"]["primer_fallo"] == "cita_inventada"
    assert datos["respuesta"].startswith("Respuestas interpretadas de E02")
    entrevista["redaccion"] = "E02 respondió «La evaluación es con proyectos y rúbricas claras» (p01) [Fuente 1]."
    _, fila = entrevista["preguntar"]("¿Cómo te evalúan tus profesores?", ["3"])
    assert fila.plan["verificacion"]["resultado"] == "aceptada"
    # Una cita real, pero atribuida a otra pregunta (consulta 1695: «durante la pregunta p04», y estaba en p07).
    entrevista["plan"] = {"intencion": "datos_respondente", "respondentes": ["E02"], "campos": ["p01", "p02"]}
    entrevista["redaccion"] = "En p02 E02 dijo «La evaluación es con proyectos y rúbricas claras» [Fuente 1]."
    _, fila = entrevista["preguntar"]("¿Cómo te evalúan tus profesores?", ["3"])
    assert fila.plan["verificacion"]["primer_fallo"] == "cita_inventada"


def test_patrones_de_una_entrevista_salen_del_texto_recuperado(entrevista):
    """Consulta 1681: sin conteos de posturas respondía «No hay resúmenes calculados». Ahora el modelo agrupa en temas
    los intercambios que recupera el RAG, con citas que deben estar en el texto."""
    entrevista["plan"] = {"intencion": "hallazgo"}
    entrevista["redaccion"] = ("- Evaluación: E02 en p01 dice «La evaluación es con proyectos y rúbricas claras» "
                               "[Fuente 1].\n- Servicios: E02 en p02 menciona «La biblioteca» [Fuente 1].")
    datos, fila = entrevista["preguntar"]("¿qué patrones interesantes encuentras?", ["3"])
    assert fila.motivo == "plan:hallazgo" and fila.ruta == "mixta"
    assert "temas o patrones" in entrevista["redacciones"][0] and "TEXTO RECUPERADO" in entrevista["redacciones"][0]
    assert datos["respuesta"].startswith("- Evaluación")


def test_el_seguimiento_recibe_el_tema_de_la_respuesta_anterior(entrevista):
    """Consulta 1676: el historial llegaba como los primeros 300 caracteres de una tabla. Ahora la interpretación
    recibe de qué trató la respuesta anterior (de rag_log) y la redacción la conversación sin tablas."""
    entrevista["plan"] = {"intencion": "datos_respondente", "respondentes": ["E02"], "campos": ["p01"]}
    entrevista["redaccion"] = "E02 dice que la evalúan con proyectos (p01) [Fuente 1]."
    primera, _ = entrevista["preguntar"]("¿Cómo lo evalúan sus profesores?", ["3"])
    historial = [{"rol": "usuario", "texto": "¿Cómo lo evalúan sus profesores?"},
                 {"rol": "asistente", "texto": primera["respuesta"], "consultaId": primera["consultaId"]}]
    entrevista["preguntar"]("¿Y le parece justo?", ["3"], historial)
    prompt_plan, prompt_redaccion = entrevista["interpretaciones"][-1], entrevista["redacciones"][-1]
    assert "TEMA ANTERIOR" in prompt_plan and "Respondentes: E02" in prompt_plan
    assert "| Pregunta |" not in prompt_plan.split("HISTORIAL:")[1]  # el historial va sin tablas
    assert "CONVERSACIÓN PREVIA" in prompt_redaccion and "¿Cómo lo evalúan sus profesores?" in prompt_redaccion
    # Si la consulta anterior no es la del último mensaje del usuario, no se lee.
    historial[0]["texto"] = "otra pregunta"
    entrevista["preguntar"]("¿Y le parece justo?", ["3"], historial)
    assert "TEMA ANTERIOR" not in entrevista["interpretaciones"][-1]


def test_que_significa_eso_retoma_el_plan_de_la_respuesta_anterior(chat):
    """Consultas 1697 y 1702: «y eso, ¿qué puede significar?» recibía una pregunta de aclaración aunque la
    interpretación veía el tema anterior. Se vuelve a calcular el plan anterior y la redacción explica."""
    chat["plan"] = {"intencion": "conteo_porcentaje", "filtros": [{"pregunta": "p02", "valor": "Sí"}]}
    chat["redaccion"] = "Cumplen la condición 2 de 5 respondentes (40.0 %) [Fuente 1]."
    primera, _ = chat["preguntar"]("¿cuántos tienen dificultades para equilibrar trabajo y estudios?", ["4"])
    historial = [{"rol": "usuario", "texto": "¿cuántos tienen dificultades para equilibrar trabajo y estudios?"},
                 {"rol": "asistente", "texto": primera["respuesta"], "consultaId": primera["consultaId"]}]
    chat["plan"] = {"intencion": "aclaracion", "aclaracion": "¿Qué quieres saber?"}
    chat["redaccion"] = "Que 2 de 5 respondentes (40.0 %) tienen dificultades sugiere que les cuesta [Fuente 1]."
    datos, fila = chat["preguntar"]("y eso, ¿qué puede significar?", ["4"], historial)
    assert fila.motivo == "plan:conteo_porcentaje" and datos["respuesta"].startswith("Que 2 de 5")
    assert "aclaración → plan de la respuesta anterior (la pregunta se refiere a ella)" in fila.plan["correcciones"]
    chat["plan"] = {"intencion": "aclaracion", "aclaracion": "¿De qué grupo?"}  # algo nuevo y ambiguo: se aclara
    _, fila = chat["preguntar"]("¿y en el otro grupo?", ["4"], historial)
    assert fila.motivo == "plan:aclaracion"
