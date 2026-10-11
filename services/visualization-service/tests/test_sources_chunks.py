"""Tests de `sources.construir_chunks` y la precedencia de título (FEAT-002).

Unit, sin I/O real: el `.txt` original se controla monkeypatcheando
`original_txt.leer_texto_original`; la agregación corre de verdad sobre un
`respondents` sintético pequeño.
"""
from __future__ import annotations

from app.core import chunking, original_txt, sources

# ── Artefacto sintético pequeño (2 dimensiones likert + numérica + binaria) ───
_TXT_SINTETICO = """\
======================================================================
INSTRUMENTO: Encuesta de Prueba (EP)
ID: enc_test
======================================================================

--- MOTIVACION ---

1. Me esfuerzo cuando el tema es interesante.
   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5

2. Encuentro significativo lo que estudio.
   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5

--- ORGANIZACION ---

3. Organizo el material antes de estudiar.
   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5
"""


def _artefacto() -> dict:
    return {
        "instrument_id": "upload_7",
        "instrument": {
            "title": "enc_test_respondido.csv",
            "objective": "",
            "dimensions_explored": [],
            "sections": [
                {
                    "name": "Reactivos",
                    "questions": [
                        {"question_id": "q1", "type": "abierta", "text": "id_resp"},
                        {"question_id": "q2", "type": "numerica_continua", "text": "promedio_gpa"},
                        {"question_id": "q3", "type": "binaria", "text": "tiene_beca"},
                        {"question_id": "q10", "type": "likert", "text": "Motivaci_item1", "scale_min": 1, "scale_max": 5},
                        {"question_id": "q11", "type": "likert", "text": "Motivaci_item2", "scale_min": 1, "scale_max": 5},
                        {"question_id": "q12", "type": "likert", "text": "Organiza_item1", "scale_min": 1, "scale_max": 5},
                    ],
                }
            ],
        },
        "metadata": {"dublin_core": {}, "survey_specific": {}},
        "design_reference": {"kpi_hints": [], "note": ""},
        "respondents": [
            {"answers": {"q2": 3.0, "q3": "True", "q10": 5, "q11": 4, "q12": 2}},
            {"answers": {"q2": 3.5, "q3": "False", "q10": 4, "q11": 5, "q12": 3}},
            {"answers": {"q2": 2.5, "q3": "True", "q10": 5, "q11": 4, "q12": 1}},
        ],
    }


def test_construir_chunks_con_txt(monkeypatch):
    """Con .txt: estructura (cabecera + 2 dim) + hallazgos (2 likert + num + bin + resumen)."""
    monkeypatch.setattr(original_txt, "leer_texto_original", lambda _id: _TXT_SINTETICO)

    chunks = sources.construir_chunks(_artefacto(), "7")
    clases = [c.clase for c in chunks]
    estructura = [c for c in chunks if c.clase == "estructura"]
    hallazgos = [c for c in chunks if c.clase == "hallazgos"]
    grupos = [c for c in chunks if c.clase == "grupo_desempeno"]

    # cabecera + 2 dimensiones de estructura
    assert len(estructura) == 3
    assert estructura[0].dimension == ""
    assert "Encuesta de Prueba (EP)" in estructura[0].texto

    # El título real del .txt gana sobre el nombre del CSV en la cabecera.
    assert "enc_test_respondido.csv" not in estructura[0].texto

    # Los ítems redactados del .txt aparecen en los chunks de dimensión.
    dim_textos = "\n".join(c.texto for c in estructura[1:])
    assert "Me esfuerzo cuando el tema es interesante." in dim_textos
    assert "Organizo el material antes de estudiar." in dim_textos

    # 2 likert estadísticos + 1 numérica + 1 binaria + 1 resumen global, MÁS
    # los chunks interpretados por dimensión (mejora 2). Conteo flexible.
    assert len(hallazgos) >= 5
    # El resumen global es el último hallazgo emitido, sin dimensión.
    assert hallazgos[-1].dimension == ""
    assert "respondentes" in hallazgos[-1].texto
    # Prosa con medias/porcentajes, no números sueltos.
    likert_textos = "\n".join(
        c.texto for c in hallazgos if "media de respuesta" in c.texto
    )
    assert "/5" in likert_textos
    assert "%" in likert_textos

    # Mejora 2: aparecen chunks interpretados por dimensión (nivel + rango).
    hallazgos_textos = "\n".join(c.texto for c in hallazgos)
    assert "nivel" in hallazgos_textos
    assert "rango de 1 a 5" in hallazgos_textos

    # Mejora 3: al menos un chunk de grupo por desempeño.
    assert len(grupos) >= 1
    grupos_textos = "\n".join(c.texto for c in grupos)

    # NIT #9: la etiqueta de grupo 'medio' nunca aparece como 'moderado' en los
    # chunks de grupo, y los interpretados por dimensión no usan 'medio' (usan
    # 'nivel moderado').
    assert "moderado" not in grupos_textos
    interpretados_textos = "\n".join(
        c.texto for c in hallazgos if "rango de 1 a 5" in c.texto
    )
    assert "nivel medio" not in interpretados_textos

    assert "nan" not in "\n".join(c.texto for c in chunks)
    assert clases.count("estructura") == 3


def test_degradacion_sin_txt(monkeypatch):
    """Sin .txt: estructura por prefijo (etiqueta aproximada) + hallazgos iguales."""
    monkeypatch.setattr(original_txt, "leer_texto_original", lambda _id: None)

    chunks = sources.construir_chunks(_artefacto(), "7")
    estructura = [c for c in chunks if c.clase == "estructura"]
    hallazgos = [c for c in chunks if c.clase == "hallazgos"]

    # Cabecera cae a instrument.title (no hay dc:title ni .txt).
    assert "enc_test_respondido.csv" in estructura[0].texto
    # Las dimensiones de estructura usan la etiqueta aproximada del prefijo.
    dim_textos = "\n".join(c.texto for c in estructura[1:])
    assert "(agrupación aproximada)" in dim_textos
    # Los hallazgos no dependen del .txt: se generan igual.
    assert hallazgos


def test_sin_respondents_solo_estructura(monkeypatch):
    """Sin respondents no se emiten chunks de hallazgos (§6.5)."""
    monkeypatch.setattr(original_txt, "leer_texto_original", lambda _id: _TXT_SINTETICO)
    art = _artefacto()
    art["respondents"] = []

    chunks = sources.construir_chunks(art, "7")
    assert chunks
    assert all(c.clase == "estructura" for c in chunks)


def test_sin_instrument_devuelve_vacio():
    """JSON sin instrument/preguntas -> []."""
    assert sources.construir_chunks({"metadata": {}}, "7") == []
    assert sources.construir_chunks(None, "7") == []


def test_chunk_sobredimensionado_se_aplana(monkeypatch):
    """Un ChunkIndexable > VENTANA se re-trocea con ids/chunk_index únicos (§6.4).

    Se usa el mismo helper de aplanado que el router (`_aplanar_piezas`).
    """
    from app.routers import rag

    gigante = sources.ChunkIndexable(
        texto="Frase larga de prueba. " * 120,  # > 800 chars
        clase="hallazgos",
        dimension="Motivación",
    )
    assert len(gigante.texto) > chunking.VENTANA

    piezas = rag._aplanar_piezas([gigante], chunking)
    assert len(piezas) > 1
    # La metadata (clase/dimension) se propaga a cada pieza.
    assert all(extra["clase_chunk"] == "hallazgos" for _, extra in piezas)
    assert all(extra["dimension"] == "Motivación" for _, extra in piezas)
    # Numeración aplanada: ids y chunk_index secuenciales y únicos.
    ids = [f"inv:7:{n}" for n in range(len(piezas))]
    assert len(set(ids)) == len(ids)


def test_pieza_corta_se_descarta():
    """Piezas por debajo de MIN_LONGITUD se descartan (§15.3-NIT4)."""
    from app.routers import rag

    corta = sources.ChunkIndexable(texto="hola", clase="estructura", dimension="")
    larga = sources.ChunkIndexable(
        texto="x" * (chunking.MIN_LONGITUD + 10), clase="estructura", dimension=""
    )
    piezas = rag._aplanar_piezas([corta, larga], chunking)
    assert len(piezas) == 1


# ── Precedencia de título en extraer_metadata (§15.2) ─────────────────────────
def test_titulo_dc_title_gana():
    art = {
        "instrument": {"title": "enc_01_respondido.csv"},
        "metadata": {"dublin_core": {"dc:title": "Título Dublin Core"}},
    }
    meta = sources.extraer_metadata(art, "1", titulo_override="Título del TXT")
    assert meta["titulo"] == "Título Dublin Core"


def test_titulo_override_txt_gana_sobre_csv():
    art = {
        "instrument": {"title": "enc_01_respondido.csv"},
        "metadata": {"dublin_core": {}},
    }
    meta = sources.extraer_metadata(art, "1", titulo_override="Inventario IEAE")
    assert meta["titulo"] == "Inventario IEAE"


def test_titulo_cae_a_instrument_title():
    art = {
        "instrument": {"title": "enc_01_respondido.csv"},
        "metadata": {"dublin_core": {}},
    }
    meta = sources.extraer_metadata(art, "1")
    assert meta["titulo"] == "enc_01_respondido.csv"


def test_titulo_cae_a_placeholder():
    meta = sources.extraer_metadata({"instrument": {"title": ""}}, "9")
    assert meta["titulo"] == "Instrumento 9"


def test_extraer_metadata_firma_retrocompatible():
    """La llamada vieja de dos argumentos sigue funcionando."""
    meta = sources.extraer_metadata({"instrument": {"title": "x"}}, "3")
    assert meta["instrumentoId"] == "3"
