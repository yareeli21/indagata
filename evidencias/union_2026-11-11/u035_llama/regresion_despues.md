# Regresión del chat — modo «despues» (2026-11-11T19:02:22)

- Casos: 28
- Respuesta correcta: 75.0 %
- Cifras correctas: 66.7 %
- Decisión de dominio correcta: 92.9 %
- Tiempo por pregunta: mediana 17.97 s, máximo 43.87 s
- Plan completo correcto: 68.0 %; por campo: {'intencion': 88.0, 'filtros': 42.9, 'limite': 100.0, 'campos': 83.3, 'respondentes': 100.0, 'preguntas': 66.7, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 13, 'redaccion': 10282, 'recuperacion': 399, 'verificacion': 3869, 'interpretacion': 10337}
- Fallas: C02, C06, C08, C13, C14, C22, C24

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 32.57 | plan:hallazgo:inferencia |
| C02 | filtro con límite y todas las respuestas | no | 21.72 | plan:datos_respondente:regenerada |
| C03 | por respondente (ordinal) | sí | 21.55 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 20.93 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | sí | 19.52 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 24.09 | plan:hallazgo:negativa_corregida |
| C07 | porcentaje en un nivel | no | 11.81 | plan:conteo_porcentaje:frase_dato |
| C08 | negación | no | 21.95 | plan:conteo_porcentaje:cifras_completadas |
| C09 | límite y solo IDs | sí | 18.06 | plan:filtrar_respondentes |
| C10 | por respondente (último) | sí | 16.98 | plan:datos_respondente |
| C11 | resumen de una pregunta | sí | 11.98 | plan:resumen_pregunta:regenerada |
| C12 | KPI | sí | 39.0 | plan:kpi:inventada |
| C13 | valor que no existe | no | 17.21 | el modelo no encontró la respuesta en el contexto |
| C14 | ambigua | no | 11.06 | similitud máxima 0.29 < 0.3 |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 10.31 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.08 | regla:privacidad |
| C18 | metodología | sí | 7.25 | None |
| C19 | uso de la plataforma | sí | 4.08 | None |
| C20 | comparar grupos de contexto | sí | 22.54 | plan:comparar_grupos:inventada |
| C21 | porcentaje de un grupo | sí | 16.33 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 22.86 | plan:comparar_grupos:inventada |
| C23 | conteo binario | sí | 9.15 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | no | 17.88 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 35.53 | plan:comparar_grupos:inventada |
| C26 | hallazgo | sí | 43.87 | plan:hallazgo:regenerada |
| C27 | entrevista por participante | no | 27.43 | plan:datos_respondente:regenerada |
| C28 | semántica abierta | sí | 14.56 | None |
