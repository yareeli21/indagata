# analysis-service (puerto 8002)

Asocia KPIs a cada instrumento por similitud semántica y sirve el mapa del espacio vectorial. Es el único
servicio que el frontend llama directo (`VITE_ANALYSIS_URL`), sin pasar por el api-gateway.

| Ruta | Método | Qué hace |
|---|---|---|
| `/vectorizacion/perfil/propuestas` | POST | KPIs sugeridos desde el perfil semántico (knowledge-service): puntaje = 0.45·general + 0.45·preguntas + 0.10·cobertura, con justificación del LLM o de plantilla |
| `/vectorizacion/perfil/confirmar` | POST | Guarda los KPIs aceptados y rechazados |
| `/vectorizacion/propuestas`, `/vectorizacion/confirmar` | POST | Método anterior, basado en el resumen del instrumento (se conserva) |
| `/vectorizacion/kpis/reindex` | POST | Vuelve a vectorizar el catálogo de KPIs (colección `kpis` de Chroma) |
| `/vectorizacion/kpis/catalogo` | GET | Catálogo de KPIs |
| `/vectorizacion/espacio` | GET | Mapa 2D del espacio vectorial (solo lectura) |
| `/vectorizacion/summary/{id_instrumento}` | GET | Inspección del embedding del resumen de un instrumento |
| `/health` | GET | Estado del servicio |

**Catálogo de KPIs.** `python scripts/seed_kpis.py` (desde esta carpeta o dentro del contenedor) carga
`infrastructure/postgres/seed/KPI_Ampliacion.csv` en `tt_rag.kpi` (con `TRUNCATE … CASCADE`, que borra también los
KPIs aceptados) y las fuentes verificadas de `KPI_Fuentes.csv`; `--solo-fuentes` recarga solo las fuentes. Después
se llama a `/vectorizacion/kpis/reindex`. `scripts/comparar_kpis.py` compara el método anterior con el nuevo.

Embeddings: `paraphrase-multilingual-mpnet-base-v2` (768 dimensiones). La imagen instala torch solo para CPU antes
que lo demás (evita una descarga de ~7 GB de CUDA): conserva ese orden en `Dockerfile.analysis-service`.

```powershell
cd services/analysis-service; ..\..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
..\..\.venv\Scripts\python.exe -m pytest tests
```
