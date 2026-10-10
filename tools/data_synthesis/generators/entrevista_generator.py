"""
entrevista_generator.py
Generates interview instruments (entrevistas): original + respondido (NLP text) + metadata.
"""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

import numpy as np

from .base_generator import BaseGenerator


# ---------------------------------------------------------------------------
# Interview definitions
# ---------------------------------------------------------------------------
INTERVIEW_DEFS: dict[str, dict] = {
    "ent_01": {
        "titulo": "Entrevista sobre estrategias de permanencia universitaria",
        "perfiles_objetivo": ["P2", "P3", "P4", "P8"],
        "n_respondentes": 40,
        "kpis_asociados": [
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Deserción / Abandono Estudiantil",
            "Servicios de Apoyo al Estudiante",
            "Proporción de Consejeros/Orientadores por Estudiante",
        ],
        "preguntas": [
            "¿Qué factores consideras que han sido fundamentales para continuar tus estudios universitarios hasta ahora?",
            "¿Has pensado alguna vez en abandonar la universidad? ¿Qué te llevó a tomar esa decisión en su momento?",
            "¿De qué manera el apoyo familiar ha influido en tu permanencia en la institución?",
            "¿Qué servicios de apoyo institucional (tutorías, becas, orientación) has utilizado y cómo te han ayudado?",
            "¿Cómo has manejado las dificultades económicas durante tu trayectoria universitaria?",
            "¿Qué rol ha jugado la relación con tus profesores en tu decisión de continuar estudiando?",
            "¿Cómo ha impactado el trabajo en tu desempeño y permanencia académica?",
            "¿Qué cambiarías de los servicios de apoyo universitario para mejorar la retención estudiantil?",
            "¿Cómo describirías tu nivel de motivación en diferentes momentos de tu trayectoria?",
            "¿Has tenido que interrumpir tus estudios temporalmente? ¿Qué sucedió?",
            "¿Qué estrategias personales has desarrollado para mantenerte en la universidad?",
            "¿Qué mensaje darías a un estudiante que está pensando en desertar?",
        ],
    },
    "ent_02": {
        "titulo": "Entrevista sobre experiencia docente y calidad educativa",
        "perfiles_objetivo": ["P1", "P2", "P5", "P7"],
        "n_respondentes": 30,
        "kpis_asociados": [
            "Cualificación Docente y Tasa de Rotación del Profesorado",
            "Satisfacción Estudiantil",
            "Tamaño Promedio de Clase (Alumnos por Aula)",
            "Ratio Estudiante-Docente",
        ],
        "preguntas": [
            "¿Cómo describirías la calidad de la enseñanza que has recibido en tu institución?",
            "¿Qué características del profesor ideal consideras más importantes para tu aprendizaje?",
            "¿Has tenido profesores que hayan marcado positivamente tu trayectoria universitaria? ¿Qué los distingue?",
            "¿Qué metodologías de enseñanza encuentras más efectivas y por qué?",
            "¿Cómo afecta el tamaño de los grupos en tu experiencia de aprendizaje?",
            "¿Sientes que los profesores están suficientemente actualizados en sus áreas de conocimiento?",
            "¿Cómo evalúas la accesibilidad y disposición de los docentes fuera del aula?",
            "¿Qué mejoras propondrías al sistema de evaluación docente de tu institución?",
            "¿Has experimentado situaciones de favoritismo o trato desigual por parte de los profesores?",
            "¿Cómo ha impactado la experiencia docente en tu satisfacción con la institución?",
        ],
    },
    "ent_03": {
        "titulo": "Entrevista sobre tecnología y aprendizaje digital",
        "perfiles_objetivo": ["P1", "P2", "P3", "P6"],
        "n_respondentes": 35,
        "kpis_asociados": [
            "Métricas de Compromiso e Interacción del Estudiante en Plataformas Virtuales",
            "Tasa de Finalización de Cursos Online",
            "Uso de Analítica de Aprendizaje",
        ],
        "preguntas": [
            "¿Qué herramientas tecnológicas utilizas con mayor frecuencia para aprender?",
            "¿Cómo describirías tu experiencia con la plataforma virtual (LMS) de tu institución?",
            "¿Cuáles son las principales ventajas y desventajas del aprendizaje en línea según tu experiencia?",
            "¿Has completado cursos en línea exitosamente? ¿Qué factores favorecieron eso?",
            "¿Qué barreras tecnológicas has enfrentado durante tus estudios?",
            "¿Cómo crees que la tecnología ha transformado tu manera de estudiar en los últimos años?",
            "¿Qué herramientas de inteligencia artificial utilizas en tu proceso de aprendizaje?",
            "¿Consideras que tu institución aprovecha bien las posibilidades del aprendizaje digital?",
            "¿Cómo ha cambiado tu motivación al estudiar en formatos virtuales vs. presenciales?",
            "¿Qué recomendarías para mejorar la educación digital en tu institución?",
        ],
    },
    "ent_04": {
        "titulo": "Entrevista sobre inclusión y diversidad universitaria",
        "perfiles_objetivo": ["P3", "P6", "P7", "P8"],
        "n_respondentes": 28,
        "kpis_asociados": [
            "Métricas de Diversidad e Inclusión (Alumnado y Docentes)",
            "Porcentaje de Estudiantes que Reciben Ayuda Financiera",
            "Estadísticas de Seguridad en el Campus (Índice de Criminalidad)",
        ],
        "preguntas": [
            "¿Te has sentido incluido/a y valorado/a en tu institución educativa?",
            "¿Has experimentado o presenciado situaciones de discriminación o exclusión en el campus?",
            "¿Cómo valoras la diversidad cultural y social presente en tu institución?",
            "¿Qué programas de inclusión ofrece tu institución y cuán efectivos son?",
            "¿Cómo ha influido tu origen socioeconómico en tu experiencia universitaria?",
            "¿Qué cambios propondrías para hacer la institución más inclusiva?",
            "¿Has accedido a programas de ayuda financiera? ¿Cómo ha sido ese proceso?",
            "¿Te sientes seguro/a dentro del campus? ¿Por qué?",
        ],
    },
    "ent_05": {
        "titulo": "Entrevista sobre investigación y producción académica (posgrado)",
        "perfiles_objetivo": ["P7"],
        "n_respondentes": 25,
        "kpis_asociados": [
            "Producción Total de Investigación Docente",
            "Tasa de Publicación del Cuerpo Docente",
            "Financiamiento y Becas de Investigación",
            "Patentes Otorgadas",
        ],
        "preguntas": [
            "¿Cuál es tu línea de investigación principal y qué te motivó a elegirla?",
            "¿Cómo describirías el ambiente de investigación en tu institución de posgrado?",
            "¿Qué dificultades has enfrentado para publicar en revistas de alto impacto?",
            "¿Has obtenido financiamiento externo para tus proyectos de investigación? ¿Cómo fue el proceso?",
            "¿Qué estrategias usas para mantenerte actualizado/a en tu campo científico?",
            "¿Cómo colaboras con otros investigadores o instituciones?",
            "¿Has considerado la transferencia tecnológica o patentes como parte de tu actividad investigativa?",
            "¿Qué recursos o infraestructura consideras indispensables para hacer investigación de calidad?",
            "¿Cómo balanceas la actividad docente con la investigación?",
            "¿Qué impacto social espera tener tu investigación en el largo plazo?",
        ],
    },
    "ent_06": {
        "titulo": "Entrevista sobre orientación vocacional y tutoría",
        "perfiles_objetivo": ["P1", "P2", "P3", "P8"],
        "n_respondentes": 32,
        "kpis_asociados": [
            "Proporción de Consejeros/Orientadores por Estudiante",
            "Tasa de Graduación / Titulación",
            "Tasa de Inserción Laboral de Egresados",
            "Tasa de Estudios de Posgrado",
        ],
        "preguntas": [
            "¿Recibiste orientación vocacional antes de ingresar a la universidad? ¿Fue de ayuda?",
            "¿Has utilizado los servicios de tutoría académica? ¿Qué experiencia tuviste?",
            "¿Cómo ha influido un mentor o tutor en tus decisiones académicas o profesionales?",
            "¿Qué dificultades has enfrentado al definir tu trayectoria profesional?",
            "¿Sientes que la carrera que elegiste está alineada con tus intereses y aptitudes?",
            "¿Qué tan preparado/a te sientes para el mercado laboral?",
            "¿Qué apoyo adicional necesitarías de tu institución para prepararte mejor?",
            "¿Tienes planes de continuar con estudios de posgrado? ¿Por qué?",
        ],
    },
    "ent_07": {
        "titulo": "Entrevista sobre actividades extracurriculares y vida de campus",
        "perfiles_objetivo": ["P1", "P2", "P5", "P6"],
        "n_respondentes": 30,
        "kpis_asociados": [
            "Oferta de Actividades Extracurriculares",
            "Satisfacción Estudiantil",
            "Tasa de Retención / Permanencia Estudiantil",
        ],
        "preguntas": [
            "¿Participas o has participado en actividades extracurriculares en tu institución?",
            "¿Cómo han contribuido las actividades extracurriculares a tu desarrollo personal?",
            "¿Qué te motivó a involucrarte en actividades fuera del ámbito académico?",
            "¿Cómo equilibras las actividades extracurriculares con tus responsabilidades académicas?",
            "¿Consideras que la oferta de actividades de tu institución es suficiente y diversa?",
            "¿Qué actividades nuevas te gustaría que ofreciera tu institución?",
            "¿Cómo ha impactado la vida de campus en tu sentido de pertenencia?",
            "¿Has desarrollado amistades o redes profesionales a través de actividades extracurriculares?",
        ],
    },
    "ent_08": {
        "titulo": "Entrevista sobre financiamiento y accesibilidad de la educación",
        "perfiles_objetivo": ["P3", "P4", "P8"],
        "n_respondentes": 28,
        "kpis_asociados": [
            "Tarifa Promedio de Matrícula / Colegiatura",
            "Tamaño del Fondo Patrimonial / Financiero (Endowment)",
            "Porcentaje de Estudiantes que Reciben Ayuda Financiera",
            "Tasa de Incumplimiento de Préstamos Estudiantiles",
        ],
        "preguntas": [
            "¿Cómo has financiado tus estudios universitarios?",
            "¿Has accedido a becas, préstamos o apoyos financieros? ¿Cómo fue el proceso?",
            "¿El costo de la educación ha representado una barrera significativa para ti?",
            "¿Cómo afecta la situación económica tu desempeño y permanencia académica?",
            "¿Qué piensas sobre el sistema de créditos o préstamos educativos disponibles?",
            "¿Qué mejoras propones para hacer la educación más accesible económicamente?",
            "¿Has tenido que trabajar para financiar tus estudios? ¿Cómo ha afectado eso tu vida académica?",
            "¿Consideras que el costo de tu carrera está justificado por los beneficios que recibes?",
        ],
    },
    "ent_09": {
        "titulo": "Entrevista sobre transición secundaria-universidad (primer año)",
        "perfiles_objetivo": ["P2", "P3", "P6", "P8"],
        "n_respondentes": 35,
        "kpis_asociados": [
            "Tasa de Retención / Permanencia Estudiantil",
            "Tasa de Deserción / Abandono Estudiantil",
            "Tasa de Asistencia Escolar y Universitaria",
            "Servicios de Apoyo al Estudiante",
        ],
        "preguntas": [
            "¿Cómo describirías tu transición del bachillerato a la universidad?",
            "¿Qué diferencias encontraste entre la secundaria y la vida universitaria?",
            "¿Cuáles fueron los principales desafíos que enfrentaste en tu primer año?",
            "¿Qué apoyo recibiste de la institución para adaptarte al ambiente universitario?",
            "¿Cómo fue tu proceso de socialización con compañeros y profesores al inicio?",
            "¿Hubo algún momento en que pensaste que no podrías superar las exigencias universitarias?",
            "¿Qué consejos darías a un estudiante que está por iniciar su primer año universitario?",
            "¿De qué manera los programas de inducción o bienvenida te ayudaron?",
        ],
    },
    "ent_10": {
        "titulo": "Entrevista sobre internacionalización y movilidad académica",
        "perfiles_objetivo": ["P6", "P7"],
        "n_respondentes": 25,
        "kpis_asociados": [
            "Ratio de Estudiantes Nacionales vs. Internacionales",
            "Tasa de Participación en Estudios en el Extranjero",
            "Alianzas Corporativas y Oportunidades de Pasantías",
            "Número de Programas Acreditados",
        ],
        "preguntas": [
            "¿Has participado en programas de intercambio estudiantil o movilidad académica?",
            "¿Cómo fue tu experiencia como estudiante en un contexto cultural diferente al tuyo?",
            "¿Qué impacto tuvo la movilidad académica en tu formación personal y profesional?",
            "¿Qué dificultades encontraste al estudiar en un contexto internacional?",
            "¿Qué aspectos del sistema educativo de otros países te parecen superiores o inferiores al local?",
            "¿Cómo apoya tu institución los programas de internacionalización?",
            "¿Qué recomendarías para fomentar la movilidad estudiantil en tu institución?",
            "¿Cómo ha impactado el conocimiento de otro idioma en tus oportunidades académicas?",
        ],
    },
}

# ---------------------------------------------------------------------------
# Response generation templates per profile
# ---------------------------------------------------------------------------
RESPUESTA_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "P1": {
        "permanencia": [
            "Considero que mi organización personal y la disciplina han sido mis principales aliados. Desde el inicio, establecí rutinas de estudio claras y siempre busqué apoyo cuando lo necesité.",
            "La motivación intrínseca es fundamental. Me apasiona lo que estudio y eso me ha mantenido enfocado/a incluso en los momentos difíciles.",
            "He aprovechado todos los recursos que la institución ofrece: tutorías, asesorías, laboratorios. Creo que eso marca la diferencia.",
        ],
        "tecnologia": [
            "Uso múltiples herramientas digitales de forma estratégica. Las plataformas LMS son esenciales para mí, aunque a veces les falta intuitividad.",
            "La IA como ChatGPT me ayuda a clarificar conceptos, pero siempre verifico la información con fuentes primarias. Es un complemento, no un sustituto.",
        ],
        "general": [
            "Mi experiencia ha sido muy positiva en general. He logrado mantener un promedio alto gracias a la combinación de esfuerzo personal y estrategias de estudio efectivas.",
            "Creo firmemente que el éxito académico depende en gran medida de la actitud y la organización del estudiante, aunque la institución tiene un papel importante en facilitarlo.",
        ],
    },
    "P2": {
        "permanencia": [
            "Ha habido momentos difíciles, especialmente en los primeros semestres. Lo que me ha mantenido es el apoyo de mi familia y algunos profesores que han sido muy comprensivos.",
            "El apoyo de mis compañeros también ha sido clave. Estudiar en grupo me ayuda cuando el material es complicado.",
            "Hubo un semestre en que casi abandono, pero el orientador me ayudó a reorganizarme y seguí adelante.",
        ],
        "tecnologia": [
            "Uso la plataforma de la institución principalmente para entregar tareas y ver materiales. A veces es confusa pero me las arreglo.",
            "Los videos de YouTube me han ayudado bastante cuando no entiendo los temas de clase. Es un recurso que uso mucho.",
        ],
        "general": [
            "No soy el mejor estudiante, pero me esfuerzo. Hay materias que se me complican más que otras, pero intento no rendirme.",
            "Creo que la institución podría hacer más para apoyar a estudiantes como yo, que no somos los más brillantes pero sí los más constantes.",
        ],
    },
    "P3": {
        "permanencia": [
            "La verdad ha sido muy difícil. Trabajo por las noches y a veces llego cansado a clases. Ha habido momentos en que he pensado seriamente en dejar la universidad.",
            "No tengo mucho dinero para materiales o transporte y eso complica todo. A veces falto porque no tengo para el camión.",
            "Soy el primero de mi familia en ir a la universidad y hay mucha presión. No tengo a quién pedirle consejos sobre la vida universitaria.",
        ],
        "tecnologia": [
            "No siempre tengo acceso a internet en casa. Cuando hay clases virtuales me complico porque uso los datos del celular y se acaban rápido.",
            "En la institución hay computadoras pero siempre están ocupadas. Quisiera que hubiera más disponibles.",
        ],
        "general": [
            "He tenido que reprimir materias. Es frustrante porque veo a otros avanzar más rápido. Pero no me voy a rendir, mi familia cuenta conmigo.",
            "A veces los profesores no entienden las situaciones de estudiantes como yo. Quisiera que hubiera más comprensión.",
        ],
    },
    "P4": {
        "permanencia": [
            "Balancear trabajo y estudio es un reto constante. Llevo muchos años estudiando a tiempo parcial y hay semestres en que avanzo poco.",
            "Mi jefe a veces me pide quedarse más tarde y eso afecta mis clases nocturnas. Es complicado pero no tengo otra opción.",
            "He aprendido a ser muy eficiente con el tiempo. Estudio en el metro, en los descansos del trabajo. Cada minuto cuenta.",
        ],
        "tecnologia": [
            "Las clases en línea han sido una bendición para mí. Me permiten estudiar sin moverme de casa cuando llego tarde del trabajo.",
            "Aunque a veces la conexión en el trabajo es mala, prefiero las herramientas digitales porque me dan flexibilidad.",
        ],
        "general": [
            "Es difícil, pero tengo claro por qué lo hago. Quiero un mejor futuro para mi familia y eso me da fuerzas para continuar.",
            "Los años que llevo en la universidad me han formado como persona, aunque el camino ha sido largo y difícil.",
        ],
    },
    "P5": {
        "permanencia": [
            "Llevo ocho semestres y estoy bastante agotado/a. Ya no siento la misma emoción que al inicio. Los temas me interesan en abstracto pero ya no tengo energía para estudiarlos bien.",
            "El burnout es real. He tenido periodos en que no dormía bien, no comía bien y solo pensaba en terminar. Es desgastante.",
            "He considerado pausar un semestre, pero sé que si paro puede ser difícil retomar. Entonces sigo aunque me cueste.",
        ],
        "tecnologia": [
            "La tecnología me ayuda a ser más eficiente, aunque a veces el exceso de notificaciones y plataformas también agobia.",
            "Las herramientas digitales son buenas cuando las usas bien, pero también pueden convertirse en una distracción enorme.",
        ],
        "general": [
            "Soy buen estudiante en papel, mis calificaciones lo demuestran, pero por dentro estoy muy cansado/a. Ojalá la institución tuviera más apoyo para este tipo de situación.",
            "Cuando termine me tomaré un descanso largo. Necesito reconectarme con por qué elegí esta carrera.",
        ],
    },
    "P6": {
        "permanencia": [
            "Coming from another country, the academic system here is quite different from what I was used to. The transition was challenging but fascinating.",
            "I had to adapt quickly to the local academic culture, the teaching styles, and even the way students interact with professors.",
            "Language barriers were sometimes an issue, especially in written exams, but I've improved significantly over time.",
        ],
        "tecnologia": [
            "I'm comfortable with digital tools since most education in my home country was already highly digitalized.",
            "The LMS here is okay, but I've seen better ones abroad. Still, it gets the job done.",
        ],
        "general": [
            "The experience has been enriching culturally and academically. I've learned as much from my peers as from the classes.",
            "Sometimes I feel a cultural disconnect in some subjects, but overall the quality of education is good.",
        ],
    },
    "P7": {
        "permanencia": [
            "En el posgrado, la dinámica es completamente diferente a la licenciatura. La motivación es más intrínseca y el enfoque en la investigación da un sentido de propósito muy claro.",
            "La comunidad académica en el posgrado es más pequeña y las relaciones con los asesores son fundamentales para el avance.",
            "He tenido que desarrollar resiliencia frente a los rechazos de publicaciones y las revisiones de mi comité. Es parte del proceso.",
        ],
        "investigacion": [
            "La investigación requiere una mentalidad de largo plazo que no todos los estudiantes tienen al inicio. Hay que aprender a tolerar la ambigüedad y el fracaso.",
            "Publicar en revistas indexadas requiere dominar no solo el contenido sino también las convenciones retóricas del campo científico. Es un aprendizaje que lleva años.",
            "La financiación de la investigación es escasa y competida. Aprender a redactar propuestas es tan importante como hacer la investigación misma.",
        ],
        "general": [
            "El posgrado ha sido la experiencia más retadora e intelectualmente estimulante de mi vida. Recomiendo que cualquier estudiante con vocación investigadora lo considere.",
            "Mi investigación busca generar conocimiento aplicable. No basta con publicar; hay que asegurarse de que el trabajo llegue a quienes pueden aprovecharlo.",
        ],
    },
    "P8": {
        "permanencia": [
            "Ha sido muy difícil. Tengo una beca que cubre parte de los gastos, pero no es suficiente. Necesito trabajar medio tiempo y eso afecta mis estudios.",
            "El estrés económico es constante. Cuando se retrasa el pago de mi beca, hay semanas en que no tengo para comer bien.",
            "He pensado en abandonar varias veces, pero sé que la universidad es mi única oportunidad de cambiar mi situación.",
        ],
        "tecnologia": [
            "No tengo computadora propia. Uso las de la institución cuando puedo, pero los horarios son limitados.",
            "Las clases virtuales son una bendición y una maldición: me ahorro el transporte pero gasto más datos del teléfono.",
        ],
        "general": [
            "La vida universitaria para mí no es la experiencia idealizada que muestran en las películas. Es una lucha constante entre la academia y la sobrevivencia económica.",
            "A pesar de todo, estoy orgulloso/a de lo que he logrado. Soy ejemplo de que con determinación y apoyo se puede.",
        ],
    },
}


class EntrevistaGenerator(BaseGenerator):
    """Generator for interview instruments."""

    def __init__(self, output_dir: Path, seed: int | None = None):
        super().__init__(seed=seed)
        self.output_dir = output_dir / "entrevistas"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, instrument_ids: list[str] | None = None) -> list[str]:
        ids = instrument_ids or list(INTERVIEW_DEFS.keys())
        generated = []
        for ent_id in ids:
            if ent_id in INTERVIEW_DEFS:
                self._generate_one(ent_id)
                generated.append(ent_id)
        return generated

    def _generate_one(self, ent_id: str) -> None:
        defn = INTERVIEW_DEFS[ent_id]
        n_resp = defn["n_respondentes"]
        allowed = defn["perfiles_objetivo"]
        preguntas = defn["preguntas"]

        # Assign respondents to profiles
        profiles_assigned = self._assign_profiles(n_resp, allowed)

        # Generate text responses file
        lines = [
            f"{'='*70}",
            f"INSTRUMENTO: {defn['titulo']}",
            f"ID: {ent_id}",
            f"Tipo: Entrevista semiestructurada",
            f"N° de respondentes: {n_resp}",
            f"KPIs asociados: {', '.join(defn['kpis_asociados'])}",
            f"{'='*70}",
            "",
        ]

        all_word_counts: list[int] = []

        for i, profile in enumerate(profiles_assigned):
            demo = self.generate_demographics(profile, 1)[0]
            demo["id_respondente"] = f"R{i+1:04d}"

            lines.append(f"{'─'*70}")
            lines.append(f"RESPONDENTE: {demo['id_respondente']}")
            lines.append(f"Perfil: {profile['id']} — {profile['nombre']}")
            lines.append(f"Edad: {demo['edad']}  |  Género: {demo['genero']}  |  Semestre: {demo['semestre']}")
            lines.append(f"Universidad: {demo['tipo_universidad']}  |  GPA: {demo['promedio_gpa']}")
            lines.append(f"Horas trabajo/semana: {demo['horas_trabajo_semana']}")
            lines.append("")

            resp_text = self._generate_responses(profile, preguntas, ent_id)

            for j, (pregunta, respuesta) in enumerate(zip(preguntas, resp_text)):
                lines.append(f"P{j+1}: {pregunta}")
                lines.append(f"R: {respuesta}")
                lines.append("")
                all_word_counts.append(len(respuesta.split()))

        lines.append(f"{'='*70}")
        lines.append("FIN DEL INSTRUMENTO")

        respondido_path = self.output_dir / f"{ent_id}_respondido.txt"
        with open(respondido_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        # Original (questions only)
        original_lines = [
            f"{'='*70}",
            f"INSTRUMENTO: {defn['titulo']}",
            f"ID: {ent_id}",
            f"Tipo: Entrevista semiestructurada",
            f"{'='*70}",
            "",
            "OBJETIVO:",
            f"Esta entrevista busca explorar en profundidad las experiencias y percepciones",
            f"de los estudiantes en relación con: {', '.join(defn['kpis_asociados'][:2])}.",
            "",
            "INSTRUCCIONES PARA EL ENTREVISTADOR:",
            "- Leer cada pregunta de forma natural, permitiendo que el respondente se exprese libremente.",
            "- Hacer preguntas de seguimiento cuando sea pertinente.",
            "- Garantizar la confidencialidad de las respuestas.",
            "- Duración estimada: 30-45 minutos.",
            "",
            "PREGUNTAS:",
            "",
        ]
        for j, pregunta in enumerate(preguntas):
            original_lines.append(f"{j+1}. {pregunta}")
            original_lines.append("")

        original_lines.append(f"{'='*70}")
        original_lines.append("FIN DEL INSTRUMENTO")

        original_path = self.output_dir / f"{ent_id}_original.txt"
        with open(original_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(original_lines))

        # Metadata
        avg_words = float(np.mean(all_word_counts)) if all_word_counts else 0.0
        metadata = {
            "titulo": defn["titulo"],
            "tipo": "entrevista",
            "fuente": "sintetico",
            "n_respondentes": n_resp,
            "n_items": len(preguntas),
            "tipo_escala": "texto_cualitativo",
            "dimensiones": ["Semiestructurada"],
            "kpis_asociados": defn["kpis_asociados"],
            "parametros_estadisticos": {
                "perfiles_usados": list({p["id"] for p in profiles_assigned}),
                "distribucion_base": "plantillas_perfil_nlp",
                "alpha_cronbach_estimado": None,
                "palabras_promedio_por_respuesta": round(avg_words, 1),
                "n_preguntas": len(preguntas),
            },
            "fecha_generacion": date.today().isoformat(),
        }

        meta_path = self.output_dir / f"{ent_id}_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)

        print(f"  ✓ {ent_id}: {n_resp} respondentes, {len(preguntas)} preguntas, ~{avg_words:.0f} palabras/respuesta")

    # ------------------------------------------------------------------
    def _generate_responses(self, profile: dict, preguntas: list[str], ent_id: str) -> list[str]:
        """Generate realistic text responses for a profile."""
        pid = profile["id"]
        templates = RESPUESTA_TEMPLATES.get(pid, RESPUESTA_TEMPLATES["P2"])

        # Pick a primary theme for this respondent
        all_templates = []
        for key in templates:
            all_templates.extend(templates[key])

        responses = []
        for i, pregunta in enumerate(preguntas):
            # Select a base template randomly
            if all_templates:
                base = random.choice(all_templates)
            else:
                base = "No tengo mucho que agregar al respecto."

            # Build a varied response
            response = self._expand_response(base, profile, pregunta, i)
            responses.append(response)

        return responses

    def _expand_response(self, base: str, profile: dict, pregunta: str, idx: int) -> str:
        """Expand a base template into a fuller response."""
        expansions = {
            "P1": [
                " Además, creo que la clave está en mantener una disciplina constante y no esperar a última hora.",
                " He comprobado que con una buena planificación casi cualquier reto académico es superable.",
                " En mi experiencia, la comunicación con los profesores hace una gran diferencia.",
            ],
            "P2": [
                " Aunque no siempre es fácil, trato de mantenerme enfocado/a en mis metas.",
                " He aprendido que pedir ayuda no es una debilidad, sino una estrategia inteligente.",
                " Los compañeros de clase son un apoyo fundamental que muchas veces se subestima.",
            ],
            "P3": [
                " Es una lucha constante, pero no me queda de otra más que seguir adelante.",
                " Quisiera que la institución entendiera mejor las condiciones en que estudiamos algunos.",
                " A veces el sistema no está diseñado pensando en estudiantes como yo.",
            ],
            "P4": [
                " El tiempo es mi recurso más escaso y aprender a administrarlo ha sido fundamental.",
                " Trabajo y estudio simultáneamente desde hace años; ya es parte de mi rutina.",
                " Los fines de semana son mi único espacio para estudiar tranquilamente.",
            ],
            "P5": [
                " Llevo años en esto y el desgaste acumulado es real, aunque mis notas no lo reflejen.",
                " Necesito un descanso, pero el miedo a rezagarme me impide tomarlo.",
                " La motivación ya no es la misma que al inicio, pero el compromiso con la meta me sostiene.",
            ],
            "P6": [
                " The cultural differences make this both challenging and enriching at the same time.",
                " Adapting to a new academic system requires flexibility and open-mindedness.",
                " I've grown more as a person during this exchange than I would have staying home.",
            ],
            "P7": [
                " En el posgrado, cada decisión académica tiene implicaciones de largo alcance en la carrera investigativa.",
                " La excelencia en investigación requiere rigor, creatividad y una tolerancia alta a la incertidumbre.",
                " He aprendido que las mejores investigaciones surgen de preguntas genuinamente relevantes.",
            ],
            "P8": [
                " A pesar de las dificultades económicas, me aferro a la convicción de que la educación cambia vidas.",
                " No es justo que el acceso a una buena educación dependa tanto del dinero que tienes.",
                " Mi familia ha sacrificado mucho para que yo pueda estar aquí; eso me da fuerzas.",
            ],
        }

        pid = profile["id"]
        ext_list = expansions.get(pid, expansions["P2"])
        extension = random.choice(ext_list)

        # Occasionally add a second sentence for variety
        if self.rng.random() > 0.5 and len(base) < 200:
            extension2 = random.choice(ext_list)
            if extension2 != extension:
                extension += " " + extension2

        return base + extension

    # ------------------------------------------------------------------
    def _assign_profiles(self, n_resp: int, allowed: list[str]) -> list[dict]:
        profiles = [p for p in self.profiles if p["id"] in allowed]
        weights = np.array([p["peso"] for p in profiles], dtype=float)
        weights /= weights.sum()
        idxs = self.rng.choice(len(profiles), size=n_resp, p=weights)
        return [profiles[i] for i in idxs]
