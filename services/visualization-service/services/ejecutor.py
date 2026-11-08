"""Etapa 2 del chat: ejecución determinista del plan (sin LLM).

Traduce un `PlanConsulta` ya validado (`plan_consulta.py`, `anclaje.py`) a cálculos sobre el documento final vigente
de cada instrumento: el mismo documento del que salen `respuesta_interpretada` y los chunks del RAG. Solo hay
operaciones permitidas (filtrar, contar, ordenar por ID, limitar, agrupar por contexto, leer resúmenes); el plan
nunca se convierte en SQL. Reglas:
  - `limite` siempre tiene tope (`LIMITE_MAX`; 10 personas cuando se piden todas sus respuestas);
  - se respeta `orden`, `limite` y `campos`;
  - nunca se devuelven variables de contexto con datos personales (nombre, correo, matrícula…);
  - el resultado dice el criterio aplicado y cuántos cumplen en total, y si quedó vacío lo dice.

El resultado (`Ejecucion`) lleva líneas con cifras, tablas y las fuentes realmente usadas (instrumento, preguntas,
respondentes, KPIs), que son las que se mostrarán como fuentes de la respuesta. Las intenciones semánticas
(`semantica_abierta`, `metodologia`, `uso_plataforma`) y las de control (`fuera_de_dominio`, `aclaracion`) no pasan
por aquí.
"""
from __future__ import annotations

import math

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from shared.conocimiento import consultas
from shared.models.limpieza_ejecucion import LimpiezaEjecucion

from services import hallazgos
from services.dominio import normalizar
from services.enrutador import Instrumento
from services.plan_consulta import ESTRUCTURADAS, LIMITE_MAX, CondicionContexto, Filtro, PlanConsulta

_MAX_CON_RESPUESTAS = 10  # personas con todas sus respuestas en una tabla
_LIMITE_IDS = 20  # IDs mostrados si el plan no da límite (7 nov: el total, los primeros 20 y la opción de pedir más)
_MAX_TEXTO_PREGUNTA = 70
_PERSONALES = re.compile(r"nombre|apellido|correo|e-?mail|telefono|celular|matricula|curp|rfc|direccion|domicilio")
# Sinónimos de nivel: el documento usa «alta/media/baja» o «acuerdo/neutral/desacuerdo» según la escala.
_NIVELES = {
    "alto": {"alta", "alto", "acuerdo"}, "acuerdo": {"alta", "alto", "acuerdo"},
    "medio": {"media", "medio", "neutral"}, "neutral": {"media", "medio", "neutral"},
    "bajo": {"baja", "bajo", "desacuerdo"}, "desacuerdo": {"baja", "bajo", "desacuerdo"},
}
_NOMBRE_NIVEL = {"alto": "nivel alto", "acuerdo": "de acuerdo (nivel alto)", "medio": "nivel medio",
                 "neutral": "neutral (nivel medio)", "bajo": "nivel bajo", "desacuerdo": "en desacuerdo (nivel bajo)"}


@dataclass
class Tabla:
    titulo: str
    columnas: list[str]
    filas: list[list[str]]

    def markdown(self) -> str:
        cab = "| " + " | ".join(self.columnas) + " |"
        sep = "|" + "---|" * len(self.columnas)
        cuerpo = ["| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in f) + " |" for f in self.filas]
        return "\n".join([f"**{self.titulo}**", cab, sep, *cuerpo])


@dataclass
class Ejecucion:
    """Resultado calculado de un plan sobre un instrumento."""

    intencion: str
    instrumento: Instrumento
    criterio: str = ""  # «los 5 primeros por número de respondente que cumplen p03 = Carga minima»
    lineas: list[str] = field(default_factory=list)
    tablas: list[Tabla] = field(default_factory=list)
    total: int | None = None  # cuántos cumplen en total (filtros)
    mostrados: int | None = None
    vacio: bool = False
    candidatos: list[dict[str, Any]] = field(default_factory=list)  # hallazgo
    preguntas: list[str] = field(default_factory=list)  # IDs completos usados (fuentes)
    respondentes: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)

    def texto(self) -> str:
        """El resultado como texto para la redacción (y para verificar sus cifras)."""
        partes = [f"Instrumento: {self.instrumento.titulo} ({self.instrumento.tipo_ui})"]
        if self.criterio:
            partes.append(f"Criterio: {self.criterio}")
        partes += self.lineas
        partes += [t.markdown() for t in self.tablas]
        return "\n".join(partes)


# ── Utilidades sobre el documento ──────────────────────────────────────────────


def _corto(id_completo: str) -> str:
    return str(id_completo or "").rsplit("-", 1)[-1]


def _items(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return doc.get("preguntas") or doc.get("reactivos") or []


def _pregunta(doc: dict[str, Any], corto: str) -> dict[str, Any] | None:
    return next((p for p in _items(doc) if _corto(p["id"]) == corto), None)


def _texto_pregunta(doc: dict[str, Any], corto: str) -> str:
    p = _pregunta(doc, corto)
    return f"{corto} «{(p or {}).get('texto', '')[:_MAX_TEXTO_PREGUNTA]}»"


def _personas(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Respondentes (encuesta), alumnos (prueba) o participantes (entrevista), con sus respuestas por pregunta corta."""
    if doc.get("entrevistas"):
        return [{"id": e.get("participante", ""), "contexto": e.get("contexto") or {},
                 "por_pregunta": {_corto(i.get("pregunta_id", "")): {"estado": "respondida", "significado": i.get("respuesta", "")}
                                  for i in e.get("intercambios") or []}} for e in doc["entrevistas"]]
    salida = []
    for r in doc.get("respondentes") or doc.get("alumnos") or []:
        por = {}
        for x in r.get("respuestas") or []:
            pid = _corto(x.get("pregunta_id") or x.get("reactivo_id") or "")
            estado = "respondida" if x.get("estado") in ("respondida", "valida") else x.get("estado")
            por[pid] = {**x, "estado": estado, "significado": x.get("significado") or x.get("respuesta") or x.get("valor")}
        salida.append({"id": r.get("id", ""), "contexto": r.get("contexto") or {}, "por_pregunta": por})
    return salida


def _mostrar(x: dict[str, Any] | None) -> str:
    if not x:
        return "(sin dato)"
    if x.get("estado") != "respondida":
        return {"sin_respuesta": "(sin respuesta)", "no_interpretada": "(no interpretada)", "nula": "(nula)"}.get(
            str(x.get("estado")), f"({x.get('estado')})")
    return str(x.get("significado") if x.get("significado") not in (None, "") else x.get("valor", ""))


def _contexto_seguro(contexto: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in contexto.items() if not _PERSONALES.search(normalizar(k))}


def _cumple(persona: dict[str, Any], f: Filtro) -> bool:
    x = persona["por_pregunta"].get(f.pregunta)
    if f.nivel is not None:
        return _en_nivel(x, f.nivel)
    if f.op in (">", ">=", "<", "<=") and isinstance(f.valor, (int, float)):
        return consultas.cumple(x, {"comparacion": [f.op, f.valor]})
    valores = [str(v) for v in (f.valor if isinstance(f.valor, list) else [f.valor])]
    dentro = consultas.cumple(x, {"valores": valores})
    if f.op == "!=":
        return bool(x) and x.get("estado") == "respondida" and not dentro
    return dentro


def _en_nivel(x: dict[str, Any] | None, nivel: str) -> bool:
    return bool(x) and x.get("estado") == "respondida" and normalizar(str(x.get("nivel") or "")) in _NIVELES[nivel]


def _describir(doc: dict[str, Any], f: Filtro) -> str:
    if f.nivel is not None:
        return f"{_texto_pregunta(doc, f.pregunta)} {_NOMBRE_NIVEL[f.nivel]}"
    valor = " o ".join(f"«{v}»" for v in f.valor) if isinstance(f.valor, list) else (
        f"{f.valor:g}" if isinstance(f.valor, (int, float)) else f"«{f.valor}»")
    return f"{_texto_pregunta(doc, f.pregunta)} {f.op} {valor}"


def _clave_id(persona: dict[str, Any]) -> tuple[str, int]:
    """Orden por número de respondente: como texto, «R999» quedaba después de «R2000» y «el último respondente»
    era R999 (28 oct, regresión C10)."""
    corto = _corto(persona["id"])
    m = re.match(r"([A-Za-z]*)(\d+)$", corto)
    return (m.group(1), int(m.group(2))) if m else (corto, 0)


def _ordenar(personas: list[dict[str, Any]], plan: PlanConsulta) -> list[dict[str, Any]]:
    desc = bool(plan.orden and plan.orden.dir == "desc")
    return sorted(personas, key=_clave_id, reverse=desc)


def _frase_orden(plan: PlanConsulta, n: int) -> str:
    desc = bool(plan.orden and plan.orden.dir == "desc")
    return f"los {n} {'últimos' if desc else 'primeros'} por número de respondente" if n > 1 else \
        f"el {'último' if desc else 'primero'} por número de respondente"


def _columnas_respuestas(doc: dict[str, Any], plan: PlanConsulta) -> list[str]:
    if isinstance(plan.campos, list):
        return plan.campos
    return [_corto(p["id"]) for p in _items(doc)]


def _tabla_respuestas(doc: dict[str, Any], personas: list[dict[str, Any]], pids: list[str]) -> Tabla:
    """Una fila por pregunta y una columna por persona: «Pregunta | R002 | R006 …»."""
    filas = [[_texto_pregunta(doc, pid), *(_mostrar(p["por_pregunta"].get(pid)) for p in personas)] for pid in pids]
    contexto = sorted({k for p in personas for k in _contexto_seguro(p["contexto"])})
    filas = [[f"Contexto: {k}", *(str(p["contexto"].get(k, "")) for p in personas)] for k in contexto] + filas
    return Tabla("Respuestas interpretadas", ["Pregunta", *(_corto(p["id"]) for p in personas)], filas)


# ── Ejecutores por intención ───────────────────────────────────────────────────


def _datos_respondente(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc, personas = ins.doc, _personas(ins.doc)
    if plan.respondentes:
        elegidos = [p for p in personas if _corto(p["id"]) in plan.respondentes]
        e.criterio = "respondentes " + ", ".join(plan.respondentes)
    else:
        n = min(plan.limite or 1, _MAX_CON_RESPUESTAS)
        elegidos = _ordenar(personas, plan)[:n]
        e.criterio = f"{_frase_orden(plan, n)} (de {len(personas)})"
    if not elegidos:
        e.vacio = True
        e.lineas.append("No hay respondentes que coincidan.")
        return
    pids = _columnas_respuestas(doc, plan)
    e.tablas.append(_tabla_respuestas(doc, elegidos, pids))
    e.mostrados, e.total = len(elegidos), len(personas)
    e.respondentes = [p["id"] for p in elegidos]
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in pids]


def _numero_texto(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _cumple_contexto(persona: dict[str, Any], c: CondicionContexto) -> bool:
    """«horas_trabajo_semana > 20»: quien no tiene el dato (o no es un número) no cumple."""
    try:
        v = float(str(persona["contexto"].get(c.variable, "")).replace(",", "."))
    except ValueError:
        return False
    return {"=": v == c.valor, "!=": v != c.valor, ">": v > c.valor, ">=": v >= c.valor,
            "<": v < c.valor, "<=": v <= c.valor}[c.op]


# Tipos de pregunta con respuesta abierta (en las entrevistas, todas lo son).
_ABIERTAS = {"texto_largo", "texto_corto", "texto", "abierta", "pregunta_abierta"}
_MAX_CITAS = 8


_RELLENO_TERMINO = {"como", "para", "sobre", "acerca", "tipo", "algun", "alguna", "tema", "temas", "cosas"}


def _raices_termino(termino: str) -> list[str]:
    """Raíz de 5 letras de cada palabra con contenido: «estrés» → «estre» (encuentra «estresada»)."""
    return [w[:5] for w in re.findall(r"[a-z0-9]+", normalizar(termino)) if len(w) >= 4 and w not in _RELLENO_TERMINO]


def grupos_termino(termino: str) -> list[list[str]]:
    """«estrés o ansiedad» → [["estre"], ["ansie"]] (cualquiera de los dos); «familia como apoyo» → [["famil"]]: lo que
    va después de «como / para / sobre» califica al tema, no es otra palabra que deba aparecer (7 nov, ENT-06 y CET-01:
    se buscaba la frase entera y daba 0)."""
    base = re.split(r"\b(?:como|para|sobre|acerca de)\b", normalizar(termino))[0]
    return [r for g in re.split(r"\s+o\s+|,|/|\s+u\s+", base) if (r := _raices_termino(g))]


def _plano(texto: str) -> str:
    """Minúsculas y sin acentos, letra por letra (misma longitud que el original, a diferencia de `normalizar`)."""
    return "".join((unicodedata.normalize("NFD", c)[0] if c.isalpha() else c).lower() for c in texto)


def _menciones(doc: dict[str, Any], persona: dict[str, Any], plan: PlanConsulta) -> list[tuple[str, str]]:
    """(pregunta, fragmento) de cada respuesta abierta de la persona que contiene TODAS las palabras del término."""
    grupos = grupos_termino(plan.menciona)
    if not grupos:
        return []
    entrevista = bool(doc.get("entrevistas"))
    abiertas = {_corto(p["id"]) for p in _items(doc) if entrevista or str(p.get("tipo", "")) in _ABIERTAS}
    salida = []
    for q, x in persona["por_pregunta"].items():
        if q not in abiertas or (plan.preguntas and q not in plan.preguntas) or (x or {}).get("estado") != "respondida":
            continue
        texto = str(x.get("significado") or "")
        normal = _plano(texto)
        for raices in grupos:  # basta un grupo («estrés o ansiedad»); dentro de un grupo, todas sus palabras
            posiciones = [m.start() for r in raices if (m := re.search(rf"\b{re.escape(r)}", normal))]
            if len(posiciones) == len(raices):
                break
        if len(posiciones) == len(raices):
            i = posiciones[0]  # _plano conserva la longitud: la posición sirve en el texto original
            salida.append((q, ("…" if i > 50 else "") + texto[max(0, i - 50):i + 70].strip() + ("…" if i + 70 < len(texto) else "")))
    return salida


def _tabla_menciones(doc: dict[str, Any], personas: list[dict[str, Any]], plan: PlanConsulta) -> Tabla:
    filas = [[_corto(p["id"]), q, f"«{frag}»"] for p in personas for q, frag in _menciones(doc, p, plan)]
    return Tabla(f"Dónde se menciona «{plan.menciona}»", ["Respondente", "Pregunta", "Fragmento"], filas[:_MAX_CITAS])


def _omisiones(persona: dict[str, Any], preguntas: list[str]) -> int:
    """Cuántas de las preguntas dejó sin respuesta válida (sin respuesta, nula o sin dato)."""
    return sum((persona["por_pregunta"].get(q) or {}).get("estado") != "respondida" for q in preguntas)


MAS_OMITIDAS = "Preguntas que más dejaron sin responder"
_TOP_OMITIDAS = 3


def _mas_omitidas(doc: dict[str, Any], grupo: list[dict[str, Any]], plan: PlanConsulta) -> str:
    """Qué preguntas explican las omisiones del grupo: «38 de 38 dejaron alguna sin responder» se entiende cuando se
    ve que nadie respondió r10 (consulta 2233, 7 nov)."""
    preguntas = [_corto(p["id"]) for p in _items(doc) if _corto(p["id"]) not in plan.excluir_preguntas]
    conteo = sorted(((sum(_omisiones(p, [q]) for p in grupo), q) for q in preguntas), key=lambda x: -x[0])
    partes = [f"{_texto_pregunta(doc, q)} ({n} de {len(grupo)})" for n, q in conteo[:_TOP_OMITIDAS] if n]
    return f"{MAS_OMITIDAS}: " + "; ".join(partes) + "."


def _filtrados(ins: Instrumento, plan: PlanConsulta) -> tuple[list[dict[str, Any]], list[str]]:
    """Personas que cumplen TODOS los filtros (y el nivel en las preguntas del plan, si lo hay)."""
    doc = ins.doc
    condiciones = ([f"{k} = «{v}»" for k, v in plan.contexto.items()]
                   + [f"{c.variable} {c.op} {_numero_texto(c.valor)}" for c in plan.contexto_num]
                   + [_describir(doc, f) for f in plan.filtros]
                   + ([f"mencionan «{plan.menciona}» en sus respuestas abiertas"
                       + (f" ({', '.join(plan.preguntas)})" if plan.preguntas else "")] if plan.menciona else [])
                   + (["dejaron alguna pregunta sin responder"] if plan.con_omisiones else []))
    preguntas = [_corto(p["id"]) for p in _items(doc) if _corto(p["id"]) not in plan.excluir_preguntas]
    personas = [p for p in _personas(doc)
                if all(normalizar(str(p["contexto"].get(k, ""))) == normalizar(v) for k, v in plan.contexto.items())
                and all(_cumple_contexto(p, c) for c in plan.contexto_num)
                and all(_cumple(p, f) for f in plan.filtros)
                and (not plan.menciona or _menciones(doc, p, plan))
                and (not plan.con_omisiones or _omisiones(p, preguntas))]
    if plan.nivel and plan.preguntas and plan.intencion == "filtrar_respondentes":
        personas = [p for p in personas if all(_en_nivel(p["por_pregunta"].get(q), plan.nivel) for q in plan.preguntas)]
        condiciones += [f"{_texto_pregunta(doc, q)} en {_NOMBRE_NIVEL[plan.nivel]}" for q in plan.preguntas]
    return personas, condiciones


def _filtrar_respondentes(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc, total = ins.doc, len(_personas(ins.doc))
    cumplen, condiciones = _filtrados(ins, plan)
    cumplen = _ordenar(cumplen, plan)
    con_respuestas = plan.campos != "solo_ids"
    n = min(plan.limite or (5 if con_respuestas else _LIMITE_IDS), _MAX_CON_RESPUESTAS if con_respuestas else LIMITE_MAX)
    inicio = plan.desde or 0
    mostrados = cumplen[inicio:inicio + n]
    e.criterio = " y ".join(condiciones) or "sin condiciones"
    e.total, e.mostrados = len(cumplen), len(mostrados)
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in {f.pregunta for f in plan.filtros} | set(plan.preguntas)]
    pct = round(100 * len(cumplen) / total, 1) if total else 0.0
    e.lineas.append(f"Cumplen la condición {len(cumplen)} de {total} respondentes ({pct} %).")
    if not cumplen:
        e.vacio = True
        return
    if plan.con_omisiones:
        e.lineas.append(_mas_omitidas(doc, cumplen, plan))
    if inicio:
        e.lineas.append(f"Se muestran del {inicio + 1} al {inicio + len(mostrados)} de los {len(cumplen)} que la cumplen.")
    else:
        e.lineas.append(f"Se muestran {_frase_orden(plan, len(mostrados))} que la cumplen: {len(mostrados)} de {len(cumplen)}.")
    if inicio + len(mostrados) < len(cumplen):
        e.lineas.append(f"Faltan {len(cumplen) - inicio - len(mostrados)}: pide «muéstrame más» para ver los siguientes.")
    e.respondentes = [p["id"] for p in mostrados]
    if plan.menciona:
        e.tablas.append(_tabla_menciones(doc, mostrados, plan))
    if con_respuestas:
        pids = _columnas_respuestas(doc, plan)
        e.tablas.append(_tabla_respuestas(doc, mostrados, pids))
        e.preguntas = list(dict.fromkeys([*e.preguntas, *(p["id"] for p in _items(doc) if _corto(p["id"]) in pids)]))
    else:
        e.lineas.append("Respondentes: " + ", ".join(_corto(p["id"]) for p in mostrados) + ".")


def _conteo_porcentaje(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc = ins.doc
    total = len(_personas(doc))
    grupo, condiciones = _filtrados(ins, plan)
    hay_condicion = bool(plan.filtros or plan.contexto or plan.contexto_num or plan.menciona or plan.con_omisiones)
    if hay_condicion:
        pct = round(100 * len(grupo) / total, 1) if total else 0.0
        e.criterio = " y ".join(condiciones)
        e.total = len(grupo)
        e.lineas.append(f"Cumplen la condición {len(grupo)} de {total} respondentes ({pct} %).")
        e.vacio = not grupo
        if plan.menciona and grupo:
            raices = [r for g in grupos_termino(plan.menciona) for r in g]
            veces = sum(len(re.findall(rf"\b(?:{'|'.join(map(re.escape, raices))})", _plano(str(x.get("significado") or ""))))
                        for p in grupo for x in p["por_pregunta"].values() if (x or {}).get("estado") == "respondida")
            e.lineas.append(f"Menciones: {veces} palabras que empiezan con {' o '.join(f'«{r}»' for r in raices)} (cuenta la "
                            "misma raíz: «estrés», «estresada»…; no cuenta sinónimos ni expresiones con otras palabras).")
            e.tablas.append(_tabla_menciones(doc, grupo, plan))
        if plan.con_omisiones and (plan.filtros or plan.contexto or plan.contexto_num or plan.menciona):
            # «De esos, ¿cuántos dejaron alguna sin responder?»: la base es el grupo anterior, no todo el instrumento
            # (consulta 2261: «38 de 97 dejaron alguna pregunta sin responder» eran 38 de 38).
            base, _ = _filtrados(ins, plan.model_copy(update={"con_omisiones": False}))
            pct_base = round(100 * len(grupo) / len(base), 1) if base else 0.0
            e.lineas.append(f"De los {len(base)} que cumplen las demás condiciones, {len(grupo)} ({pct_base} %) "
                            "dejaron alguna pregunta sin responder.")
        if plan.con_omisiones and grupo:
            e.lineas.append(_mas_omitidas(doc, grupo, plan))
        objetivo = [q for q in plan.preguntas if q not in {f.pregunta for f in plan.filtros}]
        if objetivo and not plan.nivel and grupo:
            # «De ellos, ¿qué respondieron sobre el Wi-Fi?»: además del conteo, cómo respondió ESE grupo.
            _cruce(ins, plan, e, grupo, condiciones, objetivo)
    preguntas = plan.preguntas
    if plan.nivel and preguntas:
        base = grupo if hay_condicion else _personas(doc)
        for q in preguntas:
            validas = [p for p in base if (p["por_pregunta"].get(q) or {}).get("estado") == "respondida"]
            en = sum(_en_nivel(p["por_pregunta"].get(q), plan.nivel) for p in validas)
            pct = round(100 * en / len(validas), 1) if validas else 0.0
            quien = "de quienes cumplen la condición y respondieron" if hay_condicion else "de quienes respondieron"
            e.lineas.append(f"{_texto_pregunta(doc, q)}: {en} de {len(validas)} {quien} están {_NOMBRE_NIVEL[plan.nivel]} ({pct} %).")
        e.criterio = e.criterio or f"{_NOMBRE_NIVEL[plan.nivel]} en " + ", ".join(preguntas)
    elif preguntas and not hay_condicion:
        _resumen_pregunta(ins, plan, e)
        return
    elif not hay_condicion:
        e.lineas.append(f"El instrumento tiene {total} respondentes.")
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in {f.pregunta for f in plan.filtros} | set(preguntas)]


_BOOLEANOS = {"true": "Sí", "false": "No"}


def _legible(valor: Any) -> str:
    """«True»/«False» de una variable de sí/no se muestran «Sí»/«No»: con «True | 14» y «False | 83» el modelo dio a
    los becados las cifras de los no becados (consulta 2264)."""
    return _BOOLEANOS.get(str(valor).strip().lower(), str(valor))


POSICION, SECCION = "posicion", "seccion"
_VACIOS = {"(sin respuesta)", "(nula)", "(no interpretada)", "(sin dato)"}


def distribucion(doc: dict[str, Any], personas: list[dict[str, Any]], q: str) -> tuple[int, int, dict[str, int], float | None]:
    """(respuestas válidas, sin respuesta, {opción: n} de mayor a menor, media si es numérica) de una pregunta en un
    grupo de personas (7 nov, Fase 4: cruces y comparaciones calculados sobre el grupo, no sobre toda la muestra)."""
    conteo: dict[str, int] = {}
    numeros: list[float] = []
    sin = 0
    for persona in personas:
        x = persona["por_pregunta"].get(q)
        if not x or x.get("estado") != "respondida":
            sin += 1
            continue
        seleccion = x.get("seleccion") or [_mostrar(x)]
        for valor in seleccion:
            conteo[str(valor)] = conteo.get(str(valor), 0) + 1
        try:
            numeros.append(float(x.get("valor")))
        except (TypeError, ValueError):
            pass
    validas = len(personas) - sin
    media = round(sum(numeros) / len(numeros), 2) if numeros and len(numeros) == validas else None
    return validas, sin, dict(sorted(conteo.items(), key=lambda kv: -kv[1])), media


def _celda_distribucion(validas: int, conteo: dict[str, int], media: float | None) -> str:
    if not validas:
        return "(sin respuestas)"
    partes = [f"«{o}» {n} ({round(100 * n / validas, 1)} %)" for o, n in conteo.items()]
    return (f"media {media}; " if media is not None else "") + "; ".join(partes)


def _grupos_por(ins: Instrumento, plan: PlanConsulta, base: list[dict[str, Any]]) -> tuple[str, dict[str, list[dict[str, Any]]]]:
    """(nombre del agrupamiento, {grupo: personas}) según `agrupar_por`: variable de contexto, ID de una pregunta (un
    grupo por respuesta, solo las opciones filtradas si las hay) o «posicion» (primeros N y últimos N)."""
    doc, var = ins.doc, plan.agrupar_por or ""
    if var == POSICION:
        n = max(1, min(plan.limite or 50, len(base)))
        ordenadas = sorted(base, key=_clave_id)
        solape = max(0, 2 * n - len(ordenadas))
        nombre = f"posición (primeros {n} y últimos {n}" + (f"; {solape} personas están en los dos grupos)" if solape else ")")
        return nombre, {f"Primeros {n}": ordenadas[:n], f"Últimos {n}": ordenadas[-n:]}
    if _pregunta(doc, var):
        permitidas = {str(v) for f in plan.filtros if f.pregunta == var
                      for v in (f.valor if isinstance(f.valor, list) else [f.valor])}
        grupos: dict[str, list[dict[str, Any]]] = {}
        for persona in base:
            valor = _mostrar(persona["por_pregunta"].get(var))
            if valor not in _VACIOS and (not permitidas or valor in permitidas):
                grupos.setdefault(valor, []).append(persona)
        return _texto_pregunta(doc, var), grupos
    grupos = {}
    for persona in base:
        valor = persona["contexto"].get(var)
        if valor not in (None, ""):
            grupos.setdefault(_legible(valor), []).append(persona)
    return var, grupos


def _comparar_secciones(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    """Respuestas en blanco (o nulas) por sección: cuántos reactivos tiene cada una y qué % de sus respuestas faltan
    (7 nov, PRU-08 y PRU-12)."""
    doc = ins.doc
    nombres = {s["id"]: s.get("nombre", "") for s in doc.get("secciones") or []}
    personas = _personas(doc)
    filas = []
    for sid, nombre in nombres.items():
        items = [_corto(p["id"]) for p in _items(doc) if p.get("seccion_id") == sid and _corto(p["id"]) not in plan.excluir_preguntas]
        if not items:
            continue
        posibles = len(items) * len(personas)
        vacias = sum(1 for persona in personas for q in items
                     if (persona["por_pregunta"].get(q) or {}).get("estado") != "respondida")
        filas.append([nombre, str(len(items)), str(vacias), f"{round(100 * vacias / posibles, 1) if posibles else 0.0} %"])
    e.criterio = "respuestas en blanco o nulas por sección"
    if not filas:
        e.vacio = True
        e.lineas.append("El instrumento no tiene secciones.")
        return
    e.tablas.append(Tabla("Respuestas en blanco o nulas por sección", ["Sección", "Reactivos", "En blanco o nulas",
                                                                       "% de sus respuestas"], filas))
    mayor = max(filas, key=lambda f: float(f[3].rstrip(" %")))
    e.lineas.append(f"La sección con más respuestas en blanco o nulas es «{mayor[0]}»: {mayor[2]} ({mayor[3]} de sus "
                    f"respuestas posibles, {mayor[1]} reactivos × {len(personas)} alumnos).")
    e.total = len(personas)


def _comparar_grupos(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc = ins.doc
    if not plan.agrupar_por:
        _resumen_pregunta(ins, plan, e)  # entre instrumentos: el resumen de cada uno, lado a lado
        return
    if plan.agrupar_por == SECCION:
        _comparar_secciones(ins, plan, e)
        return
    base, condiciones = _filtrados(ins, plan.model_copy(update={
        "filtros": [f for f in plan.filtros if f.pregunta != plan.agrupar_por]}))
    var, grupos = _grupos_por(ins, plan, base)
    e.criterio = f"por {var}" + (f", entre quienes cumplen {' y '.join(condiciones)}" if condiciones else "")
    if not grupos:
        e.vacio = True
        e.lineas.append(f"Ningún respondente tiene un valor de «{var}».")
        return
    preguntas = [q for q in (plan.preguntas or [f.pregunta for f in plan.filtros if f.pregunta != plan.agrupar_por][:1])
                 if q != plan.agrupar_por]
    columnas = ["Grupo", "Personas"]
    filas = []
    orden = list(grupos) if plan.agrupar_por == POSICION else sorted(grupos)
    for g in orden:
        personas = grupos[g]
        fila = [g, str(len(personas))]
        for q in preguntas:
            validas = [p for p in personas if (p["por_pregunta"].get(q) or {}).get("estado") == "respondida"]
            if plan.nivel:
                en = sum(_en_nivel(p["por_pregunta"].get(q), plan.nivel) for p in validas)
                fila.append(f"{round(100 * en / len(validas), 1) if validas else 0.0} % ({en} de {len(validas)})")
            else:
                # Toda la distribución del grupo (y su media si es numérica), no solo la opción más elegida: los grupos
                # se comparan en porcentajes sobre su propio n (7 nov, ENC-08, ENC-09 y ENC-11).
                n_validas, _, conteo, media = distribucion(doc, personas, q)
                fila.append(_celda_distribucion(n_validas, conteo, media))
        filas.append(fila)
    for q in preguntas:
        columnas.append(f"{q}: {_NOMBRE_NIVEL[plan.nivel]}" if plan.nivel else f"{q}: respuestas del grupo")
    e.tablas.append(Tabla(f"Comparación por {var}", columnas, filas))
    e.total = len(base)
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in preguntas]


def _hay_condicion(plan: PlanConsulta) -> bool:
    return bool(plan.filtros or plan.contexto or plan.contexto_num or plan.menciona or plan.con_omisiones)


def _cruce(ins: Instrumento, plan: PlanConsulta, e: Ejecucion, grupo: list[dict[str, Any]], condiciones: list[str],
           preguntas: list[str]) -> None:
    """La distribución de cada pregunta DENTRO del grupo que cumple las condiciones: «de los que marcaron Verdadero en
    r11, ¿qué eligieron en r03?» (7 nov, PRU-09 y PRU-14: se respondía con la distribución de toda la muestra)."""
    doc = ins.doc
    for q in preguntas:
        validas, sin, conteo, media = distribucion(doc, grupo, q)
        e.lineas.append(f"Entre los {len(grupo)} que cumplen {' y '.join(condiciones)}, {_texto_pregunta(doc, q)}: "
                        f"{validas} respuestas válidas" + (f", {sin} sin respuesta" if sin else "")
                        + (f"; media {media}" if media is not None else "") + ".")
        if conteo:
            e.tablas.append(Tabla(f"{q} entre quienes cumplen la condición", ["Opción", "Personas", "% del grupo"],
                                  [[o, str(n), f"{round(100 * n / validas, 1) if validas else 0.0} %"] for o, n in conteo.items()]))


def _resumen_pregunta(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc = ins.doc
    preguntas = plan.preguntas or [f.pregunta for f in plan.filtros]
    objetivo = [q for q in preguntas if q not in {f.pregunta for f in plan.filtros}]
    if _hay_condicion(plan) and objetivo:
        grupo, condiciones = _filtrados(ins, plan)
        e.criterio = " y ".join(condiciones)
        e.total = len(grupo)
        e.vacio = not grupo
        _cruce(ins, plan, e, grupo, condiciones, objetivo)
        e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in set(preguntas) | {f.pregunta for f in plan.filtros}]
        return
    if not preguntas:
        e.vacio = True
        e.lineas.append("La consulta no indica de qué pregunta se trata.")
        return
    for q in preguntas:
        p = _pregunta(doc, q)
        resumen = (p or {}).get("resumen") or {}
        if not resumen and doc.get("entrevistas"):
            # Una entrevista no tiene resúmenes por pregunta: su «resumen» es lo que respondió cada participante
            # («¿qué la detuvo antes de buscar ayuda?» daba «sin resumen calculado», Fase 6, segunda corrida).
            filas = [[_corto(x["id"]), _mostrar(x["por_pregunta"].get(q))] for x in _personas(doc) if q in x["por_pregunta"]]
            e.lineas.append(f"{_texto_pregunta(doc, q)}: respondieron {len(filas)} de {len(_personas(doc))} participantes.")
            if filas:
                e.tablas.append(Tabla(f"Respuestas a {q}", ["Participante", "Respuesta"], filas))
            continue
        if not resumen:
            e.lineas.append(f"{_texto_pregunta(doc, q)}: sin resumen calculado.")
            continue
        validas, sin = resumen.get("n_validas"), resumen.get("n_sin_respuesta")
        if validas is None and resumen.get("n_alumnos") is not None:  # reactivo de una prueba: n_alumnos y nulas aparte
            sin = (sin or 0) + (resumen.get("n_nulas") or 0)
            validas = resumen["n_alumnos"] - sin
        e.lineas.append(f"{_texto_pregunta(doc, q)}: {validas} respuestas válidas" + (f", {sin} sin respuesta" if sin else "")
                        + (f"; media {resumen['media']}" if resumen.get("media") is not None else "") + ".")
        if resumen.get("interpretacion"):
            e.lineas.append(f"Interpretación calculada: {resumen['interpretacion']}")
        dist = resumen.get("distribucion") or []
        if isinstance(dist, dict):  # reactivo de una prueba: {opción: {n, pct}} (Fase 7, consultas 2228 y 2230)
            dist = [{"significado": o, **(v if isinstance(v, dict) else {})} for o, v in dist.items()]
        if dist:
            e.tablas.append(Tabla(f"Distribución de {q}", ["Opción", "Respondentes", "%"],
                                  [[str(d.get("significado")), str(d.get("n")), f"{d.get('pct')} %"] for d in dist]))
        if resumen.get("opcion_mas_elegida"):
            m = resumen["opcion_mas_elegida"]
            e.lineas.append(f"Opción más elegida: «{m.get('significado')}» ({m.get('pct')} %, {m.get('n')} alumnos).")
    e.criterio = "resumen de " + ", ".join(preguntas)
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in preguntas]


_TOP_RANKING = 3
_NOMBRE_RANKING = {"no_respuesta": "más respuestas nulas o sin responder",
                   "coincidencia": "más coincidencia (índice de dispersión más bajo: 0 = todos eligieron lo mismo)",
                   "repartida": "respuestas más repartidas (índice de dispersión más alto: 1 = repartidas por igual entre "
                                "sus opciones; entropía normalizada)"}
_SIN_DISPERSION = {"opcion_multiple_varias", "texto_corto", "texto_largo", "abierta", "numerica", "sin_datos", "fecha",
                   "ordenamiento"}
_NO_OPCION = {"nr", "nula", "sin respuesta", "(sin respuesta)", "(nula)"}


def _medida_ranking(p: dict[str, Any], criterio: str) -> tuple[float, str] | None:
    """(valor por el que se ordena, cómo se dice) de una pregunta o reactivo; None si no tiene ese dato."""
    r = p.get("resumen") or {}
    if criterio == "no_respuesta":
        vacias = (r.get("n_nulas") or 0) + (r.get("n_sin_respuesta") or 0)
        total = r.get("n_alumnos") or ((r.get("n_validas") or 0) + vacias)
        if not total:
            return None
        pct = round(100 * vacias / total, 1)
        return pct, f"{vacias} nulas o sin responder de {total} ({pct} %)"
    # 7 nov (Fase 4): repartida y coincidencia con la entropía normalizada de la distribución (0 = todos eligieron lo
    # mismo; 1 = repartidas por igual entre todas las opciones). Con el % de la opción más elegida, una pregunta de
    # opción múltiple con siete opciones salía como la «más dividida» (ENC-14) y una escala de 10 puntos ganaba siempre
    # (CEN-04). Las de varias respuestas, abiertas o numéricas no entran: su distribución no reparte a las personas.
    if str(p.get("tipo") or p.get("tipo_reactivo") or "") in _SIN_DISPERSION:
        return None
    dist = r.get("distribucion") or []
    if isinstance(dist, dict):  # reactivo: {opción: {n, pct}}
        dist = [{"significado": o, **(v if isinstance(v, dict) else {})} for o, v in dist.items()]
    conteos = [(str(d.get("significado")), int(d.get("n") or 0)) for d in dist
               if str(d.get("significado")).strip().lower() not in _NO_OPCION]
    total = sum(n for _, n in conteos)
    if len(conteos) < 2 or not total:
        return None
    h = -sum((n / total) * math.log(n / total) for _, n in conteos if n)
    indice = round(h / math.log(len(conteos)), 3)
    top = max(conteos, key=lambda c: c[1])
    texto = (f"índice de dispersión {indice:.2f} ({len(conteos)} opciones); la más elegida, «{top[0]}», con {top[1]} de "
             f"{total} ({round(100 * top[1] / total, 1)} %)")
    return (indice, texto) if criterio == "repartida" else (round(1 - indice, 3), texto)


def _ranking_preguntas(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    """Preguntas ordenadas por un criterio, sin las excluidas («sin contar la de la contraseña»). Se muestran las 3
    primeras y las que empatan con la 3.ª."""
    doc = ins.doc
    criterio = plan.criterio_ranking or "no_respuesta"
    medidas = [(m, p) for p in _items(doc) if _corto(p["id"]) not in plan.excluir_preguntas
               and (m := _medida_ranking(p, criterio)) is not None]
    sin = ", ".join(plan.excluir_preguntas)
    e.criterio = f"preguntas con {_NOMBRE_RANKING[criterio]}" + (f", sin contar {sin}" if sin else "")
    if not medidas:
        e.vacio = True
        e.lineas.append("No hay resúmenes calculados para ordenar las preguntas.")
        return
    medidas.sort(key=lambda x: x[0][0], reverse=True)  # índice más alto primero (en coincidencia ya va invertido)
    corte = medidas[min(_TOP_RANKING, len(medidas)) - 1][0][0]
    elegidas = [x for i, x in enumerate(medidas) if i < _TOP_RANKING or x[0][0] == corte][:10]
    for n, ((valor, texto), p) in enumerate(elegidas, start=1):
        e.lineas.append(f"{n}. {_texto_pregunta(doc, _corto(p['id']))}: {texto}.")
    empatadas = [_corto(p["id"]) for (valor, _), p in elegidas if valor == elegidas[0][0][0]]
    if len(empatadas) > 1:
        e.lineas.append(f"Empatan en el primer lugar: {', '.join(empatadas)}.")
    e.tablas.append(Tabla(f"Preguntas por {criterio.replace('_', ' ')}", ["Lugar", "Pregunta", "Dato"],
                          [[str(n), _corto(p["id"]), texto] for n, ((_, texto), p) in enumerate(elegidas, start=1)]))
    e.preguntas = [p["id"] for _, p in elegidas]


def _kpi(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc = ins.doc
    kpis = doc.get("kpis_asociados") or []
    if plan.kpi:
        kpis = [k for k in kpis if k.get("kpi_id") == plan.kpi]
    if not kpis:
        e.vacio = True
        e.lineas.append("El instrumento no tiene KPIs asociados." if not plan.kpi else f"El KPI {plan.kpi} no está asociado.")
        return
    filas = []
    for k in kpis:
        preguntas = [ev["pregunta_id"] for ev in k.get("evidencia") or [] if ev.get("pregunta_id")]
        filas.append([k.get("nombre", ""), k.get("que_mide", "") or k.get("definicion", ""),
                      ", ".join(_corto(p) for p in preguntas)])
        e.kpis.append(str(k.get("kpi_id")))
        e.preguntas += preguntas
        if plan.kpi and k.get("justificacion"):
            e.lineas.append(f"Por qué se asoció: {k['justificacion']}")
    e.criterio = f"KPI {plan.kpi}" if plan.kpi else f"los {len(kpis)} KPIs asociados"
    e.tablas.append(Tabla("KPIs asociados", ["KPI", "Qué mide", "Preguntas que lo sustentan"], filas))
    e.preguntas = list(dict.fromkeys(e.preguntas))


def _hallazgo(ins: Instrumento, plan: PlanConsulta, e: Ejecucion, fiabilidad: list[dict[str, Any]] | None) -> None:
    if plan.sentido and ins.tipo == "encuesta":
        e.candidatos = hallazgos.por_polaridad(ins.doc, plan.sentido)
        nombre = "más preocupante (respuestas desfavorables)" if plan.sentido == "desfavorable" else "mejor (respuestas favorables)"
        if e.candidatos:
            e.criterio = f"lo {nombre}: % de quienes eligieron las respuestas {plan.sentido}s de cada pregunta"
            e.lineas += [f"Dato {n}: {c['texto']}" for n, c in enumerate(e.candidatos, start=1)]
            e.preguntas = list(dict.fromkeys(p for c in e.candidatos for p in c["preguntas"]))
            return
        e.lineas.append("Ninguna pregunta tiene decidido qué respuestas son favorables o desfavorables (polaridad): "
                        "estos son los datos más notables, sin juzgar si son buenos o malos.")
    e.candidatos = hallazgos.candidatos(ins.tipo, ins.doc, fiabilidad)
    e.criterio = e.criterio or "datos calculados sobre los resúmenes del documento final, del más al menos notable"
    if not e.candidatos:
        e.vacio = True
        e.lineas.append("No hay resúmenes calculados para buscar un hallazgo en este instrumento.")
        return
    e.lineas += [f"Dato {n}: {c['texto']}" for n, c in enumerate(e.candidatos, start=1)]
    e.preguntas = list(dict.fromkeys(p for c in e.candidatos for p in c["preguntas"]))


_EJECUTORES = {
    "datos_respondente": _datos_respondente,
    "filtrar_respondentes": _filtrar_respondentes,
    "conteo_porcentaje": _conteo_porcentaje,
    "comparar_grupos": _comparar_grupos,
    "resumen_pregunta": _resumen_pregunta,
    "ranking_preguntas": _ranking_preguntas,
    "kpi": _kpi,
}


def fiabilidad_de(sesion: Session, instrumentos: list[Instrumento]) -> dict[str, list[dict[str, Any]]]:
    """{id_crudo: bloques con α de Cronbach} de la última limpieza confirmada de cada instrumento."""
    salida: dict[str, list[dict[str, Any]]] = {}
    for ins in instrumentos:
        fila = (sesion.query(LimpiezaEjecucion)
                .filter(LimpiezaEjecucion.id_crudo == int(ins.id_crudo), LimpiezaEjecucion.estado == "confirmada")
                .order_by(LimpiezaEjecucion.version.desc()).first())
        estadistica = (((fila.reporte or {}).get("vista_final") or {}).get("estadistica")) if fila else None
        bloques = (estadistica or {}).get("fiabilidad")
        if isinstance(bloques, list):
            salida[ins.id_crudo] = bloques
    return salida


def ejecutar(plan: PlanConsulta, instrumentos: list[Instrumento],
             fiabilidad: dict[str, list[dict[str, Any]]] | None = None) -> list[Ejecucion]:
    """Resultado del plan en cada instrumento del alcance (los del plan o, si no nombra ninguno, todos).

    `fiabilidad`: {id_crudo: bloques con α de la última limpieza} para los hallazgos de fiabilidad baja.
    Devuelve [] si la intención no es estructurada.
    """
    if plan.intencion not in ESTRUCTURADAS:
        return []
    alcance = [i for i in instrumentos if i.id_crudo in plan.instrumentos] or instrumentos
    salida = []
    for ins in alcance:
        e = Ejecucion(plan.intencion, ins)
        if plan.intencion == "hallazgo":
            _hallazgo(ins, plan, e, (fiabilidad or {}).get(ins.id_crudo))
        else:
            _EJECUTORES[plan.intencion](ins, plan, e)
        salida.append(e)
    return salida
