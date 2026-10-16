"""Perfil semántico: contenido, fuentes de las preguntas, versiones y permisos."""
from __future__ import annotations

import json

import pytest

from conftest import ADMIN, ANA, LUIS, METADATOS, crear_instrumento, limpieza, texto_dato
from services import estructura, original, perfil

# Palabras que delatan datos técnicos o de respuestas dentro del perfil.
_PROHIBIDO = (
    "valora_tu_experiencia", "que_servicios", "n_respondentes", "pct", "media", "frecuencias", "ruta", "Matrícula", "A03100",
    ".csv", "limpio", "likert", "cuadricula", "tipo_canonico", "Matutino", "Vespertino", "ana@uni.mx", "Ana Pérez",
)


def _preguntas(p: dict) -> list[dict]:
    return [q for s in p["secciones"] for q in s["preguntas"]]


def _perfil(tipo: str, nombre_original: str | None) -> tuple[dict, estructura.Estructura]:
    o = original.leer(texto_dato(nombre_original)) if nombre_original else None
    datos = limpieza(tipo)
    if tipo == "encuesta":
        est = estructura.encuesta(12, datos["reporte"], o)
    elif tipo == "entrevista":
        filas = [dict(zip(datos["csv"]["headers"], f)) for f in datos["csv"]["rows"]]
        est = estructura.entrevista(12, filas, o)
    else:
        est = estructura.prueba(12, datos["reporte"], o)
    return perfil.construir(12, tipo, *METADATOS[tipo], est), est


# ── Encuestas ──────────────────────────────────────────────────────────────────


def test_encuesta_sin_original_usa_encabezados_y_grupos():
    p, est = _perfil("encuesta", None)
    assert p["instrumento_id"] == "INS-0012" and p["tipo"] == "encuesta"
    assert est.fuente == "encabezados" and est.avisos[0]["codigo"] == "sin_original"
    secciones = {s["nombre"]: s for s in p["secciones"]}
    grid = secciones["Valora tu experiencia en la carrera"]["preguntas"]
    assert [q["texto"] for q in grid] == [f"Valora tu experiencia en la carrera: {a}" for a in ("Profesores", "Materiales", "Instalaciones")]
    textos = {q["texto"]: q for q in _preguntas(p)}
    # Opciones solo en categóricas, binarias y de opción múltiple; nunca anclas Likert.
    assert set(textos["¿Cuál es tu principal medio de transporte?"]["opciones"]) == {"Camión", "Metro", "Bicicleta", "Auto"}
    assert "opciones" not in textos["Me siento motivado para continuar mis estudios este semestre"]
    assert all("opciones" not in q for q in grid)
    # Contexto (turno, semestre) y columnas eliminadas (marca temporal, nombre, correo) no entran.
    assert not {"Turno", "Semestre", "Nombre", "Correo", "Marca temporal"} & set(textos)


def test_encuesta_con_original_toma_textos_secciones_y_opciones():
    p, est = _perfil("encuesta", "encuesta_original.txt")
    assert est.fuente == "original"
    secciones = [s["nombre"] for s in p["secciones"]]
    assert secciones[0] == "SECCIÓN 2: EXPERIENCIA EN LA CARRERA"
    assert "SECCIÓN 1: DATOS GENERALES" not in secciones  # solo tenía preguntas de contexto
    textos = [q["texto"] for q in _preguntas(p)]
    assert "¿Cuál es tu principal medio de transporte para llegar a la universidad?" in textos  # texto completo
    assert "Valora tu experiencia en la carrera en los siguientes aspectos: Profesores" in textos
    assert "¿Recomendarías la universidad a un amigo?" in textos  # del original aunque no esté en el archivo
    assert not any(t.startswith("Turno") or t.startswith("Semestre") for t in textos)
    # Abierta en el original: no se listan como opciones las respuestas observadas.
    abierta = next(q for q in _preguntas(p) if q["texto"] == "¿Qué mejorarías de tu carrera?")
    assert "opciones" not in abierta
    # La columna que no está en el original se conserva con su encabezado, con aviso.
    assert "Idioma" in textos and est.avisos[0]["codigo"] == "preguntas_sin_original"


@pytest.mark.parametrize("nombre_original", [None, "encuesta_original.txt"])
def test_perfil_sin_datos_tecnicos_ni_duplicados(nombre_original):
    p, _ = _perfil("encuesta", nombre_original)
    texto = json.dumps(p, ensure_ascii=False)
    for palabra in _PROHIBIDO:
        assert palabra not in texto, palabra
    textos = [q["texto"] for q in _preguntas(p)]
    ids = [q["id"] for q in _preguntas(p)]
    assert len(textos) == len(set(textos)) and len(ids) == len(set(ids))
    assert set(p) == {
        "esquema_version", "instrumento_id", "tipo", "titulo", "objetivo", "temas", "palabras_clave",
        "nivel_educativo", "poblacion", "contexto", "secciones", "kpis_asociados",
    }


def test_campos_descriptivos_desde_los_metadatos():
    p, _ = _perfil("encuesta", None)
    assert p["titulo"] == "Experiencia estudiantil 2026"
    assert p["objetivo"].startswith("Conocer la satisfacción")
    assert p["temas"] == ["experiencia estudiantil", "satisfacción", "Docencia", "Infraestructura", "Satisfacción académica"]
    assert p["palabras_clave"] == ["satisfacción", "carrera"]
    assert p["nivel_educativo"] == "Licenciatura" and p["poblacion"] == "Estudiantes de licenciatura"
    assert p["contexto"].startswith("Institución: Universidad Ejemplo. Carrera(s): Pedagogía.")


def test_nivel_educativo_por_palabras_clave():
    assert perfil.nivel_educativo({"dc_coverage": "Maestría en Educación"}, {}) == "Posgrado"
    assert perfil.nivel_educativo({"dc_coverage": "Educación media superior"}, {}) == "Media superior"
    assert perfil.nivel_educativo({}, {"nivel_educativo": "Secundaria"}) == "Secundaria"
    assert perfil.nivel_educativo({}, {}) == perfil.NO_ESPECIFICADO


# ── Entrevistas y pruebas ──────────────────────────────────────────────────────


def test_entrevista_preguntas_del_entrevistador_o_del_guion():
    p, est = _perfil("entrevista", None)
    textos = [q["texto"] for q in _preguntas(p)]
    assert len(textos) == 3 and textos[1] == "¿Y qué opinas de la retroalimentación que recibes de tus profesores?"
    assert est.avisos[-1]["codigo"] == "sin_original"
    p, est = _perfil("entrevista", "entrevista_guion.txt")
    assert [s["nombre"] for s in p["secciones"]] == ["BLOQUE 1: EVALUACIÓN", "BLOQUE 2: PLAN DE ESTUDIOS"]
    assert _preguntas(p)[0]["texto"] == "¿Cómo ha sido tu experiencia con la evaluación en tus materias?"
    assert "Ana" not in json.dumps(p, ensure_ascii=False)  # el perfil no tiene respuestas


def test_prueba_reactivos_con_texto_y_opciones_del_original():
    p, est = _perfil("prueba_estandarizada", "prueba_original.txt")
    reactivos = _preguntas(p)
    assert [q["id"] for q in reactivos] == [f"INS-0012-r0{i}" for i in range(1, 6)]
    assert reactivos[0]["texto"] == "¿Cuánto es 7 × 8?" and reactivos[0]["opciones"][0] == "A) 56"
    assert [s["nombre"] for s in p["secciones"]] == ["PARTE I: ARITMÉTICA", "PARTE II: ÁLGEBRA"]
    assert "respuesta" not in json.dumps(p) and est.preguntas[2].columna == "P3"  # la clave no se publica


def test_prueba_sin_original():
    p, est = _perfil("prueba_estandarizada", None)
    assert [q["texto"] for q in _preguntas(p)][:2] == ["Reactivo P1", "Reactivo P2"]
    assert all("opciones" not in q for q in _preguntas(p)) and est.avisos[0]["codigo"] == "sin_original"


# ── Lectura del original ───────────────────────────────────────────────────────


def test_lectura_del_original():
    texto = (
        "PARTE 1: HÁBITOS\n"
        "P1. ¿Con qué frecuencia lees por gusto?\n"
        "1 = Nunca, 3 = A veces, 5 = Siempre\n"
        "Reactivo 2: Elige la opción correcta\n"
        "(a) Uno\n(b) Dos\n"
        "• Tres\n"
        "¿Algo más que quieras agregar?\n"
    )
    o = original.leer(texto)
    assert [p.texto for p in o.preguntas] == ["¿Con qué frecuencia lees por gusto?", "Elige la opción correcta", "¿Algo más que quieras agregar?"]
    assert o.preguntas[0].seccion == "PARTE 1: HÁBITOS" and o.preguntas[0].numero == 1
    assert o.preguntas[0].anclas == {1: "Nunca", 3: "A veces", 5: "Siempre"}
    assert o.preguntas[1].opciones == [("A", "Uno"), ("B", "Dos"), (None, "Tres")]
    assert original.anclas_de("Escala de 1 (Nada) a 5 (Mucho)") == {1: "Nada", 5: "Mucho"}


def test_parecido_tolera_encabezados_truncados():
    completo = "¿Con qué frecuencia utilizas la biblioteca de tu facultad para estudiar?"
    assert original.parecido("¿Con qué frecuencia utilizas la biblioteca…", completo) >= original.UMBRAL_PARECIDO
    assert original.parecido("Edad", completo) < original.UMBRAL_PARECIDO


# ── API ────────────────────────────────────────────────────────────────────────


def test_vista_previa_con_los_metadatos_del_formulario(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, original="encuesta_original.txt")
    dc, esp = METADATOS["encuesta"]
    cuerpo = {"dublin_core": dc, "enriquecidos": dict(esp, palabras_clave="satisfacción, carrera", dimensiones="Docencia")}
    r = cliente.post(f"/conocimiento/{id_crudo}/perfil/vista-previa", json=cuerpo, headers=ANA)
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["fuente"] == "original" and datos["n_preguntas"] == 10
    assert datos["perfil"]["palabras_clave"] == ["satisfacción", "carrera"]  # listas como texto con comas
    assert datos["avisos"][0]["codigo"] == "preguntas_sin_original"


def test_generar_perfil_crea_versiones(cliente, db, storage):
    from shared.models.version_conocimiento import VersionConocimiento

    id_crudo = crear_instrumento(db, storage, aprobado=True)
    r1 = cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    assert r1.status_code == 200, r1.text
    assert (r1.json()["version"], r1.json()["estado"]) == (1, "perfil_aprobado")
    r2 = cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA)
    assert r2.json()["version"] == 2
    estados = {v.version: v.estado for v in db.query(VersionConocimiento).filter_by(id_crudo=id_crudo)}
    assert estados == {1: "reemplazado", 2: "perfil_aprobado"}
    fila = db.query(VersionConocimiento).filter_by(id_crudo=id_crudo, version=2).one()
    assert fila.id_limpieza is not None and fila.id_usuario == 2 and fila.decisiones_kpi == []
    g = cliente.get(f"/conocimiento/{id_crudo}/perfil", headers=ANA).json()
    assert g["version"] == 2 and g["fuente"] == "encabezados" and g["perfil"]["titulo"] == "Experiencia estudiantil 2026"


def test_generar_exige_metadatos_aprobados_y_autoria(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage)
    assert cliente.post(f"/conocimiento/{id_crudo}/perfil", headers=ANA).status_code == 409
    assert cliente.post(f"/conocimiento/{id_crudo}/perfil/vista-previa", json={}, headers=LUIS).status_code == 403
    assert cliente.post(f"/conocimiento/{id_crudo}/perfil/vista-previa", json={}, headers=ADMIN).status_code == 200
    assert cliente.get(f"/conocimiento/{id_crudo}/perfil", headers=ANA).status_code == 404
    assert cliente.get("/conocimiento/999/perfil", headers=ANA).status_code == 404


def test_instrumento_anterior_a_la_limpieza_usa_el_json_tecnico(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, con_limpieza=False)
    r = cliente.post(f"/conocimiento/{id_crudo}/perfil/vista-previa", json={}, headers=ANA)
    assert r.status_code == 409  # sin limpieza ni JSON técnico
    storage.jsons[(id_crudo, "metadata")] = {
        "instrument": {"sections": [{"name": "Reactivos", "questions": [
            {"question_id": "q1", "text": "¿Te gusta leer?", "type": "binaria", "options": ["Sí", "No"]},
            {"question_id": "q2", "text": "Satisfacción con la biblioteca", "type": "likert", "options": ["Poco", "Mucho"]},
        ]}]}
    }
    datos = cliente.post(f"/conocimiento/{id_crudo}/perfil/vista-previa", json={}, headers=ANA).json()
    preguntas = _preguntas(datos["perfil"])
    assert datos["fuente"] == "json_tecnico" and preguntas[0]["opciones"] == ["Sí", "No"]
    assert "opciones" not in preguntas[1]  # anclas Likert fuera
    assert datos["perfil"]["titulo"] == "Instrumento sin título"


def test_storage_caido_responde_503(cliente, db, storage):
    id_crudo = crear_instrumento(db, storage, tipo="entrevista")
    storage.caido = True
    assert cliente.post(f"/conocimiento/{id_crudo}/perfil/vista-previa", json={}, headers=ANA).status_code == 503


def test_health(cliente):
    assert cliente.get("/health").json() == {"status": "ok", "service": "knowledge-service"}


def test_encabezados_codificados_se_emparejan_por_seccion_y_posicion():
    # Caso real: el archivo trae «Prefijo_de_secc_itemN» y el original, las preguntas completas.
    columnas = [
        {"id": f"h{i}", "etiqueta": f"Habitos_de_lect_item{i}", "rol": "pregunta", "tipo_canonico": "likert"} for i in (1, 2)
    ] + [{"id": "e1", "etiqueta": "Estrategias_cog_item1", "rol": "pregunta", "tipo_canonico": "likert"}]
    reporte = {"especifico": {"encuesta": {"columnas": columnas}}}
    texto = (
        "--- HÁBITOS DE LECTURA ---\n1. Leo todos los días.\n2. Leo antes de dormir.\n"
        "--- ESTRATEGIAS COGNITIVAS ---\n3. Hago resúmenes de lo que leo.\n"
    )
    est = estructura.encuesta(7, reporte, original.leer(texto))
    assert [(p.texto, p.columna) for p in est.preguntas] == [
        ("Leo todos los días.", "h1"), ("Leo antes de dormir.", "h2"), ("Hago resúmenes de lo que leo.", "e1"),
    ]
    assert [s.nombre for s in est.secciones] == ["HÁBITOS DE LECTURA", "ESTRATEGIAS COGNITIVAS"]
    assert est.avisos == []  # todas las columnas encontraron su pregunta: sin duplicados


def test_contexto_sin_metricas_de_las_notas_automaticas():
    notas = "Calidad de los datos: 20 registros con respuesta; 3% de respuestas vacías. Aplicada al cierre del semestre."
    assert perfil.sin_metricas(notas) == "Aplicada al cierre del semestre"
    ctx = perfil.contexto("encuesta", {"dc_publisher": "UNAM"}, {"notas_contextuales": notas})
    assert ctx == "Institución: UNAM. Notas: Aplicada al cierre del semestre"
    assert perfil.contexto("encuesta", {}, {"notas_contextuales": "20 registros con respuesta"}) == ""


def test_escala_general_de_las_instrucciones_y_secciones_con_el_mismo_inicio():
    # Caso real (MSLQ): la escala está en las instrucciones, y dos secciones empiezan igual.
    texto = (
        "INSTRUCCIONES:\nUsa la siguiente escala:\n"
        "  1 = Totalmente en desacuerdo / Nunca\n  2 = En desacuerdo\n  3 = Neutral\n  4 = De acuerdo\n  5 = Totalmente de acuerdo / Siempre\n"
        "--- ELABORACIÓN ---\n1. Relaciono lo que leo con lo que ya sé.\n2. Elaboro mis propios ejemplos.\n"
        "--- ELABORACIÓN CON COMPAÑEROS ---\n3. Estudio con otros estudiantes.\n"
    )
    o = original.leer(texto)
    assert o.anclas_globales == {1: "Totalmente en desacuerdo / Nunca", 2: "En desacuerdo", 3: "Neutral",
                                 4: "De acuerdo", 5: "Totalmente de acuerdo / Siempre"}
    columnas = [{"id": f"e{i}", "etiqueta": f"Elaboración_item{i}", "rol": "pregunta", "tipo_canonico": "likert"} for i in (1, 2)]
    est = estructura.encuesta(7, {"especifico": {"encuesta": {"columnas": columnas}}}, o)
    con_columna = [p for p in est.preguntas if p.columna]
    assert [(p.texto, p.columna) for p in con_columna] == [
        ("Relaciono lo que leo con lo que ya sé.", "e1"), ("Elaboro mis propios ejemplos.", "e2")]
    assert con_columna[0].anclas[1] == "Totalmente en desacuerdo / Nunca"  # escala general aplicada
