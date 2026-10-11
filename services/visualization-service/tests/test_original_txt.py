"""Tests unitarios de app/core/original_txt.py (diseño §10 unit)."""
from __future__ import annotations

from pathlib import Path

import app.core.original_txt as original_txt
from app.core.original_txt import (
    construir_mapa_dimension,
    leer_texto_original,
    mapa_por_prefijo,
    parsear_estructura,
    ruta_original,
)

# ── Fixture: el .txt real de ejemplo (IEAE, 6 secciones, 21 ítems) ──────────
_TXT = """\
======================================================================
INSTRUMENTO: Inventario de Estrategias de Aprendizaje y Estudio (IEAE)
ID: enc_01
Fuente: REAL — Fernández Liporace, M. et al.
======================================================================

INSTRUCCIONES:
  1 = Totalmente en desacuerdo / Nunca
  5 = Totalmente de acuerdo / Siempre

--- ORGANIZACIÓN Y PLANIFICACIÓN ---

1. Organizo el material de estudio antes de comenzar a estudiar.
   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5
2. Elaboro un plan de trabajo con tiempos definidos.
3. Identifico los conceptos principales antes de profundizar.
4. Reviso mis apuntes inmediatamente después de cada clase.
5. Establezco metas específicas para cada sesión de estudio.
6. Distribuyo el tiempo de estudio de manera equitativa.
7. Preparo con anticipación los materiales que necesitaré.

--- HABILIDADES PARA EL EXAMEN ---

8. Practico con exámenes anteriores.
9. Reviso mis errores de exámenes anteriores.
10. Gestiono bien el tiempo durante la realización de un examen.

--- MOTIVACIÓN ---

11. Me siento motivado/a para estudiar.
12. Encuentro significativo el contenido de lo que estudio.
13. Me esfuerzo más cuando el tema me parece interesante.

--- RECURSOS DE APRENDIZAJE ---

14. Utilizo distintas fuentes de información.
15. Aprovecho los recursos digitales.

--- ESTRATEGIAS DE CONTROL Y CONSOLIDACIÓN ---

16. Me autoevalúo para verificar si he comprendido.
17. Cuando no entiendo algo, busco aclararlo.
18. Relaciono los nuevos conocimientos con lo que ya sé.

--- HABILIDADES PARA JERARQUIZAR ---

19. Distingo entre la información principal y la secundaria.
20. Elaboro resúmenes o esquemas que priorizan los puntos clave.
21. Ordeno los temas según su importancia.

======================================================================
FIN DEL INSTRUMENTO
Total de ítems: 21
"""


def _questions_likert_inst1() -> list[dict]:
    """Los 21 question_id likert de inst_1 con el mojibake real (cp850)."""
    pref = [
        ("Organizaci\u251c\u2502n_y_", 7),
        ("Habilidades_par", 3),
        ("Motivaci\u251c\u2502n", 3),
        ("Recursos_de_apr", 2),
        ("Estrategias_de_", 3),
        ("Habilidades_par", 3),
    ]
    qs: list[dict] = []
    qid = 13
    for prefijo, k in pref:
        for n in range(1, k + 1):
            qs.append({"question_id": f"q{qid}", "text": f"{prefijo}_item{n}"})
            qid += 1
    return qs


# ── parsear_estructura ──────────────────────────────────────────────────────
def test_parsear_estructura_titulo_secciones_items():
    est = parsear_estructura(_TXT)
    assert est.titulo_instrumento == (
        "Inventario de Estrategias de Aprendizaje y Estudio (IEAE)"
    )
    assert len(est.secciones) == 6
    assert est.secciones[0].titulo == "Organización Y Planificación"
    assert len(est.secciones[0].items) == 7
    total_items = sum(len(s.items) for s in est.secciones)
    assert total_items == 21
    assert est.secciones[0].items[0].startswith("Organizo el material")


def test_parsear_estructura_ignora_casillas_e_instrucciones():
    est = parsear_estructura(_TXT)
    # Ninguna línea de casillas [ ] ni de escala debe entrar como ítem.
    for sec in est.secciones:
        for item in sec.items:
            assert "[ ]" not in item
            assert not item.startswith("=")


# ── construir_mapa_dimension (posicional) ───────────────────────────────────
def test_mapa_posicional_resuelve_colision_por_posicion():
    est = parsear_estructura(_TXT)
    questions = _questions_likert_inst1()
    mapa = construir_mapa_dimension(est, questions)
    assert len(mapa) == 21
    # q20 (Habilidades_par item1 -> sección "Habilidades Para El Examen")
    assert mapa["q20"][0] == "Habilidades Para El Examen"
    # q31 (Habilidades_par item1 de nuevo -> sección "Habilidades Para Jerarquizar")
    assert mapa["q31"][0] == "Habilidades Para Jerarquizar"
    # El texto redactado proviene del .txt
    assert mapa["q13"][1].startswith("Organizo el material")


def test_mapa_conteo_desigual_devuelve_vacio():
    est = parsear_estructura(_TXT)
    questions = _questions_likert_inst1()[:20]  # 20 != 21
    assert construir_mapa_dimension(est, questions) == {}


def test_mapa_orden_no_monotonico_devuelve_vacio():
    est = parsear_estructura(_TXT)
    # Un grupo cuya secuencia _item no es 1..k creciente.
    questions = [
        {"question_id": "q1", "text": "Grupo_a_item1"},
        {"question_id": "q2", "text": "Grupo_a_item3"},  # salta el 2 -> no monotónico
        {"question_id": "q3", "text": "Grupo_a_item2"},
    ]
    assert construir_mapa_dimension(est, questions) == {}


# ── fallback por prefijo con mojibake reparado ──────────────────────────────
def test_mapa_por_prefijo_repara_mojibake_cp850():
    questions = _questions_likert_inst1()
    mapa = mapa_por_prefijo(questions)
    # 'Organizaci├│n_y__item1' -> prefijo reparado 'Organización_y_'
    dim, item = mapa["q13"]
    assert "Organización" in dim
    assert "(agrupación aproximada)" in dim
    assert item.endswith("ítem 1")
    # Motivación reparada
    assert "Motivación" in mapa["q23"][0]


def test_mapa_por_prefijo_detecta_colision(caplog):
    import logging

    questions = _questions_likert_inst1()
    with caplog.at_level(logging.WARNING, logger="visualization-service"):
        mapa_por_prefijo(questions)
    assert any("colisión de prefijo" in r.message for r in caplog.records)


# ── ruta_original (BD mockeada) ─────────────────────────────────────────────
def _mock_bd(monkeypatch, valor_rel: str | None):
    """Hace que `_ruta_relativa_desde_bd` devuelva `valor_rel` sin tocar la BD."""
    monkeypatch.setattr(
        original_txt, "_ruta_relativa_desde_bd", lambda _id: valor_rel
    )


def test_ruta_original_convencion_upload(monkeypatch, tmp_path):
    # raw_archivo_original = "raw/x_original.txt" resuelve bajo storage/
    # (settings.raw_path_abs.parent / rel). Simulamos storage/ con tmp_path.
    storage = tmp_path / "storage"
    raw = storage / "raw"
    raw.mkdir(parents=True)
    archivo = raw / "x_original.txt"
    archivo.write_text("contenido", encoding="utf-8")

    monkeypatch.setattr(
        type(original_txt.settings), "raw_path_abs", property(lambda _s: raw)
    )
    monkeypatch.setattr(
        type(original_txt.settings), "PROJECT_ROOT", property(lambda _s: tmp_path / "otro")
    )
    _mock_bd(monkeypatch, "raw/x_original.txt")

    ruta = ruta_original("upload_1")
    assert ruta == archivo


def test_ruta_original_convencion_seed(monkeypatch, tmp_path):
    # raw_archivo_original = "storage/raw/x_original.txt" resuelve bajo PROJECT_ROOT.
    proyecto = tmp_path / "proyecto"
    archivo = proyecto / "storage" / "raw" / "x_original.txt"
    archivo.parent.mkdir(parents=True)
    archivo.write_text("contenido", encoding="utf-8")

    # raw_path_abs apunta a otro sitio que NO contiene el archivo por la 1ª convención.
    raw_distinto = tmp_path / "vacio" / "raw"
    raw_distinto.mkdir(parents=True)

    monkeypatch.setattr(
        type(original_txt.settings), "raw_path_abs", property(lambda _s: raw_distinto)
    )
    monkeypatch.setattr(
        type(original_txt.settings), "PROJECT_ROOT", property(lambda _s: proyecto)
    )
    _mock_bd(monkeypatch, "storage/raw/x_original.txt")

    ruta = ruta_original("1")
    assert ruta == archivo


# ── leer_texto_original ─────────────────────────────────────────────────────
def test_leer_texto_original_ilegible_devuelve_none(monkeypatch, tmp_path):
    archivo = tmp_path / "mal.txt"
    # Bytes no decodables como utf-8 (0xFF 0xFE sueltos no forman utf-8 válido aquí).
    archivo.write_bytes(b"\xff\xfe\x00valido\x80\x81")
    monkeypatch.setattr(original_txt, "ruta_original", lambda _id: archivo)
    resultado = leer_texto_original("x")
    assert resultado is None  # sin \ufffd, degrada a None


def test_leer_texto_original_ok(monkeypatch, tmp_path):
    archivo = tmp_path / "ok.txt"
    archivo.write_text("INSTRUMENTO: X\n", encoding="utf-8")
    monkeypatch.setattr(original_txt, "ruta_original", lambda _id: archivo)
    assert leer_texto_original("x") == "INSTRUMENTO: X\n"


def test_leer_texto_original_vacio_devuelve_none(monkeypatch, tmp_path):
    archivo = tmp_path / "vacio.txt"
    archivo.write_text("   \n", encoding="utf-8")
    monkeypatch.setattr(original_txt, "ruta_original", lambda _id: archivo)
    assert leer_texto_original("x") is None
