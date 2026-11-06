"""Plan de consulta del chat: lo que la etapa de interpretación (LLM) entiende de una pregunta.

Rediseño del chat en cuatro etapas (28 oct):
    1. Interpretación (`services/interpretacion.py`): el LLM convierte la pregunta en UN plan JSON, nunca SQL ni
       texto libre. Este módulo define el esquema del plan y lo valida contra el catálogo de los instrumentos.
    2. Ejecución (determinista, sin LLM).
    3. Redacción (LLM, solo con el resultado de la ejecución).
    4. Verificación (cifras y métricas RAGAS).

El esquema es estricto (`extra="forbid"`): un campo inventado por el modelo hace inválido el plan y se reintenta
una vez con el error. Después de validarse contra el esquema, `validar_contra_catalogo` comprueba que cada pregunta,
opción, respondente, variable de contexto y KPI exista en el instrumento: lo que no existe se corrige al valor más
cercano o se convierte en una pregunta de aclaración. Nunca se inventa.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.catalogo import Catalogo
from services.dominio import normalizar

# «Agrupar por instrumento» no es una variable de contexto: es comparar los instrumentos seleccionados.
_ENTRE_INSTRUMENTOS = {"instrumento", "instrumentos", "encuesta", "encuestas", "instrumento_id", "ambos"}
# Tope de filas que puede pedir un plan (respondentes listados, IDs…). Un plan con más se recorta, no se rechaza.
LIMITE_MAX = 50

Intencion = Literal[
    "datos_respondente",     # todas o algunas respuestas de respondentes concretos («R001», «el primer respondente»)
    "filtrar_respondentes",  # quiénes cumplen condiciones (lista de IDs o sus respuestas)
    "conteo_porcentaje",     # cuántos / qué porcentaje cumple condiciones o está en un nivel
    "comparar_grupos",       # una pregunta o nivel por grupo de contexto (turno…) o entre instrumentos
    "hallazgo",              # un dato interesante de los datos (mayor desacuerdo, contraste entre grupos…)
    "resumen_pregunta",      # distribución y resumen de una o varias preguntas
    "ranking_preguntas",     # preguntas ordenadas por un criterio (más no respuesta, más coincidencia, más repartidas)
    "kpi",                   # KPIs asociados y las preguntas que los miden
    "semantica_abierta",     # contenido abierto (comentarios, entrevistas): búsqueda en el RAG
    "metodologia",           # definiciones (alfa de Cronbach, Likert…): glosario
    "uso_plataforma",        # cómo usar Indagata: base de ayuda
    "fuera_de_dominio",      # nada que ver con los instrumentos ni con la plataforma
    "aclaracion",            # ambigua: una pregunta breve al usuario
]
INTENCIONES: tuple[str, ...] = Intencion.__args__  # type: ignore[attr-defined]

# Intenciones que se responden calculando sobre los datos (etapa 2, ejecutor estructurado).
ESTRUCTURADAS = frozenset({"datos_respondente", "filtrar_respondentes", "conteo_porcentaje", "comparar_grupos",
                           "hallazgo", "resumen_pregunta", "ranking_preguntas", "kpi"})
# Criterios del ranking de preguntas: más nulas o sin responder, opción más elegida más alta o más baja.
CriterioRanking = Literal["no_respuesta", "coincidencia", "repartida"]

Operador = Literal["=", "!=", ">", ">=", "<", "<="]
Nivel = Literal["alto", "medio", "bajo", "acuerdo", "neutral", "desacuerdo"]


class Filtro(BaseModel):
    """Una condición sobre una pregunta: «p03 = Carga minima», «p04 >= 4» o «p01 en nivel acuerdo»."""

    model_config = ConfigDict(extra="forbid")

    pregunta: str = Field(description="ID corto de la pregunta del catálogo, p. ej. «p03».")
    op: Operador = "="
    valor: str | float | list[str] | None = Field(
        default=None, description="Opción tal como aparece en el catálogo, número o lista de opciones.")
    # «están de acuerdo con la pregunta 1» es un nivel de la escala (todas sus opciones de acuerdo), no una opción
    # (28 oct, regresión C24: se filtraba solo «Totalmente de acuerdo» y faltaban los «De acuerdo»).
    nivel: Nivel | None = Field(default=None, description="Nivel de la escala en lugar de una opción.")

    @model_validator(mode="after")
    def _con_condicion(self) -> "Filtro":
        if self.valor is None and self.nivel is None:
            raise ValueError("Cada filtro necesita «valor» o «nivel».")
        return self


class CondicionContexto(BaseModel):
    """Una comparación sobre un dato de contexto numérico: «horas_trabajo_semana > 20», «edad < 20».

    Antes el contexto solo admitía igualdad y «¿cuántos trabajan más de 20 horas?» no tenía cómo expresarse cuando
    las horas eran un dato de contexto y no una pregunta (Fase 6, consultas 1486 y 1522)."""

    model_config = ConfigDict(extra="forbid")

    variable: str = Field(description="Variable del «Contexto numérico» del catálogo.")
    op: Operador = ">"
    valor: float


class Orden(BaseModel):
    model_config = ConfigDict(extra="forbid")

    por: Literal["id_respondente"] = "id_respondente"
    dir: Literal["asc", "desc"] = "asc"


class PlanConsulta(BaseModel):
    """Lo que el LLM entendió de la pregunta. Todos los campos menos `intencion` son opcionales."""

    model_config = ConfigDict(extra="forbid")

    intencion: Intencion
    instrumentos: list[str] = Field(default_factory=list, description="IDs de instrumento; vacío = todos los seleccionados.")
    respondentes: list[str] = Field(default_factory=list, description="IDs cortos de respondente («R001») si la pregunta los nombra.")
    preguntas: list[str] = Field(default_factory=list, description="IDs cortos de las preguntas de las que trata.")
    filtros: list[Filtro] = Field(default_factory=list, max_length=5)
    nivel: Nivel | None = None
    agrupar_por: str | None = Field(default=None, description="Variable de contexto del catálogo (p. ej. «Turno»).")
    # Solo un grupo de contexto («del turno vespertino» → {"Turno": "Vespertino"}) (28 oct, regresión C21).
    contexto: dict[str, str] = Field(default_factory=dict, description="Grupo de contexto al que se limita la consulta.")
    contexto_num: list[CondicionContexto] = Field(
        default_factory=list, max_length=3, description="Comparaciones sobre el contexto numérico («más de 20 horas»).")
    criterio_ranking: CriterioRanking | None = Field(
        default=None, description="En ranking_preguntas: no_respuesta, coincidencia o repartida.")
    # «sin contar la de la contraseña»: preguntas que no entran al cálculo (Fase 6, consultas 1493, 1498 y 1529).
    excluir_preguntas: list[str] = Field(default_factory=list, description="IDs cortos de preguntas que no se cuentan.")
    # «¿cuántos mencionaron la ansiedad?»: término que se busca en las respuestas abiertas (Fase 6, consultas 1468, 1540).
    menciona: str = Field(default="", max_length=60, description="Término que se busca en las respuestas abiertas.")
    kpi: str | None = Field(default=None, description="ID o nombre del KPI si la pregunta trata de uno.")
    campos: Literal["todas_las_respuestas", "solo_ids"] | list[str] = "solo_ids"
    orden: Orden | None = None
    limite: int | None = Field(default=None, ge=1)
    consulta_semantica: str = Field(default="", max_length=300)
    aclaracion: str = Field(default="", max_length=300)

    @field_validator("limite")
    @classmethod
    def _tope(cls, v: int | None) -> int | None:
        """Más de LIMITE_MAX se recorta: el plan sigue siendo válido."""
        return None if v is None else min(v, LIMITE_MAX)

    @model_validator(mode="after")
    def _coherente(self) -> "PlanConsulta":
        if self.intencion == "aclaracion" and not self.aclaracion.strip():
            raise ValueError("La intención «aclaracion» necesita la pregunta para el usuario en «aclaracion».")
        if self.intencion == "semantica_abierta" and not self.consulta_semantica.strip():
            raise ValueError("La intención «semantica_abierta» necesita «consulta_semantica».")
        return self


def esquema() -> dict:
    """JSON Schema del plan (se pasa a Ollama como `format` y se publica en `esquemas/plan_consulta.json`)."""
    return PlanConsulta.model_json_schema()


# ── Validación contra el catálogo ──────────────────────────────────────────────


@dataclass
class PlanValidado:
    plan: PlanConsulta
    correcciones: list[str] = field(default_factory=list)  # «carga mínima» → «Carga minima», «p3» → «p03»…


def _cercano(buscado: str, opciones: list[str], corte: float = 0.75) -> str | None:
    """La opción igual a `buscado` sin acentos ni mayúsculas, o la más parecida (≥ `corte`)."""
    norm = {normalizar(o): o for o in opciones}
    b = normalizar(buscado)
    if b in norm:
        return norm[b]
    parecidas = difflib.get_close_matches(b, list(norm), n=1, cutoff=corte)
    return norm[parecidas[0]] if parecidas else None


def _id_pregunta(texto: str, catalogo: Catalogo) -> str | None:
    """«p3», «P03», «3», «pregunta 3» o el ID completo («INS-0127-p03») → «p03» si existe en el catálogo."""
    t = normalizar(str(texto))
    if t in catalogo.preguntas:
        return t
    numero = re.search(r"(\d+)\s*$", t)
    if numero:
        n = int(numero.group(1))
        return next((pid for pid in catalogo.preguntas if re.fullmatch(rf"[a-z]+0*{n}", pid)), None)
    return None


def _id_respondente(texto: str, catalogo: Catalogo) -> str | None:
    """«r1», «R-001», «R001» → «R001» si existe."""
    m = re.fullmatch(r"([a-z])\s*-?\s*0*(\d{1,5})", normalizar(str(texto)))
    if not m:
        return None
    letra, n = m.group(1).upper(), int(m.group(2))
    return next((r for r in catalogo.respondentes if r[0] == letra and int(r[1:]) == n), None)


def validar_contra_catalogo(plan: PlanConsulta, catalogos: list[Catalogo]) -> PlanValidado:
    """Comprueba el plan contra los catálogos del alcance; corrige lo cercano y pide aclaración si algo no existe."""
    correcciones: list[str] = []
    por_id = {c.id: c for c in catalogos}
    instrumentos = [i for i in plan.instrumentos if i in por_id]
    if plan.instrumentos and not instrumentos:
        correcciones.append(f"instrumentos {plan.instrumentos} fuera de la selección: se usan los seleccionados")
    elegidos = [por_id[i] for i in instrumentos] or catalogos
    if not elegidos:
        return PlanValidado(plan, correcciones)
    cat = elegidos[0]

    def aclarar(texto: str) -> PlanValidado:
        return PlanValidado(PlanConsulta(intencion="aclaracion", instrumentos=instrumentos, aclaracion=texto), correcciones)

    preguntas: list[str] = []
    for p in plan.preguntas:
        pid = _id_pregunta(p, cat)
        if pid is None:
            return aclarar(f"No encontré la pregunta «{p}» en «{cat.titulo}». ¿A cuál te refieres?")
        if pid != p:
            correcciones.append(f"pregunta «{p}» → «{pid}»")
        preguntas.append(pid)

    filtros: list[Filtro] = []
    for f in plan.filtros:
        pid = _id_pregunta(f.pregunta, cat)
        if pid is None:
            return aclarar(f"No encontré la pregunta «{f.pregunta}» en «{cat.titulo}». ¿A cuál te refieres?")
        opciones = cat.preguntas[pid].opciones
        valor = f.valor
        if f.nivel is not None:  # nivel de la escala: no hay opción que emparejar
            filtros.append(Filtro(pregunta=pid, op=f.op, nivel=f.nivel))
            continue
        if isinstance(valor, (int, float)) or not opciones:
            filtros.append(Filtro(pregunta=pid, op=f.op, valor=valor))
            continue
        pedidos = valor if isinstance(valor, list) else [valor]
        if all(_cercano(str(v), opciones) is None for v in pedidos):
            # El modelo puso la opción en otra pregunta (copió el ID de un ejemplo: «Carga minima» en p02, que
            # aquí es la modalidad). Si TODAS las opciones están en una sola pregunta del catálogo, se reubica ahí.
            otras = [q for q, datos in cat.preguntas.items() if q != pid
                     and all(_cercano(str(v), datos.opciones, corte=0.9) for v in pedidos)]
            if len(otras) == 1:
                correcciones.append(f"filtro {pid} → {otras[0]} («{pedidos[0]}» es una opción de {otras[0]})")
                pid, opciones = otras[0], cat.preguntas[otras[0]].opciones
        reales = []
        for v in pedidos:
            real = _cercano(str(v), opciones)
            if real is None:
                return aclarar(f"«{v}» no es una opción de {pid} («{cat.preguntas[pid].texto}»). "
                               f"Las opciones son: {', '.join(opciones[:10])}. ¿Cuál quieres?")
            if real != v:
                correcciones.append(f"{pid}: «{v}» → «{real}»")
            reales.append(real)
        filtros.append(Filtro(pregunta=pid, op=f.op, valor=reales if isinstance(valor, list) else reales[0]))

    respondentes: list[str] = []
    for r in plan.respondentes:
        rid = _id_respondente(r, cat)
        if rid is None:
            return aclarar(f"No hay un respondente «{r}» en «{cat.titulo}» (van de {cat.respondentes[0]} a "
                           f"{cat.respondentes[-1]})." if cat.respondentes else f"«{cat.titulo}» no tiene respondentes.")
        respondentes.append(rid)

    agrupar = plan.agrupar_por if plan.agrupar_por and plan.agrupar_por.strip() else None  # «» = sin agrupar (C25)
    if agrupar is not None and normalizar(agrupar) in _ENTRE_INSTRUMENTOS:
        # «ambos instrumentos»: se comparan los instrumentos entre sí, no un grupo de contexto (regresión C25).
        correcciones.append(f"agrupar_por «{agrupar}» → comparación entre instrumentos")
        agrupar = None
    if agrupar is not None and _cercano(agrupar, list(cat.contexto)) is None and plan.intencion != "comparar_grupos":
        correcciones.append(f"agrupar_por «{agrupar}» no es una variable de contexto y la consulta no compara: se quita")
        agrupar = None
    if agrupar is not None:
        real = _cercano(agrupar, list(cat.contexto))
        if real is None:
            disponibles = ", ".join(cat.contexto) or "ninguna"
            return aclarar(f"«{agrupar}» no es una variable de contexto de «{cat.titulo}» (disponibles: {disponibles}).")
        if real != agrupar:
            correcciones.append(f"agrupar_por «{agrupar}» → «{real}»")
        agrupar = real

    contexto: dict[str, str] = {}
    for clave, valor in plan.contexto.items():
        var = _cercano(clave, list(cat.contexto))
        real = _cercano(str(valor), cat.contexto.get(var, [])) if var else None
        if var is None or real is None:
            disponibles = "; ".join(f"{k}: {', '.join(v)}" for k, v in cat.contexto.items()) or "ninguno"
            return aclarar(f"«{clave} = {valor}» no es un grupo de «{cat.titulo}» (grupos: {disponibles}).")
        if (var, real) != (clave, valor):
            correcciones.append(f"contexto «{clave} = {valor}» → «{var} = {real}»")
        contexto[var] = real

    contexto_num: list[CondicionContexto] = []
    for c in plan.contexto_num:
        var = _cercano(c.variable, list(cat.numericas))
        if var is None:
            disponibles = ", ".join(cat.numericas) or "ninguno"
            return aclarar(f"«{c.variable}» no es un dato numérico de «{cat.titulo}» (datos numéricos: {disponibles}).")
        if var != c.variable:
            correcciones.append(f"contexto «{c.variable}» → «{var}»")
        contexto_num.append(CondicionContexto(variable=var, op=c.op, valor=c.valor))

    excluir: list[str] = []
    for q in plan.excluir_preguntas:
        pid = _id_pregunta(q, cat)
        if pid is None:
            correcciones.append(f"excluir «{q}»: no es una pregunta de «{cat.titulo}», se ignora")
        elif pid not in excluir:
            excluir.append(pid)

    kpi = plan.kpi
    if kpi is not None and cat.kpis:
        por_nombre = {k.nombre: k.id for k in cat.kpis}
        ids = {k.id for k in cat.kpis}
        if kpi not in ids:
            nombre = _cercano(kpi, list(por_nombre), corte=0.6)
            kpi = por_nombre[nombre] if nombre else None
            if kpi is None and sum(i in plan.kpi for i in ids) < 2:  # varios IDs juntos = «todos», sin aviso
                correcciones.append(f"KPI «{plan.kpi}» no está asociado: se consultan todos los KPIs del instrumento")

    campos = plan.campos
    if isinstance(campos, list):
        campos = [pid for c in campos if (pid := _id_pregunta(c, cat))] or "todas_las_respuestas"

    validado = plan.model_copy(update={
        "instrumentos": instrumentos, "preguntas": preguntas, "filtros": filtros, "respondentes": respondentes,
        "agrupar_por": agrupar, "kpi": kpi, "campos": campos, "contexto": contexto, "contexto_num": contexto_num,
        "excluir_preguntas": excluir,
    })
    return PlanValidado(validado, correcciones)
