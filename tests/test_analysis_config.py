from pathlib import Path

from change_ci.config import AnalysisConfig


def test_analysis_config_loads_canonical_yaml():
    root = Path(__file__).resolve().parents[1]
    config = AnalysisConfig.from_yaml(
        root / "configs" / "change_ci.yaml", project_root=root
    )

    assert config.data_root == root / "outputs" / "composites"
    assert config.output_dir == root / "outputs" / "change_ci"
    assert config.study_areas is None
    assert config.months == ("01", "05", "09", "11")
    assert config.year_range == (2019, 2025)
    assert config.index_bands == ("NDVI", "GNDVI", "SAVI", "NDRE")
    assert config.engine == "fft"
    assert config.tau == 0.05
    assert config.tau_sensitivity == (0.02, 0.05, 0.1)
    assert config.alpha == 0.05
    assert config.max_lag_fraction == 0.25
    assert config.min_n_eff == 30
