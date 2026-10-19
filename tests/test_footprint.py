import numpy as np
import rasterio
from shapely.geometry import Point, Polygon

from s2grab import AOI
from s2grab import client as client_mod
from s2grab.client import S2Client
from s2grab.footprint import FOOTPRINT_RULE, TAG_PIXELS, TAG_RULE

# A triangle in UTM 36N (Gaza area) whose edges cut through pixels diagonally.
X0, Y0 = 350_000.0, 3_475_000.0
TRIANGLE = Polygon([(X0, Y0), (X0 + 400, Y0), (X0, Y0 + 300)])


def _aoi() -> AOI:
    return AOI.from_geometry(TRIANGLE, crs=32636, resolution=10)


def test_footprint_is_pixel_center_rule():
    aoi = _aoi()
    height, width = aoi.shape
    transform = aoi.transform
    expected = np.zeros((height, width), dtype=bool)
    for row in range(height):
        for col in range(width):
            x, y = transform * (col + 0.5, row + 0.5)
            expected[row, col] = TRIANGLE.contains(Point(x, y))
    np.testing.assert_array_equal(aoi.footprint, expected)
    assert 0 < aoi.footprint.sum() < height * width


def test_footprint_area_close_to_polygon_area():
    aoi = _aoi()
    pixel_area = abs(aoi.transform.a * aoi.transform.e)
    assert abs(aoi.footprint.sum() * pixel_area - TRIANGLE.area) / TRIANGLE.area < 0.05


def test_bbox_aoi_has_full_footprint():
    aoi = AOI.from_bounds(34.40, 31.40, 34.41, 31.41)
    assert not aoi.has_polygon
    assert aoi.footprint.all()


def _client_with_fake_fetch(monkeypatch, array):
    captured = {}

    def fake_fetch_array(**kwargs):
        captured.update(kwargs)
        return array

    monkeypatch.setattr(client_mod.fetch_mod, "fetch_array", fake_fetch_array)
    return S2Client(config=object()), captured


def test_fetch_applies_footprint_once(monkeypatch, tmp_path):
    aoi = _aoi()
    raw = np.ones(aoi.shape + (2,), dtype="float32")
    raw[0, -1, :] = np.nan  # an "interior" gap if inside, ignored if outside
    client, captured = _client_with_fake_fetch(monkeypatch, raw)

    image = client.fetch(aoi, start="2024-05-01", end="2024-05-31", product="ndvi")

    assert captured["aoi"] is aoi
    finite = np.isfinite(image.array).all(axis=2)
    assert not (finite & ~aoi.footprint).any()
    np.testing.assert_array_equal(finite, aoi.footprint & np.isfinite(raw).all(axis=2))

    path = image.save(tmp_path / "out.tif", tags={"MASK_SCL": "0,1"})
    with rasterio.open(path) as src:
        tags = src.tags()
        data = src.read(1)
        assert src.transform == aoi.transform
    assert tags[TAG_RULE] == FOOTPRINT_RULE
    assert int(tags[TAG_PIXELS]) == int(aoi.footprint.sum())
    assert tags["MASK_SCL"] == "0,1"
    assert int(np.isfinite(data).sum()) == int(finite.sum())
