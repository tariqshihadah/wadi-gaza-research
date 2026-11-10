from dataclasses import replace
from pathlib import Path

import pytest

from change_did.config import DidAnalysisConfig


def _load():
    root = Path(__file__).resolve().parents[1]
    return DidAnalysisConfig.from_yaml(
        root / "configs" / "change_did.yaml", project_root=root
    )


def test_did_config_loads_canonical_yaml():
    root = Path(__file__).resolve().parents[1]
    config = _load()

    assert config.input_paths == tuple(
        root / "outputs" / "change_ci" / index / "results.csv"
        for index in ("NDVI", "GNDVI", "SAVI", "NDRE")
    )
    assert config.output_dir == root / "outputs" / "change_did"
    assert config.indices == ("NDVI", "GNDVI", "SAVI", "NDRE")
    assert config.primary_index == "NDVI"
    assert config.months == (1, 5, 9, 11)
    assert config.supplementary_months == (1,)
    assert config.affected_site == "WadiGaza"
    assert config.event_pairs == ((2023, 2024), (2024, 2025))
    assert config.models == ("site_period", "period_only")
    assert config.tau == 0.05
    assert config.tau_sensitivity == (0.02, 0.05, 0.1)
    assert config.alpha == 0.05
    assert config.fill_n_eff == 5
    assert config.expected_flagged_primary == 22


def test_did_config_roles_and_supplementary_flags():
    config = _load()

    assert config.role("NDVI") == "primary"
    assert config.role("SAVI") == "robustness"
    assert config.is_supplementary(1)
    assert not config.is_supplementary(5)


def test_did_config_model_site_effects():
    config = _load()

    assert config.model_site_effects("site_period")
    assert not config.model_site_effects("period_only")


@pytest.mark.parametrize(
    "overrides",
    [
        {"primary_index": "EVI"},
        {"supplementary_months": (2,)},
        {"event_pairs": ((2023, 2025), (2024, 2025))},
        {"event_pairs": ((2023, 2024), (2023, 2024))},
        {"models": ()},
        {"models": ("site_period", "site_period")},
        {"models": ("site_only",)},
        {"tau": 0.07},
        {"alpha": 1.5},
        {"fill_n_eff": 0},
        {"indices": ("NDVI", "NDVI")},
    ],
)
def test_did_config_rejects_invalid_values(overrides):
    config = _load()
    with pytest.raises(ValueError):
        replace(config, **overrides)
