"""Router — KPIs desde el perfil semántico (paso «KPIs sugeridos» del wizard).

  POST /vectorizacion/perfil/propuestas  KPIs sugeridos: puntaje, preguntas que lo
                                         sustentan y justificación breve (editable).
  POST /vectorizacion/perfil/confirmar   Guarda aceptados y rechazados en la versión
                                         del conocimiento y registra los aceptados.

Requieren el JWT del api-gateway (se registra quién aceptó cada KPI).
"""
from __future__ import annotations

from fastapi import APIRouter

from shared import tiempos

from app.vectorization.dependencies import DBSession, InvestigadorJWT
from app.vectorization.perfil import servicio
from app.vectorization.schemas.perfil_kpis import (
    ConfirmarPerfilRequest,
    ConfirmarPerfilResponse,
    PropuestasPerfilRequest,
    PropuestasPerfilResponse,
)

router = APIRouter(prefix="/vectorizacion/perfil", tags=["kpis-perfil-semantico"])


@router.post("/propuestas", response_model=PropuestasPerfilResponse, summary="KPIs sugeridos desde el perfil semántico")
def proponer(cuerpo: PropuestasPerfilRequest, db: DBSession, usuario: InvestigadorJWT) -> PropuestasPerfilResponse:
    # Tiempo de cómputo: similitud con el catálogo y justificación de cada KPI (con el modelo, si está activo).
    with tiempos.medir(db, cuerpo.id_crudo, "analysis", "propuesta_kpis") as detalle:
        salida = servicio.proponer(db, usuario, cuerpo.id_crudo, justificar_con_llm=cuerpo.justificar_con_llm)
        detalle.update(kpis_sugeridos=len(salida.kpis))
    return salida


@router.post("/confirmar", response_model=ConfirmarPerfilResponse, summary="Confirma los KPIs aceptados y rechazados")
def confirmar(cuerpo: ConfirmarPerfilRequest, db: DBSession, usuario: InvestigadorJWT) -> ConfirmarPerfilResponse:
    with tiempos.medir(db, cuerpo.id_crudo, "analysis", "confirmar_kpis") as detalle:
        salida = servicio.confirmar(db, usuario, cuerpo)
        detalle.update(aceptados=sum(1 for d in cuerpo.decisiones if d.aceptado))
    return salida
