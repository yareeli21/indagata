# Regresión del chat — modo «despues» (2026-11-11T18:34:16)

- Casos: 28
- Respuesta correcta: 75.0 %
- Cifras correctas: 66.7 %
- Decisión de dominio correcta: 96.4 %
- Tiempo por pregunta: mediana 16.2 s, máximo 40.54 s
- Plan completo correcto: 72.0 %; por campo: {'intencion': 88.0, 'filtros': 42.9, 'limite': 100.0, 'campos': 100.0, 'respondentes': 100.0, 'preguntas': 66.7, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 10, 'redaccion': 8590, 'recuperacion': 381, 'verificacion': 3158, 'interpretacion': 10312}
- Fallas: C02, C06, C08, C13, C14, C22, C24

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 30.88 | plan:hallazgo:regenerada |
| C02 | filtro con límite y todas las respuestas | no | 20.32 | plan:datos_respondente:inventada |
| C03 | por respondente (ordinal) | sí | 18.99 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 18.18 | plan:datos_respondente:regenerada |
| C05 | filtros combinados (conteo) | sí | 16.17 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 20.15 | plan:hallazgo:negativa_corregida |
| C07 | porcentaje en un nivel | no | 8.78 | plan:conteo_porcentaje |
| C08 | negación | no | 20.45 | plan:conteo_porcentaje:cifras_completadas |
| C09 | límite y solo IDs | sí | 20.84 | plan:filtrar_respondentes:cifras_completadas |
| C10 | por respondente (último) | sí | 14.3 | plan:datos_respondente |
| C11 | resumen de una pregunta | sí | 11.42 | plan:resumen_pregunta:inventada |
| C12 | KPI | sí | 40.54 | plan:kpi:inventada |
| C13 | valor que no existe | no | 10.74 | plan:aclaracion |
| C14 | ambigua | no | 13.98 | similitud máxima 0.29 < 0.3 |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 10.58 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.08 | regla:privacidad |
| C18 | metodología | sí | 7.07 | None |
| C19 | uso de la plataforma | sí | 4.26 | None |
| C20 | comparar grupos de contexto | sí | 23.23 | plan:comparar_grupos:inventada |
| C21 | porcentaje de un grupo | sí | 15.95 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 22.44 | plan:comparar_grupos:regenerada |
| C23 | conteo binario | sí | 8.49 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | no | 18.02 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 32.47 | plan:comparar_grupos:cifras_completadas |
| C26 | hallazgo | sí | 32.02 | plan:hallazgo:inferencia |
| C27 | entrevista por participante | sí | 13.48 | plan:datos_respondente |
| C28 | semántica abierta | sí | 16.24 | None |
