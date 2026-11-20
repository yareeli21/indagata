"""La misma encuesta (40 respondentes, mismas respuestas) guardada como la guarda cada plataforma (Anexo G, Tabla 182).

Uso: python tools/formatos/generar_plataformas.py   → tools/formatos/corpus/plataformas/

Preguntas: P1 escala de acuerdo 1–5 (una sola), P2 cuadrícula de 3 afirmaciones con la escala de acuerdo y «No sé»,
P3 opción única con «Otro», P4 selección múltiple. Sin respuesta: algunas celdas vacías.
"""
import csv, io, random
from pathlib import Path

import openpyxl

OUT = Path(__file__).resolve().parent / "corpus" / "plataformas"
OUT.mkdir(parents=True, exist_ok=True)
random.seed(182)
N = 40
ESC = ["Totalmente en desacuerdo", "En desacuerdo", "Ni de acuerdo ni en desacuerdo", "De acuerdo", "Totalmente de acuerdo"]
P1 = "La institución responde a mis intereses académicos"
P2 = "Indica qué tan de acuerdo estás con las siguientes afirmaciones"
AFIRM = ["Los laboratorios son adecuados", "La biblioteca tiene lo que necesito", "Las aulas son cómodas"]
P3 = "¿En qué modalidad cursas tu programa?"
MOD = ["Presencial", "En línea", "Mixta"]
P4 = "¿Qué servicios usas?"
SERV = ["Biblioteca", "Cafetería", "Laboratorios", "Tutorías"]

filas = []
for i in range(N):
    base = random.choice([2, 3, 4, 4, 5])
    p1 = None if i in (7, 21) else max(1, min(5, base + random.choice([-1, 0, 0, 1])))
    p2 = [max(1, min(5, base + random.choice([-1, 0, 1]))) for _ in AFIRM]
    if i in (3, 15, 30):
        p2[1] = "nose"
    p3 = "otro" if i in (5, 26) else random.choice([0, 0, 0, 1, 2])
    p4 = sorted(random.sample(range(4), random.choice([1, 1, 2, 3])))
    filas.append((p1, p2, p3, p4))
OTRO = {5: "Dual (empresa y escuela)", 26: "Abierta sabatina"}


def guardar_csv(nombre, cab, cuerpo, sep=","):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=sep, lineterminator="\r\n")
    w.writerow(cab)
    w.writerows(cuerpo)
    (OUT / nombre).write_bytes(buf.getvalue().encode("utf-8-sig"))


def txt(v, nose="No sé"):
    return "" if v is None else (nose if v == "nose" else ESC[v - 1])


# ── Google Forms: escala lineal = número; cuadrícula = texto; casillas = «a, b» ──
cab = ["Marca temporal", "Dirección de correo electrónico", P1, *[f"{P2} [{a}]" for a in AFIRM], P3, P4]
cuerpo = []
for i, (p1, p2, p3, p4) in enumerate(filas):
    cuerpo.append([f"2026/10/25 {8 + i // 30}:{i % 60:02d}:13 a.m. GMT-6", f"alumno{i + 1}@escuela.mx",
                   "" if p1 is None else str(p1), *[txt(v) for v in p2],
                   OTRO[i] if p3 == "otro" else MOD[p3], ", ".join(SERV[k] for k in p4)])
guardar_csv("google_forms.csv", cab, cuerpo)

# ── Microsoft Forms (xlsx): calificación = número; Likert = texto por afirmación; varias = «a;b;» ──
libro = openpyxl.Workbook()
h = libro.active
h.title = "Sheet1"
h.append(["Id", "Hora de inicio", "Hora de finalización", "Correo electrónico", "Nombre", P1, *AFIRM, P3, P4])
for i, (p1, p2, p3, p4) in enumerate(filas):
    h.append([i + 1, f"10/25/26 8:{i % 60:02d}:00", f"10/25/26 8:{i % 60:02d}:40", "anonymous", None,
              p1, *[txt(v) or None for v in p2], OTRO[i] if p3 == "otro" else MOD[p3],
              "".join(SERV[k] + ";" for k in p4)])
libro.save(OUT / "microsoft_forms.xlsx")

# ── LimeSurvey: dos exportaciones del mismo levantamiento ──
sis = ["id", "submitdate", "lastpage", "startlanguage", "seed", "startdate", "datestamp"]
def sis_fila(i):
    return [str(i + 1), "2026-10-25 08:10:00", "3", "es", str(4711 + i), "2026-10-25 08:05:00", "2026-10-25 08:10:00"]

# códigos: 5 puntos = 1..5; matriz con opciones propias = A1..A5 (No sé = A6); lista = A1..; varias = Y
cab = [*sis, "G01Q01", *[f"G01Q02[SQ00{k + 1}]" for k in range(3)], "G01Q03", "G01Q03[other]",
       *[f"G01Q04[SQ00{k + 1}]" for k in range(4)]]
cuerpo = []
for i, (p1, p2, p3, p4) in enumerate(filas):
    cuerpo.append([*sis_fila(i), "" if p1 is None else str(p1), *["A6" if v == "nose" else f"A{v}" for v in p2],
                   "-oth-" if p3 == "otro" else f"A{p3 + 1}", OTRO.get(i, ""), *["Y" if k in p4 else "" for k in range(4)]])
guardar_csv("limesurvey_codigos.csv", cab, cuerpo)

# respuestas completas: encabezado = texto, valores = texto
cab = [*sis, P1, *[f"{P2} [{a}]" for a in AFIRM], P3, f"{P3} [Otro]", *[f"{P4} [{s}]" for s in SERV]]
cuerpo = []
for i, (p1, p2, p3, p4) in enumerate(filas):
    cuerpo.append([*sis_fila(i), "" if p1 is None else str(p1), *[txt(v) for v in p2],
                   "Otro" if p3 == "otro" else MOD[p3], OTRO.get(i, ""), *["Sí" if k in p4 else "" for k in range(4)]])
guardar_csv("limesurvey_completas.csv", cab, cuerpo)

# ── Microdatos con diccionario: códigos numéricos, 9 = No sabe, una variable 1/0 por servicio ──
cab = ["folio", "P1", *[f"P2_{k + 1}" for k in range(3)], "P3", *[f"P4_{k + 1}" for k in range(4)]]
cuerpo = []
for i, (p1, p2, p3, p4) in enumerate(filas):
    cuerpo.append([str(1000 + i), "" if p1 is None else str(p1), *["9" if v == "nose" else str(v) for v in p2],
                   "4" if p3 == "otro" else str(p3 + 1), *["1" if k in p4 else "0" for k in range(4)]])
guardar_csv("microdatos.csv", cab, cuerpo)
dic = [["variable", "pregunta", "valor", "etiqueta"]]
for v, preg in [("P1", P1), *[(f"P2_{k + 1}", AFIRM[k]) for k in range(3)]]:
    for n, e in enumerate(ESC, 1):
        dic.append([v, preg if n == 1 else "", str(n), e])
    if v.startswith("P2"):
        dic.append([v, "", "9", "No sé"])
for n, e in enumerate([*MOD, "Otra"], 1):
    dic.append(["P3", P3 if n == 1 else "", str(n), e])
for k, s in enumerate(SERV):
    dic += [[f"P4_{k + 1}", f"{P4} {s}", "1", "Sí"], [f"P4_{k + 1}", "", "0", "No"]]
guardar_csv("microdatos_diccionario.csv", dic[0], dic[1:])

# instrumento original (para los encabezados en código de LimeSurvey)
(OUT / "original.txt").write_text(
    "INSTRUMENTO: Prueba de formatos por plataforma\n\nEscala: 1 = Totalmente en desacuerdo … 5 = Totalmente de acuerdo\n\n"
    f"--- INSTITUCIÓN ---\n\n1. {P1}\n\n2. {P2}\n" + "".join(f"   [{a}]\n" for a in AFIRM) +
    f"\n--- SERVICIOS ---\n\n3. {P3}\n   {' / '.join(MOD)} / Otro\n\n4. {P4}\n   {' / '.join(SERV)}\n", encoding="utf-8")
print(sorted(p.name for p in OUT.iterdir()))
