# cargar_instru/services.py
"""
Capa de lógica de negocio para el módulo de gestión de instrumentos.

Servicios definidos:
  - ArchivoService      → operaciones de disco (guardar, leer, eliminar archivos)
  - PermisoService      → verificar y registrar propietario
  - JsonCanonicoService → leer el JSON canónico del disco
  - InstrumentoService  → orquestación completa del ciclo de vida

Responsabilidad de cada capa:
  Router  → recibe HTTP, valida con Pydantic, delega al service, devuelve respuesta
  Service → lógica de negocio, queries a la BD, operaciones de disco
  Model   → ORM, mapeo de tablas

Tablas que consumen estos servicios (interfaz):
  instrumento_procesado, raw_data, permiso_instrumento, usuarios

pipeline_limpieza_log no es consultada desde estos servicios — es exclusiva
del módulo pipeline_limpieza/.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from cargar_instru.models import (
    InstrumentoProcesado,
    PermisoInstrumento,
    RawData,
    Usuario,
)
from cargar_instru.schemas import (
    ArtefactosDisponibles,
    FiltrosInstrumento,
    InstrumentoCreate,
    InstrumentoDetalle,
    InstrumentoResumen,
    MetadatosUpdate,
    VersionInfo,
)


# ===========================================================================
# ArchivoService
# Operaciones de disco para archivos físicos del instrumento.
# No toca la base de datos.
# ===========================================================================

class ArchivoService:
    """Operaciones de disco para archivos del instrumento."""

    @staticmethod
    def calcular_hash_md5(contenido: bytes) -> str:
        """Devuelve el hex digest MD5 del contenido del archivo."""
        return hashlib.md5(contenido).hexdigest()

    @staticmethod
    def generar_nombre_unico(instrumento_id: int, nombre_original: str) -> str:
        """
        Genera un nombre de archivo único para storage/raw/.
        Formato: {instrumento_id}_{timestamp_unix}_{uuid8}{extension}
        """
        extension = Path(nombre_original).suffix.lower()
        ts        = int(datetime.now(timezone.utc).timestamp())
        uid       = uuid.uuid4().hex[:8]
        return f"{instrumento_id}_{ts}_{uid}{extension}"

    @staticmethod
    def guardar_archivo(contenido: bytes, directorio: Path, nombre: str) -> Path:
        """
        Escribe el archivo en disco.
        Crea el directorio si no existe.
        Devuelve la ruta absoluta al archivo guardado.
        """
        directorio.mkdir(parents=True, exist_ok=True)
        ruta = directorio / nombre
        ruta.write_bytes(contenido)
        return ruta

    @staticmethod
    def ruta_relativa(ruta_abs: Path) -> str:
        """
        Convierte una ruta absoluta a ruta relativa desde PROJECT_ROOT.
        Se usa para almacenar en la BD (portabilidad entre entornos).
        """
        return str(ruta_abs.relative_to(settings.PROJECT_ROOT))

    @staticmethod
    def ruta_absoluta(ruta_relativa: str) -> Path:
        """Convierte la ruta relativa almacenada en BD a ruta absoluta."""
        return settings.PROJECT_ROOT / ruta_relativa

    @staticmethod
    def eliminar_archivo(ruta: Path) -> None:
        """Elimina el archivo si existe. Silencioso si no existe."""
        try:
            ruta.unlink()
        except FileNotFoundError:
            pass

    @staticmethod
    def archivo_existe(ruta_relativa: str | None) -> bool:
        """Verifica si el artefacto en disco existe dado su ruta relativa en BD."""
        if not ruta_relativa:
            return False
        return (settings.PROJECT_ROOT / ruta_relativa).is_file()


# ===========================================================================
# PermisoService
# Gestión del propietario de un instrumento.
# ===========================================================================

class PermisoService:
    """Registro y verificación del propietario de un instrumento."""

    @staticmethod
    def crear_propietario(
        db: Session,
        instrumento_id: int,
        usuario_id: int,
    ) -> PermisoInstrumento:
        """
        Crea el registro de propietario al crear el instrumento.
        Se llama automáticamente en InstrumentoService.crear().
        """
        permiso = PermisoInstrumento(
            instrumento_id=instrumento_id,
            usuario_id=usuario_id,
            rol="propietario",
        )
        db.add(permiso)
        db.flush()  # obtiene permiso_id sin cerrar la transacción
        return permiso

    @staticmethod
    def es_propietario(
        db: Session,
        instrumento_id: int,
        usuario_id: int,
    ) -> bool:
        """Devuelve True si el usuario es propietario del instrumento."""
        return (
            db.query(PermisoInstrumento)
            .filter(
                PermisoInstrumento.instrumento_id == instrumento_id,
                PermisoInstrumento.usuario_id == usuario_id,
            )
            .first()
        ) is not None

    @staticmethod
    def obtener_nombre_propietario(
        db: Session,
        instrumento_id: int,
    ) -> str | None:
        """
        Resuelve el nombre de usuario del propietario del instrumento.
        Hace JOIN permiso_instrumento → usuarios.
        """
        resultado = (
            db.query(Usuario.usuario)
            .join(
                PermisoInstrumento,
                PermisoInstrumento.usuario_id == Usuario.usuario_id,
            )
            .filter(PermisoInstrumento.instrumento_id == instrumento_id)
            .scalar()
        )
        return resultado


# ===========================================================================
# JsonCanonicoService
# Lectura del JSON canónico en disco.
# El JSON solo existe desde estado 'estandarizado'.
# La escritura del JSON es responsabilidad del pipeline de estandarización.
# ===========================================================================

class JsonCanonicoService:
    """Acceso de lectura al JSON canónico del instrumento."""

    @staticmethod
    def leer(instrumento_id: int) -> dict[str, Any] | None:
        """
        Lee y deserializa el JSON canónico desde storage/json/{id}.json.
        Devuelve None si el archivo no existe (instrumento aún no estandarizado).
        """
        ruta = settings.json_path_abs / f"{instrumento_id}.json"
        if not ruta.is_file():
            return None
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def actualizar_bloques(
        instrumento_id: int,
        metadatos: MetadatosUpdate,
    ) -> bool:
        """
        Actualiza los bloques dublin_core y contexto del JSON canónico en disco.
        Solo modifica los campos enviados (merge parcial).
        No toca kpis_inferidos ni unidades_semanticas.

        Usa escritura atómica: escribe en temporal → os.replace() → archivo final.
        Devuelve True si el archivo fue actualizado, False si no existía.
        """
        ruta = settings.json_path_abs / f"{instrumento_id}.json"
        if not ruta.is_file():
            return False

        datos = json.loads(ruta.read_text(encoding="utf-8"))

        # Actualizar bloque dublin_core
        dc_update = metadatos.model_dump(
            include={
                "dc_title", "dc_creator", "dc_subject", "dc_description",
                "dc_publisher", "dc_contributor", "dc_date", "dc_type",
                "dc_format", "dc_identifier", "dc_language", "dc_coverage",
                "dc_rights", "dc_source", "dc_relation",
            },
            exclude_none=True,
        )
        if dc_update:
            datos.setdefault("dublin_core", {}).update(dc_update)

        # Actualizar campos de contexto adicionales
        ctx_update: dict[str, Any] = {}
        if metadatos.objetivo is not None:
            ctx_update["objetivo"] = metadatos.objetivo
        if metadatos.periodo_fin is not None:
            ctx_update["periodo_fin"] = metadatos.periodo_fin
        if ctx_update:
            datos.setdefault("contexto", {}).update(ctx_update)

        # Actualizar bloque especifico si fue enviado
        if metadatos.especifico is not None:
            datos["especifico"] = metadatos.especifico

        # Actualizar timestamp
        datos.setdefault("_meta", {})["ultima_actualizacion"] = (
            datetime.now(timezone.utc).isoformat()
        )

        # Escritura atómica
        JsonCanonicoService._escribir_atomico(ruta, datos)
        return True

    @staticmethod
    def eliminar(instrumento_id: int) -> None:
        """
        Elimina el JSON canónico del disco.
        Se llama al cargar nueva versión del archivo.
        """
        ruta = settings.json_path_abs / f"{instrumento_id}.json"
        ArchivoService.eliminar_archivo(ruta)

    @staticmethod
    def _escribir_atomico(ruta: Path, datos: dict[str, Any]) -> None:
        """
        Escribe el JSON de forma atómica: temp → os.replace().
        Evita JSON corruptos ante fallos de disco o de proceso.
        """
        directorio = ruta.parent
        directorio.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=directorio,
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            nombre_temp = f.name
        os.replace(nombre_temp, ruta)


# ===========================================================================
# InstrumentoService
# Orquestación del ciclo de vida del instrumento para la interfaz.
# Consume: instrumento_procesado, raw_data, permiso_instrumento, usuarios.
# ===========================================================================

class InstrumentoService:
    """Lógica de negocio del ciclo de vida del instrumento."""

    # ── Creación ─────────────────────────────────────────────────────────

    @staticmethod
    async def crear(
        db: Session,
        usuario_id: int,
        datos: InstrumentoCreate,
        archivo: UploadFile,
    ) -> InstrumentoProcesado:
        """
        Crea un instrumento nuevo en la BD y guarda el archivo en disco.

        Pasos:
          1. Lee el archivo en memoria y calcula su hash.
          2. Verifica que el mismo usuario no haya subido ya ese archivo.
          3. Crea el registro en instrumento_procesado (estado = 'recibido').
          4. Guarda el archivo en storage/raw/.
          5. Crea el registro en raw_data.
          6. Crea el registro en permiso_instrumento (propietario).
          7. Confirma la transacción.

        El pipeline de limpieza detectará el estado 'recibido' y procesará
        el instrumento automáticamente (ver pipeline_limpieza/orchestrator.py).
        """
        # 1. Leer archivo en memoria
        contenido = await archivo.read()

        # 2. Verificar duplicado por (hash, usuario)
        hash_md5 = ArchivoService.calcular_hash_md5(contenido)
        duplicado = (
            db.query(RawData)
            .filter(
                RawData.hash_md5 == hash_md5,
                RawData.usuario_id == usuario_id,
            )
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Ya tienes un instrumento con este archivo. "
                    "Puedes subir una nueva versión desde el catálogo."
                ),
            )

        # 3. Crear registro instrumento_procesado
        instrumento = InstrumentoProcesado(
            nombre=datos.nombre,
            tipo_instrumento=datos.tipo_instrumento,
            visibilidad=datos.visibilidad,
            estado="recibido",
            version=1,
        )
        db.add(instrumento)
        db.flush()  # obtiene instrumento_id

        # 4. Guardar archivo en disco
        nombre_archivo = ArchivoService.generar_nombre_unico(
            instrumento.instrumento_id,
            archivo.filename or "archivo",
        )
        ruta_abs = ArchivoService.guardar_archivo(
            contenido,
            settings.raw_path_abs,
            nombre_archivo,
        )

        # 5. Crear registro raw_data
        raw = RawData(
            instrumento_id=instrumento.instrumento_id,
            usuario_id=usuario_id,
            tipo_de_instrumento=datos.tipo_instrumento,
            raw_archivo=ArchivoService.ruta_relativa(ruta_abs),
            nombre_original=archivo.filename or nombre_archivo,
            tipo_mime=archivo.content_type,
            tamano_bytes=len(contenido),
            hash_md5=hash_md5,
        )
        db.add(raw)

        # 6. Crear permiso propietario
        PermisoService.crear_propietario(
            db, instrumento.instrumento_id, usuario_id
        )

        db.commit()
        db.refresh(instrumento)
        return instrumento

    # ── Listado ───────────────────────────────────────────────────────────

    @staticmethod
    def listar(
        db: Session,
        usuario_id: int,
        filtros: FiltrosInstrumento,
        es_admin: bool = False,
    ) -> list[InstrumentoResumen]:
        """
        Lista instrumentos accesibles para el usuario.

        Regla de visibilidad (sin admin):
          instrumento público  OR  usuario es propietario

        Con es_admin=True devuelve todos sin restricción de visibilidad.
        """
        query = db.query(InstrumentoProcesado)

        # Filtro de acceso
        if not es_admin:
            if filtros.solo_propios:
                subq = (
                    db.query(PermisoInstrumento.instrumento_id)
                    .filter(PermisoInstrumento.usuario_id == usuario_id)
                    .scalar_subquery()
                )
                query = query.filter(InstrumentoProcesado.instrumento_id.in_(subq))
            else:
                subq = (
                    db.query(PermisoInstrumento.instrumento_id)
                    .filter(PermisoInstrumento.usuario_id == usuario_id)
                    .scalar_subquery()
                )
                query = query.filter(
                    or_(
                        InstrumentoProcesado.visibilidad == "publico",
                        InstrumentoProcesado.instrumento_id.in_(subq),
                    )
                )

        # Filtros opcionales
        if filtros.q:
            query = query.filter(
                InstrumentoProcesado.nombre.ilike(f"%{filtros.q}%")
            )
        if filtros.tipo_instrumento:
            query = query.filter(
                InstrumentoProcesado.tipo_instrumento == filtros.tipo_instrumento
            )
        if filtros.visibilidad:
            query = query.filter(
                InstrumentoProcesado.visibilidad == filtros.visibilidad
            )
        if filtros.fecha_desde:
            query = query.filter(
                InstrumentoProcesado.creado_en >= filtros.fecha_desde
            )
        if filtros.fecha_hasta:
            query = query.filter(
                InstrumentoProcesado.creado_en <= filtros.fecha_hasta
            )
        if filtros.propietario:
            subq_usuario = (
                db.query(PermisoInstrumento.instrumento_id)
                .join(Usuario, Usuario.usuario_id == PermisoInstrumento.usuario_id)
                .filter(Usuario.usuario.ilike(f"%{filtros.propietario}%"))
                .scalar_subquery()
            )
            query = query.filter(
                InstrumentoProcesado.instrumento_id.in_(subq_usuario)
            )

        # Paginación
        instrumentos = (
            query
            .order_by(InstrumentoProcesado.creado_en.desc())
            .offset(filtros.skip)
            .limit(filtros.limit)
            .all()
        )

        # Construir respuesta con nombre del propietario
        resultado: list[InstrumentoResumen] = []
        for instr in instrumentos:
            nombre_propietario = PermisoService.obtener_nombre_propietario(
                db, instr.instrumento_id
            )
            resumen = InstrumentoResumen.model_validate(instr)
            resumen.propietario = nombre_propietario
            resultado.append(resumen)

        return resultado

    # ── Detalle ───────────────────────────────────────────────────────────

    @staticmethod
    def obtener_detalle(
        db: Session,
        instrumento: InstrumentoProcesado,
    ) -> InstrumentoDetalle:
        """
        Construye el detalle del instrumento.
        Lee el JSON canónico del disco si el instrumento está en 'estandarizado'
        o 'vectorizado'. En otros estados metadatos_canonicos es None.
        """
        nombre_propietario = PermisoService.obtener_nombre_propietario(
            db, instrumento.instrumento_id
        )

        metadatos_canonicos: dict | None = None
        if instrumento.estado in ("estandarizado", "vectorizado"):
            metadatos_canonicos = JsonCanonicoService.leer(instrumento.instrumento_id)

        detalle = InstrumentoDetalle.model_validate(instrumento)
        detalle.propietario       = nombre_propietario
        detalle.metadatos_canonicos = metadatos_canonicos
        return detalle

    # ── Edición de metadatos ──────────────────────────────────────────────

    @staticmethod
    def actualizar_metadatos(
        db: Session,
        instrumento: InstrumentoProcesado,
        metadatos: MetadatosUpdate,
    ) -> InstrumentoDetalle:
        """
        Actualiza el nombre en instrumento_procesado si dc_title cambia.
        Actualiza el JSON canónico en disco si existe.
        Si el instrumento estaba en 'vectorizado', lo regresa a 'estandarizado'.
        """
        # Actualizar nombre en BD si dc_title fue enviado
        if metadatos.dc_title:
            instrumento.nombre = metadatos.dc_title
            db.add(instrumento)

        # Actualizar JSON canónico si existe (estado estandarizado o vectorizado)
        if instrumento.estado in ("estandarizado", "vectorizado"):
            JsonCanonicoService.actualizar_bloques(
                instrumento.instrumento_id, metadatos
            )
            # Regresión a estandarizado para forzar re-vectorización
            if instrumento.estado == "vectorizado":
                instrumento.estado = "estandarizado"
                instrumento.fecha_procesamiento = datetime.now(timezone.utc)
                db.add(instrumento)

        db.commit()
        db.refresh(instrumento)
        return InstrumentoService.obtener_detalle(db, instrumento)

    # ── Visibilidad ───────────────────────────────────────────────────────

    @staticmethod
    def cambiar_visibilidad(
        db: Session,
        instrumento: InstrumentoProcesado,
        visibilidad: str,
    ) -> InstrumentoProcesado:
        """Cambia la visibilidad del instrumento. Solo el propietario."""
        instrumento.visibilidad = visibilidad
        db.add(instrumento)
        db.commit()
        db.refresh(instrumento)
        return instrumento

    # ── Nueva versión del archivo ─────────────────────────────────────────

    @staticmethod
    async def cargar_nueva_version(
        db: Session,
        usuario_id: int,
        instrumento: InstrumentoProcesado,
        archivo: UploadFile,
    ) -> InstrumentoProcesado:
        """
        Sube una nueva versión del archivo físico del instrumento.

        - Verifica que el hash sea distinto al de la versión actual.
        - Crea un nuevo registro en raw_data (el anterior permanece).
        - Incrementa version en instrumento_procesado.
        - Elimina el JSON canónico anterior del disco.
        - Resetea el estado a 'recibido' para que el pipeline recomience.
        """
        contenido = await archivo.read()
        hash_nuevo = ArchivoService.calcular_hash_md5(contenido)

        # Obtener hash de la versión actual
        raw_actual = (
            db.query(RawData)
            .filter(RawData.instrumento_id == instrumento.instrumento_id)
            .order_by(RawData.raw_data_id.desc())
            .first()
        )
        if raw_actual and raw_actual.hash_md5 == hash_nuevo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El archivo es idéntico a la versión actual. Sube un archivo diferente.",
            )

        # Guardar nuevo archivo
        nombre_archivo = ArchivoService.generar_nombre_unico(
            instrumento.instrumento_id,
            archivo.filename or "archivo",
        )
        ruta_abs = ArchivoService.guardar_archivo(
            contenido,
            settings.raw_path_abs,
            nombre_archivo,
        )

        # Nuevo raw_data
        raw = RawData(
            instrumento_id=instrumento.instrumento_id,
            usuario_id=usuario_id,
            tipo_de_instrumento=instrumento.tipo_instrumento,
            raw_archivo=ArchivoService.ruta_relativa(ruta_abs),
            nombre_original=archivo.filename or nombre_archivo,
            tipo_mime=archivo.content_type,
            tamano_bytes=len(contenido),
            hash_md5=hash_nuevo,
        )
        db.add(raw)

        # Eliminar JSON canónico anterior
        JsonCanonicoService.eliminar(instrumento.instrumento_id)

        # Actualizar instrumento
        instrumento.version += 1
        instrumento.estado   = "recibido"
        instrumento.ruta_json = None
        instrumento.ruta_sav  = None
        instrumento.error_detalle = None
        instrumento.fecha_procesamiento = datetime.now(timezone.utc)
        db.add(instrumento)

        db.commit()
        db.refresh(instrumento)
        return instrumento

    # ── Eliminación ───────────────────────────────────────────────────────

    @staticmethod
    def eliminar(
        db: Session,
        instrumento: InstrumentoProcesado,
    ) -> None:
        """
        Elimina el instrumento y todos sus artefactos.

        - Elimina los archivos físicos de raw_data del disco.
        - Elimina el JSON canónico del disco.
        - Elimina el .sav del disco si existe.
        - Elimina el registro de instrumento_procesado (cascade en BD).
        """
        # Eliminar archivos crudos del disco
        for raw in instrumento.raw_versions:
            ruta = ArchivoService.ruta_absoluta(raw.raw_archivo)
            ArchivoService.eliminar_archivo(ruta)

        # Eliminar JSON canónico
        JsonCanonicoService.eliminar(instrumento.instrumento_id)

        # Eliminar .sav si existe
        if instrumento.ruta_sav:
            ArchivoService.eliminar_archivo(
                ArchivoService.ruta_absoluta(instrumento.ruta_sav)
            )

        # Eliminar texto limpio si existe
        if instrumento.ruta_texto_limpio:
            ArchivoService.eliminar_archivo(
                ArchivoService.ruta_absoluta(instrumento.ruta_texto_limpio)
            )

        db.delete(instrumento)
        db.commit()

    # ── Artefactos ────────────────────────────────────────────────────────

    @staticmethod
    def obtener_artefactos(
        instrumento: InstrumentoProcesado,
    ) -> ArtefactosDisponibles:
        """
        Indica qué artefactos existen para el instrumento.
        La interfaz usa esto para decidir qué botones de descarga mostrar.
        """
        tiene_json = ArchivoService.archivo_existe(instrumento.ruta_json)
        tiene_sav  = (
            instrumento.tipo_instrumento == "encuesta"
            and ArchivoService.archivo_existe(instrumento.ruta_sav)
        )
        return ArtefactosDisponibles(
            instrumento_id=instrumento.instrumento_id,
            archivo_original=True,   # siempre disponible
            json_canonico=tiene_json,
            sav=tiene_sav,
        )

    @staticmethod
    def obtener_ruta_archivo_original(
        db: Session,
        instrumento: InstrumentoProcesado,
    ) -> tuple[Path, str]:
        """
        Devuelve (ruta_absoluta, nombre_original) del archivo más reciente.
        Lanza 404 si no existe ningún raw_data (no debería ocurrir).
        """
        raw = (
            db.query(RawData)
            .filter(RawData.instrumento_id == instrumento.instrumento_id)
            .order_by(RawData.raw_data_id.desc())
            .first()
        )
        if raw is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo original no encontrado.",
            )
        return ArchivoService.ruta_absoluta(raw.raw_archivo), raw.nombre_original

    @staticmethod
    def obtener_ruta_json(instrumento: InstrumentoProcesado) -> Path:
        """
        Devuelve la ruta absoluta al JSON canónico.
        Lanza 404 si no existe (instrumento en recibido o limpio).
        """
        if not instrumento.ruta_json:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "El JSON canónico no está disponible. "
                    "El instrumento debe estar en estado 'estandarizado' o 'vectorizado'."
                ),
            )
        ruta = ArchivoService.ruta_absoluta(instrumento.ruta_json)
        if not ruta.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El archivo JSON canónico no se encontró en disco.",
            )
        return ruta

    @staticmethod
    def obtener_ruta_sav(instrumento: InstrumentoProcesado) -> Path:
        """
        Devuelve la ruta absoluta al archivo .sav.
        Lanza 422 si el tipo de instrumento no es encuesta.
        Lanza 404 si el archivo no existe.
        """
        if instrumento.tipo_instrumento != "encuesta":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"El instrumento es de tipo '{instrumento.tipo_instrumento}'. "
                    "Solo las encuestas generan archivo .sav."
                ),
            )
        if not instrumento.ruta_sav:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "El archivo .sav no está disponible aún. "
                    "El instrumento debe alcanzar el estado 'estandarizado'."
                ),
            )
        ruta = ArchivoService.ruta_absoluta(instrumento.ruta_sav)
        if not ruta.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El archivo .sav no se encontró en disco.",
            )
        return ruta

    # ── Historial de versiones ────────────────────────────────────────────

    @staticmethod
    def listar_versiones(
        db: Session,
        instrumento: InstrumentoProcesado,
    ) -> list[VersionInfo]:
        """
        Devuelve el historial de versiones del archivo físico.
        Ordena por raw_data_id ascendente (versión 1 primero).
        """
        registros = (
            db.query(RawData)
            .filter(RawData.instrumento_id == instrumento.instrumento_id)
            .order_by(RawData.raw_data_id.asc())
            .all()
        )
        versiones: list[VersionInfo] = []
        for numero, raw in enumerate(registros, start=1):
            versiones.append(
                VersionInfo(
                    raw_data_id=raw.raw_data_id,
                    numero_version=numero,
                    nombre_original=raw.nombre_original,
                    tipo_mime=raw.tipo_mime,
                    tamano_bytes=raw.tamano_bytes,
                    subido=raw.subido,
                )
            )
        return versiones

    @staticmethod
    def obtener_ruta_version(
        db: Session,
        instrumento_id: int,
        raw_data_id: int,
    ) -> tuple[Path, str]:
        """
        Devuelve (ruta_absoluta, nombre_original) para una versión específica.
        Lanza 404 si no existe o no pertenece al instrumento.
        """
        raw = (
            db.query(RawData)
            .filter(
                and_(
                    RawData.raw_data_id == raw_data_id,
                    RawData.instrumento_id == instrumento_id,
                )
            )
            .first()
        )
        if raw is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Versión {raw_data_id} no encontrada para este instrumento.",
            )
        return ArchivoService.ruta_absoluta(raw.raw_archivo), raw.nombre_original
