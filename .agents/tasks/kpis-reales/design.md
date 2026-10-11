# Diseño técnico — Integración de KPIs reales (kpis-reales)

## Resumen

Esta tarea reemplaza el catálogo de KPIs de ejemplo por los **55 KPIs reales** del CSV
`infrastructure/postgres/seed/kpis_ampliados.csv` y los propaga por las cinco capas que los
tocan: (1) el esquema de `tt_rag.kpi` + un mecanismo de re-seed reproducible desde el CSV,
(2) el modelo ORM `shared/models/kpi.py`, (3) la indexación vectorial de la colección Chroma
`kpis` en `analysis-service`, (4) un endpoint de catálogo real estructurado y (5) la pantalla de
KPIs del frontend `pixel-perfect-pixel`.

Decisiones de arquitectura fijadas en este diseño (quedan bloqueadas al aprobarse):

- **Stack**: PostgreSQL 15+ (esquema `tt_rag`), SQLAlchemy 2.x (ORM `Mapped`/`mapped_column`),
  FastAPI (routers por servicio), ChromaDB (HttpClient, `hnsw:space=cosine`),
  sentence-transformers (`settings.EMBEDDING_MODEL`, 768-dim, `normalize_embeddings=True`),
  React + TypeScript + TanStack Router + lucide-react en el frontend. Nada de esto cambia.
- **Re-seed**: **script Python** (`csv.DictReader`, `utf-8-sig`) sobre el ORM compartido, no SQL
  generado a mano. Justificación abajo (§1.3).
- **Endpoint de catálogo**: vive en **analysis-service** y el frontend lo llama **directo vía
  `ANALYSIS_URL`** (igual que `espacio.ts`). Justificación abajo (§4).
- **Embedding**: se vectoriza **solo** `texto_contexto_rag_vectorial`; el resto son metadatos.

El re-seed destructivo de `tt_rag.kpi` está autorizado por el usuario (reemplazo completo de los
KPIs viejos por los 55 nuevos). Todo el texto de usuario, rutas e identificadores de dominio se
mantienen en español.

### Confirmación del CSV (re-lectura)

`infrastructure/postgres/seed/kpis_ampliados.csv` leído en este paso:

- Total de líneas del archivo: **56** → 1 cabecera + **55 filas de datos**.
- **8 columnas**, en orden exacto: `KPI`, `Polaridad_Rendimiento`, `Tipo_Objetivo_Estrategico`,
  `Formula_Metrica_Calculo`, `Descripcion_Ampliada_Educativa`,
  `Comportamiento_Direccional_y_Causalidad`, `Razon_Estrategica_y_Decisiones`,
  `Texto_Contexto_RAG_Vectorial`.
- Los campos contienen comas y comillas internas (texto multilínea entrecomillado), lo que hace a
  `csv.DictReader` la vía correcta de lectura (no `split(',')` ni SQL a mano).

> El CSV todavía NO está dentro del worktree `.worktrees/kpis-reales`. La implementación debe
> **copiarlo/versionarlo** en el worktree bajo la misma ruta (`infrastructure/postgres/seed/
> kpis_ampliados.csv`) antes de ejecutar el seed. El conteo 55 **no se hardcodea**: todo script
> recuenta las filas del CSV al ejecutarse.
>
> Nota sobre el conteo (mensaje 12 del usuario dijo *"estos 46 nuevos"*): el CSV entregado contiene
> en realidad **55 KPIs** (55 líneas de datos + cabecera = 56 líneas; verificado). El diseño trata
> el CSV como fuente de verdad y **recuenta en runtime** (no asume 46 ni 55), por lo que la
> discrepancia no afecta la implementación; se deja constancia para que el usuario confirme que el
> CSV cargado es el correcto. Los criterios de aceptación que citan "55" se evalúan contra el conteo
> real del CSV al momento del seed.

---

## 1. Capa 1 — Esquema de BD + re-seed (`tt_rag.kpi`)

### 1.1 Nueva forma de la tabla

En `infrastructure/postgres/init/01_schema.sql`, el bloque `CREATE TABLE IF NOT EXISTS kpi (...)`
se redefine. Se **conserva `kpi_id SERIAL PRIMARY KEY`** (las FKs de `kpi_variable`,
`kpi_inferido`, `valor_variable_inferido` y `kpi_inferido_chunk` lo referencian y deben sobrevivir)
y se reemplazan las 6 columnas actuales (`nombre_kpi, descripcion, categoria, ambito,
url_documentacion, formula`) por 8 columnas snake_case en español, una por columna del CSV:

```sql
CREATE TABLE IF NOT EXISTS kpi (
    kpi_id                               SERIAL PRIMARY KEY,
    nombre                               TEXT NOT NULL,  -- CSV: KPI
    polaridad_rendimiento                TEXT,            -- CSV: Polaridad_Rendimiento
    tipo_objetivo_estrategico            TEXT,            -- CSV: Tipo_Objetivo_Estrategico
    formula_metrica_calculo              TEXT,            -- CSV: Formula_Metrica_Calculo
    descripcion_ampliada_educativa       TEXT,            -- CSV: Descripcion_Ampliada_Educativa (significado UI)
    comportamiento_direccional_causalidad TEXT,           -- CSV: Comportamiento_Direccional_y_Causalidad
    razon_estrategica_decisiones         TEXT,            -- CSV: Razon_Estrategica_y_Decisiones
    texto_contexto_rag_vectorial         TEXT NOT NULL    -- CSV: Texto_Contexto_RAG_Vectorial (texto a embeber)
);
```

Mapeo CSV → columna SQL (decisión FR-1.2):

| Columna CSV | Columna SQL | Nullability | Razón |
|---|---|---|---|
| `KPI` | `nombre` | NOT NULL | Nombre visible; siempre presente |
| `Polaridad_Rendimiento` | `polaridad_rendimiento` | NULL | Metadato / etiqueta |
| `Tipo_Objetivo_Estrategico` | `tipo_objetivo_estrategico` | NULL | Metadato / etiqueta |
| `Formula_Metrica_Calculo` | `formula_metrica_calculo` | NULL | `comoSeMide`/`formula` en UI |
| `Descripcion_Ampliada_Educativa` | `descripcion_ampliada_educativa` | NULL | Significado mostrado en UI |
| `Comportamiento_Direccional_y_Causalidad` | `comportamiento_direccional_causalidad` | NULL | `queMide` en UI |
| `Razon_Estrategica_y_Decisiones` | `razon_estrategica_decisiones` | NULL | `infoGeneral` en UI |
| `Texto_Contexto_RAG_Vectorial` | `texto_contexto_rag_vectorial` | NOT NULL | Texto a embeber; CSV garantiza 0 vacíos |

No se reutilizan los nombres de columna viejos (son conceptualmente distintos; renombrarlos
confundiría). Se eliminan `url_documentacion` y `formula` (sin equivalente en el nuevo modelo) y
se añaden las 8 nuevas. `nombre` y `texto_contexto_rag_vectorial` son `NOT NULL` porque el CSV
garantiza que están poblados (55 nombres únicos, 0 textos RAG vacíos); el resto es nullable por
robustez ante futuros CSV con huecos.

**Invariante y propiedad (FR-1.1 / FR-1.5):** `kpi_id` sigue siendo `SERIAL PRIMARY KEY`. El seed
resetea la identidad (`RESTART IDENTITY`) y re-inserta en el orden del CSV, de modo que los IDs
quedan **contiguos 1..55**. La enforcement de la unicidad/PK la hace **Postgres** (constraint de
PK); la de "exactamente los 55 del CSV, sin residuos" la hace la **operación de seed** (truncado +
re-inserción). La capa de aplicación no inventa IDs.

> Nota: `init/*.sql` corre **solo al crear un volumen de Postgres vacío**. En una BD ya
> levantada el cambio de `CREATE TABLE IF NOT EXISTS` no se re-aplica. Por eso el cambio de forma
> de la tabla para una BD existente se hace con el comando on-demand de §1.4, y el re-seed de
> datos con el script de §1.3. En entorno de pruebas la vía recomendada es **recrear el volumen**
> (`docker compose down -v && docker compose up -d postgres`) para que `01_schema.sql` aplique la
> nueva forma desde cero; el script de seed se corre después.

### 1.2 CSV como única fuente de verdad

El seed se alimenta exclusivamente del CSV. No se incrustan en SQL los textos de los 55 KPIs
(evita divergencia CSV↔SQL, FR-1.4). El `04_seed.sql` deshabilitado
(`init/_disabled/04_seed.sql`) queda **obsoleto** (sus columnas `nombrekpi, descripcion,
direccion_deseada, razon, formula` ni siquiera coinciden con el esquema vigente); se deja donde
está (deshabilitado) y no se re-activa. No se añade ningún seed SQL nuevo bajo `init/` para KPIs.

### 1.3 Mecanismo de re-seed — DECISIÓN: script Python

**Se elige un script Python** `services/analysis-service/scripts/seed_kpis.py` (análogo a
`services/instrument-service/scripts/seed_demo.py`), por encima de un seed SQL generado:

- El CSV tiene texto multilínea con comas y comillas internas; `csv.DictReader(encoding="utf-8-sig")`
  lo parsea correctamente, mientras que generar `INSERT`s a mano es frágil y propenso a errores de
  escape.
- Mantiene el CSV como única fuente de verdad y es **re-ejecutable** contra una BD ya levantada
  (requisito del enunciado: `init/*.sql` solo corre en volumen nuevo).
- Reutiliza el ORM compartido (`shared.db.session.SessionLocal`, modelos `tt_rag`), igual que
  `seed_demo.py`, respetando el `search_path tt_rag` (lo fija `shared/db` vía el modelo con
  `__table_args__ = {"schema": SCHEMA}`).

Se ubica en **analysis-service** (no en instrument-service) porque es el servicio dueño del dominio
de KPIs/vectorización y porque tras sembrar conviene disparar el reindex (§3) desde el mismo
servicio.

Comportamiento del script (determinista e idempotente en resultado final — NFR-3):

1. Resolver la ruta del CSV de forma robusta: variable de entorno `KPIS_CSV_PATH` si está
   definida; si no, ruta por defecto relativa a la raíz del repo. El script vive en
   `services/analysis-service/scripts/seed_kpis.py`, con la **misma profundidad** que
   `services/instrument-service/scripts/seed_demo.py` (scripts → service → services → raíz), de modo
   que la raíz del repo es `Path(__file__).resolve().parents[3]` (idéntico a `seed_demo.py`, que usa
   `parents[3]`). La ruta por defecto del CSV queda **fijada** a:
   ```python
   Path(__file__).resolve().parents[3] / "infrastructure" / "postgres" / "seed" / "kpis_ampliados.csv"
   ```
   (verificado: con `parents[3]` apuntando a la raíz del worktree esa ruta es la del CSV una vez
   copiado — ver §Confirmación del CSV y §6, primer ítem).
2. Leer con `csv.DictReader(f)` sobre el archivo abierto con `encoding="utf-8-sig"`.
3. **Validaciones de pre-condición** (si fallan, aborta con código ≠ 0 y log de error, sin tocar la
   BD): la cabecera trae exactamente las 8 columnas esperadas y en el orden esperado; ninguna fila
   tiene `KPI` vacío; ninguna fila tiene `Texto_Contexto_RAG_Vectorial` vacío. El conteo de filas
   se **recalcula** (no se asume 55).
4. En **una sola transacción**: `TRUNCATE tt_rag.kpi RESTART IDENTITY CASCADE` y luego insertar las
   filas en el orden del CSV construyendo objetos `KPI(...)` (SQLAlchemy asigna `kpi_id`
   autoincremental 1..N). `commit()` al final; `rollback()` ante cualquier excepción.
5. Log final: `n_insertados` y recordatorio de ejecutar el reindex (§3).

**Error handling del script (concreto):**

| Operación | Condición de fallo | ¿Recuperable? | Resultado al invocador | Log |
|---|---|---|---|---|
| Abrir CSV | archivo inexistente / sin permiso (`OSError`) | fatal | exit code 2, no toca BD | `logger.error` con la ruta |
| Parsear CSV | cabecera incorrecta / columna faltante | fatal | exit code 3, no toca BD | `logger.error` con las columnas esperadas vs halladas |
| Validar filas | `KPI` o `Texto_Contexto_RAG_Vectorial` vacío | fatal | exit code 3, no toca BD | `logger.error` con el nº de fila |
| TRUNCATE + INSERT | error de BD (`SQLAlchemyError`) | fatal | `rollback()`, exit code 4 | `logger.exception` |
| Éxito | — | — | exit code 0, imprime `n_insertados` | `logger.info` |

El `TRUNCATE ... RESTART IDENTITY CASCADE` es **destructivo autorizado**: `CASCADE` vacía también
`kpi_variable`, `kpi_inferido`, `valor_variable_inferido` y `kpi_inferido_chunk` (inferencias
históricas). Está dentro de lo autorizado (reemplazo completo del catálogo; las inferencias previas
se consideran descartables en pruebas, ver Supuestos de requisitos). Las **constraints de FK no se
eliminan**; solo se vacían las filas hijas, por lo que las FKs siguen válidas tras el seed (CA-3).

### 1.4 Comando on-demand (BD ya levantada)

Para una BD que ya existe (volumen no recreado), el flujo documentado es:

1. Aplicar la nueva **forma** de la tabla. **Único camino soportado en pruebas (resuelve revisión
   it. 4, hallazgo NIT-4): recrear el volumen** (`docker compose down -v && docker compose up -d
   postgres`) para que `01_schema.sql` cree la tabla nueva junto con TODAS las tablas hijas y sus
   FKs. **El `DROP TABLE ... CASCADE` manual queda DESACONSEJADO**: `CASCADE` elimina las constraints
   FK de las tablas hijas (`kpi_variable`, `kpi_inferido`, `valor_variable_inferido`,
   `kpi_inferido_chunk`), y re-correr `01_schema.sql` con `CREATE TABLE IF NOT EXISTS` **no** recrea
   esas hijas ya existentes ni sus FKs, por lo que un operador que elija el DROP manual violaría CA-3
   (FKs intactas) de forma silenciosa. Si, pese a todo, se insiste en el DROP manual en una BD viva
   que no se puede recrear, es **obligatorio** recrear explícitamente después las FKs de
   `kpi_variable`, `kpi_inferido`, `valor_variable_inferido` y `kpi_inferido_chunk` hacia
   `kpi(kpi_id)`.
2. Sembrar los datos con el script de §1.3:
   ```bash
   docker compose exec analysis-service python scripts/seed_kpis.py
   # o en local, desde services/analysis-service:
   python scripts/seed_kpis.py
   ```
3. Reindexar Chroma (§3): `POST /vectorizacion/kpis/reindex` — **inmediatamente** tras desplegar el
   código nuevo (ver orden vinculante en §3.5). El reindex hace `delete_collection`+recrear, por lo
   que deja la colección `kpis` sin ningún punto con la clave de metadato vieja `nombre_kpi`.

Regla de estado de Chroma en **pruebas**: recrear el volumen de Chroma **a la vez** que el de
Postgres (`docker compose down -v && docker compose up -d` baja ambos volúmenes) para que no
sobreviva una colección `kpis` con metadatos de clave vieja antes del primer reindex (§3.5).

Se documenta en `infrastructure/postgres/README.md` (nota breve) y en el docstring del script.

### 1.5 Testabilidad

- **Unit**: el parser/validador del CSV se extrae a una función pura
  `leer_kpis_csv(path) -> list[dict]` testeable con un CSV de fixture (cabecera mala, campo vacío,
  caso feliz). No requiere BD.
- **Integración**: ejecutar el script contra una Postgres de prueba y verificar
  `SELECT COUNT(*) = 55` e IDs contiguos (CA-2).

---

## 2. Capa 2 — Modelo ORM (`shared/models/kpi.py`)

Se reescribe la clase `KPI` para reflejar exactamente la tabla de §1.1 (FR-2.1):

```python
class KPI(Base):
    __tablename__ = "kpi"
    __table_args__ = {"schema": SCHEMA}

    kpi_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    polaridad_rendimiento: Mapped[str | None] = mapped_column(Text)
    tipo_objetivo_estrategico: Mapped[str | None] = mapped_column(Text)
    formula_metrica_calculo: Mapped[str | None] = mapped_column(Text)
    descripcion_ampliada_educativa: Mapped[str | None] = mapped_column(Text)
    comportamiento_direccional_causalidad: Mapped[str | None] = mapped_column(Text)
    razon_estrategica_decisiones: Mapped[str | None] = mapped_column(Text)
    texto_contexto_rag_vectorial: Mapped[str] = mapped_column(Text, nullable=False)
```

`__repr__` se actualiza para usar `self.nombre`. No se declaran relaciones nuevas (las tablas
hijas referencian por `kpi_id` y ya existen).

**Impacto en consumidores (FR-2.2):** desaparecen `nombre_kpi`, `descripcion`, `categoria`,
`ambito`, `url_documentacion`, `formula`. Hay que reconciliar cada lectura (ver §3 y §4).

### 2.1 Schemas Pydantic compartidos (`shared/schemas/kpi.py`) — reconciliación obligatoria

`shared/schemas/kpi.py` define los DTOs Pydantic `KPIBase`, `KPICreate`, `KPIUpdate`, `KPIRead`,
re-exportados desde `shared/schemas/__init__.py` (están en `__all__`) y por tanto parte del
**contrato compartido** entre servicios (cualquier servicio puede importarlos). Su docstring dice
textualmente *"Refleja 1:1 la tabla `tt_rag.kpi` de 01_schema.sql"* y `KPIRead` usa
`ConfigDict(from_attributes=True)` sobre el ORM. Hoy usan los nombres **viejos**
(`nombre_kpi, descripcion, categoria, ambito, url_documentacion, formula`), de modo que tras
reescribir el modelo (§2) y la tabla (§1.1) quedarían inconsistentes: su docstring sería falso y
cualquier `KPIRead.model_validate(kpi_orm)` fallaría porque el ORM ya no expone esos atributos.

**Decisión:** se reescribe `shared/schemas/kpi.py` para reflejar la tabla nueva de §1.1 (8 campos),
manteniendo el patrón Base/Create/Update/Read y el docstring veraz:

```python
class KPIBase(BaseModel):
    nombre: str
    polaridad_rendimiento: str | None = None
    tipo_objetivo_estrategico: str | None = None
    formula_metrica_calculo: str | None = None
    descripcion_ampliada_educativa: str | None = None
    comportamiento_direccional_causalidad: str | None = None
    razon_estrategica_decisiones: str | None = None
    texto_contexto_rag_vectorial: str

class KPICreate(KPIBase):
    pass

class KPIUpdate(BaseModel):
    # los 8 campos como Optional (actualización parcial)
    nombre: str | None = None
    polaridad_rendimiento: str | None = None
    tipo_objetivo_estrategico: str | None = None
    formula_metrica_calculo: str | None = None
    descripcion_ampliada_educativa: str | None = None
    comportamiento_direccional_causalidad: str | None = None
    razon_estrategica_decisiones: str | None = None
    texto_contexto_rag_vectorial: str | None = None

class KPIRead(KPIBase):
    model_config = ConfigDict(from_attributes=True)
    kpi_id: int
```

No cambian los nombres exportados (`KPIBase/KPICreate/KPIUpdate/KPIRead`), así que
`shared/schemas/__init__.py` y su `__all__` **no se tocan** (los imports siguen resolviendo). Solo
cambia el cuerpo de los schemas. Grep de uso en runtime: estos schemas **no son leídos hoy** por
ningún router activo de KPIs (el catálogo nuevo usa su propio `KpiCatalogoDTO` en
`schemas/vectorizacion.py`, §4.2, no `KPIRead`); la actualización es necesaria igualmente para que
el contrato compartido y su docstring no mientan y para que un futuro `KPIRead.model_validate` sobre
el ORM funcione.

---

## 3. Capa 3 — Indexación vectorial (`analysis-service`, colección `kpis`)

### 3.1 `kpi_indexer.py`

`build_kpi_text` se reduce a devolver **solo** el texto RAG (FR-3.1):

```python
def build_kpi_text(kpi: KPI) -> str:
    """Texto a vectorizar: ÚNICAMENTE el párrafo RAG autocontenido del KPI."""
    return kpi.texto_contexto_rag_vectorial or ""
```

La metadata se construye con una **función pura** `build_kpi_metadata(kpi)` (simétrica a
`build_kpi_text`, resuelve revisión it. 4, hallazgo NIT-3) con campos escalares (sin `None`, usando
`""` de fallback) — FR-3.2. Extraerla como función pura la hace testeable como unidad sin levantar
la ruta completa:

```python
def build_kpi_metadata(kpi: KPI) -> dict:
    """Metadata escalar del punto Chroma (sin None; simétrica a build_kpi_text)."""
    return {
        "kpi_id": kpi.kpi_id,
        "nombre": kpi.nombre or "",
        "polaridad_rendimiento": kpi.polaridad_rendimiento or "",
        "tipo_objetivo_estrategico": kpi.tipo_objetivo_estrategico or "",
        "formula_metrica_calculo": kpi.formula_metrica_calculo or "",
        "descripcion_ampliada_educativa": kpi.descripcion_ampliada_educativa or "",
    }

# en reindex_kpis:
metadatas = [build_kpi_metadata(k) for k in kpis]
```

Se conserva: `ids = [str(k.kpi_id) ...]` (FR-3.3), `collection = settings.CHROMA_COLLECTION_KPIS`,
documento = `textos` (= el texto RAG), coseno + `normalize_embeddings=True` + mismo
`settings.EMBEDDING_MODEL` (FR-3.4, NFR-4). El `document` del punto queda idéntico a
`texto_contexto_rag_vectorial` (CA-4, CA-5). Se **renombra el metadato `nombre_kpi` → `nombre`**
para alinearlo con la nueva columna; esto obliga a tocar dos lectores de ese metadato (ver §3.3).

### 3.2 Purga de puntos obsoletos (FR-3.5)

El `upsert` actual no borra puntos que ya no existen. Como el seed deja IDs **contiguos 1..55** y
el catálogo viejo tenía ~30, los IDs 1..30 se **sobre-escriben** por upsert, pero no quedan IDs
huérfanos > 55 salvo que el catálogo viejo tuviera más de 55 puntos. Para garantizar que la
colección contenga **exactamente** los 55 (CA-4), el reindex **borra y recrea** la colección antes
de insertar, en lugar de confiar en el solapamiento de IDs:

- En `kpi_indexer.reindex_kpis`, antes de upsert: obtener el cliente Chroma y hacer
  `client.delete_collection(settings.CHROMA_COLLECTION_KPIS)` (idempotente: capturar la excepción
  "no existe" y continuar), luego `get_or_create_collection(...)` para recrearla con
  `hnsw:space=cosine`, y finalmente `upsert` de los 55. Esto deja la colección con exactamente 55
  puntos sin vectores huérfanos.
- Para soportarlo se añade a `chroma_client.py` un helper `delete_collection(name, *, client=None)`
  que llama `cli.delete_collection(name)` y traga el error si la colección no existe. Mantiene el
  patrón de `get_or_create_collection` (inyección de `client` para tests).

**Cambio de seam de inyección (resuelve revisión it. 4, hallazgo MEDIUM-1).** La firma actual
`reindex_kpis(db, *, collection=None)` es ambigua frente al nuevo borrado+recreación: si se inyecta
un `collection` ya construido, no está definido si se omite el borrado (dejaría huérfanos y falsearía
la prueba de purga) o si se borra por nombre fijo pese a la colección inyectada (incoherente). **Se
migra el seam de `collection` a `client`:**

```python
def reindex_kpis(db: Session, *, client=None) -> ReindexResult:
    cli = client or chroma_client.get_client()
    nombre = settings.CHROMA_COLLECTION_KPIS
    chroma_client.delete_collection(nombre, client=cli)          # idempotente
    coleccion = chroma_client.get_or_create_collection(nombre, client=cli)
    # ... build textos + metadatas, embed, upsert sobre `coleccion` ...
```

El router llama `reindex_kpis(db)` sin `collection=`. La prueba de integración de §3.6 **inyecta
`client`** (un `EphemeralClient` de Chroma) para ejercitar el borrado+recreación reales y confirmar
que quedan exactamente 55 puntos. Así el borrado SIEMPRE ocurre por nombre sobre el mismo cliente,
sin interpretaciones divergentes.

Alternativa considerada y descartada: calcular el conjunto de IDs previos y borrarlos uno a uno. Es
más código y más frágil que recrear la colección; recrear es O(1) conceptual y determinista.

### 3.3 Reconciliación de lectores del metadato / columnas viejas

Grep de lecturas de columnas viejas (`.nombre_kpi/.descripcion/.categoria/.ambito/.formula`) y del
metadato `nombre_kpi` en `analysis-service` + chroma-viewer. Resolución exacta por archivo:

- **`kpi_indexer.py`** (`build_kpi_text`, metadatas): reescrito arriba (§3.1).
- **`kpi_search.py`** — `KpiMatch` tiene `nombre_kpi, categoria, ambito`, y `search_kpis` lee
  `meta.get("nombre_kpi")`, `meta.get("categoria")`, `meta.get("ambito")`.
  - `KpiMatch` se redefine a: `kpi_id: int`, `nombre: str`, `polaridad_rendimiento: str`,
    `tipo_objetivo_estrategico: str`, `score: float`. (Se sustituyen `categoria`/`ambito` —que ya
    no existen— por los dos metadatos equivalentes más útiles para mostrar el candidato.)
  - En `search_kpis`: `nombre=str(meta.get("nombre", ""))`,
    `polaridad_rendimiento=str(meta.get("polaridad_rendimiento", ""))`,
    `tipo_objetivo_estrategico=str(meta.get("tipo_objetivo_estrategico", ""))`.
  - **Disponibilidad de los metadatos (ver §3.5):** `nombre`, `polaridad_rendimiento` y
    `tipo_objetivo_estrategico` solo existen como claves en los puntos de Chroma **tras el reindex
    nuevo** (§3.1). Antes del reindex, los puntos del catálogo viejo traen la clave `nombre_kpi` (no
    `nombre`) y carecen de los dos metadatos nuevos, de modo que `search_kpis` degradaría a `""` — un
    estado **prohibido por el runbook de §3.5** (reseed → desplegar código → reindex inmediato con
    `delete_collection`+recrear). No existe un estado intermedio soportado en el que `search_kpis` lea
    la colección antes del reindex.
- **`proposal_service.py`** — construye `PropuestaKPI(kpi_id, nombre_kpi, categoria, ambito, score)`
  a partir de `KpiMatch`. Se mapea a la nueva forma (ver §3.4): `PropuestaKPI(kpi_id=m.kpi_id,
  nombre=m.nombre, polaridad_rendimiento=m.polaridad_rendimiento,
  tipo_objetivo_estrategico=m.tipo_objetivo_estrategico, score=m.score)`.
- **`enrichment_service.py`** — lee `kpis[d.kpi_id].nombre_kpi` dos veces (al construir
  `KpiAgregado` y la clave `inferred_kpis` del JSON). Ambas pasan a `.nombre`. `KpiAgregado`
  conserva el campo de nombre pero renombrado a `nombre` (ver §3.4). La clave `inferred_kpis` del
  JSON enriquecido pasa de `{"kpi_id", "nombre_kpi", "score"}` a `{"kpi_id", "nombre", "score"}`.
- **`espacio.py`** (`_label_for`, rama `coleccion == "kpis"`) lee `meta.get("nombre_kpi")`. Pasa a
  `meta.get("nombre")`.
- **`infrastructure/chroma-viewer/app.py`** (`_label_for`, rama `kpis`) lee `meta.get("nombre_kpi")`.
  Pasa a `meta.get("nombre")`. (Es un visor read-only de diagnóstico; solo cambia la clave leída.)
- **`shared/schemas/kpi.py`** (`KPIBase/KPICreate/KPIUpdate/KPIRead`): reescrito a los 8 campos
  nuevos — ver §2.1 (contrato compartido; reconciliación obligatoria).

Alcance del grep (corrección de una afirmación previa demasiado amplia): el grep de columnas KPI
viejas (`nombre_kpi|categoria|ambito|descripcion|formula|url_documentacion`) se ejecutó sobre
**todo el worktree** (no solo `analysis-service`). Los lectores vivos resultantes son exactamente
los listados arriba: `kpi_indexer.py`, `kpi_search.py`, `proposal_service.py`,
`enrichment_service.py`, `espacio.py`, `infrastructure/chroma-viewer/app.py` y
`shared/schemas/kpi.py`. **No se afirma** que `analysis-service` fuera el único ámbito; en
particular `shared/schemas/kpi.py` es un consumidor del contrato compartido y se reconcilia en §2.1.

Lector de scratch **no desplegado** (no se toca): `.agents/tasks/chroma-viz/scratch/viewer/app.py`
también hace `meta.get("nombre_kpi")` en la rama `kpis`. Es un visor de *scratch* dentro de
`.agents/tasks/` (no forma parte del runtime de ningún servicio ni de la imagen desplegada del
chroma-viewer, que es `infrastructure/chroma-viewer/app.py`); **se deja intacto**. Si en el futuro se
promoviera a herramienta viva, debería alinear su clave a `nombre` igual que su gemelo en
`infrastructure/`.

### 3.4 Flujo propuestas/confirmar — contrato explícito

El flujo `POST /vectorizacion/propuestas` → `confirmar` expone hoy `categoria`/`ambito`, campos que
desaparecen. **Decisión:** se cambian ambos extremos de forma consistente (el frontend aún consume
estos endpoints vía mock/flujo de carga, y las propuestas son datos derivados, no un contrato
estable con terceros). Cambios en `schemas/vectorizacion.py`:

- `PropuestaKPI`: `nombre_kpi` → **`nombre`**; se **eliminan** `categoria` y `ambito` y se añaden
  `polaridad_rendimiento: str | None` y `tipo_objetivo_estrategico: str | None` (metadatos útiles y
  ya presentes en el punto de Chroma). `kpi_id` y `score` sin cambios.
- `KpiAgregado`: `nombre_kpi` → **`nombre`**.
- `ConfirmarResponse` / `json_enriquecido`: la clave `inferred_kpis` ahora usa `nombre` (§3.3).

Mapeo exacto `PropuestaKPI` viejo→nuevo: `nombre_kpi → nombre` (nombre real del nuevo catálogo),
`categoria`/`ambito` → **retargeted** a `polaridad_rendimiento`/`tipo_objetivo_estrategico` (no se
dejan como campos muertos ni se devuelven vacíos). Esto satisface CA-8: tras el reseed+reindex, las
propuestas traen `nombre` de KPIs reales del nuevo catálogo.

**Consumidor del frontend del contrato de respuesta — reconciliación obligatoria
(`pixel-perfect-pixel/src/api/carga.ts`).** El renombre de clave en el JSON de respuesta de
`/vectorizacion/propuestas` y `/vectorizacion/confirmar` (`nombre_kpi → nombre`) **rompe en runtime**
a `carga.ts`, que consume ambos endpoints y lee el campo renombrado. El build de TypeScript **no lo
detecta** porque `carga.ts` declara sus propias **interfaces locales** (`PropuestaKPI`, `KpiAgregado`)
que no importan los schemas del backend; tras el renombre, `p.nombre_kpi`/`k.nombre_kpi` resolverían a
`undefined` y el wizard de KPIs mostraría nombres vacíos (rompe CA-8 end-to-end en la pantalla real,
aunque la respuesta HTTP sí traiga `nombre`). Por eso **ambos extremos cambian de forma consistente**;
`carga.ts` se añade a §6 y se reconcilia así:

- Interfaz local `PropuestaKPI`: `nombre_kpi: string` → `nombre: string`; **eliminar**
  `categoria?: string | null` y `ambito?: string | null` (no se usan en el mapeo a `KpiSugerido`, que
  solo lee `kpi_id`, `nombre` y `score`; no es necesario traerse los metadatos nuevos al frontend).
  `kpi_id` y `score` sin cambios.
- `proponerKpis`: en el `.map`, `nombre: p.nombre_kpi` → `nombre: p.nombre`.
- Interfaz local `KpiAgregado`: `nombre_kpi: string` → `nombre: string`.
- `confirmarKpis`: en **ambas ramas** del `.map` (la de `score == null` y la de `score` presente),
  `nombreKpi: k.nombre_kpi` → `nombreKpi: k.nombre`.
- La forma de salida de `carga.ts` hacia sus llamadores **no cambia** (`KpiSugerido` sigue con
  `{ id, nombre, coincidencia }`; `confirmarKpis` sigue devolviendo `{ kpiId, nombreKpi, score? }`):
  solo cambia la **clave leída** del JSON del backend, no el contrato que `carga.ts` expone a las
  pantallas. Por eso no hay efecto en cascada en el wizard más allá de este archivo.
- `inferred_kpis` del `json_enriquecido`: la clave interna pasa de `nombre_kpi` a `nombre` (§3.3).
  Ningún consumidor del frontend lee esa sub-clave hoy (`carga.ts` solo expone `jsonEnriquecido` como
  `Record<string, unknown>` opaco y no la indexa); basta documentar el cambio de clave interna, sin
  más cambios en el frontend.

**Validación de entrada del flujo (sin cambios de reglas):** `confirmar` sigue validando que los
`kpi_id` aceptados existan en `tt_rag.kpi` (422 con `KPIs inexistentes: [...]` si no); como los IDs
ahora son 1..55, un ID fuera de rango da 422. `decisiones` vacío → responde 200 con
`kpis_agregados=[]` (comportamiento actual, se conserva).

### 3.5 Reindex tras reseed — orden de operaciones y estado de Chroma (obligatorio)

`POST /vectorizacion/kpis/reindex` debe **re-ejecutarse después de cada reseed** (no es automático).
Tras reseed+reindex correctos devuelve `n_kpis = 55` y la colección `kpis` queda con exactamente 55
puntos (CA-4, CA-6, FR-3.6). Se documenta en el docstring del router y del script de seed.

**Orden de operaciones vinculante** (resuelve el renombre de metadato `nombre_kpi → nombre`, §3.1).
El renombre de la **clave de metadato** en Chroma solo se materializa al reindexar; mientras no se
reindexe, los puntos viejos conservan la clave `nombre_kpi` y el `_label_for` nuevo (que lee
`meta.get("nombre")`) devolvería `None` y degradaría a `doc`/`pid` de forma no determinista. Para
cerrar esa ventana, la secuencia es:

1. **Reseed de Postgres** (recrear volumen de Postgres en pruebas, o script on-demand §1.3/§1.4).
2. **Desplegar el código nuevo** (indexer, lectores de metadato, routers).
3. **Inmediatamente** ejecutar `POST /vectorizacion/kpis/reindex`. Como el reindex ahora hace
   `delete_collection` + recrear (§3.2), **ningún punto conserva la clave `nombre_kpi` vieja** tras
   este paso: la colección se reconstruye desde cero con la clave `nombre`.

Regla de estado de Chroma para **pruebas**: recrear el volumen de Chroma **junto con** el de
Postgres (`docker compose down -v` afecta ambos volúmenes), de modo que no quede ninguna colección
`kpis` previa con metadatos de clave vieja antes del primer reindex. En un entorno vivo donde no se
recree el volumen, basta con que el reindex del paso 3 se corra **antes** de que cualquier visor o
búsqueda lea la colección: el `delete_collection`+recrear garantiza que, una vez completado, no
sobreviva ningún punto con `nombre_kpi`. No existe un estado intermedio soportado en el que el
código nuevo lea la colección antes del reindex; el runbook lo prohíbe explícitamente.

### 3.6 Testabilidad

- **Unit**: `build_kpi_text` (devuelve el texto RAG tal cual, `""` si None); construcción del dict
  de metadata vía `build_kpi_metadata` (función pura, sin `None`). `_distance_to_score` ya testeable.
- **Integración**: reindex contra una Chroma efímera **inyectando `client`** (`EphemeralClient`) y
  `search_kpis` con un vector conocido. Verificar que `delete_collection` + recrear deja 55 puntos
  (el `client` inyectado ejercita el borrado real, no un `collection` preconstruido).

---

## 4. Capa 4 — Endpoint de catálogo real

### 4.1 Dónde vive — DECISIÓN: analysis-service

**Se elige analysis-service**, expuesto bajo `GET /vectorizacion/kpis/catalogo` y consumido por el
frontend **directo vía `ANALYSIS_URL`** (igual que `espacio.ts`). Razones:

- analysis-service es el servicio con **acceso directo a `tt_rag.kpi`** y al dominio de KPIs
  (indexer, propuestas). instrument-service deriva su catálogo de `kpi_hints` de instrumentos, no de
  la tabla `kpi`; meterle una lectura de `tt_rag.kpi` cruzaría una frontera de servicio que la
  refactorización vigente mantiene separada (NFR-2).
- El frontend **ya tiene el patrón** de llamar a analysis-service directo (`getEspacioVectorial`
  usa `ANALYSIS_URL` porque el gateway no proxea `/vectorizacion/*`). Reutilizarlo es coherente.
- Evita cambios en el gateway (que no proxea `/vectorizacion/*`).

Se **conserva** `GET /instrumentos/kpis/catalogo` → `list[str]` en instrument-service **sin
tocarlo** (otros flujos/mocks podrían depender de él; el enunciado prohíbe removerlo). El nuevo
endpoint es aditivo.

### 4.2 Contrato del endpoint

Nuevo router `services/analysis-service/app/vectorization/routers/kpis.py`, registrado en `main.py`.
Prefijo `/vectorizacion` (coherente con los hermanos).

**Registro en `main.py` — dos ediciones, no una.** El estado actual importa los routers con
`from app.vectorization.routers import espacio, health, vectorizacion` y los registra uno por uno.
Para que `kpis.router` exista en tiempo de arranque hacen falta **ambos** cambios (si solo se añade el
`include_router`, el arranque falla con `NameError`):

1. Línea de import: `from app.vectorization.routers import espacio, health, kpis, vectorizacion`
   (añadir `kpis`, manteniendo el orden alfabético existente).
2. Registro: añadir `app.include_router(kpis.router)` junto a los otros tres `include_router`.

No hay colisión de rutas con `vectorizacion.py`: el router nuevo expone `GET /vectorizacion/kpis/
catalogo` y el existente `POST /vectorizacion/kpis/reindex` — método y ruta distintos (verificado).

```
GET /vectorizacion/kpis/catalogo  ->  200  list[KpiCatalogoDTO]
```

- **Auth/guard:** usa `UsuarioActual` (de `app.vectorization.dependencies`), **igual que las rutas
  hermanas** `espacio`/`vectorizacion` de este servicio. (analysis-service no tiene `require_rol`;
  su patrón es `UsuarioActual` + `AUTH_DEV_MODE`. "El mismo guard que las rutas hermanas" = este.)
  El frontend lo llama con `auth: false` en modo desarrollo, idéntico a `getEspacioVectorial`.
- **Orden determinista:** `db.query(KPI).order_by(KPI.kpi_id).all()` (CA-3 orden, FR-4.3).
- **Tamaño:** devuelve exactamente 55 con la BD sembrada (CA-6, FR-4.4).

`KpiCatalogoDTO` (nuevo schema Pydantic en `schemas/vectorizacion.py`), un campo por dato que el
frontend necesita (FR-4.1), todos string:

```python
class KpiCatalogoDTO(BaseModel):
    id: str                                   # str(kpi_id)
    nombre: str
    descripcion_ampliada_educativa: str
    polaridad_rendimiento: str
    tipo_objetivo_estrategico: str
    formula_metrica_calculo: str
    comportamiento_direccional_causalidad: str
    razon_estrategica_decisiones: str
```

El router mapea cada `KPI` → `KpiCatalogoDTO(id=str(k.kpi_id), nombre=k.nombre,
descripcion_ampliada_educativa=k.descripcion_ampliada_educativa or "", ...)`. Regla explícita de
nullability en el mapeo (para que ningún `null` cruce la frontera):

- `id` ← `str(k.kpi_id)`: **nunca** `null`/`""` (`kpi_id` es PK autoincremental, siempre presente).
- `nombre` ← `k.nombre`: **nunca** `null`/`""` ni lleva `or ""` (columna `NOT NULL` en §1.1).
- Los **6 campos restantes son nullable** en la tabla (§1.1) y por tanto llevan `or ""` en el router:
  `descripcion_ampliada_educativa`, `polaridad_rendimiento`, `tipo_objetivo_estrategico`,
  `formula_metrica_calculo`, `comportamiento_direccional_causalidad`, `razon_estrategica_decisiones`.
  En particular `descripcion_ampliada_educativa` (el "significado" que el usuario pidió mostrar,
  FR-5.3) **nunca** debe cruzar como `null`: el `or ""` lo garantiza aunque el dato llegue vacío.

El **ícono NO se calcula en el backend** (ver §5.2): el DTO no incluye `icono`; la heurística vive en
el frontend. Esto evita el bug previo de emitir `ChartBar` y mantiene el conjunto de íconos
sincronizado con el mapa real del componente (FR-5.4).

### 4.3 Error handling

| Operación | Fallo | ¿Recuperable? | Respuesta | Log |
|---|---|---|---|---|
| Resolver usuario (dep) | sin token y `AUTH_DEV_MODE=false` | fatal p/ request | 401 (dependencia existente) | — |
| Query `tt_rag.kpi` | error de BD | fatal p/ request | 500 (deja propagar; FastAPI → 500) | `logger.exception` en un `try/except SQLAlchemyError` del router |
| BD vacía (0 KPIs) | no es error | — | 200 con `[]` | — (el verificador la detecta por CA-6) |

No se añade degradación a mock en el backend (eso vive en el frontend, §5.1).

### 4.4 Testabilidad

- **Integración**: `GET /vectorizacion/kpis/catalogo` con BD sembrada → 200, 55 items, ordenados por
  `id` ascendente, campos poblados. Con BD vacía → `[]`.
- **Contrato**: validar el DTO con Pydantic (ya testeable sin red).

---

## 5. Capa 5 — Frontend (`pixel-perfect-pixel`, Opción B)

### 5.1 `src/api/kpis.ts` — `getCatalogoKpis`

Se reescribe el **cuerpo** de `getCatalogoKpis` para consumir el endpoint real de analysis-service y
mapear a `KpiCatalogo[]` (FR-5.1). **La firma exportada no cambia** (`(): Promise<KpiCatalogo[]>`).
`getKpis`, `getNoticias`, `getDatosGrafica` **se dejan en `simularRed`** con sus TODOs (fuera de
alcance). Las pantallas no importan mocks: los datos siguen fluyendo por `src/api/*`.

> **Dos archivos del frontend se tocan, no uno.** Además de `kpis.ts` (este §5.1), el renombre del
> contrato de respuesta de `/vectorizacion/propuestas` y `/confirmar` (`nombre_kpi → nombre`, §3.4)
> obliga a reconciliar `src/api/carga.ts` (ver §3.4, "Consumidor del frontend del contrato de
> respuesta"). El build de TS no detecta esa rotura (interfaces locales), de modo que listarla aquí es
> necesario para que CA-9 (build) **y** el flujo de propuestas en runtime (CA-8) queden ambos sanos.

```ts
import { ANALYSIS_URL, pedir, simularRed } from "./client";
// catalogoKpis (mock) se conserva solo como fallback de red.

interface KpiCatalogoDTO {
  id: string;
  nombre: string;
  descripcion_ampliada_educativa: string;
  polaridad_rendimiento: string;
  tipo_objetivo_estrategico: string;
  formula_metrica_calculo: string;
  comportamiento_direccional_causalidad: string;
  razon_estrategica_decisiones: string;
}

export async function getCatalogoKpis(): Promise<KpiCatalogo[]> {
  let dtos: KpiCatalogoDTO[];
  try {
    dtos = await pedir<KpiCatalogoDTO[]>(`${ANALYSIS_URL}/vectorizacion/kpis/catalogo`, { auth: false });
  } catch {
    return simularRed(catalogoKpis); // fallback de red para no dejar la página en blanco
  }
  if (!dtos || dtos.length === 0) return simularRed(catalogoKpis);
  return dtos.map(mapearKpi);
}
```

- Se usa `ANALYSIS_URL` + `auth: false` (igual que `espacio.ts`), **no** `API_URL`. El gateway no
  proxea `/vectorizacion/*`, así que debe ser directo.
- El fallback a `catalogoKpis` (mock) se conserva **solo** para error de red / respuesta vacía, para
  no dejar la pantalla en blanco (comportamiento actual que se preserva). No es la ruta normal.

### 5.2 Mapeo DTO → `KpiCatalogo` (Opción B)

Función pura `mapearKpi(dto: KpiCatalogoDTO): KpiCatalogo` dentro de `kpis.ts`:

| Campo `KpiCatalogo` | Origen |
|---|---|
| `id` | `dto.id` (= `str(kpi_id)`) |
| `nombre` | `dto.nombre` |
| `descripcionCorta` | `dto.descripcion_ampliada_educativa` |
| `queEs` | `dto.descripcion_ampliada_educativa` |
| `queMide` | `dto.comportamiento_direccional_causalidad` |
| `comoSeMide` | `dto.formula_metrica_calculo` |
| `formula` | `dto.formula_metrica_calculo` |
| `infoGeneral` | `dto.razon_estrategica_decisiones` |
| `etiquetas` | `derivarEtiquetas(dto.polaridad_rendimiento, dto.tipo_objetivo_estrategico)` |
| `icono` | `elegirIcono(dto.nombre)` |

`derivarEtiquetas`: devuelve pocas etiquetas cortas. Decisión concreta: tomar la **primera palabra
en MAYÚSCULAS** de `polaridad_rendimiento` (`POSITIVO`, `NEGATIVO`, `PUNTO`, `NEUTRO`…) mediante
`match(/^[A-ZÁÉÍÓÚÑ]+/)`, y una etiqueta corta derivada de `tipo_objetivo_estrategico` tomando el
texto antes del primer `/` o `(` y recortándolo a ~24 caracteres. Se filtran vacíos y se
deduplican. Esto evita volcar los textos largos del CSV como etiquetas.

### 5.3 Heurística de ícono (FR-5.2 / FR-5.4)

`elegirIcono(nombre: string): string` vive en el **frontend** (misma base que el mapa `ICONOS`),
para que **nunca** emita un nombre fuera del conjunto. Conjunto válido (único, en
`TarjetaKpi.tsx`/`DetalleKpi.tsx`): `Award, BarChart2, BookOpen, Briefcase, Calculator,
ClipboardCheck, Heart, Home, Laptop, MessageCircle, Monitor, Shield, Smile, Users, Zap`.

Heurística pequeña por palabras clave sobre el nombre, con **fallback `BarChart2`** (nunca
`ChartBar`, que no existe — CA-7).

**Normalización de acentos obligatoria (resuelve revisión it. 4, hallazgo NIT-2).** Las claves de la
heurística están escritas **sin acentos** (`acredit`, `graduaci`, `desercion`…) pero los nombres del
CSV traen acentos (`Acreditación`, `Deserción`…). Sin normalizar, varias ramas nunca dispararían y
todo caería silenciosamente a `BarChart2`. Por eso `elegirIcono` normaliza primero:

```ts
const n = nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
// comparar las claves (ya sin acentos) contra `n`
```

Ramas (comparadas contra `n`, ya en minúsculas y sin acentos):

- `acredit|ranking|logro|premio` → `Award`
- `admis|selectiv|requisit` → `ClipboardCheck`
- `donaci|financ|coleg|matricula|fondo|ingreso|costo|beca` → `Briefcase`
- `asistenc|graduaci|desercion|retencion|permanencia` → `Users`
- `clase|aula|docente|profesor|ensenanza` → `BookOpen`
- `formula|puntaje|calificacion|examen|prueba|calculo` → `Calculator`
- `segurid|bienestar|riesgo` → `Shield`
- `salud|socioemocional|psico` → `Heart`
- `satisfacc|clima` → `Smile`
- `online|digital|plataforma|tecnolog` → `Laptop` (o `Monitor` para `monitor|pantalla`)
- `convenio|colaboraci|comunicaci` → `MessageCircle`
- `energia|eficiencia|producti` → `Zap`
- `campus|instalaci|infraestruc` → `Home`
- en cualquier otro caso → `BarChart2`

Para blindar FR-5.4 a nivel de código: `elegirIcono` termina con
`return ICONOS_VALIDOS.has(candidato) ? candidato : "BarChart2";`, donde `ICONOS_VALIDOS` es un
`Set<string>` con exactamente las 15 claves del mapa. Idealmente las claves se exportan desde un
módulo compartido por `TarjetaKpi`/`DetalleKpi` y `kpis.ts`; mínimo, `kpis.ts` declara el mismo
set. (La implementación puede extraer `ICONOS` a `src/features/kpis/iconos.ts` para evitar
duplicación — mejora opcional, no obligatoria.)

### 5.4 Qué ve el usuario (FR-5.3)

`TarjetaKpi` muestra `nombre` + `descripcionCorta` (= significado) e ícono. `DetalleKpi` muestra
`nombre`, significado, `queEs`, `queMide`, `comoSeMide`, `formula`, `infoGeneral`, `etiquetas`. Los
dos datos que el usuario pidió explícitamente (nombre + significado) quedan garantizados. **No se
rediseñan** los componentes (fuera de alcance); solo se pueblan con datos reales.

### 5.5 Testabilidad

- **Unit (frontend)**: `mapearKpi` (mapeo campo a campo), `elegirIcono` (varios nombres + fallback
  `BarChart2`, y que jamás devuelve una clave fuera de `ICONOS_VALIDOS`), `derivarEtiquetas`.
- **Build**: `tsc`/build de `pixel-perfect-pixel` sin errores de tipos tras el cableado (CA-9).

---

## 6. Lista de cambios archivo por archivo

| Archivo | Cambio |
|---|---|
| `infrastructure/postgres/seed/kpis_ampliados.csv` | **Copiar/versionar** dentro del worktree (misma ruta). |
| `infrastructure/postgres/init/01_schema.sql` | Redefinir `CREATE TABLE kpi` con `kpi_id SERIAL PK` + las 8 columnas nuevas (§1.1). |
| `infrastructure/postgres/init/_disabled/04_seed.sql` | Sin cambios (queda obsoleto/deshabilitado). |
| `infrastructure/postgres/README.md` | Nota breve: cómo re-sembrar on-demand (script + reindex) y que `init/*.sql` solo corre en volumen nuevo (§1.4). |
| `services/analysis-service/scripts/seed_kpis.py` | **Nuevo** script de re-seed desde el CSV (`csv.DictReader`, `utf-8-sig`, TRUNCATE RESTART IDENTITY CASCADE + inserts, validaciones, idempotente) (§1.3). |
| `shared/models/kpi.py` | Reescribir `KPI` con `kpi_id` + las 8 columnas (`Mapped`), `__repr__` usando `nombre` (§2). |
| `shared/schemas/kpi.py` | Reescribir `KPIBase/KPICreate/KPIUpdate/KPIRead` a los 8 campos nuevos; docstring veraz; nombres exportados sin cambios (§2.1). |
| `shared/schemas/__init__.py` | Sin cambios (los nombres exportados `KPIBase/KPICreate/KPIUpdate/KPIRead` no cambian; solo cambia el cuerpo de los schemas). |
| `services/analysis-service/app/vectorization/core/kpi_indexer.py` | `build_kpi_text` devuelve solo `texto_contexto_rag_vectorial`; metadata escalar sin `None`; purga+recrea colección antes del upsert (§3.1, §3.2). |
| `services/analysis-service/app/vectorization/core/chroma_client.py` | Añadir `delete_collection(name, *, client=None)` idempotente (§3.2). |
| `services/analysis-service/app/vectorization/core/kpi_search.py` | `KpiMatch` → `kpi_id, nombre, polaridad_rendimiento, tipo_objetivo_estrategico, score`; `search_kpis` lee los nuevos metadatos (§3.3). |
| `services/analysis-service/app/vectorization/services/proposal_service.py` | Construir `PropuestaKPI` con `nombre`/metadatos nuevos (§3.3, §3.4). |
| `services/analysis-service/app/vectorization/services/enrichment_service.py` | `nombre_kpi` → `nombre` (KpiAgregado y clave `inferred_kpis`) (§3.3, §3.4). |
| `services/analysis-service/app/vectorization/routers/espacio.py` | `_label_for` rama `kpis`: `nombre_kpi` → `nombre` (§3.3). |
| `services/analysis-service/app/vectorization/schemas/vectorizacion.py` | `PropuestaKPI`/`KpiAgregado` renombran `nombre_kpi`→`nombre`, `PropuestaKPI` cambia `categoria`/`ambito`→`polaridad_rendimiento`/`tipo_objetivo_estrategico`; añadir `KpiCatalogoDTO` (§3.4, §4.2). |
| `services/analysis-service/app/vectorization/routers/kpis.py` | **Nuevo** router `GET /vectorizacion/kpis/catalogo` → `list[KpiCatalogoDTO]`, guard `UsuarioActual`, orden por `kpi_id` (§4). |
| `services/analysis-service/main.py` | **Dos cambios:** añadir `kpis` a `from app.vectorization.routers import espacio, health, kpis, vectorizacion` **y** `app.include_router(kpis.router)` (§4.2). |
| `infrastructure/chroma-viewer/app.py` | `_label_for` rama `kpis`: `nombre_kpi` → `nombre` (§3.3). |
| `pixel-perfect-pixel/src/api/kpis.ts` | Reescribir cuerpo de `getCatalogoKpis` (ANALYSIS_URL, mapeo DTO→KpiCatalogo, `elegirIcono`, `derivarEtiquetas`); firma estable; resto en `simularRed` (§5.1–§5.3). |
| `pixel-perfect-pixel/src/api/carga.ts` | Reconciliar el renombre `nombre_kpi→nombre`: interfaces locales `PropuestaKPI`/`KpiAgregado` (`nombre_kpi`→`nombre`, quitar `categoria`/`ambito` de `PropuestaKPI`), `proponerKpis` (`p.nombre_kpi`→`p.nombre`) y `confirmarKpis` (`k.nombre_kpi`→`k.nombre` en ambas ramas). La forma que `carga.ts` expone a las pantallas no cambia (§3.4). |
| `pixel-perfect-pixel/src/features/kpis/iconos.ts` *(opcional)* | Extraer el mapa `ICONOS`/claves válidas para compartir con la heurística (§5.3). |

Archivos **no modificados** a propósito: `services/instrument-service/app/routers/list.py`
(se conserva `GET /instrumentos/kpis/catalogo` → `list[str]`), `src/types/index.ts` (la interfaz
`KpiCatalogo` ya tiene todos los campos del mapeo), `TarjetaKpi.tsx`/`DetalleKpi.tsx` (salvo la
extracción opcional de `iconos.ts`), gateway (no se añade proxy; se llama directo),
`.agents/tasks/chroma-viz/scratch/viewer/app.py` (scratch no desplegado; se deja intacto — §3.3).

---

## 7. Casos borde

- **Campos nullable vacíos**: el DTO del catálogo y la metadata de Chroma usan `or ""` → nunca
  `null`/`None` cruza la frontera. El frontend recibe strings; `derivarEtiquetas` filtra vacíos.
- **Texto RAG con comas/comillas/saltos de línea**: resuelto por `csv.DictReader`; `TRUNCATE`+ORM
  inserta el texto tal cual (sin escapes manuales).
- **BD no sembrada aún**: catálogo → `[]` (200); frontend cae a mock por "respuesta vacía".
- **Reindex sin reseed previo**: devolvería `n_kpis` = lo que haya en BD; el flujo documentado exige
  reseed → reindex en ese orden.
- **IDs fuera de rango en `confirmar`**: 422 `KPIs inexistentes` (validación existente, IDs 1..55).
- **CSV con cabecera cambiada/campo obligatorio vacío**: el script aborta antes de tocar la BD
  (§1.3 error handling), evitando un catálogo corrupto.
- **`delete_collection` cuando la colección no existe**: se traga la excepción (idempotente).

---

## 8. Trazabilidad requisitos → diseño

- FR-1.1/1.5, CA-2/CA-3 → §1.1 (SERIAL PK, IDs 1..55, FKs intactas vía TRUNCATE CASCADE sin dropear
  constraints).
- FR-1.2 → §1.1 (mapeo CSV→SQL). FR-1.3/1.4, NFR-3 → §1.2, §1.3 (seed Python idempotente desde CSV).
- FR-2.1/2.2 → §2, §3.3.
- FR-3.1 → §3.1. FR-3.2/3.3/3.4, NFR-4, CA-4/CA-5 → §3.1. FR-3.5 → §3.2. FR-3.6, CA-6 → §3.5.
  CA-8 → §3.4.
- FR-4.1/4.2/4.3/4.4, CA-6 → §4.
- FR-5.1 → §5.1. FR-5.2/5.4, CA-7 → §5.3. FR-5.3 → §5.4. CA-9 → §5.5.
- NFR-1 (español), CA-10 → columnas/rutas/campos nuevos todos en español.
- NFR-2 → §4.1 (no se cruza frontera instrument→kpi; no se toca gateway; `GET /instrumentos/kpis/
  catalogo` intacto).
- CA-1 → §Confirmación del CSV + validaciones del script (§1.3).

---

## 9. Respuestas a la revisión de diseño (iteración 2)

Revisión fuente: `.agents/tasks/kpis-reales/design-review.json` / `design-review.md`
(veredicto `CHANGES_REQUESTED`, 1 HIGH + 1 MEDIUM + 4 NIT). Resolución de cada hallazgo:

- **Hallazgo 1 [HIGH] — `shared/schemas/kpi.py` sin reconciliar / afirmación de grep falsa.**
  **Atendido.** Se añadió §2.1 que reescribe `KPIBase/KPICreate/KPIUpdate/KPIRead` a los 8 campos
  nuevos (manteniendo nombres exportados y `__all__` intactos, con docstring veraz). Se añadió
  `shared/schemas/kpi.py` a la lista de reconciliación de §3.3 y a la tabla de §6. Se corrigió la
  frase de §3.3 para no afirmar que el grep se limitó a `analysis-service`: ahora enumera
  explícitamente los siete lectores vivos (incluido `shared/schemas/kpi.py`) y aclara el alcance del
  grep sobre todo el worktree. Alineado con FR-2.2 (todo consumidor del modelo se actualiza) y NFR-2
  (el contrato compartido queda coherente).

- **Hallazgo 2 [MEDIUM] — orden de operaciones y estado de Chroma para el renombre
  `nombre_kpi → nombre`.** **Atendido.** §3.5 ahora fija un **orden vinculante** (reseed →
  desplegar código → reindex inmediato) y, como el reindex hace `delete_collection`+recrear (§3.2),
  garantiza que tras el paso 3 no sobreviva ningún punto con la clave vieja `nombre_kpi`. §1.4 y
  §3.5 añaden la regla de **recrear el volumen de Chroma junto con el de Postgres en pruebas** y
  prohíben el estado intermedio en el que el código nuevo lea la colección antes del reindex. Esto
  elimina la degradación no determinista del `_label_for`.

- **Hallazgo 3 [NIT] — `parents[N]` sin pinear.** **Atendido.** §1.3 fija `parents[3]` (misma
  profundidad que `seed_demo.py`, verificada) y la ruta por defecto del CSV
  `parents[3]/infrastructure/postgres/seed/kpis_ampliados.csv`.

- **Hallazgo 4 [NIT] — "46" del usuario vs 55 del CSV.** **Atendido** (constancia). §Confirmación
  del CSV documenta que el CSV trae 55 KPIs (no 46), que el diseño recuenta en runtime (no hardcodea
  el número) y que el CSV manda; se invita al usuario a confirmar que el CSV cargado es el correcto.

- **Hallazgo 5 [NIT] — CSV aún no está en el worktree.** **Atendido** (ya previsto). Sigue como
  primer ítem de §6 (copiar/versionar el CSV al worktree antes del seed); el script aborta con exit
  code 2 bien manejado si corre antes de la copia (§1.3). No requiere cambio de diseño.

- **Hallazgo 6 [NIT] — visor scratch `chroma-viz/scratch/viewer/app.py` no listado.** **Atendido.**
  §3.3 lo anota explícitamente como código de *scratch* no desplegado que **no se toca** (su gemelo
  vivo es `infrastructure/chroma-viewer/app.py`, que sí se reconcilia), y §6 lo lista entre los
  archivos no modificados a propósito.

Todas las resoluciones son consistentes con los requisitos originales (ninguna introduce alcance
nuevo ni contradice los criterios de aceptación).

---

## 10. Respuestas a la revisión de diseño (iteración 3)

Revisión fuente: `.agents/tasks/kpis-reales/design-review.json` / `design-review.md`
(veredicto `CHANGES_REQUESTED`, 1 HIGH + 1 MEDIUM + 2 NIT). Resolución de cada hallazgo:

- **Hallazgo 1 [HIGH] — `pixel-perfect-pixel/src/api/carga.ts` consume `nombre_kpi` de
  `/vectorizacion/propuestas` y `/confirmar`, que §3.4 renombra a `nombre`, sin reconciliar el
  frontend.** **Atendido** (se eligió reconciliar el frontend, no revertir el renombre del backend,
  porque mantener `nombre` alineado con la nueva columna es más limpio y CA-8 pide nombres reales).
  Verificado en el código del worktree: `carga.ts` declara interfaces locales propias `PropuestaKPI
  { nombre_kpi, categoria?, ambito?, ... }` y `KpiAgregado { nombre_kpi }`, y las lee en
  `proponerKpis` (`p.nombre_kpi`) y `confirmarKpis` (ambas ramas: `k.nombre_kpi`); como son
  interfaces locales, el build de TS no detectaría la rotura. §3.4 añade un bloque "Consumidor del
  frontend del contrato de respuesta" con la reconciliación campo por campo (`nombre_kpi→nombre`,
  quitar `categoria`/`ambito` de `PropuestaKPI`, ambas ramas de `confirmarKpis`), §5.1 añade la nota
  de que **son dos** los archivos del frontend tocados, y §6 añade la fila de `carga.ts`. La forma que
  `carga.ts` expone a las pantallas no cambia, así que no hay efecto en cascada. Alineado con CA-8
  (propuestas con nombres reales en runtime) y CA-9 (build).

- **Hallazgo 2 [MEDIUM] — registrar el router nuevo en `main.py` exige editar también la línea de
  import.** **Atendido.** Verificado que `main.py` importa
  `from app.vectorization.routers import espacio, health, vectorizacion`. §4.2 y §6 ahora especifican
  los **dos** cambios: (1) añadir `kpis` al import (orden alfabético:
  `espacio, health, kpis, vectorizacion`) y (2) `app.include_router(kpis.router)`. Se anota que no hay
  colisión de ruta con `vectorizacion.py` (`GET /vectorizacion/kpis/catalogo` vs
  `POST /vectorizacion/kpis/reindex`).

- **Hallazgo 3 [NIT] — el bullet de `kpi_search.py` (§3.3) debe remitir a §3.5 sobre la
  disponibilidad de los metadatos nuevos tras el reindex.** **Atendido.** El bullet de `kpi_search.py`
  en §3.3 añade una nota explícita: `nombre`/`polaridad_rendimiento`/`tipo_objetivo_estrategico` solo
  existen tras el reindex nuevo (§3.1); antes del reindex degradarían a `""`, estado prohibido por el
  runbook de §3.5.

- **Hallazgo 4 [NIT] — fijar que `id`/`nombre` nunca son `null` y los demás campos del DTO llevan
  `or ""`.** **Atendido.** §4.2 ahora lista explícitamente que `id` (PK) y `nombre` (`NOT NULL`)
  nunca son `null`/`""` ni llevan `or ""`, y que los otros **6** campos nullable sí llevan `or ""`;
  en particular `descripcion_ampliada_educativa` (significado, FR-5.3) nunca cruza como `null`.

Todas las resoluciones son consistentes con los requisitos originales (ninguna introduce alcance
nuevo ni contradice los criterios de aceptación) y con las decisiones ya bloqueadas en §1–§8.
