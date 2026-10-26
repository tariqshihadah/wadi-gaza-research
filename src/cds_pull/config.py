"""Configuration for the ERA5-Land climate context pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_EXPECTED_KEYS = {
    "sites_source",
    "id_field",
    "output_dir",
    "dataset",
    "data_format",
    "variables",
    "extraction_range",
    "reference_period",
    "study_years",
    "study_months",
    "wet_season_months",
    "near_zero_normal_mm",
    "min_reference_periods",
    "daily_temp_range_c",
    "daily_precip_cap_mm",
}


@dataclass(frozen=True)
class ClimateConfig:
    """Validated climate-context settings loaded from the project YAML file.

    ``extraction_range`` holds the inclusive first and last UTC days of daily
    output. ``wet_season_months`` holds the first and last calendar months of
    the wet season (October and April by default).
    """

    sites_source: Path
    id_field: str
    output_dir: Path
    dataset: str
    data_format: str
    variables: tuple[str, ...]
    extraction_range: tuple[date, date]
    reference_period: tuple[int, int]
    study_years: tuple[int, int]
    study_months: tuple[int, ...]
    wet_season_months: tuple[int, int]
    near_zero_normal_mm: float
    min_reference_periods: int
    daily_temp_range_c: tuple[float, float]
    daily_precip_cap_mm: float

    @classmethod
    def from_yaml(cls, path: Path, *, project_root: Path) -> ClimateConfig:
        """Load settings from YAML, resolving relative paths from project_root."""
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        if not isinstance(data, dict):
            raise ValueError(f"Configuration must be a YAML mapping: {path}")
        missing = _EXPECTED_KEYS.difference(data)
        extra = data.keys() - _EXPECTED_KEYS
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing keys: {sorted(missing)}")
            if extra:
                details.append(f"unexpected keys: {sorted(extra)}")
            raise ValueError(f"Invalid climate configuration in {path}: " + "; ".join(details))

        def resolve_path(value: Any, name: str) -> Path:
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a path string")
            path_value = Path(value)
            return path_value if path_value.is_absolute() else project_root / path_value

        variables = data["variables"]
        if not isinstance(variables, list) or not all(
            isinstance(v, str) and v for v in variables
        ):
            raise ValueError("variables must be a sequence of non-empty strings")
        extraction = data["extraction_range"]
        if not isinstance(extraction, list) or len(extraction) != 2:
            raise ValueError("extraction_range must contain two ISO dates")

        return cls(
            sites_source=resolve_path(data["sites_source"], "sites_source"),
            id_field=_string(data["id_field"], "id_field"),
            output_dir=resolve_path(data["output_dir"], "output_dir"),
            dataset=_string(data["dataset"], "dataset"),
            data_format=_string(data["data_format"], "data_format"),
            variables=tuple(variables),
            extraction_range=(_date(extraction[0]), _date(extraction[1])),
            reference_period=_int_pair(data["reference_period"], "reference_period"),
            study_years=_int_pair(data["study_years"], "study_years"),
            study_months=_int_tuple(data["study_months"], "study_months"),
            wet_season_months=_int_pair(data["wet_season_months"], "wet_season_months"),
            near_zero_normal_mm=_number(data["near_zero_normal_mm"], "near_zero_normal_mm"),
            min_reference_periods=_int(data["min_reference_periods"], "min_reference_periods"),
            daily_temp_range_c=_number_pair(data["daily_temp_range_c"], "daily_temp_range_c"),
            daily_precip_cap_mm=_number(data["daily_precip_cap_mm"], "daily_precip_cap_mm"),
        )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        start, end = self.extraction_range
        if start > end:
            raise ValueError("extraction_range must be increasing")
        ref_first, ref_last = self.reference_period
        if ref_first > ref_last:
            raise ValueError("reference_period must be an increasing inclusive range")
        if self.study_years[0] > self.study_years[1]:
            raise ValueError("study_years must be an increasing inclusive range")
        if not self.study_months or len(set(self.study_months)) != len(self.study_months):
            raise ValueError("study_months must be non-empty and contain no duplicates")
        season_start, season_end = self.wet_season_months
        for month in (*self.study_months, season_start, season_end):
            if not 1 <= month <= 12:
                raise ValueError(f"Month out of range: {month}")
        if season_start <= season_end:
            raise ValueError("wet_season_months must span the new year (start > end)")
        if season_start in self.study_months:
            raise ValueError(
                "study_months cannot include the wet-season start month; the cumulative "
                "window before it would be empty"
            )
        if self.near_zero_normal_mm < 0 or self.daily_precip_cap_mm <= 0:
            raise ValueError("Precipitation thresholds must be positive")
        if self.min_reference_periods < 1:
            raise ValueError("min_reference_periods must be at least 1")
        if self.daily_temp_range_c[0] >= self.daily_temp_range_c[1]:
            raise ValueError("daily_temp_range_c must be increasing")

        # Accumulation windows reach back to the season start before the first
        # reference year and up to two years before the first study year.
        earliest_needed = date(min(ref_first - 1, self.study_years[0] - 2), season_start, 1)
        latest_needed = date(max(ref_last, self.study_years[1]), 12, 31)
        if start > earliest_needed:
            raise ValueError(
                f"extraction_range must start on or before {earliest_needed.isoformat()}"
            )
        if end < latest_needed:
            raise ValueError(f"extraction_range must end on or after {latest_needed.isoformat()}")

    @property
    def study_period_years(self) -> tuple[int, ...]:
        """Return every study year in the inclusive study range."""
        return tuple(range(self.study_years[0], self.study_years[1] + 1))

    @property
    def reference_years(self) -> tuple[int, ...]:
        """Return every year in the inclusive reference period."""
        return tuple(range(self.reference_period[0], self.reference_period[1] + 1))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable configuration mapping."""
        values = asdict(self)
        values["sites_source"] = str(self.sites_source)
        values["output_dir"] = str(self.output_dir)
        values["extraction_range"] = [d.isoformat() for d in self.extraction_range]
        return values


def _string(data: Any, name: str) -> str:
    if not isinstance(data, str) or not data:
        raise ValueError(f"{name} must be a non-empty string")
    return data


def _number(data: Any, name: str) -> float:
    if not isinstance(data, (int, float)) or isinstance(data, bool):
        raise ValueError(f"{name} must be a number")
    return data


def _int(data: Any, name: str) -> int:
    if not isinstance(data, int) or isinstance(data, bool):
        raise ValueError(f"{name} must be an integer")
    return data


def _int_tuple(data: Any, name: str) -> tuple[int, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{name} must be a sequence of integers")
    return tuple(_int(value, name) for value in data)


def _int_pair(data: Any, name: str) -> tuple[int, int]:
    values = _int_tuple(data, name)
    if len(values) != 2:
        raise ValueError(f"{name} must contain two integers")
    return values[0], values[1]


def _number_pair(data: Any, name: str) -> tuple[float, float]:
    if not isinstance(data, list) or len(data) != 2:
        raise ValueError(f"{name} must contain two numbers")
    return _number(data[0], name), _number(data[1], name)


def _date(data: Any) -> date:
    if isinstance(data, date):
        return data
    if not isinstance(data, str):
        raise ValueError("extraction_range values must be ISO date strings")
    return date.fromisoformat(data)
