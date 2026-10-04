# Plan de implementación — INDAGATA (universidad + rediseño del panel)

Proyecto: `pixel-perfect-pixel` (TanStack Start + React 19 + Tailwind v4, español, sin backend, datos simulados).
Reglas aplicadas (AGENTS.md): las pantallas nunca importan `src/mocks/` directo (todo pasa por `src/api/`), colores/tipografía/sombras solo como tokens semánticos de `src/styles.css` (nada de clases de color literales), todo en español. NO tocar `src/routes/login.tsx` salvo que un cambio de tipos lo obligue (no lo obliga: login no usa niveles). NO cambiar los valores de color existentes de `src/styles.css`; se pueden AÑADIR tokens/utilidades nuevas.

## Hallazgos de toolchain (línea base real, verificados en exploración)

- `bun` 1.4.2 disponible. Scripts: `bun run build` (vite build), `bunx eslint src`.
- **`bun run build` → exit 0** en el estado actual: ESTE es el gate verde. El build es transpile-only (rolldown), no hace typecheck completo.
- **`bunx tsc --noEmit` arroja 10 errores PREEXISTENTES** (chat.ts, instrumentos.ts, GraficasKpi.tsx, FormularioContexto.tsx línea 36, ArmarInvestigacionPage.tsx) porque el tsconfig es estricto (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) pero el build no lo exige. Por tanto "typecheck sin errores" NO puede significar un `tsc` limpio: el gate alcanzable es **no introducir errores NUEVOS más allá de esa línea base**, y `bun run build` exit 0.
  - Nota: `FormularioContexto.tsx:36` compara `nivel !== ""` y hoy ya es un error TS2367 preexistente. Al reducir la lista de niveles este error sigue siendo del mismo tipo; mantenerlo igual (no es regresión) o, si se toca ese archivo en el Cambio 2, se puede simplificar (ver FEAT-002).
- **`bunx eslint src` arroja ~7330 errores PREEXISTENTES**, casi todos `prettier/prettier "Delete ␍"`: el repo tiene `core.autocrlf=true` sin `.gitattributes`, así que en Windows el checkout es CRLF y prettier espera LF. Son ruido local de fin de línea, NO del contenido. Al filtrarlos quedan solo **9 warnings** `react-refresh/only-export-components` (preexistentes, son warnings, no errores).
  - Gate de lint alcanzable: ejecutar **`bunx eslint src --fix`** (normaliza a LF) y confirmar que **no quedan errores**; los 9 warnings `react-refresh/only-export-components` son preexistentes y aceptables. Tras `--fix` los archivos quedan en LF (que es como están en el repo), así no se ensucian commits con cambios de EOL masivos.

---

## (a) Decisión de niveles universitarios

**Se elige `NIVELES_EDUCATIVOS = ["Licenciatura", "Posgrado"] as const`.**

Porqué: ambos son educación universitaria (cumple "solo universidad") y aportan DOS categorías, lo que mantiene con sentido todo lo que ya existe y agrupa "por nivel": el filtro de nivel en `Mis instrumentos`, el selector de cobertura Dublin Core en `Subir instrumento`, el selector de nivel en el contexto del `Chat`, la razón "Mismo nivel" de `buscarRelacionados`, y sobre todo la **gráfica de barras "Por nivel educativo"** de KPIs (`src/api/kpis.ts` → `porNivel`), que con un único valor "Universidad" quedaría con una sola barra y perdería sentido. Con dos niveles la UI sigue siendo interesante sin reorientar gráficas ni filtros. El código consume el nivel de forma genérica (se muestra como string y se compara por igualdad; nunca hay nombres de nivel hardcodeados en lógica fuera de los mocks), así que cambiar los valores de la lista es seguro.

---

## (b) Cambio 1 — reorientar datos a investigación universitaria (archivo por archivo)

Reparto de niveles nuevos para los 15 instrumentos (mezcla equilibrada Licenciatura/Posgrado para que las gráficas tengan variedad): ins-01, ins-03, ins-05, ins-07, ins-09, ins-11, ins-13, ins-15 → **Licenciatura**; ins-02, ins-04, ins-06, ins-08, ins-10, ins-12, ins-14 → **Posgrado**. (El reparto exacto puede ajustarse; lo esencial es que ambos niveles queden representados y que título/descripción sean coherentes con el nivel asignado.)

### 1. `src/types/index.ts`
- Reemplazar el array `NIVELES_EDUCATIVOS` por `["Licenciatura", "Posgrado"] as const`. El `type NivelEducativo` se deriva solo. No cambian las interfaces (`Instrumento.nivel`, `DublinCore.cobertura`, `ContextoInvestigacion.nivel` siguen tipados por `NivelEducativo`).

### 2. `src/mocks/data.ts` (todas las ocurrencias de niveles básicos a universitario)
- `investigaciones`: `res-1 "Lectura en primarias rurales"` → tema universitario (p. ej. "Comprensión lectora en licenciatura"); `res-2 "Deserción en media superior"` → "Deserción en licenciatura"; `res-3 "Formación docente inicial"` se mantiene o se reorienta a posgrado docente.
- `instrumentos` (los 15): cambiar cada `nivel` al valor nuevo del reparto y reescribir títulos/descripciones/etiquetas que citen niveles básicos:
  - ins-01 "…lectura en primaria" → contexto licenciatura; descripción "alumnos de 3º a 6º" → estudiantes universitarios.
  - ins-03 "…nivel básico" → nivel universitario.
  - ins-05 "Guía de observación de juego libre" (nivel Preescolar) → reescribir a un instrumento universitario (p. ej. observación de prácticas en aula universitaria / tutorías).
  - ins-06 etiqueta `"bachillerato"` → etiqueta universitaria (p. ej. "licenciatura").
  - ins-08 (Secundaria, "álgebra temprana") → razonamiento cuantitativo universitario.
  - ins-09 "acompañamiento familiar / madres, padres y cuidadores / tareas escolares" → reorientar a acompañamiento académico universitario (tutoría/mentoría).
  - ins-12 "Prueba de lenguaje oral en preescolar", descripción "niñas y niños de 4 a 6 años" → reescribir por completo a un instrumento universitario (p. ej. competencias comunicativas en licenciatura).
  - ins-14 "directores escolares / gestión en la escuela" → gestión/liderazgo académico universitario.
  - Revisar el resto para que título↔nivel sean coherentes.
- `kpis` (resumen): `kpi-8 { etiqueta: "Nivel más cubierto", valor: "Primaria" }` → `valor: "Licenciatura"` (coherente con el reparto). Revisar que los conteos de `kpi-1..kpi-7` sigan teniendo sentido (15 instrumentos, 9 estandarizados, etc. no cambian).
- `noticias`: `not-2 "educación media superior"` → "educación superior/universitaria"; `not-4 "pruebas de lenguaje en preescolar"` → noticia universitaria coherente.
- `catalogoKpis` (reorientar marcos de educación básica a educación superior):
  - cat-01: `infoGeneral` "Plan de Estudios 2022 (SEP) y los marcos de PISA/PIRLS. Aplicable desde tercer grado de primaria." → marcos de educación superior (p. ej. lectura académica/alfabetización informacional en universidad); etiqueta `"primaria"` → "licenciatura".
  - cat-03: `infoGeneral` "ENLACE y PLANEA" → marcos de evaluación de aprendizajes en educación superior (p. ej. EGEL/CENEVAL o rúbricas institucionales).
  - cat-06: `comoSeMide` "nivel preescolar y primaria" + `infoGeneral` CASEL → competencias socioemocionales en estudiantes universitarios; etiqueta `"preescolar"` → "universidad".
  - cat-07: `infoGeneral` "validada con estudiantes de bachillerato" → "estudiantes universitarios"; etiqueta `"bachillerato"` → "licenciatura".
  - cat-08: etiqueta `"primaria"` → "universidad" y reorientar "madres, padres y cuidadores / hijos" a acompañamiento académico universitario, o re-tematizar el KPI a algo propio de universidad.
  - cat-11 "Desarrollo del lenguaje" (todo preescolar: "niños de preescolar", "4-6 años", "éxito lector en primaria") → **reescribir el KPI completo** a uno universitario (p. ej. "Competencias comunicativas" o "Alfabetización académica"), ya que ins-12 también cambia; mantener `id: "cat-11"` e `icono`.
  - cat-12: etiqueta `"primaria"` → "universidad"; reorientar "director escolar" a gestión académica universitaria si procede.
  - cat-13: `infoGeneral` "PISA… desde 1° de secundaria" → marco universitario; etiqueta `"secundaria"` → "licenciatura".
  - cat-15 "Clima escolar": `comoSeMide`/`infoGeneral` "estudiantes de secundaria" → "estudiantes universitarios"; etiqueta `"secundaria"` → "universidad".
  - IMPORTANTE: los campos `nombre` del catálogo que aparecen en `instrumento.kpis` deben seguir coincidiendo; si se renombra `cat-11`, actualizar también `kpis: [...]` de los instrumentos que lo referencian (ins-12) para que `getDatosGrafica` siga encontrando coincidencias.

### 3. `src/mocks/carga.ts`
- `reporteLimpiezaEjemplo.cambios`: la fila `{ campo: "Texto", antes: "  secundaria ", despues: "Secundaria" }` → ejemplo universitario (p. ej. `antes: "  licenciatura ", despues: "Licenciatura"`). Opcional: `"Edad del Alumno"`/`"ESCUELA(Clave)"` son neutrales, se pueden dejar.
- `kpisSugeridosEjemplo`: ítem `"Distribución por nivel educativo"` sigue válido; revisar que ningún texto cite nivel básico (no lo hace).

### 4. `src/api/chat.ts`
- `CONTINUACIONES`: reescribir las frases que citan niveles básicos: "patrones consistentes en distintos niveles educativos" (ok, genérico), "entre primaria urbana y rural" → "entre licenciatura y posgrado" o "entre distintos programas universitarios"; "varía según el nivel y la zona geográfica" (ok). Dejar el tono coherente con investigación universitaria.

### 5. Verificación de que no quedan referencias
- `grep` case-insensitive en `src/**/*.{ts,tsx}` de `preescolar|primaria|secundaria|media superior|bachiller|niñ[oa]s?|PISA|PIRLS|ENLACE|PLANEA|CASEL`: debe devolver **0** resultados en archivos de datos/API (los nombres de componentes y comentarios genéricos no cuentan). Confirmar que `src/types/index.ts` ya no contiene los niveles antiguos.

**Verify Cambio 1:** `bun run build` → exit 0, y la UI (filtros, selector Dublin Core, contexto de chat, barras "por nivel" de KPIs) muestra Licenciatura/Posgrado. `bunx eslint src --fix` sin errores (solo los 9 warnings preexistentes).

---

## (c) Cambio 2 — pulir el interior del panel (apartado por pantalla)

Estilo objetivo (igual al login aprobado): navy `--primary` + crema `--accent-soft`, `font-display` (Poppins) en títulos, `font-sans` (Nunito) en texto, bordes redondeados generosos (`rounded-2xl`/`rounded-3xl`/`rounded-4xl`), sombras `shadow-card`/`shadow-soft`/`shadow-elevated`. Reutilizar primitivos de `src/components/ui/` (Button, Card, Badge, Input, Label, Select, Tabs, ToggleGroup, Separator, etc.); NO crear primitivos nuevos. Accesibilidad: foco visible, labels, roles ARIA, contraste; responsivo md/lg. Solo tokens semánticos, nada de clases de color literales.

Si el rediseño necesita utilidades nuevas (p. ej. un patrón de encabezado reutilizable o un token de espaciado), AÑADIRLAS a `src/styles.css` sin alterar los valores existentes. Se puede crear un pequeño componente compartido de encabezado de página en `src/components/layout/` (p. ej. `PageHeader.tsx` con título `font-display` + subtítulo) para unificar jerarquía; es un componente de layout, no un primitivo de color.

### Layout global
- `src/components/layout/Sidebar.tsx`: reemplazar `rounded-xl` sueltos y estados hover por un patrón acorde al navy; estado activo con `bg-sidebar-accent`/`text-sidebar-accent-foreground` ya existe — reforzar con indicador (barra lateral o icono), foco visible (`focus-visible:ring`), y marca INDAGATA con tipografía display. Mantener `aria-current` del `Link` activo.
- `src/components/layout/Header.tsx`: alinear alturas y espaciados, avatar/nombre con jerarquía clara, `ResearchSelector` integrado; sombra `shadow-card` en el borde inferior.
- `src/components/layout/ResearchSelector.tsx`: revisar (leer antes de tocar) para que el selector de investigación activa use Select/Badge con tokens.
- `src/components/layout/PagePlaceholder.tsx`: ya usa `rounded-2xl`/`shadow-card`; alinear al nuevo `PageHeader` si se crea.

### Mis instrumentos (`src/features/instruments/`: InstrumentosPage, FiltrosPanel, ChipsFiltros, TablaInstrumentos, VistaRapida, TipoBadge, EstadoVacio, MenuDescarga, DialogoEliminar)
- Encabezado con `PageHeader` (título `font-display` + subtítulo), espaciados consistentes.
- Convertir el repositorio en navegable y profesional: `FiltrosPanel` con filtros tipo/nivel universitario/estado/año/búsqueda en `Card` con `shadow-soft`; añadir filtro por **estado** (`EstadoInstrumento`: Borrador/En revisión/Estandarizado) y por **año** (ya hay rango de fechas; mantener o cambiar a año) — esto requiere extender `Filtros`/`aplicarFiltros` en `filtros.ts` y los chips en `ChipsFiltros.tsx`.
- Tarjetas/filas con `Badge` por tokens (tipo con `TipoBadge`, estado con color semántico via tokens), `rounded-2xl`, hover accesible. `EstadoVacio` cuidado (icono en círculo `bg-primary-soft`, texto claro). Mantener `TablaInstrumentos` o migrar a tarjetas si mejora la lectura; decidir una sola opción (recomendado: tabla en lg, tarjetas en md).

### Subir instrumento (`src/features/upload/`: UploadWizard, Stepper, StepArchivo, StepLimpieza, StepDublinCore, StepMetadatosTipo, JsonPreview, StepKpis, StepGuardar)
- `Stepper.tsx` moderno con progreso visual (barra/segmentos con `--primary`, paso actual destacado, pasos completados con check), accesible (`aria-current="step"`).
- `UploadWizard`: encabezado con `PageHeader`, tarjeta del paso con `rounded-3xl`/`shadow-card`, footer de navegación consistente. Pulir cada Step (Dublin Core, limpieza, KPIs sugeridos, guardar) con jerarquía y espaciados; el selector de cobertura ya muestra los niveles nuevos.

### Armar investigación (`src/features/research/`: ArmarInvestigacionPage, Stepper, Paso1Seleccion, Paso2Relacionados, Paso3Revision, ResearchContext)
- Reusar el `Stepper` pulido. Organización clara de los 3 pasos, tarjetas de instrumento con badges por tokens, estados de carga ("buscando relacionados") cuidados, revisión final legible.

### Chat (`src/features/chat/`: ChatPage, BarraEntrada, BurbujaMensaje, ChipsFuentes, EstadoVacioChat, FormularioContexto, PanelNoticias)
- Burbujas pulidas (usuario vs asistente con tokens `--primary`/`--muted`, `rounded-2xl`), estado "generando" cuidado (cursor/puntos animados accesible, `aria-live`), `ChipsFuentes`/`PanelNoticias` legibles con `Card`/`shadow-soft`, `BarraEntrada` con `Input`/`Select` de modelo y foco visible.
- `FormularioContexto`: el selector de nivel ahora muestra Licenciatura/Posgrado. Oportunidad de limpiar el error TS preexistente de `nivel !== ""` (tipar el estado como `NivelEducativo | ""` ya está; la comparación `nivel !== ""` da TS2367 por el union — se puede evitar comprobando `nivel.length > 0` o `Boolean(nivel)`). No es obligatorio pero mejora la línea base.

### KPIs (`src/features/kpis/`: KpisPage, TarjetaKpi, DetalleKpi, GraficasKpi)
- Tira de **tarjetas de métrica** arriba (consumir `getKpis()` de `src/api/kpis.ts`, que hoy no se usa en la pantalla) con variación (↑/↓) y tokens; `TarjetaKpi` del catálogo pulida.
- Gráficas `recharts` usando `--chart-1..5` (ya lo hacen) dentro de `Card` con `shadow-card`; dashboard con jerarquía (`PageHeader`, separadores), estados vacíos cuidados. La barra "Por nivel educativo" mostrará Licenciatura/Posgrado.

**Verify Cambio 2:** `bun run build` → exit 0; `bunx eslint src --fix` sin errores nuevos (solo los 9 warnings preexistentes `react-refresh/only-export-components`); revisión visual de que todas las pantallas usan tokens (grep de clases de color literales `bg-(blue|slate|gray|red|green)-|text-\[#|bg-\[#` debe dar 0 en `src/`); login intacto (`git diff --stat src/routes/login.tsx` vacío salvo que un cambio de tipos lo exija — no lo exige).

---

## (d) Orden seguro para no romper la compilación en cascada

El riesgo es cambiar `NIVELES_EDUCATIVOS` y dejar datos con niveles viejos (que ya no son del tipo). Orden:

1. **Primero** `src/types/index.ts` (nueva lista) **junto con** `src/mocks/data.ts` y `src/mocks/carga.ts` en el mismo paso/commit: al reducir el union, todos los literales `nivel: "Primaria"|...` dejan de compilar hasta reemplazarlos. Hacerlo atómico mantiene el build verde.
2. Luego `src/api/chat.ts` y cualquier texto en `src/api/` (no afecta tipos, solo contenido).
3. Verificar `bun run build` exit 0 — todo el Cambio 1 cerrado.
4. **Después** el Cambio 2 (UI), que no cambia tipos y puede hacerse pantalla por pantalla dejando el build verde entre cada una. Si se crea `PageHeader` o utilidades en `styles.css`, hacerlo antes de usarlas.

Los componentes que leen `NIVELES_EDUCATIVOS` (`FiltrosPanel`, `FormularioContexto`, `StepDublinCore`) y los que muestran `ins.nivel` (Tabla/VistaRapida/Paso1/Paso2/Paso3) **no requieren cambios de código** para el Cambio 1: consumen la lista/los valores genéricamente. Solo cambian lo que muestran.

---

## (e) Recordatorio de verificación (gates del proyecto)

- `bun run build` → **exit 0** (gate principal; es transpile-only pero es el que exige el proyecto).
- `bunx eslint src --fix` → sin **errores** (normaliza EOL a LF; quedan solo 9 warnings preexistentes `react-refresh/only-export-components`). El `--fix` es necesario por `core.autocrlf=true` en Windows.
- Typecheck: no introducir errores NUEVOS respecto a la línea base de 10 errores preexistentes de `tsc --noEmit` (idealmente reducirlos). No existe gate de `tsc` limpio porque la línea base ya está sucia y el build no lo exige.
- Sin clases de color literales nuevas; sin importar `src/mocks/` desde pantallas; `src/routes/login.tsx` sin cambios; valores de color de `src/styles.css` intactos.
