"""Puerto de almacenamiento de archivos (la ENTRADA LIMPIA al storage-service).

Este microservicio NO decide ni ejecuta cómo/dónde se guardan los archivos: esa
responsabilidad es del **storage-service** (File I/O, storage ops). Aquí solo se
define el CONTRATO que el instrument-service le pide al almacenamiento:

    guardar(content, filename) -> StoredRef
    eliminar(ref)

Hoy existe una implementación local provisional (`local_backend.py`) porque el
storage-service aún no está construido. Cuando exista, se añade un backend que
llame a su API por HTTP y se cambia la fábrica en `__init__.py`. El resto del
servicio (upload/delete) no cambia: depende solo de este puerto, no del disco.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredRef:
    """Referencia a un archivo almacenado, devuelta por el almacenamiento.

    Es intencionalmente opaca para el instrument-service: lo que importa es
    `ruta` (lo que se persiste en `raw_data`), no dónde vive físicamente. Con el
    storage-service, `ruta` podría ser una key/URL en vez de una ruta de disco,
    sin que este servicio tenga que cambiar.

    Attributes:
        nombre_original: Nombre con el que el usuario subió el archivo.
        ruta:            Identificador/ruta que se guarda en `raw_data`
                         (raw_archivo / raw_archivo_original).
        size_bytes:      Tamaño del contenido almacenado.
    """

    nombre_original: str
    ruta: str
    size_bytes: int


class StoragePort(ABC):
    """Contrato de almacenamiento de archivos crudos.

    El instrument-service depende de esta abstracción, nunca de una
    implementación concreta. Así, delegar al storage-service en el futuro es
    cambiar la implementación, no la lógica de negocio.
    """

    @abstractmethod
    def guardar(self, content: bytes, nombre_original: str) -> StoredRef:
        """Almacena el contenido y devuelve su referencia.

        Raises:
            StorageError: si el almacenamiento falla.
        """

    @abstractmethod
    def eliminar(self, ruta: str) -> None:
        """Elimina un archivo por su referencia (idempotente: no falla si no existe)."""


class StorageError(Exception):
    """Fallo del almacenamiento (independiente del backend)."""
