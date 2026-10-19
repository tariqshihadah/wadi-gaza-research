from s2grab.config import AcquisitionConfig


def test_acquisition_config_contains_current_study_defaults():
    config = AcquisitionConfig()

    assert config.months == (1, 5, 9, 11)
    assert config.years == tuple(range(2019, 2026))
    assert config.bands == ("B02", "B03", "B04", "B05", "B08", "B8A", "B11", "B12")
    assert config.indices == ("NDVI", "GNDVI", "SAVI", "NDRE")
    assert config.resolution == 10
    assert config.upsampling == "NEAREST"
    assert config.max_cloud == 20
    assert config.mask_scl == (0, 1, 2, 3, 7, 8, 9, 10, 11)
    assert config.compute_std is True
