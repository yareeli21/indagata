"""Genera dos versiones sucias de pru_03 (Alfabetización Digital) y la verdad de cada error inyectado.

Uso: python tools/limpieza/ensuciar_pru_03.py storage/instrumentos_sinteticos/pruebas
Es determinista (semilla fija). Se eligió pru_03 y no pru_01 porque pru_01 ya se usó para ajustar la limpieza
(evidencias/limpieza_2026-10-24).

  - `pru_03_sucio_contemplado.csv`: errores que la limpieza de pruebas sí tiene contemplados
    (cleaning-service, services/motores/pruebas/motor.py y tipos.py; limpieza.yaml → pruebas).
  - `pru_03_sucio_no_contemplado.csv`: errores frecuentes en hojas de respuestas reales que no tienen regla.

Cada error se identifica por alumno y reactivo (no por número de fila, que cambia al insertar filas). En la
verdad, `esperado` es lo que la limpieza debería producir; en la versión no contemplada es lo que haría una
persona que revisa a mano, para medir la distancia.
"""
import csv
import io
import json
import random
import sys
from pathlib import Path

SEMILLA = 11
carpeta = Path(sys.argv[1])
with open(carpeta / "pru_03_respondido.csv", encoding="utf-8", newline="") as f:
    lector = csv.reader(f)
    encabezado = next(lector)
    base = [fila for fila in lector if fila]

ID = encabezado.index("id_respondente")
OM = [i for i, h in enumerate(encabezado) if "Competenci" in h or "Ordenamien" in h]
VF = [i for i, h in enumerate(encabezado) if "Verdadero" in h]


def nueva_version():
    return [list(f) for f in base], random.Random(SEMILLA), set()


def tomar(filas, rng, usadas, columnas, n):
    """n celdas (fila, columna) distintas y no usadas antes, en filas también distintas."""
    salida, filas_usadas = [], {fu for fu, _ in usadas}
    while len(salida) < n:
        i, j = rng.randrange(len(filas)), rng.choice(columnas)
        if i in filas_usadas:
            continue
        filas_usadas.add(i)
        usadas.add((i, j))
        salida.append((i, j))
    return salida


def inyectar(filas, rng, usadas, verdad, tipo, columnas, valores, esperado, nota=""):
    for k, (i, j) in enumerate(tomar(filas, rng, usadas, columnas, len(valores))):
        original = filas[i][j]
        filas[i][j] = valores[k]
        verdad.append({"tipo": tipo, "id_alumno": filas[i][ID], "pregunta": encabezado[j], "original": original,
                       "inyectado": valores[k], "esperado": esperado, **({"nota": nota} if nota else {})})


def guardar(filas, nombre, verdad, extra):
    buf = io.StringIO()
    escritor = csv.writer(buf, lineterminator="\n")
    escritor.writerow(encabezado)
    escritor.writerows(filas)
    (carpeta / f"{nombre}.csv").write_text(buf.getvalue(), encoding="utf-8")
    resumen: dict[str, int] = {}
    for v in verdad:
        resumen[v["tipo"]] = resumen.get(v["tipo"], 0) + 1
    resumen.update({k: len(v) if isinstance(v, list) else v for k, v in extra.items()})
    return resumen


# ── 1. Lo que la limpieza sí contempla ─────────────────────────────────────────
filas, rng, usadas = nueva_version()
verdad: list[dict] = []
inyectar(filas, rng, usadas, verdad, "respuesta_multiple", OM, ["A,B", "BC", "A/D", "C;D", "AB", "B C"], "nula/respuesta_multiple")
inyectar(filas, rng, usadas, verdad, "ilegible", OM + VF, ["?", "#", "*", "B?", "#C"], "nula/ilegible")
inyectar(filas, rng, usadas, verdad, "caracter_invalido", OM, ["Z", "E", "X", "G"], "nula/caracter_invalido")
inyectar(filas, rng, usadas, verdad, "minusculas_o_espacios", OM, ["b", " C ", "d ", " a"], "valida", "se normaliza a la letra en mayúscula")
inyectar(filas, rng, usadas, verdad, "vf_escrito_completo", VF, ["Verdadero", "falso", "f", "VERDADERO"], "valida", "se normaliza a V/F")
inyectar(filas, rng, usadas, verdad, "no_respondida", OM + VF, ["", "NR", "nr", ""], "NR/no_respondida")
# IDs repetidos: tres alumnos toman el ID de otro.
ids_dup = []
for i, fuente in zip(*(tomar(filas, rng, usadas, [ID], 3), tomar(filas, rng, usadas, [ID], 3))):
    filas[i[0]][ID] = filas[fuente[0]][ID]
    ids_dup.append(filas[fuente[0]][ID])
# Filas vacías (con y sin separadores).
for pos in (20, 61):
    filas.insert(pos, [""] * len(encabezado))
extra = {"id_duplicado": sorted(ids_dup), "filas_vacias": 2}
resumen = guardar(filas, "pru_03_sucio_contemplado", verdad, extra)
(carpeta / "pru_03_ruido_contemplado.json").write_text(json.dumps(
    {"base": "pru_03_respondido.csv", "archivo": "pru_03_sucio_contemplado.csv", "generador": "tools/limpieza/ensuciar_pru_03.py",
     "semilla": SEMILLA, "resumen": resumen, "id_duplicado": sorted(ids_dup), "filas_vacias": 2, "detalle": verdad},
    ensure_ascii=False, indent=2), encoding="utf-8")
print("contemplado:", resumen)

# ── 2. Lo que la limpieza NO contempla ─────────────────────────────────────────
filas, rng, usadas = nueva_version()
verdad = []
# pru_03_Competenci_q10 se vacía completa más abajo: no se inyecta nada en ella.
col_vacia = encabezado.index("pru_03_Competenci_q10")
OM_NC = [j for j in OM if j != col_vacia]
inyectar(filas, rng, usadas, verdad, "numero_en_lugar_de_letra", OM_NC, ["1", "2", "3", "4"], "valida (1→A, 2→B, 3→C, 4→D)",
         "lectoras ópticas y algunos formularios exportan la opción como número")
inyectar(filas, rng, usadas, verdad, "letra_con_signo", OM_NC, ["B)", "(C)", "c.", "D-"], "valida (la letra sin el signo)")
inyectar(filas, rng, usadas, verdad, "no_respuesta_escrita_distinto", OM_NC + VF, ["N/R", "Sin respuesta", "-", "N/A", "0"],
         "NR/no_respondida", "otras formas de decir «no respondió»")
inyectar(filas, rng, usadas, verdad, "letra_parecida_otro_alfabeto", OM_NC, ["А", "Ｃ"], "valida (A y C)",
         "«А» cirílica y «Ｃ» de ancho completo: se ven iguales a A y C")
inyectar(filas, rng, usadas, verdad, "misma_letra_dos_veces", OM_NC, ["AA", "CC"], "valida (una sola opción marcada dos veces)")
# Columna de reactivo vacía: el reactivo no se aplicó a nadie.
for f in filas:
    f[col_vacia] = ""
extra_nc = {"columna_reactivo_vacia": "pru_03_Competenci_q10: el reactivo debe seguir apareciendo, con 100 % sin respuesta"}
# Fila desplazada: falta la celda de «genero» y todo lo demás se corre una columna a la izquierda.
i_desp = tomar(filas, rng, usadas, [ID], 1)[0][0]
desplazada = filas[i_desp][ID]
g = encabezado.index("genero")
filas[i_desp] = filas[i_desp][:g] + filas[i_desp][g + 1:] + [""]
extra_nc["fila_desplazada"] = f"{desplazada}: falta «genero»; sus 22 respuestas quedan en el reactivo equivocado"
# Mismo alumno con el ID escrito distinto (minúscula / sin un cero) y mismo alumno con otro ID.
copias = []
fuentes = [f for f, _ in tomar(filas, rng, usadas, [ID], 3)]
for fuente, transformar in zip(fuentes, (str.lower, lambda s: s[0] + s[2:], lambda s: "R9999")):
    copia = list(filas[fuente])
    copia[ID] = transformar(copia[ID])
    filas.append(copia)
    copias.append({"original": filas[fuente][ID], "copia": copia[ID]})
extra_nc["alumno_repetido_con_id_distinto"] = copias
# Encabezado repetido a mitad del archivo (dos exportaciones pegadas).
filas.insert(48, list(encabezado))
extra_nc["encabezado_repetido"] = "una fila igual al encabezado en medio de los datos: debe descartarse, no contarse como alumno"
resumen = guardar(filas, "pru_03_sucio_no_contemplado", verdad, {})
resumen.update({k: 1 if isinstance(v, str) else len(v) for k, v in extra_nc.items()})
(carpeta / "pru_03_ruido_no_contemplado.json").write_text(json.dumps(
    {"base": "pru_03_respondido.csv", "archivo": "pru_03_sucio_no_contemplado.csv", "generador": "tools/limpieza/ensuciar_pru_03.py",
     "semilla": SEMILLA, "resumen": resumen, "estructura": extra_nc, "detalle": verdad},
    ensure_ascii=False, indent=2), encoding="utf-8")
print("no contemplado:", resumen)
