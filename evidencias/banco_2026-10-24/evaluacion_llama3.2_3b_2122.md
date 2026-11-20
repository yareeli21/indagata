# Evaluación con el banco de preguntas (2026-10-24T21:22:39)

- Redactor: `llama3.2:3b` · Juez: `{'evaluadas': 27, 'calculadas_por_construccion': 20, 'fidelidad': 0.553, 'relevancia': 0.767, 'precision_contexto': 0.13}` · 55 preguntas, 275 consultas
- Decisión de dominio: exactitud 0.982, F1 macro 0.965, falsas aceptaciones 0
- Exactitud con referencia: 31/45 (0.689); fallidas: E11-07, E11-09, E11-11, E09-02, E09-04, E10-03, P01-01, P01-02, P02-02, P10-02, ENT1-02, ENT1-05, ENT2-01, ENT2-02
- Por tipo: calidad 2/2, descripcion 4/4, dijo 2/2, estructura 0/2, filtro 6/8, glosario 2/2, patrones 1/3, pct_nivel 4/5, postura 0/2, reactivo_dificil 2/3, respondente_con_nivel 2/2, respuesta 1/1, semantica 5/9
- Recuperación: Hit@k 1.0, MRR 1.0 (5 preguntas)
- Consistencia ante paráfrasis: 0.682 · Estabilidad: 1.0
- Latencia: p50 2.58 s, p95 17.27 s
- Juez: 27 evaluadas (20 fieles por construcción); fidelidad 0.553, relevancia 0.767, precisión 0.13

| Pregunta | Decisión | Exacta | Ruta | s | Motivo |
|---|---|---|---|---|---|
| E11-01 | dentro (✓) | True | estructurada | 2.45 | estructurada:pct_nivel:cifras_corregidas |
| E11-02 | dentro (✓) | True | estructurada | 2.05 | estructurada:filtro |
| E11-03 | dentro (✓) | True | estructurada | 2.09 | estructurada:filtro |
| E11-04 | dentro (✓) | True | estructurada | 1.56 | estructurada:filtro:cifras_completadas |
| E11-05 | dentro (✓) | True | estructurada | 3.04 | estructurada:filtro:cifras_corregidas |
| E11-06 | dentro (✓) | True | semantica | 4.73 | None |
| E11-07 | dentro (✓) | False | estructurada | 2.48 | estructurada:filtro |
| E11-08 | dentro (✓) | True | semantica | 4.53 | None |
| E11-09 | dentro (✓) | False | semantica | 5.21 | None |
| E11-10 | dentro (✓) | None | semantica | 4.64 | None |
| E11-11 | dentro (✓) | False | estructurada | 0.13 | estructurada:estructura |
| E11-12 | dentro (✓) | True | estructurada | 0.14 | estructurada:descripcion |
| E11-13 | dentro (✓) | True | estructurada | 13.69 | estructurada:respuesta:cifras_completadas |
| E11-14 | dentro (✓) | True | estructurada | 9.12 | estructurada:calidad:negativa_corregida |
| E09-01 | dentro (✓) | True | estructurada | 2.11 | estructurada:filtro |
| E09-02 | dentro (✓) | False | estructurada | 17.27 | estructurada:filtro |
| E09-03 | dentro (✓) | True | semantica | 3.63 | None |
| E09-04 | dentro (✓) | False | semantica | 4.39 | None |
| E09-05 | dentro (✓) | True | estructurada | 6.14 | estructurada:filtro:cifras_corregidas |
| E10-01 | dentro (✓) | True | estructurada | 2.13 | estructurada:pct_nivel |
| E10-02 | dentro (✓) | True | estructurada | 1.1 | estructurada:respondente_con_nivel:negativa_corregida |
| E10-03 | dentro (✓) | False | semantica | 4.84 | None |
| E10-04 | dentro (✓) | True | estructurada | 0.11 | estructurada:respondente_con_nivel:no_existe |
| P01-01 | dentro (✓) | False | estructurada | 1.99 | estructurada:reactivo_dificil:cifras_completadas |
| P01-02 | dentro (✓) | False | estructurada | 0.12 | estructurada:patrones |
| P01-03 | dentro (✓) | True | estructurada | 19.27 | estructurada:calidad |
| P02-01 | dentro (✓) | True | estructurada | 2.19 | estructurada:reactivo_dificil:cifras_completadas |
| P02-02 | dentro (✓) | False | semantica | 3.93 | None |
| P04-01 | dentro (✓) | True | semantica | 3.26 | None |
| P04-02 | dentro (✓) | True | estructurada | 2.94 | estructurada:reactivo_dificil |
| P10-01 | dentro (✓) | True | semantica | 3.55 | None |
| P10-02 | dentro (✓) | False | semantica | 4.24 | None |
| ENT1-01 | dentro (✓) | True | estructurada | 16.85 | estructurada:dijo |
| ENT1-02 | fuera (✗) | False | semantica | 0.31 | similitud máxima 0.29 < 0.3 |
| ENT1-03 | dentro (✓) | True | semantica | 9.18 | None |
| ENT1-04 | dentro (✓) | True | estructurada | 0.2 | estructurada:descripcion |
| ENT1-05 | dentro (✓) | False | semantica | 20.95 | None |
| ENT2-01 | dentro (✓) | False | estructurada | 21.03 | estructurada:postura:cifras_completadas |
| ENT2-02 | dentro (✓) | False | estructurada | 2.85 | estructurada:postura:cifras_completadas |
| ENT2-03 | dentro (✓) | True | estructurada | 2.58 | estructurada:dijo |
| MUL-01 | dentro (✓) | True | estructurada | 0.18 | estructurada:descripcion |
| MUL-02 | dentro (✓) | True | estructurada | 0.18 | estructurada:descripcion |
| MUL-03 | dentro (✓) | True | estructurada | 0.25 | estructurada:patrones |
| MUL-04 | dentro (✓) | True | estructurada | 0.19 | estructurada:descripcion |
| DOM-01 | fuera (✓) | None | semantica | 0.13 | similitud máxima 0.14 < 0.3 |
| DOM-02 | fuera (✓) | None | None | 0.02 | regla:fuera |
| DOM-03 | privacidad (✓) | None | None | 0.03 | regla:privacidad |
| DOM-04 | privacidad (✓) | None | None | 0.09 | regla:privacidad |
| DOM-05 | manipulacion (✓) | None | None | 0.08 | regla:manipulacion |
| DOM-06 | manipulacion (✓) | None | None | 0.07 | regla:manipulacion |
| DOM-07 | sin_informacion (✓) | None | semantica | 6.38 | el modelo no encontró la respuesta en el contexto |
| GLO-01 | dentro (✓) | True | semantica | 5.71 | None |
| GLO-02 | dentro (✓) | True | semantica | 4.15 | None |
| AYU-01 | ayuda (✓) | None | ayuda | 3.19 | None |
| AYU-02 | ayuda (✓) | None | ayuda | 2.19 | None |