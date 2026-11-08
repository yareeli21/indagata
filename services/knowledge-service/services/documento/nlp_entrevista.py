"""Qué cuenta la persona en cada respuesta de entrevista: temas, valoración, actores, barreras, experiencias y
propuestas, cada uno con la cita literal que lo sustenta (7 nov 2026).

Se calcula UNA vez, en el mismo trabajo de segundo plano que el análisis de unidades (`services/analisis.py`), y se
guarda en `intercambios[].analisis.nlp` del documento final. El chat lo lee; nunca lo recalcula por pregunta.

Por qué el modelo local y no otras herramientas: los temas, las barreras y las propuestas dependen de la pregunta
guía y del sentido de la frase, no de palabras sueltas. Un clasificador de sentimiento como pysentimiento está
entrenado con tuits y obligaría a meter torch en la imagen de knowledge-service; spaCy solo aportaría lemas, que
las raíces de las reglas ya cubren. El modelo corre offline y una vez por respuesta, así que su lentitud no pesa en el
chat.

Garantías (mismo principio que `analisis_entrevista.validar`):
  - **Cita literal**: toda etiqueta del modelo trae una cita, y lo que se guarda es el tramo EXACTO de la respuesta
    al que corresponde (`anclar`: el más parecido, ≥ 85 % de las palabras). La que no corresponde a ningún tramo se
    descarta y se cuenta en `descartadas`.
  - **Origen**: cada etiqueta dice de dónde salió (`llm` o `regla`).
  - **Respaldo por reglas** (`config/marcadores_entrevista.yaml`): actores, valoración, barreras, experiencias y
    propuestas por raíces, con la oración donde aparecen. Los actores por regla se suman siempre a los del modelo.
  - **Nada de diagnósticos**: el modelo describe lo que la persona dice; la instrucción lo prohíbe y las etiquetas
    solo valen con una cita suya.
"""
from __future__ import annotations

import json
import re
from typing import Any

from services.documento.analisis_entrevista import _norm, marcadores

VALORES = ("positivo", "negativo", "mixto", "neutro")
LISTAS = ("barreras", "experiencias", "propuestas")
_MAX_TEMAS = 4
_MAX_POR_LISTA = 4
_MAX_CITAS = 3
_MAX_TEMA = 60


def _oraciones(respuesta: str) -> list[str]:
    return [o.strip() for o in re.split(r"(?<=[.;!?…])\s+", " ".join(respuesta.split())) if len(o.strip()) > 2]


def _tiene(texto_norm: str, raices: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(_norm(r))}", texto_norm) for r in raices)


def literal(cita: str, respuesta: str) -> bool:
    """¿La cita aparece textual en la respuesta? (sin mayúsculas, acentos ni signos)."""
    c = _norm(cita)
    return bool(c) and c in _norm(respuesta)


_PALABRA = re.compile(r"\w+")
_MIN_PARECIDO = 0.85


def anclar(cita: str, respuesta: str) -> str | None:
    """El fragmento EXACTO de la respuesta al que se refiere la cita, o None.

    El modelo copia casi literal: quita una muletilla («Em,»), cambia un acento o una palabra. En lugar de descartar
    esas citas, se busca en la respuesta el tramo de palabras más parecido (≥ 85 %) y se guarda ESE tramo, tomado del
    texto original: lo guardado siempre es literal.
    """
    from difflib import SequenceMatcher

    buscadas = _norm(cita).split()
    if not buscadas:
        return None
    spans = [(m.start(), m.end(), _norm(m.group())) for m in _PALABRA.finditer(respuesta)]
    palabras = [w for _, _, w in spans]
    n, mejor = len(buscadas), (0.0, None)
    for largo in {max(1, n - 2), n - 1, n, n + 1, n + 2} - {0}:
        for i in range(0, max(0, len(palabras) - largo) + 1):
            r = SequenceMatcher(None, buscadas, palabras[i:i + largo]).ratio()
            if r > mejor[0]:
                mejor = (r, (i, i + largo))
    if mejor[1] is None or mejor[0] < _MIN_PARECIDO:
        return None
    i, j = mejor[1]
    return respuesta[spans[i][0]:spans[j - 1][1]]


# ── Reglas ────────────────────────────────────────────────────────────────────


def _actores_reglas(oraciones: list[str]) -> list[dict[str, str]]:
    salida = []
    for actor, raices in (marcadores().get("actores") or {}).items():
        cita = next((o for o in oraciones if _tiene(_norm(o), raices)), None)
        if cita:
            salida.append({"actor": actor, "cita": cita, "origen": "regla"})
    return salida


def _valoracion_reglas(oraciones: list[str]) -> dict[str, str]:
    lex = marcadores().get("valoracion") or {}
    puntos = [(sum(_tiene(_norm(o), [w]) for w in lex.get("positivo", [])),
               sum(_tiene(_norm(o), [w]) for w in lex.get("negativo", [])), o) for o in oraciones]
    pos, neg = sum(p for p, _, _ in puntos), sum(n for _, n, _ in puntos)
    valor = "neutro" if pos == neg == 0 else "mixto" if pos and neg else "positivo" if pos else "negativo"
    cita = max(puntos, key=lambda x: x[0] + x[1], default=(0, 0, ""))[2] if pos or neg else ""
    return {"valor": valor, "cita": cita, "origen": "regla"}


def analizar_reglas(respuesta: str) -> dict[str, Any]:
    oraciones = _oraciones(respuesta)
    salida: dict[str, Any] = {"temas": [], "valoracion": _valoracion_reglas(oraciones), "actores": _actores_reglas(oraciones)}
    for lista in LISTAS:
        raices = marcadores().get(lista) or []
        salida[lista] = [{"texto": o, "origen": "regla"} for o in oraciones if _tiene(_norm(o), raices)][:_MAX_POR_LISTA]
    salida["citas_clave"] = []
    salida["metodo"], salida["descartadas"] = "reglas", 0
    return salida


# ── Con el modelo de lenguaje ─────────────────────────────────────────────────


def prompt(pregunta: str, respuesta: str) -> str:
    return (
        "Analiza lo que cuenta una persona entrevistada. No diagnostiques ni supongas: describe solo lo que ella dice.\n"
        f"PREGUNTA GUÍA: {pregunta}\nRESPUESTA: {respuesta}\n\n"
        "Cada cita debe copiarse LITERALMENTE de la RESPUESTA (mismas palabras, sin resumir).\n"
        '- "temas": hasta 4 temas de los que habla, relacionados con la pregunta, cada uno con un nombre corto '
        '(2 a 5 palabras) y su "cita";\n'
        '- "valoracion": cómo valora lo que cuenta: "positivo", "negativo", "mixto" o "neutro", con la "cita" que lo '
        "muestra;\n"
        '- "actores": personas o instancias que menciona (profesores, tutor, servicios, compañeros, familia…), cada '
        'uno con su "cita";\n'
        '- "barreras": citas donde cuenta algo que le impidió o dificultó algo;\n'
        '- "experiencias": citas donde cuenta algo que vivió;\n'
        '- "propuestas": citas donde propone o pide un cambio;\n'
        '- "citas_clave": hasta 3 citas que mejor resumen su respuesta.\n'
        'Responde SOLO un JSON: {"temas": [{"tema": "...", "cita": "..."}], "valoracion": {"valor": "...", '
        '"cita": "..."}, "actores": [{"actor": "...", "cita": "..."}], "barreras": ["..."], "experiencias": ["..."], '
        '"propuestas": ["..."], "citas_clave": ["..."]}'
    )


def _texto(x: Any) -> str:
    return " ".join(str(x or "").split())


def validar(respuesta: str, salida: Any) -> dict[str, Any] | None:
    """Análisis del modelo con sus citas verificadas; None si no queda nada con respaldo."""
    if isinstance(salida, str):
        try:
            salida = json.loads(salida)
        except ValueError:
            return None
    if not isinstance(salida, dict):
        return None
    descartadas = 0

    def con_cita(items: Any, clave: str, n: int) -> list[dict[str, str]]:
        nonlocal descartadas
        buenos = []
        for x in items if isinstance(items, list) else []:
            etiqueta, cita = (_texto(x.get(clave)), _texto(x.get("cita"))) if isinstance(x, dict) else ("", "")
            exacta = anclar(cita, respuesta) if etiqueta else None
            if exacta:
                buenos.append({clave: etiqueta[:_MAX_TEMA], "cita": exacta, "origen": "llm"})
            else:
                descartadas += 1
        return buenos[:n]

    def citas(items: Any, n: int) -> list[str]:
        nonlocal descartadas
        buenas = []
        for x in items if isinstance(items, list) else []:
            cita = _texto(x.get("cita") if isinstance(x, dict) else x)
            exacta = anclar(cita, respuesta) if cita else None
            if exacta and exacta not in buenas:
                buenas.append(exacta)
            elif cita and not exacta:
                descartadas += 1
        return buenas[:n]

    v = salida.get("valoracion") if isinstance(salida.get("valoracion"), dict) else {}
    valor, cita_v = str(v.get("valor") or "").strip().lower(), _texto(v.get("cita"))
    exacta_v = anclar(cita_v, respuesta) if valor in VALORES and cita_v else None
    valoracion = {"valor": valor, "cita": exacta_v, "origen": "llm"} if exacta_v else None
    resultado: dict[str, Any] = {
        "temas": con_cita(salida.get("temas"), "tema", _MAX_TEMAS),
        "valoracion": valoracion,
        "actores": con_cita(salida.get("actores"), "actor", 8),
        **{lista: [{"texto": c, "origen": "llm"} for c in citas(salida.get(lista), _MAX_POR_LISTA)] for lista in LISTAS},
        "citas_clave": citas(salida.get("citas_clave"), _MAX_CITAS),
    }
    if not (resultado["temas"] or resultado["citas_clave"] or valoracion):
        return None
    resultado["metodo"], resultado["descartadas"] = "llm", descartadas
    return resultado


def _unir(llm: dict[str, Any], reglas: dict[str, Any]) -> dict[str, Any]:
    """Lo del modelo manda; lo que le falta lo completan las reglas, cada cosa con su origen."""
    salida = dict(llm)
    if not salida.get("valoracion"):
        salida["valoracion"] = reglas["valoracion"]
    vistos = {_norm(a["actor"]) for a in salida["actores"]}
    salida["actores"] = salida["actores"] + [a for a in reglas["actores"] if _norm(a["actor"]) not in vistos
                                             and not any(_norm(a["cita"]) == _norm(b["cita"]) for b in salida["actores"])]
    for lista in LISTAS:
        if not salida[lista]:
            salida[lista] = reglas[lista]
    return salida


# ── Por partes, con esquema (forma elegida el 7 nov) ──────────────────────────
#
# Comparación sobre la entrevista 129 (evidencias/nlp_formato_2026-11-07, 9 respuestas): una petición en JSON libre
# dio 4 análisis válidos (gemma3:4b devolvía «{}» en 1–2 s); una petición con esquema, 9 con 29 citas descartadas;
# tres peticiones cortas con esquema, 9 con 2 citas descartadas (~45 s por respuesta). El esquema solo fija los campos
# y sus tipos (como un formulario); el contenido lo decide el modelo y las citas se siguen verificando.

def _con_cita(clave: str) -> dict[str, Any]:
    return {"type": "array", "items": {"type": "object", "required": [clave, "cita"],
                                       "properties": {clave: {"type": "string"}, "cita": {"type": "string"}}}}


_LISTA = {"type": "array", "items": {"type": "string"}}
CAMPOS: dict[str, dict[str, Any]] = {
    "temas": _con_cita("tema"),
    "valoracion": {"type": "object", "required": ["valor", "cita"],
                   "properties": {"valor": {"enum": list(VALORES)}, "cita": {"type": "string"}}},
    "actores": _con_cita("actor"), "barreras": _LISTA, "experiencias": _LISTA, "propuestas": _LISTA,
    "citas_clave": _LISTA,
}
PARTES: list[tuple[str, ...]] = [("temas", "citas_clave"), ("valoracion", "actores"), ("barreras", "experiencias", "propuestas")]
_INSTRUCCION = {
    "temas": '"temas": hasta 4 temas de los que habla, relacionados con la pregunta, cada uno con un nombre corto '
             '(2 a 5 palabras) y su "cita"',
    "citas_clave": '"citas_clave": hasta 3 citas que mejor resumen su respuesta',
    "valoracion": '"valoracion": cómo valora lo que cuenta ("positivo", "negativo", "mixto" o "neutro") con la "cita" '
                  "que lo muestra",
    "actores": '"actores": personas o instancias que menciona (profesores, tutor, servicios, compañeros, familia…), '
               'cada uno con su "cita"; lista vacía si no menciona',
    "barreras": '"barreras": citas donde cuenta algo que le impidió o dificultó algo; lista vacía si no hay',
    "experiencias": '"experiencias": citas donde cuenta algo que vivió; lista vacía si no hay',
    "propuestas": '"propuestas": citas donde propone o pide un cambio; lista vacía si no hay',
}


def esquema(campos: tuple[str, ...]) -> dict[str, Any]:
    return {"type": "object", "required": list(campos), "properties": {c: CAMPOS[c] for c in campos}}


def prompt_parte(pregunta: str, respuesta: str, campos: tuple[str, ...]) -> str:
    return ("Analiza lo que cuenta una persona entrevistada. No diagnostiques ni supongas: describe solo lo que ella "
            f"dice.\nPREGUNTA GUÍA: {pregunta}\nRESPUESTA: {respuesta}\n\n"
            "Cada cita debe copiarse LITERALMENTE de la RESPUESTA (mismas palabras, sin resumir).\n"
            + "\n".join(f"- {_INSTRUCCION[c]};" for c in campos) + "\nResponde SOLO un JSON con esos campos.")


def analizar(pregunta: str, respuesta: str, llm: Any | None = None) -> dict[str, Any]:
    """Análisis con el modelo (`llm(prompt, esquema) -> dict|str|None`) en tres peticiones cortas, completado y
    respaldado por reglas."""
    reglas = analizar_reglas(respuesta)
    if llm is not None:
        try:
            unido: dict[str, Any] = {}
            for campos in PARTES:
                salida = llm(prompt_parte(pregunta, respuesta, campos), esquema(campos))
                if isinstance(salida, str):
                    salida = json.loads(salida)
                if isinstance(salida, dict):
                    unido.update({c: salida[c] for c in campos if c in salida})
            resultado = validar(respuesta, unido) if unido else None
        except Exception:  # noqa: BLE001 — el modelo nunca es requisito
            resultado = None
        if resultado is not None:
            return _unir(resultado, reglas)
    return reglas
