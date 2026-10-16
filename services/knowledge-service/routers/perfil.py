"""Router del perfil semántico (prefijo `/conocimiento`, expuesto en el api-gateway).

- POST /conocimiento/{id_crudo}/perfil/vista-previa  perfil con los metadatos del formulario (sin guardar)
- POST /conocimiento/{id_crudo}/perfil               perfil con los metadatos YA aprobados → versión N
- GET  /conocimiento/{id_crudo}/perfil               perfil de la versión actual
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from dependencies import DBSession, Investigador
from models import MetadatosPayload, PerfilOut, PerfilVistaPreviaOut
from services import fuentes, perfil, versiones

logger = logging.getLogger("knowledge-service")

router = APIRouter(prefix="/conocimiento", tags=["perfil semántico"])

# Fuente de las preguntas según los avisos guardados (el perfil no la incluye: solo
# describe el instrumento).
_FUENTE_POR_AVISO = {"sin_limpieza": "json_tecnico", "sin_original": "encabezados"}


def _construir(id_crudo: int, tipo: str, dc: dict, esp: dict, est) -> dict:  # noqa: ANN001
    try:
        return perfil.construir(id_crudo, tipo, dc, esp, est)
    except perfil.PerfilInvalido as exc:
        logger.exception("Perfil inválido para id_crudo=%s", id_crudo)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"El perfil generado no es válido: {exc}") from exc


@router.post("/{id_crudo}/perfil/vista-previa", response_model=PerfilVistaPreviaOut, summary="Vista previa del perfil semántico")
def vista_previa(id_crudo: int, cuerpo: MetadatosPayload, db: DBSession, usuario: Investigador) -> PerfilVistaPreviaOut:
    ctx = fuentes.cargar(db, usuario, id_crudo)
    est = fuentes.estructura_de(ctx)
    datos = _construir(id_crudo, ctx.tipo, cuerpo.dublin_core, cuerpo.enriquecidos, est)
    return PerfilVistaPreviaOut(perfil=datos, fuente=est.fuente, n_preguntas=perfil.n_preguntas(datos), avisos=est.avisos)


@router.post("/{id_crudo}/perfil", response_model=PerfilOut, summary="Genera y guarda el perfil semántico aprobado")
def generar(id_crudo: int, db: DBSession, usuario: Investigador) -> PerfilOut:
    ctx = fuentes.cargar(db, usuario, id_crudo)
    dc, esp = fuentes.metadatos_aprobados(db, ctx)
    est = fuentes.estructura_de(ctx)
    datos = _construir(id_crudo, ctx.tipo, dc, esp, est)
    fila = versiones.crear_con_perfil(
        db, id_crudo, datos, usuario,
        id_limpieza=ctx.limpieza.id_limpieza if ctx.limpieza else None,
        avisos=[dict(a, origen="perfil") for a in est.avisos],
    )
    return _salida(fila, est.fuente)


@router.get("/{id_crudo}/perfil", response_model=PerfilOut, summary="Perfil semántico de la versión actual")
def obtener(id_crudo: int, db: DBSession, usuario: Investigador) -> PerfilOut:
    fuentes.cargar(db, usuario, id_crudo)  # autoría
    fila = versiones.actual(db, id_crudo)
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El instrumento aún no tiene perfil semántico.")
    return _salida(fila, None)


def _salida(fila, fuente: str | None) -> PerfilOut:  # noqa: ANN001
    avisos = [a for a in (fila.avisos or []) if a.get("origen") == "perfil"]
    fuente_guardada = next((_FUENTE_POR_AVISO[a["codigo"]] for a in avisos if a.get("codigo") in _FUENTE_POR_AVISO), "original")
    return PerfilOut(
        id_crudo=fila.id_crudo,
        version=fila.version,
        estado=fila.estado,
        fecha_creacion=fila.fecha_creacion,
        perfil=fila.perfil,
        fuente=fuente or fuente_guardada,
        n_preguntas=perfil.n_preguntas(fila.perfil),
        avisos=[{"codigo": a["codigo"], "mensaje": a["mensaje"], "n": a.get("n")} for a in avisos],
    )
