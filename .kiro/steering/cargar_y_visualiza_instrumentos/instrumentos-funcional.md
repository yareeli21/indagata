---
inclusion: manual
---

# Instrumentos de Investigación — Especificación Funcional
**Versión:** 1.1  
**Fecha:** Agosto 2026  
**Alcance:** Pantalla de carga de instrumentos y pantalla de visualización/gestión

---

## 1. Contexto del módulo

El módulo de instrumentos es el punto de entrada de todo el sistema. Un instrumento de investigación es cualquier archivo que documenta una encuesta, entrevista o prueba estandarizada aplicada en un contexto educativo. El sistema recibe ese archivo, lo procesa y eventualmente lo convierte en conocimiento consultable mediante RAG.

Este documento cubre exclusivamente la experiencia del usuario en dos pantallas:
- **Pantalla de carga:** donde el investigador sube un instrumento y proporciona sus metadatos.
- **Pantalla de catálogo:** donde el investigador visualiza, filtra y gestiona instrumentos.

---

## 2. Actores

| Actor | Descripción |
|---|---|
| **Investigador** | Usuario autenticado que carga, gestiona y consulta instrumentos. Es el actor principal de todas las operaciones de usuario. |
| **Administrador** | Usuario con acceso sin restricciones. Puede ver todos los instrumentos independientemente de su visibilidad y reiniciar instrumentos en estado `error`. |
| **Sistema** | Procesos automáticos del pipeline (limpieza, estandarización, vectorización). No interactúa vía UI. |

> El sistema solo tiene dos roles de usuario: Investigador y Administrador. No existe el rol de Colaborador ni de Lector. Las reglas de visibilidad (público/privado) determinan qué investigadores pueden ver cada instrumento.

---

## 3. Casos de uso

### 3.1 Gestión de instrumentos propios

| ID | Actor | Descripción |
|---|---|---|
| CU01 | Investigador | Cargar un nuevo instrumento (archivo + metadatos obligatorios) |
| CU02 | Investigador | Editar los metadatos de un instrumento propio |
| CU03 | Investigador | Reemplazar el archivo de un instrumento propio (sobrescribe el anterior) |
| CU04 | Investigador | Cambiar la visibilidad de un instrumento (público / privado) |
| CU05 | Investigador | Eliminar un instrumento propio |

### 3.2 Visualización y descarga

| ID | Actor | Descripción |
|---|---|---|
| CU06 | Investigador | Consultar el catálogo de instrumentos accesibles |
| CU07 | Investigador | Filtrar instrumentos por texto, tipo, autor, visibilidad y rango de fechas |
| CU08 | Investigador | Ver el detalle completo de un instrumento |
| CU09 | Investigador | Descargar el archivo original del instrumento |
| CU10 | Investigador | Descargar el JSON canónico de un instrumento (disponible desde estado `estandarizado`) |
| CU11 | Investigador | Descargar el archivo `.sav` de una encuesta (disponible desde estado `estandarizado`, solo para tipo encuesta) |

### 3.3 Acciones del sistema (sin interacción directa del usuario)

| ID | Actor | Descripción |
|---|---|---|
| CU13 | Sistema | Ejecutar el pipeline de limpieza cuando un instrumento entra en estado `recibido` |
| CU14 | Sistema | Generar el JSON canónico al completar la estandarización (inferencia KPI + metadatos consolidados) |
| CU15 | Sistema | Generar el archivo `.sav` al completar la estandarización (solo encuestas) |

---

## 4. Pantallas

### 4.1 Pantalla de carga de instrumento

**Propósito:** Permitir al investigador subir un nuevo instrumento y registrar sus metadatos obligatorios en un único paso.

**Acceso:** Botón "Cargar instrumento" en la pantalla de catálogo.

**Principio de diseño:** Los metadatos no son opcionales. Todo instrumento debe tener contexto semántico suficiente desde el momento de la carga. El JSON canónico no puede existir sin ellos.

#### Sección 1 — Archivo y datos básicos

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| Archivo | File upload | Sí | Cualquier formato. Sin restricción de tipo MIME. |
| Nombre del instrumento | Texto libre | Sí | Nombre descriptivo. Máximo 255 caracteres. |
| Tipo de instrumento | Selector | Sí | Encuesta / Entrevista / Prueba estandarizada |
| Visibilidad | Toggle | No | Público / Privado. **Por defecto: Público.** |

#### Sección 2 — Metadatos Dublin Core obligatorios (13 campos)

Estos campos son obligatorios para poder cargar el instrumento. Sin ellos el sistema no puede garantizar la calidad semántica del conocimiento que representará.

| # | Campo Dublin Core | Equivalente semántico | Descripción |
|---|---|---|---|
| 1 | `dc_title` | Título | Nombre completo del instrumento |
| 2 | `dc_creator` | Autor/Creador | Persona o grupo que lo elaboró |
| 3 | `dc_subject` | Tema(s) | Lista de temas o palabras clave principales |
| 4 | `dc_description` | Descripción | Resumen del propósito del instrumento |
| 5 | `dc_publisher` | Institución responsable | Entidad que lo publicó o aplicó |
| 6 | `dc_contributor` | Colaboradores | Personas que contribuyeron (puede ser igual al creador) |
| 7 | `dc_date` | Fecha de aplicación | Cuándo fue aplicado (formato YYYY o YYYY-MM) |
| 8 | `dc_type` | Tipo de recurso | Encuesta / Entrevista / Prueba estandarizada |
| 9 | `dc_format` | Formato original | Formato del archivo original (PDF, DOCX, etc.) |
| 10 | `dc_identifier` | Identificador semántico | Código único legible (ej. IND-ENC-042) |
| 11 | `dc_language` | Idioma | Idioma del instrumento (ej. "es", "en") |
| 12 | `dc_coverage` | Cobertura / Población | Población o contexto geográfico de aplicación |
| 13 | `dc_rights` | Derechos | Condiciones de uso y acceso |

> `dc_identifier`, `dc_contributor` y `dc_format` pueden tener valores sugeridos automáticamente por el sistema, pero el investigador debe confirmarlos o ajustarlos.

#### Sección 3 — Metadatos específicos del instrumento (opcional en este paso)

El investigador puede completar la estructura interna del instrumento al cargar o después desde el detalle.

| Bloque | Aplica a | Campos principales |
|---|---|---|
| Específico encuesta | Encuesta | Escala de respuesta, metodología, dimensiones e ítems |
| Específico entrevista | Entrevista | Tipo, guión temático, perfil de entrevistados |
| Específico prueba | Prueba estandarizada | Áreas de competencia, escala, normas de referencia |

**Comportamiento al enviar:**
- El sistema valida los 13 campos Dublin Core obligatorios.
- Si alguno falta, muestra la lista de campos pendientes y no avanza.
- Si todos están presentes: guarda el archivo, registra el instrumento con estado `recibido`, y muestra el instrumento en el catálogo.
- El pipeline de limpieza se activa automáticamente en segundo plano.
- Al completar la limpieza, el sistema genera el JSON canónico automáticamente (sin acción adicional del usuario).

**Errores posibles:**

| Error | Mensaje |
|---|---|
| Archivo duplicado (mismo hash del mismo usuario) | "Ya tienes un instrumento con este archivo. Puedes subir una nueva versión desde el catálogo." |
| Campo nombre vacío | Validación en formulario, no llega al servidor. |
| Campos Dublin Core faltantes | "Faltan los siguientes campos obligatorios: [lista]." |

---

### 4.2 Pantalla de catálogo de instrumentos

**Propósito:** Mostrar todos los instrumentos accesibles al investigador autenticado y permitir su gestión.

**Visibilidad de instrumentos:**
- Un investigador ve todos los instrumentos públicos del sistema.
- Un investigador ve sus propios instrumentos privados.
- Un investigador **no** ve los instrumentos privados de otros.
- Un administrador ve todos los instrumentos sin restricción.

#### Barra de filtros

| Filtro | Tipo | Descripción |
|---|---|---|
| Búsqueda por texto | Campo de texto | Busca en el nombre del instrumento (búsqueda de texto completo) |
| Tipo de instrumento | Selector múltiple | Encuesta / Entrevista / Prueba estandarizada |
| Visibilidad | Selector | Todos / Solo míos / Solo públicos de otros |
| Autor | Campo de texto | Filtra por nombre de usuario del propietario |
| Fecha desde | Selector de fecha | Filtra instrumentos cargados a partir de esta fecha |
| Fecha hasta | Selector de fecha | Filtra instrumentos cargados hasta esta fecha |

> El filtro de fecha aplica sobre la fecha de carga del instrumento (`creado_en`), no sobre el periodo de aplicación del instrumento. El rango puede usarse con solo uno de los dos extremos.

#### Tabla de resultados

| Columna | Descripción |
|---|---|
| Nombre | Nombre del instrumento. Enlace al detalle. |
| Tipo | Encuesta / Entrevista / Prueba |
| Propietario | Nombre de usuario que lo cargó |
| Estado | Badge visual con color por estado (ver tabla siguiente) |
| Versión | Número de versión actual |
| Fecha de carga | `creado_en` del instrumento |
| Visibilidad | Ícono público / privado |
| Acciones | Descargar archivo · Ver detalle · **Editar (solo propietario)** · Eliminar (solo propietario) |

#### Estados con indicación visual

| Estado | Color sugerido | Descripción para el usuario |
|---|---|---|
| Recibido | Gris | El archivo fue recibido. Procesando contenido en segundo plano. |
| Limpio | Amarillo | Texto procesado. Preparando análisis de indicadores. |
| Estandarizado | Naranja | Análisis completado. JSON canónico disponible. |
| Vectorizado | Azul | Listo para consulta en el sistema RAG. |
| Error | Rojo | Ocurrió un problema en el procesamiento. |

---

### 4.3 Pantalla de detalle del instrumento

**Propósito:** Ver toda la información de un instrumento y acceder a los artefactos descargables.

#### Sección de cabecera

- Nombre, tipo, propietario, estado (badge), versión, fecha de carga, visibilidad.
- Si el investigador es el propietario: botón "Editar metadatos" y botón "Reemplazar archivo".

#### Sección: Metadatos Dublin Core

Muestra los 13 campos obligatorios y los opcionales (`dc_source`, `dc_relation`). El propietario puede editarlos.

#### Sección: Metadatos específicos del instrumento

Muestra el bloque `especifico` según el tipo. El propietario puede editarlo en cualquier momento.

#### Sección: Información del procesamiento

Visible para el propietario (y el administrador):

| Campo | Descripción |
|---|---|
| Estado actual | Estado en la máquina de estados |
| Última actualización | Timestamp del último cambio de estado |
| Error (si aplica) | Mensaje amigable si estado = `error` (campo `error_detalle`) |

> El sistema no expone en la interfaz información técnica del pipeline (modelo LLM, extractor, versión de prompt, tokens). Esos datos son exclusivos del monitoreo interno.

#### Sección: Artefactos descargables

| Artefacto | Disponible desde estado | Disponible para | Botón |
|---|---|---|---|
| Archivo original | `recibido` (siempre) | Cualquier investigador con acceso | "Descargar archivo original" |
| JSON canónico | `estandarizado` | Cualquier investigador con acceso | "Descargar JSON canónico" |
| Archivo `.sav` | `estandarizado` (solo encuestas) | Cualquier investigador con acceso | "Descargar .sav (SPSS)" |

#### Sección: Versiones

Esta sección no existe. El sistema no mantiene historial de versiones del archivo. El sistema siempre tiene la versión más reciente. Si se reemplaza el archivo, el anterior se elimina del disco.

---

## 5. Flujos de usuario

### 5.1 Flujo completo — Investigador carga un instrumento nuevo

```
1. El investigador abre la pantalla de catálogo.
2. Hace clic en "Cargar instrumento".
3. Selecciona el archivo desde su dispositivo.
4. Escribe el nombre del instrumento.
5. Selecciona el tipo (encuesta, entrevista, prueba).
6. La visibilidad está en "Público" por defecto. Puede cambiarla a "Privado".
7. Completa los 13 campos Dublin Core obligatorios.
8. Opcionalmente, completa los metadatos específicos del instrumento.
9. Hace clic en "Cargar".
10. El sistema valida todos los campos obligatorios.
    Si faltan campos: muestra la lista y detiene el proceso.
11. El sistema guarda el archivo y registra el instrumento con estado "Recibido".
12. El instrumento aparece en el catálogo con badge gris ("Recibido").
13. En segundo plano: el pipeline extrae y limpia el texto del archivo.
14. El estado cambia a "Limpio" automáticamente.
    El investigador lo ve actualizado al refrescar o vía polling del frontend.
15. El pipeline de estandarización infiere KPIs y genera el JSON canónico.
16. El estado cambia a "Estandarizado". JSON canónico y .sav (si es encuesta) disponibles.
17. El pipeline de vectorización continúa hacia "Vectorizado".
```

### 5.2 Flujo — Investigador reemplaza el archivo

```
1. El investigador entra al detalle y hace clic en "Reemplazar archivo".
2. Selecciona el nuevo archivo.
3. El sistema calcula el hash del nuevo archivo.
   Si es idéntico al actual: muestra error "El archivo es idéntico al actual".
4. El archivo anterior se elimina del disco.
5. El nuevo archivo se guarda en storage/raw/.
6. El instrumento regresa a estado "Recibido".
7. El JSON canónico anterior se elimina del disco.
8. El .sav anterior se elimina si existe.
9. Los metadatos Dublin Core se conservan.
10. El pipeline de limpieza se activa automáticamente.
11. Al completar la estandarización, el JSON canónico se regenera con los metadatos existentes.
```

### 5.3 Flujo — Investigador consulta el catálogo

```
1. El investigador navega a la pantalla de catálogo.
2. Ve todos los instrumentos públicos y sus propios instrumentos privados.
3. Aplica filtros opcionales (texto, tipo, visibilidad, autor, rango de fechas).
4. Hace clic en un instrumento para ver su detalle.
5. Puede descargar el archivo original siempre.
   Puede descargar el JSON canónico y el .sav desde estado estandarizado (el .sav solo si es encuesta).
6. Si es el propietario: puede editar metadatos, cambiar visibilidad, subir nueva versión o eliminar.
7. Si no es el propietario: solo puede ver y descargar (si el instrumento es público).
```

### 5.4 Flujo — Instrumento en error

```
1. El instrumento entra en estado "Error" por fallo del pipeline.
2. El investigador ve el badge rojo en el catálogo.
3. Entra al detalle y lee el mensaje de error en la sección de procesamiento.
4. Si el error es por archivo no procesable: puede subir una nueva versión con un archivo diferente.
5. Si el error es por fallo técnico del sistema: el administrador puede reiniciar el instrumento
   a estado "Recibido" para que el pipeline reintente.
```

### 5.5 Flujo — Investigador edita metadatos

```
1. El investigador entra al detalle de un instrumento propio.
2. Hace clic en "Editar metadatos".
3. Modifica los campos deseados (Dublin Core y/o específicos).
4. Guarda los cambios.
5. El JSON canónico en disco se actualiza inmediatamente.
6. Si el instrumento estaba en "Vectorizado": regresa a "Limpio" para forzar re-procesamiento.
7. El pipeline continúa desde "Limpio" hacia "Vectorizado" nuevamente.
```

---

## 6. Acciones disponibles por estado

| Estado | Acciones disponibles para el propietario | Acciones para otros investigadores (instrumento público) |
|---|---|---|
| Recibido | Ver detalle · Editar metadatos · Cambiar visibilidad | Ver detalle |
| Limpio | Ver detalle · Editar metadatos · Cambiar visibilidad · Reemplazar archivo | Ver detalle |
| Estandarizado | Ver detalle · Editar metadatos · Descargar JSON · Descargar .sav* · Cambiar visibilidad · Reemplazar archivo | Ver detalle · Descargar JSON · Descargar .sav* |
| Vectorizado | Ver detalle · Editar metadatos · Descargar JSON · Descargar .sav* · Cambiar visibilidad · Reemplazar archivo | Ver detalle · Descargar JSON · Descargar .sav* |
| Error | Ver detalle · Ver error · Reemplazar archivo · Cambiar visibilidad | Ver detalle (si es público) |

> \* Solo disponible para instrumentos de tipo **Encuesta**.

> Editar metadatos cuando el instrumento está en `vectorizado` regresa el estado a `estandarizado` para forzar re-vectorización.

---

## 7. Gestión de artefactos

### 7.1 Archivo original

- **Qué es:** El archivo tal como lo subió el investigador (PDF, DOCX, XLSX, TXT, CSV, etc.).
- **Cuándo existe:** Siempre, desde el primer cargue. Solo existe el archivo más reciente — no hay historial.
- **Quién puede descargarlo:** Cualquier investigador con acceso al instrumento (propietario, o cualquiera si es público).
- **Comportamiento:** `GET /instrumentos/{id}/descargar` devuelve el archivo actual del instrumento.
- **Al reemplazar:** el archivo anterior se elimina del disco. No hay recuperación del anterior.

### 7.2 JSON canónico

- **Qué es:** El documento estructurado que representa el conocimiento consolidado del instrumento. Contiene los metadatos Dublin Core, el contexto derivado y los KPIs inferidos. Las unidades semánticas se agregan en la vectorización.
- **Cuándo existe:** A partir del estado `estandarizado`. Lo genera el pipeline de estandarización al finalizar la inferencia de KPIs, consolidando los metadatos Dublin Core y los KPIs inferidos.
- **Quién puede descargarlo:** Cualquier investigador con acceso al instrumento.
- **Comportamiento:** `GET /instrumentos/{id}/json` devuelve el archivo JSON del disco.
- **Nota:** En estados `recibido` y `limpio` el JSON no existe todavía. No se muestra el botón de descarga en esos estados.

### 7.3 Archivo `.sav`

- **Qué es:** Representación del instrumento en formato SPSS, útil para análisis estadístico externo.
- **Cuándo existe:** Solo para instrumentos de tipo **encuesta**, a partir del estado `estandarizado`.
- **Quién puede descargarlo:** Cualquier investigador con acceso al instrumento.
- **Comportamiento:** `GET /instrumentos/{id}/sav` devuelve el archivo `.sav`.
- **Nota:** Para entrevistas y pruebas estandarizadas este artefacto no se genera ni se muestra en la interfaz.

---

## 8. Reglas de negocio

1. Un investigador no puede cargar el mismo archivo dos veces (mismo hash MD5 por usuario). Si intenta hacerlo, se le sugiere subir una nueva versión del instrumento existente.

2. Los 13 campos Dublin Core son obligatorios en el momento de la carga. Sin ellos el sistema rechaza la operación con la lista de campos faltantes.

3. Los 13 campos Dublin Core obligatorios son: `dc_title`, `dc_creator`, `dc_subject`, `dc_description`, `dc_publisher`, `dc_contributor`, `dc_date`, `dc_type`, `dc_format`, `dc_identifier`, `dc_language`, `dc_coverage`, `dc_rights`. Estos garantizan el ancla semántica completa para los embeddings.

4. El JSON canónico se genera automáticamente cuando el pipeline de estandarización termina (inferencia KPI completa). No requiere ninguna acción adicional del investigador.

5. El investigador puede editar los metadatos en cualquier estado. Si el instrumento está en `vectorizado`, la edición lo regresa a `estandarizado` para forzar re-vectorización.

6. Reemplazar el archivo siempre regresa el instrumento a `recibido`. El archivo anterior, el JSON canónico y el .sav se eliminan del disco. Los metadatos Dublin Core se conservan. No hay historial de archivos anteriores.

7. **La visibilidad por defecto es `público`.** El investigador puede cambiarla a `privado` si no desea que otros accedan al instrumento.

8. Un instrumento público es visible y descargable por cualquier investigador autenticado. Solo el propietario puede editarlo, cambiar su visibilidad, subir nuevas versiones o eliminarlo.

9. El archivo `.sav` solo se genera para instrumentos de tipo **encuesta**. Para entrevistas y pruebas estandarizadas no existe este artefacto.

10. No es posible eliminar un instrumento que está en estado `estandarizado` o `vectorizado` sin confirmación explícita, dado que puede haber procesamiento dependiente del JSON canónico.

---

## 9. Mensajes del sistema al investigador

| Situación | Mensaje sugerido |
|---|---|
| Carga exitosa | "Instrumento registrado. El contenido se procesará en segundo plano." |
| Archivo duplicado | "Ya tienes un instrumento con este archivo. Puedes subir una nueva versión desde el catálogo." |
| Campos DC faltantes al cargar | "Faltan los siguientes campos obligatorios: [lista de campos]." |
| Estado cambia a Limpio | "El contenido del instrumento fue procesado. El análisis de indicadores continúa en segundo plano." |
| Error en el pipeline | "No se pudo procesar este instrumento: [mensaje de error]. Puedes intentar con una nueva versión del archivo." |
| Editar metadatos en vectorizado | "Editar los metadatos reiniciará la vectorización del instrumento desde el estado Estandarizado." |
| Instrumento eliminado | "El instrumento y todos sus artefactos han sido eliminados." |
| Archivo idéntico al subir versión | "El archivo es idéntico a la versión actual. Sube un archivo diferente." |

---

## 10. Permisos por rol — resumen visual

| Acción | Propietario | Otro investigador (instrumento público) | Otro investigador (instrumento privado) | Administrador |
|---|:---:|:---:|:---:|:---:|
| Ver instrumento | ✓ | ✓ | — | ✓ |
| Descargar archivo original | ✓ | ✓ | — | ✓ |
| Descargar JSON canónico | ✓ | ✓ | — | ✓ |
| Descargar .sav (encuestas) | ✓ | ✓ | — | ✓ |
| Editar metadatos | ✓ | — | — | ✓ |
| Reemplazar archivo | ✓ | — | — | — |
| Cambiar visibilidad | ✓ | — | — | — |
| Eliminar instrumento | ✓ | — | — | ✓ |
| Reiniciar instrumento en error | — | — | — | ✓ |
