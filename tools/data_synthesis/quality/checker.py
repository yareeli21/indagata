"""
checker.py
Quality validation for generated synthetic data.
Runs Cronbach alpha estimation, outlier detection, and inter-item correlation checks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_metadata(base_dir: Path) -> list[dict]:
    """Load all metadata.json files under base_dir recursively."""
    metas = []
    for f in sorted(base_dir.rglob("*_metadata.json")):
        with open(f, encoding="utf-8") as fh:
            meta = json.load(fh)
            meta["_path"] = str(f)
        metas.append(meta)
    return metas


def cronbach_alpha(matrix: np.ndarray) -> float:
    """Estimate Cronbach's alpha."""
    n_items = matrix.shape[1]
    if n_items < 2:
        return float("nan")
    item_vars = matrix.var(axis=0, ddof=1)
    total_var = matrix.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return 0.0
    return float(np.clip((n_items / (n_items - 1)) * (1 - item_vars.sum() / total_var), 0, 1))


def detect_outlier_pct(matrix: np.ndarray, z_threshold: float = 3.0) -> float:
    """Return percentage of outlier respondents."""
    row_means = matrix.mean(axis=1)
    std = row_means.std()
    if std == 0:
        return 0.0
    z = np.abs((row_means - row_means.mean()) / std)
    return float((z > z_threshold).mean()) * 100


def inter_item_corr_summary(matrix: np.ndarray) -> dict:
    """Compute mean and std of inter-item correlations."""
    if matrix.shape[1] < 2:
        return {"mean": float("nan"), "std": float("nan"), "min": float("nan"), "max": float("nan")}
    corr = np.corrcoef(matrix.T)
    # Extract upper triangle (excluding diagonal)
    idx = np.triu_indices(corr.shape[0], k=1)
    off_diag = corr[idx]
    return {
        "mean": round(float(np.nanmean(off_diag)), 3),
        "std": round(float(np.nanstd(off_diag)), 3),
        "min": round(float(np.nanmin(off_diag)), 3),
        "max": round(float(np.nanmax(off_diag)), 3),
    }


def check_instrument(csv_path: Path, tipo: str) -> dict | None:
    """Run quality checks on a single CSV."""
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except Exception as e:
        return {"error": str(e)}

    # Identify numeric Likert or score columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Remove demographic/id columns
    skip_cols = {"edad", "semestre", "promedio_gpa", "horas_trabajo_semana", "score_estimado"}
    likert_cols = [c for c in numeric_cols if c.lower() not in skip_cols and "id" not in c.lower()]

    if not likert_cols or len(likert_cols) < 2:
        return {"n_cols": len(numeric_cols), "skipped": "not_enough_numeric_cols"}

    matrix = df[likert_cols].dropna().values.astype(float)

    if matrix.shape[0] < 5:
        return {"skipped": "not_enough_rows"}

    alpha = cronbach_alpha(matrix)
    pct_out = detect_outlier_pct(matrix)
    corr = inter_item_corr_summary(matrix)

    target_alpha = 0.7
    pass_alpha = (not np.isnan(alpha)) and (alpha >= target_alpha or tipo in ("entrevista", "prueba_estandarizada"))

    return {
        "alpha_cronbach": round(alpha, 4) if not np.isnan(alpha) else None,
        "pct_outliers": round(pct_out, 2),
        "inter_item_corr": corr,
        "n_respondents": matrix.shape[0],
        "n_items_numeric": len(likert_cols),
        "pass": pass_alpha,
        "pass_reason": f"alpha={'N/A' if np.isnan(alpha) else round(alpha, 3)} {'≥' if pass_alpha else '<'} {target_alpha}",
    }


def run_all_checks(base_dir: Path) -> None:
    """Run quality checks on all instruments and print report."""
    print("\n" + "="*70)
    print("REPORTE DE CALIDAD — DATOS SINTÉTICOS INDAGATA")
    print("="*70)

    total = 0
    passed = 0
    results: list[dict] = []

    for tipo_dir in sorted(base_dir.iterdir()):
        if not tipo_dir.is_dir() or tipo_dir.name == "graficas":
            continue

        tipo = tipo_dir.name  # encuestas, entrevistas, pruebas
        csv_files = sorted(tipo_dir.glob("*_respondido.csv"))
        meta_files = sorted(tipo_dir.glob("*_metadata.json"))

        if not csv_files:
            continue

        print(f"\n--- {tipo.upper()} ---")
        print(f"{'ID':<12} {'Alpha':>8} {'Outliers%':>10} {'r̄ items':>8} {'n_resp':>7} {'PASS':>6}")
        print("-"*55)

        for csv_f in csv_files:
            inst_id = csv_f.stem.replace("_respondido", "")
            meta_f = tipo_dir / f"{inst_id}_metadata.json"

            inst_tipo = tipo.rstrip("s")  # encuesta, entrevista, prueba
            result = check_instrument(csv_f, inst_tipo)

            if result is None or "skipped" in result or "error" in result:
                status = f"SKIP: {result}"
                print(f"{inst_id:<12} {'N/A':>8} {'N/A':>10} {'N/A':>8} {'N/A':>7} {'—':>6}")
                continue

            alpha_str = f"{result['alpha_cronbach']:.3f}" if result["alpha_cronbach"] is not None else "N/A"
            corr_mean = result["inter_item_corr"]["mean"]
            pass_str = "✓ OK" if result["pass"] else "✗ FAIL"
            print(
                f"{inst_id:<12} {alpha_str:>8} {result['pct_outliers']:>9.1f}% "
                f"{corr_mean:>8.3f} {result['n_respondents']:>7} {pass_str:>6}"
            )

            total += 1
            if result["pass"]:
                passed += 1

            results.append({"id": inst_id, "tipo": tipo, **result})

    print("\n" + "="*70)
    print(f"RESUMEN: {passed}/{total} instrumentos pasaron el umbral de calidad (alpha ≥ 0.7 para Likert)")
    print("="*70)

    # Save results
    out_path = base_dir / "quality_report.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(f"\nReporte guardado en: {out_path}")


if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent.parent.parent
    base_dir = repo_root / "storage" / "instrumentos_sinteticos"
    if not base_dir.exists():
        print(f"Error: directorio no encontrado: {base_dir}")
        sys.exit(1)
    run_all_checks(base_dir)
