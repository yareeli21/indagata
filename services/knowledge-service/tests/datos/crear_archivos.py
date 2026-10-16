"""Archivos de ejemplo (deterministas) para las pruebas del knowledge-service.

Uso:  python crear_archivos.py   (escribe los CSV/TXT en esta carpeta)
"""
import csv
import random
from pathlib import Path

D = Path(__file__).parent
random.seed(12)
ESCALA = ["Totalmente en desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo", "De acuerdo", "Totalmente de acuerdo"]
ASPECTOS = ["Profesores", "Materiales", "Instalaciones"]
NOMBRES = ["Ana Pérez", "Luis Gómez", "María López", "Jorge Ruiz", "Sofía Díaz", "Pedro Mora", "Lucía Vega", "Diego Cruz",
           "Elena Ríos", "Raúl Soto", "Carmen Gil", "Iván León", "Rosa Peña", "Tomás Luna", "Inés Rey", "Hugo Sanz",
           "Alma Ortiz", "Saúl Vera", "Nora Paz", "Omar Lara"]

enc = ["Marca temporal", "Nombre", "Correo", "Matrícula", "Turno", "Semestre", "Idioma"] + \
      [f"Valora tu experiencia en la carrera [{a}]" for a in ASPECTOS] + [
      "Me siento motivado para continuar mis estudios este semestre",
      "¿Trabajas actualmente?", "¿Qué servicios de la universidad utilizas?", "¿Cuál es tu principal medio de transporte?",
      "¿Qué mejorarías de tu carrera?"]
filas = []
for i, nombre in enumerate(NOMBRES):
    turno = "Matutino" if i % 2 == 0 else "Vespertino"
    actitud = random.randint(1, 5)
    lik = [ESCALA[max(0, min(4, actitud - 1 + random.choice((-1, 0, 0, 1))))] for _ in range(4)]
    if i == 0:
        lik = ["En desacuerdo", "Totalmente en desacuerdo", "En desacuerdo", "Totalmente en desacuerdo"]  # criterio 2
    if all(x == ESCALA[2] for x in lik):
        lik[0] = ESCALA[3]  # nadie neutral en las 4 escalas (caso negativo del criterio 2)
    filas.append([f"2026-09-{1 + i:02d} 10:00", nombre, f"{nombre.split()[0].lower()}@uni.mx", f"A0{3100 + i}", turno, str(1 + i % 8),
                  random.choice(["Español", "Inglés"]), *lik,
                  random.choice(["Sí", "No"]), random.choice(["Biblioteca, Cafetería", "Biblioteca", "Gimnasio, Biblioteca", "Cafetería"]),
                  random.choice(["Camión", "Metro", "Bicicleta", "Auto"]), random.choice(["", "Más prácticas", "Mejores horarios", "Más actividades culturales y deportivas"])])
filas[4][10] = ""  # una respuesta faltante
filas[7][10] = "No sé"  # «No sé»: se conserva marcada
with open(D / "encuesta.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows([enc, *filas])

(D / "encuesta_original.txt").write_text("""# Encuesta de experiencia estudiantil

SECCIÓN 1: DATOS GENERALES
1. Turno en el que estudias
2. Semestre que cursas

SECCIÓN 2: EXPERIENCIA EN LA CARRERA
3. Valora tu experiencia en la carrera en los siguientes aspectos
   1 = Totalmente en desacuerdo, 5 = Totalmente de acuerdo
4. Me siento motivado para continuar mis estudios este semestre
5. ¿Trabajas actualmente?
   a) Sí
   b) No
6. ¿Qué servicios de la universidad utilizas? (puedes elegir varios)
   a) Biblioteca
   b) Cafetería
   c) Gimnasio
7. ¿Cuál es tu principal medio de transporte para llegar a la universidad?
   a) Camión
   b) Metro
   c) Bicicleta
   d) Auto
8. ¿Qué mejorarías de tu carrera?
9. ¿Recomendarías la universidad a un amigo?
""", encoding="utf-8")

(D / "entrevista.txt").write_text("""Entrevistador: Buenos días, gracias por participar. ¿Cómo ha sido tu experiencia con la evaluación en tus materias?
Ana: La evaluación me parece justa, aunque a veces los exámenes no reflejan lo que aprendimos en clase.
Ana: Preferiría más proyectos.
Entrevistador: ¿Y qué opinas de la retroalimentación que recibes de tus profesores?
Beto: Casi nunca recibo retroalimentación a tiempo, eso me frustra mucho.
Entrevistador: ¿Qué cambiarías del plan de estudios?
Ana: Agregaría más prácticas profesionales desde los primeros semestres.
Beto: Yo cambiaría la evaluación final por una evaluación continua.
""", encoding="utf-8")
(D / "entrevista_guion.txt").write_text("""Guion de entrevista semiestructurada

BLOQUE 1: EVALUACIÓN
1. ¿Cómo ha sido tu experiencia con la evaluación en tus materias?
2. ¿Qué opinas de la retroalimentación que recibes de tus profesores?

BLOQUE 2: PLAN DE ESTUDIOS
3. ¿Qué cambiarías del plan de estudios?
""", encoding="utf-8")

clave = {"P1": "A", "P2": "C", "P3": "B", "P4": "D", "P5": "A"}
with open(D / "prueba_clave.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["pregunta", "respuesta"]); w.writerows(clave.items())
with open(D / "prueba_respuestas.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["matricula", "turno", *clave])
    for a in range(12):
        fila = [f"2026{a:04d}", "Matutino" if a % 2 == 0 else "Vespertino"]
        for k, (p, c) in enumerate(clave.items()):
            acierto = random.random() < (0.85 - 0.15 * k)
            fila.append(c if acierto else random.choice([o for o in "ABCD" if o != c]))
        w.writerow(fila)
    w.writerow(["20260012", "Vespertino", "AB", "", "*", "D", "A"])
(D / "prueba_original.txt").write_text("""Examen diagnóstico de matemáticas

PARTE I: ARITMÉTICA
1. ¿Cuánto es 7 × 8?
A) 56
B) 54
C) 64
D) 48
2. ¿Cuál es el resultado de 144 ÷ 12?
A) 14
B) 10
C) 12
D) 11
PARTE II: ÁLGEBRA
3. Si 2x + 3 = 11, ¿cuánto vale x?
A) 3
B) 4
C) 5
D) 6
4. ¿Cuál es la pendiente de la recta y = 3x − 2?
A) −2
B) 2
C) −3
D) 3
5. Factoriza x² − 9
A) (x − 3)(x + 3)
B) (x − 9)(x + 1)
C) (x − 3)²
D) (x + 9)(x − 1)
""", encoding="utf-8")
print("ok")
