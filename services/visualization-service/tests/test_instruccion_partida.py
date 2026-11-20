"""Instrucción partida (12 nov): reglas según lo que trae el mensaje y ejemplos por parecido."""
from services import interpretacion, prompt
from shared.db.core.config import settings

CONTEO = ("RESULTADO CALCULADO (exacto, no lo recalcules):\n159 de 2000 respondentes (8.0 %)\n\n"
          "PREGUNTA: ¿Cuántos están considerando abandonar?")
ENTREVISTA = ("TEXTO RECUPERADO (fragmentos):\n[Fuente 1] Salud mental (Entrevista)\n<datos fuente=\"1\">\n"
              "- intercambio: Participante E01, pregunta guía p04: …\n</datos>\n\nPREGUNTA: ¿Cómo le fue con la psicóloga?")


def test_apagada_manda_las_21_reglas(monkeypatch):
    monkeypatch.setattr(settings, "RAG_PROMPT_MODULAR", False)
    assert prompt.sistema_para(CONTEO) == prompt.SISTEMA


def test_las_reglas_conservan_su_texto():
    assert len(prompt._REGLAS) == 21
    assert all(r in prompt.SISTEMA for r in prompt._REGLAS.values())


def test_un_conteo_no_lleva_las_reglas_de_entrevistas(monkeypatch):
    monkeypatch.setattr(settings, "RAG_PROMPT_MODULAR", True)
    texto = prompt.sistema_para(CONTEO)
    assert prompt._REGLAS[10] in texto and prompt._REGLAS[16] in texto  # resultado exacto, % con su n
    assert prompt._REGLAS[13] not in texto and prompt._REGLAS[5] not in texto  # entrevistas
    assert prompt._REGLAS[7] not in texto  # con resultado no se dice «sin información»
    assert prompt._GLOSARIO_AYUDA not in texto
    assert len(texto) < len(prompt.SISTEMA)


def test_una_entrevista_lleva_sus_reglas(monkeypatch):
    monkeypatch.setattr(settings, "RAG_PROMPT_MODULAR", True)
    texto = prompt.sistema_para(ENTREVISTA)
    assert all(prompt._REGLAS[n] in texto for n in (5, 13, 18))
    assert prompt._REGLAS[10] not in texto and prompt._REGLAS[7] in texto
    numeros = [int(l.split(".", 1)[0]) for l in texto.split("Reglas obligatorias:\n", 1)[1].splitlines() if l[:1].isdigit()]
    assert numeros == list(range(1, len(numeros) + 1))  # renumeradas


def test_glosario_y_comparacion_solo_cuando_aplican(monkeypatch):
    monkeypatch.setattr(settings, "RAG_PROMPT_MODULAR", True)
    con = prompt.sistema_para("GLOSARIO:\n[Glosario: alfa] …\n\nPREGUNTA: Compara el alfa entre turnos")
    assert prompt._GLOSARIO_AYUDA in con and prompt._REGLAS[17] in con


def test_ejemplos_por_parecido(monkeypatch):
    monkeypatch.setattr(settings, "RAG_EJEMPLOS_MAX", 3)
    ajustes: list[str] = []
    texto = interpretacion.construir_prompt("¿Cuántos trabajan más de 20 horas?", [], [], ajustes=ajustes)
    fijos = sum(1 for _, p in interpretacion._EJEMPLOS if p["intencion"] in interpretacion._EJEMPLOS_FIJOS)
    assert texto.count("PLAN: {") <= 3 + fijos < len(interpretacion._EJEMPLOS)
    assert "ejemplos por parecido: 3" in ajustes
