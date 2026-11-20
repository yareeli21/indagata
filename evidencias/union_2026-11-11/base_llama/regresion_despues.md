# Regresión del chat — modo «despues» (2026-11-11T18:20:17)

- Casos: 28
- Respuesta correcta: 78.6 %
- Cifras correctas: 73.3 %
- Decisión de dominio correcta: 92.9 %
- Tiempo por pregunta: mediana 17.1 s, máximo 59.52 s
- Plan completo correcto: 68.0 %; por campo: {'intencion': 88.0, 'filtros': 42.9, 'limite': 100.0, 'campos': 83.3, 'respondentes': 100.0, 'preguntas': 66.7, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 16, 'redaccion': 9689, 'recuperacion': 319, 'verificacion': 2, 'interpretacion': 10241}
- Fallas: C02, C06, C08, C13, C14, C22

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 59.52 | plan:hallazgo |
| C02 | filtro con límite y todas las respuestas | no | 18.52 | plan:datos_respondente |
| C03 | por respondente (ordinal) | sí | 20.76 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 19.85 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | sí | 16.9 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 8.24 | plan:comparar_grupos |
| C07 | porcentaje en un nivel | no | 9.22 | plan:conteo_porcentaje |
| C08 | negación | no | 20.8 | plan:conteo_porcentaje:cifras_corregidas |
| C09 | límite y solo IDs | sí | 20.8 | plan:filtrar_respondentes:cifras_corregidas |
| C10 | por respondente (último) | sí | 16.53 | plan:datos_respondente |
| C11 | resumen de una pregunta | sí | 12.28 | plan:resumen_pregunta:inventada |
| C12 | KPI | sí | 36.45 | plan:kpi:inventada |
| C13 | valor que no existe | no | 17.49 | el modelo no encontró la respuesta en el contexto |
| C14 | ambigua | no | 10.85 | similitud máxima 0.29 < 0.3 |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 10.26 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | sí | 7.52 | None |
| C19 | uso de la plataforma | sí | 4.2 | None |
| C20 | comparar grupos de contexto | sí | 21.88 | plan:comparar_grupos:inventada |
| C21 | porcentaje de un grupo | sí | 16.46 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 23.72 | plan:comparar_grupos:inventada |
| C23 | conteo binario | sí | 9.39 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | no | 17.31 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 33.63 | plan:comparar_grupos:inventada |
| C26 | hallazgo | sí | 29.16 | plan:hallazgo:regenerada |
| C27 | entrevista por participante | no | 23.09 | plan:datos_respondente:inventada |
| C28 | semántica abierta | sí | 15.15 | None |
