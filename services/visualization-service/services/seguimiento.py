"""Hilo de la conversación (B, 7 nov): una conversación puede pasar de un tema a otro y volver a precisar el anterior.

Cada pregunta se relaciona con la respuesta anterior de una de tres formas:
  - «nueva»: empieza limpio aunque venga después de otra cosa («¿qué patrones hay entre los amigos?»);
  - «continua»: conserva las condiciones del plan anterior y suma o cambia lo que la pregunta dice
    («de ellos, ¿cuántos trabajan?», «¿y los que tienen beca contra los que no?», «¿y sobre los psicólogos?»);
  - «profundiza»: repite el plan anterior para explicarlo («¿por qué?», «¿qué significa eso?», «¿en qué te basas?»).

La interpretación (LLM) propone la relación en el campo `relacion` del plan; unas señales explícitas de la pregunta la
confirman o la corrigen, porque el modelo de 3–4B la olvida a menudo. La herencia se hace sobre el PLAN ANTERIOR
guardado en rag_log (sus condiciones exactas, ya validadas), no sobre el texto: desde el texto se heredaban
condiciones equivocadas (consulta 2149: «p01 = Sí» porque el enunciado sucio de p01 empieza con «Cargas máxima») y se
perdían otras (2187: la pregunta del phishing; 2189: «más de 20 horas»).
"""
from __future__ import annotations

import re
from typing import Any

from services import enrutador
from services.dominio import normalizar
from services.plan_consulta import ESTRUCTURADAS, PlanConsulta

# «de ellos», «entre esos», «a esos»: se habla del grupo anterior.
_GRUPO_ANTERIOR = re.compile(r"\b(?:de|entre|a|con|para) (?:ellos|ellas|esos|esas|estos|estas|aquellos|aquellas)\b")
# «¿Y …?» al inicio de una pregunta corta: precisa la anterior («¿Y R0067?», «¿y sobre los psicólogos?»).
_Y_INICIAL = re.compile(r"^\s*y\b")
_MAX_PALABRAS_Y = 12
# Pedir que se explique lo anterior.
_EXPLICAR = re.compile(r"\b(?:por que|a que se debe|que significa\w*|que quiere decir|que puede significa\w*|"
                       r"explica\w*|interpreta\w*|profundiza\w*)\b")
# Estas solo tienen sentido sobre lo que se acaba de responder.
_EXPLICAR_ANTERIOR = re.compile(r"\b(?:en que te basas|como lo sabes|a que te refieres|por que (?:lo )?consideras|"
                                r"por que (?:lo )?crees|por que dices)\b")
# Referencias a lo dicho antes: con ellas, «¿por qué…?» es sobre la respuesta anterior y no una pregunta nueva.
_LO_ANTERIOR = re.compile(r"\b(?:eso|esto|ello|lo anterior|lo que (?:me )?dijiste|el dato|ese dato|ese resultado|esa "
                          r"respuesta|la anterior|esa pregunta|nadie la|la (?:contest|respond)\w*)\b")
_MAX_PALABRAS_EXPLICAR = 6  # «¿por qué?», «¿y eso qué significa?»: sin referencia explícita, solo si es corta

# Intenciones con condiciones sobre las personas: un seguimiento hereda sus condiciones.
_CON_CONDICIONES = {"conteo_porcentaje", "filtrar_respondentes", "comparar_grupos", "resumen_pregunta"}
_SIN_PLAN = {"aclaracion", "fuera_de_dominio", "uso_plataforma", "metodologia"}
# Intenciones con las que el modelo devuelve «¿y sobre X?» cuando se hablaba de lo que dijo una persona.
_SOBRE_LA_PERSONA = {"datos_respondente", "semantica_abierta", "aclaracion", "resumen_pregunta", "hallazgo"}


def relacion(pregunta: str, plan: PlanConsulta, anterior: dict[str, Any] | None) -> str:
    """La relación de la pregunta con la anterior: la de las señales explícitas si las hay; si no, la del modelo."""
    if not anterior or not anterior.get("intencion"):
        return "nueva"
    texto = normalizar(pregunta)
    palabras = len(texto.split())
    if _GRUPO_ANTERIOR.search(texto):
        return "continua"
    explicita = bool(enrutador._preguntas(texto)) or bool(enrutador._persona(texto))
    if not explicita and (_EXPLICAR_ANTERIOR.search(texto) or (
            _EXPLICAR.search(texto) and plan.intencion != "metodologia"
            and (_LO_ANTERIOR.search(texto) or palabras <= _MAX_PALABRAS_EXPLICAR))):
        return "profundiza"
    if _Y_INICIAL.search(texto) and palabras <= _MAX_PALABRAS_Y:
        return "continua"
    if plan.relacion == "profundiza" and explicita:
        return "continua"  # nombra otra persona o pregunta: no es repetir lo anterior
    return plan.relacion


def combinar(plan: PlanConsulta, anterior: dict[str, Any] | None, rel: str,
             recuperadas: list[str] | None = None, pregunta: str = "",
             catalogos: list[Any] | None = None) -> tuple[PlanConsulta, list[str]]:
    """El plan con lo que hereda del anterior según la relación, y las notas para `rag_log.plan.correcciones`.

    `recuperadas`: preguntas de los intercambios que recuperó el RAG (en una entrevista dicen en qué pregunta habló
    la persona del tema nuevo: «¿y sobre los psicólogos?» → p04, p07)."""
    if rel == "nueva" or not anterior:
        return (plan if plan.relacion == "nueva" else plan.model_copy(update={"relacion": "nueva"})), []
    try:
        previo = PlanConsulta.model_validate(anterior)
    except ValueError:
        return plan, []
    if rel == "profundiza":
        if previo.intencion in _SIN_PLAN:
            return plan.model_copy(update={"relacion": "profundiza"}), []
        return previo.model_copy(update={"relacion": "profundiza"}), [
            f"profundiza: se repite el plan anterior ({previo.intencion}) para explicarlo"]
    return _continuar(plan, previo, recuperadas or [], pregunta, catalogos or [])


def _preguntas_dichas(pregunta: str, preguntas: list[str], catalogos: list[Any]) -> bool:
    """¿La consulta nombra esas preguntas, por su número o por una palabra de su enunciado?"""
    texto = normalizar(pregunta)
    if enrutador._preguntas(texto):
        return True
    raices = enrutador._raices(texto)
    for cat in catalogos:
        for q in preguntas:
            if q in cat.preguntas and enrutador._raices(cat.preguntas[q].texto) & raices:
                return True
    return False


def _continuar(plan: PlanConsulta, previo: PlanConsulta, recuperadas: list[str], pregunta: str = "",
               catalogos: list[Any] | None = None) -> tuple[PlanConsulta, list[str]]:
    cambios: dict[str, Any] = {"relacion": "continua"}
    notas: list[str] = []
    intencion = plan.intencion
    if not plan.instrumentos and previo.instrumentos:
        cambios["instrumentos"] = previo.instrumentos
    # Lo que dijo una persona: «¿y sobre los psicólogos?» sigue con la misma persona y busca el tema en sus respuestas.
    # El modelo la dio como búsqueda abierta, aclaración, resumen de una pregunta o hallazgo (consultas 2176 y 2219).
    if previo.intencion == "datos_respondente" and previo.respondentes and not plan.respondentes \
            and intencion in _SOBRE_LA_PERSONA and not plan.orden and not plan.filtros and not plan.agrupar_por:
        propias = plan.campos if isinstance(plan.campos, list) and intencion == "datos_respondente" else plan.preguntas
        campos = list(dict.fromkeys([*propias, *recuperadas]))[:3] or "todas_las_respuestas"
        cambios.update(intencion="datos_respondente", respondentes=previo.respondentes, campos=campos,
                       consulta_semantica="", aclaracion="")
        notas.append(f"continúa con {', '.join(previo.respondentes)}"
                     + (f" en {', '.join(campos)}" if isinstance(campos, list) else ""))
        return plan.model_copy(update=cambios), notas
    # Otra persona, lo mismo: «¿Y R0067?» después de «¿qué contestó R0057 en las de verdadero o falso?».
    if previo.intencion == "datos_respondente" and intencion == "datos_respondente" and plan.respondentes \
            and isinstance(previo.campos, list) and not isinstance(plan.campos, list):
        cambios["campos"] = previo.campos
        notas.append(f"preguntas {', '.join(previo.campos)} heredadas del plan anterior")
    if intencion in _SIN_PLAN or intencion not in ESTRUCTURADAS:
        return plan.model_copy(update=cambios), notas
    if previo.intencion in _CON_CONDICIONES and intencion in _CON_CONDICIONES:
        propias = {f.pregunta for f in plan.filtros}
        heredados = [f for f in previo.filtros if f.pregunta not in propias]
        if heredados:
            cambios["filtros"] = [*plan.filtros, *heredados][:5]
            notas += [f"filtro {f.pregunta} heredado del plan anterior" for f in heredados]
        contexto = {k: v for k, v in previo.contexto.items() if k not in plan.contexto and k != plan.agrupar_por}
        if contexto:
            cambios["contexto"] = {**contexto, **plan.contexto}
            notas += [f"contexto {k} = «{v}» heredado del plan anterior" for k, v in contexto.items()]
        variables = {c.variable for c in plan.contexto_num}
        numericas = [c for c in previo.contexto_num if c.variable not in variables]
        if numericas:
            cambios["contexto_num"] = [*plan.contexto_num, *numericas][:3]
            notas += [f"contexto {c.variable} {c.op} {c.valor:g} heredado del plan anterior" for c in numericas]
        if previo.con_omisiones and not plan.con_omisiones and intencion != "comparar_grupos":
            cambios["con_omisiones"] = True
    # La misma pregunta del instrumento: «¿y los que tienen beca contra los que no?» después de comparar el phishing.
    if intencion in ("comparar_grupos", "resumen_pregunta") and plan.preguntas and previo.preguntas             and plan.preguntas != previo.preguntas and pregunta and catalogos             and not _preguntas_dichas(pregunta, plan.preguntas, catalogos):
        # «¿Y los que tienen beca contra los que no?» no nombra ninguna pregunta: el modelo puso r01 y se perdió la
        # del phishing (consulta 2259). Una pregunta que la consulta no dice no reemplaza a la anterior.
        notas.append(f"preguntas {', '.join(plan.preguntas)} descartadas (la consulta no las nombra)")
        plan = plan.model_copy(update={"preguntas": []})
    if intencion in ("comparar_grupos", "resumen_pregunta") and not plan.preguntas and previo.preguntas:
        cambios["preguntas"] = previo.preguntas
        if previo.nivel and not plan.nivel:
            cambios["nivel"] = previo.nivel
        notas.append(f"preguntas {', '.join(previo.preguntas)} heredadas del plan anterior")
    return plan.model_copy(update=cambios), notas


def resumen_plan(plan: dict[str, Any] | None) -> str:
    """Las condiciones del plan anterior en una línea, para que la interpretación sepa de qué se habló."""
    if not plan:
        return ""
    partes = []
    if plan.get("respondentes"):
        partes.append("respondentes " + ", ".join(plan["respondentes"][:5]))
    if plan.get("preguntas"):
        partes.append("preguntas " + ", ".join(plan["preguntas"][:5]))
    for f in plan.get("filtros") or []:
        valor = f.get("nivel") or f.get("valor")
        partes.append(f"{f.get('pregunta')} {f.get('op', '=')} {valor}")
    partes += [f"{k} = {v}" for k, v in (plan.get("contexto") or {}).items()]
    partes += [f"{c.get('variable')} {c.get('op', '>')} {c.get('valor')}" for c in plan.get("contexto_num") or []]
    if plan.get("agrupar_por"):
        partes.append(f"por {plan['agrupar_por']}")
    if plan.get("con_omisiones"):
        partes.append("dejaron alguna pregunta sin responder")
    return "Condiciones: " + "; ".join(partes) if partes else ""
