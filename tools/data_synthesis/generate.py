"""
generate.py — Motor de datos sintéticos Indagata
=================================================

CLI de generación de instrumentos de investigación sintéticos.

Uso:
  python generate.py --all                         # Genera todos los instrumentos
  python generate.py --tipo encuesta --n 3         # Genera 3 encuestas más
  python generate.py --tipo entrevista             # Genera todas las entrevistas
  python generate.py --tipo prueba                 # Genera todas las pruebas
  python generate.py --charts-only                 # Solo genera gráficas
  python generate.py --quality-only                # Solo corre validación de calidad
  python generate.py --seed 42 --all               # Generación reproducible

El sistema lee los metadatos existentes para continuar la numeración
y puede calibrar nuevos instrumentos con los ya generados.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Resolve project root (2 levels up from this file)
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = REPO_ROOT / "storage" / "instrumentos_sinteticos"

# Add generators to path
sys.path.insert(0, str(SCRIPT_DIR))

from generators.encuesta_generator import EncuestaGenerator
from generators.entrevista_generator import EntrevistaGenerator
from generators.prueba_generator import PruebaGenerator


def run_generation(
    tipo: str | None,
    n: int | None,
    seed: int,
    output_dir: Path,
) -> None:
    """Run the generation pipeline."""
    print(f"\n{'='*60}")
    print("  INDAGATA — Motor de Datos Sintéticos v1.0")
    print(f"  Salida: {output_dir}")
    print(f"  Semilla aleatoria: {seed}")
    print(f"{'='*60}\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()

    # --- Encuestas ---
    if tipo is None or tipo == "encuesta":
        print("📋 Generando ENCUESTAS...")
        gen = EncuestaGenerator(output_dir=output_dir, seed=seed)
        if n is not None:
            ids = gen.generate_n_more(n)
        else:
            ids = gen.generate_all()
        print(f"  → {len(ids)} encuesta(s) generada(s): {', '.join(ids)}\n")

    # --- Entrevistas ---
    if tipo is None or tipo == "entrevista":
        print("🎙  Generando ENTREVISTAS...")
        gen = EntrevistaGenerator(output_dir=output_dir, seed=seed + 100)
        if n is not None:
            all_ids = list(__import__("generators.entrevista_generator", fromlist=["INTERVIEW_DEFS"]).INTERVIEW_DEFS.keys())
            existing = gen.read_existing_metadata(output_dir / "entrevistas", "ent")
            to_gen = all_ids[len(existing): len(existing) + n]
            ids = gen.generate_all(to_gen)
        else:
            ids = gen.generate_all()
        print(f"  → {len(ids)} entrevista(s) generada(s): {', '.join(ids)}\n")

    # --- Pruebas ---
    if tipo is None or tipo == "prueba":
        print("📝 Generando PRUEBAS ESTANDARIZADAS...")
        gen = PruebaGenerator(output_dir=output_dir, seed=seed + 200)
        if n is not None:
            all_ids = list(__import__("generators.prueba_generator", fromlist=["TEST_DEFS"]).TEST_DEFS.keys())
            existing = gen.read_existing_metadata(output_dir / "pruebas", "pru")
            to_gen = all_ids[len(existing): len(existing) + n]
            ids = gen.generate_all(to_gen)
        else:
            ids = gen.generate_all()
        print(f"  → {len(ids)} prueba(s) generada(s): {', '.join(ids)}\n")

    elapsed = time.time() - t0
    print(f"✅ Generación completada en {elapsed:.1f}s")


def run_charts(output_dir: Path) -> None:
    """Generate all charts."""
    from visualization.chart_generator import generate_all_charts
    print("\n📊 Generando visualizaciones...")
    generate_all_charts(output_dir)


def run_quality(output_dir: Path) -> None:
    """Run quality checks."""
    from quality.checker import run_all_checks
    run_all_checks(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor de datos sintéticos — Indagata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--all", action="store_true",
        help="Genera todos los instrumentos (encuestas + entrevistas + pruebas)"
    )
    parser.add_argument(
        "--tipo", choices=["encuesta", "entrevista", "prueba"],
        help="Tipo de instrumento a generar"
    )
    parser.add_argument(
        "--n", type=int, default=None,
        help="Número de instrumentos a generar (adicionales a los ya existentes)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Semilla para reproducibilidad (default: 42)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help=f"Directorio de salida (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--charts-only", action="store_true",
        help="Solo genera gráficas (requiere datos ya generados)"
    )
    parser.add_argument(
        "--quality-only", action="store_true",
        help="Solo corre validación de calidad"
    )
    parser.add_argument(
        "--no-charts", action="store_true",
        help="Omite la generación de gráficas"
    )
    parser.add_argument(
        "--no-quality", action="store_true",
        help="Omite la validación de calidad"
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    # Charts only
    if args.charts_only:
        run_charts(output_dir)
        return

    # Quality only
    if args.quality_only:
        run_quality(output_dir)
        return

    # Determine what to generate
    if args.all:
        tipo = None  # all types
    elif args.tipo:
        tipo = args.tipo
    else:
        parser.print_help()
        print("\n⚠  Especifica --all o --tipo <tipo>")
        sys.exit(1)

    run_generation(
        tipo=tipo,
        n=args.n,
        seed=args.seed,
        output_dir=output_dir,
    )

    # Post-generation charts
    if not args.no_charts:
        run_charts(output_dir)

    # Post-generation quality
    if not args.no_quality:
        run_quality(output_dir)


if __name__ == "__main__":
    main()
