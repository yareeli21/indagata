"""Genera la versión de ent_11 con ruido que la limpieza NO tiene contemplado, y guarda la verdad del ruido.

Uso: python tools/limpieza/ensuciar_ent_11_no_contemplado.py storage/instrumentos_sinteticos/entrevistas
Es determinista: siempre produce el mismo archivo. A diferencia de `ensuciar_ent_11.py`, este ruido se eligió de
lo que suele traer una transcripción real y no tiene regla en el cleaning-service (`texto.py`, `transcripcion.py`,
`limpieza.yaml`), para medir el límite de la limpieza. Cada inyección guarda la cadena exacta que se metió, para
buscarla después en el texto limpio.
"""
import json
import sys
from pathlib import Path

carpeta = Path(sys.argv[1])
limpia = (carpeta / "ent_11_salud_mental_limpia.txt").read_text(encoding="utf-8")
verdad: list[dict] = []


def anotar(tipo: str, inyectado: str, nota: str = "") -> None:
    verdad.append({"tipo": tipo, "inyectado": inyectado, **({"nota": nota} if nota else {})})


# Ruido dentro de las respuestas: (turno de la entrevistada, texto a buscar, reemplazo, tipo).
_EN_TEXTO = [
    (1, "Ha sido un semestre pesado.", "Ha sido un semestre pesado, o sea,", "muletilla_no_contemplada"),
    (1, "no por flojera", "no por flojera [risas]", "anotacion_transcriptor"),
    (2, "Sobre todo la carga", "Este... pues sobre todo la carga", "muletilla_no_contemplada"),
    (2, "en una papelería", "en una [inaudible 00:05:41] papelería", "anotacion_transcriptor"),
    (3, "Sabía que existía algo", "Yo, yo sabía que existía algo", "arranque_en_falso"),
    (4, "orientación psicológica", "orientación psicológica, ¿no?,", "muletilla_no_contemplada"),
    (4, "ejercicios de respiración", "ejercicios de res piración", "error_reconocimiento_voz"),
    (5, "Pasaron casi dos semanas.", "Pasaron casi dos semanas. (silencio)", "anotacion_transcriptor"),
    (6, "Me daba pena", "Me daba, me daba pena", "arranque_en_falso"),
    (6, "está loca", "está loca [hablan al mismo tiempo]", "anotacion_transcriptor"),
    (7, "La psicóloga fue muy amable", "La psicóloga fue muy amable (la entrevistada sonríe)", "nota_del_entrevistador"),
    (9, "Mi tutor académico", "Mi tu tor académico", "error_reconocimiento_voz"),
    (10, "En mi grupo somos treinta y dos", "En mi grupo somos treinta y dos, este,", "muletilla_no_contemplada"),
    (11, "Primero, que hubiera más psicólogos", "Primero, que hubiera más sicólogos", "error_reconocimiento_voz"),
    (12, "Que no espere a estar muy mal", "Que no espere a estar muy mal [pausa larga]", "anotacion_transcriptor"),
]
# Mojibake: UTF-8 leído como latin-1 y guardado otra vez (solo en un turno, como pasa al pegar de otro programa).
_MOJIBAKE_TURNO = 8
_ENCABEZADO_PAGINA = "Universidad Tecnológica — Transcripción confidencial — Proyecto Bienestar 2026"
_PIE_PAGINA = "Documento de uso interno. Prohibida su reproducción."

salida = [_ENCABEZADO_PAGINA, ""]
anotar("encabezado_repetido", _ENCABEZADO_PAGINA, "encabezado con texto al inicio de cada página")
turno_entrevistada = 0
turno = 0
for linea in limpia.split("\n"):
    if not linea.startswith(("Entrevistadora:", "Entrevistada:")):
        salida.append(linea)
        continue
    turno += 1
    etiqueta, texto = linea.split(":", 1)
    texto = texto.strip()
    if etiqueta == "Entrevistada":
        turno_entrevistada += 1
        for n, buscar, poner, tipo in _EN_TEXTO:
            if n == turno_entrevistada:
                assert buscar in texto, (n, buscar)
                texto = texto.replace(buscar, poner, 1)
                anotar(tipo, poner, f"respuesta {n}; original: «{buscar}»")
        if turno_entrevistada == _MOJIBAKE_TURNO:
            original = texto
            texto = texto.encode("utf-8").decode("latin-1")
            anotar("mojibake", texto[:60], f"respuesta {_MOJIBAKE_TURNO}; original: «{original[:60]}»")
    # Etiquetas inconsistentes: abreviada o con la hora pegada al estilo de Otter/Descript.
    if turno == 5:
        etiqueta = "E"
        anotar("etiqueta_inconsistente", "E:", "turno 5: «Entrevistadora» abreviada a «E»")
    if turno == 16:
        etiqueta = "ENTREVISTADA"
        anotar("etiqueta_inconsistente", "ENTREVISTADA:", "turno 16: en mayúsculas")
    if turno == 20:
        etiqueta = "Entrevistada (min 23)"
        anotar("marca_de_tiempo_no_contemplada", "(min 23)", "turno 20: hora en minutos junto a la etiqueta")
    salida.append(f"{etiqueta}: {texto}")
    # Salto de página cada 8 turnos: pie y encabezado con texto, sin número de página.
    if turno % 8 == 0:
        salida += ["", _PIE_PAGINA, _ENCABEZADO_PAGINA, ""]
        anotar("pie_repetido", _PIE_PAGINA, f"después del turno {turno}")
        anotar("encabezado_repetido", _ENCABEZADO_PAGINA, f"después del turno {turno}")

(carpeta / "ent_11_salud_mental_ruido_no_contemplado.txt").write_text("\n".join(salida), encoding="utf-8")
(carpeta / "ent_11_ruido_no_contemplado.json").write_text(json.dumps(
    {"archivo_limpio": "ent_11_salud_mental_limpia.txt",
     "archivo_con_ruido": "ent_11_salud_mental_ruido_no_contemplado.txt",
     "generador": "tools/limpieza/ensuciar_ent_11_no_contemplado.py",
     "resumen": {t: sum(1 for v in verdad if v["tipo"] == t) for t in dict.fromkeys(v["tipo"] for v in verdad)},
     "detalle": verdad}, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(verdad), "inyecciones")
