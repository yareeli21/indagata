"""Contrato de los motores de limpieza (uno por tipo de instrumento).

Cada motor implementa dos pasos PUROS (sin red ni base de datos) sobre el
contenido del archivo crudo:

  1. `automatica(entrada)` — fase automática: transforma lo que no requiere
     decisión y detecta los hallazgos que el investigador debe revisar, cada uno
     con opciones y una opción sugerida (preseleccionada).
  2. `aplicar(entrada, automatico, decisiones)` — aplica las decisiones y produce
     el resultado final (filas del CSV limpio, métricas después, vista final).

Como el crudo nunca cambia y ambos pasos son deterministas, al confirmar se
repite la fase automática y se aplican las decisiones guardadas: no hace falta
guardar archivos intermedios.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


class ErrorLimpieza(Exception):
    """La limpieza no puede continuar. El mensaje se muestra tal cual al investigador."""


@dataclass(frozen=True)
class Entrada:
    """Lo que un motor necesita del instrumento (sin acceso a red ni BD)."""

    id_crudo: int
    tipo_instrumento: str  # encuesta | entrevista | prueba_estandarizada
    nombre_archivo: str
    extension: str  # con punto y en minúsculas: ".csv", ".docx"…
    contenido: bytes
    clave: bytes | None = None  # clave de respuestas (pruebas tabulares)
    extension_clave: str | None = None


@dataclass
class Hallazgo:
    """Algo que el investigador debe decidir en la fase asistida.

    Attributes:
        id:          Estable entre ejecuciones del mismo crudo (p. ej. "col-ajena:fecha_inicio"),
                     para poder precargar decisiones al crear una versión nueva.
        tipo:        Clase de hallazgo (columna_ajena, rol_columna, duplicados…); la UI
                     elige la tarjeta según este valor.
        tema:        Agrupación para la UI ("Columnas", "Calidad", "Escalas"…).
        objetivo:    Qué se decide (id de columna, hablante, id de alumno…).
        titulo:      Frase corta para el investigador.
        descripcion: Explicación de por qué se señala.
        opciones:    Valores posibles de la decisión.
        sugerida:    Opción preseleccionada, o None si no hay sugerencia.
        obligatoria: True si el investigador DEBE elegir explícitamente (sin sugerencia válida).
        detalle:     Datos para la tarjeta (ejemplos de valores, conteos…).
    """

    id: str
    tipo: str
    tema: str
    objetivo: str
    titulo: str
    descripcion: str
    opciones: list[str]
    sugerida: str | None = None
    obligatoria: bool = False
    detalle: dict[str, Any] = field(default_factory=dict)

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoAutomatico:
    """Salida de la fase automática."""

    hallazgos: list[Hallazgo]
    transformaciones: list[dict[str, Any]]  # {regla, detalle, afectados}
    metricas: dict[str, Any]  # métricas "antes"
    especifico: dict[str, Any]  # sección específica del tipo (provisional)
    avisos: list[str] = field(default_factory=list)  # mensajes claros para la UI
    estadistica: dict[str, Any] = field(default_factory=dict)  # medidas estadísticas "antes"


@dataclass
class ResultadoFinal:
    """Salida de aplicar las decisiones: lo que se guarda y se muestra."""

    encabezados: list[str]
    filas: list[list[str]]
    metricas: dict[str, Any]  # métricas "después"
    especifico: dict[str, Any]  # sección específica del tipo (definitiva)
    transformaciones: list[dict[str, Any]]  # transformaciones derivadas de decisiones
    cifras: list[dict[str, Any]]  # 3–4 cifras clave para la vista final {etiqueta, valor}
    vista: dict[str, Any]  # {"forma": "tabla"|"turnos", "columnas": [...], "filas": [...]}
    estadistica: dict[str, Any] = field(default_factory=dict)  # medidas estadísticas "después"


class Motor(Protocol):
    """Interfaz de un motor de limpieza."""

    nombre: str

    def automatica(self, entrada: Entrada) -> ResultadoAutomatico: ...

    def aplicar(
        self, entrada: Entrada, automatico: ResultadoAutomatico, decisiones: dict[str, str]
    ) -> ResultadoFinal: ...
