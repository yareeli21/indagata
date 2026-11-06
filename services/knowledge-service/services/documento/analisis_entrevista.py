"""Análisis de una respuesta de entrevista guiado por la pregunta (unidades de significado).

Una respuesta real divaga: «Cuando iba en la primaria no lo pensaba así […] pero ahora creo
que sí, me llenan de energía por querer mantener la beca deportiva». La pregunta («¿…
actualmente tienen impacto…?») pide el presente; el relato del pasado es contexto. Aquí se
divide la respuesta en UNIDADES con:

  - `marco_temporal`: actual | pasado | hipotetico | general
  - `funcion`:        responde | contexto | digresion   (respecto a la pregunta)
  - `postura`:        si | no | ambivalente | no_aplica

y se obtiene el NÚCLEO (las unidades que responden) y la POSTURA global con su motivo.

Garantías (mismo principio que `cifras_fieles` en el chat):
  - **Literalidad**: cada unidad debe aparecer textual en la respuesta (comparación sin
    mayúsculas, acentos ni signos); la que no aparece se descarta y se cuenta.
  - **Motivo anclado**: el motivo debe salir de la respuesta (≥ 60 % de sus palabras de
    contenido presentes); si no, se omite.
  - **Respaldo sin LLM** (`analizar_reglas`): oraciones y conectores, marco por marcadores
    editables (`config/marcadores_entrevista.yaml`) y postura solo si es explícita.
  - Todo nace `propuesto`: el investigador lo revisa y corrige antes de publicar.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

MARCOS = ("actual", "pasado", "hipotetico", "general")
FUNCIONES = ("responde", "contexto", "digresion")
POSTURAS = ("si", "no", "ambivalente", "no_aplica")
_RUTA_MARCADORES = Path(__file__).resolve().parents[2] / "config" / "marcadores_entrevista.yaml"
_VACIAS = {"de", "la", "el", "los", "las", "que", "y", "a", "en", "por", "un", "una", "lo", "me", "mi", "se", "es",
           "con", "para", "al", "del", "o", "su", "le", "ya", "muy", "mas", "pero", "como", "porque", "eso"}


@lru_cache(maxsize=1)
def marcadores() -> dict[str, Any]:
    with _RUTA_MARCADORES.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _norm(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w\s]", " ", sin.lower()).split())


def _contiene_frase(texto_norm: str, frases: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(_norm(f))}(?!\w)", texto_norm) for f in frases)


def marco_de(texto: str) -> str:
    """Marco temporal por marcadores; «general» si no hay ninguno."""
    n = _norm(texto)
    hallados = [(m.start(), marco) for marco in ("pasado", "actual", "hipotetico")
                for f in marcadores().get("tiempo", {}).get(marco, [])
                if (m := re.search(rf"(?<!\w){re.escape(_norm(f))}(?!\w)", n))]
    return min(hallados)[1] if hallados else "general"


def marco_de_pregunta(pregunta: str) -> str:
    """La pregunta pide el presente salvo que hable del pasado o de un supuesto."""
    m = marco_de(pregunta)
    return "actual" if m == "general" else m


def _postura_explicita(texto: str) -> str:
    n = _norm(texto)
    p = marcadores().get("postura", {})
    si, no = _contiene_frase(n, p.get("si", [])), _contiene_frase(n, p.get("no", []))
    return "ambivalente" if si and no else "si" if si else "no" if no else "no_aplica"


def empieza_ambivalente(texto: str) -> bool:
    """¿Empieza con «depende», «más o menos», «a veces»…? (solo al inicio: «Sí, a veces voy» es «sí»)."""
    inicio = " ".join(_norm(texto).split()[:4])
    return any(re.match(rf"{re.escape(_norm(f))}(?!\w)", inicio) for f in marcadores().get("ambivalencia", []))


def _global(unidades: list[dict[str, Any]], respuesta: str = "") -> str:
    # «Depende; en matemáticas sí, pero en redacción no tanto»: el modelo y las reglas veían solo
    # el «sí» (anotación de la investigadora, 22 oct 2026). La marca al inicio decide.
    if empieza_ambivalente(respuesta) or any(u["funcion"] == "responde" and empieza_ambivalente(u["texto"]) for u in unidades):
        return "ambivalente"
    posturas = {u["postura"] for u in unidades if u["funcion"] == "responde" and u["postura"] != "no_aplica"}
    if not posturas:
        return "no_aplica"
    return posturas.pop() if len(posturas) == 1 else "ambivalente"


def _nucleo(unidades: list[dict[str, Any]]) -> str:
    return " ".join(u["texto"] for u in unidades if u["funcion"] == "responde")


# ── Respaldo por reglas ───────────────────────────────────────────────────────


def _segmentos(respuesta: str) -> list[str]:
    partes = [p.strip() for p in re.split(r"(?<=[.;!?])\s+", " ".join(respuesta.split())) if p.strip()]
    for conector in marcadores().get("conectores", []):
        nuevas = []
        for p in partes:
            trozos = p.split(conector)
            nuevas += [t.strip(" ,") for t in [trozos[0]] + [conector.strip(" ,") + " " + t for t in trozos[1:]] if t.strip(" ,")]
        partes = nuevas
    return partes


def analizar_reglas(pregunta: str, respuesta: str) -> dict[str, Any]:
    objetivo = marco_de_pregunta(pregunta)
    unidades = []
    for s in _segmentos(respuesta):
        marco = marco_de(s)
        funcion = "responde" if marco in (objetivo, "general") else "contexto"
        unidades.append({"texto": s, "marco_temporal": marco, "funcion": funcion, "postura": _postura_explicita(s)})
    if unidades and not any(u["funcion"] == "responde" for u in unidades):
        unidades[-1]["funcion"] = "responde"  # sin marco que coincida: la última frase suele concluir
    postura = _global(unidades, respuesta)
    return {"unidades": unidades, "nucleo": _nucleo(unidades), "postura": postura if postura != "no_aplica" else "sin_determinar",
            "motivo": "", "marco_pregunta": objetivo, "metodo": "reglas", "estado": "propuesto", "descartadas": 0}


# ── Con el modelo de lenguaje ─────────────────────────────────────────────────


def prompt(pregunta: str, respuesta: str) -> str:
    return (
        "Analiza la respuesta de una persona entrevistada en relación con la pregunta que se le hizo.\n"
        f"PREGUNTA: {pregunta}\nRESPUESTA: {respuesta}\n\n"
        "Divide la RESPUESTA en fragmentos copiados LITERALMENTE (mismas palabras, sin resumir ni corregir) y, "
        "para cada uno, indica:\n"
        '- "marco_temporal": "actual", "pasado", "hipotetico" o "general" (de qué momento habla el fragmento);\n'
        '- "funcion": "responde" si contesta lo que la pregunta pide (en el momento que la pregunta pide), '
        '"contexto" si es un antecedente o relato que ayuda a entender, "digresion" si se sale del tema;\n'
        '- "postura": "si", "no", "ambivalente" o "no_aplica" respecto a la pregunta.\n'
        'Después da la "postura" global de la persona (según los fragmentos que responden) y el "motivo" que '
        "da, con palabras de la propia respuesta (vacío si no da ninguno).\n"
        'Responde SOLO un JSON: {"unidades": [{"texto": "...", "marco_temporal": "...", "funcion": "...", '
        '"postura": "..."}], "postura": "...", "motivo": "..."}'
    )


def _anclado(motivo: str, respuesta: str) -> bool:
    palabras = [p for p in _norm(motivo).split() if p not in _VACIAS]
    if not palabras:
        return False
    presentes = set(_norm(respuesta).split())
    return sum(p in presentes for p in palabras) / len(palabras) >= 0.6


def validar(pregunta: str, respuesta: str, salida: Any) -> dict[str, Any] | None:
    """Análisis del LLM verificado; None si no queda ninguna unidad literal."""
    if isinstance(salida, str):
        try:
            salida = json.loads(salida)
        except ValueError:
            return None
    if not isinstance(salida, dict) or not isinstance(salida.get("unidades"), list):
        return None
    base = _norm(respuesta)
    unidades, descartadas = [], 0
    for u in salida["unidades"]:
        texto = " ".join(str((u or {}).get("texto") or "").split()) if isinstance(u, dict) else ""
        if not texto or _norm(texto) not in base:
            descartadas += 1
            continue
        unidades.append({
            "texto": texto,
            "marco_temporal": u.get("marco_temporal") if u.get("marco_temporal") in MARCOS else marco_de(texto),
            "funcion": u.get("funcion") if u.get("funcion") in FUNCIONES else "contexto",
            "postura": u.get("postura") if u.get("postura") in POSTURAS else "no_aplica",
        })
    if not unidades:
        return None
    if not any(u["funcion"] == "responde" for u in unidades):
        return None  # sin núcleo: mejor el respaldo por reglas que un análisis vacío
    # En lo que responde, una postura EXPLÍCITA («sí», «ya no», «nunca») manda sobre el juicio del
    # modelo; y la global sale de esas unidades, no de la que redacta el modelo: el de 3B marcaba
    # «ambivalente» a quien cambió de opinión con el tiempo (no antes, sí ahora), mezclando el
    # contexto del pasado con la respuesta (matriz de entrevistas, 22 oct 2026).
    for u in unidades:
        if u["funcion"] == "responde" and (explicita := _postura_explicita(u["texto"])) != "no_aplica":
            u["postura"] = explicita
    postura = _global(unidades, respuesta)
    if postura == "no_aplica" and salida.get("postura") in POSTURAS:
        postura = salida["postura"]
    motivo = " ".join(str(salida.get("motivo") or "").split())
    return {"unidades": unidades, "nucleo": _nucleo(unidades), "postura": postura,
            "motivo": motivo if motivo and _anclado(motivo, respuesta) else "",
            "marco_pregunta": marco_de_pregunta(pregunta), "metodo": "llm", "estado": "propuesto",
            "descartadas": descartadas}


def analizar(pregunta: str, respuesta: str, llm: Any | None = None) -> dict[str, Any]:
    """Análisis con el LLM (`llm(prompt) -> dict|str|None`) y respaldo por reglas."""
    if llm is not None:
        try:
            resultado = validar(pregunta, respuesta, llm(prompt(pregunta, respuesta)))
        except Exception:  # noqa: BLE001 — el LLM nunca es requisito
            resultado = None
        if resultado is not None:
            return resultado
    return analizar_reglas(pregunta, respuesta)
