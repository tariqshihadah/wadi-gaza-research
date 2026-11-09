from pathlib import Path

from s2grab.config import AcquisitionConfig


def test_acquisition_config_loads_current_study_settings():
    root = Path(__file__).resolve().parents[1]
    config = AcquisitionConfig.from_yaml(
        root / "configs" / "imagery.yaml", project_root=root
    )

    assert config.months == (1, 2, 3, 5, 9, 11)
    assert config.years == tuple(range(2019, 2026))
    assert config.bands == ("B02", "B03", "B04", "B05", "B08", "B8A", "B11", "B12")
    assert config.indices == ("NDVI", "GNDVI", "SAVI", "NDRE")
    assert config.savi_l == 0.5
    assert config.resolution == 10
    assert config.upsampling == "NEAREST"
    assert config.max_cloud == 20
    assert config.mask_scl == (0, 1, 2, 3, 7, 8, 9, 10, 11)
    assert config.compute_std is True
    assert config.sites_source == root / "sites" / "StudySites.gpkg"
    assert config.id_field == "site_name"
    assert config.output_dir == root / "outputs" / "composites"
    assert config.demo_month == 5
    assert config.demo_output_dir == root / "outputs" / "_demo_composites"
