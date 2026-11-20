# Fase 1: datos (7 nov 2026)

Commit `02de69f`. Solo se cambió el conocimiento (knowledge-service); el chat no se tocó.

## Qué se cambió

| Problema (Fase 0) | Cambio | Evidencia |
|---|---|---|
| Textos de pregunta pegados en la encuesta 127 («Cargas máxima ¿Tu programa…») | El lector ya estaba corregido desde el 5 nov; se regeneró el documento de la 127 (v4), conservando sus 5 KPIs aceptados (`tools/rag/regenerar_conocimiento.py`) | p01: «¿Tu programa académico cuenta con acreditación vigente…?» |
| Escalas 1–5 sin significado de sus extremos | Las escalas lineales de Google Forms se leen del PDF y se asignan a su pregunta por palabras | p13: «Nada probable → Muy probable»; p16–p18: «Totalmente en desacuerdo → Totalmente de acuerdo» |
| Guía de la entrevista 129 con 13 preguntas: indicaciones pegadas a p01 y el «gracias» final como pregunta | Las oraciones previas a la primera pregunta van en `instrumento.indicaciones`; el cierre no es un intercambio | 12 preguntas; aviso `cierre` |
| Sin polaridad por pregunta (C11) | El modelo propone y solo se acepta si es consistente; la decide la investigadora | 127: 15 preguntas revisadas por la investigadora (`../nlp_formato_2026-11-07/polaridad_127_revisada.py`) |
| Sin análisis de lo que se cuenta en entrevistas (D4) | Temas, valoración, actores, barreras, experiencias, propuestas y citas clave, con cita literal y origen | 129: análisis del modelo en 12 de 12 respuestas, 3 citas descartadas; 60: solo reglas (decisión de la investigadora) |
| D5 (pruebas calificadas) | Nada que borrar en el documento ni en la limpieza | `../chat_2026-11-07_antes/diagnostico.md` §4 |

## Decisiones con evidencia (`../nlp_formato_2026-11-07/`)

**Cómo pedir el análisis de entrevistas** (entrevista 129). Con gemma3:4b fueron 9 respuestas, porque 3 se perdieron
al reiniciar Ollama; con llama3.2:3b, las 12.

| Forma | gemma3:4b válidos | gemma descartadas | llama3.2:3b válidos | llama descartadas |
|---|---|---|---|---|
| a) Una petición, JSON libre | 4 de 9 (`{}` en 1–2 s) | 17 | 12 de 12 | 5 |
| b) Una petición con esquema | 9 de 9 | 29 | 12 de 12 | 7 |
| c) Tres peticiones cortas con esquema (**elegida**) | 9 de 9 | 2 | 12 de 12 | 0 |

- Tiempo por respuesta con la forma c: ~45 s con gemma y ~10 s con llama.
- El modelo de todo el sistema sigue siendo gemma3:4b.

**Polaridad.** La verificación de consistencia exige que el modelo dé el mismo juicio dos veces (los dos extremos de
la escala, o las opciones en distinto orden).
- **Encuesta 127, con gemma:** pasaron la verificación 3 de 15 preguntas con polaridad; en otras 7 coincidió en que no
  tienen, y 5 quedaron sin determinar.
- **Encuesta 61, con gemma:** 2 de 17 con polaridad, 5 sin ella y 10 sin determinar.
- **Encuesta 61, con llama:** 4 de 17 con polaridad y 13 sin determinar.
- **Sin la verificación**, gemma invirtió enunciados positivos («La carga de trabajo me permite mantener un equilibrio
  saludable»: el acuerdo quedaba como desfavorable).
- **Conclusión:** con modelos de 4B la polaridad la confirma la investigadora. La 61 (control) se queda con la
  propuesta automática, sin revisión, para medir el caso sin ayuda humana.

## Casos repetidos (`casos/`, `resumen.md`)

La mayoría de las fallas se corrigen en las fases 2 a 4 (chunks, hilo, operaciones y uso de la polaridad y del análisis
en el chat). Aquí solo cambian los datos.

| Caso | Antes | Ahora | ¿Por los datos? |
|---|---|---|---|
| ENC-19 | Opciones correctas | Opciones sin texto pegado; responde con la distribución en lugar de solo listar las opciones | Sí (texto); el formato se corrige en la Fase 4 |
| ENC-14 | p01 con texto pegado; ranking equivocado | p07 con su texto limpio; el ranking «repartida» sigue tomando una pregunta de opción múltiple (C6) | Texto, sí; el ranking, en la Fase 4 |
| ENC-20 | 3 preguntas sin extremos | Menciona «muy probable» y «totalmente de acuerdo», pero sigue nombrando 3 preguntas y llama «4» a «muy probable» | Parcial; la Fase 4 lista las escalas desde el catálogo |
| ENT-19 | 12 preguntas, temas pobres | 12 preguntas; temas generales | Igual |
| ENT-20 | Inventó «cinco horas» | «No se especifica su duración»; aún no dice «a profundidad» (está en el contexto de la ficha) | Mejoró; el tipo se resuelve en las fases 2 y 4 |
| ENT-21 | Indicaciones correctas por similitud | Respondió con la pregunta p03: las indicaciones ya están en el documento pero todavía no en los chunks | No; la Fase 2 las agrega a la ficha |
| ENT-03 | Pidió aclaración | Igual (falta la operación de cobertura de la guía) | No; Fase 4 |

## Incidentes

- **Docker se cayó** por falta de memoria durante la primera regeneración (análisis de la 129). Se reinició con
  permiso de la investigadora (`wsl --shutdown` y Docker Desktop). Después del reinicio varios puertos no respondían
  y se reiniciaron sus contenedores.
- **Ollama creció hasta 5.2 GB** con la swap llena (0.65 tokens/s) y se reinició entre pasos. Ahora el análisis
  guarda después de cada respuesta.
- Mientras dure el trabajo offline se detuvieron frontend, chroma-viewer, instrument-service y cleaning-service.
