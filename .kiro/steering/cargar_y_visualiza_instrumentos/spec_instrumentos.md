---
inclusion: manual
---

# Especificación Funcional y Técnica — Módulo de Gestión de Instrumentos
**Versión:** 2.1  
**Fecha:** Agosto 2026  
**Módulo:** `cargar_instru` + `pipeline_limpieza`  
**Stack:** FastAPI · SQLAlchemy · PostgreSQL (`tt_rag`) · Pydantic v2 · Ollama (LLM local)

---

## Principios de diseño de esta versión

Cinco decisiones de arquitectura guían toda la especificación:

1. **Separación de procesos.** La carga del archivo físico y la captura de metadatos son operaciones independientes con endpoints propios. El archivo puede existir sin metadatos completos; los metadatos pueden actualizarse sin reemplazar el archivo.

2. **JSON canónico como fuente de verdad semántica.** Todo el conocimiento estructurado del instrumento vive en `storage/json/{instrumento_id}.json`. PostgreSQL almacena únicamente campos operativos e índices de búsqueda, nunca duplica el contenido del JSON.

3. **Generación de `.sav` desacoplada de la carga.** El archivo SPSS es un artefacto del pipeline de estandarización, no de la ingesta. Solo se genera cuando el instrumento alcanza el estado `estandarizado`.

4. **Visibilidad controlada.** Cada instrumento tiene un nivel de acceso (`publico | privado`) que determina quién puede leerlo, descargarlo e incluirlo en búsquedas RAG.

5. **Limpieza guiada por LLM como primera etapa automática del pipeline.** Cuando un instrumento entra en estado `ingresado`, el pipeline de limpieza se activa automáticamente: extrae texto del archivo crudo, aplica un LLM local (Ollama) para producir texto limpio y estructurado, actualiza el JSON canónico con trazabilidad completa del proceso, y avanza el instrumento a `limpio`. Los endpoints de usuario no participan en este proceso.

---

## 1. Casos de Uso

| ID   | Actor                | Descripción                                                                       |
|------|----------------------|-----------------------------------------------------------------------------------|
| CU01 | Usuario autenticado  | Cargar el archivo físico de un instrumento nuevo                                  |
| CU02 | Usuario autenticado  | Registrar o actualizar los metadatos de un instrumento propio                     |
| CU03 | Usuario autenticado  | Consultar instrumentos accesibles (propios + públicos de otros)                   |
| CU04 | Usuario autenticado  | Consultar únicamente sus propios instrumentos                                     |
| CU05 | Usuario autenticado  | Descargar el archivo original de un instrumento accesible                         |
| CU06 | Usuario autenticado  | Eliminar un instrumento propio                                                    |
| CU07 | Usuario autenticado  | Cargar una nueva versión del archivo de un instrumento propio                     |
| CU08 | Usuario autenticado  | Cambiar el nivel de visibilidad de un instrumento propio (público/privado)        |
| CU09 | Pipeline (sistema)   | Marcar un instrumento como listo para procesamiento RAG                           |
| CU10 | Pipeline (sistema)   | Escribir el JSON canónico enriquecido después del procesamiento                   |
| CU11 | Pipeline (sistema)   | Generar y almacenar el `.sav` al completar la estandarización                     |
| CU12 | Administrador        | Listar todos los instrumentos del sistema sin restricción de visibilidad          |
| CU13 | Pipeline de limpieza | Extraer texto del archivo crudo, limpiarlo con LLM y actualizar el JSON canónico |

### Flujos principales

**CU01 — Cargar archivo**

1. El usuario envía `POST /instrumentos` con el archivo, nombre y tipo. Los metadatos son opcionales en este paso.
2. El sistema calcula el `hash_md5` del contenido recibido.
3. Si existe otro registro con el mismo `hash_md5` para el mismo `usuario_id`, devuelve `409 Conflict`.
4. Se crea el registro en `instrumento_procesado` con `estado = 'ingresado'` y `visibilidad = 'privado'` por defecto.
5. Se guarda el archivo en `storage/raw/`.
6. Se crea el registro en `raw_data`.
7. Se inicializa el JSON canónico semilla en `storage/json/{instrumento_id}.json` con los datos disponibles y el resto de bloques vacíos.
8. La respuesta devuelve `instrumento_id`, `version` y `estado`.

**CU02 — Registrar o actualizar metadatos**

1. El usuario envía `PATCH /instrumentos/{id}/metadatos` con el cuerpo de metadatos semánticos.
2. El sistema verifica propiedad.
3. Se actualiza el JSON canónico en disco: los bloques `contexto`, `dublin_core` y `especifico` se reescriben con los datos recibidos; los bloques `kpis_inferidos` y `unidades_semanticas` permanecen intactos.
4. PostgreSQL **no almacena** el cuerpo completo de metadatos. Solo actualiza los campos de búsqueda: `nombre`, `tipo_instrumento`, y los campos de índice si cambiaron.
5. Si el instrumento estaba en estado `vectorizado`, se resetea a `ingresado` para forzar reprocesamiento.

**CU07 — Nueva versión del archivo**

1. El usuario envía `POST /instrumentos/{id}/versiones` con el nuevo archivo.
2. El sistema verifica propiedad.
3. Se calcula el hash. Si es idéntico al de la versión más reciente, devuelve `409 Conflict`.
4. Se guarda el nuevo archivo en `storage/raw/`.
5. Se crea nuevo registro en `raw_data`. El anterior permanece intacto.
6. Se incrementa `instrumento_procesado.version`.
7. El estado se resetea a `ingresado`.
8. El JSON canónico **no se sobreescribe** — los metadatos semánticos se conservan. Solo se actualiza el campo operativo `ruta_json` si la ruta cambió.

**CU09 — Marcar para pipeline RAG**

1. El pipeline invoca `PATCH /instrumentos/{id}/estado` con `estado = 'limpio'` (o el siguiente estado del flujo).
2. El sistema valida que la transición de estado es válida (ver §3.3).
3. Se actualiza el estado en PostgreSQL.
4. No se modifica el JSON canónico.

**CU11 — Generar `.sav`**

1. El pipeline invoca internamente `SavService.generar_sav(instrumento_id)` una vez que el estado es `estandarizado` y el tipo es `encuesta`.
2. El service lee el bloque `especifico.dimensiones` del JSON canónico.
3. Construye el DataFrame y escribe `storage/sav/{instrumento_id}.sav`.
4. Actualiza `instrumento_procesado.ruta_sav`.

---

## 2. Entidades de Dominio

```
InstrumentoProcesado          ← Registro operativo y de búsqueda
  ├── RawData (1..N)          ← Historial de archivos físicos por versión
  ├── PermisoInstrumento       ← Nivel de visibilidad y reglas de acceso
  └── DocumentoVectorizado (N) ← Chunks en ChromaDB (pipeline posterior)

Usuarios                      ← Propietario (FK en raw_data.usuario_id)
```

### Separación de responsabilidades entre PostgreSQL y JSON canónico

| Dato                                          | PostgreSQL | JSON canónico |
|-----------------------------------------------|:----------:|:-------------:|
| `instrumento_id`, `version`, `estado`         | ✓          | —             |
| `nombre`, `tipo_instrumento`                  | ✓ (índice) | ✓ (contexto)  |
| `ruta_json`, `ruta_sav`, `ruta_raw`           | ✓          | —             |
| `ruta_texto_extraido`, `ruta_texto_limpio`    | ✓          | —             |
| `hash_md5`, `tipo_mime`, `tamano_bytes`       | ✓          | —             |
| `visibilidad`, `creado_en`, `schema_version`  | ✓          | —             |
| `error_detalle`                               | ✓          | —             |
| Bloque `contexto` completo                    | —          | ✓             |
| Bloque `dublin_core`                          | —          | ✓             |
| Bloque `especifico` (dimensiones, ítems…)     | —          | ✓             |
| Bloque `limpieza` (texto extraído y limpio)   | —          | ✓             |
| `kpis_inferidos[]`                            | FK parcial | ✓ completo    |
| `unidades_semanticas[]`                       | —          | ✓             |
| Metadatos de filtrado en ChromaDB             | —          | subconjunto   |

> **Regla:** si un dato sirve para operar el sistema (rutas, estados, trazabilidad), vive en PostgreSQL. Si sirve para interpretar el instrumento como conocimiento educativo, vive en el JSON canónico.

---

## 3. Modelo de Datos

### 3.1 Ajustes al esquema SQL existente

```sql
-- ── instrumento_procesado ─────────────────────────────────────────────────────
ALTER TABLE tt_rag.instrumento_procesado
  ADD COLUMN IF NOT EXISTS tipo_instrumento VARCHAR(30) NOT NULL
      DEFAULT 'encuesta'
      CHECK (tipo_instrumento IN ('encuesta', 'entrevista', 'prueba_estandarizada')),
  ADD COLUMN IF NOT EXISTS version        INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS visibilidad    VARCHAR(10) NOT NULL DEFAULT 'privado'
      CHECK (visibilidad IN ('publico', 'privado')),
  ADD COLUMN IF NOT EXISTS creado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN IF NOT EXISTS schema_version VARCHAR(10) DEFAULT '1.0',
  -- Rutas a los artefactos generados por el pipeline de limpieza
  ADD COLUMN IF NOT EXISTS ruta_texto_extraido TEXT,  -- texto crudo extraído del archivo
  ADD COLUMN IF NOT EXISTS ruta_texto_limpio   TEXT,  -- texto limpio producido por el LLM
  -- Trazabilidad de errores del pipeline
  ADD COLUMN IF NOT EXISTS error_detalle TEXT;

-- Eliminar la columna metadatos JSONB de instrumento_procesado:
-- El JSON canónico en disco ES la fuente de verdad semántica.
-- metadatos JSONB en PostgreSQL solo duplicaría ese contenido.
ALTER TABLE tt_rag.instrumento_procesado
  DROP COLUMN IF EXISTS metadatos;

-- ── raw_data ──────────────────────────────────────────────────────────────────
-- hash_md5 debe ser único por (hash_md5, usuario_id), no globalmente.
ALTER TABLE tt_rag.raw_data
  DROP CONSTRAINT IF EXISTS raw_data_hash_md5_key;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_raw_data_hash_usuario
  ON tt_rag.raw_data (hash_md5, usuario_id);

-- ── Tabla de log del pipeline de limpieza ────────────────────────────────────
CREATE TABLE IF NOT EXISTS tt_rag.pipeline_limpieza_log (
    log_id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id       INTEGER NOT NULL
                         REFERENCES tt_rag.instrumento_procesado(instrumento_id)
                         ON DELETE CASCADE,
    iniciado_en          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_en        TIMESTAMP,
    resultado            VARCHAR(20) NOT NULL DEFAULT 'en_proceso'
                         CHECK (resultado IN ('en_proceso', 'exitoso', 'error')),
    extractor_usado      VARCHAR(50),   -- ej. 'pypdf', 'docx', 'text_plain'
    modelo_llm           VARCHAR(100),  -- ej. 'llama3.1:8b'
    prompt_version       VARCHAR(20),
    tokens_entrada       INTEGER,
    tokens_salida        INTEGER,
    latencia_ms          INTEGER,
    error_mensaje        TEXT           -- null si resultado = 'exitoso'
);

CREATE INDEX IF NOT EXISTS idx_limpieza_log_instrumento
  ON tt_rag.pipeline_limpieza_log (instrumento_id);

-- ── Tabla de permisos ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tt_rag.permiso_instrumento (
    permiso_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrumento_id   INTEGER NOT NULL
                     REFERENCES tt_rag.instrumento_procesado(instrumento_id)
                     ON DELETE CASCADE,
    usuario_id       INTEGER NOT NULL
                     REFERENCES tt_rag.usuarios(usuario_id)
                     ON DELETE CASCADE,
    rol              VARCHAR(20) NOT NULL DEFAULT 'lector'
                     CHECK (rol IN ('propietario', 'colaborador', 'lector')),
    otorgado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (instrumento_id, usuario_id)
);

-- ── Índices de búsqueda ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_instrumento_nombre_fts
  ON tt_rag.instrumento_procesado
  USING gin(to_tsvector('spanish', nombre));

CREATE INDEX IF NOT EXISTS idx_instrumento_tipo
  ON tt_rag.instrumento_procesado (tipo_instrumento);

CREATE INDEX IF NOT EXISTS idx_instrumento_visibilidad
  ON tt_rag.instrumento_procesado (visibilidad);

CREATE INDEX IF NOT EXISTS idx_permiso_usuario
  ON tt_rag.permiso_instrumento (usuario_id);
```

### 3.2 Tablas involucradas

| Tabla                      | Rol                                                           |
|----------------------------|---------------------------------------------------------------|
| `instrumento_procesado`    | Registro operativo maestro                                    |
| `raw_data`                 | Historial de archivos físicos por versión                     |
| `permiso_instrumento`      | Control de acceso por usuario e instrumento                   |
| `pipeline_limpieza_log`    | Trazabilidad de cada ejecución del pipeline de limpieza       |
| `usuarios`                 | Propietario y usuarios con acceso                             |
| `documento_vectorizado`    | Chunks en ChromaDB (pipeline RAG, no en este módulo)          |
| `pregunta_kpi`             | Vinculación KPI—pregunta (pipeline de inferencia, no aquí)    |

### 3.3 Máquina de estados del pipeline

```
ingresado ──► limpio ──► estandarizado ──► vectorizado
    │             │              │               │
    └─────────────┴──────────────┴───────────────┴──► error
```

Transiciones válidas:

| Desde         | Hacia            | Quién lo dispara              |
|---------------|------------------|-------------------------------|
| `ingresado`   | `limpio`         | Pipeline de limpieza          |
| `limpio`      | `estandarizado`  | Pipeline de estandarización   |
| `estandarizado` | `vectorizado`  | Pipeline de embeddings        |
| Cualquiera    | `error`          | Cualquier etapa del pipeline  |
| `error`       | `ingresado`      | Administrador (reintento)     |
| `vectorizado` | `ingresado`      | Sistema (nueva versión o edición de metadatos) |

Un cambio de estado solo lo puede aplicar el pipeline (autenticado con token de servicio) o un administrador. Los usuarios regulares **no** pueden modificar el estado directamente.

### 3.4 Diagrama de relaciones

```
usuarios (1) ──< permiso_instrumento (N) >── instrumento_procesado (1)
                                                      │
                                     ┌────────────────┼──────────────────┐
                                     ▼                ▼                  ▼
                               raw_data (N)  pipeline_limpieza_log (N)  documento_vectorizado (N)
```

---

## 4. Modelos SQLAlchemy

Ubicación: `backend/cargar_instru/models.py`

```python
# backend/cargar_instru/models.py
from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, BigInteger,
    Boolean, DateTime, ForeignKey, CheckConstraint,
    UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InstrumentoProcesado(Base):
    __tablename__ = "instrumento_procesado"

    instrumento_id:       Mapped[int]       = mapped_column(Integer, primary_key=True)
    nombre:               Mapped[str]       = mapped_column(String(255), nullable=False)
    tipo_instrumento:     Mapped[str]       = mapped_column(String(30), nullable=False, default="encuesta")
    plataforma:           Mapped[str | None] = mapped_column(String(50))
    ruta_json:            Mapped[str | None] = mapped_column(Text)
    ruta_sav:             Mapped[str | None] = mapped_column(Text)
    ruta_texto_extraido:  Mapped[str | None] = mapped_column(Text)   # pipeline de limpieza
    ruta_texto_limpio:    Mapped[str | None] = mapped_column(Text)   # pipeline de limpieza
    estado:               Mapped[str]       = mapped_column(String(50), nullable=False, default="ingresado")
    visibilidad:          Mapped[str]       = mapped_column(String(10), nullable=False, default="privado")
    version:              Mapped[int]       = mapped_column(Integer, nullable=False, default=1)
    schema_version:       Mapped[str | None] = mapped_column(String(10), default="1.0")
    error_detalle:        Mapped[str | None] = mapped_column(Text)
    fecha_procesamiento:  Mapped[datetime]  = mapped_column(DateTime, nullable=False, server_default=func.now())
    creado_en:            Mapped[datetime]  = mapped_column(DateTime, nullable=False, server_default=func.now())

    raw_versions: Mapped[list["RawData"]] = relationship(
        "RawData", back_populates="instrumento", cascade="all, delete-orphan"
    )
    permisos: Mapped[list["PermisoInstrumento"]] = relationship(
        "PermisoInstrumento", back_populates="instrumento", cascade="all, delete-orphan"
    )
    logs_limpieza: Mapped[list["PipelineLimpiezaLog"]] = relationship(
        "PipelineLimpiezaLog", back_populates="instrumento", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "tipo_instrumento IN ('encuesta','entrevista','prueba_estandarizada')",
            name="ck_tipo_instrumento"
        ),
        CheckConstraint(
            "estado IN ('ingresado','limpio','estandarizado','vectorizado','error')",
            name="ck_estado_instrumento"
        ),
        CheckConstraint(
            "visibilidad IN ('publico','privado')",
            name="ck_visibilidad"
        ),
        {"schema": "tt_rag"},
    )


class RawData(Base):
    __tablename__ = "raw_data"

    raw_data_id:          Mapped[int]       = mapped_column(Integer, primary_key=True)
    instrumento_id:       Mapped[int]       = mapped_column(
        Integer,
        ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"),
        nullable=False
    )
    usuario_id:           Mapped[int]       = mapped_column(
        Integer, ForeignKey("tt_rag.usuarios.usuario_id"), nullable=False
    )
    subido:               Mapped[datetime]  = mapped_column(DateTime, server_default=func.now())
    tipo_de_instrumento:  Mapped[str]       = mapped_column(String(30), nullable=False)
    raw_archivo:          Mapped[str]       = mapped_column(Text, nullable=False)
    nombre_original:      Mapped[str]       = mapped_column(Text, nullable=False)
    tipo_mime:            Mapped[str | None] = mapped_column(String(100))
    tamano_bytes:         Mapped[int]       = mapped_column(BigInteger, nullable=False)
    hash_md5:             Mapped[str | None] = mapped_column(String(32))

    instrumento: Mapped["InstrumentoProcesado"] = relationship(
        "InstrumentoProcesado", back_populates="raw_versions"
    )

    __table_args__ = (
        {"schema": "tt_rag"},
    )


class PermisoInstrumento(Base):
    __tablename__ = "permiso_instrumento"

    permiso_id:     Mapped[int]      = mapped_column(Integer, primary_key=True)
    instrumento_id: Mapped[int]      = mapped_column(
        Integer,
        ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"),
        nullable=False
    )
    usuario_id:     Mapped[int]      = mapped_column(
        Integer, ForeignKey("tt_rag.usuarios.usuario_id", ondelete="CASCADE"), nullable=False
    )
    rol:            Mapped[str]      = mapped_column(String(20), nullable=False, default="lector")
    otorgado_en:    Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    instrumento: Mapped["InstrumentoProcesado"] = relationship(
        "InstrumentoProcesado", back_populates="permisos"
    )

    __table_args__ = (
        UniqueConstraint("instrumento_id", "usuario_id", name="uq_permiso_instrumento_usuario"),
        CheckConstraint(
            "rol IN ('propietario','colaborador','lector')",
            name="ck_rol_permiso"
        ),
        {"schema": "tt_rag"},
    )


class PipelineLimpiezaLog(Base):
    __tablename__ = "pipeline_limpieza_log"

    log_id:           Mapped[int]       = mapped_column(Integer, primary_key=True)
    instrumento_id:   Mapped[int]       = mapped_column(
        Integer,
        ForeignKey("tt_rag.instrumento_procesado.instrumento_id", ondelete="CASCADE"),
        nullable=False
    )
    iniciado_en:      Mapped[datetime]  = mapped_column(DateTime, nullable=False, server_default=func.now())
    finalizado_en:    Mapped[datetime | None] = mapped_column(DateTime)
    resultado:        Mapped[str]       = mapped_column(String(20), nullable=False, default="en_proceso")
    extractor_usado:  Mapped[str | None] = mapped_column(String(50))
    modelo_llm:       Mapped[str | None] = mapped_column(String(100))
    prompt_version:   Mapped[str | None] = mapped_column(String(20))
    tokens_entrada:   Mapped[int | None] = mapped_column(Integer)
    tokens_salida:    Mapped[int | None] = mapped_column(Integer)
    latencia_ms:      Mapped[int | None] = mapped_column(Integer)
    error_mensaje:    Mapped[str | None] = mapped_column(Text)

    instrumento: Mapped["InstrumentoProcesado"] = relationship(
        "InstrumentoProcesado", back_populates="logs_limpieza"
    )

    __table_args__ = (
        CheckConstraint(
            "resultado IN ('en_proceso','exitoso','error')",
            name="ck_resultado_limpieza"
        ),
        {"schema": "tt_rag"},
    )


class Usuario(Base):
    """Modelo de sólo lectura en este módulo."""
    __tablename__ = "usuarios"

    usuario_id:    Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario:       Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en:     Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = ({"schema": "tt_rag"},)
```

---

## 5. Schemas Pydantic

Ubicación: `backend/cargar_instru/schemas.py`

```python
# backend/cargar_instru/schemas.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


TipoInstrumento = Literal["encuesta", "entrevista", "prueba_estandarizada"]
EstadoPipeline  = Literal["ingresado", "limpio", "estandarizado", "vectorizado", "error"]
Visibilidad     = Literal["publico", "privado"]
RolPermiso      = Literal["propietario", "colaborador", "lector"]


# ── Carga inicial del archivo ──────────────────────────────────────────────────
class ArchivoCreate(BaseModel):
    """
    Datos mínimos requeridos al cargar el archivo físico.
    Los metadatos semánticos completos se envían en un paso separado (CU02).
    """
    nombre:           str            = Field(..., min_length=1, max_length=255)
    tipo_instrumento: TipoInstrumento
    visibilidad:      Visibilidad    = Field(default="privado")


# ── Metadatos semánticos (paso independiente) ──────────────────────────────────
class MetadatosContexto(BaseModel):
    """Bloque 'contexto' del JSON canónico."""
    titulo:                  str | None = None
    descripcion:             str | None = None
    objetivo:                str | None = None
    institucion_responsable: str | None = None
    poblacion_alcance:       str | None = None
    periodo_inicio:          str | None = None
    periodo_fin:             str | None = None
    idioma:                  str        = Field(default="es")
    condiciones_uso:         str | None = None
    palabras_clave:          list[str]  = Field(default_factory=list)


class MetadatosDublinCore(BaseModel):
    """Bloque 'dublin_core' según ISO 15836."""
    dc_title:       str | None = None
    dc_creator:     str | None = None
    dc_subject:     list[str]  = Field(default_factory=list)
    dc_description: str | None = None
    dc_publisher:   str | None = None
    dc_contributor: str | None = None
    dc_date:        str | None = None
    dc_type:        str | None = None
    dc_format:      str | None = None
    dc_identifier:  str | None = None   # ej. "IND-ENC-042" — identificador semántico
    dc_source:      str | None = None
    dc_language:    str | None = None
    dc_relation:    str | None = None
    dc_coverage:    str | None = None
    dc_rights:      str | None = None


class MetadatosEspecificoEncuesta(BaseModel):
    n_items_total:         int | None         = None
    escala_respuesta:      str | None         = None
    metodologia_aplicacion: str | None        = None
    tasa_respuesta:        float | None       = None
    dimensiones:           list[dict[str, Any]] = Field(default_factory=list)
    limitaciones:          list[str]          = Field(default_factory=list)


class MetadatosEspecificoEntrevista(BaseModel):
    tipo_entrevista:    str | None              = None
    n_preguntas_guia:   int | None              = None
    duracion_estimada:  str | None              = None
    guion_tematico:     list[dict[str, Any]]    = Field(default_factory=list)
    perfil_entrevistados: str | None            = None
    tecnica_analisis:   str | None              = None
    limitaciones:       list[str]               = Field(default_factory=list)


class MetadatosEspecificoPrueba(BaseModel):
    n_reactivos_total:        int | None           = None
    areas_competencia:        list[dict[str, Any]] = Field(default_factory=list)
    escala_calificacion:      str | None           = None
    normas_referencia:        str | None           = None
    poblacion_normativa:      str | None           = None
    coeficiente_confiabilidad: float | None        = None
    validez:                  str | None           = None
    limitaciones:             list[str]            = Field(default_factory=list)


class MetadatosUpdate(BaseModel):
    """
    Cuerpo del PATCH /instrumentos/{id}/metadatos.
    Todos los bloques son opcionales — solo se actualizan los enviados.
    """
    contexto:    MetadatosContexto    | None = None
    dublin_core: MetadatosDublinCore  | None = None
    especifico:  (MetadatosEspecificoEncuesta |
                  MetadatosEspecificoEntrevista |
                  MetadatosEspecificoPrueba)  | None = None


# ── Respuestas ────────────────────────────────────────────────────────────────
class CargaArchivoResponse(BaseModel):
    instrumento_id: int
    version:        int
    estado:         EstadoPipeline
    visibilidad:    Visibilidad
    mensaje:        str


class InstrumentoResumen(BaseModel):
    instrumento_id:   int
    nombre:           str
    tipo_instrumento: TipoInstrumento
    estado:           EstadoPipeline
    visibilidad:      Visibilidad
    version:          int
    creado_en:        datetime
    propietario:      str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstrumentoDetalle(InstrumentoResumen):
    ruta_json:           str | None
    ruta_sav:            str | None
    schema_version:      str | None
    fecha_procesamiento: datetime
    # Los metadatos semánticos se leen del JSON canónico, no de PostgreSQL.
    # Este campo se popula en el service leyendo el archivo en disco.
    metadatos_canonicos: dict[str, Any] | None = None


class VersionInfo(BaseModel):
    raw_data_id:     int
    nombre_original: str
    tipo_mime:       str | None
    tamano_bytes:    int
    subido:          datetime
    numero_version:  int

    model_config = ConfigDict(from_attributes=True)


class PermisoRead(BaseModel):
    permiso_id:  int
    usuario_id:  int
    usuario:     str
    rol:         RolPermiso
    otorgado_en: datetime

    model_config = ConfigDict(from_attributes=True)


class PermisoCreate(BaseModel):
    usuario_id: int
    rol:        RolPermiso = "lector"


# ── Filtros de listado ────────────────────────────────────────────────────────
class FiltrosInstrumento(BaseModel):
    q:                str | None             = Field(None, description="Texto libre en nombre")
    tipo_instrumento: TipoInstrumento | None = None
    propietario:      str | None             = None
    visibilidad:      Visibilidad | None     = None
    estado:           EstadoPipeline | None  = None
    solo_propios:     bool                   = False
    skip:             int                    = Field(0, ge=0)
    limit:            int                    = Field(20, ge=1, le=100)


# ── Cambio de estado (uso interno del pipeline) ───────────────────────────────
class EstadoUpdate(BaseModel):
    estado: EstadoPipeline


# ── Cambio de visibilidad ─────────────────────────────────────────────────────
class VisibilidadUpdate(BaseModel):
    visibilidad: Visibilidad
```

---

## 6. Endpoints REST

Prefijo base: `/route_instru`  
Todos los endpoints requieren JWT válido. Los marcados con `[pipeline]` aceptan token de servicio además de usuario.

| Método | Ruta                                          | Descripción                                          | Quién puede         |
|--------|-----------------------------------------------|------------------------------------------------------|---------------------|
| POST   | `/instrumentos`                               | Cargar archivo + crear registro                      | Usuario autenticado |
| GET    | `/instrumentos`                               | Listar instrumentos accesibles (con filtros)         | Usuario autenticado |
| GET    | `/instrumentos/propios`                       | Listar solo los propios                              | Usuario autenticado |
| GET    | `/instrumentos/{id}`                          | Detalle de un instrumento                            | Con acceso          |
| PATCH  | `/instrumentos/{id}/metadatos`                | Actualizar metadatos semánticos                      | Propietario         |
| PATCH  | `/instrumentos/{id}/visibilidad`              | Cambiar visibilidad pública/privada                  | Propietario         |
| PATCH  | `/instrumentos/{id}/estado`                   | Cambiar estado del pipeline                          | Pipeline [pipeline] |
| GET    | `/instrumentos/{id}/descargar`                | Descargar archivo de la versión actual               | Con acceso          |
| DELETE | `/instrumentos/{id}`                          | Eliminar instrumento                                 | Propietario         |
| POST   | `/instrumentos/{id}/versiones`                | Cargar nueva versión del archivo                     | Propietario         |
| GET    | `/instrumentos/{id}/versiones`                | Listar historial de versiones                        | Con acceso          |
| GET    | `/instrumentos/{id}/permisos`                 | Listar permisos del instrumento                      | Propietario         |
| POST   | `/instrumentos/{id}/permisos`                 | Otorgar acceso a otro usuario                        | Propietario         |
| DELETE | `/instrumentos/{id}/permisos/{permiso_id}`    | Revocar acceso a un usuario                          | Propietario         |

### Detalles por endpoint

#### POST `/instrumentos`
- **Content-Type:** `multipart/form-data`
- **Campos:**
  - `archivo`: `UploadFile` (requerido)
  - `nombre`: `str`
  - `tipo_instrumento`: `encuesta | entrevista | prueba_estandarizada`
  - `visibilidad`: `publico | privado` (default: `privado`)
- **Respuesta:** `201 Created` → `CargaArchivoResponse`
- **Errores:** `409 Conflict` (hash duplicado del usuario), `422`

#### PATCH `/instrumentos/{id}/metadatos`
- **Content-Type:** `application/json`
- **Body:** `MetadatosUpdate` (todos los campos opcionales)
- **Comportamiento:** actualiza el JSON canónico en disco. Solo reescribe los bloques enviados. No toca PostgreSQL salvo el campo `nombre` si `contexto.titulo` cambia.
- **Respuesta:** `200 OK` → `InstrumentoDetalle`
- **Errores:** `403 Forbidden`, `404 Not Found`

#### PATCH `/instrumentos/{id}/visibilidad`
- **Body:** `VisibilidadUpdate`
- **Respuesta:** `200 OK` → `{"instrumento_id": int, "visibilidad": str}`
- **Errores:** `403`, `404`

#### PATCH `/instrumentos/{id}/estado`
- **Requiere:** token de servicio (pipeline) o rol administrador.
- **Body:** `EstadoUpdate`
- **Validación:** la transición debe ser válida según la máquina de estados (§3.3).
- **Respuesta:** `200 OK` → `{"instrumento_id": int, "estado": str}`
- **Efecto secundario:** si `estado = 'estandarizado'` y `tipo = 'encuesta'`, se dispara `SavService.generar_sav()` en background.
- **Errores:** `403`, `404`, `422` (transición inválida)

#### GET `/instrumentos/{id}/descargar`
- Devuelve `FileResponse` con el archivo crudo de la versión más reciente.
- **Header:** `Content-Disposition: attachment; filename="{nombre_original}"`
- **Errores:** `403 Forbidden` (instrumento privado sin permiso), `404`

#### GET `/instrumentos/{id}`
- El campo `metadatos_canonicos` se popula leyendo `storage/json/{id}.json` desde disco. Si el archivo no existe aún, el campo es `null`.
- **Errores:** `403` (privado sin permiso), `404`

---

## 7. Modelo de Permisos

### Roles

| Rol            | Puede leer | Puede descargar | Puede editar metadatos | Puede subir versión | Puede eliminar | Puede gestionar permisos |
|----------------|:----------:|:---------------:|:----------------------:|:-------------------:|:--------------:|:------------------------:|
| `propietario`  | ✓          | ✓               | ✓                      | ✓                   | ✓              | ✓                        |
| `colaborador`  | ✓          | ✓               | ✓                      | ✓                   | —              | —                        |
| `lector`       | ✓          | ✓               | —                      | —                   | —              | —                        |
| Sin permiso + público | ✓   | ✓               | —                      | —                   | —              | —                        |
| Sin permiso + privado | —   | —               | —                      | —                   | —              | —                        |

### Asignación automática de permisos

Al crear un instrumento (`POST /instrumentos`), el sistema automáticamente crea un registro en `permiso_instrumento` con `rol = 'propietario'` para el `usuario_id` del solicitante. Este registro nunca puede ser eliminado manualmente — solo se elimina en cascada si se borra el instrumento.

### Lógica de acceso

```python
def puede_acceder(instrumento, usuario_id, db) -> bool:
    """
    Un usuario puede acceder a un instrumento si:
    - el instrumento es público, O
    - tiene un registro en permiso_instrumento para ese instrumento.
    """
    if instrumento.visibilidad == "publico":
        return True
    return db.query(PermisoInstrumento).filter(
        PermisoInstrumento.instrumento_id == instrumento.instrumento_id,
        PermisoInstrumento.usuario_id == usuario_id
    ).first() is not None


def obtener_rol(instrumento_id, usuario_id, db) -> RolPermiso | None:
    permiso = db.query(PermisoInstrumento).filter(
        PermisoInstrumento.instrumento_id == instrumento_id,
        PermisoInstrumento.usuario_id == usuario_id
    ).first()
    return permiso.rol if permiso else None
```

### Filtrado en listados

El endpoint `GET /instrumentos` devuelve únicamente instrumentos accesibles para el usuario autenticado:

```sql
SELECT ip.*
FROM tt_rag.instrumento_procesado ip
WHERE
  ip.visibilidad = 'publico'
  OR EXISTS (
    SELECT 1 FROM tt_rag.permiso_instrumento pi
    WHERE pi.instrumento_id = ip.instrumento_id
      AND pi.usuario_id = :usuario_id
  )
```

---

## 8. Services

Ubicación: `backend/cargar_instru/services.py`

### 8.1 `InstrumentoService`

```
cargar_archivo(db, usuario_id, nombre, tipo, visibilidad, archivo)
    → CargaArchivoResponse
    Orquesta: calcular_hash → verificar_duplicado → guardar_archivo_crudo
              → crear_instrumento_procesado → crear_raw_data
              → crear_permiso_propietario
              → inicializar_json_canonico (background)

actualizar_metadatos(db, instrumento_id, usuario_id, metadatos_update)
    → InstrumentoDetalle
    Verifica rol >= colaborador. Actualiza JSON canónico en disco (merge parcial).
    Si estado == 'vectorizado', resetea a 'ingresado'.

obtener_instrumento(db, instrumento_id, usuario_id)
    → InstrumentoDetalle | None
    Verifica acceso. Lee el JSON canónico del disco y lo adjunta.

listar_instrumentos(db, usuario_id, filtros)
    → list[InstrumentoResumen]
    Aplica filtro de visibilidad/permiso + filtros adicionales.

obtener_ruta_descarga(db, instrumento_id, usuario_id)
    → tuple[Path, str]   # (ruta_absoluta, nombre_original)
    Verifica acceso. Devuelve la ruta del raw_data más reciente.

eliminar_instrumento(db, instrumento_id, usuario_id)
    → None
    Verifica rol == propietario. Elimina archivos en disco. Elimina registro.

cargar_nueva_version(db, instrumento_id, usuario_id, archivo)
    → CargaArchivoResponse
    Verifica rol >= colaborador. No sobreescribe el JSON canónico.

cambiar_visibilidad(db, instrumento_id, usuario_id, visibilidad)
    → dict
    Verifica rol == propietario.

cambiar_estado(db, instrumento_id, nuevo_estado, solicitante_es_pipeline)
    → dict
    Valida transición. Si estado → 'estandarizado' y tipo == 'encuesta',
    dispara SavService.generar_sav() en background.

listar_versiones(db, instrumento_id, usuario_id)
    → list[VersionInfo]
```

### 8.2 `ArchivoService`

```
guardar_archivo(contenido: bytes, destino_dir: Path, nombre_unico: str)
    → Path

calcular_hash_md5(contenido: bytes) → str

eliminar_archivo(ruta: Path) → None
    # No lanza excepción si el archivo no existe.
```

### 8.3 `JsonCanonicoService`

```
inicializar_json(instrumento_id, nombre, tipo)
    → Path
    Crea el JSON semilla con bloques vacíos:
    contexto, dublin_core, especifico, kpis_inferidos=[], unidades_semanticas=[].

actualizar_bloques(instrumento_id, metadatos_update: MetadatosUpdate)
    → Path
    Lee el JSON existente, hace merge parcial de los bloques recibidos,
    conserva kpis_inferidos y unidades_semanticas intactos, escribe de vuelta.

leer_json(instrumento_id) → dict | None
    Lee y parsea el JSON canónico desde disco.
    Devuelve None si el archivo no existe.

exportar_contexto_para_chroma(instrumento_id) -> dict
    Extrae el subconjunto de campos del JSON canónico que van como
    metadatos en ChromaDB (ver §11.2).
```

### 8.4 `SavService`

```
generar_sav(db, instrumento_id) -> Path
    Lee el bloque especifico.dimensiones del JSON canónico.
    Construye DataFrame con pandas.
    Escribe storage/sav/{instrumento_id}.sav con pyreadstat.
    Actualiza instrumento_procesado.ruta_sav en PostgreSQL.
    Solo ejecutable cuando estado == 'estandarizado' y tipo == 'encuesta'.
```

### 8.5 `PermisoService`

```
crear_permiso_propietario(db, instrumento_id, usuario_id) -> PermisoInstrumento

otorgar_permiso(db, instrumento_id, solicitante_id, nuevo_usuario_id, rol)
    → PermisoInstrumento
    Solo el propietario puede otorgar permisos.
    No permite crear un segundo propietario.

revocar_permiso(db, instrumento_id, solicitante_id, permiso_id) -> None
    No permite revocar al propietario.

listar_permisos(db, instrumento_id, solicitante_id) -> list[PermisoRead]
```

---

## 9. Flujo de Almacenamiento de Archivos

```
POST /instrumentos
        │
        ▼
1. Leer UploadFile completo en bytes (en memoria)
        │
        ▼
2. Calcular hash_md5 del contenido en bytes
        │
        ▼
3. Verificar duplicado: ¿existe raw_data con (hash_md5, usuario_id)?
   ──► sí: 409 Conflict
        │
        ▼
4. INSERT instrumento_procesado
   estado='ingresado', visibilidad=recibido, version=1
        │
        ▼
5. Generar nombre único de archivo:
   {instrumento_id}_{timestamp_unix}_{uuid4[:8]}{extension_original}
        │
        ▼
6. Escribir bytes en storage/raw/{nombre_unico}
        │
        ▼
7. INSERT raw_data (instrumento_id, usuario_id, hash_md5, ruta, mime, tamaño)
        │
        ▼
8. INSERT permiso_instrumento (instrumento_id, usuario_id, rol='propietario')
        │
        ▼
9. BackgroundTask: JsonCanonicoService.inicializar_json(instrumento_id, nombre, tipo)
        │
        ▼
10. Responder 201 → CargaArchivoResponse
```

**Directorios de almacenamiento:**

| Artefacto          | Directorio              | Config key   | Cuándo se crea              |
|--------------------|-------------------------|--------------|-----------------------------|
| Archivo crudo      | `storage/raw/`          | `RAW_PATH`   | Al cargar (CU01, CU07)      |
| JSON canónico      | `storage/json/`         | `JSON_PATH`  | Al cargar (background)      |
| Archivo `.sav`     | `storage/sav/`          | `SAV_PATH`   | Post-estandarización (CU11) |
| Archivos temporales | `storage/temp/`        | `TEMP_PATH`  | Solo durante procesamiento  |

---

## 10. Flujo del JSON Canónico

### 10.1 Inicialización (al cargar archivo)

```python
# Estructura semilla que se escribe en storage/json/{instrumento_id}.json
{
  "_meta": {
    "instrumento_id": instrumento_id,
    "schema_version": "1.0",
    "creado_en": "ISO-8601",
    "ultima_actualizacion": "ISO-8601",
    "tipo_instrumento": tipo
  },
  "contexto": {
    "titulo": nombre,       # único campo pre-poblado con el nombre del instrumento
    "descripcion": null,
    "objetivo": null,
    "institucion_responsable": null,
    "poblacion_alcance": null,
    "periodo_inicio": null,
    "periodo_fin": null,
    "idioma": "es",
    "condiciones_uso": null,
    "palabras_clave": []
  },
  "dublin_core": { ... todos null ... },
  "especifico": {},          # estructura vacía según tipo_instrumento
  "kpis_inferidos": [],      # se llena en pipeline de inferencia KPI
  "unidades_semanticas": []  # se llena en pipeline de chunking IEC
}
```

### 10.2 Actualización de metadatos (PATCH /metadatos)

```
PATCH /instrumentos/{id}/metadatos
        │
        ▼
1. Verificar rol >= colaborador
        │
        ▼
2. Leer JSON canónico actual desde disco
        │
        ▼
3. Merge parcial por bloques:
   - Si metadatos_update.contexto recibido → reemplazar bloque "contexto"
   - Si metadatos_update.dublin_core recibido → reemplazar bloque "dublin_core"
   - Si metadatos_update.especifico recibido → reemplazar bloque "especifico"
   - Bloques kpis_inferidos y unidades_semanticas → NUNCA tocar desde este endpoint
        │
        ▼
4. Actualizar _meta.ultima_actualizacion
        │
        ▼
5. Escribir JSON actualizado en disco (sobrescritura atómica: write temp → rename)
        │
        ▼
6. Si contexto.titulo cambió: UPDATE instrumento_procesado SET nombre = nuevo_titulo
        │
        ▼
7. Si estado == 'vectorizado': UPDATE instrumento_procesado SET estado = 'ingresado'
        │
        ▼
8. Responder 200 → InstrumentoDetalle (con metadatos_canonicos leído del JSON)
```

### 10.3 Escritura atómica

Para evitar JSON corrompidos ante fallos:

```python
import tempfile, os, shutil

def escribir_json_atomico(ruta: Path, datos: dict) -> None:
    directorio = ruta.parent
    with tempfile.NamedTemporaryFile(
        mode="w", dir=directorio, suffix=".tmp", delete=False, encoding="utf-8"
    ) as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        nombre_temp = f.name
    os.replace(nombre_temp, ruta)   # atómico en sistemas POSIX y Windows
```

---

## 11. Generación del archivo `.sav`

El `.sav` es un artefacto del pipeline de estandarización, **no** de la ingesta.

### Condiciones de generación

- `instrumento_procesado.tipo_instrumento == 'encuesta'`
- `instrumento_procesado.estado == 'estandarizado'`
- El bloque `especifico.dimensiones` del JSON canónico debe estar poblado.

### Flujo

```
Pipeline dispara PATCH /instrumentos/{id}/estado con estado='estandarizado'
        │
        ▼
El endpoint valida la transición y detecta condición SAV
        │
        ▼
BackgroundTask: SavService.generar_sav(db, instrumento_id)
        │
        ▼
1. JsonCanonicoService.leer_json(instrumento_id)
        │
        ▼
2. Extraer especifico.dimensiones[]
   Para cada dimensión: nombre, items_representativos, n_items
        │
        ▼
3. Construir DataFrame con pandas:
   columnas = ítems del instrumento
   metadatos de columna = etiquetas de variable (variable labels)
        │
        ▼
4. pyreadstat.write_sav(df, ruta_sav, variable_value_labels=etiquetas)
        │
        ▼
5. UPDATE instrumento_procesado SET ruta_sav = ruta_relativa
```

---

## 12. Estrategia de Versionado

### Modelo

```
instrumento_procesado.version    → versión actual (entero, inicia en 1)
raw_data (N registros)           → un registro por versión del archivo
storage/json/{id}.json           → único archivo, sobreescrito en cada PATCH /metadatos
storage/raw/{nombre_unico}       → un archivo distinto por versión
```

### Invariantes

1. `raw_data` nunca se borra al subir nueva versión. Es el historial inmutable.
2. El JSON canónico no se sobreescribe al subir nueva versión de archivo — los metadatos semánticos se preservan.
3. Subir nueva versión del archivo resetea `estado → 'ingresado'` y elimina los chunks de ChromaDB del instrumento si los había (responsabilidad del pipeline, notificado por el cambio de estado).
4. Editar metadatos no cambia el número de versión del archivo.

### Tabla de versionado

| Acción del usuario              | `version` | `raw_data` | JSON canónico    | `estado`      |
|---------------------------------|:---------:|:----------:|:----------------:|:-------------:|
| Cargar archivo inicial          | 1         | +1 nuevo   | inicializado     | `ingresado`   |
| PATCH /metadatos                | sin cambio | sin cambio | actualizado      | si era `vectorizado` → `ingresado`; si no, sin cambio |
| POST /versiones (nuevo archivo) | +1         | +1 nuevo   | sin cambio       | `ingresado`   |
| PATCH /estado (pipeline)        | sin cambio | sin cambio | sin cambio       | nuevo estado  |

---

## 13. Integración con el pipeline RAG

Este módulo es la **puerta de entrada** al pipeline. Define el contrato que los módulos posteriores deben respetar.

### 13.1 Posición en el flujo general

```
[cargar_instru]        [pipeline_limpieza]      [pipeline_kpi]        [pipeline_vectorizacion]
       │                       │                      │                        │
 POST /instrumentos     Polling estado               Lee JSON canónico      Lee JSON canónico
 PATCH /metadatos       = 'ingresado'               Escribe kpis_inferidos  Escribe unidades_semanticas
       │                       │                     en JSON canónico        Crea documento_vectorizado
 JSON semilla creado    Extrae texto del             PATCH /estado           en ChromaDB
 estado='ingresado'     archivo crudo                estado→'estandarizado'  PATCH /estado
                               │                     Dispara generación SAV  estado→'vectorizado'
                        LLM limpia y
                        estructura texto
                               │
                        Escribe bloque
                        'limpieza' en JSON
                               │
                        PATCH /estado
                        estado→'limpio'
```

### 13.2 Contrato: campos que el pipeline escribe en el JSON canónico

Los pipelines posteriores **no** llaman a `PATCH /metadatos` (ese endpoint es para usuarios). Acceden directamente al JSON canónico en disco y lo actualizan via `JsonCanonicoService`.

| Pipeline            | Campos que escribe                                              | Campos que debe preservar             |
|---------------------|-----------------------------------------------------------------|---------------------------------------|
| Limpieza            | `limpieza{}` completo, `_meta.ultima_actualizacion`             | `contexto`, `dublin_core`, `especifico`, `kpis_inferidos`, `unidades_semanticas` |
| Inferencia KPI      | `kpis_inferidos[]` completo                                     | `contexto`, `dublin_core`, `especifico`, `limpieza`, `unidades_semanticas` |
| Chunking IEC        | `unidades_semanticas[]` completo                                | `contexto`, `dublin_core`, `especifico`, `limpieza`, `kpis_inferidos`      |
| Estandarización SAV | Solo escribe `ruta_sav` en PostgreSQL, no toca el JSON          | —                                     |

### 13.3 Campos del JSON canónico que van a ChromaDB

Al vectorizar, el pipeline de embeddings extrae los campos de `contexto` como metadatos en ChromaDB. La tabla siguiente muestra qué va a cada capa:

| Campo del JSON canónico              | Metadato ChromaDB        | Contenido embebido |
|--------------------------------------|--------------------------|--------------------|
| `contexto.titulo`                    | `titulo`                 | ✓ (en ancla)       |
| `contexto.tipo_instrumento`          | `tipo_instrumento`       | ✓ (en ancla)       |
| `contexto.institucion_responsable`   | `institucion`            | ✓ (en ancla)       |
| `contexto.periodo_inicio/fin`        | `periodo`                | ✓ (en ancla)       |
| `contexto.poblacion_alcance`         | `poblacion`              | ✓ (en ancla)       |
| `contexto.idioma`                    | `idioma`                 | —                  |
| `dublin_core.dc_identifier`          | `codigo_instrumento`     | —                  |
| `kpis_inferidos[].kpi_id`            | `kpis_ids` (JSON string) | ✓ (en narrativa)   |
| `kpis_inferidos[].nombre_kpi`        | `kpis_nombres`           | ✓ (en narrativa)   |
| `instrumento_id` (de PostgreSQL)     | `instrumento_id`         | —                  |
| `unidades_semanticas[].tipo`         | `tipo_chunk`             | —                  |
| `unidades_semanticas[].id_chunk`     | —                        | —                  |
| `unidades_semanticas[].chunk_padre`  | `chunk_padre`            | —                  |

### 13.4 Eventos que dispara este módulo hacia el pipeline

| Evento en este módulo                                  | Qué debe hacer el pipeline             |
|--------------------------------------------------------|----------------------------------------|
| `estado` = `ingresado` (nuevo instrumento o reintento) | Encolar para pipeline de limpieza      |
| `estado` cambia a `estandarizado` (encuesta)           | Generar SAV                            |
| `estado` cambia a `vectorizado` → `ingresado` (edición)| Invalidar chunks en ChromaDB           |

En esta versión los eventos se detectan por polling del estado en PostgreSQL. En versiones futuras se puede reemplazar por un message broker (Redis Pub/Sub, RabbitMQ).

### 13.5 Acceso de los pipelines a la API

Los pipelines se autentican con un token de servicio (mismo mecanismo JWT, rol especial `pipeline`). Solo tienen acceso a:

- `PATCH /instrumentos/{id}/estado` — avanzar el estado.
- Lectura/escritura directa del JSON canónico en disco via `JsonCanonicoService`.

Los pipelines **no** usan endpoints de usuario (no crean instrumentos, no modifican metadatos de usuario, no gestionan permisos).

---

## 14. Estructura de Directorios del Módulo

```
backend/
├── cargar_instru/
│   ├── __init__.py
│   ├── models.py                  ← Modelos SQLAlchemy (incluye PipelineLimpiezaLog)
│   ├── schemas.py                 ← Schemas Pydantic
│   ├── services.py                ← Lógica de negocio de gestión de instrumentos
│   ├── routers_cargar_instru.py   ← Endpoints FastAPI de usuario
│   └── dependencies.py            ← get_current_user, verificar_rol, puede_acceder
└── pipeline_limpieza/
    ├── __init__.py
    ├── orchestrator.py            ← Punto de entrada del pipeline (polling + ejecución)
    ├── extractor.py               ← Extracción de texto por tipo MIME
    ├── llm_cleaner.py             ← Limpieza y estructuración con Ollama
    ├── json_writer.py             ← Escritura del bloque 'limpieza' en el JSON canónico
    └── prompts/
        └── limpieza_v1.txt        ← Prompt de limpieza versionado
```

---

## 15. Dependencias Requeridas

| Biblioteca           | Uso                                                    | En requirements.txt |
|----------------------|--------------------------------------------------------|:-------------------:|
| `fastapi`            | Framework, routing, UploadFile, BackgroundTasks        | ✓                   |
| `sqlalchemy`         | ORM, sesiones, queries                                 | ✓                   |
| `pydantic[v2]`       | Schemas                                                | ✓                   |
| `python-jose`        | JWT                                                    | ✓                   |
| `python-multipart`   | multipart/form-data                                    | ✓                   |
| `pandas`             | Construcción del DataFrame para el `.sav`              | ✓                   |
| `langchain-ollama`   | Cliente LLM para el pipeline de limpieza               | ✓                   |
| `pypdf`              | Extracción de texto de archivos PDF                    | ✓                   |
| `python-docx`        | Extracción de texto de archivos `.docx`                | **falta agregar**   |
| `openpyxl`           | Extracción de texto de archivos `.xlsx`                | ✓                   |
| `pyreadstat>=1.2.0`  | Escritura de archivos `.sav` (SPSS)                    | **falta agregar**   |

> Agregar a `requirements.txt`: `python-docx>=1.1.0` y `pyreadstat>=1.2.0`.

---

## 16. Notas de Implementación — Módulo de Gestión

> El contenido detallado del pipeline de limpieza está en §17.

---

## 17. Pipeline de Limpieza Guiado por LLM

### 17.1 Responsabilidad y alcance

El pipeline de limpieza es la **primera etapa automática** del procesamiento de instrumentos. Actúa de forma independiente a los endpoints de usuario — no es invocado por ninguna petición HTTP de usuario, no modifica permisos, y no expone endpoints propios. Es un proceso de sistema que observa el estado de los instrumentos y actúa cuando corresponde.

**Responsabilidades:**
1. Detectar instrumentos en estado `ingresado` pendientes de procesar.
2. Extraer el contenido textual del archivo crudo según su tipo MIME.
3. Limpiar y estructurar el texto extraído usando un LLM local (Ollama).
4. Escribir los resultados en el bloque `limpieza` del JSON canónico.
5. Registrar trazabilidad completa en `pipeline_limpieza_log`.
6. Avanzar el instrumento a estado `limpio` o marcarlo como `error`.

**No es responsabilidad de este pipeline:**
- Inferir KPIs (pipeline de inferencia KPI, etapa posterior).
- Generar chunks semánticos (pipeline de chunking IEC, etapa posterior).
- Generar el `.sav` (pipeline de estandarización, etapa posterior).
- Modificar los bloques `contexto`, `dublin_core`, `especifico`, `kpis_inferidos` ni `unidades_semanticas` del JSON canónico.

---

### 17.2 Disparador: integración con la máquina de estados

El pipeline opera mediante **polling activo** sobre PostgreSQL. No requiere infraestructura de mensajería adicional.

```python
# pipeline_limpieza/orchestrator.py — bucle principal

async def run_polling_loop(intervalo_segundos: int = 30):
    """
    Cada `intervalo_segundos`, busca instrumentos en estado 'ingresado'
    que no tengan un log activo con resultado='en_proceso'.
    """
    while True:
        with SessionLocal() as db:
            pendientes = (
                db.query(InstrumentoProcesado)
                .filter(InstrumentoProcesado.estado == "ingresado")
                .filter(
                    ~db.query(PipelineLimpiezaLog)
                    .filter(
                        PipelineLimpiezaLog.instrumento_id == InstrumentoProcesado.instrumento_id,
                        PipelineLimpiezaLog.resultado == "en_proceso"
                    )
                    .exists()
                )
                .limit(10)   # procesar en lotes pequeños
                .all()
            )
            for instrumento in pendientes:
                await procesar_instrumento(db, instrumento)
        await asyncio.sleep(intervalo_segundos)
```

**Condición de entrada al pipeline:**

| Condición                                | Comportamiento                                  |
|------------------------------------------|-------------------------------------------------|
| `estado == 'ingresado'`                  | Encola para procesamiento                       |
| Ya existe log con `resultado='en_proceso'` | Omite (evita procesamiento paralelo)          |
| `estado != 'ingresado'`                  | Ignora                                          |

La transición `ingresado → limpio` (o `ingresado → error`) es la **única transición de estado** que hace este pipeline. Solo ejecuta `cambiar_estado(instrumento_id, 'limpio')` al concluir exitosamente.

---

### 17.3 Extracción de texto por tipo MIME

Ubicación: `pipeline_limpieza/extractor.py`

El extractor es una función de despacho que selecciona la estrategia correcta según el `tipo_mime` del archivo en `raw_data`.

```python
ESTRATEGIAS_EXTRACCION: dict[str, Callable] = {
    "application/pdf":                          extraer_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extraer_docx,
    "application/msword":                       extraer_docx,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":       extraer_xlsx,
    "application/vnd.ms-excel":                 extraer_xlsx,
    "text/plain":                               extraer_texto_plano,
    "text/csv":                                 extraer_csv,
}

def extraer_texto(ruta_archivo: Path, tipo_mime: str) -> str:
    estrategia = ESTRATEGIAS_EXTRACCION.get(tipo_mime, extraer_fallback)
    return estrategia(ruta_archivo)
```

**Estrategias de extracción:**

| MIME / Extensión            | Biblioteca        | Estrategia                                                  |
|-----------------------------|-------------------|-------------------------------------------------------------|
| `application/pdf`           | `pypdf`           | Extrae página por página, concatena con separador `\n\n`    |
| `.docx`                     | `python-docx`     | Extrae párrafos en orden, conserva estructura de títulos    |
| `.xlsx`                     | `openpyxl`        | Extrae celda por celda, hoja por hoja, separadas por `\n`   |
| `text/plain`, `text/csv`    | built-in          | Lectura directa con encoding UTF-8 (fallback a latin-1)     |
| Desconocido / binario       | fallback          | Intenta decodificación UTF-8; si falla, registra advertencia y usa texto vacío |

El texto extraído **no se modifica** en esta etapa: se conserva tal cual, incluyendo caracteres especiales, tabulaciones y saltos de línea. La limpieza es responsabilidad del LLM en la etapa siguiente.

**Artefacto generado:**  
`storage/temp/{instrumento_id}_extraido.txt` — texto crudo extraído, guardado antes de llamar al LLM. Si el pipeline falla en la etapa LLM, el texto extraído ya está disponible para diagnóstico.

---

### 17.4 Limpieza y estructuración con LLM

Ubicación: `pipeline_limpieza/llm_cleaner.py`

#### Prompt de limpieza

El prompt se almacena como archivo versionado en `pipeline_limpieza/prompts/limpieza_v1.txt` y se referencia desde `prompt.prompt_id` en la tabla `prompt` de PostgreSQL (`tipo = 'metadatos'`).

```
SISTEMA: Eres un asistente especializado en instrumentos de investigación educativa.
Tu tarea es limpiar y estructurar el texto de un instrumento de investigación.

INSTRUCCIONES:
1. Elimina encabezados de página, números de página, marcas de agua y artefactos de extracción.
2. Normaliza espacios, guiones y comillas tipográficas.
3. Conserva la estructura original del instrumento: secciones, preguntas numeradas, opciones de respuesta.
4. No agregues, inventes ni resumas ningún contenido. Solo limpia y organiza lo que ya existe.
5. Identifica y conserva: el título del instrumento, las instrucciones al respondiente,
   las secciones o dimensiones, las preguntas o ítems con sus códigos, y las opciones de respuesta.
6. Si el texto contiene tablas, conviértelas a formato legible en texto plano.
7. Devuelve exclusivamente el texto limpio. No incluyas explicaciones ni comentarios propios.

TEXTO A LIMPIAR:
{texto_extraido}
```

#### Llamada al LLM (Ollama)

```python
# pipeline_limpieza/llm_cleaner.py

from langchain_ollama import OllamaLLM
from app.core.config import settings


def limpiar_con_llm(texto_extraido: str, prompt_template: str) -> tuple[str, dict]:
    """
    Retorna (texto_limpio, metricas).
    metricas incluye: modelo, tokens_entrada, tokens_salida, latencia_ms.
    """
    llm = OllamaLLM(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_HOST,
        temperature=0.0,        # determinista: limpieza, no generación creativa
        num_predict=8192,       # límite de tokens de salida
    )

    prompt = prompt_template.replace("{texto_extraido}", texto_extraido[:12000])
    # Truncado a 12000 chars para no exceder el contexto del modelo base.
    # Si el texto es mayor, se segmenta en ventanas solapadas (ver §17.5).

    inicio = time.monotonic()
    texto_limpio = llm.invoke(prompt)
    latencia_ms = int((time.monotonic() - inicio) * 1000)

    return texto_limpio, {
        "modelo_llm": settings.OLLAMA_MODEL,
        "tokens_entrada": len(prompt.split()),    # aproximación
        "tokens_salida": len(texto_limpio.split()),
        "latencia_ms": latencia_ms,
    }
```

#### Manejo de textos largos (segmentación)

Si `len(texto_extraido) > 12000` caracteres:

1. Dividir el texto en segmentos de 10000 caracteres con solapamiento de 500 caracteres.
2. Llamar al LLM para cada segmento con el mismo prompt.
3. Concatenar los resultados con separador `\n\n--- continuación ---\n\n`.
4. El texto final concatenado es el `texto_limpio`.

El umbral y el solapamiento son configurables en `settings` (`LIMPIEZA_VENTANA_CHARS`, `LIMPIEZA_SOLAPE_CHARS`).

---

### 17.5 Artefactos generados

| Artefacto                                  | Ruta                                          | Cuándo se crea              |
|--------------------------------------------|-----------------------------------------------|-----------------------------|
| Texto extraído (crudo)                     | `storage/temp/{instrumento_id}_extraido.txt`  | Después de la extracción    |
| Texto limpio (LLM)                         | `storage/temp/{instrumento_id}_limpio.txt`    | Después de la limpieza LLM  |
| JSON canónico actualizado (bloque limpieza)| `storage/json/{instrumento_id}.json`          | Después de validación       |

Los archivos en `storage/temp/` son temporales. Después de que el pipeline escribe exitosamente el JSON canónico y avanza el estado a `limpio`, los archivos temporales **se eliminan**. Si el pipeline falla, los archivos se conservan en `temp/` para diagnóstico hasta que se resuelva el error.

> `ruta_texto_extraido` y `ruta_texto_limpio` en `instrumento_procesado` solo se populan temporalmente durante el estado de error, para facilitar diagnóstico. Una vez que el instrumento llega a `limpio`, estas rutas apuntan a `null` (los archivos fueron eliminados de `temp/`).

---

### 17.6 Estructura del bloque `limpieza` en el JSON canónico

El pipeline de limpieza escribe un bloque nuevo en el JSON canónico:

```json
"limpieza": {
  "fecha_limpieza":      "2026-08-15T14:32:00Z",
  "modelo_llm":          "llama3.1:8b",
  "prompt_version":      "v1",
  "extractor_usado":     "pypdf",
  "texto_extraido_hash": "a3f8c2...",   // MD5 del texto extraído (trazabilidad)
  "segmentos":           1,             // número de segmentos si el texto fue dividido
  "texto_limpio":        "Encuesta de Satisfacción Estudiantil\n\nInstrucciones: ..."
}
```

**Reglas del bloque `limpieza`:**

1. `texto_limpio` es el único campo que alimenta los pipelines posteriores (inferencia KPI, chunking IEC). Los pipelines no leen el archivo crudo ni el texto extraído — solo `texto_limpio`.
2. `texto_extraido_hash` garantiza trazabilidad: permite verificar que el texto limpio corresponde a una versión específica del archivo crudo, incluso si el archivo temporal ya fue eliminado.
3. El bloque `limpieza` no se incluye en el embedding ni en los metadatos de ChromaDB. Es exclusivamente operativo.
4. Si el instrumento recibe una nueva versión del archivo (`POST /versiones`), el bloque `limpieza` se **elimina** del JSON canónico al resetear el estado a `ingresado`. Se regenera en el siguiente ciclo del pipeline.

---

### 17.7 Flujo completo del pipeline de limpieza

```
Polling detecta instrumento en estado 'ingresado'
        │
        ▼
1. INSERT pipeline_limpieza_log (resultado='en_proceso')
        │
        ▼
2. Obtener ruta del archivo crudo desde raw_data
   (el registro con mayor raw_data_id para ese instrumento_id)
        │
        ▼
3. TextoExtractor.extraer_texto(ruta, tipo_mime)
   ──► Texto extraído en memoria
        │
   ┌── si falla ─────────────────────────────────────────────────────────────┐
   │   UPDATE pipeline_limpieza_log SET resultado='error', error_mensaje=... │
   │   UPDATE instrumento_procesado SET estado='error', error_detalle=...    │
   │   Guardar texto extraído parcial en storage/temp/ si existe             │
   └─────────────────────────────────────────────────────────────────────────┘
        │
        ▼
4. Escribir storage/temp/{instrumento_id}_extraido.txt (texto crudo)
        │
        ▼
5. Cargar prompt activo desde prompt WHERE tipo='metadatos' AND activo=TRUE
        │
        ▼
6. LLMCleaner.limpiar_con_llm(texto_extraido, prompt)
   ──► texto_limpio, métricas
        │
   ┌── si falla ─────────────────────────────────────────────────────────────┐
   │   UPDATE pipeline_limpieza_log SET resultado='error', ...               │
   │   UPDATE instrumento_procesado SET estado='error', ...                  │
   │   Conservar storage/temp/ para diagnóstico                              │
   └─────────────────────────────────────────────────────────────────────────┘
        │
        ▼
7. Escribir storage/temp/{instrumento_id}_limpio.txt (texto limpio)
        │
        ▼
8. Calcular MD5 del texto extraído (para trazabilidad)
        │
        ▼
9. JsonCanonicoService.escribir_bloque_limpieza(instrumento_id, {
       fecha_limpieza, modelo_llm, prompt_version,
       extractor_usado, texto_extraido_hash, segmentos, texto_limpio
   })
   ──► Escritura atómica del JSON canónico
        │
        ▼
10. UPDATE instrumento_procesado
    SET estado='limpio',
        ruta_texto_extraido=NULL,
        ruta_texto_limpio=NULL,
        error_detalle=NULL
        │
        ▼
11. Eliminar storage/temp/{instrumento_id}_extraido.txt
    Eliminar storage/temp/{instrumento_id}_limpio.txt
        │
        ▼
12. UPDATE pipeline_limpieza_log
    SET resultado='exitoso',
        finalizado_en=NOW(),
        extractor_usado, modelo_llm, prompt_version,
        tokens_entrada, tokens_salida, latencia_ms
```

---

### 17.8 Services internos del pipeline

Ubicación: `pipeline_limpieza/`

#### `TextoExtractorService`

```
extraer_texto(ruta: Path, tipo_mime: str) -> str
    Despacha a la estrategia correcta según tipo_mime.
    Lanza TextoExtractionError si el formato no es soportado y el fallback falla.

extraer_pdf(ruta: Path) -> str
extraer_docx(ruta: Path) -> str
extraer_xlsx(ruta: Path) -> str
extraer_texto_plano(ruta: Path) -> str
extraer_csv(ruta: Path) -> str
extraer_fallback(ruta: Path) -> str
    Intenta UTF-8, luego latin-1. Si ambos fallan, retorna "".
```

#### `LLMCleanerService`

```
limpiar_con_llm(texto: str, prompt_template: str) -> tuple[str, dict]
    Si len(texto) > LIMPIEZA_VENTANA_CHARS: segmentar y procesar por ventanas.
    Retorna (texto_limpio, metricas).

segmentar_texto(texto: str, ventana: int, solape: int) -> list[str]
    Divide el texto en segmentos con solapamiento.

cargar_prompt_activo(db: Session) -> tuple[str, str]
    Retorna (contenido_prompt, version) desde la tabla prompt.
```

#### `JsonLimpiezaWriter`

```
escribir_bloque_limpieza(instrumento_id: int, datos: dict) -> Path
    Lee el JSON canónico existente.
    Agrega o reemplaza el bloque "limpieza" con los datos recibidos.
    Actualiza _meta.ultima_actualizacion.
    Escribe de forma atómica.
    No toca ningún otro bloque del JSON.

eliminar_bloque_limpieza(instrumento_id: int) -> None
    Elimina el bloque "limpieza" del JSON canónico.
    Se llama cuando el instrumento recibe nueva versión del archivo.
```

#### `LimpiezaOrchestrator`

```
run_polling_loop(intervalo_segundos: int) -> None
    Bucle principal. Busca instrumentos en estado 'ingresado' sin log activo.

procesar_instrumento(db: Session, instrumento: InstrumentoProcesado) -> None
    Ejecuta el flujo completo (pasos 1–12 del §17.7).
    Maneja excepciones y registra errores en el log.

obtener_pendientes(db: Session, limite: int) -> list[InstrumentoProcesado]
    Query de polling contra PostgreSQL.
```

---

### 17.9 Manejo de errores y reintentos

| Tipo de error                        | Acción                                                                    |
|--------------------------------------|---------------------------------------------------------------------------|
| Formato de archivo no soportado      | `estado → 'error'`, `error_detalle = "formato no soportado: {mime}"`     |
| Archivo no encontrado en disco       | `estado → 'error'`, `error_detalle = "archivo no encontrado: {ruta}"`    |
| LLM no disponible (Ollama down)      | No cambia estado. Reintenta en el próximo ciclo de polling                |
| LLM retorna respuesta vacía          | `estado → 'error'`, `error_detalle = "LLM retornó texto vacío"`          |
| Error al escribir JSON canónico      | `estado → 'error'`, conserva archivos en `temp/` para diagnóstico        |
| Error desconocido                    | `estado → 'error'`, `error_detalle = traceback`                           |

**Reintentos:** un administrador puede resetear el estado de `error → ingresado` mediante `PATCH /instrumentos/{id}/estado`. Esto limpia `error_detalle` y el instrumento vuelve a ser elegible para el polling.

---

### 17.10 Consideraciones de concurrencia

1. El pipeline usa la presencia de un log con `resultado = 'en_proceso'` como lock optimista. Si dos instancias del pipeline pollan simultáneamente, ambas ven el mismo instrumento pero solo la primera crea el log `en_proceso`. La segunda, al hacer el INSERT, falla por unicidad del log activo y omite el instrumento.

2. En la versión actual, el pipeline corre como un **proceso background** dentro de la misma aplicación FastAPI, iniciado en el evento `startup`. Para escalar, puede extraerse a un worker independiente que comparta la misma base de datos.

3. El batch de polling está limitado a 10 instrumentos por ciclo para evitar saturar Ollama con llamadas concurrentes.

---

### 17.11 Integración con el evento `startup` de FastAPI

```python
# backend/main.py — fragmento

import asyncio
from pipeline_limpieza.orchestrator import LimpiezaOrchestrator

@app.on_event("startup")
async def startup_event():
    print("inicianding app")
    orchestrator = LimpiezaOrchestrator()
    asyncio.create_task(orchestrator.run_polling_loop(intervalo_segundos=30))
```

El pipeline corre como una corutina concurrente al servidor HTTP. No bloquea las peticiones de los usuarios ni comparte estado mutable con los routers.

---

## 17. Pipeline de Limpieza Guiado por LLM — Especificación Completa

> Esta sección es un marcador. El contenido completo del pipeline está en §17 (arriba).

---

## 18. Notas de Implementación — Pipeline de Limpieza

1. **PostgreSQL no almacena metadatos semánticos.** La columna `metadatos JSONB` del esquema original debe eliminarse de `instrumento_procesado`. El JSON canónico en disco es la única copia del conocimiento semántico.

2. **La lectura del JSON canónico en `GET /instrumentos/{id}` es síncrona.** El archivo es pequeño (< 50 KB en la mayoría de casos) y la lectura desde disco local es suficientemente rápida. Si en el futuro el volumen lo justifica, se puede cachear en Redis.

3. **`visibilidad` en el listado.** El query de listado **siempre** aplica el filtro de visibilidad/permiso. No existe un endpoint público sin autenticación.

4. **Nombre de propietario en listados.** Se resuelve via JOIN con `permiso_instrumento` (rol = 'propietario') y `usuarios`. Siempre hay exactamente un propietario por instrumento.

5. **Prevención de huérfanos en disco.** Si la transacción de base de datos falla después de guardar el archivo en disco, el archivo queda huérfano. Implementar un job de limpieza periódico que compare los hashes en `raw_data` contra los archivos en `storage/raw/`.

6. **El bloque `limpieza` no se embebe ni se indexa en ChromaDB.** Es información operativa del pipeline, no conocimiento semántico. Los pipelines de inferencia KPI y chunking IEC leen `limpieza.texto_limpio` como insumo, pero no lo exponen al espacio vectorial.

7. **El pipeline de limpieza no requiere endpoints de usuario.** Los usuarios solo ven el `estado` del instrumento avanzar de `ingresado` a `limpio`. El proceso es transparente para ellos.

8. **Transición de estado protegida.** El endpoint `PATCH /estado` verifica la máquina de estados antes de actualizar. Un usuario regular que intente hacer esta llamada recibirá `403 Forbidden`, no `422`.
