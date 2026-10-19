import logging

from change_ci.discovery import build_pairs, discover_rasters


def test_discovery_and_consecutive_pairs(tmp_path, caplog, analysis_config_factory):
    area = tmp_path / "Area"
    area.mkdir()
    for year in (2023, 2024):
        (area / f"Area_{year}-09.tif").touch()
    (area / "not_a_raster_name.tif").touch()
    config = analysis_config_factory(
        tmp_path, tmp_path / "out", months=("09",), year_range=(2023, 2024)
    )
    with caplog.at_level(logging.WARNING):
        records = discover_rasters(tmp_path)
    pairs = build_pairs(records, config)
    assert len(records) == 2
    assert len(pairs) == 1
    assert pairs[0].year_start == 2023
    assert "unexpected name" in caplog.text


def test_missing_pair_is_logged(tmp_path, caplog, analysis_config_factory):
    area = tmp_path / "Area"
    area.mkdir()
    (area / "Area_2023-09.tif").touch()
    config = analysis_config_factory(
        tmp_path, tmp_path / "out", months=("09",), year_range=(2023, 2024)
    )
    with caplog.at_level(logging.WARNING):
        pairs = build_pairs(discover_rasters(tmp_path), config)
    assert pairs == []
    assert "Skipping missing pair" in caplog.text
