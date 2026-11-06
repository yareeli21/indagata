# instrument-service (puerto 8001)

Primer paso del asistente de carga: recibe el archivo de respuestas de un instrumento (encuesta, entrevista o
prueba estandarizada) y, si se tiene, el instrumento original; detecta el formato, lo lee en forma tabular o de
documento (`app/parsing/`) y entrega los bytes a storage-service. El identificador que nace aquí, `id_crudo`
(PK de `raw_data`), es el que usan todos los servicios y el frontend.

| Ruta | Método | Qué hace |
|---|---|---|
| `/instrumentos/upload` | POST | Sube las respuestas y el original opcional; crea `raw_data` e `instrumento_procesado` |
| `/instrumentos` | GET | Lista los instrumentos |
| `/instrumentos/{id}` | GET | Un instrumento por `id_crudo` |
| `/instrumentos/kpis/catalogo` | GET | Unión de los `kpi_hints` de todos los instrumentos |
| `/instrumentos/{id_crudo}` | DELETE | Borra el instrumento en cascada: base de datos, archivos y vectores (dueño o administrador) |
| `/health` | GET | Estado del servicio |

Formatos aceptados y reglas de lectura: `documentación/02_Desarrollo.md` (formatos aceptados). Las pruebas
estandarizadas no se califican: una clave de respuestas se rechaza con 400.

El almacenamiento es un puerto con dos implementaciones (`http` → storage-service, `local`), elegidas con
`STORAGE_BACKEND`.

```powershell
docker compose restart instrument-service   # después de cambiar el código
```
