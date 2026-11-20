# Experimento de modelos: resumen

Instrumento 129; 13 turnos en 8 casos. Generado con `scripts/modelos/reporte.py`.

## 1. Redactores (métricas sin juez, contra la referencia y humanas)

| Métrica | gemma3:4b | qwen3:4b-instruct |
|---|---|---|
| Intención correcta | 92 % | 62 % |
| Plantillas indebidas | 2 | 11 |
| Respuestas redactadas por el modelo | 2 | 0 |
| Regeneraciones | 0 | 2 |
| Cifras con respaldo (redactadas) | 100 % | — |
| Cifras sin respaldo | 0 | 0 |
| IDs inventados | 0 | 0 |
| Contexto suficiente (dato) | 60 % | 20 % |
| Exactitud de cifras | 100 % | 0 % |
| Criterios cumplidos | 71 % | 29 % |
| Similitud semántica | 0.428 | 0.251 |
| Latencia mediana (s) | 6.7 | 6.3 |
| Calificación humana media (0–2) | 1.385 | 0.538 |
| Respuestas «Bien» | 62 % | 23 % |
| Turnos calificados | 13 | 13 |

## 2. Matriz redactor × juez (promedio de fidelidad, relevancia y precisión)

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 82 % |
| qwen3:4b-instruct | **87 %** |

En negritas, la autoevaluación (el redactor se juzga a sí mismo).

**Fidelidad**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 95 % |
| qwen3:4b-instruct | 100 % |

**Relevancia**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 49 % |
| qwen3:4b-instruct | 61 % |

**Precisión del contexto**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 100 % |
| qwen3:4b-instruct | 100 % |

## 3. Sesgo de autoevaluación

Promedio cuando el redactor se juzga a sí mismo menos el promedio que le dan los demás jueces (positivo = se califica mejor).

- Sin datos suficientes (hace falta que el redactor también sea juez y al menos otro juez).

## 4. ¿Se puede confiar en cada juez? (cruce)

Kappa: 1 = acuerdo total, 0 = el del azar. Spearman: 1 = ordenan igual, 0 = sin relación.

| Juez | Fidelidad vs cifras con respaldo (kappa) | Juez aprobado vs «Bien» humano (kappa) | Promedio vs humana (Spearman) | Relevancia vs humana (Spearman) | Respuestas |
|---|---|---|---|---|---|
| qwen3:4b-instruct | — (n=1) | 0.316 | 0.302 | 0.415 | 13 (13 calificadas) |

**Precisión del contexto del juez contra «contexto suficiente» (turnos de dato)**

| Juez | Alta y suficiente | Alta e insuficiente | Baja y suficiente | Baja e insuficiente |
|---|---|---|---|---|
| qwen3:4b-instruct | 4 | 2 | 0 | 0 |

## 5. ¿Falla del modelo o del código?

Un turno que sale mal con todos los redactores apunta al código (interpretación, cálculo o datos); uno que sale bien con alguno apunta al modelo. Acierto = calificación humana «Bien»; sin calificación, las métricas contra la referencia.

| Turno | Tipo | gemma3:4b | qwen3:4b-instruct | Lectura |
|---|---|---|---|---|
| 1.1 | dato | ✓ | ✗ | depende del modelo |
| 1.2 | dato | ✓ | ✗ | depende del modelo |
| 1.3 | interpretativo | ✓ | ✗ | depende del modelo |
| 2.1 | interpretativo | ✓ | ✓ | bien en todos |
| 3.1 | inexistente | ✗ | ✗ | falla en todos: probable código |
| 4.1 | dato | ✓ | ✗ | depende del modelo |
| 4.2 | interpretativo | ✗ | ✗ | falla en todos: probable código |
| 5.1 | control | ✗ | ✗ | falla en todos: probable código |
| 5.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 6.1 | dato | ✓ | ✗ | depende del modelo |
| 6.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 7.1 | dato | ✓ | ✓ | bien en todos |
| 8.1 | control | ✓ | ✓ | bien en todos |