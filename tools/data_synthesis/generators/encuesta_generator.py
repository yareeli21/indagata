"""
encuesta_generator.py
Generates survey instruments (encuestas): original + respondido + metadata.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .base_generator import BaseGenerator

# ---------------------------------------------------------------------------
# Instrument definitions
# ---------------------------------------------------------------------------
INSTRUMENT_DEFS: dict[str, dict] = {
    "enc_01": {
        "titulo": "Inventario de Estrategias de Aprendizaje y Estudio (IEAE)",
        "fuente": "real",
        "referencia": "Fernández Liporace, M. et al.",
        "n_respondentes": 180,
        "perfiles_permitidos": None,  # all profiles
        "dimensiones": [
            {"nombre": "Organización y planificación", "n_items": 7, "item_type": "normal",
             "items": [
                 "Organizo el material de estudio antes de comenzar a estudiar.",
                 "Elaboro un plan de trabajo con tiempos definidos para cada asignatura.",
                 "Identifico los conceptos principales antes de profundizar en el tema.",
                 "Reviso mis apuntes inmediatamente después de cada clase.",
                 "Establezco metas específicas para cada sesión de estudio.",
                 "Distribuyo el tiempo de estudio de manera equitativa entre las materias.",
                 "Preparo con anticipación los materiales que necesitaré en clase.",
             ]},
            {"nombre": "Habilidades para el examen", "n_items": 3, "item_type": "normal",
             "items": [
                 "Practico con exámenes anteriores para prepararme para las evaluaciones.",
                 "Reviso mis errores de exámenes anteriores para no repetirlos.",
                 "Gestiono bien el tiempo durante la realización de un examen.",
             ]},
            {"nombre": "Motivación", "n_items": 3, "item_type": "motivacion",
             "items": [
                 "Me siento motivado/a para estudiar y aprender en mis clases.",
                 "Encuentro significativo el contenido de lo que estudio.",
                 "Me esfuerzo más cuando el tema me parece interesante.",
             ]},
            {"nombre": "Recursos de aprendizaje", "n_items": 2, "item_type": "normal",
             "items": [
                 "Utilizo distintas fuentes de información para complementar mis apuntes.",
                 "Aprovecho los recursos digitales (videos, podcasts) para reforzar el aprendizaje.",
             ]},
            {"nombre": "Estrategias de control y consolidación", "n_items": 3, "item_type": "normal",
             "items": [
                 "Me autoevalúo para verificar si he comprendido el material.",
                 "Cuando no entiendo algo, busco aclararlo inmediatamente.",
                 "Relaciono los nuevos conocimientos con lo que ya sé.",
             ]},
            {"nombre": "Habilidades para jerarquizar", "n_items": 3, "item_type": "normal",
             "items": [
                 "Distingo entre la información principal y la secundaria en un texto.",
                 "Elaboro resúmenes o esquemas que priorizan los puntos clave.",
                 "Ordeno los temas según su importancia para estudiarlos.",
             ]},
        ],
        "kpis_asociados": [
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Retención / Permanencia Estudiantil",
            "Métricas de Compromiso e Interacción del Estudiante en Plataformas Virtuales",
            "Servicios de Apoyo al Estudiante",
            "Tasa de Deserción / Abandono Estudiantil",
        ],
    },
    "enc_02": {
        "titulo": "Cuestionario de Compromiso Estudiantil (Student Engagement Questionnaire)",
        "fuente": "real",
        "referencia": "Development and validation of student engagement questionnaire, Pakistan",
        "n_respondentes": 200,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Compromiso cognitivo", "n_items": 5, "item_type": "normal",
             "items": [
                 "Reflexiono profundamente sobre los conceptos presentados en clase.",
                 "Conecto los nuevos conocimientos con experiencias previas.",
                 "Me hago preguntas cuando encuentro ideas complejas.",
                 "Reviso el material hasta que lo comprendo completamente.",
                 "Analizo la información de manera crítica antes de aceptarla.",
             ]},
            {"nombre": "Compromiso conductual", "n_items": 5, "item_type": "normal",
             "items": [
                 "Asisto regularmente a todas mis clases.",
                 "Entrego mis tareas y trabajos en los plazos establecidos.",
                 "Participo activamente en las actividades del aula.",
                 "Sigo las instrucciones del docente durante las clases.",
                 "Dedico tiempo fuera del aula para estudiar.",
             ]},
            {"nombre": "Compromiso afectivo", "n_items": 5, "item_type": "motivacion",
             "items": [
                 "Me siento parte importante de mi institución educativa.",
                 "Disfruto de estar en clases y de aprender con mis compañeros.",
                 "Siento que mis profesores se preocupan por mi aprendizaje.",
                 "Me entusiasma aprender cosas nuevas en la universidad.",
                 "Me siento cómodo/a expresando mis opiniones en clase.",
             ]},
            {"nombre": "Compromiso social", "n_items": 4, "item_type": "normal",
             "items": [
                 "Colaboro activamente con mis compañeros en proyectos grupales.",
                 "Busco apoyo de mis pares cuando tengo dificultades académicas.",
                 "Participo en actividades sociales organizadas por la institución.",
                 "Tengo buenas relaciones con mis profesores y compañeros.",
             ]},
        ],
        "kpis_asociados": [
            "Métricas de Compromiso e Interacción del Estudiante en Plataformas Virtuales",
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Asistencia Escolar y Universitaria",
            "Tasa de Finalización de Cursos Online",
            "Satisfacción Estudiantil",
        ],
    },
    "enc_03": {
        "titulo": "Cuestionario de Compromiso Escolar (Student Engagement in Schools Questionnaire – SESQ)",
        "fuente": "real",
        "referencia": "The Student Engagement in Schools Questionnaire",
        "n_respondentes": 220,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Gusto por la escuela", "n_items": 4, "item_type": "motivacion",
             "items": [
                 "Me gusta ir a la universidad.",
                 "Me siento bien cuando estoy en la institución.",
                 "La universidad es un lugar donde me siento aceptado/a.",
                 "Mis experiencias en la institución son positivas.",
             ]},
            {"nombre": "Gusto por aprender", "n_items": 4, "item_type": "motivacion",
             "items": [
                 "Disfruto aprender cosas nuevas en clase.",
                 "El contenido de mis materias me resulta interesante.",
                 "Me gusta enfrentarme a problemas difíciles.",
                 "Aprendo cosas que me serán útiles fuera de la escuela.",
             ]},
            {"nombre": "Comportamiento, esfuerzo y persistencia", "n_items": 9, "item_type": "normal",
             "items": [
                 "Me esfuerzo al máximo en mis tareas y trabajos.",
                 "Cuando algo es difícil, sigo intentándolo hasta lograrlo.",
                 "Presto atención durante las clases.",
                 "Completo mis asignaciones aunque sean difíciles.",
                 "Hago más de lo que se me pide cuando el tema me interesa.",
                 "Me preparo con anticipación para las evaluaciones.",
                 "No me rindo cuando enfrento dificultades académicas.",
                 "Busco ayuda cuando no entiendo algo.",
                 "Me mantengo en clase aunque la materia sea desafiante.",
             ]},
            {"nombre": "Actividades extracurriculares", "n_items": 3, "item_type": "normal",
             "items": [
                 "Participo en clubes, deportes u otras actividades de la institución.",
                 "Asisto a eventos culturales o académicos organizados por la universidad.",
                 "Soy miembro activo de alguna organización estudiantil.",
             ]},
            {"nombre": "Estrategias cognitivas", "n_items": 12, "item_type": "normal",
             "items": [
                 "Repaso el material varias veces para memorizarlo mejor.",
                 "Elaboro preguntas propias sobre lo que he leído.",
                 "Busco el significado de palabras o conceptos que no conozco.",
                 "Uso mapas mentales o diagramas para entender mejor.",
                 "Relaciono lo aprendido con ejemplos de la vida real.",
                 "Hago pausas para reflexionar sobre lo que estoy aprendiendo.",
                 "Identifico los puntos clave de cada tema.",
                 "Evalúo mi comprensión después de cada sección.",
                 "Uso técnicas de estudio activo como el subrayado o los esquemas.",
                 "Repaso el material antes de cada clase.",
                 "Busco conectar temas entre distintas asignaturas.",
                 "Reflexiono sobre cómo podría aplicar lo aprendido.",
             ]},
        ],
        "kpis_asociados": [
            "Métricas de Compromiso e Interacción del Estudiante en Plataformas Virtuales",
            "Oferta de Actividades Extracurriculares",
            "Tasa de Deserción / Abandono Estudiantil",
            "Satisfacción Estudiantil",
            "Tasa de Asistencia Escolar y Universitaria",
        ],
    },
    "enc_04": {
        "titulo": "MSLQ-SF: Cuestionario de Motivación y Estrategias de Aprendizaje Forma Corta",
        "fuente": "real",
        "referencia": "Motivated Strategies for Learning Questionnaire – Short Form (MSLQ-SF)",
        "n_respondentes": 200,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Elaboración", "n_items": 5, "item_type": "normal",
             "items": [
                 "Cuando leo el material para esta clase, trato de relacionarlo con lo que ya sé.",
                 "Cuando estudio, elaboro mis propios ejemplos para entender mejor los conceptos.",
                 "Intento aplicar ideas de las lecturas en actividades o discusiones de clase.",
                 "Formulo mis propias preguntas sobre el material para que me ayuden a enfocarlo.",
                 "Relaciono lo aprendido en esta clase con lo que veo en otras asignaturas.",
             ]},
            {"nombre": "Organización", "n_items": 4, "item_type": "normal",
             "items": [
                 "Cuando estudio, repaso mis apuntes e intento encontrar los conceptos más importantes.",
                 "Realizo esquemas, diagramas o tablas para organizar el material del curso.",
                 "Al estudiar, hago listas de los términos clave y su definición.",
                 "Subrayo las ideas principales de los textos para facilitar el estudio.",
             ]},
            {"nombre": "Pensamiento crítico", "n_items": 5, "item_type": "normal",
             "items": [
                 "Cuando escucho una afirmación, pienso en posibles alternativas.",
                 "Trato de cuestionar lo que escucho o leo antes de aceptarlo.",
                 "Al analizar un problema, busco más de una solución posible.",
                 "Evalúo la solidez de los argumentos que me presentan.",
                 "Intento descubrir suposiciones implícitas en los materiales de clase.",
             ]},
            {"nombre": "Autorregulación metacognitiva", "n_items": 6, "item_type": "normal",
             "items": [
                 "Me hago preguntas para verificar si entendí lo que estudié.",
                 "Si me doy cuenta de que no entiendo algo, tomo medidas para resolverlo.",
                 "Ajusto mi estrategia de estudio cuando me resulta ineficaz.",
                 "Reflexiono sobre lo que aprendo para evaluar si lo he comprendido bien.",
                 "Cuando el trabajo es difícil, me detengo a aclarar mis dudas.",
                 "Reviso mis errores para no repetirlos en el futuro.",
             ]},
            {"nombre": "Gestión del tiempo y del esfuerzo", "n_items": 7, "item_type": "normal",
             "items": [
                 "Suelo estudiar a las mismas horas cada semana.",
                 "Acabo todas las lecturas y actividades asignadas.",
                 "Asisto a todas las clases aunque pueda perderme algo interesante.",
                 "Cuando el trabajo es aburrido, igualmente lo termino.",
                 "Me esfuerzo aunque el material no me sea de interés.",
                 "Establezco prioridades de estudio según la dificultad de cada materia.",
                 "Termino los proyectos aunque me lleven más tiempo de lo esperado.",
             ]},
            {"nombre": "Elaboración con compañeros", "n_items": 3, "item_type": "normal",
             "items": [
                 "Trabajo con otros estudiantes para completar las tareas del curso.",
                 "Explico el material a mis compañeros cuando me lo piden.",
                 "Estudio con otros estudiantes cuando tengo que prepararme para un examen.",
             ]},
            {"nombre": "Motivación intrínseca", "n_items": 4, "item_type": "motivacion",
             "items": [
                 "Prefiero aprender contenidos que realmente me desafíen, aunque cometa errores.",
                 "En esta clase, prefiero materiales que despierten mi curiosidad.",
                 "Me interesa más entender profundamente que solo obtener buenas notas.",
                 "El aprender me produce satisfacción personal más allá de las calificaciones.",
             ]},
            {"nombre": "Autoeficacia", "n_items": 4, "item_type": "rendimiento",
             "items": [
                 "Confío en que podré aprender el material de esta clase.",
                 "Creo que obtendré buenas calificaciones en esta asignatura.",
                 "Me siento capaz de realizar tareas difíciles en este curso.",
                 "Espero desempeñarme bien en esta clase.",
             ]},
        ],
        "kpis_asociados": [
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Graduación / Titulación",
            "Métricas de Compromiso e Interacción del Estudiante en Plataformas Virtuales",
            "Años Promedio para la Graduación (Duración Real del Programa)",
        ],
    },
    "enc_05": {
        "titulo": "Escala RAU de Rendimiento Académico Universitario",
        "fuente": "real",
        "referencia": "Escala RAU",
        "n_respondentes": 180,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Aportación en actividades académicas", "n_items": 5, "item_type": "rendimiento",
             "items": [
                 "Aporto ideas relevantes durante las clases y discusiones.",
                 "Participo activamente en trabajos en equipo.",
                 "Contribuyo con materiales o recursos para las actividades grupales.",
                 "Presento trabajos con calidad superior a la requerida.",
                 "Asumo roles de liderazgo en los proyectos de clase.",
             ]},
            {"nombre": "Dedicación al estudio", "n_items": 6, "item_type": "normal",
             "items": [
                 "Estudio con regularidad, no solo antes de los exámenes.",
                 "Dedico varias horas semanales al estudio de cada materia.",
                 "Leo el material asignado antes de asistir a clase.",
                 "Consulto fuentes adicionales para profundizar en los temas.",
                 "Repaso el material de forma sistemática durante el semestre.",
                 "Me preparo con anticipación para todas las evaluaciones.",
             ]},
            {"nombre": "Falta de organización de recursos", "n_items": 4, "item_type": "normal",
             "items": [
                 "Olvido materiales importantes cuando voy a clase.",
                 "No sé dónde encontrar los recursos necesarios para estudiar.",
                 "Me cuesta organizar mis notas de manera efectiva.",
                 "No llevo un registro de las fechas de entrega de trabajos.",
             ]},
            {"nombre": "Promedio de calificaciones", "n_items": 5, "item_type": "rendimiento",
             "items": [
                 "Mis calificaciones reflejan el esfuerzo que dedico al estudio.",
                 "Mi promedio general ha mejorado a lo largo de los semestres.",
                 "Obtengo calificaciones iguales o superiores a la media del grupo.",
                 "He tenido que repetir pocas o ninguna materia.",
                 "Mis notas me permiten aspirar a becas o reconocimientos.",
             ]},
            {"nombre": "Actividades de estudio", "n_items": 6, "item_type": "normal",
             "items": [
                 "Uso técnicas de estudio específicas (mapas mentales, fichas, etc.).",
                 "Realizo ejercicios de práctica para aplicar lo que aprendo.",
                 "Reviso el material antes de las evaluaciones con suficiente anticipación.",
                 "Trabajo de forma constante a lo largo del semestre.",
                 "Distribuyo las horas de estudio de manera equilibrada.",
                 "Identifico mis áreas débiles y las refuerzo antes de los exámenes.",
             ]},
        ],
        "kpis_asociados": [
            "Tasa de Graduación / Titulación",
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Años Promedio para la Graduación (Duración Real del Programa)",
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Deserción / Abandono Estudiantil",
        ],
    },
    "enc_06": {
        "titulo": "Encuesta de Satisfacción con Servicios Institucionales",
        "fuente": "sintetico",
        "referencia": "Generada sintéticamente – Indagata v1.0",
        "n_respondentes": 160,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Servicios académicos", "n_items": 5, "item_type": "normal",
             "items": [
                 "Los servicios de biblioteca (física y digital) son suficientes para mis necesidades.",
                 "El personal de la institución me orienta adecuadamente.",
                 "Los servicios de tutoría académica son accesibles y útiles.",
                 "Los trámites administrativos son eficientes y rápidos.",
                 "Los laboratorios y talleres están bien equipados.",
             ]},
            {"nombre": "Infraestructura", "n_items": 5, "item_type": "normal",
             "items": [
                 "Las aulas de clase son cómodas y adecuadas para el aprendizaje.",
                 "Las instalaciones deportivas y recreativas son satisfactorias.",
                 "La conectividad a internet del campus es buena.",
                 "Los espacios de estudio individual son suficientes.",
                 "La cafetería ofrece opciones variadas y de buena calidad.",
             ]},
            {"nombre": "Seguridad", "n_items": 5, "item_type": "normal",
             "items": [
                 "Me siento seguro/a dentro del campus universitario.",
                 "Los protocolos de seguridad son visibles y efectivos.",
                 "El acceso controlado al campus me brinda confianza.",
                 "Los servicios de emergencia son accesibles.",
                 "El ambiente del campus es libre de acoso o violencia.",
             ]},
        ],
        "preguntas_adicionales": {
            "opcion_multiple": [
                {"texto": "¿Con qué frecuencia utilizas los servicios de orientación psicológica?",
                 "opciones": ["Nunca", "Una vez al semestre", "Una vez al mes", "Semanalmente"]},
                {"texto": "¿Cómo calificarías la comunicación institucional contigo?",
                 "opciones": ["Muy deficiente", "Deficiente", "Aceptable", "Buena", "Excelente"]},
                {"texto": "¿Cuál servicio usas con más frecuencia?",
                 "opciones": ["Biblioteca", "Laboratorios", "Cafetería", "Tutoría", "Deportes"]},
                {"texto": "¿Recomendarías esta institución a otras personas?",
                 "opciones": ["Definitivamente no", "Probablemente no", "Probablemente sí", "Definitivamente sí"]},
                {"texto": "¿El costo de los servicios complementarios es razonable?",
                 "opciones": ["Totalmente en desacuerdo", "En desacuerdo", "Neutral", "De acuerdo", "Totalmente de acuerdo"]},
            ],
            "si_no": [
                {"texto": "¿Has utilizado el servicio de bolsa de trabajo institucional?"},
                {"texto": "¿Has recibido atención de los servicios de salud del campus?"},
                {"texto": "¿Conoces los programas de becas disponibles en tu institución?"},
            ],
            "escala_numerica": [
                {"texto": "En una escala del 0 al 10, ¿cuán satisfecho/a estás con tu experiencia universitaria en general?",
                 "min": 0, "max": 10},
                {"texto": "En una escala del 0 al 10, ¿qué tan probable es que recomiendes esta institución?",
                 "min": 0, "max": 10},
            ],
        },
        "kpis_asociados": [
            "Satisfacción Estudiantil",
            "Servicios de Apoyo al Estudiante",
            "Proporción de Consejeros/Orientadores por Estudiante",
            "Estadísticas de Seguridad en el Campus (Índice de Criminalidad)",
        ],
    },
    "enc_07": {
        "titulo": "Encuesta de Diversidad e Inclusión en el Aula",
        "fuente": "sintetico",
        "referencia": "Generada sintéticamente – Indagata v1.0",
        "n_respondentes": 160,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Inclusión académica", "n_items": 4, "item_type": "normal",
             "items": [
                 "En mis clases, todos los estudiantes reciben el mismo trato del profesor.",
                 "Se adaptan los contenidos a estudiantes con diferentes capacidades.",
                 "El profesorado fomenta la participación de todos por igual.",
                 "Los materiales de clase representan distintas perspectivas culturales.",
             ]},
            {"nombre": "Diversidad cultural", "n_items": 4, "item_type": "normal",
             "items": [
                 "En mi grupo hay estudiantes de diferentes orígenes culturales.",
                 "Se respetan las distintas tradiciones y visiones del mundo.",
                 "Los docentes promueven el diálogo intercultural.",
                 "Las actividades académicas incorporan ejemplos de contextos diversos.",
             ]},
            {"nombre": "Equidad de género", "n_items": 4, "item_type": "normal",
             "items": [
                 "El trato de los docentes es equitativo independientemente del género.",
                 "No he presenciado situaciones de sexismo o discriminación de género.",
                 "Las mujeres y hombres tienen las mismas oportunidades en el aula.",
                 "Existe respeto hacia las personas con diversas identidades de género.",
             ]},
        ],
        "preguntas_adicionales": {
            "opcion_multiple": [
                {"texto": "¿Con qué frecuencia participas en actividades de celebración de la diversidad?",
                 "opciones": ["Nunca", "Raramente", "A veces", "Frecuentemente"]},
                {"texto": "¿Tu institución ofrece programas de inclusión para personas con discapacidad?",
                 "opciones": ["Sí, y son efectivos", "Sí, pero son limitados", "No los conozco", "No existen"]},
                {"texto": "¿Cuál es tu identidad de género?",
                 "opciones": ["Hombre cisgénero", "Mujer cisgénero", "No binario/a", "Prefiero no decir", "Otro"]},
                {"texto": "¿Eres estudiante de intercambio internacional?",
                 "opciones": ["Sí", "No"]},
            ],
            "si_no": [
                {"texto": "¿Has experimentado algún tipo de discriminación en tu institución?"},
                {"texto": "¿Tienes acceso a becas o apoyos financieros por condición socioeconómica?"},
                {"texto": "¿Tu institución cuenta con protocolos contra el acoso escolar?"},
                {"texto": "¿Participas en organizaciones estudiantiles de diversidad o inclusión?"},
            ],
        },
        "kpis_asociados": [
            "Métricas de Diversidad e Inclusión (Alumnado y Docentes)",
            "Oferta de Actividades Extracurriculares",
            "Alianzas Corporativas y Oportunidades de Pasantías",
            "Porcentaje de Estudiantes que Reciben Ayuda Financiera",
        ],
    },
    "enc_08": {
        "titulo": "Encuesta de Bienestar y Salud Mental Estudiantil",
        "fuente": "sintetico",
        "referencia": "Generada sintéticamente – Indagata v1.0",
        "n_respondentes": 160,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Bienestar emocional", "n_items": 4, "item_type": "normal",
             "items": [
                 "Me siento emocionalmente equilibrado/a durante el semestre.",
                 "Manejo bien el estrés académico que experimento.",
                 "Tengo personas de confianza con quienes hablar de mis problemas.",
                 "Siento que tengo control sobre mi vida universitaria.",
             ]},
            {"nombre": "Estrés académico", "n_items": 3, "item_type": "normal",
             "items": [
                 "La carga académica me genera niveles elevados de ansiedad.",
                 "Siento presión excesiva por las evaluaciones y entregas.",
                 "El rendimiento académico afecta negativamente mi salud mental.",
             ]},
            {"nombre": "Apoyo institucional", "n_items": 3, "item_type": "normal",
             "items": [
                 "La institución cuenta con servicios adecuados de salud mental.",
                 "Es fácil acceder a los servicios psicológicos de la institución.",
                 "Me siento respaldado/a por la institución cuando tengo problemas personales.",
             ]},
        ],
        "preguntas_adicionales": {
            "escala_numerica": [
                {"texto": "En una escala del 1 al 10, ¿cómo calificarías tu nivel de bienestar general?", "min": 1, "max": 10},
                {"texto": "En una escala del 1 al 10, ¿cuánto estrés sientes actualmente por la vida universitaria?", "min": 1, "max": 10},
                {"texto": "En una escala del 1 al 10, ¿cuán satisfecho/a estás con el apoyo emocional recibido?", "min": 1, "max": 10},
            ],
            "opcion_multiple": [
                {"texto": "¿Con qué frecuencia has sentido síntomas de agotamiento (burnout) en el último semestre?",
                 "opciones": ["Nunca", "Raramente", "Ocasionalmente", "Frecuentemente", "Siempre"]},
                {"texto": "¿Has buscado ayuda psicológica profesional durante tu carrera?",
                 "opciones": ["No, nunca", "Sí, en la institución", "Sí, de forma externa", "Estoy considerándolo"]},
                {"texto": "¿Cuál es el principal factor de estrés en tu vida académica?",
                 "opciones": ["Exámenes y evaluaciones", "Trabajo y conciliación", "Economía familiar", "Relaciones interpersonales", "Carga de materias"]},
                {"texto": "¿Con qué frecuencia realizas actividades de autocuidado (deporte, meditación, etc.)?",
                 "opciones": ["Nunca", "Raramente", "Semanalmente", "Diariamente"]},
                {"texto": "¿Has pensado en abandonar los estudios por razones emocionales?",
                 "opciones": ["Nunca", "En algún momento", "Frecuentemente", "Sí, actualmente"]},
            ],
            "si_no": [
                {"texto": "¿Duermes al menos 7 horas diarias en promedio?"},
                {"texto": "¿Tu institución tiene un programa formal de atención a la salud mental estudiantil?"},
            ],
        },
        "kpis_asociados": [
            "Uso de Servicios de Salud Mental Estudiantil",
            "Tasa de Deserción / Abandono Estudiantil",
            "Servicios de Apoyo al Estudiante",
            "Proporción de Consejeros/Orientadores por Estudiante",
            "Satisfacción Estudiantil",
        ],
    },
    "enc_09": {
        "titulo": "Encuesta de Carga Académica y Gestión del Tiempo",
        "fuente": "sintetico",
        "referencia": "Generada sintéticamente – Indagata v1.0",
        "n_respondentes": 160,
        "perfiles_permitidos": None,
        "dimensiones": [
            {"nombre": "Carga horaria percibida", "n_items": 4, "item_type": "normal",
             "items": [
                 "Considero que la cantidad de materias que curso es manejable.",
                 "El volumen de lecturas y tareas es proporcional al crédito de cada materia.",
                 "Tengo tiempo suficiente para estudiar cada materia adecuadamente.",
                 "La carga de trabajo me permite mantener un equilibrio saludable.",
             ]},
            {"nombre": "Organización del tiempo", "n_items": 4, "item_type": "normal",
             "items": [
                 "Planifico mis actividades con anticipación usando agendas o calendarios.",
                 "Cumplo con mis horarios de estudio establecidos.",
                 "Identifico y elimino distracciones durante mis sesiones de estudio.",
                 "Distribuyo el tiempo de manera equilibrada entre todas mis materias.",
             ]},
        ],
        "preguntas_adicionales": {
            "opcion_multiple": [
                {"texto": "¿Cuántas materias cursas actualmente?",
                 "opciones": ["1-2", "3-4", "5-6", "7 o más"]},
                {"texto": "¿Con qué frecuencia dejas tareas para el último momento?",
                 "opciones": ["Nunca", "Raramente", "A veces", "Frecuentemente", "Siempre"]},
                {"texto": "¿Qué estrategia usas más para gestionar tu tiempo?",
                 "opciones": ["Agenda física", "App digital", "Lista de tareas informal", "Sin estrategia definida"]},
                {"texto": "¿Cuántas horas dedicas al estudio fuera de clases por semana?",
                 "opciones": ["Menos de 5h", "5-10h", "10-15h", "15-20h", "Más de 20h"]},
                {"texto": "¿Has reprobado alguna materia por falta de tiempo para estudiar?",
                 "opciones": ["Sí, varias veces", "Sí, una vez", "No, nunca", "Casi lo hago"]},
                {"texto": "¿Cuál es tu carga laboral actual?",
                 "opciones": ["No trabajo", "Trabajo menos de 20h semanales", "Trabajo 20-30h", "Trabajo más de 30h"]},
            ],
            "escala_numerica": [
                {"texto": "¿Cuántas horas por semana dedicas al estudio fuera de clases? (número)", "min": 0, "max": 50},
                {"texto": "Del 1 al 10, ¿cuánta presión sientes por la carga académica?", "min": 1, "max": 10},
                {"texto": "Del 1 al 10, ¿qué tan efectivo/a eres gestionando tu tiempo?", "min": 1, "max": 10},
                {"texto": "¿Cuántos créditos cursas este semestre? (número)", "min": 10, "max": 40},
            ],
            "si_no": [
                {"texto": "¿Tienes dificultades para equilibrar trabajo y estudios?"},
                {"texto": "¿Tu institución ofrece talleres de gestión del tiempo?"},
            ],
        },
        "kpis_asociados": [
            "Años Promedio para la Graduación (Duración Real del Programa)",
            "Tasa de Deserción / Abandono Estudiantil",
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Asistencia Escolar y Universitaria",
            "Ratio de Matriculados frente a Graduados del Curso",
        ],
    },
    "enc_10": {
        "titulo": "Encuesta de Inserción Laboral y Expectativas Profesionales",
        "fuente": "sintetico",
        "referencia": "Generada sintéticamente – Indagata v1.0",
        "n_respondentes": 150,
        "perfiles_permitidos": ["P1", "P2", "P4", "P5", "P7"],
        "dimensiones": [
            {"nombre": "Expectativas laborales", "n_items": 4, "item_type": "normal",
             "items": [
                 "Creo que mi carrera me proporcionará buenas oportunidades laborales.",
                 "Espero trabajar en mi campo de formación al terminar mis estudios.",
                 "Tengo claro qué tipo de empleo buscaré al graduarme.",
                 "Considero que la formación recibida es relevante para el mercado laboral actual.",
             ]},
            {"nombre": "Competencias profesionales", "n_items": 4, "item_type": "rendimiento",
             "items": [
                 "Me siento preparado/a para enfrentar los retos del mundo laboral.",
                 "He desarrollado habilidades prácticas a lo largo de mi carrera.",
                 "Tengo un portafolio o experiencias que puedo presentar a empleadores.",
                 "Las prácticas profesionales o pasantías han enriquecido mi formación.",
             ]},
            {"nombre": "Redes de contacto", "n_items": 2, "item_type": "normal",
             "items": [
                 "He establecido contactos profesionales útiles durante mi carrera.",
                 "Participo en eventos de networking organizados por la institución.",
             ]},
        ],
        "preguntas_adicionales": {
            "opcion_multiple": [
                {"texto": "¿Tienes experiencia laboral en tu área de formación?",
                 "opciones": ["Sí, tiempo completo", "Sí, en prácticas/pasantías", "Sí, como freelance", "No tengo experiencia"]},
                {"texto": "¿Cuál es tu principal motivación para estudiar esta carrera?",
                 "opciones": ["Interés personal", "Oportunidades laborales", "Expectativa familiar", "Ingreso económico esperado"]},
                {"texto": "¿Tienes planes de continuar con estudios de posgrado?",
                 "opciones": ["Sí, inmediatamente", "Sí, en algunos años", "Lo estoy considerando", "No tengo planes"]},
                {"texto": "¿En qué sector laboral esperas trabajar al graduarte?",
                 "opciones": ["Gobierno/Público", "Empresa privada", "ONG/Social", "Emprendimiento propio", "Academia/Investigación"]},
            ],
            "si_no": [
                {"texto": "¿Has realizado prácticas profesionales o pasantías durante tu carrera?"},
                {"texto": "¿Tu institución te ha conectado con empleadores potenciales?"},
                {"texto": "¿Conoces los servicios de bolsa de trabajo de tu institución?"},
            ],
            "escala_numerica": [
                {"texto": "Del 1 al 10, ¿cuán preparado/a te sientes para el mercado laboral?", "min": 1, "max": 10},
                {"texto": "Del 1 al 10, ¿cuánto crees que tu carrera tendrá retorno económico?", "min": 1, "max": 10},
                {"texto": "¿Cuál es el salario mensual mínimo que esperarías recibir al graduarte? (en miles)", "min": 5, "max": 60},
            ],
        },
        "kpis_asociados": [
            "Tasa de Inserción Laboral de Egresados",
            "Alianzas Corporativas y Oportunidades de Pasantías",
            "Ingresos por Educación Continua",
            "Tasa de Estudios de Posgrado",
            "Tasa de Donaciones de Exalumnos (Filantropía de Egresados)",
        ],
    },
}


class EncuestaGenerator(BaseGenerator):
    """Generator for survey instruments."""

    def __init__(self, output_dir: Path, seed: int | None = None):
        super().__init__(seed=seed)
        self.output_dir = output_dir / "encuestas"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def generate_all(self, instrument_ids: list[str] | None = None) -> list[str]:
        """Generate all encuestas. Returns list of generated IDs."""
        ids = instrument_ids or list(INSTRUMENT_DEFS.keys())
        generated = []
        for enc_id in ids:
            if enc_id in INSTRUMENT_DEFS:
                self._generate_one(enc_id)
                generated.append(enc_id)
        return generated

    def generate_n_more(self, n: int) -> list[str]:
        """Generate n more encuestas, continuing from the last generated number."""
        existing = self.read_existing_metadata(self.output_dir, "enc")
        last_num = len(existing)
        all_ids = list(INSTRUMENT_DEFS.keys())
        to_generate = all_ids[last_num: last_num + n]
        return self.generate_all(to_generate)

    # ------------------------------------------------------------------
    def _generate_one(self, enc_id: str) -> None:
        defn = INSTRUMENT_DEFS[enc_id]
        n_resp = defn["n_respondentes"]
        dimensions = defn["dimensiones"]
        allowed_profiles = defn.get("perfiles_permitidos")
        additional = defn.get("preguntas_adicionales", {})

        # --- Sample respondents ---
        all_profiles: list[dict] = []
        all_demographics: list[dict] = []
        all_responses: list[np.ndarray] = []

        # Distribute respondents across profiles
        profile_assignments = self._assign_profiles(n_resp, allowed_profiles)

        likert_items_per_dimension = [d["n_items"] for d in dimensions]
        total_likert = sum(likert_items_per_dimension)
        item_labels = self._build_item_labels(dimensions)

        for profile in profile_assignments:
            block = self.generate_instrument_responses(profile, dimensions, n_respondents=1)
            all_profiles.append(profile["id"])
            all_responses.append(block[0])

        all_demographics = []
        unique_profiles = list({p["id"] for p in profile_assignments})
        profile_map = {p["id"]: p for p in self.profiles}

        respondent_counter = 0
        for i, profile in enumerate(profile_assignments):
            demo = self.generate_demographics(profile, 1)[0]
            demo["id_respondente"] = f"R{i+1:04d}"
            all_demographics.append(demo)

        response_matrix = np.array(all_responses)

        # --- Generate additional question responses ---
        extra_cols = {}
        for q in additional.get("opcion_multiple", []):
            col_name = q["texto"][:40].replace(" ", "_").replace("¿", "").replace("?", "")
            opciones = q["opciones"]
            extra_cols[col_name] = [opciones[self.rng.integers(0, len(opciones))] for _ in range(n_resp)]

        for q in additional.get("si_no", []):
            col_name = q["texto"][:40].replace(" ", "_").replace("¿", "").replace("?", "")
            extra_cols[col_name] = [self.rng.choice(["Sí", "No"]) for _ in range(n_resp)]

        for q in additional.get("escala_numerica", []):
            col_name = q["texto"][:40].replace(" ", "_").replace("¿", "").replace("?", "")
            extra_cols[col_name] = [int(self.rng.integers(q["min"], q["max"] + 1)) for _ in range(n_resp)]

        # --- Build CSV ---
        demo_df = pd.DataFrame(all_demographics)
        likert_df = pd.DataFrame(response_matrix, columns=item_labels)
        extra_df = pd.DataFrame(extra_cols)
        full_df = pd.concat([demo_df, likert_df, extra_df], axis=1)

        csv_path = self.output_dir / f"{enc_id}_respondido.csv"
        full_df.to_csv(csv_path, index=False, encoding="utf-8")

        # --- Compute stats ---
        alpha = self.cronbach_alpha(response_matrix) if total_likert >= 2 else float("nan")
        outliers = self.detect_outliers(response_matrix)
        pct_outliers = float(outliers.mean()) * 100

        # --- Write original instrument ---
        original_text = self._build_original_text(enc_id, defn, additional)
        original_path = self.output_dir / f"{enc_id}_original.txt"
        with open(original_path, "w", encoding="utf-8") as fh:
            fh.write(original_text)

        # --- Write metadata ---
        metadata = {
            "titulo": defn["titulo"],
            "tipo": "encuesta",
            "fuente": defn["fuente"],
            "referencia": defn.get("referencia", ""),
            "n_respondentes": n_resp,
            "n_items": total_likert + sum(
                len(additional.get("opcion_multiple", [])) +
                len(additional.get("si_no", [])) +
                len(additional.get("escala_numerica", []))
                for _ in [1]
            ),
            "tipo_escala": "mixta" if additional else "likert_1_5",
            "dimensiones": [d["nombre"] for d in dimensions],
            "kpis_asociados": defn["kpis_asociados"],
            "parametros_estadisticos": {
                "perfiles_usados": list({p["id"] for p in profile_assignments}),
                "distribucion_base": "beta_rescalada",
                "alpha_cronbach_estimado": round(alpha, 4) if not np.isnan(alpha) else None,
                "pct_outliers_detectados": round(pct_outliers, 2),
                "n_items_likert": total_likert,
            },
            "fecha_generacion": date.today().isoformat(),
        }

        meta_path = self.output_dir / f"{enc_id}_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)

        print(f"  ✓ {enc_id}: {n_resp} respondentes, alpha={alpha:.3f}, outliers={pct_outliers:.1f}%")

    # ------------------------------------------------------------------
    def _assign_profiles(self, n_resp: int, allowed: list[str] | None) -> list[dict]:
        profiles = self.profiles
        if allowed:
            profiles = [p for p in profiles if p["id"] in allowed]
        weights = np.array([p["peso"] for p in profiles], dtype=float)
        weights /= weights.sum()
        idxs = self.rng.choice(len(profiles), size=n_resp, p=weights)
        return [profiles[i] for i in idxs]

    def _build_item_labels(self, dimensions: list[dict]) -> list[str]:
        labels = []
        for dim in dimensions:
            dim_short = dim["nombre"][:15].replace(" ", "_")
            for j in range(dim["n_items"]):
                labels.append(f"{dim_short}_item{j+1}")
        return labels

    def _build_original_text(self, enc_id: str, defn: dict, additional: dict) -> str:
        lines = [
            f"{'='*70}",
            f"INSTRUMENTO: {defn['titulo']}",
            f"ID: {enc_id}",
            f"Fuente: {defn.get('fuente','').upper()} — {defn.get('referencia','')}",
            f"{'='*70}",
            "",
            "INSTRUCCIONES:",
            "Por favor, lee cada afirmación y marca la opción que mejor describe",
            "tu situación actual utilizando la siguiente escala:",
            "",
            "  1 = Totalmente en desacuerdo / Nunca",
            "  2 = En desacuerdo / Pocas veces",
            "  3 = Ni de acuerdo ni en desacuerdo / A veces",
            "  4 = De acuerdo / Frecuentemente",
            "  5 = Totalmente de acuerdo / Siempre",
            "",
        ]

        item_num = 1
        for dim in defn["dimensiones"]:
            lines.append(f"--- {dim['nombre'].upper()} ---")
            lines.append("")
            for item_text in dim["items"]:
                lines.append(f"{item_num}. {item_text}")
                lines.append("   [ ] 1   [ ] 2   [ ] 3   [ ] 4   [ ] 5")
                lines.append("")
                item_num += 1

        if additional:
            if additional.get("opcion_multiple"):
                lines.append("--- PREGUNTAS DE OPCIÓN MÚLTIPLE ---")
                lines.append("")
                for q in additional["opcion_multiple"]:
                    lines.append(f"{item_num}. {q['texto']}")
                    for i, opt in enumerate(q["opciones"]):
                        lines.append(f"   {chr(65+i)}) {opt}")
                    lines.append("")
                    item_num += 1

            if additional.get("si_no"):
                lines.append("--- PREGUNTAS DE SÍ / NO ---")
                lines.append("")
                for q in additional["si_no"]:
                    lines.append(f"{item_num}. {q['texto']}")
                    lines.append("   [ ] Sí   [ ] No")
                    lines.append("")
                    item_num += 1

            if additional.get("escala_numerica"):
                lines.append("--- ESCALAS NUMÉRICAS ---")
                lines.append("")
                for q in additional["escala_numerica"]:
                    lines.append(f"{item_num}. {q['texto']}")
                    lines.append(f"   Rango: {q['min']} — {q['max']}")
                    lines.append(f"   Respuesta: _______")
                    lines.append("")
                    item_num += 1

        lines.append(f"{'='*70}")
        lines.append("FIN DEL INSTRUMENTO")
        lines.append(f"Total de ítems: {item_num - 1}")
        return "\n".join(lines)
