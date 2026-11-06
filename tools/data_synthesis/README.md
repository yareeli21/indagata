# Motor de Datos Sintéticos — Indagata

Sistema de generación reproducible de instrumentos de investigación educativa con datos sintéticos estadísticamente fundamentados.

## Estructura

```
tools/data_synthesis/
  generate.py               # CLI principal
  config/
    perfiles_estudiantes.json   # 8 perfiles de estudiantes con parámetros estadísticos
    kpi_mapping.json            # Mapeo de KPIs por instrumento
    coherencia_encuestas.json   # Reglas de las preguntas no Likert (modelo «coherente», v1.1)
  generators/
    __init__.py
    base_generator.py           # Utilidades compartidas: muestreo, beta, demografía
    encuesta_generator.py       # Generador de encuestas (11 instrumentos)
    coherencia.py               # Respuestas coherentes de las preguntas no Likert
    entrevista_generator.py     # Generador de entrevistas (10 instrumentos)
    prueba_generator.py         # Generador de pruebas estandarizadas (10 instrumentos)
  quality/
    checker.py                  # Validación: alpha Cronbach, outliers, correlación
    verificar_coherencia.py     # ¿Las preguntas no Likert dependen del respondente? (uniforme vs coherente)
  visualization/
    chart_generator.py          # Gráficas por instrumento y resumen general
```

## Uso rápido

```bash
# Generar todos los instrumentos
python generate.py --all

# Generar todos los instrumentos con semilla específica (reproducible)
python generate.py --all --seed 42

# Generar solo encuestas
python generate.py --tipo encuesta

# Generar 3 encuestas adicionales (continúa la numeración)
python generate.py --tipo encuesta --n 3

# Generar solo visualizaciones
python generate.py --charts-only

# Generar solo reporte de calidad
python generate.py --quality-only

# Directorio de salida personalizado
python generate.py --all --output /ruta/personalizada
```

## Instrumentos generados

| ID | Título | Tipo | Fuente | N |
|----|--------|------|--------|---|
| enc_01 | Inventario Estrategias Aprendizaje (IEAE) | Encuesta | Real | 180 |
| enc_02 | Student Engagement Questionnaire | Encuesta | Real | 200 |
| enc_03 | SESQ | Encuesta | Real | 220 |
| enc_04 | MSLQ-SF | Encuesta | Real | 200 |
| enc_05 | Escala RAU | Encuesta | Real | 180 |
| enc_06 | Satisfacción Servicios Institucionales | Encuesta | Sintético | 160 |
| enc_07 | Diversidad e Inclusión | Encuesta | Sintético | 160 |
| enc_08 | Bienestar y Salud Mental | Encuesta | Sintético | 160 |
| enc_09 | Carga Académica y Tiempo | Encuesta | Sintético | 160 |
| enc_10 | Inserción Laboral | Encuesta | Sintético | 150 |
| enc_11 | Trayectoria Académica, Trabajo y Servicios (todos los tipos de pregunta, v1.1) | Encuesta | Sintético | 160 |
| ent_01 | Estrategias de permanencia | Entrevista | Sintético | 40 |
| ent_02 | Experiencia docente | Entrevista | Sintético | 30 |
| ent_03 | Tecnología y aprendizaje | Entrevista | Sintético | 35 |
| ent_04 | Inclusión y diversidad | Entrevista | Sintético | 28 |
| ent_05 | Investigación (posgrado) | Entrevista | Sintético | 25 |
| ent_06 | Orientación vocacional | Entrevista | Sintético | 32 |
| ent_07 | Vida de campus | Entrevista | Sintético | 30 |
| ent_08 | Financiamiento | Entrevista | Sintético | 28 |
| ent_09 | Transición secundaria-uni | Entrevista | Sintético | 35 |
| ent_10 | Internacionalización | Entrevista | Sintético | 25 |
| pru_01 | Comprensión Lectora | Prueba | Sintético | 100 |
| pru_02 | Competencias Matemáticas | Prueba | Sintético | 110 |
| pru_03 | Alfabetización Digital | Prueba | Sintético | 95 |
| pru_04 | Aprendizaje Autónomo (CAA) | Prueba | Sintético | 90 |
| pru_05 | Competencias Docentes | Prueba | Sintético | 120 |
| pru_06 | Investigación Científica | Prueba | Sintético | 80 |
| pru_07 | Orientación Vocacional | Prueba | Sintético | 110 |
| pru_08 | Competencias Interculturales | Prueba | Sintético | 90 |
| pru_09 | Comunicación Académica | Prueba | Sintético | 100 |
| pru_10 | Liderazgo Estudiantil | Prueba | Sintético | 100 |

## Perfiles de estudiantes

Los datos se generan a partir de 8 perfiles estadísticamente calibrados:

| Perfil | Nombre | Peso | GPA medio | Likert medio |
|--------|--------|------|-----------|--------------|
| P1 | Alto rendimiento, autoregulado | 12% | 3.75 | ~4.2 |
| P2 | Promedio comprometido | 20% | 3.15 | ~3.4 |
| P3 | En riesgo académico | 15% | 2.15 | ~2.1 |
| P4 | Trabajador adulto tiempo parcial | 13% | 2.90 | ~3.0 |
| P5 | Avanzado desmotivado (burnout) | 10% | 3.40 | ~3.0 |
| P6 | Internacional/contexto diverso | 8% | 3.35 | ~3.1 |
| P7 | Posgrado alta competencia | 12% | 3.85 | ~4.5 |
| P8 | Dificultades socioeconómicas | 10% | 2.60 | ~2.8 |

## Preguntas que no son Likert: modelo «coherente» (v1.1) y «uniforme» (v1.0)

Las encuestas mezclan ítems Likert con otros tipos de pregunta. Los ítems Likert siempre
dependen del perfil del estudiante. Para los demás tipos hay dos modelos:

| Modelo | Cómo se genera la respuesta | Para qué |
|---|---|---|
| `coherente` (por defecto, v1.1) | Depende de factores del propio respondente (sus Likert, una dimensión, promedio, horas de trabajo, semestre, beca…) con las reglas de `config/coherencia_encuestas.json` | Datos con relaciones realistas y verificables (p. ej., a menor promedio, más «Sí» en «¿has reprobado?») |
| `uniforme` (v1.0) | Sorteo con la misma probabilidad para todas las opciones | Reproducir exactamente el acervo original |

```bash
python generate.py --tipo encuesta                                # coherente
python generate.py --tipo encuesta --modelo-adicionales uniforme  # acervo v1.0, idéntico byte a byte con --seed 42
```

Los ítems Likert y los datos de contexto salen **idénticos** en ambos modelos (las respuestas
coherentes usan un generador de números al azar propio de cada instrumento). Tipos soportados:
opción múltiple, Sí/No, escala numérica y, desde la v1.1, selección múltiple (`; `),
jerarquización («Ordena…», `, `) y preguntas abiertas (plantillas por tono). Cómo escribir una
regla: ver la cabecera de `generators/coherencia.py` y la clave `_descripcion` del JSON.

Comprobar las relaciones:

```bash
python generate.py --tipo encuesta --modelo-adicionales uniforme --output /tmp/u --no-charts --no-quality
python generate.py --tipo encuesta --output /tmp/c --no-charts --no-quality
python quality/verificar_coherencia.py /tmp/u /tmp/c
```

## Reproducibilidad

El sistema usa semillas NumPy para resultados reproducibles:
- Semilla base: encuestas (seed), entrevistas (seed+100), pruebas (seed+200)
- Default seed: 42

## Dependencias

```
numpy>=2.0
pandas>=3.0
scipy>=1.10
matplotlib>=3.9
seaborn>=0.13
```
