"""Tests unitarios de app/core/agregacion.py (diseño §10 unit)."""
from __future__ import annotations

import math

from app.core.agregacion import (
    HallazgoDimension,
    HallazgoGrupo,
    ResumenItem,
    _clasificar_nivel,
    _escala_efectiva,
    _num,
    agregar_categorica,
    agregar_likert,
    agregar_numerica,
    agrupar_por_desempeno,
    escala_efectiva,
    redactar_grupo,
    redactar_hallazgo,
    redactar_interpretacion_dimension,
    redactar_resumen_global,
)


def _r(**answers) -> dict:
    return {"answers": dict(answers)}


# ── _num ────────────────────────────────────────────────────────────────────
def test_num_excluye_bool():
    assert _num(True) is None
    assert _num(False) is None


def test_num_acepta_int_float_y_str_con_coma():
    assert _num(4) == 4.0
    assert _num(3.5) == 3.5
    assert _num("4") == 4.0
    assert _num("3,5") == 3.5
    assert _num("  2 ") == 2.0


def test_num_rechaza_str_no_numerico():
    assert _num("hola") is None
    assert _num(None) is None
    assert _num([1]) is None


# ── agregar_likert ──────────────────────────────────────────────────────────
def test_agregar_likert_media_de_y_pct_alto():
    items = [("q1", "Ítem uno", 1, 5), ("q2", "Ítem dos", 1, 5)]
    respondents = [
        _r(q1=5, q2=5),
        _r(q1=4, q2=4),
        _r(q1=3, q2=1),
    ]
    h = agregar_likert(items, respondents, "Motivación")
    assert h is not None
    assert h.n == 3
    # vector = [5,5,4,4,3,1] -> media 3.6667, de poblacional
    vector = [5, 5, 4, 4, 3, 1]
    assert math.isclose(h.media, sum(vector) / len(vector), rel_tol=1e-9)
    # pct_alto: umbral tercio superior 1..5 = 1 + 2*4/3 = 3.6667 -> valores >= 3.667: 5,5,4,4 = 4/6
    assert math.isclose(h.pct_alto, 4 / 6 * 100.0, rel_tol=1e-9)
    # item más alto = q1 (media 4), más bajo = q2 (media 3.3333)
    assert h.item_mas_alto.question_id == "q1"
    assert h.item_mas_bajo.question_id == "q2"


def test_agregar_likert_todos_none_devuelve_none():
    items = [("q1", "Ítem uno", 1, 5)]
    respondents = [_r(q1=None), _r(q1="x"), _r(q1=True)]
    assert agregar_likert(items, respondents, "Dim") is None


def test_agregar_likert_un_solo_respondente():
    items = [("q1", "Ítem uno", 1, 5)]
    h = agregar_likert(items, [_r(q1=4)], "Dim")
    assert h is not None
    assert h.n == 1
    assert h.media == 4.0
    assert h.de == 0.0


def test_agregar_likert_escala_no_1_5_umbral_tercio_superior():
    # escala 0..10, umbral = 0 + 2*10/3 = 6.6667
    items = [("q1", "Ítem", 0, 10)]
    respondents = [_r(q1=10), _r(q1=7), _r(q1=5), _r(q1=0)]
    h = agregar_likert(items, respondents, "Dim")
    assert h is not None
    # valores >= 6.667: 10 y 7 -> 2/4
    assert math.isclose(h.pct_alto, 2 / 4 * 100.0, rel_tol=1e-9)


def test_agregar_likert_str_con_coma_decimal():
    items = [("q1", "Ítem", 1, 5)]
    h = agregar_likert([("q1", "Ítem", 1, 5)], [_r(q1="4,5"), _r(q1="3,5")], "Dim")
    assert h is not None
    assert math.isclose(h.media, 4.0, rel_tol=1e-9)


# ── agregar_numerica ──────────────────────────────────────────────────────────
def test_agregar_numerica():
    respondents = [_r(q6=3.0), _r(q6=1.5), _r(q6=4.0)]
    h = agregar_numerica("q6", "GPA", respondents)
    assert h is not None
    assert h.n == 3
    assert h.minimo == 1.5
    assert h.maximo == 4.0


def test_agregar_numerica_sin_valores_devuelve_none():
    assert agregar_numerica("q6", "GPA", [_r(q6=None), _r(q6="x")]) is None


# ── agregar_categorica ──────────────────────────────────────────────────────
def test_agregar_categorica_distribucion():
    respondents = [
        _r(q=" privada "),
        _r(q="privada"),
        _r(q="pública"),
        _r(q=""),
        _r(q=None),
    ]
    h = agregar_categorica("q", "tipo de universidad", "opcion_multiple", respondents)
    assert h is not None
    assert h.n == 3
    categorias = dict(h.distribucion)
    assert math.isclose(categorias["privada"], 2 / 3 * 100.0, rel_tol=1e-9)


def test_agregar_categorica_binaria_si_no():
    respondents = [_r(q="True"), _r(q="False"), _r(q="True")]
    h = agregar_categorica("q", "trabaja", "binaria", respondents)
    assert h is not None
    categorias = dict(h.distribucion)
    assert "sí" in categorias
    assert "no" in categorias


def test_agregar_categorica_vacio_devuelve_none():
    assert agregar_categorica("q", "x", "opcion_multiple", [_r(q=""), _r(q=None)]) is None


# ── redacción ────────────────────────────────────────────────────────────────
def test_redactar_hallazgo_likert_formato_espanol():
    h = HallazgoDimension(
        dimension="Motivación",
        tipo="likert",
        n=180,
        media=4.12,
        de=0.83,
        pct_alto=72.0,
        item_mas_alto=ResumenItem("q3", "Me esfuerzo más", 4.4, 0.5, 180),
        item_mas_bajo=ResumenItem("q2", "Encuentro significativo", 3.6, 0.6, 180),
    )
    texto = redactar_hallazgo(h)
    assert "Motivación" in texto
    assert "4.1/5" in texto  # 1 decimal
    assert "DE 0.8" in texto
    assert "72 %" in texto  # porcentaje entero
    assert "n = 180 respondentes." in texto
    assert "nan" not in texto


def test_redactar_hallazgo_numerica():
    h = HallazgoDimension(
        dimension="GPA", tipo="numerica", n=180, media=3.14, de=0.5, minimo=1.5, maximo=4.0
    )
    texto = redactar_hallazgo(h)
    assert "3.1" in texto
    assert "mínimo 1.5" in texto
    assert "máximo 4.0" in texto


def test_redactar_hallazgo_categorica():
    h = HallazgoDimension(
        dimension="tipo de universidad",
        tipo="categorica",
        n=180,
        distribucion=[("privada", 54.0), ("pública", 33.0), ("mixta", 13.0)],
    )
    texto = redactar_hallazgo(h)
    assert "54 %" in texto
    assert "n = 180" in texto


def test_redactar_resumen_global_sin_likert_ni_numericas():
    hallazgos = [
        HallazgoDimension(dimension="tipo", tipo="categorica", n=10, distribucion=[("a", 100.0)])
    ]
    texto = redactar_resumen_global(hallazgos, 10, "Instrumento X")
    assert "10 respondentes" in texto
    assert "media más alta" not in texto
    assert "nan" not in texto


def test_redactar_resumen_global_hallazgos_vacio():
    texto = redactar_resumen_global([], 42, "Instrumento X")
    assert "42 respondentes" in texto
    assert "No se registraron dimensiones" in texto
    assert "nan" not in texto


def test_redactar_resumen_global_con_likert_y_numerica():
    hallazgos = [
        HallazgoDimension(dimension="A", tipo="likert", n=5, media=4.5, de=0.1),
        HallazgoDimension(dimension="B", tipo="likert", n=5, media=2.1, de=0.2),
        HallazgoDimension(dimension="GPA", tipo="numerica", n=5, media=3.0, de=0.3),
    ]
    texto = redactar_resumen_global(hallazgos, 5, "Inst")
    assert "más alta fue A" in texto
    assert "más baja B" in texto
    assert "GPA" in texto


# ── escala_efectiva (§16.1, §5.4) ─────────────────────────────────────────────
def _it(qid, smin, smax):
    return (qid, f"Ítem {qid}", smin, smax)


def test_escala_efectiva_homogenea_1_5():
    items = [_it("q1", 1, 5), _it("q2", 1, 5)]
    assert escala_efectiva(items) == (1.0, 5.0)


def test_escala_efectiva_mixta_devuelve_envolvente():
    items = [_it("q1", 0, 4), _it("q2", 1, 5)]
    assert escala_efectiva(items) == (0.0, 5.0)


def test_escala_efectiva_vacia_cae_a_1_5():
    assert escala_efectiva([]) == (1.0, 5.0)


def test_escala_efectiva_invalida_cae_a_1_5():
    assert escala_efectiva([("q1", "x", None, None)]) == (1.0, 5.0)
    assert escala_efectiva([("q1",)]) == (1.0, 5.0)


def test_escala_efectiva_min_mayor_igual_max_cae_a_1_5():
    assert escala_efectiva([_it("q1", 5, 5)]) == (1.0, 5.0)
    assert escala_efectiva([_it("q1", 7, 3)]) == (1.0, 5.0)


def test_escala_efectiva_alias_privado_disponible():
    assert _escala_efectiva is escala_efectiva


def test_escala_efectiva_coincide_con_rango_pct_alto_en_1_5():
    # El rango que agregar_likert usa para pct_alto (umbral 1 + 2*4/3 = 3.667)
    # proviene del mismo (1.0, 5.0) que devuelve escala_efectiva (§16.1).
    items = [_it("q1", 1, 5), _it("q2", 1, 5)]
    smin, smax = escala_efectiva(items)
    assert (smin, smax) == (1.0, 5.0)
    h = agregar_likert(items, [_r(q1=5, q2=4), _r(q1=3, q2=1)], "Dim")
    umbral = smin + 2.0 * (smax - smin) / 3.0
    # valores >= 3.667: 5,4 de [5,4,3,1] -> 2/4
    assert h is not None
    assert math.isclose(h.pct_alto, 2 / 4 * 100.0, rel_tol=1e-9)
    assert math.isclose(umbral, 1.0 + 2.0 * 4.0 / 3.0, rel_tol=1e-9)


# ── _clasificar_nivel (§16.2) ─────────────────────────────────────────────────
def test_clasificar_nivel_1_5():
    assert _clasificar_nivel(1.8, 1.0, 5.0) == "bajo"
    assert _clasificar_nivel(3.0, 1.0, 5.0) == "medio"
    assert _clasificar_nivel(4.2, 1.0, 5.0) == "alto"


def test_clasificar_nivel_limites_exactos():
    # corte_bajo = 1 + 4/3 = 2.3333; corte_alto = 1 + 8/3 = 3.6667.
    # En el corte exacto la media cae en el nivel superior (media < corte -> inferior).
    corte_bajo = 1.0 + 4.0 / 3.0
    corte_alto = 1.0 + 8.0 / 3.0
    assert _clasificar_nivel(corte_bajo, 1.0, 5.0) == "medio"  # >= corte_bajo
    assert _clasificar_nivel(corte_bajo - 1e-9, 1.0, 5.0) == "bajo"
    assert _clasificar_nivel(corte_alto, 1.0, 5.0) == "alto"  # >= corte_alto
    assert _clasificar_nivel(corte_alto - 1e-9, 1.0, 5.0) == "medio"


def test_clasificar_nivel_escala_0_10():
    # corte_bajo = 10/3 = 3.333; corte_alto = 20/3 = 6.667
    assert _clasificar_nivel(2.0, 0.0, 10.0) == "bajo"
    assert _clasificar_nivel(5.0, 0.0, 10.0) == "medio"
    assert _clasificar_nivel(8.0, 0.0, 10.0) == "alto"


def test_clasificar_nivel_rango_invalido_cae_a_1_5():
    # rango <= 0 -> asume 1..5: 2.0 bajo, 3.0 medio, 4.0 alto
    assert _clasificar_nivel(2.0, 5.0, 5.0) == "bajo"
    assert _clasificar_nivel(3.0, 5.0, 5.0) == "medio"
    assert _clasificar_nivel(4.0, 5.0, 5.0) == "alto"


# ── redactar_interpretacion_dimension (§5.3, §16.2-§16.7) ─────────────────────
def _hl(dim, media, n=180):
    return HallazgoDimension(dimension=dim, tipo="likert", n=n, media=media, de=0.5)


def test_interpretacion_una_dim_sin_comparacion():
    h = _hl("Motivación", 4.1)
    texto = redactar_interpretacion_dimension(h, [h], 1.0, 5.0)
    assert texto is not None
    assert "Motivación" in texto
    assert "nivel alto" in texto
    assert "más fuerte" not in texto  # sin comparación con 1 sola dim
    assert "rango de 1 a 5" in texto
    assert "/5" not in texto
    assert "n = 180 respondentes." in texto
    assert "nan" not in texto
    assert len(texto) <= 700


def test_interpretacion_tres_dims_max_min_y_brecha():
    alta = _hl("Motivación", 4.4)
    media = _hl("Recursos", 3.0)
    baja = _hl("Organización", 2.1)
    todos = [alta, media, baja]
    texto = redactar_interpretacion_dimension(media, todos, 1.0, 5.0)
    assert texto is not None
    assert "Motivación" in texto  # más fuerte
    assert "Organización" in texto  # más débil
    # brecha abs(4.4 - 2.1) = 2.3 con 1 decimal
    assert "2.3 puntos" in texto
    assert "nivel moderado" in texto  # etiqueta de dimensión, no "medio"
    assert "medio" not in texto  # NIT #9: etiqueta de grupo no aparece


def test_interpretacion_empate_toma_primera_en_orden():
    a = _hl("A", 4.0)
    b = _hl("B", 4.0)  # empate máximo
    c = _hl("C", 2.0)
    texto = redactar_interpretacion_dimension(a, [a, b, c], 1.0, 5.0)
    assert texto is not None
    # máximo con desempate determinista = «A» (primera en orden)
    assert "más fuerte del instrumento es «A»" in texto


def test_interpretacion_media_none_devuelve_none():
    h = HallazgoDimension(dimension="X", tipo="likert", n=5, media=None)
    assert redactar_interpretacion_dimension(h, [h], 1.0, 5.0) is None


def test_interpretacion_tipo_no_likert_devuelve_vacio():
    h = HallazgoDimension(dimension="X", tipo="numerica", n=5, media=3.0)
    assert redactar_interpretacion_dimension(h, [], 1.0, 5.0) == ""


# ── agrupar_por_desempeno (§6, §16.6) ─────────────────────────────────────────
def test_agrupar_grupos_esperados():
    items_por_dim = {"Dim": [_it("q1", 1, 5), _it("q2", 1, 5)]}
    respondents = [
        _r(q1=5, q2=5),  # puntaje 5 -> alto
        _r(q1=4, q2=5),  # 4.5 -> alto
        _r(q1=3, q2=3),  # 3.0 -> medio
        _r(q1=1, q2=2),  # 1.5 -> bajo
    ]
    grupos = agrupar_por_desempeno(items_por_dim, respondents)
    etiquetas = {g.grupo for g in grupos}
    assert etiquetas == {"alto", "medio", "bajo"}
    # % suma ~100 sobre 4 clasificados
    assert math.isclose(sum(g.pct for g in grupos), 100.0, rel_tol=1e-9)
    for g in grupos:
        assert not math.isnan(g.puntaje_medio)


def test_agrupar_equiponderado_dimension_larga_baja_corta_alta():
    # Dimensión larga (3 ítems) con valores bajos, corta (1 ítem) con valor alto.
    # Media por ítem: (1+1+1+5)/4 = 2.0 -> bajo. Equiponderado: (1.0 + 5.0)/2 = 3.0 -> medio.
    items_por_dim = {
        "Larga": [_it("q1", 1, 5), _it("q2", 1, 5), _it("q3", 1, 5)],
        "Corta": [_it("q4", 1, 5)],
    }
    respondents = [_r(q1=1, q2=1, q3=1, q4=5)]
    grupos = agrupar_por_desempeno(items_por_dim, respondents)
    assert len(grupos) == 1
    assert grupos[0].grupo == "medio"  # equiponderado, no "bajo"
    assert math.isclose(grupos[0].puntaje_medio, 3.0, rel_tol=1e-9)


def test_agrupar_excluye_respondente_sin_likert_valido():
    items_por_dim = {"Dim": [_it("q1", 1, 5)]}
    respondents = [
        _r(q1=5),
        _r(q1="x"),  # no numérico -> sin dimensión válida -> excluido
        _r(q1=None),  # excluido
    ]
    grupos = agrupar_por_desempeno(items_por_dim, respondents)
    assert len(grupos) == 1
    assert grupos[0].n == 1
    assert math.isclose(grupos[0].pct, 100.0, rel_tol=1e-9)  # sobre clasificados


def test_agrupar_num_con_bool_y_str_coma():
    items_por_dim = {"Dim": [_it("q1", 1, 5)]}
    respondents = [
        _r(q1=True),  # bool -> None (excluido)
        _r(q1="4,5"),  # str con coma -> 4.5 -> alto
    ]
    grupos = agrupar_por_desempeno(items_por_dim, respondents)
    assert len(grupos) == 1
    assert grupos[0].grupo == "alto"
    assert grupos[0].n == 1


def test_agrupar_anti_regresion_perfil():
    # Dos datasets idénticos en Likert pero con 'perfil' distinto -> MISMOS grupos.
    items_por_dim = {"Dim": [_it("q1", 1, 5), _it("q2", 1, 5)]}
    base = [_r(q1=5, q2=5), _r(q1=1, q2=1)]
    con_perfil_a = [{"answers": r["answers"], "perfil": "P1"} for r in base]
    con_perfil_b = [{"answers": r["answers"], "perfil": "P8"} for r in base]
    g_a = agrupar_por_desempeno(items_por_dim, con_perfil_a)
    g_b = agrupar_por_desempeno(items_por_dim, con_perfil_b)
    repr_a = sorted((g.grupo, g.n) for g in g_a)
    repr_b = sorted((g.grupo, g.n) for g in g_b)
    assert repr_a == repr_b


def test_agrupar_sin_items_likert_devuelve_vacio():
    assert agrupar_por_desempeno({}, [_r(q1=5)]) == []


def test_agrupar_todos_invalidos_total_cero_devuelve_vacio():
    items_por_dim = {"Dim": [_it("q1", 1, 5)]}
    assert agrupar_por_desempeno(items_por_dim, [_r(q1="x"), _r(q1=None)]) == []


# ── redactar_grupo (§6.5, NIT #9) ─────────────────────────────────────────────
def test_redactar_grupo_encabezado_y_puntaje():
    g = HallazgoGrupo(
        grupo="bajo",
        n=32,
        pct=18.0,
        puntaje_medio=2.1,
        dim_altas=[("Motivación", 2.6)],
        dim_bajas=[("Organización", 1.8), ("Examen", 1.9)],
    )
    texto = redactar_grupo(g, 5.0)
    assert "Grupo de desempeño bajo (n = 32, 18 % del total)." in texto
    assert "2.1 sobre 5" in texto
    assert "Organización (media 1.8)" in texto
    assert "Examen (media 1.9)" in texto
    assert "Motivación (media 2.6)" in texto
    assert "apoyo más urgentes" in texto
    assert "nan" not in texto


def test_redactar_grupo_omision_redundante_una_dim():
    # dim_altas y dim_bajas coinciden (grupo de 1 dimensión) -> se omite fortaleza.
    g = HallazgoGrupo(
        grupo="medio",
        n=5,
        pct=50.0,
        puntaje_medio=3.0,
        dim_altas=[("Única", 3.0)],
        dim_bajas=[("Única", 3.0)],
    )
    texto = redactar_grupo(g, 5.0)
    assert "Relativa fortaleza" not in texto
    assert "Mayor debilidad en Única (media 3.0)." in texto


def test_redactar_grupo_etiqueta_medio_no_moderado():
    g = HallazgoGrupo(
        grupo="medio",
        n=5,
        pct=100.0,
        puntaje_medio=3.0,
        dim_altas=[("A", 3.5)],
        dim_bajas=[("B", 2.5)],
    )
    texto = redactar_grupo(g, 5.0)
    assert "desempeño medio" in texto
    assert "moderado" not in texto  # NIT #9
