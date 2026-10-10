"""
chart_generator.py
Generates per-instrument distribution plots and a summary correlation heatmap.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

PALETTE = {
    "P1": "#2196F3", "P2": "#4CAF50", "P3": "#F44336",
    "P4": "#FF9800", "P5": "#9C27B0", "P6": "#00BCD4",
    "P7": "#3F51B5", "P8": "#E91E63",
}


def _get_likert_cols(df: pd.DataFrame) -> list[str]:
    """Select numeric columns that are likely Likert items."""
    skip = {"edad", "semestre", "promedio_gpa", "horas_trabajo_semana", "score_estimado"}
    return [c for c in df.select_dtypes(include=[np.number]).columns
            if c.lower() not in skip and "id" not in c.lower()]


def generate_encuesta_chart(csv_path: Path, out_path: Path, title: str) -> None:
    """Box plots per Likert item colored by profile."""
    df = pd.read_csv(csv_path, encoding="utf-8")
    likert_cols = _get_likert_cols(df)

    if not likert_cols:
        print(f"    Skipping chart (no Likert cols): {csv_path.name}")
        return

    # Limit columns for readability
    cols_to_plot = likert_cols[:20]

    has_profile = "perfil" in df.columns
    fig, ax = plt.subplots(figsize=(max(12, len(cols_to_plot) * 0.6), 6))
    fig.patch.set_facecolor("#FAFAFA")

    if has_profile:
        profiles_present = sorted(df["perfil"].unique())
        positions = np.arange(len(cols_to_plot))

        for i, col in enumerate(cols_to_plot):
            col_data = []
            col_colors = []
            for pid in profiles_present:
                subset = df[df["perfil"] == pid][col].dropna().values
                if len(subset) > 0:
                    col_data.append(subset)
                    col_colors.append(PALETTE.get(pid, "#999999"))

            bp = ax.boxplot(
                col_data,
                positions=[i + j * 0.12 - 0.3 for j in range(len(col_data))],
                widths=0.1,
                patch_artist=True,
                showfliers=False,
            )
            for patch, color in zip(bp["boxes"], col_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.75)

        ax.set_xticks(range(len(cols_to_plot)))
        ax.set_xticklabels([c.split("_item")[0][:12] for c in cols_to_plot], rotation=45, ha="right", fontsize=8)

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=PALETTE.get(p, "#999"), label=p) for p in profiles_present]
        ax.legend(handles=legend_elements, loc="upper right", fontsize=8, title="Perfil")
    else:
        data_to_plot = [df[col].dropna().values for col in cols_to_plot]
        ax.boxplot(data_to_plot, showfliers=False, patch_artist=True)
        ax.set_xticks(range(1, len(cols_to_plot) + 1))
        ax.set_xticklabels([c[:12] for c in cols_to_plot], rotation=45, ha="right", fontsize=8)

    ax.set_ylabel("Puntuación Likert (1-5)", fontsize=10)
    ax.set_title(f"{title}\nDistribución de ítems por perfil estudiantil", fontsize=11, pad=10)
    ax.set_ylim(0.5, 5.5)
    ax.yaxis.grid(True, alpha=0.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_prueba_chart(csv_path: Path, out_path: Path, title: str) -> None:
    """Score distribution histogram by profile."""
    df = pd.read_csv(csv_path, encoding="utf-8")

    if "score_estimado" not in df.columns:
        print(f"    Skipping chart (no score_estimado): {csv_path.name}")
        return

    has_profile = "perfil" in df.columns
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#FAFAFA")

    # Overall distribution
    ax = axes[0]
    scores = df["score_estimado"].dropna() * 100
    ax.hist(scores, bins=20, color="#3F51B5", alpha=0.75, edgecolor="white")
    ax.axvline(scores.mean(), color="red", linestyle="--", label=f"Media={scores.mean():.1f}%")
    ax.set_xlabel("Score estimado (%)", fontsize=10)
    ax.set_ylabel("Frecuencia", fontsize=10)
    ax.set_title("Distribución general de puntuaciones", fontsize=10)
    ax.legend(fontsize=9)
    ax.xaxis.grid(True, alpha=0.3)

    # By profile
    ax2 = axes[1]
    if has_profile:
        profiles = sorted(df["perfil"].unique())
        profile_means = []
        profile_labels = []
        profile_stds = []
        colors_list = []

        for pid in profiles:
            subset = df[df["perfil"] == pid]["score_estimado"].dropna() * 100
            if len(subset) > 0:
                profile_means.append(subset.mean())
                profile_stds.append(subset.std())
                profile_labels.append(pid)
                colors_list.append(PALETTE.get(pid, "#999"))

        x = np.arange(len(profile_labels))
        bars = ax2.bar(x, profile_means, yerr=profile_stds, color=colors_list,
                       alpha=0.8, capsize=4, error_kw={"elinewidth": 1.5})
        ax2.set_xticks(x)
        ax2.set_xticklabels(profile_labels, fontsize=9)
        ax2.set_ylabel("Score promedio (%)", fontsize=10)
        ax2.set_title("Score promedio por perfil estudiantil", fontsize=10)
        ax2.set_ylim(0, 105)
        ax2.yaxis.grid(True, alpha=0.3)
        ax2.axhline(70, color="orange", linestyle="--", alpha=0.6, label="Umbral 70%")
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "Sin datos de perfil", ha="center", va="center")

    fig.suptitle(f"{title}", fontsize=12, y=1.01)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_entrevista_chart(txt_path: Path, out_path: Path, title: str) -> None:
    """Word frequency chart for interview text responses."""
    try:
        with open(txt_path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception:
        return

    # Extract response lines (lines starting with "R: ")
    response_lines = [line[3:] for line in text.split("\n") if line.startswith("R: ")]
    combined = " ".join(response_lines).lower()

    # Remove common stopwords
    stopwords = {
        "de", "la", "el", "en", "y", "a", "los", "las", "que", "es", "un", "una",
        "con", "por", "para", "su", "sus", "se", "me", "mi", "lo", "le", "si",
        "al", "del", "hay", "no", "más", "muy", "pero", "también", "han", "he",
        "the", "is", "and", "in", "to", "a", "i", "my", "of", "it", "was",
        "have", "that", "this", "are", "been", "from", "has", "had",
        "so", "be", "can", "not", "but", "or", "as", "at", "an",
    }

    words = re.findall(r"\b[a-záéíóúüñ]{4,}\b", combined)
    words = [w for w in words if w not in stopwords]

    if not words:
        return

    from collections import Counter
    freq = Counter(words)
    top_20 = freq.most_common(20)
    if not top_20:
        return

    labels, counts = zip(*top_20)

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#FAFAFA")
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(labels)))
    bars = ax.barh(list(labels), list(counts), color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Frecuencia", fontsize=10)
    ax.set_title(f"{title}\nFrecuencia de palabras más comunes en respuestas", fontsize=11)
    ax.xaxis.grid(True, alpha=0.4)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_summary_heatmap(base_dir: Path, out_path: Path) -> None:
    """Correlation heatmap of survey item mean scores."""
    all_means = {}

    enc_dir = base_dir / "encuestas"
    if not enc_dir.exists():
        return

    for csv_f in sorted(enc_dir.glob("*_respondido.csv")):
        df = pd.read_csv(csv_f, encoding="utf-8")
        likert_cols = _get_likert_cols(df)
        if likert_cols:
            means = df[likert_cols].mean()
            prefix = csv_f.stem.replace("_respondido", "")
            all_means[prefix] = means

    if not all_means:
        return

    # Build matrix of mean scores per instrument
    inst_names = list(all_means.keys())
    n = len(inst_names)

    # Compute correlation between instruments using item means
    # Truncate to common minimum length
    min_len = min(len(v) for v in all_means.values())
    matrix = np.array([v.values[:min_len] for v in all_means.values()])

    corr = np.corrcoef(matrix)

    fig, ax = plt.subplots(figsize=(max(8, n), max(6, n - 2)))
    fig.patch.set_facecolor("#FAFAFA")

    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, ax=ax,
        annot=True, fmt=".2f", cmap="RdYlGn",
        xticklabels=inst_names, yticklabels=inst_names,
        vmin=-1, vmax=1, center=0,
        linewidths=0.5, cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Mapa de correlación entre encuestas\n(basado en medias de ítems por instrumento)", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ resumen_general.png guardado")


def generate_all_charts(base_dir: Path) -> None:
    """Generate all charts for all instruments."""
    graficas_dir = base_dir / "graficas"
    graficas_dir.mkdir(parents=True, exist_ok=True)

    # Encuestas
    enc_dir = base_dir / "encuestas"
    if enc_dir.exists():
        print("\n  Generando gráficas de encuestas...")
        for csv_f in sorted(enc_dir.glob("*_respondido.csv")):
            inst_id = csv_f.stem.replace("_respondido", "")
            meta_f = enc_dir / f"{inst_id}_metadata.json"
            title = inst_id
            if meta_f.exists():
                with open(meta_f, encoding="utf-8") as fh:
                    title = json.load(fh).get("titulo", inst_id)
            out_p = graficas_dir / f"{inst_id}_distribucion.png"
            generate_encuesta_chart(csv_f, out_p, title)
            print(f"    ✓ {inst_id}_distribucion.png")

    # Entrevistas
    ent_dir = base_dir / "entrevistas"
    if ent_dir.exists():
        print("\n  Generando gráficas de entrevistas...")
        for txt_f in sorted(ent_dir.glob("*_respondido.txt")):
            inst_id = txt_f.stem.replace("_respondido", "")
            meta_f = ent_dir / f"{inst_id}_metadata.json"
            title = inst_id
            if meta_f.exists():
                with open(meta_f, encoding="utf-8") as fh:
                    title = json.load(fh).get("titulo", inst_id)
            out_p = graficas_dir / f"{inst_id}_distribucion.png"
            generate_entrevista_chart(txt_f, out_p, title)
            print(f"    ✓ {inst_id}_distribucion.png")

    # Pruebas
    pru_dir = base_dir / "pruebas"
    if pru_dir.exists():
        print("\n  Generando gráficas de pruebas...")
        for csv_f in sorted(pru_dir.glob("*_respondido.csv")):
            inst_id = csv_f.stem.replace("_respondido", "")
            meta_f = pru_dir / f"{inst_id}_metadata.json"
            title = inst_id
            if meta_f.exists():
                with open(meta_f, encoding="utf-8") as fh:
                    title = json.load(fh).get("titulo", inst_id)
            out_p = graficas_dir / f"{inst_id}_distribucion.png"
            generate_prueba_chart(csv_f, out_p, title)
            print(f"    ✓ {inst_id}_distribucion.png")

    # Summary heatmap
    print("\n  Generando mapa de correlación general...")
    generate_summary_heatmap(base_dir, graficas_dir / "resumen_general.png")


if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent.parent.parent
    base_dir = repo_root / "storage" / "instrumentos_sinteticos"
    generate_all_charts(base_dir)
