"""Construye el BORRADOR del banco de evaluación v1 del chat (11 nov 2026) para revisión humana.

Qué contiene (tools/rag/evaluacion/banco_v1_borrador.json y .csv):
  - 62 preguntas, 2 por instrumento vigente (31), redactadas con palabras distintas a las del instrumento para no
    favorecer a la búsqueda por palabras; cada una con 2 paráfrasis.
  - Su fragmento correcto («relevantes»): instrumento + preguntaId (pregunta, reactivo o pregunta guía). Un fragmento
    recuperado cuenta como relevante si es de ese instrumento y trae ese preguntaId (la pregunta, el reactivo o los
    intercambios de esa pregunta guía). No depende del texto del fragmento: sobrevive a una reindexación.
  - La respuesta esperada de encuestas y pruebas, calculada con SQL sobre tt_rag.respuesta_interpretada (versión
    vigente), sin usar el chat: opción más elegida, su porcentaje y la distribución completa. Las entrevistas no tienen
    cifra: sus «hechos_clave» los completa quien revisa (campo `revisar`).
  - 8 preguntas SIN respuesta (temas que ningún fragmento menciona; verificado con una búsqueda en
    documento_vectorizado) y 2 fuera de dominio: miden si el chat sabe decir que no tiene información.
  - División desarrollo / prueba: las preguntas «a» de cada instrumento y 6 de las 10 sin respuesta van a PRUEBA (se
    reporta con ellas y nunca se usan para ajustar umbrales); las «b» y el resto, a DESARROLLO (para calibrar).

Uso (con la app levantada):  python tools/rag/evaluacion/construir_banco_v1.py
Después de revisar el CSV, se congela copiando banco_v1_borrador.json a banco_v1.json.
"""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SALIDA = Path(__file__).resolve().parent

# (instrumento, tipo, [(clave, preguntaId corto, pregunta, [paráfrasis, paráfrasis])]).
PREGUNTAS: list[tuple[str, str, list[tuple[str, str, str, list[str]]]]] = [
    ("86", "encuesta", [
        ("a", "p01", "¿Los estudiantes suelen ordenar sus materiales antes de ponerse a estudiar?",
         ["¿Qué tanto preparan su material antes de estudiar?", "¿Acostumbran acomodar lo que van a estudiar antes de empezar?"]),
        ("b", "p04", "¿Con qué frecuencia repasan sus notas al salir de clase?",
         ["¿Revisan sus apuntes justo después de la clase?", "¿Qué tan seguido releen lo que anotaron al terminar la clase?"]),
    ]),
    ("87", "encuesta", [
        ("a", "p06", "¿Los alumnos van a todas sus clases?",
         ["¿Qué tan regular es su asistencia a clase?", "¿Faltan mucho a clases los estudiantes?"]),
        ("b", "p02", "¿Relacionan lo nuevo que aprenden con lo que ya han vivido?",
         ["¿Vinculan los contenidos nuevos con sus experiencias anteriores?", "¿Conectan lo que aprenden con vivencias previas?"]),
    ]),
    ("88", "encuesta", [
        ("a", "p01", "¿A los estudiantes les gusta asistir a la universidad?",
         ["¿Qué tanto disfrutan ir a la universidad?", "¿Les agrada estar en la universidad?"]),
        ("b", "p03", "¿Se sienten aceptados en la universidad?",
         ["¿Sienten que la universidad los acepta como son?", "¿Qué tan aceptados se perciben en la institución?"]),
    ]),
    ("89", "encuesta", [
        ("a", "p02", "¿Inventan sus propios ejemplos para entender los temas?",
         ["¿Crean ejemplos propios cuando estudian?", "¿Usan ejemplos hechos por ellos mismos para comprender los conceptos?"]),
        ("b", "p05", "¿Relacionan lo que ven en esta materia con otras asignaturas?",
         ["¿Vinculan lo aprendido con otras materias?", "¿Conectan los contenidos de esta clase con los de otros cursos?"]),
    ]),
    ("90", "encuesta", [
        ("a", "p06", "¿Estudian de forma constante o solo antes del examen?",
         ["¿Estudian con regularidad durante el periodo?", "¿Dejan el estudio para el último momento antes de los exámenes?"]),
        ("b", "p05", "¿Toman el liderazgo en los proyectos de clase?",
         ["¿Suelen dirigir los proyectos en equipo?", "¿Qué tanto asumen el papel de líder en los trabajos de clase?"]),
    ]),
    ("91", "encuesta", [
        ("a", "p01", "¿Los profesores tratan igual a todos los alumnos?",
         ["¿Reciben todos los estudiantes el mismo trato de parte del docente?", "¿Hay trato parejo del profesor hacia todo el grupo?"]),
        ("b", "p05", "¿Hay diversidad de orígenes culturales en los grupos?",
         ["¿En los salones conviven estudiantes de distintas culturas?", "¿Qué tan diverso culturalmente es su grupo?"]),
    ]),
    ("92", "encuesta", [
        ("a", "p02", "¿Cómo manejan el estrés de la escuela?",
         ["¿Qué tan bien llevan la presión académica?", "¿Saben controlar el estrés que les generan los estudios?"]),
        ("b", "p03", "¿Tienen a alguien de confianza para platicar sus problemas?",
         ["¿Cuentan con personas con quienes hablar de lo que les preocupa?", "¿Tienen con quién desahogarse cuando tienen problemas?"]),
    ]),
    ("93", "encuesta", [
        ("a", "p01", "¿Les parece manejable el número de materias que llevan?",
         ["¿Pueden con la cantidad de asignaturas que cursan?", "¿Consideran razonable cuántas materias tienen?"]),
        ("b", "p05", "¿Usan agenda o calendario para planear sus actividades?",
         ["¿Planean con anticipación lo que tienen que hacer?", "¿Organizan sus pendientes en un calendario?"]),
    ]),
    ("94", "prueba_estandarizada", [
        ("a", "r04", "¿Qué respondieron los alumnos cuando se les preguntó qué es el phishing?",
         ["¿Qué opción eligieron más sobre el phishing?", "¿Cómo definieron el phishing los estudiantes en la prueba?"]),
        ("b", "r03", "¿Qué opción eligieron más sobre para qué sirve una VPN?",
         ["¿Qué contestaron sobre la función de una VPN?", "¿Para qué creen los alumnos que se usa una VPN?"]),
    ]),
    ("95", "prueba_estandarizada", [
        ("a", "r02", "¿Buscan recursos extra cuando no entienden un tema?",
         ["¿Consultan materiales adicionales si algo no les queda claro?", "¿Qué hacen cuando no comprenden bien un tema: buscan más fuentes?"]),
        ("b", "r05", "¿Administran su tiempo sin que nadie se lo recuerde?",
         ["¿Organizan su tiempo por su cuenta, sin recordatorios?", "¿Qué tan independientes son para manejar su tiempo?"]),
    ]),
    ("96", "prueba_estandarizada", [
        ("a", "r06", "¿Qué entienden los alumnos por aprendizaje activo?",
         ["¿Cómo definieron el aprendizaje activo en el aula?", "¿Qué opción eligieron más sobre el aprendizaje activo?"]),
        ("b", "r03", "¿Qué piensan que indica la retroalimentación formativa de un docente?",
         ["¿Qué contestaron sobre la retroalimentación formativa?", "¿Para qué creen que sirve la retroalimentación formativa del profesor?"]),
    ]),
    ("97", "prueba_estandarizada", [
        ("a", "r04", "¿Qué contestaron sobre la triangulación en investigación?",
         ["¿Cómo entienden los alumnos la triangulación?", "¿Qué opción eligieron más sobre triangular en una investigación?"]),
        ("b", "r03", "¿Cómo entienden la validez de un instrumento de medición?",
         ["¿Qué respondieron sobre la validez de un instrumento?", "¿Qué creen que significa que un instrumento sea válido?"]),
    ]),
    ("98", "prueba_estandarizada", [
        ("a", "r05", "¿Qué sector laboral prefieren los estudiantes?",
         ["¿En qué sector les gustaría trabajar?", "¿Qué área de trabajo les atrae más a los alumnos?"]),
        ("b", "r01", "¿En qué tipo de ambiente de trabajo creen que rendirían mejor?",
         ["¿Dónde piensan que se desempeñarían mejor laboralmente?", "¿Qué entorno laboral prefieren para trabajar a gusto?"]),
    ]),
    ("99", "prueba_estandarizada", [
        ("a", "r06", "¿Qué respondieron sobre la distancia al poder de Hofstede?",
         ["¿Cómo entienden la dimensión de distancia al poder?", "¿Qué opción eligieron más sobre la distancia al poder en las dimensiones culturales?"]),
        ("b", "r02", "¿Qué entienden por etnocentrismo en el ámbito académico?",
         ["¿Cómo definieron el etnocentrismo en la universidad?", "¿Qué contestaron sobre el etnocentrismo académico?"]),
    ]),
    ("100", "prueba_estandarizada", [
        ("a", "r05", "¿Cómo creen que se presenta una cita textual larga en APA?",
         ["¿Qué respondieron sobre las citas directas de más de 40 palabras en APA?", "¿Cómo dicen que se escribe una cita larga en estilo APA?"]),
        ("b", "r03", "¿Qué conector eligieron para expresar contraste?",
         ["¿Qué palabra de enlace marcaron como de contraposición?", "¿Qué conectivo identificaron para oponer ideas?"]),
    ]),
    ("101", "encuesta", [
        ("a", "p01", "¿Les alcanza la biblioteca para lo que necesitan?",
         ["¿Están conformes con los servicios bibliotecarios, físicos y digitales?", "¿La biblioteca cubre sus necesidades académicas?"]),
        ("b", "p04", "¿Qué tan rápidos les parecen los trámites administrativos?",
         ["¿Consideran eficientes los trámites de la institución?", "¿Cómo califican la agilidad de los procesos administrativos?"]),
    ]),
    ("102", "encuesta", [
        ("a", "p02", "¿Esperan trabajar en lo que estudiaron?",
         ["¿Creen que se emplearán en su área de formación?", "¿Piensan trabajar en su campo al egresar?"]),
        ("b", "p05", "¿Se sienten listos para el mundo laboral?",
         ["¿Qué tan preparados se perciben para los retos del trabajo?", "¿Se sienten capaces de enfrentar el mercado laboral?"]),
    ]),
    ("103", "prueba_estandarizada", [
        ("a", "r02", "¿Qué papel le dan al docente en el aprendizaje basado en problemas?",
         ["¿Qué contestaron sobre la función del profesor en el ABP?", "¿Cómo describen el rol del docente en el modelo ABP?"]),
        ("b", "r06", "¿Qué entienden por metacognición dentro del ABP?",
         ["¿Qué respondieron sobre la metacognición en el aprendizaje basado en problemas?", "¿Cómo definieron la metacognición en el ABP?"]),
    ]),
    ("104", "prueba_estandarizada", [
        ("a", "r03", "¿Qué respuesta eligieron más en el problema del artículo de $500 con 20 % de descuento?",
         ["¿Cuánto dijeron que se paga con el descuento del 20 %?", "¿Qué contestaron en el ejercicio del descuento?"]),
        ("b", "r06", "¿Qué contestaron sobre la raíz cuadrada de 144?",
         ["¿Qué opción marcaron más para la raíz de 144?", "¿Cuánto dijeron que vale la raíz cuadrada de 144?"]),
    ]),
    ("105", "prueba_estandarizada", [
        ("a", "r02", "¿Animan a sus compañeros cuando el equipo tiene problemas?",
         ["¿Motivan al grupo cuando las cosas se complican?", "¿Qué tanto alientan a sus compañeros en momentos difíciles?"]),
        ("b", "r05", "¿Cómo manejan los conflictos cuando hay desacuerdos?",
         ["¿Resuelven bien los desacuerdos en el grupo?", "¿Qué tan constructivos son al enfrentar conflictos?"]),
    ]),
    ("106", "entrevista", [
        ("a", "p03", "¿Cómo ha influido la familia en que sigan estudiando?",
         ["¿Qué papel tiene el apoyo familiar en su permanencia?", "¿Sus familias los han ayudado a no dejar la universidad?"]),
        ("b", "p05", "¿Cómo han enfrentado los problemas de dinero durante la carrera?",
         ["¿Qué hacen ante las dificultades económicas en la universidad?", "¿Cómo sortean la falta de recursos para estudiar?"]),
    ]),
    ("107", "entrevista", [
        ("a", "p05", "¿Qué opinan del tamaño de los grupos en sus clases?",
         ["¿Cómo les afecta que los grupos sean grandes o pequeños?", "¿Influye cuántos alumnos hay en el salón en cómo aprenden?"]),
        ("b", "p02", "¿Cómo sería para ellos el profesor ideal?",
         ["¿Qué cualidades valoran más en un docente?", "¿Qué características debe tener un buen profesor según ellos?"]),
    ]),
    ("108", "entrevista", [
        ("a", "p05", "¿Qué problemas tecnológicos han tenido al estudiar?",
         ["¿Qué obstáculos de tecnología han enfrentado en sus estudios?", "¿Qué fallas o limitaciones tecnológicas les han afectado?"]),
        ("b", "p02", "¿Qué opinan de la plataforma virtual de su universidad?",
         ["¿Cómo ha sido su experiencia con el LMS institucional?", "¿Les funciona bien la plataforma en línea de la escuela?"]),
    ]),
    ("109", "entrevista", [
        ("a", "p02", "¿Han vivido o visto discriminación en el campus?",
         ["¿Han presenciado situaciones de exclusión en la universidad?", "¿Han sido testigos o víctimas de trato discriminatorio en la institución?"]),
        ("b", "p06", "¿Qué cambiarían para que la universidad sea más inclusiva?",
         ["¿Qué propuestas tienen para mejorar la inclusión?", "¿Qué harían para que la institución incluya a todos?"]),
    ]),
    ("110", "entrevista", [
        ("a", "p03", "¿Qué obstáculos encuentran para publicar en revistas de alto impacto?",
         ["¿Qué dificultades tienen para que les acepten artículos en revistas indexadas?", "¿Por qué les cuesta publicar en revistas importantes?"]),
        ("b", "p06", "¿Cómo trabajan con otros investigadores o instituciones?",
         ["¿Colaboran con investigadores de otras instituciones?", "¿Qué tipo de colaboración científica tienen?"]),
    ]),
    ("111", "entrevista", [
        ("a", "p01", "¿Les sirvió la orientación vocacional antes de entrar a la universidad?",
         ["¿Recibieron orientación para elegir carrera y les fue útil?", "¿Qué tan útil fue la orientación que tuvieron antes de ingresar?"]),
        ("b", "p06", "¿Qué tan preparados se sienten para conseguir trabajo?",
         ["¿Se sienten listos para el mercado laboral?", "¿Creen estar preparados para emplearse al egresar?"]),
    ]),
    ("112", "entrevista", [
        ("a", "p04", "¿Cómo combinan las actividades extracurriculares con la escuela?",
         ["¿Cómo equilibran lo extracurricular con sus deberes académicos?", "¿Les da tiempo de hacer actividades fuera de clase sin descuidar sus estudios?"]),
        ("b", "p06", "¿Qué actividades nuevas les gustaría que hubiera?",
         ["¿Qué otras actividades proponen que ofrezca la universidad?", "¿Qué actividades echan de menos en su institución?"]),
    ]),
    ("113", "entrevista", [
        ("a", "p01", "¿De dónde sacan el dinero para pagar sus estudios?",
         ["¿Cómo financian su carrera?", "¿Con qué recursos pagan la universidad?"]),
        ("b", "p03", "¿El costo de estudiar ha sido un obstáculo para ellos?",
         ["¿Lo caro de la educación les ha dificultado estudiar?", "¿Qué tanto les ha frenado el costo de la universidad?"]),
    ]),
    ("114", "entrevista", [
        ("a", "p03", "¿Qué fue lo más difícil de su primer año?",
         ["¿Qué retos enfrentaron al empezar la universidad?", "¿Cuáles fueron sus principales dificultades en el primer año?"]),
        ("b", "p05", "¿Cómo se integraron con compañeros y profesores al principio?",
         ["¿Cómo fue su socialización al inicio de la carrera?", "¿Les costó relacionarse con compañeros y docentes al llegar?"]),
    ]),
    ("115", "entrevista", [
        ("a", "p04", "¿Qué complicaciones tuvieron al estudiar en el extranjero?",
         ["¿Qué dificultades encontraron en su intercambio internacional?", "¿Qué se les hizo difícil al estudiar en otro país?"]),
        ("b", "p06", "¿Cómo apoya la universidad los intercambios internacionales?",
         ["¿Qué apoyo da la institución para la movilidad académica?", "¿La universidad respalda los programas de internacionalización?"]),
    ]),
    ("117", "encuesta", [
        ("a", "p03", "¿Los estudiantes toman sus clases presenciales, en línea o mixtas?",
         ["¿En qué modalidad estudian su programa?", "¿Cómo cursan su carrera: presencial o a distancia?"]),
        ("b", "p05", "¿Cuántos de sus profesores tienen doctorado?",
         ["¿Qué proporción de sus docentes cuenta con doctorado?", "¿Sus profesores de este periodo tienen grado de doctor?"]),
    ]),
]

# Sin respuesta: ningún fragmento indexado menciona el tema (búsqueda en documento_vectorizado, 11 nov 2026).
SIN_RESPUESTA = [
    ("S01", "¿Cuántos estudiantes consumen alcohol o tabaco?", "alcohol|tabaco", "prueba"),
    ("S02", "¿Qué opinan los estudiantes del estacionamiento de la universidad?", "estacionamiento", "prueba"),
    ("S03", "¿Cómo afectó la pandemia de COVID-19 a los estudiantes?", "pandemia|covid", "prueba"),
    ("S04", "¿Cuántas horas a la semana juegan videojuegos los alumnos?", "videojuego", "prueba"),
    ("S05", "¿Están cómodos los estudiantes con el aire acondicionado de las aulas?", "aire acondicionado|clima", "prueba"),
    ("S06", "¿Qué piensan los alumnos sobre usar uniforme?", "uniforme", "prueba"),
    ("S07", "¿Con qué frecuencia usan los estudiantes el gimnasio de la universidad?", "gimnasio", "desarrollo"),
    ("S08", "¿Participaron los estudiantes en alguna huelga o paro?", "huelga|paro estudiantil", "desarrollo"),
]
FUERA_DE_DOMINIO = [
    ("F01", "¿Cuál es la capital de Francia?", "prueba"),
    ("F02", "Dame una receta para hacer pastel de chocolate.", "desarrollo"),
]


def _psql_json(sql: str):
    r = subprocess.run(["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "indagata_db",
                        "-t", "-A", "-c", sql], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    salida = r.stdout.strip()
    return json.loads(salida) if salida else None


def _distribucion(id_crudo: str, pregunta: str) -> dict | None:
    """Distribución de respuestas de la versión vigente (respuesta_interpretada), sin usar el chat."""
    pid = f"INS-{int(id_crudo):04d}-{pregunta}"
    filas = _psql_json(f"""
        SELECT json_agg(json_build_object('opcion', significado, 'n', n) ORDER BY n DESC) FROM (
          SELECT significado, count(*) AS n FROM tt_rag.respuesta_interpretada
          WHERE id_crudo = {int(id_crudo)} AND pregunta_id = '{pid}' AND estado IN ('respondida', 'valida')
            AND version = (SELECT max(version) FROM tt_rag.respuesta_interpretada WHERE id_crudo = {int(id_crudo)})
          GROUP BY significado) t""")
    if not filas:
        return None
    total = sum(f["n"] for f in filas)
    distribucion = [{"opcion": f["opcion"], "n": f["n"], "porcentaje": round(100 * f["n"] / total, 1)} for f in filas]
    return {"respondieron": total, "distribucion": distribucion}


def _titulos() -> dict[str, str]:
    filas = _psql_json("SELECT json_object_agg(id_crudo::text, dc_title) FROM tt_rag.metadatos_dc") or {}
    return {k: v for k, v in filas.items() if v}


def main() -> None:
    titulos = _titulos()
    preguntas = []
    for id_crudo, tipo, items in PREGUNTAS:
        for clave, pid, texto, parafrasis in items:
            entrada = {
                "id": f"I{id_crudo}-{clave}",
                "conjunto": "prueba" if clave == "a" else "desarrollo",
                "tipo": "con_respuesta",
                "tipo_instrumento": tipo,
                "instrumento": titulos.get(id_crudo, ""),
                "alcance": [id_crudo],
                "pregunta": texto,
                "parafrasis": parafrasis,
                "decision_esperada": "dentro",
                "relevantes": [{"instrumentoId": id_crudo, "preguntaId": f"INS-{int(id_crudo):04d}-{pid}"}],
                "esperada": None,
                "cifras_clave": [],
                "hechos_clave": [],
                "verificacion": "",
                "revisar": "",
            }
            if tipo == "entrevista":
                entrada["verificacion"] = "anotación humana (entrevista: sin cifra)"
                entrada["revisar"] = "Escribir 1–3 hechos clave que debe mencionar una buena respuesta."
            else:
                d = _distribucion(id_crudo, pid)
                if d:
                    top = d["distribucion"][0]
                    entrada["esperada"] = (f"Más elegida: «{top['opcion']}», {top['porcentaje']} % "
                                           f"({top['n']} de {d['respondieron']}).")
                    entrada["cifras_clave"] = [str(top["porcentaje"])]
                    entrada["distribucion"] = d["distribucion"]
                    entrada["verificacion"] = "SQL sobre respuesta_interpretada (versión vigente)"
                else:
                    entrada["revisar"] = "No se encontró la distribución: revisar el preguntaId."
            preguntas.append(entrada)
    for ident, texto, patron, conjunto in SIN_RESPUESTA:
        preguntas.append({"id": ident, "conjunto": conjunto, "tipo": "sin_respuesta", "alcance": [], "pregunta": texto,
                          "parafrasis": [], "decision_esperada": "sin_informacion", "relevantes": [],
                          "verificacion": f"0 fragmentos con ~* '({patron})' en documento_vectorizado (11 nov 2026)",
                          "revisar": ""})
    for ident, texto, conjunto in FUERA_DE_DOMINIO:
        preguntas.append({"id": ident, "conjunto": conjunto, "tipo": "fuera_de_dominio", "alcance": [], "pregunta": texto,
                          "parafrasis": [], "decision_esperada": "fuera", "relevantes": [], "verificacion": "",
                          "revisar": ""})

    banco = {"version": "1-borrador", "fecha": date.today().isoformat(), "estado": "borrador: falta revisión humana",
             "criterio_relevancia": "mismo instrumentoId y preguntaId (pregunta, reactivo o intercambios de la pregunta guía)",
             "preguntas": preguntas}
    (SALIDA / "banco_v1_borrador.json").write_text(json.dumps(banco, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(SALIDA / "banco_v1_borrador.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "conjunto", "tipo", "instrumento", "pregunta", "paráfrasis 1", "paráfrasis 2",
                    "fragmento correcto", "respuesta esperada", "pendiente de revisar", "OK (sí/no)", "comentario"])
        for p in preguntas:
            par = p.get("parafrasis") or []
            w.writerow([p["id"], p["conjunto"], p["tipo"], p.get("instrumento", ""), p["pregunta"],
                        par[0] if par else "", par[1] if len(par) > 1 else "",
                        ", ".join(r["preguntaId"] for r in p["relevantes"]), p.get("esperada") or "",
                        p.get("revisar", ""), "", ""])
    resumen = {t: sum(1 for p in preguntas if p["tipo"] == t) for t in ("con_respuesta", "sin_respuesta", "fuera_de_dominio")}
    print(f"{len(preguntas)} preguntas {resumen}; prueba {sum(p['conjunto'] == 'prueba' for p in preguntas)}, "
          f"desarrollo {sum(p['conjunto'] == 'desarrollo' for p in preguntas)}; "
          f"sin distribución: {[p['id'] for p in preguntas if 'No se encontró' in p.get('revisar', '')]}")


if __name__ == "__main__":
    main()
