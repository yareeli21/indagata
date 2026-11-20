# Experimento de modelos: resumen

Instrumento 129; 13 turnos en 8 casos. Generado con `scripts/modelos/reporte.py`.

## 1. Redactores (métricas sin juez, contra la referencia y humanas)

| Métrica | qwen3:4b-instruct | gemma3:4b |
|---|---|---|
| Intención correcta | 62 % | 92 % |
| Plantillas indebidas | 7 | 2 |
| Respuestas redactadas por el modelo | 4 | 2 |
| Regeneraciones | 3 | 1 |
| Cifras con respaldo (redactadas) | 100 % | 100 % |
| Cifras sin respaldo | 0 | 0 |
| IDs inventados | 0 | 0 |
| Contexto suficiente (dato) | 40 % | 80 % |
| Exactitud de cifras | 100 % | 100 % |
| Criterios cumplidos | 57 % | 86 % |
| Similitud semántica | 0.442 | 0.317 |
| Latencia mediana (s) | 11.8 | 8.1 |
| Calificación humana media (0–2) | 1.385 | 1.538 |
| Respuestas «Bien» | 62 % | 69 % |
| Turnos calificados | 13 | 13 |

## 2. Matriz redactor × juez (promedio de fidelidad, relevancia y precisión)

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | **76 %** |
| gemma3:4b | 78 % |

En negritas, la autoevaluación (el redactor se juzga a sí mismo).

**Fidelidad**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | 83 % |
| gemma3:4b | 100 % |

**Relevancia**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | 54 % |
| gemma3:4b | 33 % |

**Precisión del contexto**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | 90 % |
| gemma3:4b | 100 % |

## 3. Sesgo de autoevaluación

Promedio cuando el redactor se juzga a sí mismo menos el promedio que le dan los demás jueces (positivo = se califica mejor).

- Sin datos suficientes (hace falta que el redactor también sea juez y al menos otro juez).

## 4. ¿Se puede confiar en cada juez? (cruce)

Kappa: 1 = acuerdo total, 0 = el del azar. Spearman: 1 = ordenan igual, 0 = sin relación.

| Juez | Fidelidad vs cifras con respaldo (kappa) | Juez aprobado vs «Bien» humano (kappa) | Promedio vs humana (Spearman) | Relevancia vs humana (Spearman) | Respuestas |
|---|---|---|---|---|---|
| qwen3:4b-instruct | 0.0 (n=3) | -0.186 | 0.288 | 0.162 | 17 (17 calificadas) |

**Precisión del contexto del juez contra «contexto suficiente» (turnos de dato)**

| Juez | Alta y suficiente | Alta e insuficiente | Baja y suficiente | Baja e insuficiente |
|---|---|---|---|---|
| qwen3:4b-instruct | 6 | 2 | 0 | 0 |

## 5. ¿Falla del modelo o del código?

Un turno que sale mal con todos los redactores apunta al código (interpretación, cálculo o datos); uno que sale bien con alguno apunta al modelo. Acierto = calificación humana «Bien»; sin calificación, las métricas contra la referencia.

| Turno | Tipo | qwen3:4b-instruct | gemma3:4b | Lectura |
|---|---|---|---|---|
| 1.1 | dato | ✗ | ✓ | depende del modelo |
| 1.2 | dato | ✗ | ✓ | depende del modelo |
| 1.3 | interpretativo | ✓ | ✓ | bien en todos |
| 2.1 | interpretativo | ✓ | ✓ | bien en todos |
| 3.1 | inexistente | ✓ | ✗ | depende del modelo |
| 4.1 | dato | ✓ | ✓ | bien en todos |
| 4.2 | interpretativo | ✗ | ✗ | falla en todos: probable código |
| 5.1 | control | ✓ | ✗ | depende del modelo |
| 5.2 | dato | ✗ | ✓ | depende del modelo |
| 6.1 | dato | ✓ | ✓ | bien en todos |
| 6.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 7.1 | dato | ✓ | ✓ | bien en todos |
| 8.1 | control | ✓ | ✓ | bien en todos |