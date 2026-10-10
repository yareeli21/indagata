"""
base_generator.py
Shared utilities: profile sampling, beta distributions, correlation structure,
demographic generation, and outlier injection.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import beta as beta_dist


# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------
_CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_profiles() -> dict:
    with open(_CONFIG_DIR / "perfiles_estudiantes.json", encoding="utf-8") as fh:
        return json.load(fh)


def load_kpi_mapping() -> dict:
    with open(_CONFIG_DIR / "kpi_mapping.json", encoding="utf-8") as fh:
        return json.load(fh)


class BaseGenerator:
    """Shared functionality for all instrument generators."""

    def __init__(self, seed: int | None = None):
        config = load_profiles()
        self.profiles: list[dict] = config["perfiles"]
        self.correlation_config: dict = config["estructura_correlacion"]
        self.special_patterns: dict = config["patrones_respuesta_especiales"]
        self.kpi_mapping: dict = load_kpi_mapping()
        self.rng = np.random.default_rng(seed)
        random.seed(seed)

    # ------------------------------------------------------------------
    # Profile sampling
    # ------------------------------------------------------------------
    def sample_profile(self, allowed_profiles: list[str] | None = None) -> dict:
        """Sample one profile according to weight distribution."""
        profiles = self.profiles
        if allowed_profiles:
            profiles = [p for p in profiles if p["id"] in allowed_profiles]
        weights = np.array([p["peso"] for p in profiles], dtype=float)
        weights /= weights.sum()
        idx = self.rng.choice(len(profiles), p=weights)
        return profiles[idx]

    # ------------------------------------------------------------------
    # Beta distribution helpers
    # ------------------------------------------------------------------
    def beta_to_scale(self, alpha: float, beta: float, scale_min: int, scale_max: int, n: int) -> np.ndarray:
        """Generate n values from beta(alpha,beta) mapped to [scale_min, scale_max]."""
        raw = self.rng.beta(alpha, beta, n)
        scaled = raw * (scale_max - scale_min) + scale_min
        return scaled

    def generate_likert_item(self, profile: dict, n: int = 1, item_type: str = "normal") -> np.ndarray:
        """Generate Likert responses for a single item given a profile."""
        lk = profile["likert"]
        a, b = lk["alpha"], lk["beta"]
        raw = self.beta_to_scale(a, b, 1, 5, n)

        # Burnout profile: separate motivation/performance items
        if profile.get("patron_respuesta") == "mixto_burnout" and item_type == "motivacion":
            raw = self.beta_to_scale(2, 4, 1, 5, n)
        elif profile.get("patron_respuesta") == "mixto_burnout" and item_type == "rendimiento":
            raw = self.beta_to_scale(5, 2, 1, 5, n)

        # Flatten for ceiling-effect profiles
        if profile.get("patron_respuesta") == "techo":
            raw = np.clip(raw, 3.5, 5.0)

        return np.clip(np.round(raw), 1, 5).astype(int)

    # ------------------------------------------------------------------
    # Correlated item block generation
    # ------------------------------------------------------------------
    def generate_correlated_block(
        self,
        profile: dict,
        n_items: int,
        n_respondents: int,
        item_types: list[str] | None = None,
    ) -> np.ndarray:
        """
        Generate (n_respondents x n_items) Likert matrix with intra-block
        correlation structure matching the profile.
        """
        r_intra_min = self.correlation_config["intra_dimension"]["min"]
        r_intra_max = self.correlation_config["intra_dimension"]["max"]
        r_intra = self.rng.uniform(r_intra_min, r_intra_max)

        # Build correlation matrix: rho on off-diagonals
        corr_matrix = np.full((n_items, n_items), r_intra)
        np.fill_diagonal(corr_matrix, 1.0)

        # Cholesky decomposition for correlated normals
        try:
            L = np.linalg.cholesky(corr_matrix)
        except np.linalg.LinAlgError:
            # Fallback: perturb slightly
            corr_matrix = corr_matrix + 0.05 * np.eye(n_items)
            L = np.linalg.cholesky(corr_matrix)

        lk = profile["likert"]
        mean_val = lk["media_estimada"]
        std_val = lk["desviacion_estimada"]

        # Generate standard normals and correlate
        Z = self.rng.standard_normal((n_respondents, n_items))
        correlated_Z = Z @ L.T

        # Scale to Likert range
        raw = correlated_Z * std_val + mean_val
        responses = np.clip(np.round(raw), 1, 5).astype(int)

        # Inject special response patterns
        responses = self._inject_special_patterns(responses, n_respondents, n_items)

        return responses

    def _inject_special_patterns(
        self, responses: np.ndarray, n_resp: int, n_items: int
    ) -> np.ndarray:
        """Inject acquiescence, rejection, and zigzag patterns."""
        sp = self.special_patterns
        n_acquiescence = int(n_resp * sp["aquiescencia"]["probabilidad"])
        n_rejection = int(n_resp * sp["rechazo"]["probabilidad"])
        n_zigzag = int(n_resp * sp["zigzag"]["probabilidad"])

        indices = list(range(n_resp))
        self.rng.shuffle(np.array(indices))

        selected = set()
        # Acquiescence: all high values
        for i in range(min(n_acquiescence, len(indices))):
            idx = indices[i]
            selected.add(idx)
            responses[idx] = self.rng.integers(4, 6, n_items)

        # Rejection: all low values
        for i in range(n_acquiescence, min(n_acquiescence + n_rejection, len(indices))):
            idx = indices[i]
            selected.add(idx)
            responses[idx] = self.rng.integers(1, 3, n_items)

        # Zigzag: alternating high/low
        start = n_acquiescence + n_rejection
        for i in range(start, min(start + n_zigzag, len(indices))):
            idx = indices[i]
            if idx not in selected:
                for j in range(n_items):
                    responses[idx, j] = 5 if j % 2 == 0 else 1

        return responses

    # ------------------------------------------------------------------
    # Multi-dimension Likert generation
    # ------------------------------------------------------------------
    def generate_instrument_responses(
        self,
        profile: dict,
        dimensions: list[dict],  # [{"name": ..., "n_items": ..., "item_type": "normal"}]
        n_respondents: int,
    ) -> np.ndarray:
        """
        Generate a full response matrix for a multi-dimension instrument.
        Cross-dimension correlation is lower than intra-dimension.
        """
        r_cross_min = self.correlation_config["inter_dimension"]["min"]
        r_cross_max = self.correlation_config["inter_dimension"]["max"]

        all_blocks = []
        for dim in dimensions:
            block = self.generate_correlated_block(
                profile,
                dim["n_items"],
                n_respondents,
                item_types=[dim.get("item_type", "normal")] * dim["n_items"],
            )
            all_blocks.append(block)

        if len(all_blocks) == 1:
            return all_blocks[0]

        # Combine blocks with cross-correlation noise
        full_matrix = np.hstack(all_blocks)

        # Add cross-dimension correlation via shared noise
        r_cross = self.rng.uniform(r_cross_min, r_cross_max)
        n_total_items = full_matrix.shape[1]
        shared_noise = self.rng.standard_normal((n_respondents, 1))
        cross_adjustment = (shared_noise * r_cross * 0.5).astype(int)
        full_matrix = full_matrix + cross_adjustment
        full_matrix = np.clip(full_matrix, 1, 5)

        return full_matrix

    # ------------------------------------------------------------------
    # Demographic generation
    # ------------------------------------------------------------------
    def generate_demographics(self, profile: dict, n: int) -> list[dict]:
        """Generate coherent demographic data for n respondents matching profile."""
        demographics = []
        edad_min, edad_max = profile["edad_rango"]
        sem_min, sem_max = profile.get("semestre_rango", [1, 10])
        trabajo_min, trabajo_max = profile.get("horas_trabajo_rango", [0, 20])
        gpa_min, gpa_max = profile.get("gpa_rango", [2.0, 4.0])

        genero_dist = profile.get("genero_dist", {"masculino": 0.5, "femenino": 0.45, "otro": 0.05})
        genero_opts = list(genero_dist.keys())
        genero_weights = [genero_dist[g] for g in genero_opts]

        tipo_uni = profile.get("tipo_universidad", "publica")
        nivel_ses = profile.get("nivel_ses", "medio")
        nivel_estudio = profile.get("nivel_estudio", "pregrado")

        for i in range(n):
            edad = int(self.rng.integers(edad_min, edad_max + 1))
            semestre = int(self.rng.integers(sem_min, sem_max + 1))
            horas_trabajo = int(self.rng.integers(trabajo_min, trabajo_max + 1))
            gpa = round(float(self.rng.uniform(gpa_min, gpa_max)), 2)
            genero = self.rng.choice(genero_opts, p=genero_weights)

            demographics.append({
                "id_respondente": f"R{i+1:04d}",
                "perfil": profile["id"],
                "edad": edad,
                "genero": str(genero),
                "semestre": semestre,
                "promedio_gpa": gpa,
                "horas_trabajo_semana": horas_trabajo,
                "tipo_universidad": tipo_uni,
                "nivel_ses": nivel_ses,
                "nivel_estudio": nivel_estudio,
                "primera_generacion": profile.get("es_primera_generacion", False),
                "tiene_beca": profile.get("tiene_beca", False),
            })

        return demographics

    # ------------------------------------------------------------------
    # Outlier respondent detection helper
    # ------------------------------------------------------------------
    @staticmethod
    def detect_outliers(matrix: np.ndarray, z_threshold: float = 3.0) -> np.ndarray:
        """Return boolean mask of outlier respondents (row-wise z-score)."""
        row_means = matrix.mean(axis=1)
        z = np.abs((row_means - row_means.mean()) / (row_means.std() + 1e-10))
        return z > z_threshold

    # ------------------------------------------------------------------
    # Cronbach alpha estimation
    # ------------------------------------------------------------------
    @staticmethod
    def cronbach_alpha(matrix: np.ndarray) -> float:
        """Estimate Cronbach's alpha for a response matrix (respondents x items)."""
        n_items = matrix.shape[1]
        if n_items < 2:
            return float("nan")
        item_variances = matrix.var(axis=0, ddof=1)
        total_variance = matrix.sum(axis=1).var(ddof=1)
        if total_variance == 0:
            return 0.0
        alpha = (n_items / (n_items - 1)) * (1 - item_variances.sum() / total_variance)
        return float(np.clip(alpha, 0, 1))

    # ------------------------------------------------------------------
    # Utility: read existing metadata to continue numbering
    # ------------------------------------------------------------------
    @staticmethod
    def read_existing_metadata(output_dir: Path, tipo: str) -> list[dict]:
        """Read all existing metadata.json files for a given tipo."""
        pattern = f"{tipo[:3]}_*_metadata.json"
        existing = []
        for f in sorted(output_dir.glob(pattern)):
            with open(f, encoding="utf-8") as fh:
                existing.append(json.load(fh))
        return existing
