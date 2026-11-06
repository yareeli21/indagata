"""Genera la versión de enc_06 con errores que la limpieza de encuestas NO tiene contemplados, y su verdad.

Uso: python tools/limpieza/ensuciar_enc_06_no_contemplado.py storage/instrumentos_sinteticos/encuestas
Es determinista (semilla fija). Se eligió enc_06 (Satisfacción con Servicios Institucionales) porque no se usó
para ajustar la limpieza: con enc_11 se midieron los errores contemplados (evidencias/limpieza_2026-10-24) y con
la 127 se hicieron correcciones el 28 oct.

Lo contemplado queda fuera a propósito: mayúsculas y acentos («SI», «semanalmente»), espacios, «NA» / «-» como
vacío, duplicados exactos (aunque cambie el ID), valores fuera de escala, «No sé» y columnas de plataforma.

Cada error se identifica por respondente y columna. `esperado` es lo que haría una persona que revisa a mano.
"""
import csv
import io
import json
import random
import sys
from pathlib import Path

SEMILLA = 13
carpeta = Path(sys.argv[1])
with open(carpeta / "enc_06_respondido.csv", encoding="utf-8", newline="") as f:
    lector = csv.reader(f)
    encabezado = next(lector)
    filas = [fila for fila in lector if fila]

rng = random.Random(SEMILLA)
ID = encabezado.index("id_respondente")
col = {h: i for i, h in enumerate(encabezado)}


def buscar(prefijo: str) -> int:
    return next(i for h, i in col.items() if h.startswith(prefijo))


LIKERT = [i for h, i in col.items() if "_item" in h]
ESCALA_10 = [i for h, i in col.items() if "escala_del_0_al_10" in h]
FRECUENCIA = buscar("Con_qué_frecuencia")
SERVICIO = buscar("Cuál_servicio")
SI_NO = [buscar("Has_utilizado"), buscar("Has_recibido"), buscar("Conoces_los_programas")]
verdad: list[dict] = []
filas_usadas: set[int] = set()


def fila_libre(condicion=lambda i: True) -> int:
    while True:
        i = rng.randrange(len(filas))
        if i not in filas_usadas and condicion(i):
            filas_usadas.add(i)
            return i


def inyectar(tipo: str, columnas: list[int], valores, esperado, nota: str = "", si=lambda o: True) -> None:
    """`valores` y `esperado` pueden ser funciones del valor original; `si` filtra las celdas elegibles."""
    for k, v in enumerate(valores):
        j = columnas[k % len(columnas)]
        i = fila_libre(lambda i: si(filas[i][j]))
        original = filas[i][j]
        nuevo = v(original) if callable(v) else v
        filas[i][j] = nuevo
        verdad.append({"tipo": tipo, "id": filas[i][ID], "columna": encabezado[j], "original": original, "inyectado": nuevo,
                       "esperado": esperado(original) if callable(esperado) else esperado, **({"nota": nota} if nota else {})})


_ETIQUETA = {"1": "Totalmente en desacuerdo", "2": "En desacuerdo", "3": "Neutral", "4": "De acuerdo", "5": "Totalmente de acuerdo"}
_PALABRA = {"1": "uno", "2": "dos", "3": "tres", "4": "cuatro", "5": "cinco"}
inyectar("numero_con_etiqueta", LIKERT, [lambda o: f"{o} - {_ETIQUETA[o]}", lambda o: f"{o} ({_ETIQUETA[o]})", lambda o: f"{o} - {_ETIQUETA[o]}"],
         lambda o: o, "exportación que pega la etiqueta al número de la escala")
inyectar("numero_en_palabra", LIKERT, [lambda o: _PALABRA[o]] * 3, lambda o: o)
inyectar("apostrofo_de_excel", LIKERT, [lambda o: f"'{o}"] * 2, lambda o: o, "Excel marca así un número guardado como texto")
inyectar("coma_decimal", ESCALA_10 + [col["promedio_gpa"]], [lambda o: f"{o},5" if "." not in o else o.replace(".", ",")] * 4,
         lambda o: f"{o}.5" if "." not in o else o, si=lambda o: o != "10")
inyectar("unidad_en_el_numero", [col["edad"], col["horas_trabajo_semana"]], [lambda o: f"{o} años", lambda o: f"{o} hrs", lambda o: f"{o} años"],
         lambda o: o)
_TYPO = {"Semanalmente": "Semanalemnte", "Una vez al mes": "Una vez al mse", "Una vez al semestre": "Una vez al semetre",
         "Nunca": "Nuca"}
inyectar("error_ortografico_en_categoria", [FRECUENCIA], [lambda o: _TYPO[o]] * 3, lambda o: o)
_SINONIMO = {"Semanalmente": "Cada semana", "Una vez al mes": "Mensualmente", "Una vez al semestre": "1 vez por semestre",
             "Nunca": "Jamás"}
inyectar("sinonimo_de_categoria", [FRECUENCIA], [lambda o: _SINONIMO[o]] * 3, lambda o: o)
inyectar("otro_con_texto", [SERVICIO], ["Otro: cafetería", "Otro (enfermería)", "Otro - transporte"], "Otro (con el texto aparte)")
inyectar("si_no_codificado", SI_NO, [lambda o: "1" if o == "Sí" else "0", lambda o: "Yes" if o == "Sí" else "No", lambda o: "1" if o == "Sí" else "0"],
         lambda o: o)
inyectar("mojibake", SI_NO, [lambda o: o.encode("utf-8").decode("latin-1")] * 2, lambda o: o, "UTF-8 leído como latin-1 en una sola celda",
         si=lambda o: o == "Sí")

estructura: dict = {}
# Casi duplicados: la misma persona dos veces con otro ID y UNA respuesta distinta (no es un duplicado exacto).
casi = []
for nuevo_id in ("R0161", "R0162"):
    fuente = fila_libre()
    copia = list(filas[fuente])
    copia[ID] = nuevo_id
    j = LIKERT[rng.randrange(len(LIKERT))]
    copia[j] = "1" if copia[j] != "1" else "2"
    filas.append(copia)
    casi.append({"original": filas[fuente][ID], "copia": nuevo_id, "columna_distinta": encabezado[j]})
estructura["casi_duplicado"] = casi
# Fila desplazada: falta la celda de «genero».
i = fila_libre()
estructura["fila_desplazada"] = {"id": filas[i][ID], "nota": "falta «genero»: todo lo demás se corre una columna a la izquierda"}
g = col["genero"]
filas[i] = filas[i][:g] + filas[i][g + 1:] + [""]
# Fila de promedios al final (exportación de Excel con totales).
promedios = ["Promedio"] + [""] * (len(encabezado) - 1)
for j in LIKERT + ESCALA_10:
    numeros = [float(f[j]) for f in filas if f[j].replace(".", "", 1).isdigit()]
    promedios[j] = f"{sum(numeros) / len(numeros):.2f}"
filas.append(promedios)
estructura["fila_de_promedios"] = "última fila «Promedio» con la media de cada ítem: debe descartarse, no contarse como respondente"
# Segunda fila de encabezado con el texto de las preguntas (como la exportan Qualtrics o SurveyMonkey).
texto = ["ID del respondente", "Perfil", "Edad", "Género", "Semestre", "Promedio", "Horas de trabajo a la semana"]
segunda = [texto[j] if j < len(texto) else f"Pregunta {j - 6}" for j in range(len(encabezado))]
filas.insert(0, segunda)
# Fila de datos (1 = primera fila después del encabezado, igual que los hallazgos de la limpieza) ya con todo insertado.
fila_de = {f[ID]: n for n, f in enumerate(filas, start=1)}
for v in verdad:
    v["fila"] = fila_de[v["id"]]
estructura["segunda_fila_de_encabezado"] = "la fila 2 trae el texto de las preguntas: debe tomarse como etiqueta, no como respondente"

buf = io.StringIO()
escritor = csv.writer(buf, lineterminator="\n")
escritor.writerow(encabezado)
escritor.writerows(filas)
(carpeta / "enc_06_sucio_no_contemplado.csv").write_text(buf.getvalue(), encoding="utf-8")
resumen: dict[str, int] = {}
for v in verdad:
    resumen[v["tipo"]] = resumen.get(v["tipo"], 0) + 1
resumen.update({k: len(v) if isinstance(v, list) else 1 for k, v in estructura.items()})
(carpeta / "enc_06_ruido_no_contemplado.json").write_text(json.dumps(
    {"base": "enc_06_respondido.csv", "archivo": "enc_06_sucio_no_contemplado.csv",
     "generador": "tools/limpieza/ensuciar_enc_06_no_contemplado.py", "semilla": SEMILLA, "resumen": resumen,
     "estructura": estructura, "detalle": verdad}, ensure_ascii=False, indent=2), encoding="utf-8")
print(resumen)
