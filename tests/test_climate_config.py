from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
import yaml

from cds_pull.config import ClimateConfig

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "climate.yaml"


def test_climate_config_loads_canonical_yaml():
    config = ClimateConfig.from_yaml(CONFIG_PATH, project_root=ROOT)

    assert config.sites_source == ROOT / "sites" / "StudySites.gpkg"
    assert config.id_field == "site_name"
    assert config.output_dir == ROOT / "outputs" / "climate"
    assert config.dataset == "reanalysis-era5-land-timeseries"
    assert config.variables == ("2m_temperature", "total_precipitation")
    assert config.region_lat == (31.2, 32.0)
    assert config.region_lon == (34.2, 34.8)
    assert config.site_cell_overrides == {"HolotPalmahim": "N31.9_E34.8", "NahalRubin": "N31.9_E34.8"}
    assert config.extraction_range == (date(1990, 10, 1), date(2025, 12, 31))
    assert config.reference_period == (1991, 2020)
    assert config.study_years == (2019, 2025)
    assert config.study_months == (2, 5, 9, 11)
    assert config.wet_season_months == (10, 4)
    assert config.near_zero_normal_mm == 10
    assert config.min_reference_periods == 30
    assert config.daily_temp_range_c == (-5, 45)
    assert config.daily_precip_cap_mm == 200
    assert len(config.reference_years) == 30
    assert config.to_dict()["extraction_range"] == ["1990-10-01", "2025-12-31"]


@pytest.mark.parametrize("change", ["missing", "unexpected"])
def test_climate_config_rejects_bad_keys(tmp_path, change):
    data = yaml.safe_load(CONFIG_PATH.read_text())
    if change == "missing":
        del data["near_zero_normal_mm"]
    else:
        data["unexpected"] = 1
    path = tmp_path / "climate.yaml"
    path.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match=f"{change}"):
        ClimateConfig.from_yaml(path, project_root=ROOT)


def test_climate_config_requires_october_before_reference_period():
    config = ClimateConfig.from_yaml(CONFIG_PATH, project_root=ROOT)

    with pytest.raises(ValueError, match="start on or before 1990-10-01"):
        replace(config, extraction_range=(date(1991, 1, 1), date(2025, 12, 31)))


def test_climate_config_rejects_season_start_as_study_month():
    config = ClimateConfig.from_yaml(CONFIG_PATH, project_root=ROOT)

    with pytest.raises(ValueError, match="season start month"):
        replace(config, study_months=(2, 10))


def test_climate_config_validates_region_and_overrides():
    config = ClimateConfig.from_yaml(CONFIG_PATH, project_root=ROOT)

    with pytest.raises(ValueError, match="0.1 degree grid"):
        replace(config, region_lat=(31.25, 32.0))
    with pytest.raises(ValueError, match="increasing"):
        replace(config, region_lon=(34.8, 34.2))
    with pytest.raises(ValueError, match="Invalid cell ID"):
        replace(config, site_cell_overrides={"A": "31.9,34.8"})
