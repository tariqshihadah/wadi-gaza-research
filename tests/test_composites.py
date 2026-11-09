from types import SimpleNamespace

import numpy as np

from s2grab.composites import composite_qa
from s2grab.evalscripts import INDEX_LIBRARY, savi


class FakeClient:
    def __init__(self, scenes, images):
        self.scenes = scenes
        self.images = iter(images)
        self.fetch_calls = []

    def search(self, aoi, start, end, max_cloud):
        return self.scenes

    def fetch(self, aoi, **kwargs):
        self.fetch_calls.append(kwargs)
        return next(self.images)


def test_composite_qa_calculates_metrics_and_fetches_optional_std():
    aoi = SimpleNamespace(
        footprint=np.array([[True, True], [True, False]]),
    )
    image = SimpleNamespace(
        array=np.array(
            [
                [[1.0, 2.0], [np.nan, np.nan]],
                [[3.0, 4.0], [np.nan, np.nan]],
            ]
        )
    )
    std_image = SimpleNamespace(
        array=np.array(
            [
                [[1.0, 3.0], [np.nan, np.nan]],
                [[3.0, 5.0], [np.nan, np.nan]],
            ]
        )
    )
    client = FakeClient(
        scenes=[
            SimpleNamespace(cloud_cover=10.0),
            SimpleNamespace(cloud_cover=20.0),
            SimpleNamespace(cloud_cover=None),
        ],
        images=[image, std_image],
    )

    result, qa = composite_qa(
        client,
        aoi,
        "2024-05-01",
        "2024-05-31",
        bands=("B04",),
        indices=("NDVI",),
        max_cloud=20,
        mask_scl=(0, 1),
        compute_std=True,
        upsampling="NEAREST",
        savi_l=0.5,
    )

    assert result is image
    assert qa == {
        "n_scenes": 3,
        "mean_cloud": 15.0,
        "pct_nodata": 100.0 / 3.0,
        "mean_pixel_std": 3.0,
    }
    assert len(client.fetch_calls) == 2


def test_composite_qa_returns_without_fetching_when_no_scenes():
    aoi = SimpleNamespace(footprint=np.ones((1, 1), dtype=bool))
    client = FakeClient(scenes=[], images=[])

    image, qa = composite_qa(
        client,
        aoi,
        "2024-05-01",
        "2024-05-31",
        bands=("B04",),
        indices=("NDVI",),
        max_cloud=20,
        mask_scl=(0, 1),
        compute_std=True,
    )

    assert image is None
    assert qa["n_scenes"] == 0
    assert np.isnan(qa["mean_cloud"])
    assert np.isnan(qa["pct_nodata"])
    assert np.isnan(qa["mean_pixel_std"])
    assert client.fetch_calls == []


def test_savi_factory_builds_expression_from_l():
    index = savi(0.5)
    assert index.expr == "((s.B08 - s.B04) / (s.B08 + s.B04 + 0.5)) * 1.5"
    assert INDEX_LIBRARY["SAVI"] == index


def test_composite_qa_forwards_savi_l_into_evalscript():
    aoi = SimpleNamespace(footprint=np.ones((1, 1), dtype=bool))
    image = SimpleNamespace(array=np.zeros((1, 1, 1)))
    client = FakeClient(scenes=[SimpleNamespace(cloud_cover=5.0)], images=[image])

    composite_qa(
        client,
        aoi,
        "2024-05-01",
        "2024-05-31",
        bands=(),
        indices=("SAVI",),
        max_cloud=20,
        mask_scl=(0, 1),
        compute_std=False,
        savi_l=0.75,
    )

    script = client.fetch_calls[0]["product"].script
    assert "s.B08 + s.B04 + 0.75" in script
    assert "* 1.75" in script
