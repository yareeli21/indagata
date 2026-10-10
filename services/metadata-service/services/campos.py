"""Catálogo de campos de metadatos (fuente única de verdad del servicio).

Refleja 1:1 las tablas de infrastructure/postgres/init/01_schema.sql:
  - metadatos_dc                         (13 campos Dublin Core, OBLIGATORIOS para
                                          todo instrumento salvo `dc_relation`)
  - metadatos_enriquecidos_encuestas
  - metadatos_enriquecidos_entrevistas
  - metadatos_enriquecidos_pruebas

`requerido` define qué debe estar completo para que el autor pueda aprobar los
metadatos (requisito para ingerir el instrumento al RAG). `automatico` marca los
campos que el sistema completa a partir de hechos (usuario, archivo, fecha).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from shared.models.metadatos_encuestas import MetadatosEnriquecidosEncuestas
from shared.models.metadatos_entrevistas import MetadatosEnriquecidosEntrevistas
from shared.models.metadatos_pruebasestandarizadas import MetadatosEnriquecidosPruebas

TipoDato = Literal["texto", "texto_largo", "entero", "lista", "mapa"]


@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    tipo: TipoDato = "texto"
    requerido: bool = False
    automatico: bool = False
    ayuda: str = ""
    max_longitud: int | None = None

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)


CAMPOS_DC: tuple[Campo, ...] = (
    Campo("dc_title", "Título", requerido=True, ayuda="Nombre con el que se identifica el instrumento."),
    Campo("dc_creator", "Creador", requerido=True, automatico=True, ayuda="Autor o equipo responsable."),
    Campo("dc_subject", "Tema", requerido=True, ayuda="Temas o palabras clave, separados por comas."),
    Campo("dc_description", "Descripción", "texto_largo", requerido=True, ayuda="Qué mide el instrumento, a quién y para qué."),
    Campo("dc_type", "Tipo", requerido=True, automatico=True, max_longitud=50),
    Campo("dc_date", "Fecha", requerido=True, automatico=True, max_longitud=100),
    Campo("dc_language", "Idioma", requerido=True, automatico=True, max_longitud=10, ayuda="Código ISO 639-1, p. ej. es."),
    Campo("dc_coverage", "Cobertura", requerido=True, ayuda="Nivel educativo y alcance (población, lugar, periodo)."),
    Campo("dc_publisher", "Editor", requerido=True, automatico=True, ayuda="Institución que pone a disposición el instrumento."),
    Campo("dc_rights", "Derechos", requerido=True, max_longitud=255, ayuda="Licencia o condiciones de uso."),
    Campo("dc_format", "Formato", requerido=True, automatico=True, max_longitud=50),
    Campo("dc_source", "Fuente", requerido=True, automatico=True, ayuda="Archivo u obra de origen."),
    Campo("dc_relation", "Relación", ayuda="Instrumentos o proyectos relacionados (opcional)."),
)

CAMPOS_ENCUESTA: tuple[Campo, ...] = (
    Campo("n_respondentes", "Número de respondentes", "entero", requerido=True, ayuda="Registros con respuesta en el archivo."),
    Campo("n_poblacion", "Tamaño de la población", "entero", ayuda="Universo del que se extrajo la muestra."),
    Campo("objetivo", "Objetivo", "texto_largo", requerido=True),
    Campo("carrera", "Carrera(s)", ayuda="Programas educativos de los respondentes."),
    Campo("poblacion_objetivo", "Población objetivo", requerido=True),
    Campo("constructo_principal", "Constructo principal", requerido=True, ayuda="Concepto teórico que mide la encuesta."),
    Campo("palabras_clave", "Palabras clave", "lista", requerido=True),
    Campo("dimensiones", "Dimensiones", "lista", requerido=True, ayuda="Subescalas o bloques de reactivos."),
    Campo("notas_contextuales", "Notas contextuales", "texto_largo"),
    Campo("notas_interpretacion", "Notas de interpretación", "texto_largo"),
)

CAMPOS_ENTREVISTA: tuple[Campo, ...] = (
    Campo("identificador_propio", "Identificador propio", automatico=True),
    Campo("objetivo", "Objetivo", "texto_largo", requerido=True),
    Campo("metodologia", "Metodología", requerido=True, ayuda="Estructurada, semiestructurada, a profundidad, grupo focal…"),
    Campo("institucion", "Institución", requerido=True),
    Campo("derechos", "Derechos", ayuda="Consentimiento informado y condiciones de uso."),
)

CAMPOS_PRUEBA: tuple[Campo, ...] = (
    Campo("unidad_de_aprendizaje", "Unidad de aprendizaje", requerido=True),
    Campo("mapeo_de_reactivos_por_seccion", "Reactivos por sección", "mapa", ayuda="Una línea por sección: «Sección: número»."),
    Campo("institucion", "Institución"),
    Campo("campus", "Campus"),
    Campo("grado", "Grado"),
    Campo("grupo", "Grupo"),
    Campo("ciclo_escolar", "Ciclo escolar"),
    Campo("tipo_de_prueba", "Tipo de prueba", requerido=True, ayuda="Diagnóstica, formativa, sumativa…"),
    Campo("version", "Versión"),
    Campo("taxonomia_bloom", "Taxonomía de Bloom", ayuda="Niveles cognitivos que evalúa."),
    Campo("nivel_educativo", "Nivel educativo", requerido=True),
    Campo("objetivo_de_evaluacion", "Objetivo de la evaluación", "texto_largo", requerido=True),
    Campo("subareas", "Subáreas"),
    Campo("competencias", "Competencias", "texto_largo"),
)

CAMPOS_POR_TIPO: dict[str, tuple[Campo, ...]] = {
    "encuesta": CAMPOS_ENCUESTA,
    "entrevista": CAMPOS_ENTREVISTA,
    "prueba_estandarizada": CAMPOS_PRUEBA,
}

TABLA_POR_TIPO: dict[str, type] = {
    "encuesta": MetadatosEnriquecidosEncuestas,
    "entrevista": MetadatosEnriquecidosEntrevistas,
    "prueba_estandarizada": MetadatosEnriquecidosPruebas,
}

NOMBRE_TABLA_POR_TIPO: dict[str, str] = {
    "encuesta": "metadatos_enriquecidos_encuestas",
    "entrevista": "metadatos_enriquecidos_entrevistas",
    "prueba_estandarizada": "metadatos_enriquecidos_pruebas",
}

TIPO_UI: dict[str, str] = {
    "encuesta": "Encuesta",
    "entrevista": "Entrevista",
    "prueba_estandarizada": "Prueba estandarizada",
}


def campos_de(tipo: str) -> tuple[Campo, ...]:
    try:
        return CAMPOS_POR_TIPO[tipo]
    except KeyError as exc:
        raise ValueError(f"Tipo de instrumento no soportado: {tipo}") from exc


def obligatorios(campos: tuple[Campo, ...]) -> list[str]:
    return [c.clave for c in campos if c.requerido]
