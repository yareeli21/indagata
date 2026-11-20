# Experimento de modelos: resumen

Instrumento 130; 22 turnos en 12 casos. Generado con `scripts/modelos/reporte.py`.

## 1. Redactores (métricas sin juez, contra la referencia y humanas)

| Métrica | gemma3:4b | qwen3:4b-instruct |
|---|---|---|
| Intención correcta | 46 % | 50 % |
| Plantillas indebidas | 8 | 10 |
| Respuestas redactadas por el modelo | 6 | 5 |
| Regeneraciones | 1 | 4 |
| Cifras con respaldo (redactadas) | 100 % | 100 % |
| Cifras sin respaldo | 0 | 0 |
| IDs inventados | 0 | 0 |
| Contexto suficiente (dato) | 27 % | 46 % |
| Exactitud de cifras | 18 % | 46 % |
| Criterios cumplidos | 25 % | 50 % |
| Similitud semántica | 0.369 | 0.37 |
| Latencia mediana (s) | 17.0 | 9.7 |
| Calificación humana media (0–2) | 0.773 | 0.773 |
| Respuestas «Bien» | 27 % | 27 % |
| Turnos calificados | 22 | 22 |

## 2. Matriz redactor × juez (promedio de fidelidad, relevancia y precisión)

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 84 % |
| qwen3:4b-instruct | **77 %** |

En negritas, la autoevaluación (el redactor se juzga a sí mismo).

**Fidelidad**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 95 % |
| qwen3:4b-instruct | 87 % |

**Relevancia**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 60 % |
| qwen3:4b-instruct | 56 % |

**Precisión del contexto**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| gemma3:4b | 100 % |
| qwen3:4b-instruct | 88 % |

## 3. Sesgo de autoevaluación

Promedio cuando el redactor se juzga a sí mismo menos el promedio que le dan los demás jueces (positivo = se califica mejor).

- Sin datos suficientes (hace falta que el redactor también sea juez y al menos otro juez).

## 4. ¿Se puede confiar en cada juez? (cruce)

Kappa: 1 = acuerdo total, 0 = el del azar. Spearman: 1 = ordenan igual, 0 = sin relación.

| Juez | Fidelidad vs cifras con respaldo (kappa) | Juez aprobado vs «Bien» humano (kappa) | Promedio vs humana (Spearman) | Relevancia vs humana (Spearman) | Respuestas |
|---|---|---|---|---|---|
| qwen3:4b-instruct | 0.0 (n=9) | 0.118 | 0.342 | 0.406 | 18 (18 calificadas) |

**Precisión del contexto del juez contra «contexto suficiente» (turnos de dato)**

| Juez | Alta y suficiente | Alta e insuficiente | Baja y suficiente | Baja e insuficiente |
|---|---|---|---|---|
| qwen3:4b-instruct | 8 | 4 | 0 | 0 |

## 5. ¿Falla del modelo o del código?

Un turno que sale mal con todos los redactores apunta al código (interpretación, cálculo o datos); uno que sale bien con alguno apunta al modelo. Acierto = calificación humana «Bien»; sin calificación, las métricas contra la referencia.

| Turno | Tipo | gemma3:4b | qwen3:4b-instruct | Lectura |
|---|---|---|---|---|
| 1.1 | dato | ✓ | ✓ | bien en todos |
| 1.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 1.3 | interpretativo | ✗ | ✗ | falla en todos: probable código |
| 2.1 | capacidad | ✗ | ✗ | falla en todos: probable código |
| 2.2 | capacidad | ✗ | ✗ | falla en todos: probable código |
| 3.1 | dato | ✓ | ✓ | bien en todos |
| 3.2 | interpretativo | ✓ | ✗ | depende del modelo |
| 4.1 | dato | ✗ | ✓ | depende del modelo |
| 4.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 5.1 | dato | ✗ | ✗ | falla en todos: probable código |
| 5.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 6.1 | inexistente | ✓ | ✓ | bien en todos |
| 6.2 | inexistente | ✓ | ✗ | depende del modelo |
| 7.1 | dato | ✗ | ✗ | falla en todos: probable código |
| 8.1 | inexistente | ✓ | ✓ | bien en todos |
| 8.2 | inexistente | ✗ | ✗ | falla en todos: probable código |
| 9.1 | dato | ✗ | ✗ | falla en todos: probable código |
| 9.2 | dato | ✗ | ✓ | depende del modelo |
| 10.1 | interpretativo | ✗ | ✗ | falla en todos: probable código |
| 10.2 | interpretativo | ✗ | ✗ | falla en todos: probable código |
| 11.1 | dato | ✗ | ✗ | falla en todos: probable código |
| 12.1 | interpretativo | ✗ | ✗ | falla en todos: probable código |