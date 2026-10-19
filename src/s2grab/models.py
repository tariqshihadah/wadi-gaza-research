"""Rich result objects — the Pythonic layer over the functional core.

These wrap the plain data returned by the functional modules (a DataFrame from
``search``, a numpy array from ``fetch``) in small, discoverable objects with
natural ``len()`` / iteration / ``repr`` behaviour and convenience methods.

They deliberately hold no credentials or network logic — that lives in
:class:`s2grab.client.S2Client`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Sequence, Union

import numpy as np
import pandas as pd

from .aoi import AOI
from .footprint import FOOTPRINT_RULE, TAG_PIXELS, TAG_RULE
from .io import write_geotiff


@dataclass(frozen=True)
class Scene:
    """A single Sentinel-2 acquisition intersecting an AOI."""

    id: str
    datetime: str
    date: str
    cloud_cover: Union[float, None]

    def __repr__(self) -> str:
        cc = f"{self.cloud_cover:.1f}%" if self.cloud_cover is not None else "n/a"
        return f"Scene(date={self.date}, cloud={cc})"


class SceneList:
    """An ordered collection of :class:`Scene`, backed by a DataFrame.

    Supports ``len()``, iteration, and indexing (int -> Scene, slice ->
    SceneList) so it feels like a normal Python sequence, while ``to_dataframe``
    exposes the tabular form researchers expect.
    """

    def __init__(self, df: pd.DataFrame):
        self._df = df.reset_index(drop=True)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "SceneList":
        return cls(df)

    def to_dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    @property
    def dates(self) -> list[str]:
        return list(self._df["date"])

    def cleanest(self) -> Scene:
        """Return the least-cloudy scene."""
        if self._df.empty:
            raise ValueError("SceneList is empty; no cleanest scene.")
        idx = self._df["cloud_cover"].astype(float).idxmin()
        return self._row_to_scene(self._df.loc[idx])

    def __len__(self) -> int:
        return len(self._df)

    def __iter__(self) -> Iterator[Scene]:
        for _, row in self._df.iterrows():
            yield self._row_to_scene(row)

    def __getitem__(self, key) -> Union[Scene, "SceneList"]:
        if isinstance(key, slice):
            return SceneList(self._df.iloc[key])
        return self._row_to_scene(self._df.iloc[key])

    @staticmethod
    def _row_to_scene(row: pd.Series) -> Scene:
        return Scene(
            id=row["id"],
            datetime=row["datetime"],
            date=row["date"],
            cloud_cover=row["cloud_cover"],
        )

    def __repr__(self) -> str:
        n = len(self._df)
        if n == 0:
            return "SceneList(0 scenes)"
        return (
            f"SceneList({n} scenes, "
            f"{self._df['date'].iloc[0]} … {self._df['date'].iloc[-1]})"
        )


@dataclass
class Image:
    """A fetched raster: the pixel array plus its geospatial context."""

    array: np.ndarray  # (H, W, bands)
    aoi: AOI
    band_names: Union[Sequence[str], None] = None
    product: Union[str, None] = None

    @property
    def shape(self) -> tuple[int, ...]:
        return self.array.shape

    def save(
        self,
        path: Union[str, Path],
        tags: Union[Mapping[str, object], None] = None,
    ) -> Path:
        """Write to a georeferenced GeoTIFF and return the path.

        The study-area footprint rule and pixel count are always written as
        dataset tags; ``tags`` adds any further provenance metadata.
        """
        all_tags = {
            TAG_RULE: FOOTPRINT_RULE if self.aoi.has_polygon else "bbox",
            TAG_PIXELS: int(self.aoi.footprint.sum()),
            **(tags or {}),
        }
        return write_geotiff(
            path,
            self.array,
            self.aoi.bbox,
            band_names=self.band_names,
            tags=all_tags,
            transform=self.aoi.transform,
        )

    def __repr__(self) -> str:
        return (
            f"Image(product={self.product}, shape={self.array.shape}, "
            f"EPSG:{self.aoi.epsg})"
        )
