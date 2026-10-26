"""ERA5-Land 0.1 degree grid cells and the assignment of study sites to them.

Each site uses the cell containing its polygon centroid unless the
configuration names a different cell for it (``site_cell_overrides``).
"""

from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box
from shapely.validation import make_valid

GRID_STEP_DEG = 0.1
EARTH_RADIUS_KM = 6371.0088

SITE_CELL_COLUMNS = [
    "site",
    "centroid_lat",
    "centroid_lon",
    "centroid_cell_id",
    "cell_id",
    "cell_lat",
    "cell_lon",
    "distance_km",
    "assignment",
    "shared_with",
]


def predict_cell(lat: float, lon: float) -> tuple[float, float]:
    """Return the ERA5-Land grid point nearest to a WGS84 location.

    Grid points sit on multiples of 0.1 degrees, so cell edges are at +/-0.05.
    Points exactly on an edge are assigned to the cell to the north or east.
    """
    return _snap(lat), _snap(lon)


def cell_id(cell_lat: float, cell_lon: float) -> str:
    """Return a cell identifier such as ``N31.5_E34.4`` from its center."""
    ns = "N" if cell_lat >= 0 else "S"
    ew = "E" if cell_lon >= 0 else "W"
    return f"{ns}{abs(cell_lat):.1f}_{ew}{abs(cell_lon):.1f}"


def parse_cell_id(value: str) -> tuple[float, float]:
    """Return the (latitude, longitude) centre encoded in a cell ID."""
    lat_part, lon_part = value.split("_")
    lat = float(lat_part[1:]) * (1 if lat_part[0] == "N" else -1)
    lon = float(lon_part[1:]) * (1 if lon_part[0] == "E" else -1)
    return lat, lon


def grid_cells(lat_range: tuple[float, float], lon_range: tuple[float, float]) -> pd.DataFrame:
    """Return every grid point in an inclusive latitude and longitude range."""
    lats = _grid(*lat_range)
    lons = _grid(*lon_range)
    rows = [(cell_id(lat, lon), lat, lon) for lat in lats for lon in lons]
    return pd.DataFrame(rows, columns=["cell_id", "cell_lat", "cell_lon"])


def cell_box(cell_lat: float, cell_lon: float):
    """Return the 0.1 degree cell polygon centered on a grid point (EPSG:4326)."""
    half = GRID_STEP_DEG / 2
    return box(cell_lon - half, cell_lat - half, cell_lon + half, cell_lat + half)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two WGS84 points in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def load_sites(path: Path, id_field: str) -> gpd.GeoDataFrame:
    """Read site polygons and repair invalid geometry with ``make_valid``."""
    sites = gpd.read_file(path)
    if sites.crs is None:
        raise ValueError(f"Site source has no CRS: {path}")
    if id_field not in sites.columns:
        raise ValueError(f"Site source has no '{id_field}' column: {path}")
    if sites[id_field].duplicated().any():
        raise ValueError(f"Site identifiers in '{id_field}' must be unique")
    invalid = ~sites.geometry.is_valid
    if invalid.any():
        sites.loc[invalid, "geometry"] = sites.loc[invalid, "geometry"].apply(make_valid)
    return sites


def assign_cells(
    sites: gpd.GeoDataFrame, id_field: str, overrides: dict[str, str] | None = None
) -> pd.DataFrame:
    """Assign each site to the cell containing its centroid, or to an override.

    Centroids are computed in the sites' projected CRS and then transformed to
    WGS84. ``assignment`` is ``"centroid"`` or ``"manual"``. Returns one row
    per site with the columns in ``SITE_CELL_COLUMNS``.
    """
    if sites.crs is None or not sites.crs.is_projected:
        raise ValueError("Sites must be in a projected CRS to compute centroids")
    overrides = overrides or {}
    unknown = set(overrides) - set(sites[id_field].astype(str))
    if unknown:
        raise ValueError(f"Overrides name unknown sites: {sorted(unknown)}")
    centroids = gpd.GeoSeries(sites.geometry.centroid, crs=sites.crs).to_crs(4326)

    rows = []
    for site, point in zip(sites[id_field].astype(str), centroids):
        lat, lon = point.y, point.x
        centroid_cell = cell_id(*predict_cell(lat, lon))
        assigned = overrides.get(site, centroid_cell)
        cell_lat, cell_lon = parse_cell_id(assigned)
        rows.append(
            {
                "site": site,
                "centroid_lat": lat,
                "centroid_lon": lon,
                "centroid_cell_id": centroid_cell,
                "cell_id": assigned,
                "cell_lat": cell_lat,
                "cell_lon": cell_lon,
                "distance_km": haversine_km(lat, lon, cell_lat, cell_lon),
                "assignment": "manual" if site in overrides else "centroid",
            }
        )
    table = pd.DataFrame(rows)
    table["shared_with"] = [
        ";".join(sorted(table.loc[(table["cell_id"] == cid) & (table["site"] != s), "site"]))
        for s, cid in zip(table["site"], table["cell_id"])
    ]
    return table[SITE_CELL_COLUMNS]


def cells_geodataframe(cells: pd.DataFrame) -> gpd.GeoDataFrame:
    """Return one 0.1 degree box feature per cell (EPSG:4326).

    ``cells`` needs ``cell_id``, ``cell_lat`` and ``cell_lon``; other columns
    are kept from the first row of each cell.
    """
    cells = (
        cells.drop_duplicates("cell_id")
        .sort_values("cell_id")
        .reset_index(drop=True)
    )
    geometry = [cell_box(lat, lon) for lat, lon in zip(cells["cell_lat"], cells["cell_lon"])]
    return gpd.GeoDataFrame(cells, geometry=geometry, crs="EPSG:4326")


def write_cells_gpkg(cells: pd.DataFrame, path: Path) -> Path:
    """Write the cell reference layer to a GeoPackage and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cells_geodataframe(cells).to_file(path, layer="era5land_cells", driver="GPKG")
    return path


def _grid(low: float, high: float) -> list[float]:
    count = int(round((high - low) / GRID_STEP_DEG))
    return [round(low + i * GRID_STEP_DEG, 1) for i in range(count + 1)]


def _snap(value: float) -> float:
    # Round half up on the 0.1 grid, then round again to remove float noise.
    return round(math.floor(value / GRID_STEP_DEG + 0.5) * GRID_STEP_DEG, 1)
