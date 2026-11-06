"""Califica en la terminal las respuestas de una corrida que no tienen calificación humana.

Uso (dentro del contenedor del chat; SIN -T, porque pide respuestas por teclado):
    docker compose exec visualization-service python scripts/modelos/calificar.py --corrida llama3.2:3b=1328

Recorre los turnos de la corrida en orden de caso (los mismos que toma `reporte.py`: si una pregunta se hizo dos
veces, la última) y, por cada uno sin calificar, muestra la pregunta, el turno anterior del caso y la respuesta; pide
la calificación (0 mal, 1 parcial, 2 bien), si entendió, si fundamentó y un comentario opcional. Se guarda en
`rag_calificacion`, igual que el panel del chat. `--todas` vuelve a pedir también las ya calificadas (Enter las deja
como estaban). Ctrl+C sale; lo ya guardado se queda.
"""
from __future__ import annotations

import argparse
import sys
import textwrap

import comun  # noqa: F401  (ajusta sys.path)
from comun import CASOS, emparejar, leer_casos, parsear_corrida

from shared.db.session import SessionLocal
from shared.models.rag_evaluacion import RagCalificacion
from shared.models.usuario import Usuario

_SI_NO = {"s": True, "si": True, "sí": True, "n": False, "no": False, "na": None, "x": None}


def _leer(texto: str) -> str:
    """Lee una línea sin caerse con acentos: la terminal de Windows puede mandarlos en cp1252/cp850, no en UTF-8."""
    print(texto, end="", flush=True)
    crudo = sys.stdin.buffer.readline()
    if not crudo:
        raise EOFError
    for codificacion in ("utf-8", "cp1252", "cp850"):
        try:
            return crudo.decode(codificacion).rstrip("\r\n")
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", errors="replace").rstrip("\r\n")


def _pedir(texto: str, validas: dict, previa=...):
    """Pide una opción hasta que sea válida; con Enter conserva `previa` (si la hay)."""
    while True:
        r = _leer(texto).strip().lower()
        if not r and previa is not ...:
            return previa
        if r in validas:
            return validas[r]
        print("   Opción no válida.")


def _bloque(etiqueta: str, texto: str | None) -> None:
    print(f"\n{etiqueta}")
    for parrafo in (texto or "(sin texto)").splitlines() or [""]:
        print(textwrap.fill(parrafo, 110, initial_indent="   ", subsequent_indent="   ") if parrafo.strip() else "")


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--corrida", required=True, help="modelo=INICIO-FIN (rag_log_id)")
    args.add_argument("--casos", default="casos.json", help="archivo de casos junto a este script (p. ej. casos_pru03.json)")
    args.add_argument("--todas", action="store_true", help="pide también las que ya tienen calificación")
    args.add_argument("--usuario", default="admin@indagata.com", help="correo de quien califica")
    a = args.parse_args()

    casos = leer_casos(CASOS.with_name(a.casos))
    sesion = SessionLocal()
    try:
        corrida = parsear_corrida(a.corrida)
        faltan = emparejar(sesion, corrida, casos)
        usuario = sesion.query(Usuario).filter_by(email=a.usuario).one_or_none()
        textos = {(c["caso"], i): t["texto"] for c in casos["casos"] for i, t in enumerate(c["turnos"], 1)}
        turnos = sorted(corrida.filas.items())
        por_calificar = [(k, f) for k, f in turnos if a.todas or sesion.get(RagCalificacion, f.rag_log_id) is None]
        print(f"{corrida.nombre}: {len(turnos)} turnos encontrados, {len(por_calificar)} por calificar"
              + (f"; faltan {len(faltan)} turnos (no se hicieron o el texto no coincide)" if faltan else "") + ".")
        for n, ((caso, turno), fila) in enumerate(por_calificar, 1):
            previa = sesion.get(RagCalificacion, fila.rag_log_id)
            print("\n" + "═" * 110 + f"\n[{n}/{len(por_calificar)}] Caso {caso}.{turno} · consulta {fila.rag_log_id}")
            if turno > 1:
                anterior = corrida.filas.get((caso, turno - 1))
                _bloque(f"Turno anterior ({caso}.{turno - 1}):", textos[(caso, turno - 1)]
                        + (f"\n→ {(anterior.respuesta or '')[:300]}…" if anterior is not None else ""))
            _bloque("Pregunta:", fila.pregunta)
            _bloque("Respuesta:", fila.respuesta)
            if previa is not None:
                print(f"\n   Ya calificada: {previa.calificacion} · entendió {previa.entendio} · "
                      f"fundamentó {previa.fundamenta} (Enter conserva cada valor)")
            print()
            cal = _pedir("Respuesta: 0 mal, 1 parcial, 2 bien → ", {"0": 0, "1": 1, "2": 2},
                         previa.calificacion if previa else ...)
            entendio = _pedir("¿Entendió lo que pediste? s/n → ", {k: v for k, v in _SI_NO.items() if v is not None},
                              previa.entendio if previa else ...)
            fundamenta = _pedir("¿Fundamentó? s/n/na (no aplica) → ", _SI_NO, previa.fundamenta if previa else ...)
            comentario = _leer("Comentario (opcional, Enter para omitir) → ").strip()
            fila_cal = previa or RagCalificacion(rag_log_id=fila.rag_log_id)
            fila_cal.calificacion, fila_cal.entendio, fila_cal.fundamenta = cal, entendio, fundamenta
            if comentario or previa is None:
                fila_cal.comentario = comentario or None
            fila_cal.usuario_id = usuario.usuario_id if usuario else None
            sesion.add(fila_cal)
            sesion.commit()
            print("   Guardada.")
        print("\nListo." if por_calificar else "\nNo había respuestas por calificar.")
    except (KeyboardInterrupt, EOFError):
        print("\n\nSalida; lo calificado hasta aquí quedó guardado.")
    finally:
        sesion.close()


if __name__ == "__main__":
    main()
