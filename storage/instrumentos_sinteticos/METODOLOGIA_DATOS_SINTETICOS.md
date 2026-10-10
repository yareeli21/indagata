# Metodología de Generación de Datos Sintéticos
## Proyecto Indagata — Repositorio de Instrumentos de Investigación Educativa

**Versión:** 1.0  
**Fecha:** 2026-10-10  
**Sistema:** Motor de datos sintéticos Indagata (`tools/data_synthesis/`)

---

## 1. Justificación del enfoque de datos sintéticos

La generación de datos sintéticos para instrumentos de investigación educativa responde a tres necesidades metodológicas fundamentales:

### 1.1 Privacidad y protección de datos

Los datos reales de estudiantes están sujetos a marcos normativos de protección de información personal (FERPA en EE.UU., GDPR en Europa, LFPDPPP en México). La generación sintética permite demostrar el funcionamiento completo del sistema sin comprometer información de personas reales ni requerir permisos institucionales de uso de datos.

### 1.2 Escasez de datos etiquetados

En investigación educativa, obtener conjuntos de datos suficientemente grandes con etiquetas de KPIs verificadas es un proceso que puede tardar meses o años. Los datos sintéticos permiten acelerar el ciclo de desarrollo, validación y demostración del sistema Indagata sin esperar a la recolección de datos longitudinales.

### 1.3 Variabilidad controlada

Los datos sintéticos permiten representar intencionalmente perfiles estudiantiles subrepresentados en muestras naturales (estudiantes de primera generación, trabajadores adultos, estudiantes con burnout), garantizando que el sistema sea evaluado en condiciones diversas y estadísticamente robustas.

---

## 2. Perfiles de estudiantes: parámetros estadísticos

Los datos se generaron a partir de 8 perfiles de estudiantes universitarios, calibrados con base en literatura de psicología educativa e indicadores de rendimiento académico.

### Tabla de parámetros por perfil

| Perfil | Nombre | Peso (%) | Edad | Universidad | SES | β(α,β) Likert | Media Likert | σ Likert |
|--------|--------|----------|------|-------------|-----|--------------|-------------|---------|
| **P1** | Alto rendimiento, autoregulado | 12 | 18–22 | Privada | Alto | β(6,2) | 4.2 | 0.6 |
| **P2** | Promedio comprometido | 20 | 19–24 | Pública | Medio | β(4,3) | 3.4 | 0.9 |
| **P3** | En riesgo académico | 15 | 17–21 | Pública | Bajo | β(2,5) | 2.1 | 1.1 |
| **P4** | Trabajador adulto (parcial) | 13 | 25–35 | Pública | Medio | β(3,3) | 3.0 | 1.3 |
| **P5** | Avanzado desmotivado (burnout) | 10 | 22–27 | Mixta | Medio | β(3,4) | 2.6/3.8* | 0.8 |
| **P6** | Internacional/diverso | 8 | 18–28 | Privada | Medio-alto | β(3,3) | 3.1 | 1.0 |
| **P7** | Posgrado alta competencia | 12 | 24–35 | Privada | Alto | β(7,2) | 4.5 | 0.5 |
| **P8** | Dificultades socioeconómicas | 10 | 18–26 | Pública | Muy bajo | β(2.5,4) | 2.8 | 1.2 |

*P5 tiene dos distribuciones: motivación (β=2.6) y rendimiento (β=3.8).

### Variables demográficas coherentes por perfil

Cada respondente generado incluye las siguientes variables demográficas, coherentes con su perfil asignado:

- `id_respondente`: Identificador único (R0001...RNNNN)
- `perfil`: Código de perfil (P1–P8)
- `edad`: Muestreado uniformemente del rango del perfil
- `genero`: Masculino / Femenino / Otro (pesos por perfil)
- `semestre`: Muestreado del rango por perfil
- `promedio_gpa`: Uniforme en [gpa_min, gpa_max] del perfil
- `horas_trabajo_semana`: Coherente con la situación laboral del perfil
- `tipo_universidad`: Pública / Privada / Mixta
- `nivel_ses`: Alto / Medio / Bajo / Muy bajo
- `primera_generacion`: Booleano (solo P3)
- `tiene_beca`: Booleano (solo P8)

---

## 3. Técnicas estadísticas utilizadas

### 3.1 Distribuciones beta reescaladas para ítems Likert

Para generar respuestas Likert realistas (escala 1–5), se utilizó la distribución beta con reparametrización al intervalo [1, 5]:

```
X_raw ~ Beta(α, β)
X_likert = round(X_raw × 4 + 1)  →  clipped to [1, 5]
```

La distribución beta fue seleccionada por su flexibilidad para modelar asimetría positiva (perfiles de alto rendimiento: α > β) y negativa (perfiles en riesgo: α < β), así como distribuciones planas (α = β = 3).

### 3.2 Estructura de correlación entre ítems

La correlación realista entre ítems de la misma dimensión fue implementada mediante descomposición de Cholesky:

**Intra-dimensión:** r = U[0.45, 0.65]  
**Inter-dimensión:** r = U[0.10, 0.25]

```python
# Algoritmo de generación correlacionada:
corr_matrix[i,j] = r_intra   (para i≠j, misma dimensión)
L = cholesky(corr_matrix)
Z ~ Normal(0, 1)^(n_resp × n_items)
Z_corr = Z @ L.T
X = Z_corr × σ + μ
```

### 3.3 Patrones de respuesta especiales (sesgo de respuesta)

Para mayor realismo, se inyectaron tres patrones de sesgo de respuesta típicos de la literatura:

| Patrón | Probabilidad | Descripción |
|--------|-------------|-------------|
| Aquiescencia | 1.5% | Respondente marca todo 4–5 |
| Rechazo | 1.5% | Respondente marca todo 1–2 |
| Zigzag | 1.0% | Alternancia 5-1-5-1... |

### 3.4 Modelo de rendimiento en pruebas

El rendimiento en pruebas estandarizadas se modeló con rangos por perfil:

| Perfil | Rango score | Descripción |
|--------|-------------|-------------|
| P1 | 75–95% | Alto rendimiento académico |
| P2 | 55–75% | Rendimiento promedio |
| P3 | 35–60% | Bajo rendimiento, riesgo académico |
| P4 | 50–70% | Rendimiento moderado con irregularidad |
| P5 | 60–75% | Competente pero desmotivado |
| P6 | 45–80% | Alta variabilidad (contexto cultural) |
| P7 | 75–95% | Alto rendimiento (posgrado) |
| P8 | 35–60% | Afectado por condiciones económicas |

Para ítems de opción múltiple, los distractores más cercanos a la respuesta correcta tienen mayor probabilidad de ser seleccionados como error (patrón de error realista, no aleatorio).

### 3.5 Detección de valores atípicos

Se utiliza z-score de las medias por respondente:

```
z_i = |mean(X_i) - mean(means)| / std(means)
outlier si z_i > 3.0
```

---

## 4. Estimaciones de Cronbach Alpha por instrumento

El coeficiente alpha de Cronbach (Cronbach, 1951) fue calculado como:

```
α = (k/(k-1)) × (1 - Σvar_i / var_total)
```

Donde k = número de ítems, var_i = varianza del ítem i, var_total = varianza de la suma total.

### Resultados por instrumento (Likert únicamente)

| Instrumento | Alpha | Estado |
|-------------|-------|--------|
| enc_01 (IEAE) | 0.937 | ✓ Excelente |
| enc_02 (Engagement) | 0.939 | ✓ Excelente |
| enc_03 (SESQ) | 0.957 | ✓ Excelente |
| enc_04 (MSLQ-SF) | 0.960 | ✓ Excelente |
| enc_05 (RAU) | 0.942 | ✓ Excelente |
| enc_06 (Servicios) | 0.940 | ✓ Excelente |
| enc_07 (Diversidad) | 0.916 | ✓ Excelente |
| enc_08 (Bienestar)* | 0.887 | ✓ Bueno |
| enc_09 (Carga)* | 0.914 | ✓ Excelente |
| enc_10 (Laboral)* | 0.882 | ✓ Bueno |
| pru_04 (CAA) | 0.929 | ✓ Excelente |
| pru_07 (Vocacional) | 0.936 | ✓ Excelente |

*Los instrumentos mixtos tienen alpha calculado solo sobre los ítems Likert. Los ítems de opción múltiple, sí/no y escala numérica se excluyen del cálculo de alpha.

**Umbral recomendado:** α ≥ 0.70 (aceptable), α ≥ 0.80 (bueno), α ≥ 0.90 (excelente)

---

## 5. Cómo generar más datos

El motor es re-ejecutable y continúa la numeración desde el último instrumento generado.

### Comandos disponibles

```bash
# Generar todos los instrumentos (idempotente, sobreescribe)
python tools/data_synthesis/generate.py --all

# Generar 3 encuestas adicionales (numeración continua)
python tools/data_synthesis/generate.py --tipo encuesta --n 3

# Generación reproducible (misma semilla = mismos datos)
python tools/data_synthesis/generate.py --all --seed 42

# Solo regenerar visualizaciones
python tools/data_synthesis/generate.py --charts-only

# Solo correr validación de calidad
python tools/data_synthesis/generate.py --quality-only

# Generar sin gráficas ni validación (más rápido)
python tools/data_synthesis/generate.py --all --no-charts --no-quality

# Salida personalizada
python tools/data_synthesis/generate.py --all --output /mi/directorio
```

### Cómo agregar un nuevo instrumento

1. Agregar la definición en el diccionario `INSTRUMENT_DEFS` del generador correspondiente (`encuesta_generator.py`, `entrevista_generator.py`, `prueba_generator.py`).
2. Incluir: `titulo`, `fuente`, `n_respondentes`, `dimensiones` (con ítems), `kpis_asociados`.
3. Ejecutar `python generate.py --tipo <tipo>`.

### Cómo agregar un nuevo perfil de estudiante

1. Editar `config/perfiles_estudiantes.json`.
2. Agregar el perfil con su `id`, `peso`, `edad_rango`, parámetros `likert` (alpha, beta, media, desviacion) y `rendimiento_prueba`.
3. Los pesos deben sumar 1.0.
4. Re-ejecutar la generación.

---

## 6. Limitaciones y consideraciones para la tesis

### 6.1 Naturaleza simulada de los datos

Los datos generados son **probabilísticamente plausibles** pero no provienen de estudiantes reales. Esto implica:

- Las relaciones entre ítems son matemáticamente construidas, no empíricamente observadas.
- Los patrones de respuesta tienen la estructura teórica correcta pero pueden no capturar fenómenos idiosincrásicos de contextos educativos específicos.
- Los datos son útiles para demostración técnica del sistema, pero no deben usarse para extraer conclusiones educativas reales.

### 6.2 Limitaciones del modelo de perfiles

- Los 8 perfiles son simplificaciones tipológicas. La realidad estudiantil es un continuo multidimensional.
- Los pesos de los perfiles (P1=12%, P2=20%, etc.) son supuestos razonables basados en literatura, no en datos censales de instituciones específicas.
- La distribución beta asume unimodalidad; algunos perfiles reales pueden ser bimodales.

### 6.3 Validez para demostración técnica

Los datos sintéticos son **plenamente válidos** para:
- Demostrar el flujo completo del sistema Indagata (carga, procesamiento, vectorización, recuperación RAG)
- Probar los microservicios de análisis y KPIs
- Validar la arquitectura de la base de datos vectorial
- Entrenar y calibrar el grafo de recomendación de instrumentos

### 6.4 Camino hacia datos reales

Para transicionar a datos reales, el sistema acepta cualquier formato de respuesta (CSV, TXT, PDF). El proceso recomendado es:

1. Cargar los instrumentos originales al sistema mediante la API de carga de instrumentos.
2. Recolectar respuestas reales en formato CSV o papel + digitalización.
3. Subir las respuestas mediante el endpoint de carga de respondentes.
4. El sistema calculará KPIs reales automáticamente.

---

## 7. Descripción de los 30 instrumentos generados

### 7.1 Encuestas (10 instrumentos)

| ID | Título | Fuente | N ítems | N respondentes | KPIs principales |
|----|--------|--------|---------|----------------|-----------------|
| enc_01 | Inventario de Estrategias de Aprendizaje y Estudio (IEAE) | Real (Fernández Liporace et al.) | 21 | 180 | Benchmark Test Scores, Learner Engagement |
| enc_02 | Student Engagement Questionnaire (Pakistan) | Real | 19 | 200 | Learner Engagement, Retention Rate |
| enc_03 | Student Engagement in Schools Questionnaire (SESQ) | Real | 32 | 220 | Learner Engagement, Extracurricular Activities |
| enc_04 | MSLQ-SF: Motivación y Estrategias Forma Corta | Real | 37 | 200 | Benchmark Test Scores, Graduation Rate |
| enc_05 | Escala RAU de Rendimiento Académico | Real | 26 | 180 | Graduation Rate, Dropout Rate |
| enc_06 | Satisfacción con Servicios Institucionales | Sintético | 25 | 160 | Student Satisfaction, Support Services |
| enc_07 | Diversidad e Inclusión en el Aula | Sintético | 20 | 160 | Diversity Metrics, Financial Aid |
| enc_08 | Bienestar y Salud Mental Estudiantil | Sintético | 20 | 160 | Mental Health Services, Dropout Rate |
| enc_09 | Carga Académica y Gestión del Tiempo | Sintético | 20 | 160 | Avg. Years to Graduation, Dropout Rate |
| enc_10 | Inserción Laboral y Expectativas Profesionales | Sintético | 20 | 150 | Job Placement Rate, Industry Partnerships |

### 7.2 Entrevistas (10 instrumentos)

| ID | Título | Perfiles | N respondentes | Preguntas | KPIs |
|----|--------|---------|----------------|-----------|------|
| ent_01 | Estrategias de permanencia universitaria | P2,P3,P4,P8 | 40 | 12 | Retention, Dropout |
| ent_02 | Experiencia docente y calidad educativa | P1,P2,P5,P7 | 30 | 10 | Faculty Qualification |
| ent_03 | Tecnología y aprendizaje digital | P1,P2,P3,P6 | 35 | 10 | Learner Engagement |
| ent_04 | Inclusión y diversidad universitaria | P3,P6,P7,P8 | 28 | 8 | Diversity Metrics |
| ent_05 | Investigación académica (posgrado) | P7 | 25 | 10 | Faculty Research Output |
| ent_06 | Orientación vocacional y tutoría | P1,P2,P3,P8 | 32 | 8 | Counselor Ratio |
| ent_07 | Actividades extracurriculares y campus | P1,P2,P5,P6 | 30 | 8 | Extracurricular Activities |
| ent_08 | Financiamiento y accesibilidad | P3,P4,P8 | 28 | 8 | Tuition Fee, Endowment |
| ent_09 | Transición secundaria-universidad | P2,P3,P6,P8 | 35 | 8 | Retention Rate |
| ent_10 | Internacionalización y movilidad | P6,P7 | 25 | 8 | Study Abroad Rate |

### 7.3 Pruebas estandarizadas (10 instrumentos)

| ID | Título | Tipos de ítems | N ítems | N respondentes | KPIs |
|----|--------|---------------|---------|----------------|------|
| pru_01 | Comprensión Lectora Universitaria | MC, V/F, Corta | 25 | 100 | Benchmark Test Scores |
| pru_02 | Competencias Matemáticas Básicas | MC, Numérico, V/F | 20 | 110 | Benchmark Test Scores |
| pru_03 | Alfabetización Digital | MC, V/F, Emparej. | 22 | 95 | Learner Engagement |
| pru_04 | Aprendizaje Autónomo (CAA) | Likert, MC, S/N | 18 | 90 | Benchmark, Retention |
| pru_05 | Competencias Docentes (perspectiva est.) | MC | 20 | 120 | Faculty Qualification |
| pru_06 | Investigación Científica | MC, V/F, Emparej. | 15 | 80 | Faculty Research Output |
| pru_07 | Orientación Vocacional | MC, Preferencias | 25 | 110 | Job Placement Rate |
| pru_08 | Competencias Interculturales | MC, V/F, Escen. | 20 | 90 | Diversity Metrics |
| pru_09 | Comunicación Académica | MC, V/F | 18 | 100 | Benchmark Test Scores |
| pru_10 | Liderazgo Estudiantil | Likert, MC, S/N | 20 | 100 | Extracurricular Activities |

---

## 8. Glosario técnico

| Término | Definición |
|---------|-----------|
| **Alpha de Cronbach** | Coeficiente de consistencia interna; mide la confiabilidad de una escala Likert |
| **Beta distribution** | Distribución de probabilidad continua en [0,1]; flexible para modelar asimetría |
| **Cholesky decomposition** | Factorización de matrices para generar vectores aleatorios con correlación específica |
| **KPI** | Key Performance Indicator; indicador clave de desempeño educativo |
| **Likert scale** | Escala de respuesta ordinal típicamente de 1 a 5 o 1 a 7 |
| **Outlier** | Respondente cuyas respuestas se desvían significativamente de la distribución central |
| **Aquiescencia** | Sesgo de respuesta donde el sujeto tiende a estar de acuerdo con todas las afirmaciones |
| **SES** | Socioeconomic Status; nivel socioeconómico del respondente |
| **Score estimado** | Porcentaje de respuestas correctas estimado para pruebas estandarizadas |

---

## 9. Referencias

- Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. *Psychometrika*, 16(3), 297–334.
- Fernández Liporace, M., et al. (2010). IEAE: Inventario de Estrategias de Aprendizaje y Estudio. *Revista Argentina de Ciencias del Comportamiento*.
- Pintrich, P. R., et al. (1993). Reliability and predictive validity of the Motivated Strategies for Learning Questionnaire (MSLQ). *Educational and Psychological Measurement*, 53, 801–813.
- Skinner, E. A., et al. (2009). A motivational perspective on coping. *Journal of Educational Psychology*.
- Xu, J., et al. (2016). Development and validation of a student engagement questionnaire. *International Journal of Educational Research*.
- Wainer, H., & Kiely, G. L. (1987). Item clusters and computerized adaptive testing. *Journal of Educational Measurement*, 24(3), 185–201.

---

*Documento generado automáticamente por el motor de datos sintéticos Indagata v1.0*  
*Para regenerar este conjunto de datos: `python tools/data_synthesis/generate.py --all --seed 42`*
