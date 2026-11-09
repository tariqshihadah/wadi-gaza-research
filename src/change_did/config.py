"""Configuration for the weighted fixed-effects model on index change."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DidAnalysisConfig:
    """Validated fixed-effects model settings loaded from the project YAML file."""

    input_paths: tuple[Path, ...]
    output_dir: Path
    indices: tuple[str, ...]
    primary_index: str
    months: tuple[int, ...]
    supplementary_months: tuple[int, ...]
    affected_site: str
    event_pairs: tuple[tuple[int, int], tuple[int, int]]
    tau: float
    tau_sensitivity: tuple[float, ...]
    alpha: float
    fill_n_eff: float
    expected_flagged_primary: int | None

    @classmethod
    def from_yaml(cls, path: Path, *, project_root: Path) -> DidAnalysisConfig:
        """Load settings from YAML, resolving relative paths from project_root."""
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        if not isinstance(data, dict):
            raise ValueError(f"Configuration must be a YAML mapping: {path}")
        expected = {
            "input_paths",
            "output_dir",
            "indices",
            "primary_index",
            "months",
            "supplementary_months",
            "affected_site",
            "event_pairs",
            "tau",
            "tau_sensitivity",
            "alpha",
            "fill_n_eff",
            "expected_flagged_primary",
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

        input_paths = data["input_paths"]
        if not isinstance(input_paths, list) or not input_paths or not all(
            isinstance(entry, str) for entry in input_paths
        ):
            raise ValueError("input_paths must be a non-empty sequence of path strings")

        indices = data["indices"]
        if not isinstance(indices, list) or not all(
            isinstance(index, str) and index for index in indices
        ):
            raise ValueError("indices must be a sequence of non-empty strings")

        months = _int_sequence(data["months"], "months")
        supplementary_months = _int_sequence(
            data["supplementary_months"], "supplementary_months"
        )

        event_pairs = data["event_pairs"]
        if (
            not isinstance(event_pairs, list)
            or len(event_pairs) != 2
            or not all(
                isinstance(pair, list)
                and len(pair) == 2
                and all(isinstance(year, int) and not isinstance(year, bool) for year in pair)
                for pair in event_pairs
            )
        ):
            raise ValueError("event_pairs must be two [year_start, year_end] pairs")

        sensitivity = data["tau_sensitivity"]
        if not isinstance(sensitivity, list) or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in sensitivity
        ):
            raise ValueError("tau_sensitivity must be a sequence of numbers")

        expected_flagged = data["expected_flagged_primary"]
        if expected_flagged is not None and (
            not isinstance(expected_flagged, int) or isinstance(expected_flagged, bool)
        ):
            raise ValueError("expected_flagged_primary must be null or an integer")

        return cls(
            input_paths=tuple(
                resolve_path(entry, "input_paths") for entry in input_paths
            ),
            output_dir=resolve_path(data["output_dir"], "output_dir"),
            indices=tuple(indices),
            primary_index=_string(data["primary_index"], "primary_index"),
            months=months,
            supplementary_months=supplementary_months,
            affected_site=_string(data["affected_site"], "affected_site"),
            event_pairs=(
                (event_pairs[0][0], event_pairs[0][1]),
                (event_pairs[1][0], event_pairs[1][1]),
            ),
            tau=_number(data["tau"], "tau"),
            tau_sensitivity=tuple(float(value) for value in sensitivity),
            alpha=_number(data["alpha"], "alpha"),
            fill_n_eff=_number(data["fill_n_eff"], "fill_n_eff"),
            expected_flagged_primary=expected_flagged,
        )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.indices or len(set(self.indices)) != len(self.indices):
            raise ValueError("indices must be non-empty and contain no duplicates")
        if self.primary_index not in self.indices:
            raise ValueError("primary_index must be included in indices")
        if not self.months or len(set(self.months)) != len(self.months):
            raise ValueError("months must be non-empty and contain no duplicates")
        if not set(self.supplementary_months) <= set(self.months):
            raise ValueError("supplementary_months must be a subset of months")
        for year_start, year_end in self.event_pairs:
            if year_end != year_start + 1:
                raise ValueError("event_pairs must be consecutive-year pairs")
        if self.event_pairs[0] == self.event_pairs[1]:
            raise ValueError("event_pairs must be two distinct pairs")
        if self.tau not in self.tau_sensitivity:
            raise ValueError("tau must be included in tau_sensitivity")
        if not 0 < self.alpha < 1:
            raise ValueError("alpha must be between 0 and 1")
        if self.fill_n_eff <= 0:
            raise ValueError("fill_n_eff must be positive")

    def role(self, index: str) -> str:
        """Return the reporting role for an index."""
        return "primary" if index == self.primary_index else "robustness"

    def is_supplementary(self, month: int) -> bool:
        """Return whether a month is reported as supplementary."""
        return month in self.supplementary_months

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable configuration mapping."""
        values = asdict(self)
        values["input_paths"] = [str(path) for path in self.input_paths]
        values["output_dir"] = str(self.output_dir)
        values["event_pairs"] = [list(pair) for pair in self.event_pairs]
        return values


def _int_sequence(data: Any, name: str) -> tuple[int, ...]:
    if not isinstance(data, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) for value in data
    ):
        raise ValueError(f"{name} must be a sequence of integers")
    return tuple(data)


def _string(data: Any, name: str) -> str:
    if not isinstance(data, str):
        raise ValueError(f"{name} must be a string")
    return data


def _number(data: Any, name: str) -> float:
    if not isinstance(data, (int, float)) or isinstance(data, bool):
        raise ValueError(f"{name} must be a number")
    return data
