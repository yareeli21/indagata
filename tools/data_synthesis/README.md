# Motor de Datos Sintéticos — Indagata

Genera instrumentos de investigación educativa (encuestas, entrevistas y pruebas) con respuestas sintéticas y
reproducibles: cada respondente es un tipo de estudiante (perfil) y sus respuestas dependen de ese perfil. Cómo
funciona, con los fragmentos de código que lo hacen y un instrumento de cada tipo: Desarrollo X.6
(`documentación/02_Desarrollo.md`).

## Estructura

```
tools/data_synthesis/
  generate.py               # CLI principal
  generar_enc_10_turno.py   # Caso de prueba con resultado conocido (no usa el motor; Pruebas Y.1.3)
  config/
    perfiles_estudiantes.json   # 8 perfiles: proporción, respuesta Likert típica y dispersión, rangos de contexto
    kpi_mapping.json            # Mapeo de KPIs por instrumento
    coherencia_encuestas.json   # Reglas de las preguntas no Likert (modelo «coherente», v1.1)
  generators/
    __init__.py
    base_generator.py           # Perfil, ítems Likert (normal + Cholesky por dimensión) y datos de contexto
    encuesta_generator.py       # Generador de encuestas (11 instrumentos)
    coherencia.py               # Respuestas coherentes de las preguntas no Likert
    entrevista_generator.py     # Generador de entrevistas (10 instrumentos)
    prueba_generator.py         # Generador de pruebas estandarizadas (10 instrumentos, sin respuesta correcta)
  quality/
    checker.py                  # Reporte de calidad (α sobre todas las columnas numéricas, atípicos, correlación)
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

| ID | Título | Tipo | Preguntas | N |
|----|--------|------|--------|---|
| enc_01 | Inventario Estrategias Aprendizaje (IEAE) | Encuesta | De un cuestionario publicado | 180 |
| enc_02 | Student Engagement Questionnaire | Encuesta | De un cuestionario publicado | 200 |
| enc_03 | SESQ | Encuesta | De un cuestionario publicado | 220 |
| enc_04 | MSLQ-SF | Encuesta | De un cuestionario publicado | 200 |
| enc_05 | Escala RAU | Encuesta | De un cuestionario publicado | 180 |
| enc_06 | Satisfacción Servicios Institucionales | Encuesta | Inventadas | 160 |
| enc_07 | Diversidad e Inclusión | Encuesta | Inventadas | 160 |
| enc_08 | Bienestar y Salud Mental | Encuesta | Inventadas | 160 |
| enc_09 | Carga Académica y Tiempo | Encuesta | Inventadas | 160 |
| enc_10 | Inserción Laboral | Encuesta | Inventadas | 150 |
| enc_11 | Trayectoria Académica, Trabajo y Servicios (todos los tipos de pregunta, v1.1) | Encuesta | Inventadas | 160 |
| ent_01 | Estrategias de permanencia | Entrevista | Inventadas | 40 |
| ent_02 | Experiencia docente | Entrevista | Inventadas | 30 |
| ent_03 | Tecnología y aprendizaje | Entrevista | Inventadas | 35 |
| ent_04 | Inclusión y diversidad | Entrevista | Inventadas | 28 |
| ent_05 | Investigación (posgrado) | Entrevista | Inventadas | 25 |
| ent_06 | Orientación vocacional | Entrevista | Inventadas | 32 |
| ent_07 | Vida de campus | Entrevista | Inventadas | 30 |
| ent_08 | Financiamiento | Entrevista | Inventadas | 28 |
| ent_09 | Transición secundaria-uni | Entrevista | Inventadas | 35 |
| ent_10 | Internacionalización | Entrevista | Inventadas | 25 |
| pru_01 | Comprensión Lectora | Prueba | Inventadas | 100 |
| pru_02 | Competencias Matemáticas | Prueba | Inventadas | 110 |
| pru_03 | Alfabetización Digital | Prueba | Inventadas | 95 |
| pru_04 | Aprendizaje Autónomo (CAA) | Prueba | Inventadas | 90 |
| pru_05 | Competencias Docentes | Prueba | Inventadas | 120 |
| pru_06 | Investigación Científica | Prueba | Inventadas | 80 |
| pru_07 | Orientación Vocacional | Prueba | Inventadas | 110 |
| pru_08 | Competencias Interculturales | Prueba | Inventadas | 90 |
| pru_09 | Comunicación Académica | Prueba | Inventadas | 100 |
| pru_10 | Liderazgo Estudiantil | Prueba | Inventadas | 100 |

## Perfiles de estudiantes

Cada respondente recibe uno de 8 perfiles, sorteado con su peso. El perfil fija la respuesta Likert típica (media de
una curva normal), su dispersión y los rangos de los datos de contexto (`config/perfiles_estudiantes.json`):

| Perfil | Nombre | Peso | GPA medio | Likert típico (dispersión) |
|--------|--------|------|-----------|--------------|
| P1 | Alto rendimiento, autoregulado | 12% | 3.75 | 4.2 (0.6) |
| P2 | Promedio comprometido | 20% | 3.15 | 3.4 (0.9) |
| P3 | En riesgo académico | 15% | 2.15 | 2.1 (1.1) |
| P4 | Trabajador adulto tiempo parcial | 13% | 2.90 | 3.0 (1.3) |
| P5 | Avanzado desmotivado (burnout) | 10% | 3.40 | 3.0 (0.8) |
| P6 | Internacional/contexto diverso | 8% | 3.35 | 3.1 (1.0) |
| P7 | Posgrado alta competencia | 12% | 3.85 | 4.5 (0.5) |
| P8 | Dificultades socioeconómicas | 10% | 2.60 | 2.8 (1.2) |

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

## Pruebas y entrevistas

- **Pruebas:** cada reactivo recibe pesos al azar para sus opciones (Dirichlet en opción múltiple, proporción entre
  25 % y 75 % en V/F y Sí/No) y cada alumno elige con esos pesos. No hay respuesta correcta. Los reactivos Likert
  conductuales salen del perfil, igual que en las encuestas.
- **Entrevistas:** cada una se dirige a ciertos perfiles (`perfiles_objetivo`); la respuesta es una frase de las
  plantillas del perfil más una o dos frases de extensión del mismo perfil.

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
