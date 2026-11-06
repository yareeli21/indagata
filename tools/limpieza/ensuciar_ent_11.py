"""Genera la versión con ruido de ent_11 a partir de la limpia y guarda la verdad del ruido inyectado.

Uso: python tools/limpieza/ensuciar_ent_11.py storage/instrumentos_sinteticos/entrevistas
Es determinista: siempre produce el mismo archivo con ruido.
"""
import json
import sys
from pathlib import Path

carpeta = Path(sys.argv[1])
limpia = (carpeta / "ent_11_salud_mental_limpia.txt").read_text(encoding="utf-8")
lineas = limpia.split("\n")
verdad: dict[str, list] = {}


def anotar(tipo, detalle):
    verdad.setdefault(tipo, []).append(detalle)


salida = []
# Encabezado de exportación con ID, separadores y página.
salida += ["*" * 40, "ID: ENT-0011", "Folio 2026-114", "*" * 40, ""]
anotar("identificador", "ID: ENT-0011")
anotar("identificador", "Folio 2026-114")
anotar("separador", "*" * 40)
anotar("separador", "*" * 40)

reloj = 0
turno = 0
pagina = 1
for linea in lineas:
    if linea.startswith(("Entrevistadora:", "Entrevistada:")):
        turno += 1
        reloj += 95
        h, m, s = reloj // 3600, reloj // 60 % 60, reloj % 60
        etiqueta, texto = linea.split(":", 1)
        texto = texto.strip()
        # Marcas de tiempo: entre corchetes (impares) o al inicio de línea sin corchetes (pares).
        marca = f"[{h:02d}:{m:02d}:{s:02d}]" if turno % 2 else f"{h:02d}:{m:02d}:{s:02d}"
        anotar("marca_de_tiempo", marca)
        # Negritas de Markdown en la etiqueta cada tercer turno.
        etq = f"**{etiqueta}:**" if turno % 3 == 0 else f"{etiqueta}:"
        if turno % 3 == 0:
            anotar("negritas_markdown", etq)
        # Espacios dobles, tabulador y espacio antes de coma.
        if turno % 4 == 1:
            texto = texto.replace(", ", " , ", 1).replace(". ", ".  ", 1)
            anotar("espacios", f"turno {turno}: espacio antes de coma y doble espacio")
        if turno % 5 == 2:
            texto = texto.replace(" ", "\t", 1)
            anotar("tabulador", f"turno {turno}")
        # Caracteres invisibles (espacio de ancho cero y espacio duro).
        if turno % 6 == 0:
            texto = texto.replace(" ", " ​", 1).replace(" ", " ", 1)
            anotar("invisibles", f"turno {turno}: U+200B y U+00A0")
        # Muletillas de transcripción automática al inicio de respuestas.
        if etiqueta == "Entrevistada" and turno in (4, 8, 14, 20):
            muletilla = {4: "Eh, ", 8: "Mmm... ", 14: "Em, ", 20: "Ehm, "}[turno]
            texto = muletilla + texto
            anotar("muletilla", muletilla.strip())
        nueva = f"{marca} {etq} {texto}"
        # Palabras partidas por guion de fin de línea.
        for palabra in ("psicológica", "respiración", "coordinación", "confidencial"):
            if palabra in nueva and palabra not in json.dumps(verdad.get("palabra_partida", []), ensure_ascii=False):
                corte = len(palabra) // 2
                nueva = nueva.replace(palabra, f"{palabra[:corte]}-\n{palabra[corte:]}", 1)
                anotar("palabra_partida", f"{palabra[:corte]}-/{palabra[corte:]}")
                break
        salida.append(nueva)
        # Salto de página cada 6 turnos: separador y número de página.
        if turno % 6 == 0:
            pagina += 1
            pie = f"Página {pagina - 1} de 5" if pagina % 2 else f"- {pagina - 1} -"
            salida += ["", pie, "-" * 30, ""]
            anotar("numero_de_pagina", pie)
            anotar("separador", "-" * 30)
    else:
        salida.append(linea)

texto = "\n".join(salida)
# Letras espaciadas (texto copiado de un PDF).
for palabra in ("ansiedad", "estadística"):
    texto = texto.replace(palabra, " ".join(palabra), 1)
    anotar("letras_espaciadas", " ".join(palabra))
# Fin de línea de Windows.
texto = texto.replace("\n", "\r\n")
anotar("fin_de_linea", "CRLF en todo el archivo")

(carpeta / "ent_11_salud_mental_ruido.txt").write_bytes(texto.encode("utf-8"))
resumen = {tipo: len(v) for tipo, v in verdad.items()}
(carpeta / "ent_11_ruido_inyectado.json").write_text(
    json.dumps({"archivo_limpio": "ent_11_salud_mental_limpia.txt", "archivo_con_ruido": "ent_11_salud_mental_ruido.txt",
                "resumen": resumen, "detalle": verdad}, ensure_ascii=False, indent=2), encoding="utf-8")
print(resumen)
