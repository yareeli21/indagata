"""
prueba_generator.py
Generates standardized test instruments (pruebas): original + respondido (CSV) + metadata.
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
# Test definitions
# ---------------------------------------------------------------------------
TEST_DEFS: dict[str, dict] = {
    "pru_01": {
        "titulo": "Prueba de Comprensión Lectora Universitaria",
        "kpis_asociados": [
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Aprobación de Exámenes de Certificación",
        ],
        "n_respondentes": 100,
        "secciones": [
            {
                "nombre": "Comprensión de textos académicos",
                "tipo": "opcion_multiple",
                "n_items": 10,
                "texto_base": "Lectura: 'El aprendizaje basado en problemas y su impacto en el desarrollo de competencias universitarias.'",
                "items": [
                    {"pregunta": "Según el texto, ¿cuál es el objetivo principal del aprendizaje basado en problemas?",
                     "opciones": ["A) Memorizar conceptos teóricos", "B) Desarrollar competencias para resolver situaciones reales", "C) Evaluar el rendimiento mediante exámenes", "D) Reducir la carga académica del estudiante"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué papel cumple el docente en el modelo ABP descrito?",
                     "opciones": ["A) Transmisor de información", "B) Evaluador exclusivo", "C) Facilitador del proceso de aprendizaje", "D) Supervisor disciplinario"],
                     "correcta": "C"},
                    {"pregunta": "¿Cuál de las siguientes NO es una competencia que desarrolla el ABP según el texto?",
                     "opciones": ["A) Pensamiento crítico", "B) Memorización mecánica", "C) Trabajo colaborativo", "D) Resolución de problemas"],
                     "correcta": "B"},
                    {"pregunta": "¿En qué nivel educativo ha demostrado ser más efectivo el ABP?",
                     "opciones": ["A) Educación primaria", "B) Bachillerato", "C) Educación universitaria y posgrado", "D) Educación inicial"],
                     "correcta": "C"},
                    {"pregunta": "Según el texto, ¿cómo se mide el éxito en un ambiente ABP?",
                     "opciones": ["A) Por calificaciones numéricas únicamente", "B) Por la solución creativa y fundamentada del problema", "C) Por el tiempo que tarda el estudiante", "D) Por la participación en clase"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué implica la metacognición en el contexto del ABP?",
                     "opciones": ["A) Memorizar el proceso de aprendizaje", "B) Reflexionar sobre el propio proceso de aprendizaje", "C) Ignorar los errores cometidos", "D) Depender del docente para evaluar el aprendizaje"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es una limitación del ABP mencionada en el texto?",
                     "opciones": ["A) Requiere mucho tiempo y recursos", "B) Solo funciona en ciencias exactas", "C) No desarrolla habilidades sociales", "D) Es aplicable solo en posgrado"],
                     "correcta": "A"},
                    {"pregunta": "¿Qué tipo de evaluación predomina en el ABP?",
                     "opciones": ["A) Evaluación sumativa final", "B) Evaluación formativa y continua", "C) Autoevaluación exclusiva", "D) Evaluación por coevaluación únicamente"],
                     "correcta": "B"},
                    {"pregunta": "Según el texto, ¿con qué habilidad del siglo XXI está más relacionado el ABP?",
                     "opciones": ["A) Memorización de datos", "B) Transcripción de información", "C) Pensamiento crítico y resolución de problemas", "D) Obediencia a normas académicas"],
                     "correcta": "C"},
                    {"pregunta": "¿Cuál es la diferencia principal entre el aprendizaje tradicional y el ABP?",
                     "opciones": ["A) El ABP usa más tecnología", "B) El ABP parte de problemas reales para construir conocimiento", "C) El aprendizaje tradicional es más efectivo", "D) No hay diferencias significativas"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Identificación de ideas principales",
                "tipo": "opcion_multiple",
                "n_items": 5,
                "items": [
                    {"pregunta": "¿Cuál de los siguientes párrafos expresa mejor la idea principal de un texto académico bien estructurado?",
                     "opciones": ["A) Una lista de fechas históricas", "B) Una afirmación que sintetiza el argumento central", "C) Una descripción detallada de personajes", "D) Una serie de ejemplos concretos sin conclusión"],
                     "correcta": "B"},
                    {"pregunta": "En un artículo científico, ¿dónde se ubica habitualmente la tesis o idea principal?",
                     "opciones": ["A) En las referencias bibliográficas", "B) En la metodología", "C) En la introducción y las conclusiones", "D) Únicamente en el título"],
                     "correcta": "C"},
                    {"pregunta": "¿Qué estrategia es más efectiva para identificar la idea principal de un texto?",
                     "opciones": ["A) Leer solo el primer párrafo", "B) Buscar palabras clave recurrentes y el argumento central", "C) Leer únicamente las conclusiones", "D) Contar el número de párrafos"],
                     "correcta": "B"},
                    {"pregunta": "Una idea secundaria en un texto académico cumple la función de:",
                     "opciones": ["A) Sustituir a la idea principal", "B) Apoyar, ejemplificar o ampliar la idea principal", "C) Contradecir el argumento central", "D) Resumir el texto completo"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es la función de un párrafo de conclusión en un texto académico?",
                     "opciones": ["A) Introducir nuevas ideas no desarrolladas", "B) Sintetizar las ideas principales y proyectar implicaciones", "C) Repetir literalmente la introducción", "D) Agregar bibliografía adicional"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Verdadero o Falso",
                "tipo": "verdadero_falso",
                "n_items": 5,
                "items": [
                    {"pregunta": "La idea principal siempre se encuentra en el primer párrafo de un texto.", "correcta": "F"},
                    {"pregunta": "El resumen de un artículo científico (abstract) refleja las ideas más importantes del trabajo.", "correcta": "V"},
                    {"pregunta": "En la lectura crítica, el lector acepta todas las afirmaciones del autor sin cuestionarlas.", "correcta": "F"},
                    {"pregunta": "La coherencia textual se refiere a la relación lógica entre las ideas de un texto.", "correcta": "V"},
                    {"pregunta": "Los conectores lógicos no tienen ningún impacto en la comprensión lectora.", "correcta": "F"},
                ],
            },
            {
                "nombre": "Respuesta corta",
                "tipo": "respuesta_corta",
                "n_items": 5,
                "items": [
                    {"pregunta": "Define con tus propias palabras qué es la comprensión lectora inferencial."},
                    {"pregunta": "Menciona dos estrategias de lectura activa que uses en tus estudios."},
                    {"pregunta": "¿Cuál es la diferencia entre parafrasear y plagiar un texto?"},
                    {"pregunta": "¿Por qué es importante identificar el propósito del autor al leer un texto académico?"},
                    {"pregunta": "Explica brevemente qué es la lectura crítica y para qué sirve."},
                ],
            },
        ],
    },
    "pru_02": {
        "titulo": "Prueba de Competencias Matemáticas Básicas",
        "kpis_asociados": [
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Graduación / Titulación",
            "Años Promedio para la Graduación (Duración Real del Programa)",
        ],
        "n_respondentes": 110,
        "secciones": [
            {
                "nombre": "Álgebra y aritmética",
                "tipo": "opcion_multiple",
                "n_items": 7,
                "items": [
                    {"pregunta": "Si x + 5 = 12, ¿cuánto vale x?", "opciones": ["A) 5", "B) 7", "C) 17", "D) 3"], "correcta": "B"},
                    {"pregunta": "¿Cuál es el resultado de 3² + 4²?", "opciones": ["A) 25", "B) 49", "C) 14", "D) 7"], "correcta": "A"},
                    {"pregunta": "Una tienda ofrece 20% de descuento en un artículo de $500. ¿Cuánto se paga?", "opciones": ["A) $400", "B) $480", "C) $450", "D) $420"], "correcta": "A"},
                    {"pregunta": "¿Cuál de los siguientes es un número primo?", "opciones": ["A) 9", "B) 15", "C) 17", "D) 21"], "correcta": "C"},
                    {"pregunta": "Si f(x) = 2x + 3, ¿cuál es f(4)?", "opciones": ["A) 8", "B) 11", "C) 14", "D) 7"], "correcta": "B"},
                    {"pregunta": "¿Cuánto es la raíz cuadrada de 144?", "opciones": ["A) 11", "B) 12", "C) 13", "D) 14"], "correcta": "B"},
                    {"pregunta": "Si se invierten $1000 al 5% anual por 2 años (interés simple), ¿cuánto se obtiene?", "opciones": ["A) $1100", "B) $1050", "C) $1102.50", "D) $1000"], "correcta": "A"},
                ],
            },
            {
                "nombre": "Estadística básica",
                "tipo": "opcion_multiple",
                "n_items": 5,
                "items": [
                    {"pregunta": "En el conjunto {2, 4, 4, 6, 8}, ¿cuál es la moda?", "opciones": ["A) 4", "B) 6", "C) 2", "D) 8"], "correcta": "A"},
                    {"pregunta": "¿Cuál es la mediana de {1, 3, 5, 7, 9}?", "opciones": ["A) 3", "B) 5", "C) 7", "D) 4"], "correcta": "B"},
                    {"pregunta": "Si hay 40 estudiantes y 10 reprueban, ¿cuál es la tasa de reprobación?", "opciones": ["A) 40%", "B) 25%", "C) 10%", "D) 15%"], "correcta": "B"},
                    {"pregunta": "¿Qué mide la desviación estándar?", "opciones": ["A) El valor más frecuente", "B) La dispersión de los datos respecto a la media", "C) El valor central de los datos", "D) El rango de los datos"], "correcta": "B"},
                    {"pregunta": "Si la probabilidad de lluvia es 0.3, ¿cuál es la probabilidad de que NO llueva?", "opciones": ["A) 0.3", "B) 0.5", "C) 0.7", "D) 1.3"], "correcta": "C"},
                ],
            },
            {
                "nombre": "Cálculo numérico",
                "tipo": "calculo_numerico",
                "n_items": 4,
                "items": [
                    {"pregunta": "Calcula: 15 × 23 = ___", "respuesta_correcta": 345},
                    {"pregunta": "Calcula: 144 / 12 = ___", "respuesta_correcta": 12},
                    {"pregunta": "Calcula: 7³ = ___", "respuesta_correcta": 343},
                    {"pregunta": "Un estudiante tiene notas: 7, 8, 6, 9, 10. ¿Cuál es su promedio? ___", "respuesta_correcta": 8.0},
                ],
            },
            {
                "nombre": "Verdadero o Falso matemático",
                "tipo": "verdadero_falso",
                "n_items": 4,
                "items": [
                    {"pregunta": "El número 0 es considerado par.", "correcta": "V"},
                    {"pregunta": "La media aritmética es sensible a los valores atípicos.", "correcta": "V"},
                    {"pregunta": "Un número negativo elevado a un exponente par siempre da negativo.", "correcta": "F"},
                    {"pregunta": "La probabilidad de un evento imposible es 0.", "correcta": "V"},
                ],
            },
        ],
    },
    "pru_03": {
        "titulo": "Prueba de Alfabetización Digital",
        "kpis_asociados": [
            "Métricas de Compromiso e Interacción del Estudiante en Plataformas Virtuales",
            "Uso de Analítica de Aprendizaje",
            "Tasa de Finalización de Cursos Online",
        ],
        "n_respondentes": 95,
        "secciones": [
            {
                "nombre": "Competencias digitales básicas",
                "tipo": "opcion_multiple",
                "n_items": 10,
                "items": [
                    {"pregunta": "¿Cuál es la extensión correcta de un archivo de hoja de cálculo en Excel?", "opciones": ["A) .docx", "B) .xlsx", "C) .pptx", "D) .pdf"], "correcta": "B"},
                    {"pregunta": "¿Qué significa LMS en contextos educativos?", "opciones": ["A) Learning Management System", "B) Library Management Software", "C) Local Messaging System", "D) Lecture Multimedia Server"], "correcta": "A"},
                    {"pregunta": "¿Cuál es la principal función de una VPN?", "opciones": ["A) Aumentar la velocidad de internet", "B) Crear una conexión segura y privada", "C) Bloquear anuncios publicitarios", "D) Almacenar archivos en la nube"], "correcta": "B"},
                    {"pregunta": "¿Qué es el phishing?", "opciones": ["A) Un tipo de búsqueda en Google", "B) Un intento fraudulento de obtener información personal", "C) Una herramienta de edición de imágenes", "D) Un protocolo de transferencia de archivos"], "correcta": "B"},
                    {"pregunta": "¿Cuál herramienta es más adecuada para la colaboración en documentos en tiempo real?", "opciones": ["A) USB compartida", "B) Correo electrónico con adjuntos", "C) Google Docs o Microsoft 365", "D) Imprimir y entregar físicamente"], "correcta": "C"},
                    {"pregunta": "¿Qué es la nube (cloud computing) en tecnología?", "opciones": ["A) Un servidor físico en tu oficina", "B) Almacenamiento y servicios de internet a través de servidores remotos", "C) Una aplicación de mensajería", "D) Un hardware específico"], "correcta": "B"},
                    {"pregunta": "¿Qué significa una licencia Creative Commons?", "opciones": ["A) El contenido es completamente privado", "B) El autor permite ciertos usos de su obra bajo condiciones específicas", "C) El contenido puede ser vendido libremente", "D) El contenido no tiene derechos de autor"], "correcta": "B"},
                    {"pregunta": "¿Cuál es la principal función de un buscador web como Google?", "opciones": ["A) Almacenar información en la nube", "B) Indexar y recuperar páginas web relevantes", "C) Enviar correos electrónicos", "D) Crear presentaciones"], "correcta": "B"},
                    {"pregunta": "¿Cuál de los siguientes es un criterio para evaluar la confiabilidad de una fuente en internet?", "opciones": ["A) El número de visitas del sitio", "B) La autoridad del autor y la fecha de publicación", "C) El diseño visual del sitio web", "D) La cantidad de imágenes que tiene"], "correcta": "B"},
                    {"pregunta": "¿Qué es una contraseña segura?", "opciones": ["A) El nombre de tu mascota", "B) Una combinación de letras, números y símbolos de al menos 12 caracteres", "C) Tu fecha de nacimiento", "D) Una sola palabra del diccionario"], "correcta": "B"},
                ],
            },
            {
                "nombre": "Verdadero o Falso digital",
                "tipo": "verdadero_falso",
                "n_items": 7,
                "items": [
                    {"pregunta": "El correo electrónico es siempre un canal seguro para enviar información confidencial.", "correcta": "F"},
                    {"pregunta": "El análisis de datos de aprendizaje (learning analytics) puede ayudar a identificar estudiantes en riesgo.", "correcta": "V"},
                    {"pregunta": "Plagiar contenido digital tiene las mismas consecuencias éticas que plagiar contenido impreso.", "correcta": "V"},
                    {"pregunta": "La inteligencia artificial puede generar texto, imágenes y código de programación.", "correcta": "V"},
                    {"pregunta": "Usar redes Wi-Fi públicas sin VPN es completamente seguro.", "correcta": "F"},
                    {"pregunta": "El almacenamiento en la nube elimina por completo el riesgo de perder datos.", "correcta": "F"},
                    {"pregunta": "La huella digital incluye todo rastro que dejamos en línea.", "correcta": "V"},
                ],
            },
            {
                "nombre": "Ordenamiento y emparejamiento (codificado como opción múltiple)",
                "tipo": "opcion_multiple",
                "n_items": 5,
                "items": [
                    {"pregunta": "¿Cuál es el orden correcto para crear un documento académico digital? (1) Guardar borrador (2) Investigar (3) Redactar (4) Revisar y citar fuentes",
                     "opciones": ["A) 1-2-3-4", "B) 2-3-1-4", "C) 3-4-2-1", "D) 4-3-2-1"], "correcta": "B"},
                    {"pregunta": "Empareja: HTTPS → ___",
                     "opciones": ["A) Protocolo de mensajería", "B) Protocolo seguro de transferencia web", "C) Servidor de correo", "D) Sistema de archivos"], "correcta": "B"},
                    {"pregunta": "¿Qué herramienta corresponde mejor al propósito de gestionar referencias bibliográficas?",
                     "opciones": ["A) Canva", "B) Zotero o Mendeley", "C) Trello", "D) Photoshop"], "correcta": "B"},
                    {"pregunta": "¿Qué tipo de licencia permite modificar y redistribuir libremente un software?",
                     "opciones": ["A) Propietaria", "B) Freeware", "C) Open Source / Código abierto", "D) Shareware"], "correcta": "C"},
                    {"pregunta": "¿Cuál es el emparejamiento correcto? Big Data ↔ ___",
                     "opciones": ["A) Impresión 3D", "B) Análisis de grandes volúmenes de datos", "C) Redes sociales únicamente", "D) Hardware de almacenamiento físico"], "correcta": "B"},
                ],
            },
        ],
    },
    "pru_04": {
        "titulo": "Evaluación de Competencias para el Aprendizaje Autónomo (CAA)",
        "kpis_asociados": [
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Graduación / Titulación",
        ],
        "n_respondentes": 90,
        "secciones": [
            {
                "nombre": "Conductas de aprendizaje autónomo",
                "tipo": "likert_conductual",
                "n_items": 8,
                "items": [
                    {"pregunta": "Establezco mis propios objetivos de aprendizaje al inicio de cada materia."},
                    {"pregunta": "Busco recursos adicionales cuando no entiendo completamente un tema."},
                    {"pregunta": "Evalúo mi propio progreso sin esperar la retroalimentación del docente."},
                    {"pregunta": "Adapto mis estrategias de estudio cuando los resultados no son los esperados."},
                    {"pregunta": "Gestiono mi tiempo de manera independiente sin necesitar recordatorios externos."},
                    {"pregunta": "Me hago responsable de mis fracasos académicos y busco soluciones."},
                    {"pregunta": "Aprendo de mis errores en evaluaciones anteriores para mejorar."},
                    {"pregunta": "Busco retroalimentación proactivamente para mejorar mi desempeño."},
                ],
            },
            {
                "nombre": "Conocimiento sobre aprendizaje",
                "tipo": "opcion_multiple",
                "n_items": 6,
                "items": [
                    {"pregunta": "¿Qué es la metacognición en el aprendizaje?",
                     "opciones": ["A) La capacidad de memorizar mucha información", "B) El conocimiento y regulación del propio proceso de aprendizaje", "C) La velocidad de lectura", "D) La habilidad para tomar apuntes"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál técnica de estudio está más respaldada por la investigación?",
                     "opciones": ["A) Leer el material una sola vez intensamente", "B) Subrayar todo el texto", "C) Práctica espaciada y recuperación activa", "D) Estudiar solo el día antes del examen"],
                     "correcta": "C"},
                    {"pregunta": "La zona de desarrollo próximo (Vygotsky) se refiere a:",
                     "opciones": ["A) Lo que el estudiante no puede aprender nunca", "B) Lo que el estudiante puede lograr con apoyo de otro más competente", "C) El nivel actual de conocimiento sin ayuda", "D) El espacio físico de aprendizaje"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es un indicador de aprendizaje superficial?",
                     "opciones": ["A) Capacidad de explicar el concepto a otros", "B) Memorización de definiciones sin comprensión", "C) Aplicación de conceptos en situaciones nuevas", "D) Construcción de analogías propias"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la mentalidad de crecimiento (growth mindset)?",
                     "opciones": ["A) Creer que la inteligencia es fija e inamovible", "B) Pensar que las habilidades pueden desarrollarse con esfuerzo", "C) Evitar los desafíos por miedo al fracaso", "D) Depender de la motivación externa"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es el beneficio de la autoexplicación como técnica de estudio?",
                     "opciones": ["A) Ahorra tiempo de estudio", "B) Refuerza la comprensión al verbalizar el razonamiento", "C) Es más efectiva que cualquier otra técnica", "D) Solo sirve para matemáticas"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Autonomía: Sí / No",
                "tipo": "si_no",
                "n_items": 4,
                "items": [
                    {"pregunta": "¿Tienes un horario de estudio personal que cumples regularmente?"},
                    {"pregunta": "¿Buscas fuentes adicionales más allá de las asignadas por el profesor?"},
                    {"pregunta": "¿Has tomado algún curso en línea por iniciativa propia (MOOC, YouTube, etc.)?"},
                    {"pregunta": "¿Te fijas metas de aprendizaje concretas al inicio de cada semestre?"},
                ],
            },
        ],
    },
    "pru_05": {
        "titulo": "Evaluación de Competencias Docentes desde la Perspectiva Estudiantil",
        "kpis_asociados": [
            "Cualificación Docente y Tasa de Rotación del Profesorado",
            "Satisfacción Estudiantil",
            "Tasa de Publicación del Cuerpo Docente",
        ],
        "n_respondentes": 120,
        "secciones": [
            {
                "nombre": "Competencias pedagógicas",
                "tipo": "opcion_multiple",
                "n_items": 10,
                "items": [
                    {"pregunta": "¿Cuál es la característica más importante de un docente universitario efectivo?",
                     "opciones": ["A) Dominar exclusivamente la teoría", "B) Combinar conocimiento disciplinar con habilidades pedagógicas", "C) Usar muchas tecnologías", "D) Impartir clases de forma magistral"],
                     "correcta": "B"},
                    {"pregunta": "Un docente que fomenta el pensamiento crítico principalmente:",
                     "opciones": ["A) Da todas las respuestas antes de que el estudiante reflexione", "B) Plantea preguntas que generan análisis y debate", "C) Solo evalúa mediante exámenes escritos", "D) Impide que los estudiantes pregunten"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué indica la retroalimentación formativa de un docente?",
                     "opciones": ["A) Una calificación final sin comentarios", "B) Comentarios sobre el proceso para mejorar el aprendizaje", "C) La nota de asistencia", "D) La evaluación del comportamiento"],
                     "correcta": "B"},
                    {"pregunta": "Un docente inclusivo en el aula:",
                     "opciones": ["A) Solo atiende a los estudiantes más brillantes", "B) Adapta su enseñanza a las diversas necesidades del grupo", "C) Ignora las diferencias entre los estudiantes", "D) Aplica el mismo método sin variaciones"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es la mejor forma de evaluar la comprensión profunda de un concepto?",
                     "opciones": ["A) Examen de opciones múltiples con fechas", "B) Pedir al estudiante que explique y aplique el concepto en situaciones nuevas", "C) Repetir la definición del libro", "D) Copiar el concepto del pizarrón"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es el aprendizaje activo en el aula universitaria?",
                     "opciones": ["A) Escuchar al profesor sin interrumpir", "B) El estudiante participa, debate, experimenta y construye conocimiento", "C) Leer el libro de texto", "D) Tomar apuntes de manera pasiva"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es el riesgo del uso excesivo de la clase magistral?",
                     "opciones": ["A) Que el docente aprenda demasiado", "B) Que favorezca el aprendizaje pasivo y la falta de participación", "C) Que los estudiantes participen en exceso", "D) Que se use demasiada tecnología"],
                     "correcta": "B"},
                    {"pregunta": "La diversificación de estrategias didácticas permite:",
                     "opciones": ["A) Reducir el esfuerzo del docente", "B) Atender distintos estilos de aprendizaje y mantener el interés", "C) Evaluar menos a los estudiantes", "D) Simplificar el contenido del curso"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué hace un docente que modela habilidades investigativas?",
                     "opciones": ["A) Solo lee artículos en clase", "B) Muestra cómo busca, analiza y aplica conocimiento nuevo", "C) Evita hablar de sus propias investigaciones", "D) Solo da clases teóricas"],
                     "correcta": "B"},
                    {"pregunta": "Un docente con alta inteligencia emocional en el aula:",
                     "opciones": ["A) Ignora el estado emocional de los estudiantes", "B) Reconoce y gestiona las emociones propias y del grupo para favorecer el aprendizaje", "C) Solo se enfoca en los contenidos académicos", "D) Es más permisivo con las entregas"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Evaluación y ética docente",
                "tipo": "opcion_multiple",
                "n_items": 10,
                "items": [
                    {"pregunta": "¿Cuál es una práctica ética esencial en la evaluación docente?",
                     "opciones": ["A) Subir las notas a estudiantes favoritos", "B) Aplicar criterios de evaluación claros, justos y comunicados con anticipación", "C) Cambiar los criterios después del examen", "D) No devolver los exámenes calificados"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué indica la rúbrica de evaluación?",
                     "opciones": ["A) La lista de asistencia", "B) Los criterios y niveles de desempeño esperados", "C) El programa de la materia", "D) Las calificaciones finales"],
                     "correcta": "B"},
                    {"pregunta": "El plagio académico de los estudiantes es responsabilidad exclusivamente de:",
                     "opciones": ["A) El docente", "B) El estudiante y la institución comparten la responsabilidad", "C) Solo la institución", "D) Solo el estudiante"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué debe hacer un docente al detectar deshonestidad académica?",
                     "opciones": ["A) Ignorarla para evitar conflictos", "B) Actuar conforme al protocolo institucional de integridad académica", "C) Reprobar al estudiante sin informarle", "D) Compartirlo públicamente"],
                     "correcta": "B"},
                    {"pregunta": "La evaluación sumativa sirve principalmente para:",
                     "opciones": ["A) Guiar el proceso de aprendizaje durante el curso", "B) Certificar el nivel de logro al final del proceso de aprendizaje", "C) Motivar al estudiante", "D) Diagnosticar conocimientos previos"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué implica la autoevaluación estudiantil como práctica pedagógica?",
                     "opciones": ["A) El estudiante pone su propia nota sin criterios", "B) El estudiante reflexiona sobre su propio aprendizaje con criterios establecidos", "C) El docente no interviene en la evaluación", "D) La calificación siempre es la máxima"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es el objetivo de la evaluación diagnóstica?",
                     "opciones": ["A) Obtener la nota final", "B) Conocer los conocimientos previos para adaptar la enseñanza", "C) Evaluar el comportamiento del estudiante", "D) Determinar quién merece pasar el curso"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la coevaluación?",
                     "opciones": ["A) Cuando el docente evalúa sin criterios", "B) Cuando los estudiantes se evalúan mutuamente con criterios establecidos", "C) Cuando la institución evalúa al docente", "D) Cuando solo se evalúa la asistencia"],
                     "correcta": "B"},
                    {"pregunta": "Un docente que actualiza constantemente su práctica es más probable que:",
                     "opciones": ["A) Abandone la docencia pronto", "B) Mejore la calidad del aprendizaje de sus estudiantes", "C) Genere más carga para los estudiantes", "D) Reciba peores evaluaciones"],
                     "correcta": "B"},
                    {"pregunta": "¿Por qué es importante que el docente conozca las teorías del aprendizaje?",
                     "opciones": ["A) Para memorizar definiciones", "B) Para fundamentar sus decisiones pedagógicas y mejorar su práctica", "C) Para aprobar exámenes de certificación", "D) Para competir con otros docentes"],
                     "correcta": "B"},
                ],
            },
        ],
    },
    "pru_06": {
        "titulo": "Prueba de Competencia en Investigación Científica",
        "kpis_asociados": [
            "Producción Total de Investigación Docente",
            "Financiamiento y Becas de Investigación",
            "Número de Programas Acreditados",
        ],
        "n_respondentes": 80,
        "secciones": [
            {
                "nombre": "Metodología de investigación",
                "tipo": "opcion_multiple",
                "n_items": 8,
                "items": [
                    {"pregunta": "¿Qué caracteriza a la investigación cuantitativa?",
                     "opciones": ["A) El uso de narrativas y significados subjetivos", "B) La medición numérica y el análisis estadístico", "C) La observación participante", "D) Las entrevistas en profundidad"],
                     "correcta": "B"},
                    {"pregunta": "La hipótesis en investigación científica es:",
                     "opciones": ["A) La conclusión final del estudio", "B) Una suposición que se somete a verificación empírica", "C) La descripción del método", "D) El resumen del trabajo"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la validez en un instrumento de medición?",
                     "opciones": ["A) Que dé siempre los mismos resultados", "B) Que mida lo que realmente se pretende medir", "C) Que sea fácil de aplicar", "D) Que tenga muchos ítems"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la triangulación en investigación?",
                     "opciones": ["A) Usar solo un método de recolección de datos", "B) Combinar múltiples métodos o fuentes para validar resultados", "C) Dividir la muestra en tres grupos", "D) Usar estadística triangular"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es la función del marco teórico en una investigación?",
                     "opciones": ["A) Presentar los resultados obtenidos", "B) Sustentar conceptualmente el estudio y situar el problema en la literatura existente", "C) Describir la metodología", "D) Reemplazar los datos empíricos"],
                     "correcta": "B"},
                    {"pregunta": "Un muestreo probabilístico garantiza:",
                     "opciones": ["A) Que todos los individuos de la población tienen igual probabilidad de ser seleccionados", "B) Que la muestra sea muy grande", "C) Que no haya errores en la investigación", "D) Que la investigación sea cualitativa"],
                     "correcta": "A"},
                    {"pregunta": "El coeficiente alpha de Cronbach mide:",
                     "opciones": ["A) La validez del instrumento", "B) La confiabilidad de una escala de medición", "C) La correlación entre dos variables", "D) El tamaño de la muestra"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es una revisión sistemática de literatura?",
                     "opciones": ["A) Leer todos los libros sobre un tema", "B) Una búsqueda estructurada, reproducible y crítica de evidencia sobre un tema", "C) Un resumen personal de lo que se sabe", "D) La bibliografía de un trabajo"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Ética y difusión científica",
                "tipo": "verdadero_falso",
                "n_items": 4,
                "items": [
                    {"pregunta": "El acceso abierto (open access) permite la lectura gratuita de artículos científicos.", "correcta": "V"},
                    {"pregunta": "La fabricación de datos en investigación es éticamente aceptable si el investigador cree que los resultados serán positivos.", "correcta": "F"},
                    {"pregunta": "El factor de impacto de una revista científica indica cuántas veces son citados en promedio sus artículos.", "correcta": "V"},
                    {"pregunta": "Publicar el mismo artículo en dos revistas distintas sin declararlo es una práctica de integridad científica.", "correcta": "F"},
                ],
            },
            {
                "nombre": "Emparejamiento investigativo",
                "tipo": "opcion_multiple",
                "n_items": 3,
                "items": [
                    {"pregunta": "¿Cuál base de datos es específicamente para artículos científicos indizados?",
                     "opciones": ["A) Wikipedia", "B) Scopus o Web of Science", "C) Google Drive", "D) YouTube"], "correcta": "B"},
                    {"pregunta": "El DOI (Digital Object Identifier) sirve para:",
                     "opciones": ["A) Descargar artículos ilegalmente", "B) Identificar de manera permanente y única un documento digital", "C) Crear correos electrónicos académicos", "D) Almacenar datos de investigación"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es un artículo de revisión (review article)?",
                     "opciones": ["A) Un artículo que critica a otros investigadores", "B) Una síntesis crítica del estado del conocimiento sobre un tema específico", "C) El primer artículo de un investigador", "D) Un artículo pendiente de revisión por pares"],
                     "correcta": "B"},
                ],
            },
        ],
    },
    "pru_07": {
        "titulo": "Test de Orientación Vocacional y Aptitudes Profesionales",
        "kpis_asociados": [
            "Tasa de Inserción Laboral de Egresados",
            "Tasa de Estudios de Posgrado",
            "Alianzas Corporativas y Oportunidades de Pasantías",
        ],
        "n_respondentes": 110,
        "secciones": [
            {
                "nombre": "Aptitudes profesionales",
                "tipo": "opcion_multiple",
                "n_items": 15,
                "items": [
                    {"pregunta": "¿En qué ambiente de trabajo te desempeñarías mejor?",
                     "opciones": ["A) Trabajo en solitario con mínima interacción", "B) Trabajo colaborativo con mucha interacción social", "C) Trabajo de campo al aire libre", "D) Trabajo remoto sin supervisión"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué tipo de problemas disfrutas resolver más?",
                     "opciones": ["A) Problemas matemáticos o lógicos", "B) Problemas de comunicación y relaciones humanas", "C) Problemas artísticos y creativos", "D) Problemas técnicos con maquinaria"],
                     "correcta": "A"},
                    {"pregunta": "¿Qué habilidad consideras tu mayor fortaleza?",
                     "opciones": ["A) Análisis de datos", "B) Comunicación persuasiva", "C) Creatividad e innovación", "D) Organización y gestión de proyectos"],
                     "correcta": "A"},
                    {"pregunta": "¿Qué actividad académica disfrutas más?",
                     "opciones": ["A) Resolver ejercicios y problemas", "B) Leer y analizar textos", "C) Hacer presentaciones o debates", "D) Diseñar y crear proyectos"],
                     "correcta": "A"},
                    {"pregunta": "¿Cuál sector laboral te atrae más?",
                     "opciones": ["A) Tecnología e innovación", "B) Salud y bienestar", "C) Arte y entretenimiento", "D) Gobierno y política pública"],
                     "correcta": "A"},
                    {"pregunta": "¿Qué valoras más en un trabajo?",
                     "opciones": ["A) Estabilidad económica", "B) Impacto social y significado", "C) Autonomía y flexibilidad", "D) Reconocimiento y estatus"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál descripción te identifica mejor como profesional?",
                     "opciones": ["A) Analítico/a y orientado/a a datos", "B) Empático/a y orientado/a a personas", "C) Creativo/a e innovador/a", "D) Organizado/a y gestor/a de procesos"],
                     "correcta": "A"},
                    {"pregunta": "¿Preferirías trabajar en qué tipo de organización?",
                     "opciones": ["A) Empresa multinacional grande", "B) Startup o empresa pequeña", "C) Organización sin fines de lucro", "D) Institución académica o investigativa"],
                     "correcta": "D"},
                    {"pregunta": "¿Cuándo enfrentas una decisión difícil, ¿qué haces primero?",
                     "opciones": ["A) Analizo datos y evidencias disponibles", "B) Consulto con personas de confianza", "C) Confío en mi intuición", "D) Reviso procedimientos establecidos"],
                     "correcta": "A"},
                    {"pregunta": "¿Cuál de estas habilidades te gustaría desarrollar más?",
                     "opciones": ["A) Liderazgo", "B) Programación", "C) Negociación", "D) Investigación y análisis"],
                     "correcta": "D"},
                    {"pregunta": "¿Cómo te sientes al trabajar en equipo?",
                     "opciones": ["A) Prefiero trabajar solo/a", "B) Disfruto colaborar si hay roles claros", "C) Me adapto a cualquier dinámica", "D) Solo colaboro cuando es estrictamente necesario"],
                     "correcta": "C"},
                    {"pregunta": "¿En cuál área te sientes más competente?",
                     "opciones": ["A) Ciencias exactas y tecnología", "B) Humanidades y ciencias sociales", "C) Arte y diseño", "D) Administración y negocios"],
                     "correcta": "A"},
                    {"pregunta": "¿Cuál es tu principal motivación profesional a largo plazo?",
                     "opciones": ["A) Maximizar ingresos económicos", "B) Generar impacto positivo en la sociedad", "C) Ser reconocido/a en mi campo", "D) Construir un negocio propio"],
                     "correcta": "B"},
                    {"pregunta": "¿Cómo prefieres aprender nuevas habilidades profesionales?",
                     "opciones": ["A) Cursos formales y certificaciones", "B) Práctica directa en proyectos reales", "C) Mentoría de expertos", "D) Autoaprendizaje con recursos en línea"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál aspecto del mundo laboral te preocupa más?",
                     "opciones": ["A) La automatización y el desempleo tecnológico", "B) La falta de oportunidades en mi campo", "C) La inestabilidad económica global", "D) La dificultad para lograr equilibrio trabajo-vida"],
                     "correcta": "D"},
                ],
            },
            {
                "nombre": "Escalas de preferencia profesional",
                "tipo": "likert_conductual",
                "n_items": 10,
                "items": [
                    {"pregunta": "Me interesa trabajar en proyectos relacionados con la educación y el desarrollo humano."},
                    {"pregunta": "Me atrae la posibilidad de trabajar en investigación científica o académica."},
                    {"pregunta": "Prefiero entornos laborales predecibles y con procedimientos claros."},
                    {"pregunta": "Me entusiasma emprender y crear mis propios proyectos profesionales."},
                    {"pregunta": "Me importa que mi trabajo tenga un impacto social visible."},
                    {"pregunta": "Valoro el desarrollo continuo de habilidades y la formación permanente."},
                    {"pregunta": "Me interesa trabajar en entornos internacionales o multiculturales."},
                    {"pregunta": "Prefiero trabajos que me permitan tener autonomía en mis decisiones."},
                    {"pregunta": "Me motiva competir y superar metas de desempeño profesional."},
                    {"pregunta": "Aspiro a posiciones de liderazgo o gestión a lo largo de mi carrera."},
                ],
            },
        ],
    },
    "pru_08": {
        "titulo": "Evaluación de Competencias Interculturales",
        "kpis_asociados": [
            "Métricas de Diversidad e Inclusión (Alumnado y Docentes)",
            "Ratio de Estudiantes Nacionales vs. Internacionales",
            "Tasa de Participación en Estudios en el Extranjero",
        ],
        "n_respondentes": 90,
        "secciones": [
            {
                "nombre": "Conocimiento intercultural",
                "tipo": "opcion_multiple",
                "n_items": 10,
                "items": [
                    {"pregunta": "¿Qué es la competencia intercultural?",
                     "opciones": ["A) Saber hablar varios idiomas", "B) La capacidad de comunicarse y actuar efectivamente en contextos culturalmente diversos", "C) Conocer la historia de otros países", "D) Haber vivido en el extranjero"],
                     "correcta": "B"},
                    {"pregunta": "El etnocentrismo en contextos académicos implica:",
                     "opciones": ["A) Apreciar otras culturas como iguales", "B) Juzgar otras culturas usando los propios valores como referencia", "C) Estudiar múltiples idiomas", "D) Fomentar el diálogo intercultural"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál práctica favorece el aprendizaje intercultural en el aula?",
                     "opciones": ["A) Usar solo materiales de la cultura local", "B) Incorporar perspectivas y autores de diversas culturas", "C) Evitar temas políticamente sensibles", "D) Separar a los estudiantes por nacionalidad"],
                     "correcta": "B"},
                    {"pregunta": "La comunicación no verbal es especialmente relevante en contextos interculturales porque:",
                     "opciones": ["A) Es idéntica en todas las culturas", "B) Puede tener significados muy diferentes según la cultura", "C) No influye en la comunicación real", "D) Solo es importante en idiomas no europeos"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la sensibilidad cultural?",
                     "opciones": ["A) Saber comer comida de otros países", "B) La conciencia y respeto genuino hacia las diferencias culturales", "C) Hablar en voz baja con extranjeros", "D) Evitar contacto con personas de otras culturas"],
                     "correcta": "B"},
                    {"pregunta": "En las dimensiones culturales de Hofstede, la 'distancia al poder' se refiere a:",
                     "opciones": ["A) La distancia física entre países", "B) El grado en que los miembros menos poderosos aceptan la distribución desigual del poder", "C) La diferencia de idiomas entre culturas", "D) El nivel económico de un país"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es una barrera común en la comunicación intercultural?",
                     "opciones": ["A) Conocer demasiados idiomas", "B) Los estereotipos y prejuicios culturales", "C) La tecnología de comunicación", "D) Viajar con frecuencia"],
                     "correcta": "B"},
                    {"pregunta": "El concepto de 'choque cultural' describe:",
                     "opciones": ["A) Un accidente en el extranjero", "B) La incomodidad o desorientación al adaptarse a una nueva cultura", "C) El aprendizaje acelerado de un nuevo idioma", "D) Una celebración multicultural"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué fomenta el desarrollo de la empatía intercultural?",
                     "opciones": ["A) Evitar interactuar con personas diferentes", "B) Escuchar activamente y ponerse en el lugar del otro culturalmente", "C) Juzgar las prácticas ajenas con los propios valores", "D) Assumir que todos piensan igual"],
                     "correcta": "B"},
                    {"pregunta": "¿Por qué es relevante la diversidad cultural en la educación superior?",
                     "opciones": ["A) No tiene ninguna relevancia académica", "B) Enriquece el aprendizaje, amplía perspectivas y prepara para entornos globales", "C) Solo es útil para carreras de idiomas", "D) Complica la gestión académica"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Verdadero / Falso intercultural",
                "tipo": "verdadero_falso",
                "n_items": 5,
                "items": [
                    {"pregunta": "La globalización ha reducido completamente las diferencias culturales.", "correcta": "F"},
                    {"pregunta": "Los estereotipos culturales siempre tienen una base de verdad estadística significativa.", "correcta": "F"},
                    {"pregunta": "El bilingüismo o multilingüismo facilita la competencia intercultural.", "correcta": "V"},
                    {"pregunta": "En algunas culturas, el contacto visual directo se considera irrespetuoso.", "correcta": "V"},
                    {"pregunta": "La diversidad cultural en las aulas solo genera conflictos y no aporta valor académico.", "correcta": "F"},
                ],
            },
            {
                "nombre": "Escenarios interculturales",
                "tipo": "opcion_multiple",
                "n_items": 5,
                "items": [
                    {"pregunta": "Un estudiante internacional no participa en clase. ¿Cuál es la respuesta más apropiada del docente?",
                     "opciones": ["A) Ignorarlo", "B) Investigar si hay barreras culturales o idiomáticas y brindar apoyo", "C) Llamarle la atención públicamente", "D) Reducir su calificación de participación"],
                     "correcta": "B"},
                    {"pregunta": "Un grupo de trabajo tiene conflicto por diferentes estilos de comunicación cultural. El mejor enfoque es:",
                     "opciones": ["A) Asignar roles según la cultura de origen", "B) Dialogar sobre las diferencias y establecer normas de comunicación compartidas", "C) Disolver el grupo", "D) Ignorar el conflicto"],
                     "correcta": "B"},
                    {"pregunta": "Un estudiante de intercambio celebra una festividad que el resto desconoce. ¿Cuál es la actitud intercultural correcta?",
                     "opciones": ["A) Ignorarla para no perder tiempo de clase", "B) Mostrar curiosidad y permitir que comparta su tradición como aprendizaje cultural", "C) Pedirle que no hable de eso en clase", "D) Asumir que es inferior a las festividades locales"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es el primer paso ante una incomprensión cultural en contexto académico?",
                     "opciones": ["A) Ignorarla", "B) Pedir aclaración con respeto y sin asumir intenciones negativas", "C) Reportar al docente sin hablar primero", "D) Publicarlo en redes sociales"],
                     "correcta": "B"},
                    {"pregunta": "Un docente nota que sus materiales de clase son culturalmente sesgados. ¿Qué debe hacer?",
                     "opciones": ["A) Ignorarlo porque es su cultura", "B) Revisar y diversificar las fuentes y ejemplos utilizados", "C) Continuar igual para mantener la coherencia", "D) Eliminar todo el contenido cultural"],
                     "correcta": "B"},
                ],
            },
        ],
    },
    "pru_09": {
        "titulo": "Prueba de Habilidades de Comunicación Académica",
        "kpis_asociados": [
            "Puntajes en Pruebas Estandarizadas de Referencia",
            "Tasa de Aprobación de Exámenes de Certificación",
            "Cualificación Docente y Tasa de Rotación del Profesorado",
        ],
        "n_respondentes": 100,
        "secciones": [
            {
                "nombre": "Escritura académica",
                "tipo": "opcion_multiple",
                "n_items": 12,
                "items": [
                    {"pregunta": "¿Cuál es la estructura básica de un texto académico argumentativo?",
                     "opciones": ["A) Lista de datos-Conclusión", "B) Introducción-Desarrollo-Conclusión", "C) Resumen-Ejemplos-Datos", "D) Preguntas-Respuestas-Preguntas"],
                     "correcta": "B"},
                    {"pregunta": "El abstract de un artículo académico debe incluir:",
                     "opciones": ["A) Referencias bibliográficas detalladas", "B) Objetivo, metodología, resultados y conclusiones en forma concisa", "C) Los datos crudos de la investigación", "D) Una opinión personal del autor"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál conectivo indica contraste o contraposición?",
                     "opciones": ["A) Además", "B) Por lo tanto", "C) Sin embargo", "D) Por ejemplo"],
                     "correcta": "C"},
                    {"pregunta": "La coherencia textual se refiere a:",
                     "opciones": ["A) Usar muchas citas bibliográficas", "B) La relación lógica y progresiva de las ideas", "C) El número de palabras del texto", "D) El uso correcto de la puntuación"],
                     "correcta": "B"},
                    {"pregunta": "En el estilo APA, una cita directa de más de 40 palabras se presenta:",
                     "opciones": ["A) En negrita dentro del párrafo", "B) En un bloque de texto sangrado, sin comillas", "C) En cursiva y entre comillas", "D) Solo en la bibliografía"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es la diferencia entre paráfrasis y cita directa?",
                     "opciones": ["A) No hay diferencia", "B) La paráfrasis reformula las ideas con palabras propias; la cita directa reproduce textualmente", "C) La cita directa es siempre más corta", "D) La paráfrasis no requiere citar la fuente"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la cohesión textual?",
                     "opciones": ["A) La argumentación lógica del texto", "B) Los mecanismos lingüísticos que conectan las oraciones y párrafos", "C) El número de referencias citadas", "D) La longitud del texto"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál de las siguientes es una fuente primaria?",
                     "opciones": ["A) Una enciclopedia general", "B) Un artículo de revisión", "C) Un experimento o estudio original", "D) Un manual de texto"],
                     "correcta": "C"},
                    {"pregunta": "¿Qué función cumple la discusión en un artículo científico?",
                     "opciones": ["A) Repetir los resultados numéricos", "B) Interpretar los resultados en relación con la literatura y las hipótesis", "C) Presentar la metodología", "D) Listar las referencias"],
                     "correcta": "B"},
                    {"pregunta": "¿Por qué es importante el uso de lenguaje no sexista en la escritura académica?",
                     "opciones": ["A) Por estética únicamente", "B) Para promover la equidad de género e inclusión en el discurso", "C) Para cumplir un requisito editorial sin relevancia real", "D) Porque lo exige la gramática española"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es la función de las notas al pie en un texto académico?",
                     "opciones": ["A) Reemplazar la bibliografía", "B) Ampliar información secundaria o aclarar aspectos sin interrumpir el flujo principal", "C) Resumir el texto", "D) Citar fuentes en formato APA"],
                     "correcta": "B"},
                    {"pregunta": "El plagio involuntario ocurre cuando:",
                     "opciones": ["A) El autor copia intencionalmente sin citar", "B) Se usa información de otros sin citar por desconocimiento o descuido", "C) Se inventa información", "D) Se autoplagia conscientemente"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Verdadero / Falso - comunicación académica",
                "tipo": "verdadero_falso",
                "n_items": 6,
                "items": [
                    {"pregunta": "Un buen resumen académico puede incluir la opinión personal del autor.", "correcta": "F"},
                    {"pregunta": "El uso de un lenguaje formal en textos académicos implica evitar coloquialismos.", "correcta": "V"},
                    {"pregunta": "Reformular correctamente la idea de otro autor sin citarlo es una práctica académica aceptable.", "correcta": "F"},
                    {"pregunta": "La revisión por pares garantiza la calidad y rigor de un artículo científico.", "correcta": "V"},
                    {"pregunta": "En la escritura académica, los argumentos siempre deben estar respaldados por evidencia.", "correcta": "V"},
                    {"pregunta": "El uso excesivo de vocabulario técnico mejora siempre la claridad de un texto.", "correcta": "F"},
                ],
            },
        ],
    },
    "pru_10": {
        "titulo": "Evaluación de Liderazgo y Participación Estudiantil",
        "kpis_asociados": [
            "Oferta de Actividades Extracurriculares",
            "Tasa de Retención / Permanencia Estudiantil",
            "Satisfacción Estudiantil",
        ],
        "n_respondentes": 100,
        "secciones": [
            {
                "nombre": "Habilidades de liderazgo (Likert conductual)",
                "tipo": "likert_conductual",
                "n_items": 8,
                "items": [
                    {"pregunta": "Tomo la iniciativa en proyectos grupales cuando se necesita liderazgo."},
                    {"pregunta": "Motivo a mis compañeros cuando el grupo enfrenta dificultades."},
                    {"pregunta": "Comunico mis ideas con claridad en contextos grupales."},
                    {"pregunta": "Tomo decisiones considerando el bienestar de todo el grupo."},
                    {"pregunta": "Resuelvo conflictos de manera constructiva en situaciones de desacuerdo."},
                    {"pregunta": "Reconozco las fortalezas de mis compañeros y las aprovecho en el trabajo conjunto."},
                    {"pregunta": "Me mantengo calmado/a bajo presión y ayudo al grupo a mantener el enfoque."},
                    {"pregunta": "Busco retroalimentación del grupo para mejorar mi desempeño como líder."},
                ],
            },
            {
                "nombre": "Conocimiento sobre liderazgo",
                "tipo": "opcion_multiple",
                "n_items": 8,
                "items": [
                    {"pregunta": "¿Cuál es la principal diferencia entre un líder y un jefe?",
                     "opciones": ["A) El líder tiene más autoridad formal", "B) El líder influye por respeto y confianza, no solo por posición jerárquica", "C) El jefe es más efectivo", "D) No hay diferencia relevante"],
                     "correcta": "B"},
                    {"pregunta": "El liderazgo transformacional se caracteriza por:",
                     "opciones": ["A) Enfocarse solo en las tareas y resultados", "B) Inspirar y motivar a los seguidores hacia una visión compartida", "C) Aplicar recompensas y castigos", "D) Mantener el statu quo"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál es una característica del liderazgo situacional?",
                     "opciones": ["A) Aplicar siempre el mismo estilo sin importar el contexto", "B) Adaptar el estilo de liderazgo según el nivel de madurez del equipo", "C) Tomar todas las decisiones sin consultar", "D) Evitar dar retroalimentación negativa"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué implica la inteligencia emocional en el liderazgo estudiantil?",
                     "opciones": ["A) Ignorar las emociones para ser más efectivo", "B) Reconocer, gestionar y responder a las emociones propias y ajenas de manera constructiva", "C) Mostrar siempre entusiasmo sin importar la situación", "D) Evitar el conflicto a toda costa"],
                     "correcta": "B"},
                    {"pregunta": "¿Cómo puede un estudiante desarrollar habilidades de liderazgo?",
                     "opciones": ["A) Esperando a ser elegido formalmente", "B) Participando activamente en proyectos, organizaciones y roles de responsabilidad", "C) Solo leyendo libros de liderazgo", "D) Siendo el más inteligente del grupo"],
                     "correcta": "B"},
                    {"pregunta": "¿Qué es la escucha activa en el liderazgo?",
                     "opciones": ["A) Fingir atención mientras se piensa en otra cosa", "B) Prestar atención plena al interlocutor y responder de manera reflexiva", "C) Solo escuchar para rebatir", "D) Interrumpir para mostrar interés"],
                     "correcta": "B"},
                    {"pregunta": "¿Cuál comportamiento indica falta de habilidades de liderazgo?",
                     "opciones": ["A) Delegar responsabilidades apropiadamente", "B) Tomar todo el crédito y no reconocer el trabajo del equipo", "C) Pedir retroalimentación constantemente", "D) Admitir errores y aprender de ellos"],
                     "correcta": "B"},
                    {"pregunta": "La toma de decisiones en grupo se beneficia de la diversidad porque:",
                     "opciones": ["A) Hace el proceso más lento sin añadir valor", "B) Aporta perspectivas variadas que reducen los sesgos y mejoran la calidad de las decisiones", "C) Garantiza que todos estén de acuerdo", "D) Evita que el líder tenga que decidir solo"],
                     "correcta": "B"},
                ],
            },
            {
                "nombre": "Participación estudiantil: Sí / No",
                "tipo": "si_no",
                "n_items": 4,
                "items": [
                    {"pregunta": "¿Has ocupado un cargo de representación estudiantil (delegado/a, presidente de sociedad, etc.)?"},
                    {"pregunta": "¿Participas en organizaciones estudiantiles de tu institución?"},
                    {"pregunta": "¿Has liderado algún proyecto o iniciativa grupal en tu trayectoria universitaria?"},
                    {"pregunta": "¿Tu institución ofrece formación formal en habilidades de liderazgo estudiantil?"},
                ],
            },
        ],
    },
}


class PruebaGenerator(BaseGenerator):
    """Generator for standardized test instruments."""

    def __init__(self, output_dir: Path, seed: int | None = None):
        super().__init__(seed=seed)
        self.output_dir = output_dir / "pruebas"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, instrument_ids: list[str] | None = None) -> list[str]:
        ids = instrument_ids or list(TEST_DEFS.keys())
        generated = []
        for pru_id in ids:
            if pru_id in TEST_DEFS:
                self._generate_one(pru_id)
                generated.append(pru_id)
        return generated

    def _generate_one(self, pru_id: str) -> None:
        defn = TEST_DEFS[pru_id]
        n_resp = defn["n_respondentes"]
        secciones = defn["secciones"]

        # Assign profiles
        profiles_assigned = self._assign_all_profiles(n_resp)

        # Generate responses
        all_rows: list[dict] = []
        likert_scores: list[np.ndarray] = []

        for i, profile in enumerate(profiles_assigned):
            demo = self.generate_demographics(profile, 1)[0]
            demo["id_respondente"] = f"R{i+1:04d}"
            row = dict(demo)

            perf_min = profile["rendimiento_prueba"]["min"]
            perf_max = profile["rendimiento_prueba"]["max"]
            base_score = float(self.rng.uniform(perf_min, perf_max))

            likert_row_items = []

            for sec in secciones:
                tipo = sec["tipo"]
                items = sec["items"]

                if tipo == "opcion_multiple":
                    for j, item in enumerate(items):
                        correcta = item["correcta"]
                        opciones = item["opciones"]
                        # Wrong answer with realistic patterns
                        if self.rng.random() < base_score:
                            row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = correcta
                        else:
                            wrong = [o[0] for o in opciones if o[0] != correcta]
                            # Weight wrong answers: distractors near correct are more likely
                            w = np.array([1.0, 0.5, 0.25][:len(wrong)])
                            w = w / w.sum()
                            row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = (
                                self.rng.choice(wrong, p=w)
                            )

                elif tipo == "verdadero_falso":
                    for j, item in enumerate(items):
                        correcta = item["correcta"]
                        if self.rng.random() < base_score:
                            row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = correcta
                        else:
                            row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = "V" if correcta == "F" else "F"

                elif tipo == "calculo_numerico":
                    for j, item in enumerate(items):
                        correct_val = item["respuesta_correcta"]
                        if self.rng.random() < base_score:
                            row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = correct_val
                        else:
                            # Add a plausible error
                            error = float(correct_val) * self.rng.uniform(0.7, 1.4)
                            row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = round(error, 1)

                elif tipo == "respuesta_corta":
                    for j, item in enumerate(items):
                        # Encode as quality score 0-2
                        quality = int(self.rng.integers(0, 3)) if base_score < 0.6 else int(self.rng.integers(1, 3))
                        row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = quality

                elif tipo in ("likert_conductual", "likert"):
                    profile_for_likert = {**profile, "likert": {
                        "alpha": 2 + base_score * 6,
                        "beta": 2 + (1 - base_score) * 4,
                        "media_estimada": 1 + base_score * 4,
                        "desviacion_estimada": 0.8,
                    }}
                    block = self.generate_correlated_block(profile_for_likert, len(items), 1)
                    for j in range(len(items)):
                        row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = int(block[0, j])
                    likert_row_items.extend(block[0].tolist())

                elif tipo == "si_no":
                    for j, item in enumerate(items):
                        row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = (
                            "Sí" if self.rng.random() < base_score else "No"
                        )

                elif tipo == "escala_preferencia":
                    for j, item in enumerate(items):
                        val = int(self.rng.integers(1, 6))
                        row[f"{pru_id}_{sec['nombre'][:10]}_q{j+1}"] = val
                        likert_row_items.append(val)

            row["score_estimado"] = round(base_score, 3)
            all_rows.append(row)
            if likert_row_items:
                likert_scores.append(np.array(likert_row_items))

        # Build dataframe
        df = pd.DataFrame(all_rows)
        csv_path = self.output_dir / f"{pru_id}_respondido.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Original instrument
        original_text = self._build_original_text(pru_id, defn)
        orig_path = self.output_dir / f"{pru_id}_original.txt"
        with open(orig_path, "w", encoding="utf-8") as fh:
            fh.write(original_text)

        # Alpha from likert items
        if likert_scores and len(likert_scores) > 1:
            matrix = np.array(likert_scores)
            alpha = self.cronbach_alpha(matrix)
        else:
            alpha = float("nan")

        total_items = sum(len(s["items"]) for s in secciones)
        metadata = {
            "titulo": defn["titulo"],
            "tipo": "prueba_estandarizada",
            "fuente": "sintetico",
            "n_respondentes": n_resp,
            "n_items": total_items,
            "tipo_escala": "mixta",
            "dimensiones": [s["nombre"] for s in secciones],
            "kpis_asociados": defn["kpis_asociados"],
            "parametros_estadisticos": {
                "perfiles_usados": list({p["id"] for p in profiles_assigned}),
                "distribucion_base": "beta_rendimiento_por_perfil",
                "alpha_cronbach_estimado": round(alpha, 4) if not (isinstance(alpha, float) and (alpha != alpha)) else None,
                "modelo_rendimiento": {
                    "P1": "75-95%", "P2": "55-75%", "P3": "35-60%",
                    "P4": "50-70%", "P5": "60-75%", "P6": "45-80%",
                    "P7": "75-95%", "P8": "35-60%",
                },
                "n_secciones": len(secciones),
            },
            "fecha_generacion": date.today().isoformat(),
        }

        meta_path = self.output_dir / f"{pru_id}_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)

        score_mean = df["score_estimado"].mean() if "score_estimado" in df.columns else 0
        print(f"  ✓ {pru_id}: {n_resp} respondentes, score_mean={score_mean:.2f}")

    # ------------------------------------------------------------------
    def _assign_all_profiles(self, n_resp: int) -> list[dict]:
        weights = np.array([p["peso"] for p in self.profiles], dtype=float)
        weights /= weights.sum()
        idxs = self.rng.choice(len(self.profiles), size=n_resp, p=weights)
        return [self.profiles[i] for i in idxs]

    def _build_original_text(self, pru_id: str, defn: dict) -> str:
        lines = [
            f"{'='*70}",
            f"INSTRUMENTO: {defn['titulo']}",
            f"ID: {pru_id}",
            f"Tipo: Prueba estandarizada",
            f"{'='*70}",
            "",
            "INSTRUCCIONES GENERALES:",
            "Lee cuidadosamente cada pregunta antes de responder.",
            "Tiempo estimado: 45-60 minutos.",
            "Responde todas las preguntas en el espacio indicado.",
            "",
        ]

        item_num = 1
        for sec in defn["secciones"]:
            tipo = sec["tipo"]
            lines.append(f"{'─'*60}")
            lines.append(f"SECCIÓN: {sec['nombre'].upper()}")
            lines.append("")

            if tipo == "opcion_multiple":
                lines.append("Instrucciones: Selecciona la opción que consideres correcta (A, B, C o D).")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    for opt in item.get("opciones", []):
                        lines.append(f"   {opt}")
                    lines.append("")
                    item_num += 1

            elif tipo == "verdadero_falso":
                lines.append("Instrucciones: Escribe V (Verdadero) o F (Falso) según corresponda.")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    lines.append("   Respuesta: _____")
                    lines.append("")
                    item_num += 1

            elif tipo == "calculo_numerico":
                lines.append("Instrucciones: Realiza el cálculo y escribe el resultado numérico.")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    lines.append("")
                    item_num += 1

            elif tipo == "respuesta_corta":
                lines.append("Instrucciones: Responde brevemente en 2-4 oraciones.")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    lines.append("   Respuesta: ____________________________________________")
                    lines.append("")
                    item_num += 1

            elif tipo in ("likert_conductual", "likert"):
                lines.append("Instrucciones: Marca del 1 al 5 según la frecuencia (1=Nunca, 5=Siempre).")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    lines.append("   [ ]1  [ ]2  [ ]3  [ ]4  [ ]5")
                    lines.append("")
                    item_num += 1

            elif tipo == "si_no":
                lines.append("Instrucciones: Responde Sí o No.")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    lines.append("   [ ] Sí   [ ] No")
                    lines.append("")
                    item_num += 1

            elif tipo == "escala_preferencia":
                lines.append("Instrucciones: Marca del 1 al 5 (1=No me interesa nada, 5=Me interesa mucho).")
                lines.append("")
                for item in sec["items"]:
                    lines.append(f"{item_num}. {item['pregunta']}")
                    lines.append("   [ ]1  [ ]2  [ ]3  [ ]4  [ ]5")
                    lines.append("")
                    item_num += 1

        lines.append(f"{'='*70}")
        lines.append("FIN DEL INSTRUMENTO")
        lines.append(f"Total de ítems: {item_num - 1}")
        return "\n".join(lines)
