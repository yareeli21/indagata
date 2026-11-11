# Banco de evaluación v1 del chat (borrador)

`construir_banco_v1.py` genera `banco_v1_borrador.json` (para los scripts) y `banco_v1_borrador.csv` (para revisarlo
en Excel: separador `;`, UTF-8). Con la app levantada:

```powershell
.venv\Scripts\python.exe tools\rag\evaluacion\construir_banco_v1.py
```

## Qué contiene

| Tipo | Cuántas | Para qué |
|---|---|---|
| Con respuesta | 62 (2 por instrumento vigente) | Búsqueda (Hit@k, MRR, Recall@k, nDCG) y exactitud de la respuesta |
| Sin respuesta | 8 | Falsas aceptaciones: temas que ningún fragmento indexado menciona |
| Fuera de dominio | 2 | Rechazo de preguntas ajenas a la plataforma |

- **Redacción**: con palabras distintas a las del instrumento, más 2 paráfrasis por pregunta (consistencia).
- **Fragmento correcto**: instrumento + `preguntaId` (pregunta, reactivo o pregunta guía). Un fragmento recuperado es
  relevante si es de ese instrumento y trae ese `preguntaId`; no depende del texto, así que sobrevive a reindexar.
- **Respuesta esperada**: en encuestas y pruebas se calcula con SQL sobre `tt_rag.respuesta_interpretada` (versión
  vigente), sin usar el chat. Las entrevistas no tienen cifra: sus hechos clave se anotan a mano (columna
  «pendiente de revisar»).
- **Desarrollo / prueba**: las preguntas «a» de cada instrumento y 6 de las sin respuesta son de **prueba** (se reporta
  con ellas; no se usan para ajustar nada); las «b» y el resto, de **desarrollo** (para calibrar umbrales).

## Cómo revisarlo

1. Abrir `banco_v1_borrador.csv` y, por fila, marcar «OK (sí/no)»: ¿la pregunta es natural?, ¿el fragmento correcto
   es el que la responde?, ¿la respuesta esperada es la correcta?
2. En las entrevistas, escribir en «comentario» 1–3 hechos clave que debe mencionar una buena respuesta.
3. Corregir lo necesario en `PREGUNTAS` / `SIN_RESPUESTA` de `construir_banco_v1.py` y volver a generarlo.
4. **Congelar**: copiar `banco_v1_borrador.json` a `banco_v1.json` y no volver a cambiarlo antes de medir.

## Nota del 11 nov

Dos preguntas sin respuesta pasan hoy el umbral por significado: «videojuegos» (S04) recupera las horas de estudio
fuera de clase (0.66) y «aire acondicionado» (S05) una respuesta sobre seguridad en el campus (0.65). Son falsas
aceptaciones reales de la búsqueda y se dejan en el banco a propósito.
