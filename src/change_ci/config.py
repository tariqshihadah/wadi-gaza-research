"""Configuration for raster change confidence interval analyses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AnalysisConfig:
    """Validated change-analysis settings loaded from the project YAML file."""

    data_root: Path
    output_dir: Path
    study_areas: tuple[str, ...] | None
    months: tuple[str, ...]
    year_range: tuple[int, int]
    index_band: str
    engine: str
    tau: float
    tau_sensitivity: tuple[float, ...]
    alpha: float
    max_lag_fraction: float
    min_n_eff: float

    @classmethod
    def from_yaml(cls, path: Path, *, project_root: Path) -> AnalysisConfig:
        """Load settings from YAML, resolving relative paths from project_root."""
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        if not isinstance(data, dict):
            raise ValueError(f"Configuration must be a YAML mapping: {path}")
        expected = {
            "data_root",
            "output_dir",
            "study_areas",
            "months",
            "year_range",
            "index_band",
            "engine",
            "tau",
            "tau_sensitivity",
            "alpha",
            "max_lag_fraction",
            "min_n_eff",
        }
        missing = expected.difference(data)
        extra = data.keys() - expected
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing keys: {sorted(missing)}")
            if extra:
                details.append(f"unexpected keys: {sorted(extra)}")
            raise ValueError(f"Invalid analysis configuration in {path}: " + "; ".join(details))

        def resolve_path(value: Any, name: str) -> Path:
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a path string")
            path_value = Path(value)
            return path_value if path_value.is_absolute() else project_root / path_value

        study_areas = data["study_areas"]
        if study_areas is not None:
            if not isinstance(study_areas, list) or not all(
                isinstance(area, str) for area in study_areas
            ):
                raise ValueError("study_areas must be null or a sequence of strings")

        months = data["months"]
        if not isinstance(months, list) or not all(isinstance(m, str) for m in months):
            raise ValueError("months must be a sequence of strings")
        year_range = data["year_range"]
        if not isinstance(year_range, list) or len(year_range) != 2 or not all(
            isinstance(year, int) and not isinstance(year, bool) for year in year_range
        ):
            raise ValueError("year_range must contain two integers")
        sensitivity = data["tau_sensitivity"]
        if not isinstance(sensitivity, list) or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in sensitivity
        ):
            raise ValueError("tau_sensitivity must be a sequence of numbers")

        return cls(
            data_root=resolve_path(data["data_root"], "data_root"),
            output_dir=resolve_path(data["output_dir"], "output_dir"),
            study_areas=tuple(study_areas) if study_areas is not None else None,
            months=tuple(months),
            year_range=(year_range[0], year_range[1]),
            index_band=_string(data["index_band"], "index_band"),
            engine=_string(data["engine"], "engine"),
            tau=_number(data["tau"], "tau"),
            tau_sensitivity=tuple(float(value) for value in sensitivity),
            alpha=_number(data["alpha"], "alpha"),
            max_lag_fraction=_number(data["max_lag_fraction"], "max_lag_fraction"),
            min_n_eff=_number(data["min_n_eff"], "min_n_eff"),
        )

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


def _string(data: Any, name: str) -> str:
    if not isinstance(data, str):
        raise ValueError(f"{name} must be a string")
    return data


def _number(data: Any, name: str) -> float:
    if not isinstance(data, (int, float)) or isinstance(data, bool):
        raise ValueError(f"{name} must be a number")
    return data