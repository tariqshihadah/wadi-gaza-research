"""Area of interest: turn geographic bounds or a polygon into a request geometry.

Sentinel-2 is delivered in UTM zones, and we want resolution expressed in metres,
so every AOI is reprojected to its local UTM zone before building a request.

An AOI carries a bounding box (always) and, optionally, a clip polygon. When a
polygon is present, the Process API clips output to that shape (pixels outside
come back masked). This module depends only on shapely + pyproj + sentinelhub —
no file IO, no geopandas — so it stays lean and easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from pyproj import CRS as PyprojCRS
from pyproj import Transformer
from sentinelhub import CRS, BBox, Geometry, bbox_to_dimensions
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

# Process API caps a single request at this many pixels per side.
MAX_DIM = 2500


def utm_epsg(lon: float, lat: float) -> int:
    """Return the EPSG code of the UTM zone containing a lon/lat point."""
    zone = int((lon + 180) / 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def _to_epsg(crs: Union[int, str, "PyprojCRS"]) -> int:
    """Normalise a variety of CRS inputs to an EPSG integer."""
    if isinstance(crs, int):
        return crs
    return int(PyprojCRS.from_user_input(crs).to_epsg())


@dataclass
class AOI:
    """A request-ready area of interest in a local UTM projection.

    Attributes
    ----------
    bbox: the UTM bounding box (carries CRS + extent), always present.
    size: (width, height) in pixels.
    resolution: effective ground resolution in metres.
    geometry: optional UTM clip polygon; when set, requests are masked to it.
    """

    bbox: BBox
    size: tuple[int, int]
    resolution: float
    geometry: Optional[Geometry] = None

    @property
    def epsg(self) -> int:
        return int(self.bbox.crs.value)

    @property
    def is_clipped(self) -> bool:
        return self.geometry is not None

    def __repr__(self) -> str:
        shape = "polygon" if self.is_clipped else "bbox"
        return (
            f"AOI(EPSG:{self.epsg}, {self.size[0]}x{self.size[1]}px, "
            f"{self.resolution:.1f}m, {shape})"
        )

    @classmethod
    def from_geometry(
        cls,
        geom: BaseGeometry,
        crs: Union[int, str, "PyprojCRS"],
        resolution: float = 10,
        clip: bool = True,
    ) -> "AOI":
        """Build an :class:`AOI` from an in-memory shapely geometry.

        Parameters
        ----------
        geom: any shapely geometry (Polygon, MultiPolygon, ...).
        crs: the geometry's CRS. Required because shapely geometries carry
            none. Accepts an EPSG int, an authority string ("EPSG:4326"), or a
            pyproj CRS.
        resolution: requested ground resolution in metres.
        clip: when True (default), keep the polygon so requests are masked to
            it. When False, only the bounding box is used (rectangular output).

        The geometry is reprojected to the local UTM zone of its centroid. If
        the requested resolution would exceed the Process API pixel cap, it is
        coarsened just enough to fit.
        """
        src_epsg = _to_epsg(crs)

        # Centroid in lon/lat to choose the UTM zone.
        if src_epsg == 4326:
            centroid = geom.centroid
            center_lon, center_lat = centroid.x, centroid.y
        else:
            to_wgs = Transformer.from_crs(src_epsg, 4326, always_xy=True).transform
            centroid = shapely_transform(to_wgs, geom).centroid
            center_lon, center_lat = centroid.x, centroid.y

        utm_epsg_code = utm_epsg(center_lon, center_lat)
        to_utm = Transformer.from_crs(src_epsg, utm_epsg_code, always_xy=True).transform
        geom_utm = shapely_transform(to_utm, geom)

        utm_crs = CRS(utm_epsg_code)
        utm_bbox = BBox(geom_utm.bounds, crs=utm_crs)

        eff_res = resolution
        size = bbox_to_dimensions(utm_bbox, resolution=eff_res)
        if max(size) > MAX_DIM:
            eff_res = resolution * (max(size) / MAX_DIM)
            size = bbox_to_dimensions(utm_bbox, resolution=eff_res)

        geometry = Geometry(geom_utm, crs=utm_crs) if clip else None
        return cls(bbox=utm_bbox, size=size, resolution=eff_res, geometry=geometry)

    @classmethod
    def from_bounds(
        cls,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        resolution: float = 10,
    ) -> "AOI":
        """Build a rectangular :class:`AOI` from WGS84 lon/lat bounds.

        Delegates to :meth:`from_geometry` with ``clip=False`` so output is the
        full bounding box.
        """
        return cls.from_geometry(
            box(min_lon, min_lat, max_lon, max_lat),
            crs=4326,
            resolution=resolution,
            clip=False,
        )


# Functional-style alias for the classmethod constructor.
def aoi_from_bounds(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    resolution: float = 10,
) -> AOI:
    """Functional wrapper around :meth:`AOI.from_bounds`."""
    return AOI.from_bounds(min_lon, min_lat, max_lon, max_lat, resolution=resolution)
