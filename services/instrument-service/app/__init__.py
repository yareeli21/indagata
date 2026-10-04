"""Instrument Service — aplicación.

Microservicio enfocado 100% en la CARGA (upload) de instrumentos:
  1. Recibe el archivo respondido (tabular/documento con las respuestas) y,
     opcionalmente, el archivo original del instrumento (sin respuestas).
  2. Identifica el tipo de cada archivo y lo enruta a la familia de parser
     que le corresponde (tabular vs. documento).
  3. Delega su almacenamiento en el puerto de storage (app/storage) —el
     storage-service cuando exista— y registra el instrumento en la tabla padre
     `tt_rag.raw_data` (+ `instrumento_procesado` en estado 'recibido').

Fuente de verdad del esquema: infrastructure/postgres/init/01_schema.sql.
Modelos/esquemas compartidos: shared/models y shared/schemas.
"""
