#!/usr/bin/env python3
"""
fetch_sentinel2.py
==================
Automated retrieval of clipped, multi-band Sentinel-2 L2A rasters from the
Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Process API.

For every polygon in a shapefile and every date window in config.yaml, this
script finds qualifying (low-cloud) acquisitions and downloads a single
GeoTIFF per scene containing:

    Bands 1-10 : B02 B03 B04 B05 B06 B07 B08 B8A B11 B12  (surface reflectance, 0-1)
    Band  11   : NDVI   = (B08 - B04) / (B08 + B04)
    Band  12   : EVI    = 2.5*(B08 - B04) / (B08 + 6*B04 - 7.5*B02 + 1)
    Band  13   : NDWI   = (B03 - B08) / (B03 + B08)        (McFeeters, water)
    Band  14   : NDMI   = (B08 - B11) / (B08 + B11)        (moisture)
    Band  15   : SCL    = scene classification (integer class, 0-11)
    Band  16   : dataMask = 1 where valid data exists, else 0

Output is FLOAT32 so reflectance and indices keep physically meaningful values.

-------------------------------------------------------------------------------
SETUP (one time)
-------------------------------------------------------------------------------
1. Create a free account at https://dataspace.copernicus.eu and register an
   OAuth client (Dashboard -> User Settings -> OAuth clients -> Create).
2. Install dependencies:
       pip install "sentinelhub>=3.9" geopandas rasterio pyproj shapely numpy pyyaml
3. Provide credentials EITHER by saving a profile once in Python:
       from sentinelhub import SHConfig
       c = SHConfig()
       c.sh_client_id = "<id>"; c.sh_client_secret = "<secret>"
       c.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
       c.sh_base_url  = "https://sh.dataspace.copernicus.eu"
       c.save("cdse")
   ...OR by exporting environment variables before running:
       export SH_CLIENT_ID=...   SH_CLIENT_SECRET=...
4. Run:  python fetch_sentinel2.py            (uses config.yaml in same folder)
         python fetch_sentinel2.py other.yaml
-------------------------------------------------------------------------------
"""

import os
import sys
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
import yaml

load_dotenv()  # reads .env file (if present) into environment variables
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
from pyproj import Transformer

from sentinelhub import (
    SHConfig,
    DataCollection,
    SentinelHubCatalog,
    SentinelHubRequest,
    BBox,
    CRS,
    Geometry,
    MimeType,
    MosaickingOrder,
    bbox_to_dimensions,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("s2fetch")

# CDSE service endpoints (do not change for the public CDSE deployment).
SH_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SH_BASE_URL = "https://sh.dataspace.copernicus.eu"

# Output band order and names (also written into the GeoTIFF metadata).
BAND_NAMES = [
    "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12",
    "NDVI", "EVI", "NDWI", "NDMI", "SCL", "dataMask",
]

# Process API per-request dimension cap. Larger AOIs are coarsened (with a warning).
MAX_DIM = 2500

# The evalscript: requests the bands, computes the indices, returns 16 layers.
# index(a, b) is a Sentinel Hub built-in equal to (a - b) / (a + b).
EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B02","B03","B04","B05","B06","B07","B08","B8A","B11","B12","SCL","dataMask"],
      units: "REFLECTANCE"
    }],
    output: { bands: 16, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(s) {
  let ndvi = index(s.B08, s.B04);
  let ndwi = index(s.B03, s.B08);
  let ndmi = index(s.B08, s.B11);
  let denom = s.B08 + 6.0 * s.B04 - 7.5 * s.B02 + 1.0;
  let evi = denom !== 0.0 ? 2.5 * (s.B08 - s.B04) / denom : 0.0;
  return [
    s.B02, s.B03, s.B04, s.B05, s.B06, s.B07, s.B08, s.B8A, s.B11, s.B12,
    ndvi, evi, ndwi, ndmi, s.SCL, s.dataMask
  ];
}
"""


def load_config(path):
    with open(path, "r") as fh:
        cfg = yaml.safe_load(fh)
    cfg.setdefault("site_id_field", None)
    cfg.setdefault("resolution", 10)
    cfg.setdefault("max_cloud_cover", 30)
    cfg.setdefault("mode", "per_scene")
    return cfg


def make_config():
    """Build an SHConfig from a saved 'cdse' profile or environment variables."""
    config = SHConfig("cdse") if "cdse" in SHConfig.get_available_profiles() else SHConfig()
    if os.getenv("SH_CLIENT_ID"):
        config.sh_client_id = os.environ["SH_CLIENT_ID"]
    if os.getenv("SH_CLIENT_SECRET"):
        config.sh_client_secret = os.environ["SH_CLIENT_SECRET"]
    config.sh_token_url = SH_TOKEN_URL
    config.sh_base_url = SH_BASE_URL
    if not config.sh_client_id or not config.sh_client_secret:
        log.error("No credentials found. Save a 'cdse' profile or set SH_CLIENT_ID / SH_CLIENT_SECRET.")
        sys.exit(1)
    return config


def utm_epsg_for(lon, lat):
    """Return the EPSG code of the UTM zone containing a lon/lat point."""
    zone = int((lon + 180) / 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def find_acquisition_dates(catalog, collection, geometry, start, end, max_cc):
    """Return sorted unique acquisition dates (YYYY-MM-DD) below the cloud threshold."""
    results = catalog.search(
        collection,
        geometry=geometry,
        time=(start, end),
        filter=f"eo:cloud_cover < {max_cc}",
        fields={"include": ["properties.datetime", "properties.eo:cloud_cover"], "exclude": []},
    )
    dates = set()
    for item in results:
        dates.add(item["properties"]["datetime"][:10])
    return sorted(dates)


def fetch_one(config, collection, geometry, utm_geometry, bbox, size, time_interval,
              mode, max_cc, out_path):
    """Run a single Process API request and write a georeferenced GeoTIFF."""
    mosaicking = MosaickingOrder.LEAST_CC if mode == "composite" else MosaickingOrder.MOST_RECENT
    request = SentinelHubRequest(
        evalscript=EVALSCRIPT,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=collection,
                time_interval=time_interval,
                mosaicking_order=mosaicking,
                other_args={"dataFilter": {"maxCloudCoverage": max_cc}},
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        geometry=utm_geometry,   # clips output to the polygon, not just the bbox
        config=config,
    )
    data = request.get_data()[0]              # numpy array, shape (H, W, 16)
    if data is None or not np.any(data):
        log.warning("    empty response, skipping %s", os.path.basename(out_path))
        return False

    arr = np.transpose(data, (2, 0, 1)).astype("float32")   # -> (bands, H, W)
    transform = from_bounds(*bbox, width=size[0], height=size[1])
    with rasterio.open(
        out_path, "w", driver="GTiff",
        height=size[1], width=size[0], count=arr.shape[0],
        dtype="float32", crs=bbox.crs.pyproj_crs(), transform=transform,
        compress="deflate", nodata=None,
    ) as dst:
        dst.write(arr)
        for i, name in enumerate(BAND_NAMES, start=1):
            dst.set_band_description(i, name)
    return True


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(cfg_path)
    config = make_config()

    collection = DataCollection.SENTINEL2_L2A.define_from("cdse_s2l2a", service_url=SH_BASE_URL)
    catalog = SentinelHubCatalog(config=config)

    gdf = gpd.read_file(cfg["shapefile"])
    if gdf.crs is None:
        log.error("Shapefile has no CRS defined; please assign one and re-run.")
        sys.exit(1)
    gdf = gdf.to_crs(epsg=4326)               # work from WGS84 lon/lat
    log.info("Loaded %d site polygon(s) from %s", len(gdf), cfg["shapefile"])

    os.makedirs(cfg["output_dir"], exist_ok=True)
    total = 0

    for idx, row in gdf.iterrows():
        site_id = str(row[cfg["site_id_field"]]) if cfg["site_id_field"] else f"site{idx}"
        geom_wgs = row.geometry
        cx, cy = geom_wgs.centroid.x, geom_wgs.centroid.y
        epsg = utm_epsg_for(cx, cy)

        # Reproject the polygon to its local UTM zone so resolution is in metres.
        to_utm = Transformer.from_crs(4326, epsg, always_xy=True).transform
        from shapely.ops import transform as shp_transform
        geom_utm = shp_transform(to_utm, geom_wgs)

        utm_crs = CRS(epsg)
        utm_geometry = Geometry(geom_utm, crs=utm_crs)
        bbox = BBox(geom_utm.bounds, crs=utm_crs)

        size = bbox_to_dimensions(bbox, resolution=cfg["resolution"])
        if max(size) > MAX_DIM:
            scale = max(size) / MAX_DIM
            eff_res = cfg["resolution"] * scale
            log.warning("  %s: AOI exceeds %dpx; coarsening to ~%.1f m", site_id, MAX_DIM, eff_res)
            size = bbox_to_dimensions(bbox, resolution=eff_res)

        site_dir = os.path.join(cfg["output_dir"], site_id)
        os.makedirs(site_dir, exist_ok=True)
        log.info("Site %s  (UTM EPSG:%d, %dx%d px)", site_id, epsg, size[0], size[1])

        wgs_geometry = Geometry(geom_wgs, crs=CRS.WGS84)
        for start, end in cfg["date_windows"]:
            if cfg["mode"] == "composite":
                date_jobs = [((start, end), f"{start}_{end}_composite")]
            else:
                dates = find_acquisition_dates(
                    catalog, collection, wgs_geometry, start, end, cfg["max_cloud_cover"]
                )
                log.info("  %s -> %s : %d scene(s)", start, end, len(dates))
                date_jobs = []
                for d in dates:
                    nxt = (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                    date_jobs.append(((d, nxt), d))

            for time_interval, label in date_jobs:
                out_path = os.path.join(site_dir, f"{site_id}_{label}.tif")
                if os.path.exists(out_path):
                    log.info("    exists, skipping %s", os.path.basename(out_path))
                    continue
                try:
                    if fetch_one(config, collection, geom_wgs, utm_geometry, bbox, size,
                                 time_interval, cfg["mode"], cfg["max_cloud_cover"], out_path):
                        log.info("    wrote %s", os.path.basename(out_path))
                        total += 1
                except Exception as exc:           # keep going on per-scene failures
                    log.error("    FAILED %s : %s", os.path.basename(out_path), exc)

    log.info("Done. %d new GeoTIFF(s) written under %s/", total, cfg["output_dir"])


if __name__ == "__main__":
    main()
