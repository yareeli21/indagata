# Fase 5: evaluación final del chat (8 nov 2026)

Corrida con `tools/rag/evaluar_chat.py`, `gemma3:4b`, sin caché, Ollama reiniciado cada 15 casos (`reinicios.log`).
Control en `../chat_2026-11-08_final_control/` (encuesta 61, entrevista 60 y prueba sintética 133). Calificación contra
el «Debe» en `calificacion_debe.json` de cada carpeta, con una nota en cada caso que no cumple.

## Resultados

| Medida | Línea base (`chat_2026-11-07_antes`) | Corrida limpia (`chat_2026-11-08_despues`) | Final |
|---|---|---|---|
| Baterías: cumplen (de 79) | 31 (16 parciales, 32 no) | 54 (16 parciales, 9 no) | **63** (14 parciales, 2 no) |
| Encuesta (25) | 12 | 19 | 21 |
| Prueba (25) | 8 | 13 | 21 |
| Entrevista (25) | 11 | 18 | 17 |
| Cortesía (4) | 0 | 4 | 4 |
| Control encuesta y entrevista (de 16) | 1 (4 parciales, 11 no) | 9 (5 parciales, 2 no) | **13** (3 parciales, 0 no) |
| Control prueba sintética (de 8) | — | — | 6 (2 parciales, 0 no) |
| Planes válidos | 83 de 97 (85.6 %) | 69 de 77 (89.6 %) | 71 de 77 (92.2 %) |
| Plan del modelo usado sin cambios | — | — | 18 de 77 (23.4 %) |
| Caídas a plantilla | 28 de 102 | 31 de 102 | 34 de 102 |
| K-Precision, mediana | 0.85 (n = 74) | 0.86 (n = 63) | 0.87 (n = 60) |
| Cifras con respaldo | 963 de 982 | 760 de 800 | 815 de 856 |
| Tiempo por turno: mediana / p90 | 40 s / 188 s | 33 s / 64 s | 35 s / 115 s |
| *Hit rate*@3, baterías / control (`recuperacion.json`) | 0.61 / 0.89 | 0.79 / 1.00 | 0.84 / 1.00 |

## Casos que se repitieron y por qué

La corrida final se calificó caso por caso. Al calificarla aparecieron fallas generales del código; se corrigieron y se
repitieron **solo los casos afectados**. Las respuestas anteriores se conservan:

| Carpeta | Casos | Motivo de la repetición | Commit |
|---|---|---|---|
| `pruebas_primera_pasada/` y `../chat_2026-11-08_final_control/pruebas_primera_pasada/` | PRU-01 a PRU-25, CPR-01 a CPR-08 | La comprobación de lenguaje de calificación nunca se activaba: comparaba el tipo de la fuente con «prueba» y es «Prueba estandarizada» (PRU-05 y PRU-08 decían «comprensión» y «dificultad») | `73525c1` |
| `ranking_primera_pasada/` | PRU-07, PRU-13, PRU-17, CPR-02 | La comprobación del orden del ranking no reconocía reactivos: otra variable con el mismo nombre la reemplazaba | `51c96e5` |
| `segunda_pasada/` | PRU-17, CPR-04, CPR-05, CPR-06 | Reactivo fuera de rango respondido con otro; filtro por una opción del mismo reactivo que se resume; «conocimiento» y «entendimiento» como lenguaje de calificación. CPR-05 se repitió otra vez porque Ollama no respondió (`CPR-05_modelo_no_disponible.json`) | `d138f67` |

Una corrección posterior (`af2e458`: «ninguna sección tiene respuestas en blanco» en lugar de «la sección con más: 0»)
no se volvió a correr; CPR-05 quedó calificado como parcial con la frase anterior.

## Lo que sigue sin cumplir

- **PRU-11:** comparar conjuntos de reactivos agrupados por tema (no implementado).
- **ENT-15:** «¿eso qué dice sobre la difusión?» repite el dato sin interpretación marcada.
- **Parciales recurrentes:**
  - una frase sin cifras que contradice el resultado (ENC-11, ENC-13, PRU-14, ENT-13);
  - citas textuales que se parafrasean (ENT-04, ENT-08, ENT-14);
  - interpretación sin la aclaración de «un solo testimonio» (ENT-17);
  - agrupar la guía en temas (ENT-19);
  - la polaridad sin revisar de la encuesta de control (CEN-05).
- **ENC-22** dijo «nocturna no existe» en la corrida limpia y no en la final: el modelo puso otro filtro (variación
  del modelo).

## Otros archivos

- `pytest/`: salida de las pruebas automáticas de los seis servicios, todas en verde: 436 en visualization-service,
  126 en knowledge-service, 38 en storage-service, 186 en cleaning-service, 29 en metadata-service y 21 en
  analysis-service (836).
- `textos_instrumentos_en_codigo.txt`: búsqueda de los textos de los instrumentos 127, 129 y 130 en el código cambiado
  (`tools/rag/buscar_textos_instrumentos.py --sin-pruebas`); las coincidencias son comentarios, etiquetas genéricas o
  mensajes del sistema.
- `recuperacion.json`: *hit rate*@k con y sin el filtro de personas del chat.
