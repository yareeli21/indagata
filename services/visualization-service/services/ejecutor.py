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
_LIMITE_IDS = 30  # IDs mostrados si el plan no da límite
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


def _raices_termino(termino: str) -> list[str]:
    """Raíz de 5 letras de cada palabra con contenido: «estrés» → «estre» (encuentra «estresada»)."""
    return [w[:5] for w in re.findall(r"[a-z0-9]+", normalizar(termino)) if len(w) >= 4]


def _plano(texto: str) -> str:
    """Minúsculas y sin acentos, letra por letra (misma longitud que el original, a diferencia de `normalizar`)."""
    return "".join((unicodedata.normalize("NFD", c)[0] if c.isalpha() else c).lower() for c in texto)


def _menciones(doc: dict[str, Any], persona: dict[str, Any], plan: PlanConsulta) -> list[tuple[str, str]]:
    """(pregunta, fragmento) de cada respuesta abierta de la persona que contiene TODAS las palabras del término."""
    raices = _raices_termino(plan.menciona)
    if not raices:
        return []
    entrevista = bool(doc.get("entrevistas"))
    abiertas = {_corto(p["id"]) for p in _items(doc) if entrevista or str(p.get("tipo", "")) in _ABIERTAS}
    salida = []
    for q, x in persona["por_pregunta"].items():
        if q not in abiertas or (plan.preguntas and q not in plan.preguntas) or (x or {}).get("estado") != "respondida":
            continue
        texto = str(x.get("significado") or "")
        normal = _plano(texto)
        posiciones = [m.start() for r in raices if (m := re.search(rf"\b{re.escape(r)}", normal))]
        if len(posiciones) == len(raices):
            i = posiciones[0]  # _plano conserva la longitud: la posición sirve en el texto original
            salida.append((q, ("…" if i > 50 else "") + texto[max(0, i - 50):i + 70].strip() + ("…" if i + 70 < len(texto) else "")))
    return salida


def _tabla_menciones(doc: dict[str, Any], personas: list[dict[str, Any]], plan: PlanConsulta) -> Tabla:
    filas = [[_corto(p["id"]), q, f"«{frag}»"] for p in personas for q, frag in _menciones(doc, p, plan)]
    return Tabla(f"Dónde se menciona «{plan.menciona}»", ["Respondente", "Pregunta", "Fragmento"], filas[:_MAX_CITAS])


def _filtrados(ins: Instrumento, plan: PlanConsulta) -> tuple[list[dict[str, Any]], list[str]]:
    """Personas que cumplen TODOS los filtros (y el nivel en las preguntas del plan, si lo hay)."""
    doc = ins.doc
    condiciones = ([f"{k} = «{v}»" for k, v in plan.contexto.items()]
                   + [f"{c.variable} {c.op} {_numero_texto(c.valor)}" for c in plan.contexto_num]
                   + [_describir(doc, f) for f in plan.filtros]
                   + ([f"mencionan «{plan.menciona}» en sus respuestas abiertas"
                       + (f" ({', '.join(plan.preguntas)})" if plan.preguntas else "")] if plan.menciona else []))
    personas = [p for p in _personas(doc)
                if all(normalizar(str(p["contexto"].get(k, ""))) == normalizar(v) for k, v in plan.contexto.items())
                and all(_cumple_contexto(p, c) for c in plan.contexto_num)
                and all(_cumple(p, f) for f in plan.filtros)
                and (not plan.menciona or _menciones(doc, p, plan))]
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
    mostrados = cumplen[:n]
    e.criterio = " y ".join(condiciones) or "sin condiciones"
    e.total, e.mostrados = len(cumplen), len(mostrados)
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in {f.pregunta for f in plan.filtros} | set(plan.preguntas)]
    pct = round(100 * len(cumplen) / total, 1) if total else 0.0
    e.lineas.append(f"Cumplen la condición {len(cumplen)} de {total} respondentes ({pct} %).")
    if not cumplen:
        e.vacio = True
        return
    e.lineas.append(f"Se muestran {_frase_orden(plan, len(mostrados))} que la cumplen: {len(mostrados)} de {len(cumplen)}.")
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
    hay_condicion = bool(plan.filtros or plan.contexto or plan.contexto_num or plan.menciona)
    if hay_condicion:
        pct = round(100 * len(grupo) / total, 1) if total else 0.0
        e.criterio = " y ".join(condiciones)
        e.total = len(grupo)
        e.lineas.append(f"Cumplen la condición {len(grupo)} de {total} respondentes ({pct} %).")
        e.vacio = not grupo
        if plan.menciona and grupo:
            e.tablas.append(_tabla_menciones(doc, grupo, plan))
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


def _comparar_grupos(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc = ins.doc
    if not plan.agrupar_por:
        _resumen_pregunta(ins, plan, e)  # entre instrumentos: el resumen de cada uno, lado a lado
        return
    var = plan.agrupar_por
    base, condiciones = _filtrados(ins, plan)
    grupos: dict[str, list[dict[str, Any]]] = {}
    for p in base:
        valor = p["contexto"].get(var)
        if valor not in (None, ""):
            grupos.setdefault(str(valor), []).append(p)
    e.criterio = f"por {var}" + (f", entre quienes cumplen {' y '.join(condiciones)}" if condiciones else "")
    if not grupos:
        e.vacio = True
        e.lineas.append(f"Ningún respondente tiene un valor de «{var}».")
        return
    preguntas = plan.preguntas or [f.pregunta for f in plan.filtros][:1]
    columnas = [var, "Respondentes"]
    filas = []
    for g, personas in sorted(grupos.items()):
        fila = [g, str(len(personas))]
        for q in preguntas:
            validas = [p for p in personas if (p["por_pregunta"].get(q) or {}).get("estado") == "respondida"]
            if plan.nivel:
                en = sum(_en_nivel(p["por_pregunta"].get(q), plan.nivel) for p in validas)
                fila.append(f"{round(100 * en / len(validas), 1) if validas else 0.0} % ({en} de {len(validas)})")
            else:
                conteo: dict[str, int] = {}
                for p in validas:
                    conteo[_mostrar(p["por_pregunta"].get(q))] = conteo.get(_mostrar(p["por_pregunta"].get(q)), 0) + 1
                if conteo:
                    top = max(conteo, key=conteo.get)
                    fila.append(f"«{top}» {round(100 * conteo[top] / len(validas), 1)} % ({conteo[top]} de {len(validas)})")
                else:
                    fila.append("(sin respuestas)")
        filas.append(fila)
    for q in preguntas:
        columnas.append(f"{q}: {_NOMBRE_NIVEL[plan.nivel]}" if plan.nivel else f"{q}: opción más elegida")
    e.tablas.append(Tabla(f"Comparación por {var}", columnas, filas))
    e.total = len(base)
    e.preguntas = [p["id"] for p in _items(doc) if _corto(p["id"]) in preguntas]


def _resumen_pregunta(ins: Instrumento, plan: PlanConsulta, e: Ejecucion) -> None:
    doc = ins.doc
    preguntas = plan.preguntas or [f.pregunta for f in plan.filtros]
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
        e.lineas.append(f"{_texto_pregunta(doc, q)}: {validas} respuestas válidas" + (f", {sin} sin respuesta" if sin else "")
                        + (f"; media {resumen['media']}" if resumen.get("media") is not None else "") + ".")
        if resumen.get("interpretacion"):
            e.lineas.append(f"Interpretación calculada: {resumen['interpretacion']}")
        dist = resumen.get("distribucion") or []
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
                   "coincidencia": "más coincidencia (opción más elegida con el porcentaje más alto)",
                   "repartida": "respuestas más repartidas (opción más elegida con el porcentaje más bajo)"}


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
    if r.get("opcion_mas_elegida"):  # pruebas
        m = r["opcion_mas_elegida"]
        return float(m.get("pct") or 0), f"«{m.get('significado')}» con {m.get('n')} de {r.get('n_alumnos')} ({m.get('pct')} %)"
    dist = r.get("distribucion") if isinstance(r.get("distribucion"), list) else []
    if not dist:
        return None
    top = max(dist, key=lambda d: d.get("pct") or 0)
    return float(top.get("pct") or 0), f"«{top.get('significado')}» con {top.get('n')} respuestas ({top.get('pct')} %)"


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
    medidas.sort(key=lambda x: x[0][0], reverse=criterio != "repartida")
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
    e.candidatos = hallazgos.candidatos(ins.tipo, ins.doc, fiabilidad)
    e.criterio = "datos calculados sobre los resúmenes del documento final, del más al menos notable"
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
