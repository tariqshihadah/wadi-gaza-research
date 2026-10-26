# Coding Plan: ERA5-Land Climate Context (Step 2X)

Draft for PI review · Oct 26, 2026

## 1. Purpose

This plan turns the [Climate Context Scripting Brief](Climate-Context-Scripting-Brief.md) (the brief) into code, notebooks and a white paper. The brief's decisions log is fixed; this plan only adds implementation detail and flags open questions (Section 12).

The step produces descriptive monthly climate context (precipitation and 2 m temperature against an ERA5-Land 1991–2020 reference climatology) for each of the 196 imagery composites (7 sites × 7 years × 4 months). It does not test or model any relationship with index change.

## 2. Repository Context

- Major step 2, so notebooks are numbered `2X_` and follow the verb-led naming of `0X_`/`1X_`.
- Follow `change_ci` conventions: frozen-dataclass config loaded from `configs/climate.yaml` with strict key validation; `pathlib`; `logging` in module code; NumPy-style docstrings; pure functions for calculations; thin notebooks (as in `11_`); `config.json` snapshot beside outputs.
- Site polygons are read from `sites/StudySites.gpkg` (`site_name`, EPSG:32636), repairing invalid geometry with `make_valid` as in `00_acquire_imagery.ipynb`. No dependency on `s2grab` or `change_ci` code.
- Credentials live in `~/.cdsapirc` (`url`, `key`), outside the repository; `cdsapi` reads it natively. `.env.example` gets a one-line pointer so the setup is documented.

## 3. Preliminary Findings (Oct 26, 2026)

**Site-to-cell assignment** (centroid rounded to 0.1°), computed from the geopackage:

| Site | Centroid lat, lon | Area (km²) | Predicted cell | ERA5-Land land fraction |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 31.3030, 34.2198 | 3.38 | N31.3_E34.2 | 0.72 |
| BesorStream | 31.3570, 34.4699 | 1.13 | N31.4_E34.5 | 1.00 |
| HaBesorNationalPark | 31.2833, 34.4931 | 9.19 | N31.3_E34.5 | 1.00 |
| HolotNizzanim | 31.7448, 34.6149 | 13.95 | N31.7_E34.6 | 0.61 |
| HolotPalmahim | 31.9153, 34.7256 | 6.21 | N31.9_E34.7 | 0.57 |
| NahalRubin | 31.9382, 34.7196 | 0.78 | N31.9_E34.7 | 0.57 |
| WadiGaza | 31.4527, 34.4043 | 2.84 | N31.5_E34.4 | 0.55 |

Six unique cells; Holot Palmahim and Nahal Rubin share one. Land fractions come from the published ERA5-Land land-sea mask (`lsm_1279l4_0.1x0.1`). Four cells are coastal (fraction 0.55–0.72). All are above 0.5, so data is expected, but the product documentation does not state the masking threshold. The first download will confirm it.

**CDS request schema** (from the dataset form, `reanalysis-era5-land-timeseries`):

```python
{
    "variable": ["2m_temperature", "total_precipitation"],
    "location": {"latitude": 31.5, "longitude": 34.4},
    "date": ["1990-10-01/2026-01-01"],
    "data_format": "csv",
}
```

- The form also offers an `area` mode (up to 1° × 1°, every grid point in the box, no aggregation). All six cells fit in one box. See Section 12.
- Data is available through 2026-10-20, so 2025 is final ERA5-Land, not the preliminary ERA5-Land-T.
- Licence: CC-BY-4.0, accepted once per dataset on the CDS download page.

**Request end date.** Precipitation is period-ending, so the daily total for 2025-12-31 needs the value stamped 2026-01-01 00:00. The request therefore ends on **2026-01-01**. Daily outputs still stop at 2025-12-31. This adds to the brief without changing it.

## 4. Configuration — `configs/climate.yaml`

```yaml
sites_source: sites/StudySites.gpkg
id_field: site_name
output_dir: outputs/climate
dataset: reanalysis-era5-land-timeseries
data_format: csv
variables: [2m_temperature, total_precipitation]
extraction_range: ["1990-10-01", "2025-12-31"]   # request end is +1 day internally
reference_period: [1991, 2020]
study_years: [2019, 2025]
study_months: [1, 5, 9, 11]
wet_season_months: [10, 4]                         # October through April
near_zero_normal_mm: 10
min_reference_periods: 30
daily_temp_range_c: [-5, 45]
daily_precip_cap_mm: 200
```

Only the brief's named parameters (near-zero threshold, reference period, extraction range, study months) are expected to change. The rest are constants kept in one place for transparency.

## 5. Module Design — `src/cds_pull/`

Added to `pyproject.toml` `packages.find`.

| Module | Contents |
| --- | --- |
| `config.py` | `ClimateConfig.from_yaml(path, project_root=...)`, `to_dict()`, validation (e.g. extraction range covers October before the reference period and study windows) |
| `cells.py` | Pure functions: `predict_cell(lat, lon) -> (cell_lat, cell_lon)`, `cell_id(...) -> "N31.5_E34.4"`, `cell_box(...)`. `assign_cells(sites_gdf) -> DataFrame` (centroid in EPSG:32636 → WGS84, distance_km, shared_with). `write_cells_gpkg(...)` |
| `download.py` | `build_request(cell, config) -> dict`; `ClimateDownloader` wrapping `cdsapi.Client`: one request per cell, skip if raw files exist, unzip into `raw/<cell_id>/`, write a JSON metadata sidecar per request and a manifest row (cell, requested and returned lat/lon, dataset, request JSON, dates, UTC timestamp, cdsapi version, path, SHA-256, variable units and any header metadata in the CSV). Decade split is added only if a full request is rejected |
| `io.py` | `read_hourly(raw_dir) -> DataFrame[time, precip_m, t2m_k]` plus the returned grid point, read from the raw CSVs with `pandas`. Column names and units are confirmed against the probe download |
| `daily.py` | `daily_precip(hourly)` (D 01:00 … D+1 00:00, ×1000, clamp negatives, clamp count), `daily_temperature(hourly)` (00:00–23:00, mean and midrange, °C), `derive_daily(hourly)` with hour counts and `day_complete` |
| `windows.py` | `wet_season_window(year, month)`, `cumulative_window(year, month)`, season label `2019/20`; implements the brief's window table exactly |
| `summaries.py` | `monthly_totals(daily)`, `window_totals(daily, windows)`, `compute_normals(daily, config)` (mean, sample SD, n, first/last period, flags), `build_monthly_summary(daily, normals, site_cells, config)` |
| `checks.py` | Each brief check as a function returning rows for a `checks.csv` table (name, scope, passed, detail) |
| `plotting.py` | Pure plotting functions (Section 8), same style as `change_ci.plotting` |

**Rules carried into code.** Incomplete days stay in the daily file but are excluded from sums and means. An incomplete month or window blanks its precipitation metrics; temperature may still be reported from complete days. The near-zero rule blanks percent of normal and sets a flag. Nothing is filled or zeroed. Normals are computed per cell and joined to sites.

## 6. Outputs — `outputs/climate/`

As in the brief, with CSV raw files: `raw/<cell_id>/…csv` plus `…metadata.json` (git-ignored cache), `download_manifest.csv`, `site_cells.csv`, `era5land_cells.gpkg`, `daily_climate.csv`, `climate_normals.csv`, `monthly_climate_summary.csv` (196 rows), plus `checks.csv`, `config.json` and `plots/`.

**Monthly summary column groups** (snake_case, unit suffixes as in the brief):

- Keys: `site`, `cell_id`, `year`, `month`.
- Monthly: `precip_mm`, `precip_normal_mm`, `precip_anom_mm`, `precip_pct_normal`, `precip_near_zero_normal`, and `t2m_mean_24h_c`/`t2m_midrange_c` with `_normal_c` and `_anom_c` for each.
- Wet season: `wet_season_label`, `wet_season_start`, `wet_season_end`, `wet_season_precip_mm`, `_normal_mm`, `_anom_mm`, `_pct_normal`, `_missing_days`.
- Cumulative since October 1: `cum_since_oct1_start`, `_end`, `_precip_mm`, `_normal_mm`, `_anom_mm`, `_pct_normal`, `_missing_days`.
- Completeness: `precip_missing_days`, `t2m_missing_days`, `month_incomplete`.

## 7. Notebooks

| Notebook | Steps |
| --- | --- |
| `20_acquire_climate_data.ipynb` | Load config. Assign sites to cells; show the table and a map of sites over cells; write `site_cells.csv` and the GeoPackage. Download each cell, or reuse the cache. Write the manifest. Confirm each returned grid point matches its predicted cell. |
| `21_compute_climate_summaries.ipynb` | Read raw files. Derive daily values and write `daily_climate.csv`. Compute normals and the monthly summary. Run automated checks and display any failures or flags. Write outputs and the `config.json` snapshot. |
| `22_visualize_climate_context.ipynb` | Load CSVs only and produce figures (Section 8). No recomputation. |

| `23_validate_era5land_timeseries.ipynb` | Two small requests to the standard `reanalysis-era5-land` dataset (GRIB or NetCDF; the only place `xarray` is needed). Day-boundary check: daily totals for a few rainy days against the 00:00 D+1 accumulation. Spot-check: one cell and one wet month, monthly total and mean temperature. Results appended to `checks.csv`. |

## 8. Figures (`22_`)

Descriptive and Wadi-Gaza-first, mirroring `12_`:

1. Sites over ERA5-Land cell boxes (white-paper map).
2. Heatmap of precipitation anomaly (or percent of normal) per study month: rows are sites, columns are years. Near-zero cells are hatched.
3. Heatmap of wet-season and cumulative-since-October-1 percent of normal by site × year.
4. Time series of temperature anomaly by study month (both methods).
5. Climatology context: monthly normal bars (±1 SD) with observed 2019–2025 values overlaid, one panel per cell.
6. Daily cumulative precipitation since October 1 for each season 2017/18–2024/25 against the normal envelope, for the Wadi Gaza cell.
7. Mean-24h versus midrange temperature difference (diagnostic).

## 9. Dependencies

Add `cdsapi>=0.7` to `pyproject.toml`. Raw time-series files are CSV, read with `pandas`. The standard dataset used in `23_` has no CSV option, so `xarray` and `netCDF4` go in an optional `validation` extra.

## 10. Tests

- **Cells:** rounding at ±0.05 edges, ID formatting, Palmahim/Rubin sharing a cell, and a box geometry 0.1° wide.
- **Daily:** synthetic hourly series checks the period-ending shift (a single rain hour at D+1 00:00 lands on D), the m→mm factor, clamp counting, mean versus midrange on an asymmetric curve, and a 23-hour day flagged incomplete.
- **Windows:** every row of the brief's window table for each study month, plus season labels.
- **Summaries:** normals over exactly 30 periods with the under-30 flag, the near-zero blanking rule, incomplete-month blanking, May cumulative equal to wet season, and 196 rows.
- **Config:** canonical YAML loads; unknown or missing keys are rejected.
- **Download:** request built with the exact form parameter names. No live API calls in tests.

## 11. White Paper — `docs/white-papers/ERA5-Land-Climate-Context.md`

Follows the brief's outline and the numbering of the two existing papers (Purpose; Scope and Data; Notation; Method 4.1–4.6; Quality Checks; Assumptions and Notes; Reported Outputs). Settings are referenced from `configs/climate.yaml`, not duplicated. It will include the site-cell table and map, the window table with the USGS naming precedent, and equations for daily derivation and anomalies. It will be drafted after the first full run so it can report actual cell assignments and any substitutions.

## 12. PI Decisions and Open Questions

Decided Oct 26, 2026:

- Credentials in `~/.cdsapirc`.
- Package `cds_pull`; validation in a separate notebook `23_`.
- Raw time-series downloads as CSV, with metadata logged separately (sidecar JSON and manifest).
- The near-zero rule (normal < 10 mm) also applies to wet-season and cumulative percent of normal.
- No figures linking climate to index change for now; climate figures stand alone.
- Review the finalized plan with the PI before any download is run.
- Download mode: point requests, one per unique cell (6 requests). A regional area box can be added later if needed.

Implementation choice (Oct 26, 2026, for PI awareness): in `daily_climate.csv`, a day with fewer than 24 hourly values for a variable keeps its row and hour count, but that variable's daily value is left blank rather than holding a partial sum or mean.

Open:

- None blocking. Downloads wait on licence acceptance (Section 13, step 1).

## 13. Execution Order

Status as of Oct 26, 2026 in brackets.

1. Credentials (done) and acceptance of the "CC-BY licence" (`cc-by`) on the dataset download page (PI; **pending**, which blocks every download).
2. Config, `cells.py`, `windows.py`, `daily.py` and their tests. No credentials needed. [**done**; `summaries.py` and `download.build_request` were also written and tested against synthetic data]
3. Downloader in `download.py` and a one-cell probe (Wadi Gaza). Inspect the file structure, units, time stamps and returned grid point; write `io.py`.
4. Full download for six cells, then `checks.py` and notebook `21_` (and `20_`).
5. Validation requests and checks (`23_`).
6. Plotting and notebook `22_`.
7. White paper draft. Then update `docs/README.md` if needed.
