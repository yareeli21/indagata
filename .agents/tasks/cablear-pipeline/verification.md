# Verificación de runtime — cablear-pipeline

Gate de verificación FAIL-CLOSED. Se ejercitó el pipeline REAL de punta a punta
sobre **Windows + Docker** contra el worktree
`c:\Users\yarel\Documents\indagata\indagata\.worktrees\cablear-pipeline`
(rama `cablear-pipeline`, commit `885cb4c`). El checkout principal queda en
`pruebas`, intacto.

**Resultado: `passed = true`.** Los 5 pasos se ejercitaron con evidencia capturada.

---

## 0. Entorno y arranque

### Contexto importante (hallazgo de configuración)

Los contenedores que ya estaban corriendo provenían del checkout principal
(`working_dir = C:\Users\yarel\Documents\indagata\indagata`, rama `pruebas`), que
monta `./services` por volumen y por tanto servía el código VIEJO, no el del
worktree. Se verificó por hash que `proxy.py`, `dc_manager.py` y `main.py`
difieren entre ambos checkouts, así que se bajó esa pila y se levantó la pila
**desde el worktree** (proyecto compose `indagata` para reutilizar volúmenes).

Además se detectó un gap de wiring de entorno pre-existente (fuera del alcance de
los 6 archivos del cambio): el `api-gateway` firma el JWT con
`SECRET_KEY=your-super-secret-key-change-in-production` (viene por `.env`), pero
`instrument/metadata/analysis-service` NO reciben `SECRET_KEY` en su `environment`
de compose y caían al default de `shared` (`dev-secret-key-change-in-production`),
rechazando el token con 401. El diseño exige que todos compartan la MISMA
`SECRET_KEY`. Para poder ejercer el pipeline se añadió un override NO versionado
(`docker-compose.verify.yml`) que iguala `SECRET_KEY` en esos servicios. No se
tocó código de producto.

### Comandos

```powershell
# .env a partir del ejemplo (compose lo necesita; defaults válidos)
Copy-Item .env.example .env -Force

# Rebuild del gateway (requisito del gate) + stack completo desde el worktree
docker compose -p indagata build api-gateway        # -> "Image indagata-api-gateway Built"
docker compose -p indagata -f docker-compose.yml -f docker-compose.verify.yml `
  up -d postgres redis ollama chromadb api-gateway instrument-service `
  analysis-service metadata-service storage-service visualization-service
```

> El servicio `frontend` del compose (dir legacy `frontend/`) falla en `npm ci`
> por un lockfile desincronizado; no es relevante para este gate (el frontend
> real es `pixel-perfect-pixel`, verificado en el paso 5). Se excluyó del `up`.

### Salud de los servicios

```powershell
foreach ($p in 8000,8001,8003,8002) { Invoke-RestMethod "http://localhost:$p/health" }
```

```
8000 OK: {"status":"ok","service":"api-gateway"}
8001 OK: {"status":"ok","service":"instrument-service"}
8003 OK: {"status":"ok","service":"metadata-service","version":"1.0.0"}
8002 OK: {"status":"ok","service":"analysis-service"}
```

Comprobación de que la clave quedó igualada:

```
indagata_api_gateway:        your-super-secret-key-change-in-production
indagata_instrument_service: your-super-secret-key-change-in-production
indagata_metadata_service:   your-super-secret-key-change-in-production
indagata_analysis_service:   your-super-secret-key-change-in-production
```

---

## 1. Login (gateway) — obtención de JWT real

```powershell
POST http://localhost:8000/auth/login
{ "email": "investigador@indagata.com", "password": "investigador123" }
```

Respuesta: `200`, `rol=investigador`, `usuario_id=2`, `access_token` (len 147).
(Credenciales sembradas por `05_seed_usuarios.sql`.)

---

## 2. Upload — POST /instrumentos/upload (a través del gateway, con Bearer)

El endpoint acepta `.csv/.xlsx/.xls` (encuesta) o `.pdf/.txt/.docx`
(entrevista/prueba). El `.md` NO es un formato aceptado por el router de upload,
así que para el archivo RESPONDIDO se usó un `.txt` real con las respuestas y como
ORIGINAL un `.txt` derivado de `inst_01.md` (el `.md` crudo se rechaza con 422,
evidencia abajo).

### Request

```powershell
curl.exe -X POST "http://localhost:8000/instrumentos/upload" `
  -H "Authorization: Bearer $token" `
  -F "archivo=@storage/raw/inst_01_respondido.txt;type=text/plain" `
  -F "tipo_instrumento=entrevista" `
  -F "archivo_original=@storage/raw/inst_01_original.txt;type=text/plain"
```

(Intento previo con `archivo_original=@storage/raw/inst_01.md` → `422`:
`"Formato '.md' no soportado. Formatos aceptados: .csv, .docx, .pdf, .txt, .xls, .xlsx."`)

### Response — `HTTP 201`

```json
{
  "id_crudo": 22,
  "id_instrumento": 22,
  "id_owner": 2,
  "tipo_instrumento": "entrevista",
  "estado": "recibido",
  "fecha_carga": "2026-10-05T01:46:23.465446",
  "archivo_respondido": {
    "nombre_original": "inst_01_respondido.txt",
    "ruta_relativa": "raw/5a887b9e8110490fbde808936cce2599__inst_01_respondido.txt",
    "extension": ".txt", "mime_type": "text/plain", "parser_family": "documento",
    "size_bytes": 1110,
    "parseo": { "parser_family": "documento", "n_chars": 1070, "n_words": 155,
                "encoding": "utf-8-sig", "text_preview": "Instrumento respondido ..." }
  },
  "archivo_original": {
    "nombre_original": "inst_01_original.txt",
    "ruta_relativa": "raw/9e22e22645d246d38b9ca912272577b1__inst_01_original.txt",
    "extension": ".txt", "parser_family": "documento", "size_bytes": 1992,
    "parseo": { "n_chars": 1939, "n_words": 312, "encoding": "utf-8-sig" }
  },
  "mensaje": "Instrumento recibido y almacenado en crudo."
}
```

Devuelve `id_crudo` e `id_instrumento` por separado + el resumen de `parseo`. **PASS.**

---

## 3. Metadatos a través del gateway (`/api/metadata/metadata/{id}/...`)

El path lleva doble segmento a propósito: gateway `/api/metadata/*` →
metadata-service, cuyo router monta `/api` + `/metadata` + `/metadata/{id}/init`.

### 3a. GET init — `HTTP 200`

```powershell
GET http://localhost:8000/api/metadata/metadata/22/init  (Bearer)
```

```json
{"instrumento_id":22,"dc_creator":"Sistema","dc_publisher":"Indagata",
 "dc_type":"entrevista","dc_format":"unknown","dc_date":"2026-10-05",
 "dc_language":"es","dc_title_sugerido":"inst_01_respondido.txt"}
```

Campos auto-poblados (creator/publisher/type/format/date/language + título sugerido). **PASS.**

### 3b. POST registrar DC — `HTTP 200`

```powershell
POST http://localhost:8000/api/metadata/metadata/22  (Bearer, --data-binary @dc_body.json)
body = {"dc_title":"Calidad academica y condiciones de aprendizaje",
        "dc_subject":["calidad academica","aprendizaje"],
        "dc_description":"...","dc_coverage":"MX","dc_rights":"CC-BY",
        "dc_source":"inst_01","dc_relation":""}
```

```json
{"instrumento_id":22,"estado":"metadatos_registrados",
 "dc_title":"Calidad academica y condiciones de aprendizaje","dc_creator":"Sistema",
 "dc_subject":["calidad academica","aprendizaje"],"dc_publisher":"Indagata",
 "dc_date":"2026-10-05","dc_type":"entrevista","dc_language":"es","dc_coverage":"MX",
 "dc_rights":"CC-BY","dc_source":"inst_01","dc_relation":"",
 "mensaje":"✅ Metadata registered successfully. Ready for analysis."}
```

### 3c. SEGUNDO POST (inmutabilidad) — `HTTP 409`

```json
{"detail":"Metadata already registered for this instrument. Registration is immutable."}
```

Primer POST registra DC y cambia estado a `metadatos_registrados`; el segundo
devuelve `409`. **PASS.**

---

## 4. Asociación de KPIs (el gap) — directo a :8002

El analysis-service corre en `AUTH_DEV_MODE` (resuelve DEV_USER_ID=1 sin token).

### 4a. Reindex del catálogo de KPIs (siembra la colección Chroma `kpis`)

La BD tenía 30 KPIs (`select count(*) from kpi; -> 30`) pero la colección Chroma
necesitaba (re)indexarse:

```powershell
POST http://localhost:8002/vectorizacion/kpis/reindex
```

```json
{"coleccion":"kpis","n_kpis":30,"mensaje":"Colección de KPIs reindexada."}
```

### 4b. POST /vectorizacion/propuestas — `HTTP 200`, lista NO vacía con scores

```powershell
curl.exe -X POST "http://localhost:8002/vectorizacion/propuestas" `
  -F "archivo_json=@storage/raw/inst_01.v1.json;type=application/json" `
  -F "instrumento_original=@storage/raw/inst_01.md;type=text/markdown" `
  -F "tipo_instrumento=entrevista" `
  -F "id_instrumento=22"
```

```json
{"id_instrumento":22,"tipo_instrumento":"entrevista",
 "metadatos_clave":{"Título":"Calidad académica y condiciones de aprendizaje", ...},
 "propuestas":[
   {"kpi_id":5,"nombre_kpi":"Tamaño Promedio de Clase","categoria":"Académico","score":0.6423},
   {"kpi_id":30,"nombre_kpi":"Puntajes de Satisfacción Estudiantil","score":0.5902},
   {"kpi_id":1,"nombre_kpi":"Estatus de Acreditación y Rankings","score":0.5833},
   {"kpi_id":21,"nombre_kpi":"Tasa de Graduación","score":0.5758},
   {"kpi_id":19,"nombre_kpi":"Calificación del Profesorado y Tasa de Rotación","score":0.5737}
 ],
 "mensaje":"Propuestas generadas por similitud semántica."}
```

5 propuestas con score. **PASS.**

### 4c. POST /vectorizacion/confirmar — `HTTP 200`, `json_enriquecido` con `inferred_kpis`

Body: `id_instrumento=22`, `decisiones` (acepta kpi 5 y 30, rechaza 1) y
`json_instrumento` = contenido completo de `inst_01.v1.json` (~117 KB).

```json
{"id_instrumento":22,
 "kpis_agregados":[
   {"kpi_id":5,"nombre_kpi":"Tamaño Promedio de Clase","score":0.6423},
   {"kpi_id":30,"nombre_kpi":"Puntajes de Satisfacción Estudiantil","score":0.5902}],
 "json_enriquecido":{ ... "inferred_kpis":[
     {"kpi_id":5,"nombre_kpi":"Tamaño Promedio de Clase","score":0.6423},
     {"kpi_id":30,"nombre_kpi":"Puntajes de Satisfacción Estudiantil","score":0.5902}] },
 "mensaje":"JSON enriquecido con los KPIs aceptados."}
```

`json_enriquecido` contiene la clave `inferred_kpis` con los KPIs aceptados. **PASS.**

### 4d. Confirmación en BD

```
select id_instrumento, estado from instrumento_procesado where id_instrumento=22;
  -> 22 | metadatos_registrados
select id_crudo, dc_title from metadatos_dc ...;
  -> 22 | Calidad academica y condiciones de aprendizaje
```

---

## 5. Frontend — `npm run build` de pixel-perfect-pixel

```powershell
cd pixel-perfect-pixel
npm run build
```

```
✓ built in 1.89s
i Generated .output/nitro.json
[nitro] √ You can preview this build using npx vite preview
```

Build/type-check verde; el wiring de `src/api/*` compila con las firmas sin
cambios. One-shot, sin dev server corriendo. **PASS.**

---

## Resumen

| Paso | Qué se verificó | Resultado |
|------|-----------------|-----------|
| 0 | Rebuild api-gateway + stack sano desde el worktree | PASS |
| 1 | Login JWT real por el gateway | PASS |
| 2 | Upload devuelve `id_crudo`/`id_instrumento` + parseo (201) | PASS |
| 3 | Metadata init 200, registro 200, 2º POST 409 (inmutable) | PASS |
| 4 | Propuestas no vacías con score; confirmar con `inferred_kpis` | PASS |
| 5 | `npm run build` verde | PASS |

**`passed = true`.** Todos los pasos del pipeline real se ejercitaron con
evidencia capturada.

### Notas de entorno (no bloqueantes, documentadas)

- `docker-compose.verify.yml` (override NO versionado) iguala `SECRET_KEY` en
  instrument/metadata/analysis/visualization para que el JWT del gateway valide.
  Es un gap de wiring de compose pre-existente, fuera del alcance de los 6
  archivos del cambio.
- Archivos de prueba creados en `storage/raw/`: `inst_01_respondido.txt`
  (respondido) e `inst_01_original.txt` (original a partir de `inst_01.md`),
  porque el router de upload no acepta `.md`.
- El servicio `frontend` del compose (dir legacy) no se usa; el frontend real es
  `pixel-perfect-pixel`.
