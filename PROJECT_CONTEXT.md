# Project Context & Next Steps

> Working notes capturing the design decisions and technical context behind this
> tool, plus open items to pick up in VS Code. This is a developer/AI-assistant
> reference, not user-facing documentation (see `README.md` for that).

---

## Goal

Build a reusable, automated workflow to retrieve Sentinel-2 raster data for a
fixed set of study sites, repeatedly across many dates and years, with minimal
manual effort and easy extensibility. Acquired data feeds downstream
mathematical/statistical analysis in QGIS, ArcGIS Pro, or Python.

---

## Key platform facts (verified during design)

- The old **Copernicus Open Access Hub / SciHub** is **retired**. All access now
  goes through the **Copernicus Data Space Ecosystem (CDSE)**. Legacy
  `sentinelsat`/SciHub scripts no longer work.
- CDSE exposes several APIs: OData/STAC catalogue, product download, **Sentinel
  Hub** (Process / Catalog / Statistical), and **openEO**.
- Account creation is free and instant; no institutional affiliation or approval
  wait. Authentication for the Process API is via an **OAuth client**
  (Client ID + Secret) created in the Sentinel Hub Dashboard.
- Endpoints in use:
  - Token: `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`
  - Base:  `https://sh.dataspace.copernicus.eu`
- A free monthly **processing-unit quota** applies; exact numbers change and
  should be checked on the dashboard before large runs.

---

## Decisions made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Access method | **Sentinel Hub Process API** | Server-side clipping + band/index computation; only the AOI is downloaded, not full tiles. |
| Product level | **L2A** (surface reflectance) | Atmospherically corrected; analysis-ready. |
| Output layers | B02–B12, NDVI, EVI, NDWI, NDMI, SCL, dataMask (16 bands) | Covers vegetation, water, moisture; SCL enables per-pixel cloud masking. |
| Output type | **FLOAT32 reflectance** | Preserves physical values for quantitative analysis (not 8-bit display). |
| Site input | Polygon **shapefile** | User's primary format; bbox support is a possible extension. |
| Acquisition mode | `per_scene` default | Full time series across days/years; `composite` available for least-cloudy mosaics. |
| Config strategy | External `config.yaml` | Add sites/dates/years without editing code. |

---

## Architecture summary

```
config.yaml ──► fetch_sentinel2.py
                   │
                   ├─ load polygons (geopandas), reproject each to local UTM
                   ├─ Catalog (STAC) search per window, filter eo:cloud_cover
                   ├─ Process API request per scene (evalscript builds 16 bands)
                   └─ write georeferenced GeoTIFF (rasterio) per site/date
                          └► outputs/<site_id>/<site_id>_<date>.tif
```

The evalscript (in `fetch_sentinel2.py`) is the place to change which bands and
indices are produced. `index(a,b)` is a Sentinel Hub built-in = `(a-b)/(a+b)`.

---

## Known limitations / risks to watch

- **SCL in the evalscript**: verify scene-classification values on first real run.
  Reflectance `units: "REFLECTANCE"` is set for optical bands; confirm SCL comes
  through as its integer class as expected.
- **Per-request pixel cap (~2500 px/side)**: large polygons are auto-coarsened
  with a warning. No true tiling yet — add if large AOIs are needed at 10 m.
- **Quota**: large site × date × year matrices may exhaust the free monthly quota.
- **Credentials**: must stay out of version control. `.gitignore` needs `.venv/`,
  `outputs/`, and any local secret files.
- Script was syntax-checked only; not yet executed end-to-end against live CDSE
  (no credentials/network at design time). First run = live validation.

---

## Next steps

### Immediate (validation)
- [ ] Register CDSE account, create OAuth client, save `cdse` profile.
- [ ] Run against 1 site, 1 short window; open output in QGIS and confirm:
      georeferencing, band order/names, reflectance range, SCL values.
- [ ] Add `.gitignore` (`.venv/`, `outputs/`, `*.tif`, credential files).

### Acquisition enhancements (optional)
- [ ] Bounding-box input mode (lat/long min/max) as an alternative to shapefile.
- [ ] Tiling for AOIs that exceed the pixel cap at native resolution.
- [ ] Per-run manifest/log (CSV of site, date, cloud %, file path) for traceability.
- [ ] Optional Statistical API path to get polygon-level stats without rasters.
- [ ] Consider openEO for large-scale cloud-side processing if volume grows.

### Analysis stage (the next conversation topic)
- [ ] Decide primary analysis environment: Python (`rasterio`/`xarray`) vs QGIS vs ArcGIS.
- [ ] Build SCL-based cloud-masking step (drop classes: cloud, cloud shadow, cirrus).
- [ ] Time-series extraction per site (e.g. mean NDVI per scene → DataFrame).
- [ ] Statistical/spatial analyses (trends, anomalies, inter-site comparison).
- [ ] Optional: QGIS Python (PyQGIS) or Processing model to automate analysis steps.

---

## Useful references

- CDSE APIs overview: https://documentation.dataspace.copernicus.eu/APIs.html
- Sentinel Hub Process API docs (with evalscript examples):
  https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html
- `sentinelhub-py` configuration: https://sentinelhub-py.readthedocs.io/en/latest/configure.html
- OAuth client registration / authentication:
  https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html
- SCL class definitions (Sentinel-2 L2A scene classification): see CDSE Sentinel-2 docs.