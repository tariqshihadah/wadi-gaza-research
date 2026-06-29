# Sentinel-2 Site Acquisition Tool

Automated retrieval of clipped, multi-band Sentinel-2 surface-reflectance rasters
for a fixed set of study sites, across arbitrary dates and years, from the
[Copernicus Data Space Ecosystem (CDSE)](https://dataspace.copernicus.eu).

The tool is built for repeated, reproducible data pulls: define your sites once
as polygons, list the time periods you care about in a config file, and run a
single command to download analysis-ready GeoTIFFs for every site and every
qualifying acquisition.

---

## Purpose

Manually searching, ordering, and clipping Sentinel-2 scenes is slow and hard to
reproduce, especially when the same sites must be revisited across many dates and
seasons. This tool replaces that manual process with a configurable script that:

- reads study-site boundaries from a polygon shapefile,
- queries the CDSE catalogue for low-cloud acquisitions in the periods you specify,
- clips and processes each scene **server-side** so only your area of interest is
  downloaded (not whole 110 km tiles), and
- writes one georeferenced, multi-band GeoTIFF per site per acquisition.

The outputs drop directly into QGIS, ArcGIS Pro, or a Python workflow
(`rasterio` / `xarray` / `geopandas`) for downstream statistical and spatial analysis.

---

## What each output contains

Every GeoTIFF is a 16-band, `FLOAT32` raster clipped to the site polygon. Values
are physical surface reflectance (≈ 0–1), not 8-bit display values, so they are
suitable for quantitative analysis.

| Band | Name | Description |
|-----:|------|-------------|
| 1–10 | B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12 | Surface reflectance (visible, red-edge, NIR, SWIR) |
| 11 | NDVI | Vegetation index `(B08 − B04) / (B08 + B04)` |
| 12 | EVI | Enhanced vegetation index |
| 13 | NDWI | Open-water index (McFeeters) `(B03 − B08) / (B03 + B08)` |
| 14 | NDMI | Moisture index `(B08 − B11) / (B08 + B11)` |
| 15 | SCL | Scene classification (integer class, 0–11; used for cloud masking) |
| 16 | dataMask | 1 where valid data exists, else 0 |

Band names are written into the GeoTIFF metadata, so GIS software labels them automatically.

---

## Repository contents

| File | Role |
|------|------|
| `fetch_sentinel2.py` | Main acquisition script. Not edited for routine use. |
| `config.yaml` | All user-editable settings: sites, dates, resolution, cloud threshold, mode. |
| `requirements.txt` | Python dependencies. |

---

## Prerequisites

- Python 3.9 or newer.
- A **free** CDSE account and a registered **OAuth client**
  (Client ID + Client Secret). See *Credentials* below.
- A polygon shapefile of your sites, with a CRS defined and an attribute column
  that uniquely identifies each site.

---

## Installation

```bash
git clone <your-repo-url>
cd <your-repo>
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

---

## Credentials

1. Register at <https://dataspace.copernicus.eu> (free; account is issued immediately).
2. Open the Sentinel Hub Dashboard → **User Settings** → **OAuth clients** →
   **Create**. Copy the **Client Secret** immediately — it is shown only once.
3. Supply the credentials in either of two ways:

   **Option A — saved profile (recommended):** run once in Python:

   ```python
   from sentinelhub import SHConfig
   c = SHConfig()
   c.sh_client_id = "<your-client-id>"
   c.sh_client_secret = "<your-client-secret>"
   c.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
   c.sh_base_url  = "https://sh.dataspace.copernicus.eu"
   c.save("cdse")
   ```

   **Option B — environment variables:**

   ```bash
   export SH_CLIENT_ID=<your-client-id>
   export SH_CLIENT_SECRET=<your-client-secret>
   ```

> **Do not commit credentials.** Keep secrets out of the repository (a saved
> profile lives in `~/.config/sentinelhub/`, outside the repo). Add `.venv/`,
> `outputs/`, and any local credential files to `.gitignore`.

---

## Configuration

All routine changes happen in `config.yaml`. You should not need to edit the
Python script to add sites, dates, or years.

```yaml
shapefile: "sites/my_sites.shp"   # path to your polygon shapefile
site_id_field: "site_id"          # attribute column used to name outputs (or null -> row index)
output_dir: "outputs"             # where GeoTIFFs are written
resolution: 10                    # output ground resolution in metres
max_cloud_cover: 30               # skip acquisitions cloudier than this (%)
mode: "per_scene"                 # "per_scene" = every qualifying date; "composite" = least-cloudy mosaic per window
date_windows:                     # add a line here to extend to new periods/years
  - ["2023-06-01", "2023-08-31"]
  - ["2024-06-01", "2024-08-31"]
  - ["2025-06-01", "2025-08-31"]
```

**Key settings**

- `mode: per_scene` produces a full time series — one file per acquisition date.
  `mode: composite` produces a single least-cloudy mosaic for each date window.
- `max_cloud_cover` filters at the scene-metadata level. The SCL band still lets
  you mask residual clouds per pixel during analysis.
- `resolution` is in metres because each site is processed in its local UTM zone.

---

## Usage

```bash
python fetch_sentinel2.py                 # uses config.yaml in the current folder
python fetch_sentinel2.py path/to/other.yaml
```

The script logs progress per site and per date window. Existing output files are
skipped, so runs are **idempotent** — interrupt and resume freely, or add new
date windows and rerun to fetch only the new scenes.

### Output layout

```
outputs/
  <site_id>/
    <site_id>_2023-07-04.tif
    <site_id>_2023-07-19.tif
    ...
```

---

## How it works

1. **Sites** are read from the shapefile and reprojected to WGS84, then each
   polygon is transformed to its local UTM zone so resolution is metric.
2. **Discovery** uses the CDSE Catalogue (STAC) API to list acquisitions in each
   date window below the cloud threshold.
3. **Processing** uses the Sentinel Hub Process API with a custom *evalscript*
   that selects the bands and computes the indices server-side, returning only the
   clipped area of interest.
4. **Writing** saves a georeferenced GeoTIFF via `rasterio`, with the correct UTM
   CRS, transform, and band descriptions.

Clipping and index computation happen in the cloud, which keeps downloads small
and avoids transferring full multi-gigabyte tiles.

---

## Notes and limitations

- **Processing quota.** A free CDSE account includes a monthly Sentinel Hub
  processing allowance. Large site × date × year matrices can consume it; check
  current limits on the CDSE dashboard before scaling up.
- **Large AOIs.** The Process API has a per-request pixel cap. Polygons large
  enough to exceed it at the requested resolution are automatically coarsened
  (with a warning). True tiling for very large areas is a possible future addition.
- **SCL handling.** Verify the scene-classification band on your first outputs;
  the evalscript can be adjusted if your masking needs differ.
- **Custom indices.** Additional indices can be added by editing the evalscript in
  `fetch_sentinel2.py` and increasing the output band count.

---

## Data attribution

Contains modified Copernicus Sentinel data, processed via the Copernicus Data
Space Ecosystem. Sentinel data are provided free and open under the Copernicus
data policy.

## License

Add your chosen license here (e.g. MIT) before publishing the repository.