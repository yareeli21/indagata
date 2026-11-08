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
# 7 nov (Fase 3): pedir ver personas del grupo anterior («muéstrame 5 de ellos», «muéstrame 5», «dame tres»).
_LISTAR = re.compile(r"^(?:muestrame|muestra|dame|ensename|lista|listame|enlista|dime)\s+(?:a\s+)?(?:los\s+|las\s+|unos\s+|unas\s+)?"
                     r"(\d{1,2}|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|algunos|algunas)\b")
_NUMEROS = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
            "diez": 10, "algunos": 5, "algunas": 5}
# Ver los datos de lo que se acaba de responder («muéstrame los datos tal cual», «muéstrame cómo se repartieron»).
_MOSTRAR = re.compile(r"\b(?:muestrame|muestra|ensename|dame|quiero ver)\s+(?:los\s+datos|la\s+tabla|la\s+distribucion|"
                      r"como\s+se\s+(?:repartieron|distribuyeron|reparten|distribuyen)|el\s+detalle|las\s+cifras)\b"
                      r"|\btal\s+cual\b")
# Una persona en singular sin nombrarla («¿dejó alguno en blanco?», «¿su respuesta al reactivo…?»).
_PERSONA_SINGULAR = re.compile(r"\b(?:su|sus|dejo|respondio|eligio|marco|contesto|escogio|dijo|menciono)\b")
_PLURAL = re.compile(r"\b(?:cuantos|cuantas|quienes|todos|todas|alumnos|respondentes|estudiantes|participantes|"
                     r"personas|ellos|ellas|los que|las que)\b")
_ID_EN_RESPUESTA = re.compile(r"\b([pr]\d{2})\b")

# Intenciones con condiciones sobre las personas: un seguimiento hereda sus condiciones.
_CON_CONDICIONES = {"conteo_porcentaje", "filtrar_respondentes", "comparar_grupos", "resumen_pregunta"}
_SIN_PLAN = {"aclaracion", "fuera_de_dominio", "uso_plataforma", "metodologia"}
# Intenciones con las que el modelo devuelve «¿y sobre X?» cuando se hablaba de lo que dijo una persona.
_SOBRE_LA_PERSONA = {"datos_respondente", "semantica_abierta", "aclaracion", "resumen_pregunta", "hallazgo"}


def relacion(pregunta: str, plan: PlanConsulta, anterior: dict[str, Any] | None) -> str:
    """La relación de la pregunta con la anterior: la de las señales explícitas si las hay; si no, la del modelo.

    Además de las tres del plan, dos internas (7 nov) que `combinar` convierte en «continua»: «listar» (muéstrame N
    del grupo anterior) y «mostrar» (los datos de lo que se acaba de responder)."""
    if not anterior or not anterior.get("intencion"):
        return "nueva"
    texto = normalizar(pregunta)
    palabras = len(texto.split())
    if _LISTAR.search(texto) and _condiciones(anterior):
        return "listar"
    if _MOSTRAR.search(texto) and anterior.get("intencion") in ESTRUCTURADAS:
        return "mostrar"
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
    respuesta_previa = str(anterior.get("_respuesta") or "")
    try:
        previo = PlanConsulta.model_validate({k: v for k, v in anterior.items() if not k.startswith("_")})
    except ValueError:
        return plan, []
    if rel == "listar":
        return _listar(previo, pregunta)
    if rel == "mostrar":
        return _mostrar(previo, respuesta_previa)
    if rel == "profundiza":
        if previo.intencion in _SIN_PLAN:
            return plan.model_copy(update={"relacion": "profundiza"}), []
        return previo.model_copy(update={"relacion": "profundiza"}), [
            f"profundiza: se repite el plan anterior ({previo.intencion}) para explicarlo"]
    return _continuar(plan, previo, recuperadas or [], pregunta, catalogos or [])


def persona_activa(pregunta: str, plan: PlanConsulta, personas: list[str]) -> tuple[PlanConsulta, list[str]]:
    """«¿Dejó alguno en blanco?», «¿su respuesta al reactivo de phishing es la más común?»: una persona en singular sin
    nombrarla es la última de la que se habló en la conversación, aunque el turno anterior no la nombrara (7 nov,
    PRU-15: se perdía en el tercer turno). `personas`: los respondentes del último plan que los tuvo."""
    texto = normalizar(pregunta)
    if not personas or plan.respondentes or not _PERSONA_SINGULAR.search(texto) or _PLURAL.search(texto) \
            or plan.intencion in ("metodologia", "uso_plataforma", "kpi", "ranking_preguntas"):
        return plan, []
    campos = plan.preguntas or (plan.campos if isinstance(plan.campos, list) else "todas_las_respuestas")
    return plan.model_copy(update={"intencion": "datos_respondente", "respondentes": personas, "campos": campos,
                                   "relacion": "continua", "aclaracion": "", "consulta_semantica": ""}), [
        f"continúa con {', '.join(personas)} (la pregunta habla de una persona sin nombrarla)"]


def _conservar_anteriores(plan: PlanConsulta, previo: PlanConsulta, pregunta: str,
                          catalogos: list[Any]) -> tuple[PlanConsulta, list[str]]:
    """En un seguimiento, una condición del grupo anterior se conserva aunque el modelo la cambie, salvo que la consulta
    hable de esa pregunta con palabras que no explica otra condición: «de ellos, ¿cuántos no trabajan?» después de
    «¿cuántos tienen dificultades?» → el modelo puso «dificultades = No» por el «no» de «no trabajan» (7 nov, CEN-03).
    «¿Y los que no tienen dificultades?» sí la cambia: nombra la pregunta."""
    anteriores = {f.pregunta: f for f in previo.filtros}
    textos = {pid: q.texto for cat in catalogos for pid, q in cat.preguntas.items()}
    opciones = {pid: q.opciones for cat in catalogos for pid, q in cat.preguntas.items()}
    raices = enrutador._raices(pregunta)
    nuevos, notas = [], []
    for f in plan.filtros:
        antes = anteriores.get(f.pregunta)
        valores = set(f.valor if isinstance(f.valor, list) else [f.valor])
        previos = set(antes.valor if antes and isinstance(antes.valor, list) else [antes.valor] if antes else [])
        if antes is None or valores & previos or f.nivel or antes.nivel:
            nuevos.append(f)
            continue
        explicadas = {r for g in plan.filtros if g.pregunta != f.pregunta
                      for o in opciones.get(g.pregunta, []) for r in enrutador._raices(o)}
        if (raices - explicadas) & enrutador._raices(textos.get(f.pregunta, "")):
            nuevos.append(f)
        else:
            nuevos.append(antes)
            notas.append(f"filtro {f.pregunta} del grupo anterior conservado (la pregunta no habla de él)")
    return (plan.model_copy(update={"filtros": nuevos}) if notas else plan), notas


def _acotar(filtros: list[Any], pregunta: str, catalogos: list[Any]) -> tuple[list[Any], list[str]]:
    """«De ellos, ¿cuántos la consiguieron por convenio?» / «¿cuántos no trabajan?»: una opción que la consulta nombra
    (por su palabra, con su polaridad) acota el grupo anterior. En la misma pregunta se queda la intersección («Sí, por
    mi cuenta» o «Sí, con convenio» → «Sí, con convenio»); en otra pregunta se suma como condición (7 nov, ENC-13 y
    CEN-03: se repetía el conteo del grupo anterior)."""
    from services import anclaje  # import tardío: anclaje no depende de este módulo
    from services.plan_consulta import Filtro

    nuevos, notas = list(filtros), []
    for cat in catalogos:
        for pid, ops in anclaje.opciones_por_raiz(pregunta, cat, con_ausentes=True).items():
            previo = next((f for f in nuevos if f.pregunta == pid), None)
            if previo is None:
                nuevos.append(Filtro(pregunta=pid, valor=ops if len(ops) > 1 else ops[0]))
                notas.append(f"filtro {pid} = «{', '.join(ops)}» sobre el grupo anterior")
                continue
            valores = previo.valor if isinstance(previo.valor, list) else [previo.valor]
            comunes = [o for o in ops if o in valores]
            if comunes and set(comunes) != set(valores):
                nuevos = [Filtro(pregunta=pid, valor=comunes if len(comunes) > 1 else comunes[0]) if f is previo else f
                          for f in nuevos]
                notas.append(f"filtro {pid} acotado a «{', '.join(comunes)}» (dentro del grupo anterior)")
    return nuevos[:5], notas


def _condiciones(anterior: dict[str, Any]) -> bool:
    return bool(anterior.get("filtros") or anterior.get("contexto") or anterior.get("contexto_num")
                or anterior.get("con_omisiones") or anterior.get("menciona"))


def _listar(previo: PlanConsulta, pregunta: str) -> tuple[PlanConsulta, list[str]]:
    """«Muéstrame 5 de ellos»: N personas del grupo anterior con sus respuestas (el total lo dice el ejecutor)."""
    m = _LISTAR.search(normalizar(pregunta))
    clave = m.group(1) if m else ""
    n = int(clave) if clave.isdigit() else _NUMEROS.get(clave, 5)
    plan = previo.model_copy(update={"intencion": "filtrar_respondentes", "limite": max(1, n), "relacion": "continua",
                                     "campos": "todas_las_respuestas", "orden": None})
    return plan, [f"listar {n} del grupo anterior (sus condiciones, con sus respuestas)"]


def _mostrar(previo: PlanConsulta, respuesta_previa: str) -> tuple[PlanConsulta, list[str]]:
    """«Muéstrame los datos tal cual»: la tabla de lo que se acaba de responder. Tras un ranking, la distribución de la
    pregunta que quedó primero (su ID es el primero que aparece en la respuesta anterior)."""
    if previo.intencion == "ranking_preguntas":
        m = _ID_EN_RESPUESTA.search(respuesta_previa)
        if m:
            return PlanConsulta(intencion="resumen_pregunta", preguntas=[m.group(1)], instrumentos=previo.instrumentos,
                                relacion="continua"), [f"mostrar: distribución de {m.group(1)}, la primera del ranking anterior"]
    if previo.intencion in ("conteo_porcentaje", "hallazgo") and previo.preguntas and not previo.filtros:
        return PlanConsulta(intencion="resumen_pregunta", preguntas=previo.preguntas, instrumentos=previo.instrumentos,
                            relacion="continua"), [f"mostrar: distribución de {', '.join(previo.preguntas)}"]
    return previo.model_copy(update={"relacion": "continua"}), [f"mostrar: se repite el plan anterior ({previo.intencion})"]


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
        plan, conservadas = _conservar_anteriores(plan, previo, pregunta, catalogos or [])
        notas += conservadas
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
        acotados, notas_acotar = _acotar(cambios.get("filtros", plan.filtros), pregunta, catalogos or [])
        if notas_acotar:
            cambios["filtros"] = acotados
            notas += notas_acotar
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
