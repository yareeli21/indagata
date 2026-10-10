# Verificación — FEAT-001 (kpis-reales)

Entorno: Windows + PowerShell. Python 3.14.2, SQLAlchemy 2.0.49, pydantic 2.13.3.
Todas las rutas bajo el worktree `.worktrees/kpis-reales`. No se ejecutó runtime
(docker/seed/reindex): esa verificación corresponde a un paso posterior.

## CSV versionado en el worktree

- Copia byte a byte del CSV del árbol principal al worktree
  (`infrastructure/postgres/seed/kpis_ampliados.csv`).
- SHA256 origen == destino: `874948DDC03F6EB997A2A85EF962CDF99338A8E35DF114D69FE4452C55421FAA` (match=True).
- Conteo de líneas del origen: **56** (1 cabecera + 55 filas de datos).
- Cabecera leída (8 columnas, orden exacto): `KPI, Polaridad_Rendimiento,
  Tipo_Objetivo_Estrategico, Formula_Metrica_Calculo, Descripcion_Ampliada_Educativa,
  Comportamiento_Direccional_y_Causalidad, Razon_Estrategica_y_Decisiones,
  Texto_Contexto_RAG_Vectorial`.

## py_compile del script de seed

Comando (desde `services/analysis-service`):

```
python -m py_compile scripts/seed_kpis.py
```

Salida: exit code 0 (compila sin error).

## Columnas del ORM

```
python -c "from shared.models.kpi import KPI; print([c.name for c in KPI.__table__.columns])"
```

Salida (9 columnas = kpi_id + 8 nuevas):

```
['kpi_id', 'nombre', 'polaridad_rendimiento', 'tipo_objetivo_estrategico',
 'formula_metrica_calculo', 'descripcion_ampliada_educativa',
 'comportamiento_direccional_causalidad', 'razon_estrategica_decisiones',
 'texto_contexto_rag_vectorial']
```

## Schemas Pydantic compartidos

```
python -c "from shared.schemas import KPIBase, KPICreate, KPIUpdate, KPIRead; print(sorted(KPIRead.model_fields.keys()))"
```

Salida (9 campos, sin ImportError de los nombres KPI):

```
['comportamiento_direccional_causalidad', 'descripcion_ampliada_educativa',
 'formula_metrica_calculo', 'kpi_id', 'nombre', 'polaridad_rendimiento',
 'razon_estrategica_decisiones', 'texto_contexto_rag_vectorial',
 'tipo_objetivo_estrategico']
```

Nota de entorno: el paquete `shared/schemas/__init__.py` importa `usuario` (usa
`EmailStr`), por lo que al correr el check hace falta `email-validator` presente
en el entorno (pydantic 2.13 lo exige de forma perezosa). Se instaló localmente
solo para ejecutar la verificación; **no** se añadió a `requirements-dev.txt`
(que, por diseño, solo lista `pytest`). Es una brecha de entorno preexistente,
ajena a los cambios de KPI de esta feature.

## pytest de leer_kpis_csv

```
pip install -r requirements-dev.txt   # pytest
python -m pytest tests/test_seed_kpis.py -q
```

Salida:

```
....                                                                     [100%]
4 passed in 1.15s
```

Casos cubiertos: caso feliz (2 filas), cabecera incorrecta (aborta),
`KPI` vacío (aborta), `Texto_Contexto_RAG_Vectorial` vacío (aborta).

## CREATE TABLE kpi (01_schema.sql)

Bloque redefinido a `kpi_id SERIAL PRIMARY KEY` + las 8 columnas snake_case
(§1.1), con `nombre` y `texto_contexto_rag_vectorial` NOT NULL. Las tablas
hijas `kpi_variable`, `kpi_inferido`, `valor_variable_inferido` y
`kpi_inferido_chunk` y sus FKs a `kpi(kpi_id)` no se tocaron (CA-3).
