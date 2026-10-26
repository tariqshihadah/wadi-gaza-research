from pathlib import Path

from cds_pull.config import ClimateConfig
from cds_pull.download import build_request

ROOT = Path(__file__).resolve().parents[1]


def test_build_request_uses_form_parameter_names():
    config = ClimateConfig.from_yaml(ROOT / "configs" / "climate.yaml", project_root=ROOT)

    request = build_request(31.5, 34.4, config)

    assert request == {
        "variable": ["2m_temperature", "total_precipitation"],
        "location": {"latitude": 31.5, "longitude": 34.4},
        "date": ["1990-10-01/2026-01-01"],
        "data_format": "csv",
    }
