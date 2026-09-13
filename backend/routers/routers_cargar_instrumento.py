# cargar_instru/routers_cargar_instru.py
"""
Endpoints FastAPI para el módulo de gestión de instrumentos.

Prefijo base: /route_instru  (registrado en main.py)

Pantallas que cubre este router:
  1. Catálogo de instrumentos  → GET /instrumentos
  2. Detalle de instrumento    → GET /instrumentos/{id}
  3. Gestión (carga, edición,
     visibilidad, versiones,
     eliminación)              → POST / PATCH / DELETE
  4. Descarga de artefactos   → GET /instrumentos/{id}/descargar
                                 GET /instrumentos/{id}/json
                                 GET /instrumentos/{id}/sav
  5. Historial de versiones   → GET /instrumentos/{id}/versiones
                                 GET /instrumentos/{id}/versiones/{raw_id}/descargar

Reglas de acceso resumidas:
  - Lectura:   público OR propietario  (puede_acceder_o_403)
  - Escritura: solo propietario        (verificar_propietario)
  - Descarga:  igual que lectura

Tablas consultadas por este módulo:
  instrumento_procesado, raw_data, permiso_instrumento, usuarios
  (pipeline_limpieza_log no se consulta desde aquí)
"""
#los routers somo como controllers a los cuales les llegan las peticiones de lo que alguien quiere hacer en la interfaz
from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.dependencies_cargar_instru import (
    DBSession,
    InstrumentoAcceso,
    InstrumentoProp,
    UsuarioActual,
    get_instrumento_o_404,
)
from app.models.models_cargar_instru import InstrumentoProcesado
from app.schemas.schemas_cargar_instru import (
    ArtefactosDisponibles,
    CargaResponse,
    FiltrosInstrumento,
    InstrumentoCreate,
    InstrumentoDetalle,
    InstrumentoResumen,
    MetadatosUpdate,
    OperacionResponse,
    TipoInstrumento,
    VersionInfo,
    Visibilidad,
    VisibilidadUpdate,
)
from app.services.services_cargar_instru import InstrumentoService

app = APIRouter()


# ===========================================================================
# Pantalla 1 — Catálogo de instrumentos
# ===========================================================================

@app.get(
    "/instrumentos",
    response_model=list[InstrumentoResumen],
    summary="Listar instrumentos accesibles",
    description=(
        "Devuelve los instrumentos públicos más los propios del usuario autenticado. "
        "Soporta filtros por texto, tipo, visibilidad, autor y rango de fechas."
    ),
)
def listar_instrumentos(
    usuario_actual: UsuarioActual,
    db: DBSession,
    q:                str | None             = Query(default=None, description="Búsqueda en nombre"),
    tipo_instrumento: TipoInstrumento | None = Query(default=None),
    propietario:      str | None             = Query(default=None, description="Nombre de usuario del propietario"),
    visibilidad:      Visibilidad | None     = Query(default=None),
    fecha_desde:      str | None             = Query(default=None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta:      str | None             = Query(default=None, description="Fecha hasta (YYYY-MM-DD)"),
    solo_propios:     bool                   = Query(default=False),
    skip:             int                    = Query(default=0, ge=0),
    limit:            int                    = Query(default=20, ge=1, le=100),
) -> list[InstrumentoResumen]:
    from datetime import date

    filtros = FiltrosInstrumento(
        q=q,
        tipo_instrumento=tipo_instrumento,
        propietario=propietario,
        visibilidad=visibilidad,
        fecha_desde=date.fromisoformat(fecha_desde) if fecha_desde else None,
        fecha_hasta=date.fromisoformat(fecha_hasta) if fecha_hasta else None,
        solo_propios=solo_propios,
        skip=skip,
        limit=limit,
    )
    return InstrumentoService.listar(db, usuario_actual.usuario_id, filtros)


@app.get(
    "/instrumentos/propios",
    response_model=list[InstrumentoResumen],
    summary="Listar solo mis instrumentos",
    description="Atajo equivalente a GET /instrumentos?solo_propios=true.",
)
def listar_propios(
    usuario_actual: UsuarioActual,
    db: DBSession,
    q:                str | None             = Query(default=None),
    tipo_instrumento: TipoInstrumento | None = Query(default=None),
    fecha_desde:      str | None             = Query(default=None),
    fecha_hasta:      str | None             = Query(default=None),
    skip:             int                    = Query(default=0, ge=0),
    limit:            int                    = Query(default=20, ge=1, le=100),
) -> list[InstrumentoResumen]:
    from datetime import date

    filtros = FiltrosInstrumento(
        q=q,
        tipo_instrumento=tipo_instrumento,
        fecha_desde=date.fromisoformat(fecha_desde) if fecha_desde else None,
        fecha_hasta=date.fromisoformat(fecha_hasta) if fecha_hasta else None,
        solo_propios=True,
        skip=skip,
        limit=limit,
    )
    return InstrumentoService.listar(db, usuario_actual.usuario_id, filtros)


# ===========================================================================
# Pantalla 2 — Detalle del instrumento
# ===========================================================================

@app.get(
    "/instrumentos/{instrumento_id}",
    response_model=InstrumentoDetalle,
    summary="Detalle del instrumento",
    description=(
        "Devuelve todos los campos del instrumento. "
        "Incluye metadatos_canonicos leídos del JSON en disco "
        "si el instrumento está en estado 'estandarizado' o 'vectorizado'."
    ),
)
def obtener_instrumento(
    instrumento: InstrumentoAcceso,
    db: DBSession,
) -> InstrumentoDetalle:
    return InstrumentoService.obtener_detalle(db, instrumento)


# ===========================================================================
# Pantalla 3 — Gestión: crear instrumento
# ===========================================================================

@app.post(
    "/instrumentos",
    response_model=CargaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar nuevo instrumento",
    description=(
        "Recibe el archivo y los 13 campos Dublin Core obligatorios "
        "en multipart/form-data. Crea el instrumento en estado 'recibido'. "
        "El pipeline de limpieza se activa automáticamente."
    ),
)
async def cargar_instrumento(
    usuario_actual: UsuarioActual,
    db: DBSession,
    archivo: UploadFile,
    # ── Datos básicos ─────────────────────────────────────────────────────
    nombre:           str        = Form(...),
    tipo_instrumento: str        = Form(...),
    visibilidad:      str        = Form(default="publico"),
    # ── 13 campos Dublin Core obligatorios ────────────────────────────────
    dc_title:       str       = Form(...),
    dc_creator:     str       = Form(...),
    dc_subject:     str       = Form(..., description="Lista separada por comas"),
    dc_description: str       = Form(...),
    dc_publisher:   str       = Form(...),
    dc_contributor: str       = Form(...),
    dc_date:        str       = Form(...),
    dc_type:        str       = Form(...),
    dc_format:      str       = Form(...),
    dc_identifier:  str       = Form(...),
    dc_language:    str       = Form(...),
    dc_coverage:    str       = Form(...),
    dc_rights:      str       = Form(...),
    # ── Campos Dublin Core opcionales ─────────────────────────────────────
    dc_source:   str | None = Form(default=None),
    dc_relation: str | None = Form(default=None),
) -> CargaResponse:
    # dc_subject llega como string separado por comas desde el formulario
    subject_lista = [s.strip() for s in dc_subject.split(",") if s.strip()]

    datos = InstrumentoCreate(
        nombre=nombre,
        tipo_instrumento=tipo_instrumento,       # type: ignore[arg-type]
        visibilidad=visibilidad,                 # type: ignore[arg-type]
        dc_title=dc_title,
        dc_creator=dc_creator,
        dc_subject=subject_lista,
        dc_description=dc_description,
        dc_publisher=dc_publisher,
        dc_contributor=dc_contributor,
        dc_date=dc_date,
        dc_type=dc_type,
        dc_format=dc_format,
        dc_identifier=dc_identifier,
        dc_language=dc_language,
        dc_coverage=dc_coverage,
        dc_rights=dc_rights,
        dc_source=dc_source,
        dc_relation=dc_relation,
    )

    instrumento = await InstrumentoService.crear(
        db, usuario_actual.usuario_id, datos, archivo
    )

    return CargaResponse(
        instrumento_id=instrumento.instrumento_id,
        version=instrumento.version,
        estado=instrumento.estado,           # type: ignore[arg-type]
        visibilidad=instrumento.visibilidad, # type: ignore[arg-type]
        mensaje="Instrumento registrado. El contenido se procesará en segundo plano.",
    )


# ===========================================================================
# Pantalla 3 — Gestión: editar metadatos
# ===========================================================================

@app.patch(
    "/instrumentos/{instrumento_id}/metadatos",
    response_model=InstrumentoDetalle,
    summary="Editar metadatos del instrumento",
    description=(
        "Actualiza dublin_core, contexto y/o especifico. "
        "Si el instrumento estaba en 'vectorizado', regresa a 'estandarizado'. "
        "Solo el propietario puede editar."
    ),
)
def actualizar_metadatos(
    instrumento: InstrumentoProp,
    metadatos: MetadatosUpdate,
    db: DBSession,
) -> InstrumentoDetalle:
    return InstrumentoService.actualizar_metadatos(db, instrumento, metadatos)


# ===========================================================================
# Pantalla 3 — Gestión: cambiar visibilidad
# ===========================================================================

@app.patch(
    "/instrumentos/{instrumento_id}/visibilidad",
    response_model=OperacionResponse,
    summary="Cambiar visibilidad del instrumento",
    description="Cambia entre público y privado. Solo el propietario.",
)
def cambiar_visibilidad(
    instrumento: InstrumentoProp,
    body: VisibilidadUpdate,
    db: DBSession,
) -> OperacionResponse:
    InstrumentoService.cambiar_visibilidad(db, instrumento, body.visibilidad)
    return OperacionResponse(
        instrumento_id=instrumento.instrumento_id,
        mensaje=f"Visibilidad actualizada a '{body.visibilidad}'.",
    )


# ===========================================================================
# Pantalla 3 — Gestión: nueva versión del archivo
# ===========================================================================

@app.post(
    "/instrumentos/{instrumento_id}/versiones",
    response_model=CargaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir nueva versión del archivo",
    description=(
        "Sube un nuevo archivo para el instrumento. "
        "Regresa el estado a 'recibido' y elimina el JSON canónico anterior. "
        "Los metadatos Dublin Core se conservan. "
        "Solo el propietario."
    ),
)
async def cargar_nueva_version(
    instrumento: InstrumentoProp,
    usuario_actual: UsuarioActual,
    db: DBSession,
    archivo: UploadFile,
) -> CargaResponse:
    instrumento_actualizado = await InstrumentoService.cargar_nueva_version(
        db, usuario_actual.usuario_id, instrumento, archivo
    )
    return CargaResponse(
        instrumento_id=instrumento_actualizado.instrumento_id,
        version=instrumento_actualizado.version,
        estado=instrumento_actualizado.estado,           # type: ignore[arg-type]
        visibilidad=instrumento_actualizado.visibilidad, # type: ignore[arg-type]
        mensaje="Nueva versión registrada. El contenido se procesará en segundo plano.",
    )


# ===========================================================================
# Pantalla 3 — Gestión: eliminar instrumento
# ===========================================================================

@app.delete(
    "/instrumentos/{instrumento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar instrumento",
    description=(
        "Elimina el instrumento, todos sus archivos en disco y sus registros en BD. "
        "Solo el propietario."
    ),
)
def eliminar_instrumento(
    instrumento: InstrumentoProp,
    db: DBSession,
) -> None:
    InstrumentoService.eliminar(db, instrumento)


# ===========================================================================
# Pantalla 4 — Descarga de artefactos
# ===========================================================================

@app.get(
    "/instrumentos/{instrumento_id}/artefactos",
    response_model=ArtefactosDisponibles,
    summary="Consultar artefactos disponibles",
    description=(
        "Indica qué artefactos existen para el instrumento. "
        "Usar para decidir qué botones de descarga mostrar en la interfaz."
    ),
)
def obtener_artefactos(
    instrumento: InstrumentoAcceso,
) -> ArtefactosDisponibles:
    return InstrumentoService.obtener_artefactos(instrumento)


@app.get(
    "/instrumentos/{instrumento_id}/descargar",
    summary="Descargar archivo original",
    description=(
        "Descarga el archivo original en su versión más reciente. "
        "Disponible desde estado 'recibido'."
    ),
)
def descargar_archivo(
    instrumento: InstrumentoAcceso,
    db: DBSession,
) -> FileResponse:
    ruta, nombre_original = InstrumentoService.obtener_ruta_archivo_original(
        db, instrumento
    )
    return FileResponse(
        path=str(ruta),
        filename=nombre_original,
        media_type="application/octet-stream",
    )


@app.get(
    "/instrumentos/{instrumento_id}/json",
    summary="Descargar JSON canónico",
    description=(
        "Descarga el JSON canónico del instrumento. "
        "Disponible desde estado 'estandarizado'."
    ),
)
def descargar_json(
    instrumento: InstrumentoAcceso,
) -> FileResponse:
    ruta = InstrumentoService.obtener_ruta_json(instrumento)
    return FileResponse(
        path=str(ruta),
        filename=f"instrumento_{instrumento.instrumento_id}.json",
        media_type="application/json",
    )


@app.get(
    "/instrumentos/{instrumento_id}/sav",
    summary="Descargar archivo .sav",
    description=(
        "Descarga el archivo .sav (SPSS). "
        "Solo disponible para encuestas desde estado 'estandarizado'."
    ),
)
def descargar_sav(
    instrumento: InstrumentoAcceso,
) -> FileResponse:
    ruta = InstrumentoService.obtener_ruta_sav(instrumento)
    return FileResponse(
        path=str(ruta),
        filename=f"instrumento_{instrumento.instrumento_id}.sav",
        media_type="application/octet-stream",
    )


# ===========================================================================
# Pantalla 5 — Historial de versiones
# ===========================================================================

@app.get(
    "/instrumentos/{instrumento_id}/versiones",
    response_model=list[VersionInfo],
    summary="Historial de versiones del archivo",
    description="Lista todas las versiones del archivo físico del instrumento.",
)
def listar_versiones(
    instrumento: InstrumentoAcceso,
    db: DBSession,
) -> list[VersionInfo]:
    return InstrumentoService.listar_versiones(db, instrumento)


@app.get(
    "/instrumentos/{instrumento_id}/versiones/{raw_data_id}/descargar",
    summary="Descargar una versión específica del archivo",
    description="Descarga una versión histórica del archivo identificada por raw_data_id.",
)
def descargar_version(
    instrumento: InstrumentoAcceso,
    raw_data_id: int,
    db: DBSession,
) -> FileResponse:
    ruta, nombre_original = InstrumentoService.obtener_ruta_version(
        db, instrumento.instrumento_id, raw_data_id
    )
    return FileResponse(
        path=str(ruta),
        filename=nombre_original,
        media_type="application/octet-stream",
    )
