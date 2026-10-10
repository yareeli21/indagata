"""Router — CÁLCULO real del valor de un KPI por instrumento.

Tras confirmar qué KPIs pertenecen a un instrumento (POST /vectorizacion/confirmar),
el investigador puede CALCULAR el valor numérico real de cada KPI usando su fórmula:

  POST /kpis/calculo/preparar     → envía la fórmula del KPI a Ollama (llama3.2:3b)
                                    para extraer las variables de entrada como JSON.
                                    Si Ollama falla o no puede extraerlas, devuelve
                                    tipo='descriptivo' (el frontend salta ese KPI).
  POST /kpis/calculo/registrar    → recibe los valores capturados y la referencia del
                                    investigador, calcula el semáforo según la polaridad
                                    del KPI y persiste todo en `kpi_calculo`.
  GET  /kpis/calculo/{id}         → lista los cálculos registrados de un instrumento.

El frontend lo llama directo vía ANALYSIS_URL (el gateway no proxea estas rutas),
igual que el catálogo de KPIs y el espacio vectorial.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.vectorization.dependencies import DBSession, UsuarioActual
from shared.db.core.config import settings
from shared.models.kpi import KPI
from shared.models.kpi_calculo import KpiCalculo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kpis/calculo", tags=["kpi-calculo"])

# Prompt EXACTO para que Ollama extraiga las variables de la fórmula del KPI.
_PROMPT_EXTRACCION = """Analiza esta fórmula de KPI educativo y extrae las variables que el investigador debe proporcionar.
Devuelve ÚNICAMENTE un objeto JSON válido, sin explicaciones ni texto adicional.

Fórmula: {formula}

Formato requerido:
{{"tipo": "ratio|conteo|descriptivo", "variables": [{{"clave": "nombre_variable", "etiqueta": "Descripción clara para el investigador", "unidad": "unidad de medida"}}], "expresion": "expresion_python_evaluable_o_null"}}

Reglas:
- tipo 'ratio': fórmula con división, devuelve expresion evaluable en Python con las claves de variables
- tipo 'conteo': número simple, una sola variable
- tipo 'descriptivo': fórmula narrativa sin valores numéricos claros, variables=[], expresion=null
- Las claves deben ser identificadores Python válidos (snake_case, sin espacios)
- La expresion debe ser evaluable con Python eval() usando las claves como variables locales"""


# ── Schemas ───────────────────────────────────────────────────────────────────


class PrepararRequest(BaseModel):
    id_instrumento: int
    kpi_id: int


class VariableKpi(BaseModel):
    clave: str
    etiqueta: str
    unidad: str


class PrepararResponse(BaseModel):
    kpi_id: int
    nombre: str
    tipo: str
    variables: list[VariableKpi]
    expresion: str | None
    formula_texto: str
    descripcion_direccional: str


class RegistrarRequest(BaseModel):
    id_instrumento: int
    kpi_id: int
    variables_input: dict[str, float]
    resultado_valor: float
    resultado_unidad: str
    referencia_valor: float
    referencia_contexto: str


class KpiCalculoResponse(BaseModel):
    kpi_calculo_id: int
    nivel_semaforo: str
    resultado_valor: float
    referencia_valor: float
    interpretacion_texto: str


# ── Helpers ─────────────────────────────────────────────────────────────────


def _descriptivo(kpi: KPI) -> PrepararResponse:
    """Respuesta de fallback: el KPI no admite cálculo automático (Ollama caído o fórmula narrativa)."""
    return PrepararResponse(
        kpi_id=kpi.kpi_id,
        nombre=kpi.nombre,
        tipo="descriptivo",
        variables=[],
        expresion=None,
        formula_texto=kpi.formula_metrica_calculo or "",
        descripcion_direccional=kpi.comportamiento_direccional_causalidad or "",
    )


def _extraer_json(texto: str) -> dict | None:
    """Extrae el primer objeto JSON del texto devuelto por Ollama. None si no hay JSON válido."""
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1 or fin < inicio:
        return None
    try:
        datos = json.loads(texto[inicio : fin + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


async def _preguntar_ollama(formula: str) -> dict | None:
    """Pide a Ollama que extraiga las variables de la fórmula. None si falla."""
    prompt = _PROMPT_EXTRACCION.format(formula=formula)
    try:
        async with httpx.AsyncClient(timeout=30.0) as cliente:
            respuesta = await cliente.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("Ollama no disponible o respuesta inválida al extraer variables del KPI.")
        return None

    return _extraer_json(str(cuerpo.get("response", "")))


def _nivel_semaforo(polaridad: str | None, resultado: float, referencia: float) -> str:
    """Calcula el nivel del semáforo comparando resultado vs. referencia según la polaridad."""
    pol = (polaridad or "").strip().upper()

    if pol.startswith("POSITIVO") or "MAXIMIZAR" in pol:
        if resultado >= referencia:
            return "bueno"
        if resultado >= 0.7 * referencia:
            return "neutro"
        return "riesgo"

    if pol.startswith("NEGATIVO") or "MINIMIZAR" in pol:
        if resultado <= referencia:
            return "bueno"
        if resultado <= 1.3 * referencia:
            return "neutro"
        return "riesgo"

    # PUNTO ÓPTIMO u otros: desviación porcentual absoluta respecto a la referencia.
    if referencia == 0:
        return "bueno" if resultado == 0 else "riesgo"
    desviacion = abs(resultado - referencia) / abs(referencia)
    if desviacion <= 0.15:
        return "bueno"
    if desviacion <= 0.30:
        return "neutro"
    return "riesgo"


def _interpretacion(
    nombre: str, resultado: float, referencia: float, nivel: str, unidad: str
) -> str:
    """Frase corta en español que interpreta el resultado frente a la referencia."""
    sufijo = f"{unidad}".strip()
    res = f"{resultado:g}{sufijo}" if sufijo and sufijo != "%" else (
        f"{resultado:g}%" if sufijo == "%" else f"{resultado:g}"
    )
    ref = f"{referencia:g}{sufijo}" if sufijo and sufijo != "%" else (
        f"{referencia:g}%" if sufijo == "%" else f"{referencia:g}"
    )
    comparacion = (
        "está por debajo de"
        if resultado < referencia
        else "está por encima de"
        if resultado > referencia
        else "coincide con"
    )
    cierre = {
        "bueno": "lo que indica un resultado favorable.",
        "neutro": "lo que indica un resultado aceptable con margen de mejora.",
        "riesgo": "lo que indica un resultado desfavorable.",
    }.get(nivel, "según tu valor de referencia.")
    return f"{nombre} ({res}) {comparacion} tu referencia ({ref}), {cierre}"


def _a_float(valor: Decimal | None) -> float:
    return float(valor) if valor is not None else 0.0


def _a_respuesta(calc: KpiCalculo, nombre: str) -> KpiCalculoResponse:
    resultado = _a_float(calc.resultado_valor)
    referencia = _a_float(calc.referencia_valor)
    return KpiCalculoResponse(
        kpi_calculo_id=calc.kpi_calculo_id,
        nivel_semaforo=calc.nivel_semaforo or "sin_calculo",
        resultado_valor=resultado,
        referencia_valor=referencia,
        interpretacion_texto=_interpretacion(
            nombre, resultado, referencia, calc.nivel_semaforo or "", calc.resultado_unidad or ""
        ),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/preparar",
    response_model=PrepararResponse,
    status_code=status.HTTP_200_OK,
    summary="Preparar el cálculo de un KPI — extraer variables con Ollama",
    description=(
        "Lee la fórmula del KPI de la BD y la envía a Ollama (llama3.2:3b) para extraer "
        "las variables que el investigador debe proporcionar. Si Ollama no está disponible "
        "o la fórmula es narrativa, devuelve tipo='descriptivo' con variables=[] para que "
        "el frontend salte ese KPI sin error."
    ),
)
async def preparar_calculo(
    usuario_actual: UsuarioActual,
    db: DBSession,
    request: PrepararRequest,
) -> PrepararResponse:
    kpi = db.get(KPI, request.kpi_id)
    if kpi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el KPI con kpi_id={request.kpi_id}.",
        )

    formula = kpi.formula_metrica_calculo or ""
    if not formula.strip():
        return _descriptivo(kpi)

    datos = await _preguntar_ollama(formula)
    if datos is None:
        return _descriptivo(kpi)

    tipo = str(datos.get("tipo") or "descriptivo")
    variables_raw = datos.get("variables") or []
    variables: list[VariableKpi] = []
    if isinstance(variables_raw, list):
        for v in variables_raw:
            if not isinstance(v, dict):
                continue
            clave = str(v.get("clave") or "").strip()
            if not clave:
                continue
            variables.append(
                VariableKpi(
                    clave=clave,
                    etiqueta=str(v.get("etiqueta") or clave),
                    unidad=str(v.get("unidad") or ""),
                )
            )

    expresion = datos.get("expresion")
    expresion = str(expresion) if expresion not in (None, "null", "") else None

    # Si no hay variables aprovechables, se trata como descriptivo (se salta).
    if tipo == "descriptivo" or not variables:
        return _descriptivo(kpi)

    return PrepararResponse(
        kpi_id=kpi.kpi_id,
        nombre=kpi.nombre,
        tipo=tipo,
        variables=variables,
        expresion=expresion,
        formula_texto=formula,
        descripcion_direccional=kpi.comportamiento_direccional_causalidad or "",
    )


@router.post(
    "/registrar",
    response_model=KpiCalculoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar el cálculo de un KPI y su semáforo",
    description=(
        "Recibe los valores capturados por el investigador y su valor de referencia, "
        "calcula el nivel del semáforo según la polaridad del KPI y persiste todo en "
        "`kpi_calculo`. Devuelve el resultado con una interpretación en español."
    ),
)
def registrar_calculo(
    usuario_actual: UsuarioActual,
    db: DBSession,
    request: RegistrarRequest,
) -> KpiCalculoResponse:
    kpi = db.get(KPI, request.kpi_id)
    if kpi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el KPI con kpi_id={request.kpi_id}.",
        )

    nivel = _nivel_semaforo(
        kpi.polaridad_rendimiento, request.resultado_valor, request.referencia_valor
    )

    try:
        resultado_valor = Decimal(str(request.resultado_valor))
        referencia_valor = Decimal(str(request.referencia_valor))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los valores numéricos del cálculo no son válidos.",
        ) from exc

    calc = KpiCalculo(
        id_procesado=request.id_instrumento,
        kpi_id=request.kpi_id,
        variables_input=request.variables_input,
        resultado_valor=resultado_valor,
        resultado_unidad=request.resultado_unidad,
        referencia_valor=referencia_valor,
        referencia_contexto=request.referencia_contexto,
        nivel_semaforo=nivel,
        formula_usada=kpi.formula_metrica_calculo,
        calculado_por=usuario_actual.usuario_id,
    )
    try:
        db.add(calc)
        db.commit()
        db.refresh(calc)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Error al guardar el cálculo del KPI en tt_rag.kpi_calculo.")
        raise

    return _a_respuesta(calc, kpi.nombre)


@router.get(
    "/{id_instrumento}",
    response_model=list[KpiCalculoResponse],
    status_code=status.HTTP_200_OK,
    summary="Cálculos registrados de un instrumento",
    description="Devuelve la lista de cálculos de KPI guardados para el instrumento dado.",
)
def listar_calculos(
    usuario_actual: UsuarioActual,
    db: DBSession,
    id_instrumento: int,
) -> list[KpiCalculoResponse]:
    try:
        filas = (
            db.query(KpiCalculo, KPI.nombre)
            .join(KPI, KPI.kpi_id == KpiCalculo.kpi_id)
            .filter(KpiCalculo.id_procesado == id_instrumento)
            .order_by(KpiCalculo.kpi_calculo_id)
            .all()
        )
    except SQLAlchemyError:
        logger.exception("Error al leer los cálculos de KPI de tt_rag.kpi_calculo.")
        raise

    return [_a_respuesta(calc, nombre) for calc, nombre in filas]
