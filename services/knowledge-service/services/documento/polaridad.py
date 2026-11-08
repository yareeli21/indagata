"""Polaridad de cada pregunta de encuesta: qué respuestas son favorables y cuáles desfavorables (7 nov 2026).

Sin ella, «¿qué es lo más preocupante?» elegía respuestas favorables: «Nunca» en «¿con qué frecuencia te ha tocado un
cambio de profesor ya iniciado el periodo?» es bueno, aunque sea el extremo bajo de la escala. Que un extremo sea
bueno o malo depende del texto de la pregunta, así que la regla no basta.

  - **Modelo** (`origen: "llm"`), una llamada por pregunta, offline, en el mismo trabajo de segundo plano que el
    análisis del documento (`services/analisis.py`):
      · escala ordenada (frecuencia, acuerdo, 1–5): el modelo primero dice qué situación describe la pregunta y luego
        juzga cada EXTREMO por separado (bueno, malo o neutro); solo se acepta si los juicios son opuestos, y las
        listas salen de los niveles de la escala. Pedirle que clasificara cada opción falló justo en el caso difícil
        (con gemma3:4b, «Siempre» quedó como favorable en el cambio de profesor) y un solo juicio invirtió enunciados
        positivos de otra encuesta (7 nov).
      · opciones sin orden: primero si la pregunta solo describe (modalidad, un rango: sin polaridad); si no, clasifica
        cada opción, dos veces con las opciones en distinto orden, y se queda con lo que coincide. Solo se aceptan
        opciones que existen y que no estén en las dos listas.
    Lo que el modelo no decide de forma consistente queda `sin_determinar`. Todo nace `propuesto`: es una sugerencia
    para que el investigador la confirme.
  - **Investigador** (`origen: "investigador"`, `estado: "revisado"`): corrige con
    PATCH /conocimiento/{id}/documento/polaridad/{pregunta}; lo revisado no se vuelve a inferir.
  - Sin modelo, o si contesta algo inválido: `sin_determinar` (el chat no la usa).

Las opciones neutras o sin valor («No lo sé», «Algunas veces», una modalidad) no van en ninguna lista.
"""
from __future__ import annotations

import json
from typing import Any

from services.documento.analisis_entrevista import _norm

# Tipos donde no hay respuestas mejores o peores que decidir (texto libre, números sueltos, listas de varias).
_SIN_POLARIDAD = {"texto_corto", "texto_largo", "abierta", "numerica", "sin_datos", "fecha", "opcion_multiple_varias"}


def opciones_de(pregunta: dict[str, Any]) -> list[str]:
    """Opciones como las ve la persona: las de la pregunta o las etiquetas de su escala."""
    if pregunta.get("opciones"):
        return [str(o) for o in pregunta["opciones"]]
    etiquetas = (pregunta.get("escala") or {}).get("etiquetas") or {}
    return [str(v) for _, v in sorted(etiquetas.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0)]


def aplica(pregunta: dict[str, Any]) -> bool:
    return pregunta.get("tipo") not in _SIN_POLARIDAD and len(opciones_de(pregunta)) >= 2


def prompt(texto: str, opciones: list[str]) -> str:
    lista = "\n".join(f"- {o}" for o in opciones)
    return (
        "Eres analista de una encuesta educativa.\n"
        f"PREGUNTA: {texto}\nOPCIONES:\n{lista}\n\n"
        "1) ¿La pregunta mide una SITUACIÓN que puede ser buena o mala para el estudiante o la institución (logros, "
        "problemas, calidad, retrasos), o solo DESCRIBE una característica sin valor (modalidad, carrera, turno, un "
        "rango sin mejor ni peor)?\n"
        "2) Si mide una situación, di qué opciones son favorables y cuáles desfavorables; las neutras o «No lo sé» en "
        "ninguna. Si solo describe, deja las dos listas vacías.\n"
        'Responde SOLO un JSON: {"tipo": "situacion" | "descriptiva", "favorables": ["..."], "desfavorables": ["..."]}'
    )


def validar(opciones: list[str], salida: Any) -> dict[str, Any] | None:
    """Listas del modelo con opciones existentes y sin cruces; None si no queda nada."""
    if isinstance(salida, str):
        try:
            salida = json.loads(salida)
        except ValueError:
            return None
    if not isinstance(salida, dict):
        return None
    if str(salida.get("tipo") or "").strip().lower() == "descriptiva":
        # Pregunta que solo describe (modalidad, un rango): ninguna respuesta es mejor que otra (7 nov: sin este paso,
        # gemma3:4b marcaba «Presencial» como desfavorable).
        return {"favorables": [], "desfavorables": [], "origen": "llm", "estado": "propuesto"}
    por_norma = {_norm(o): o for o in opciones}

    def lista(clave: str) -> list[str]:
        vistas: list[str] = []
        for x in salida.get(clave) or []:
            o = por_norma.get(_norm(str(x)))
            if o and o not in vistas:
                vistas.append(o)
        return vistas

    fav, desf = lista("favorables"), lista("desfavorables")
    cruce = set(fav) & set(desf)
    fav, desf = [o for o in fav if o not in cruce], [o for o in desf if o not in cruce]
    if not fav and not desf:
        return None
    return {"favorables": fav, "desfavorables": desf, "origen": "llm", "estado": "propuesto"}


def _niveles(pregunta: dict[str, Any]) -> tuple[list[str], list[str]] | None:
    """(etiquetas del nivel bajo, del alto) de una escala ordenada; None si no tiene niveles."""
    escala = pregunta.get("escala") or {}
    etiquetas, niveles = escala.get("etiquetas") or {}, escala.get("niveles") or {}
    # Las escalas de acuerdo nombran sus niveles «desacuerdo / neutral / acuerdo»; las demás, «baja / media / alta».
    bajo, alto = niveles.get("baja") or niveles.get("desacuerdo"), niveles.get("alta") or niveles.get("acuerdo")
    if not etiquetas or not bajo or not alto:
        return None
    def de(puntos: list[Any]) -> list[str]:
        return [str(etiquetas[str(x)]) for x in puntos if str(x) in etiquetas]
    return de(bajo), de(alto)


def prompt_escala(texto: str, baja: str, alta: str, extremo: str | None = None) -> str:
    extremo = extremo or alta
    return (
        f"Pregunta de una encuesta a estudiantes: «{texto}». Escala de «{baja}» a «{alta}».\n"
        f"Primero di qué situación describe la pregunta. Después decide: si un estudiante responde «{extremo}», ¿eso es "
        "bueno, malo o ni bueno ni malo para su formación o para la institución?\n"
        'Responde SOLO un JSON: {"situacion": "...", "juicio": "bueno" | "malo" | "neutro"}'
    )


def _juicio(salida: Any) -> str:
    if isinstance(salida, str):
        try:
            salida = json.loads(salida)
        except ValueError:
            return ""
    if not isinstance(salida, dict):
        return ""
    return str(salida.get("juicio") or salida.get("extremo_alto") or "").strip().lower()


def _por_escala(pregunta: dict[str, Any], llm: Any) -> dict[str, Any] | None:
    """Pregunta por los DOS extremos por separado y solo acepta si los juicios son opuestos (consistencia).

    Con una sola pregunta gemma3:4b invirtió enunciados positivos de la encuesta 61 («La carga de trabajo me permite
    mantener un equilibrio saludable»: el acuerdo quedaba como desfavorable, 7 nov).
    """
    niveles = _niveles(pregunta)
    if niveles is None:
        return None
    baja, alta = niveles
    texto = str(pregunta.get("texto") or "")
    alto = _juicio(llm(prompt_escala(texto, baja[0], alta[-1], alta[-1])))
    bajo = _juicio(llm(prompt_escala(texto, baja[0], alta[-1], baja[0])))
    if {alto, bajo} != {"bueno", "malo"}:
        return None
    fav, desf = (alta, baja) if alto == "bueno" else (baja, alta)
    return {"favorables": fav, "desfavorables": desf, "origen": "llm", "estado": "propuesto"}


def _por_opciones(pregunta: dict[str, Any], llm: Any) -> dict[str, Any] | None:
    """Clasifica las opciones DOS veces, en orden normal e invertido, y se queda con lo que coincide.

    Si una vez dice «descriptiva» y la otra no, no se decide (gemma3:4b dejó sin polaridad la acreditación en una
    corrida y la marcó en otra).
    """
    opciones, texto = opciones_de(pregunta), str(pregunta.get("texto") or "")
    a = validar(opciones, llm(prompt(texto, opciones)))
    b = validar(opciones, llm(prompt(texto, list(reversed(opciones)))))
    if a is None or b is None:
        return None
    fav = [o for o in a["favorables"] if o in b["favorables"]]
    desf = [o for o in a["desfavorables"] if o in b["desfavorables"]]
    descriptiva_a, descriptiva_b = not (a["favorables"] or a["desfavorables"]), not (b["favorables"] or b["desfavorables"])
    if descriptiva_a != descriptiva_b or (not descriptiva_a and not fav and not desf):
        return None
    return {"favorables": fav, "desfavorables": desf, "origen": "llm", "estado": "propuesto"}


def inferir(pregunta: dict[str, Any], llm: Any | None = None) -> dict[str, Any]:
    if llm is not None and aplica(pregunta):
        try:
            resultado = _por_escala(pregunta, llm) if _niveles(pregunta) else _por_opciones(pregunta, llm)
        except Exception:  # noqa: BLE001 — el modelo nunca es requisito
            resultado = None
        if resultado is not None:
            return resultado
    return {"favorables": [], "desfavorables": [], "origen": "sin_determinar", "estado": "propuesto"}
