"""Configuration for raster change confidence interval analyses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AnalysisConfig:
    """Explicit configuration for one analysis run."""

    data_root: Path
    output_dir: Path
    study_areas: tuple[str, ...] | None = None
    months: tuple[str, ...] = ("01", "05", "09", "11")
    year_range: tuple[int, int] = (2019, 2025)
    index_band: str = "NDVI"
    engine: str = "fft"
    tau: float = 0.05
    tau_sensitivity: tuple[float, ...] = (0.02, 0.05, 0.10)
    alpha: float = 0.05
    max_lag_fraction: float = 0.25
    min_n_eff: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.year_range[0] >= self.year_range[1]:
            raise ValueError("year_range must be an increasing inclusive range")
        if self.engine not in {"fft", "bruteforce", "pysal"}:
            raise ValueError(f"Unknown engine: {self.engine}")
        if self.tau not in self.tau_sensitivity:
            raise ValueError("tau must be included in tau_sensitivity")
        if not 0 < self.alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        if not 0 < self.max_lag_fraction <= 1:
            raise ValueError("max_lag_fraction must be in (0, 1]")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable configuration mapping."""
        values = asdict(self)
        values["data_root"] = str(self.data_root)
        values["output_dir"] = str(self.output_dir)
        return values