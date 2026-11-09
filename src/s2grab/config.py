"""Canonical defaults for the Sentinel-2 acquisition workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml

T = TypeVar("T")


@dataclass(frozen=True)
class AcquisitionConfig:
    """Validated acquisition settings loaded from the project YAML file."""

    years: tuple[int, ...]
    months: tuple[int, ...]
    bands: tuple[str, ...]
    indices: tuple[str, ...]
    savi_l: float
    resolution: int
    upsampling: str
    max_cloud: int
    mask_scl: tuple[int, ...]
    compute_std: bool
    sites_source: Path
    id_field: str
    output_dir: Path
    demo_month: int
    demo_output_dir: Path

    @classmethod
    def from_yaml(
        cls, path: Path, *, project_root: Path
    ) -> AcquisitionConfig:
        """Load settings from YAML, resolving relative paths from project_root."""
        data = _read_mapping(path)
        expected = {
            "years",
            "months",
            "bands",
            "indices",
            "savi_l",
            "resolution",
            "upsampling",
            "max_cloud",
            "mask_scl",
            "compute_std",
            "sites_source",
            "id_field",
            "output_dir",
            "demo_month",
            "demo_output_dir",
        }
        _validate_keys(data, expected, path)

        config = cls(
            years=_tuple(data["years"], "years", int),
            months=_tuple(data["months"], "months", int),
            bands=_tuple(data["bands"], "bands", str),
            indices=_tuple(data["indices"], "indices", str),
            savi_l=_number(data["savi_l"], "savi_l"),
            resolution=_integer(data["resolution"], "resolution"),
            upsampling=_string(data["upsampling"], "upsampling"),
            max_cloud=_integer(data["max_cloud"], "max_cloud"),
            mask_scl=_tuple(data["mask_scl"], "mask_scl", int),
            compute_std=_boolean(data["compute_std"], "compute_std"),
            sites_source=_resolve_path(
                data["sites_source"], project_root, "sites_source"
            ),
            id_field=_string(data["id_field"], "id_field"),
            output_dir=_resolve_path(data["output_dir"], project_root, "output_dir"),
            demo_month=_integer(data["demo_month"], "demo_month"),
            demo_output_dir=_resolve_path(
                data["demo_output_dir"], project_root, "demo_output_dir"
            ),
        )
        if not config.years:
            raise ValueError("years must not be empty")
        if not config.months or any(not 1 <= month <= 12 for month in config.months):
            raise ValueError("months must contain calendar months from 1 to 12")
        if not 1 <= config.demo_month <= 12:
            raise ValueError("demo_month must be a calendar month from 1 to 12")
        if not 0 <= config.max_cloud <= 100:
            raise ValueError("max_cloud must be between 0 and 100")
        if not 0 <= config.savi_l <= 1:
            raise ValueError("savi_l must be between 0 and 1")
        return config


def _read_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {path}")
    return data


def _validate_keys(data: dict[str, Any], expected: set[str], path: Path) -> None:
    missing = expected.difference(data)
    extra = data.keys() - expected
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing keys: {sorted(missing)}")
        if extra:
            details.append(f"unexpected keys: {sorted(extra)}")
        raise ValueError(f"Invalid acquisition configuration in {path}: " + "; ".join(details))


def _tuple(data: Any, name: str, item_type: type[T]) -> tuple[T, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{name} must be a YAML sequence")
    if any(not isinstance(item, item_type) or isinstance(item, bool) for item in data):
        raise ValueError(f"{name} contains an invalid value")
    return tuple(data)


def _integer(data: Any, name: str) -> int:
    if not isinstance(data, int) or isinstance(data, bool):
        raise ValueError(f"{name} must be an integer")
    return data


def _number(data: Any, name: str) -> float:
    if not isinstance(data, (int, float)) or isinstance(data, bool):
        raise ValueError(f"{name} must be a number")
    return float(data)


def _string(data: Any, name: str) -> str:
    if not isinstance(data, str):
        raise ValueError(f"{name} must be a string")
    return data


def _boolean(data: Any, name: str) -> bool:
    if not isinstance(data, bool):
        raise ValueError(f"{name} must be a boolean")
    return data


def _resolve_path(data: Any, project_root: Path, name: str) -> Path:
    path = Path(_string(data, name))
    return path if path.is_absolute() else project_root / path
