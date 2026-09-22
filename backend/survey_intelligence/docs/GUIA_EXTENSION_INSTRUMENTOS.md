# Guía de extensión: cómo agregar reglas por instrumento al SIS

> **Qué es este documento:** el procedimiento concreto para añadir o ampliar la lógica específica
> de un tipo de instrumento en el SIS **sin tocar el núcleo común ni romper los otros tipos**.
> Cubre los dos casos abiertos: **entrevistas** (ya implementado — sirve de plantilla) y **pruebas
> estandarizadas** (esqueleto — pendiente de definir sus reglas).
> **Base:** la arquitectura de `ARQUITECTURA_SIS.md` (facade + `pipelines/` + `engine/` + `contracts/`).

---

## 0. Regla de oro

Cada tipo de instrumento se encapsula en **su propia estrategia** (`pipelines/<tipo>.py`), con su
motor propio en `engine/` y su contrato de conocimiento en `contracts/`. El tronco común (S4..S9) y
el orquestador (`facade.py`) **no se modifican** para añadir un instrumento. Verificación obligatoria
en cada paso: `python -m survey_intelligence.tests.run_all` verde + arranque de la app en 200.

---

## 1. Dónde vive cada cosa (los tres puntos de extensión)

Para un tipo de instrumento `<T>`, la lógica específica se reparte en tres lugares:

1. **Estrategia** — `survey_intelligence/pipelines/<T>.py`
   Implementa `InstrumentPipeline` (`build_canonical` + `analyze`). Es el único punto que el facade
   invoca. Compone stages y motores; no reimplementa nada del tronco común.
2. **Motor** — `survey_intelligence/engine/<dominio>/`
   Las funciones determinísticas y prompts propios del instrumento (p. ej. `engine/nlp/` para
   entrevistas). Deben ser puras/testeables de forma aislada.
3. **Contrato de conocimiento** — `survey_intelligence/contracts/<T>.py`
   El modelo Pydantic (frozen, `extra="forbid"`) de la cara de conocimiento del instrumento
   (p. ej. `contracts/interview.py`). Se expone como campo **opcional** del `SurveyIntelligenceResult`.

Además, para que el análisis llegue al usuario final:

4. **Consolidado (host)** — `api/services/carga_artifacts.py :: _generar_json_consolidado`
   Añade la sección de conocimiento del instrumento al JSON consolidado (aditivo), y el caché en
   `api/services/carga_sis_mapping.py` si el análisis se genera en `analyze` y se materializa después.

---

## 2. Pasos para agregar/ampliar un instrumento

1. **Contrato primero.** Define/actualiza `contracts/<T>.py` con la cara de conocimiento (frozen,
   campos opcionales). Si va al resultado, añade el campo opcional en `contracts/result.py`
   (espejo de `interview_analysis`). Contratos aditivos → subir *minor* de `SCHEMA_VERSION`.
2. **Motor aislado + tests.** Implementa las funciones puras en `engine/<dominio>/` y cúbrelas con
   un test dedicado en `tests/` (registrado en `run_all`). Debe pasar antes de cablear.
3. **Estrategia.** En `pipelines/<T>.py`, implementa `build_canonical` (reusa `_document.py` si es
   documental) y `analyze` (llama a tu motor; degrada sin lanzar). Devuelve `InstrumentAnalysis`
   con tu cara de conocimiento.
4. **Registro.** Añade la estrategia al mapa de `pipelines/__init__.py :: _PIPELINES`.
5. **Consolidado.** Extiende `_generar_json_consolidado` (host) para emitir tu sección, de forma
   aditiva. No rompas las secciones de encuesta/entrevista existentes.
6. **Verifica.** Suite verde + arranque 200. Añade una fixture representativa del instrumento.

---

## 3. Entrevistas (plantilla ya implementada)

Sirve como ejemplo canónico de los tres puntos de extensión. Todo esto YA existe:

- **Estrategia:** `pipelines/entrevista.py` (`EntrevistaPipeline`).
  - `build_canonical`: vía documental compartida (`_document.py`): el host ya extrajo el texto;
    S1 valida que haya texto, S2 documental lo segmenta, S3 se salta.
  - `analyze`: **S10** `run_interview_analysis` — capa determinística (diarización → participantes
    y turnos) + capa LLM (temas, hallazgos, patrones, citas, resúmenes), degradable.
- **Motor:** `engine/nlp/diarization.py` (participantes/turnos por etiquetas de hablante) +
  `engine/nlp/interview_prompt.py` (prompt + parseo con filtro anti-invención).
- **Contrato:** `contracts/interview.py` — `InterviewAnalysis`, `Participant`, `DialogueTurn`,
  `Theme`, `Finding`, `Pattern`, `Quote`, `ParticipantSummary`. Se expone como
  `SurveyIntelligenceResult.interview_analysis` (opcional).
- **Consolidado (host):** el análisis de entrevista se cachea en `analyze` y
  `_generar_json_consolidado` lo incorpora al JSON consolidado.

**Cómo ampliar entrevistas** (si hiciera falta): añadir campos al contrato (aditivos), enriquecer el
prompt/parseo en `engine/nlp/`, o añadir métricas determinísticas en `analyze`. Nunca se toca el
tronco común.

### Forma del conocimiento de entrevista en el consolidado (referencia)

Envoltorio común + un bloque `knowledge` específico. Ejemplo abreviado:

```jsonc
{
  "instrument_type": "entrevista",
  "metadata_dc": { /* 13 campos Dublin Core */ },
  "knowledge": {
    "participantes": [ { "participant_id": "entrevistado_01", "role": "entrevistado" } ],
    "temas":     [ { "theme_id": "t1", "titulo": "…", "turn_ids": [2,3] } ],
    "hallazgos": [ { "finding_id": "h1", "enunciado": "…", "evidence_turn_ids": [2,3], "confidence": 0.72 } ],
    "citas_relevantes": [ { "quote_id": "q1", "text": "…", "speaker_id": "entrevistado_01", "turn_id": 2 } ],
    "resumen_por_participante": [ { "participant_id": "entrevistado_01", "resumen": "…" } ],
    "resumen_general": "…"
  }
}
```

Cada hallazgo/tema/cita cita su evidencia (turno, participante) → trazable y chunkeable por el RAG.

---

## 4. Pruebas estandarizadas (esqueleto — pendiente de reglas)

**Estado actual (verificado en código):** `pipelines/prueba_estandarizada.py` existe y se comporta
igual que hoy — `build_canonical` documental (mismo que entrevista) y `analyze` **vacío** (sin
análisis específico). Recorre el tronco común, así que hoy una prueba se **ingiere como texto** pero
**no se interpreta psicométricamente**. El lugar para las reglas ya está reservado y marcado con
`TODO` en ese archivo.

> **Importante:** las reglas psicométricas concretas **aún no están definidas**. Este documento NO
> las inventa. Lo que sigue es solo el *procedimiento* para incorporarlas cuando el proceso de
> pruebas estandarizadas esté decidido.

### Cuando se definan las reglas, el trabajo será:

1. **Definir el proceso** (fuera del código): qué es una prueba estandarizada en Indagata, qué
   entrada tiene (¿solo el instrumento?, ¿claves de respuesta?, ¿respuestas de sujetos?), y qué
   conocimiento debe producir (métricas, interpretación, reporte).
2. **Contrato** — crear `contracts/psychometrics.py` con la cara de conocimiento (frozen). Añadir
   `psychometric_analysis: <Modelo> | None = None` a `SurveyIntelligenceResult` (aditivo).
3. **Motor** — crear `engine/psychometrics/` con las funciones determinísticas (p. ej. índices de
   dificultad/discriminación, fiabilidad) y, si aplica, un prompt de interpretación en `engine/prompts/`.
   Tests aislados en `tests/`.
4. **Estrategia** — en `pipelines/prueba_estandarizada.py`, poblar `analyze` para llamar al motor y
   devolver `InstrumentAnalysis` con la cara psicométrica (degradable, nunca lanza). Si la prueba
   necesita una construcción de canónico distinta a la documental (p. ej. tabular con claves de
   respuesta), implementar su propio `build_canonical` en vez de reusar `_document.py`.
5. **Consolidado (host)** — emitir la sección de prueba en `_generar_json_consolidado`, aditiva.
6. **Verificar** — suite verde + arranque 200 + fixture de una prueba real.

### Andamiaje sugerido para el consolidado (sin comprometer reglas)

Mismo envoltorio común; `knowledge` mínimo y extensible para no bloquear decisiones futuras:

```jsonc
{
  "instrument_type": "prueba_estandarizada",
  "metadata_dc": { /* … */ },
  "knowledge": {
    "items": [ { "item_id": "i1", "enunciado": "…" } ],          // placeholder
    "hallazgos": [ { "finding_id": "h1", "enunciado": "…", "evidence_item_ids": [] } ]
    // Futuro: métricas psicométricas (dificultad, discriminación, fiabilidad, …)
  }
}
```

No acoplar este envoltorio a supuestos exclusivos de encuestas/entrevistas, para que las reglas
psicométricas se añadan luego sin romper nada.

---

## 5. Checklist de "no romper nada"

- [ ] El facade y el tronco común (S4..S9) quedaron **sin cambios**.
- [ ] La estrategia nueva/ampliada solo compone stages/motores; no duplica lógica común.
- [ ] Los campos añadidos a contratos son **opcionales** (compatibilidad hacia atrás).
- [ ] `analyze` **nunca lanza**: degrada y reporta el diagnóstico.
- [ ] Hay una fixture + test del instrumento, registrado en `run_all`.
- [ ] `python -m survey_intelligence.tests.run_all` verde y app en 200.
- [ ] `SCHEMA_VERSION` subido si el consolidado cambió de forma observable.
