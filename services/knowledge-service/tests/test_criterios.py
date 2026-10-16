"""Documento final: construcción desde archivos de ejemplo, validación con JSON Schema y
criterios de aceptación respondidos con consultas determinísticas (sin LLM).

Los archivos de ejemplo pasan por los motores REALES de cleaning-service
(`tests/datos/generar_limpiezas.py`). Cada valor esperado se calcula aquí de forma
independiente, directamente del CSV limpio, para no validar el documento consigo mismo.
"""
from __future__ import annotations

import copy
import json
import re

import pytest

from conftest import METADATOS, limpieza, texto_dato
from services import consultas, documento, estructura, original, perfil

ACUERDO = ["Totalmente en desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo", "De acuerdo", "Totalmente de acuerdo"]


def _kpi(ref: str, nombre: str, evidencia: list[str]) -> dict:
    return {
        "kpi_id": ref, "nombre": nombre, "definicion": f"El KPI {nombre} mide…", "dimension": "Aumentar / Mejorar",
        "que_mide": f"Mide {nombre.lower()}.", "similitud": 0.61,
        "evidencia": [{"pregunta_id": f"INS-0012-{e}", "similitud": 0.55} for e in evidencia],
        "justificacion": f"Las preguntas citadas miden aspectos de {nombre.lower()}.", "justificacion_origen": "llm_revisada",
        "aceptado_por": "Ana", "fecha": "2026-10-15T10:00:00+00:00",
    }


KPIS = {
    "encuesta": [_kpi("KPI-07", "Satisfacción estudiantil", ["p01", "p02"])],
    "prueba_estandarizada": [_kpi("KPI-03", "Dominio de álgebra", ["r04", "r05"])],
    "entrevista": [_kpi("KPI-05", "Retroalimentación docente", ["p02"])],
    "entrevista_bloques": [_kpi("KPI-11", "Servicios de apoyo", ["p03"])],
}
ORIGINALES = {"encuesta": "encuesta_original.txt", "prueba_estandarizada": "prueba_original.txt", "entrevista": "entrevista_guion.txt",
              "entrevista_bloques": "entrevista_bloques_guion.txt"}


def construir(tipo: str, con_original: bool = True) -> dict:
    datos = limpieza(tipo)
    filas = [dict(zip(datos["csv"]["headers"], f)) for f in datos["csv"]["rows"]]
    o = original.leer(texto_dato(ORIGINALES[tipo])) if con_original else None
    if tipo == "encuesta":
        est = estructura.encuesta(12, datos["reporte"], o)
    elif tipo.startswith("entrevista"):
        est = estructura.entrevista(12, filas, o)
    else:
        est = estructura.prueba(12, datos["reporte"], o)
    base = "entrevista" if tipo.startswith("entrevista") else tipo
    p = perfil.construir(12, base, *METADATOS[base], est)
    p["kpis_asociados"] = copy.deepcopy(KPIS[tipo])
    return documento.construir(p, est, datos["reporte"], filas)


@pytest.fixture(scope="module")
def enc() -> dict:
    return construir("encuesta")


@pytest.fixture(scope="module")
def pru() -> dict:
    return construir("prueba_estandarizada")


@pytest.fixture(scope="module")
def ent() -> dict:
    return construir("entrevista")


@pytest.fixture(scope="module")
def bloques() -> dict:
    return construir("entrevista_bloques")


def _csv(tipo: str) -> list[dict]:
    datos = limpieza(tipo)
    return [dict(zip(datos["csv"]["headers"], f)) for f in datos["csv"]["rows"]]


# ── Esquema y principios ───────────────────────────────────────────────────────


@pytest.mark.parametrize("tipo", ["encuesta", "prueba_estandarizada", "entrevista", "entrevista_bloques"])
@pytest.mark.parametrize("con_original", [True, False])
def test_los_tres_tipos_cumplen_su_json_schema(tipo, con_original):
    doc = construir(tipo, con_original)
    assert documento.esquema.errores(doc) == []
    version = "2.0" if tipo.startswith("entrevista") else "1.0"
    assert doc["esquema_version"] == version and doc["instrumento"]["id"] == "INS-0012"


def test_documento_invalido_se_rechaza(enc):
    malo = copy.deepcopy(enc)
    malo["respondentes"][0]["id"] = "R001"  # sin prefijo del instrumento
    del malo["preguntas"][0]["resumen"]
    with pytest.raises(documento.DocumentoInvalido) as exc:
        documento.validar(malo)
    assert "respondentes/0/id" in str(exc.value) and "resumen" in str(exc.value)


def test_cada_respuesta_una_sola_vez_y_ninguna_omitida(enc):
    con_columna = [p["id"] for p in enc["preguntas"] if p["tipo"] != "sin_datos"]
    assert len(enc["respondentes"]) == 20 == enc["instrumento"]["n_respondentes"]
    for r in enc["respondentes"]:
        ids = [x["pregunta_id"] for x in r["respuestas"]]
        assert ids == con_columna  # una por pregunta, en orden, sin repetir ni omitir
    # Las preguntas NO repiten respuestas: solo definición y resumen.
    assert all("respuestas" not in p for p in enc["preguntas"])


def test_sin_datos_personales_en_ningun_tipo(enc, pru, ent):
    filas = list(__import__("csv").reader(texto_dato("encuesta.csv").splitlines()))
    nombres = [f[1] for f in filas[1:]]
    correos = [f[2] for f in filas[1:]]
    matriculas = [f[3] for f in filas[1:]]
    texto = json.dumps(enc, ensure_ascii=False)
    for dato in nombres + correos + matriculas:
        assert dato not in texto, dato
    sin_avisos = json.dumps({k: v for k, v in enc.items() if k != "avisos"}, ensure_ascii=False)
    assert "Matrícula" not in sin_avisos  # ni como pregunta ni como contexto (solo se nombra en el aviso)
    aviso = next(a for a in enc["avisos"] if a["codigo"] == "datos_personales_excluidos")
    assert "Matrícula" in aviso["mensaje"]
    for f in _csv("prueba_estandarizada"):
        assert f["id_alumno"] not in json.dumps(pru)
    # (`aceptado_por` de los KPIs es la investigadora, no una participante.)
    texto_ent = json.dumps(ent["entrevistas"], ensure_ascii=False)
    assert not re.search(r"\b(Ana|Beto)\b", texto_ent)


def test_resumen_precalculado_con_plantilla(enc):
    p = consultas.pregunta(enc, texto="Profesores")
    res = p["resumen"]
    assert p["tipo"] == "cuadricula" and p["escala"]["niveles"] == {"desacuerdo": [1, 2], "neutral": [3], "acuerdo": [4, 5]}
    assert sum(d["n"] for d in res["distribucion"]) == res["n_validas"]
    assert pytest.approx(sum(res["por_nivel"].values()), abs=0.2) == 100
    assert [d["significado"] for d in res["distribucion"]] == [e for e in ACUERDO if e in {d["significado"] for d in res["distribucion"]}]
    nivel, valor = max(res["por_nivel"].items(), key=lambda x: x[1])
    if valor > 50:
        assert res["interpretacion"].startswith("Predomina")
    motivado = consultas.pregunta(enc, texto="motivado")["resumen"]
    assert motivado["sin_respuesta_por_motivo"] == {"no_sabe": 1, "en_blanco": 1}  # «No sé» ≠ celda vacía
    sin_datos = consultas.pregunta(enc, texto="Recomendarías")
    assert sin_datos["tipo"] == "sin_datos" and sin_datos["resumen"]["n_validas"] == 0


def test_relacion_kpi_pregunta_en_ambos_sentidos(enc, pru, ent):
    kpi = enc["kpis_asociados"][0]
    for e in kpi["evidencia"]:
        assert "KPI-07" in consultas.pregunta(enc, pregunta_id=e["pregunta_id"])["kpis_relacionados"]
    assert [r["id"] for r in pru["reactivos"] if "KPI-03" in r["kpis_relacionados"]] == ["INS-0012-r04", "INS-0012-r05"]
    guia = next(g for g in ent["preguntas"] if g["id"] == "INS-0012-p02")
    assert guia["kpis_relacionados"] == ["KPI-05"]
    intercambios = [i for e in ent["entrevistas"] for i in e["intercambios"] if i.get("pregunta_id") == "INS-0012-p02"]
    assert intercambios and all("retroalimentación" in i["pregunta"] for i in intercambios)


# ── Criterios de aceptación ────────────────────────────────────────────────────


def test_criterio_1_que_respondio_un_respondente(enc):
    r = consultas.respuesta(enc, "R001", texto="Profesores")
    assert r["significado"] == "En desacuerdo" and r["nivel"] == "desacuerdo" and r["valor"] == 2
    no_se = consultas.respuesta(enc, "R008", texto="motivado")
    assert no_se["estado"] == "sin_respuesta" and no_se["motivo"] == "no_sabe" and no_se["significado"] == "No sé"
    transporte = consultas.respuesta(enc, "R003", texto="transporte")
    assert transporte["significado"] == _csv("encuesta")[2]["cual_es_tu_principal_medio_de_transporte"]


def test_criterio_2_respondente_en_desacuerdo_en_varias_o_ninguno(enc):
    preguntas = ["p01", "p02", "p03"]
    columnas = ["valora_tu_experiencia_en_la_carrera_prof", "valora_tu_experiencia_en_la_carrera_mate", "valora_tu_experiencia_en_la_carrera_inst"]
    esperados = [i for i, f in enumerate(_csv("encuesta")) if all(f[c] in ("1", "2") for c in columnas)]
    encontrado = consultas.respondente_con_nivel(enc, preguntas, "desacuerdo")
    assert esperados and encontrado == f"INS-0012-R{esperados[0] + 1:03d}" == "INS-0012-R001"
    # Sin distinguir «En desacuerdo» de «Totalmente en desacuerdo»: R001 tiene ambas.
    assert {consultas.respuesta(enc, "R001", pregunta_id=p)["significado"] for p in preguntas} == {"En desacuerdo", "Totalmente en desacuerdo"}
    # Caso negativo: nadie es neutral en las cuatro escalas → se confirma que no existe.
    assert consultas.respondente_con_nivel(enc, ["p01", "p02", "p03", "p04"], "neutral") is None


def test_criterio_3_porcentaje_de_un_grupo_de_acuerdo(enc):
    filas = [f for f in _csv("encuesta") if f["turno"] == "Vespertino"]
    validas = [f["me_siento_motivado_para_continuar_mis_es"] for f in filas if f["me_siento_motivado_para_continuar_mis_es"] in "12345" and f["me_siento_motivado_para_continuar_mis_es"]]
    esperado = round(100 * sum(1 for v in validas if v in ("4", "5")) / len(validas), 1)
    assert consultas.pct_nivel(enc, "p04", "acuerdo", {"Turno": "Vespertino"}) == esperado
    assert consultas.pct_nivel(enc, "p04", "acuerdo", {"Turno": "Nocturno"}) is None


def test_criterio_4_por_que_el_kpi_y_que_mide(enc):
    info = consultas.info_kpi(enc, "KPI-07")
    assert info["definicion"] and info["que_mide"] and info["justificacion"] and info["dimension"]
    assert [e["texto"] for e in info["evidencia"]] == [
        "Valora tu experiencia en la carrera en los siguientes aspectos: Profesores",
        "Valora tu experiencia en la carrera en los siguientes aspectos: Materiales",
    ]
    assert all(e["resumen"]["distribucion"] and e["resumen"]["interpretacion"] for e in info["evidencia"])


def test_criterio_5_preguntas_que_miden_un_kpi_y_como_respondieron(enc):
    preguntas = consultas.preguntas_de_kpi(enc, "KPI-07")
    assert [p["pregunta_id"] for p in preguntas] == ["INS-0012-p01", "INS-0012-p02"]
    columna = "valora_tu_experiencia_en_la_carrera_prof"
    esperado = sum(1 for f in _csv("encuesta") if f[columna] in ("4", "5"))
    dist = {d["significado"]: d["n"] for d in preguntas[0]["resumen"]["distribucion"]}
    assert dist.get("De acuerdo", 0) + dist.get("Totalmente de acuerdo", 0) == esperado


def test_criterio_6_reactivo_mas_dificil_y_alumnos_que_fallaron(pru):
    filas = [f for f in _csv("prueba_estandarizada") if f["motivo"] != "duplicado"]
    por_reactivo: dict[str, list[dict]] = {}
    for f in filas:
        por_reactivo.setdefault(f["pregunta"], []).append(f)
    pct = {p: round(100 * sum(f["correcta"] == "1" for f in fs) / len(fs), 1) for p, fs in por_reactivo.items()}
    peor = min(pct, key=lambda p: (pct[p], p))
    res = consultas.reactivo_mas_dificil(pru)
    assert res["pct_acierto"] == pct[peor] and res["reactivo_id"] == f"INS-0012-r0{peor[1:]}"
    erradas = [f["respuesta"] for f in por_reactivo[peor] if f["estado"] == "valida" and f["correcta"] == "0"]
    if erradas:
        mas = max(sorted(set(erradas)), key=erradas.count)
        assert res["distractor_mas_elegido"]["opcion"] == mas
    assert res["texto"]  # texto real del reactivo (del original)

    fallaron = consultas.alumnos_que_fallaron_kpi(pru, "KPI-03")
    orden = list(dict.fromkeys(f["id_alumno"] for f in filas))  # A001… en orden de aparición
    for clave, reactivo in (("P4", "INS-0012-r04"), ("P5", "INS-0012-r05")):
        esperado = [f"INS-0012-A{orden.index(f['id_alumno']) + 1:03d}" for f in por_reactivo[clave] if f["correcta"] != "1"]
        assert fallaron[reactivo] == esperado
    alumno = pru["alumnos"][0]
    assert alumno["total"] == 5 and alumno["puntaje"] == sum(r["correcta"] for r in alumno["respuestas"])
    assert alumno["contexto"] == {"turno": "Matutino"}
    assert pru["reactivos"][0]["opciones"]["A"] == "56"


def test_criterio_7_que_dijo_un_participante_sobre_un_tema(ent):
    dicho = consultas.dijo(ent, "E02", "retroalimentación")
    assert len(dicho) == 1
    assert dicho[0]["respuesta"] == "Casi nunca recibo retroalimentación a tiempo, eso me frustra mucho."
    assert dicho[0]["pregunta"] == "¿Y qué opinas de la retroalimentación que recibes de tus profesores?"
    # Turnos consecutivos del mismo hablante se unen en una sola respuesta.
    e01 = consultas.dijo(ent, "E01", "evaluación")
    assert e01[0]["respuesta"].endswith("Preferiría más proyectos.")
    # La misma pregunta respondida por dos participantes: un intercambio para cada uno.
    plan = [i for e in ent["entrevistas"] for i in e["intercambios"] if i["pregunta"] == "¿Qué cambiarías del plan de estudios?"]
    assert len(plan) == 2 and {i["pregunta_id"] for i in plan} == {"INS-0012-p03"}
    assert consultas.dijo(ent, "E09", "evaluación") == []


def test_cada_respuesta_lleva_el_texto_de_su_pregunta(enc, pru):
    textos = {p["id"]: p["texto"] for p in enc["preguntas"]}
    for x in enc["respondentes"][0]["respuestas"]:
        assert x["pregunta"] == textos[x["pregunta_id"]]
    reactivos = {r["id"]: r["texto"] for r in pru["reactivos"]}
    assert all(x["pregunta"] == reactivos[x["reactivo_id"]] for x in pru["alumnos"][0]["respuestas"])


def test_prueba_sin_clave_con_reactivos_no_calificables():
    """Sintético real (pru_04): opción múltiple + escala 1–5 + Sí/No, con clave propuesta."""
    datos = limpieza("prueba_sin_clave")
    filas = [dict(zip(datos["csv"]["headers"], f)) for f in datos["csv"]["rows"]]
    est = estructura.prueba(12, datos["reporte"], original.leer(texto_dato("pru_04_original.txt")))
    p = perfil.construir(12, "prueba_estandarizada", *METADATOS["prueba_estandarizada"], est)
    doc = documento.construir(p, est, datos["reporte"], filas)
    assert documento.esquema.errores(doc) == []
    tipos = [r["tipo_reactivo"] for r in doc["reactivos"]]
    assert tipos.count("opcion_multiple") == 6 and tipos.count("escala") == 8 and tipos.count("si_no") == 4
    escala = next(r for r in doc["reactivos"] if r["tipo_reactivo"] == "escala")
    assert escala["calificable"] is False and escala["respuesta_correcta"] == "" and escala["resumen"]["pct_acierto"] is None
    assert escala["resumen"]["interpretacion"].startswith("Media") and "no calificable" in escala["resumen"]["interpretacion"]
    assert any(a["codigo"] == "clave_inferida" for a in doc["avisos"])
    alumno = doc["alumnos"][0]
    assert alumno["total"] == 6  # solo los reactivos calificables cuentan en el puntaje
    r_escala = next(x for x in alumno["respuestas"] if x["reactivo_id"] == escala["id"])
    assert "correcta" not in r_escala and r_escala["significado"].endswith("en escala 1–5")
    r_sino = next(x for x in alumno["respuestas"] if x["reactivo_id"] == next(r["id"] for r in doc["reactivos"] if r["tipo_reactivo"] == "si_no"))
    assert r_sino["significado"] in ("Sí", "No")
    assert "score_estimado" in alumno["contexto"]
    # El reactivo más difícil solo se busca entre los calificables.
    assert consultas.reactivo_mas_dificil(doc)["pct_acierto"] is not None


# ── Entrevistas: solo pregunta y respuesta ─────────────────────────────────────


def test_entrevista_solo_texto_sin_estadisticas(ent, bloques):
    for doc in (ent, bloques):
        assert set(doc) == {"esquema_version", "instrumento", "kpis_asociados", "preguntas", "entrevistas", "avisos"}
        assert not any(k.startswith("n_") for k in doc["instrumento"])
        for e in doc["entrevistas"]:
            assert set(e) == {"participante", "intercambios"}
            for i in e["intercambios"]:
                assert set(i) <= {"pregunta_id", "pregunta", "respuesta"} and i["respuesta"]


def test_entrevista_con_bloques_de_respondentes(bloques):
    """Formato ent_01: «RESPONDENTE: R0001» + P1/R. Una entrevista por bloque, en orden."""
    filas = _csv("entrevista_bloques")
    assert [e["participante"] for e in bloques["entrevistas"]] == ["INS-0012-E01", "INS-0012-E02", "INS-0012-E03"]
    assert [g["texto"] for g in bloques["preguntas"]] == [
        "¿Qué factores te han ayudado a continuar tus estudios?",
        "¿Has pensado en abandonar la universidad?",
        "¿Qué servicios de apoyo institucional has utilizado?",
    ]
    e01 = bloques["entrevistas"][0]["intercambios"]
    assert [i["pregunta_id"] for i in e01] == ["INS-0012-p01", "INS-0012-p02", "INS-0012-p03"]
    assert e01[1]["respuesta"] == "Sí, en el primer semestre, pero el orientador me ayudó a reorganizarme."
    # R0002 dejó P2 sin respuesta: no hay intercambio vacío.
    assert [i["pregunta_id"] for i in bloques["entrevistas"][1]["intercambios"]] == ["INS-0012-p01", "INS-0012-p03"]
    # Ni el ID del bloque ni el contexto (edad, género…) llegan al documento.
    texto = json.dumps(bloques, ensure_ascii=False)
    assert "R0001" not in texto and "Edad" not in texto and "masculino" not in texto
    respuestas = [f["texto"] for f in filas if f["rol"] == "entrevistado"]
    assert sorted(respuestas) == sorted(i["respuesta"] for e in bloques["entrevistas"] for i in e["intercambios"])
    servicios = consultas.preguntas_de_kpi(bloques, "KPI-11")
    assert [p["pregunta_id"] for p in servicios] == ["INS-0012-p03"]
    assert consultas.dijo(bloques, "E02", "tutorías")[0]["respuesta"] == "Ninguno, no sabía que existían las tutorías."
