# Regresión del chat: antes y después del rediseño

Antes: 2026-10-28T13:39:44 (solo reglas). Después: 2026-10-28T13:28:29 (interpretación → ejecución → redacción → verificación). Mismos 28 casos, mismos instrumentos, sin caché.

| Medida | Antes | Después |
|---|---|---|
| Respuesta correcta | 53.6 % | 96.4 % |
| Cifras correctas | 46.7 % | 100.0 % |
| Decisión de dominio correcta | 85.7 % | 100.0 % |
| Plan completo correcto | — (sin plan) | 92.0 % |
| Tiempo por pregunta (mediana) | 11.84 s | 28.23 s |
| Tiempo por pregunta (máximo) | 20.14 s | 55.57 s |
| Fidelidad (RAGAS) | 0.846 | 0.807 |
| Relevancia (RAGAS) | 0.561 | 0.526 |
| Precisión del contexto (RAGAS) | 0.903 | 0.913 |

Plan por campo (después): {'intencion': 92.0, 'filtros': 100.0, 'limite': 100.0, 'campos': 100.0, 'respondentes': 100.0, 'preguntas': 100.0, 'nivel': 100.0, 'agrupar_por': 100.0, 'contexto': 100.0}

Mediana por etapa, después (ms): {'ejecucion': 14, 'redaccion': 8111, 'verificacion': 1988, 'interpretacion': 25568}

| Caso | Categoría | Antes | Después |
|---|---|---|---|
| C01 | hallazgo | no | sí |
| C02 | filtro con límite y todas las respuestas | sí | sí |
| C03 | por respondente (ordinal) | no | sí |
| C04 | por respondente (ID y pregunta) | sí | sí |
| C05 | filtros combinados (conteo) | sí | sí |
| C06 | seguimiento con historial | no | sí |
| C07 | porcentaje en un nivel | no | sí |
| C08 | negación | no | sí |
| C09 | límite y solo IDs | sí | sí |
| C10 | por respondente (último) | no | sí |
| C11 | resumen de una pregunta | no | sí |
| C12 | KPI | sí | sí |
| C13 | valor que no existe | no | no |
| C14 | ambigua | no | sí |
| C15 | fuera de dominio (regla) | sí | sí |
| C16 | fuera de dominio (plan) | sí | no |
| C17 | reidentificación | sí | sí |
| C18 | metodología | no | sí |
| C19 | uso de la plataforma | sí | sí |
| C20 | comparar grupos de contexto | no | sí |
| C21 | porcentaje de un grupo | sí | sí |
| C22 | comparar grupos de contexto | no | sí |
| C23 | conteo binario | sí | sí |
| C24 | filtro con nivel y opción | sí | sí |
| C25 | comparación entre instrumentos | no | sí |
| C26 | hallazgo | sí | sí |
| C27 | entrevista por participante | sí | sí |
| C28 | semántica abierta | sí | sí |

Fallas antes: C01, C03, C06, C07, C08, C10, C11, C13, C14, C18, C20, C22, C25.
Fallas después: C13.
