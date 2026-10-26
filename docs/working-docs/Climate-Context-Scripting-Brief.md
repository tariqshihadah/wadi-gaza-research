# ERA5-Land Climate Context: Scripting Handoff Brief

Oct 26, 2026 · @Tariq

## Purpose and context

Build a reproducible pipeline that pulls ERA5-Land hourly precipitation and 2 m temperature for the seven study sites, derives daily values, and produces descriptive monthly climate summaries against a 1991–2020 reference climatology.

The summaries give climate context for the vegetation index results. They help show whether a period was climatically unusual across the region, so the sharp change at Wadi Gaza and the small changes elsewhere can be read against regional climate. They are descriptive only: no correlation tests or regression models are planned.

The pipeline sits beside the existing imagery workflow (Imagery Acquisition and Preparation) and the mean index change analysis (Confidence Intervals for Mean Index Change). Follow the same conventions those pipelines use: settings in a YAML config under `configs/`, outputs under `outputs/`, provenance recorded with every product, and automated checks.

The monthly summary has one row per site, year (2019–2025) and study month (January, May, September, November): 7 × 7 × 4 = 196 rows, one per imagery composite.

## Decisions log

All items below are confirmed with the PI. Treat them as fixed unless the PI changes them.

| Topic | Decision |
| --- | --- |
| Source | ERA5-Land hourly time-series dataset on the Copernicus Climate Data Store (CDS), via the Python `cdsapi` client |
| Variables | Total precipitation (output in mm) and 2 m air temperature (output in °C) |
| Extraction period | 1990-10-01 through 2025-12-31 (October 1990 is needed only for accumulation normals) |
| Reference period | 1991–2020 for all normals |
| Spatial unit | The ERA5-Land grid cell containing each site's centroid; one download per unique cell |
| Day definition | UTC calendar days |
| Daily temperature | Two parallel methods: 24-hour mean and (max + min) / 2 midrange, both from hourly values |
| Precipitation metrics | Monthly total, normal, absolute anomaly (mm) and percent of normal |
| Temperature metrics | Monthly mean, normal and anomaly (°C), for each temperature method |
| Near-zero rule | Percent of normal is left blank and flagged when the monthly normal is below 10 mm; the threshold is a config parameter |
| Wet season | Most recently completed October–April season before the observation month |
| Cumulative precipitation | From October 1 through the last day of the month **before** the observation month; labeled "cumulative precipitation since October 1", never "water year" |
| Wet-season normals | The 30 seasons **ending** April 1991 through April 2020 (seasons 1990/91 to 2019/20) |
| Cumulative normals | Observation years 1991–2020 for each study month |
| Missing data | Counted and flagged, never filled or treated as zero |
| Dropped metrics | Percentile ranks and standardized anomalies are out of scope; store standard deviations so they can be added later |

## Data source and access

Use the CDS dataset [ERA5-Land hourly time-series data from 1950 to present](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries) (`reanalysis-era5-land-timeseries`). It serves long hourly records for a single point on the 0.1° ERA5-Land grid, as NetCDF or CSV.

Key properties, from the [product user guide](https://confluence.ecmwf.int/x/Dg32Hw):

- Point requests snap to the nearest 0.1° grid point. The returned file carries that point's coordinates.
- Total precipitation is already **de-accumulated to hourly values**, in metres. 2 m temperature is in kelvin.
- Each hourly value is labelled at the **end** of its hour, so the 00:00 value belongs to the previous day.
- Dates with fewer than 24 hourly samples are skipped, not padded.
- Temperature and precipitation sit in different parameter groups, so one request returns two files.
- The dataset is marked **experimental**: it may change format or be withdrawn. Archive every raw download.

**Credentials are separate from the Sentinel Hub / Copernicus Data Space Ecosystem key.** Setup:

1. Create an ECMWF account and log in to the [CDS](https://cds.climate.copernicus.eu/how-to-api).
2. Copy the personal access token into `~/.cdsapirc` (`url: https://cds.climate.copernicus.eu/api` and `key: <token>`), or pass it to the client from the project's existing secrets handling.
3. Accept the dataset licence once on the dataset's download page. Without this, requests fail with a licence error.
4. Install the client: `pip install "cdsapi>=0.7"`.

**Request shape.** Build the exact request once from the dataset's download form ("Show API request") and copy its parameter names into the code; don't guess them. Request per unique cell: both variables, the full date range, NetCDF output. If a single full-range request is rejected as too large, split by decade.

**Fallback (only if the time-series entry is unavailable).** The standard `reanalysis-era5-land` dataset carries the same data, but precipitation there is accumulated from 00 UTC. The 00:00 value on day D+1 is the full total for day D and must not be summed with other hours. Don't build this path unless needed.

## Site-to-cell assignment

Each site maps to the one ERA5-Land cell that contains its polygon centroid. No polygon upload or reference grid is needed: the API takes a latitude/longitude point.

At about 31.5°N a 0.1° cell is roughly 11.1 km north–south by 9.5 km east–west (about 105 km²). The largest site, Holot Nizzanim, is about 14 km², so every site falls within a small part of one cell. Several sites are expected to share cells.

Steps:

1. Read each polygon from `sites/StudySites.gpkg` (EPSG:32636), repairing HaBesor National Park with `make_valid` as the imagery pipeline does.
2. Compute the centroid in EPSG:32636, then transform it to WGS84 latitude/longitude.
3. Predict the cell by rounding the centroid to the nearest 0.1° (grid points sit on multiples of 0.1°; cell edges at ±0.05°).
4. Build a cell ID from the cell-center coordinates, e.g. `N31.4_E34.4`.
5. Download once per unique cell. After download, confirm the returned grid point matches the predicted cell.

**Reference layer.** Write the 0.1° cell boxes for all assigned cells as a small polygon layer (GeoPackage, EPSG:4326, one feature per cell with its cell ID). It supports a white-paper map of site boundaries over cells.

**Coastal cells.** ERA5-Land has values only over land, and some coastal cells are empty. Holot Nizzanim and Holot Palmahim are coastal. Start with the centroid cell. If a cell returns no data, use the nearest cell that has data and record the substitution, but don't script this case until it occurs.

## Daily derivation

Days are UTC calendar days. Local time (UTC+2/+3) is not used; document this in one sentence.

**Precipitation.** Hourly values in the time-series product are period-ending. The daily total for date D is the sum of the 24 values stamped D 01:00 through D+1 00:00, multiplied by 1,000 to convert m to mm. Summing 00:00–23:00 on D shifts every day by one hour; avoid this.

```latex
P_D = 1000 \sum_{h=1}^{24} p\left(D\ 00{:}00 + h\ \text{hours}\right)
```

Clamp tiny negative hourly values (numerical noise) to zero and count how many were clamped.

**Temperature.** From the 24 hourly values stamped 00:00–23:00 on D, after subtracting 273.15:

- `t2m_mean_24h`: the mean of the 24 values.
- `t2m_midrange`: (max + min) / 2 of the 24 values, the convention most weather stations use.

The two usually differ by a few tenths of a degree because the daily cycle is asymmetric. Carry both through every later step as parallel columns. Max and min come from hourly samples, so they slightly understate true daily extremes.

**Completeness.** Record the number of hourly values present for each variable and day (24 expected). A day is complete only with all 24. Incomplete days stay in the daily file with a flag but are excluded from monthly sums and means, and the month is flagged.

## Monthly summaries and metrics

For each site, year 2019–2025 and study month (January, May, September, November):

| Metric | Definition | Units |
| --- | --- | --- |
| Monthly precipitation | Sum of daily totals for the calendar month | mm |
| Precipitation normal | Mean of the same calendar month's totals, 1991–2020 | mm |
| Precipitation anomaly | Observed minus normal | mm |
| Percent of normal | 100 × observed / normal; blank when the normal is below the near-zero threshold | % |
| Near-zero normal flag | True when the normal is below the threshold (default 10 mm, config parameter) | — |
| Monthly mean temperature | Mean of daily values, for each method (24-hour mean and midrange) | °C |
| Temperature normal | Mean of the same calendar month's monthly means, 1991–2020, same method | °C |
| Temperature anomaly | Observed minus normal, same method | °C |
| Missing days | Expected days minus complete days, per variable | days |
| Incomplete flag | True when any day in the month is incomplete | — |

Expect the near-zero flag in May and September at every site, and possibly in some Novembers. For an incomplete month, leave the precipitation total and its derived metrics blank, because a partial sum understates rainfall. The temperature mean may be reported from complete days, with the flag set.

## Accumulation measures

Two rainfall measures per observation, both in mm, each with its normal, absolute anomaly, percent of normal and missing-day count.

- **Wet-season precipitation:** total for the most recently completed October–April season before the observation month.
- **Cumulative precipitation since October 1:** total from October 1 through the last day of the month before the observation month. Use this exact label; never call it a water year or hydrological year.

| Observation month (year Y) | Wet season used | Cumulative since October 1 |
| --- | --- | --- |
| January | Oct Y−2 – Apr Y−1 | Oct 1 – Dec 31, Y−1 |
| May | Oct Y−1 – Apr Y | Oct 1, Y−1 – Apr 30, Y |
| September | Oct Y−1 – Apr Y | Oct 1, Y−1 – Aug 31, Y |
| November | Oct Y−1 – Apr Y | Oct 1 – Oct 31, Y |

Notes for the scripting agent:

- January's "most recently completed" season ended nine months earlier, because the current season is still under way. The cumulative measure captures the October–December rain instead.
- For May, the two measures are identical (both October–April). Keep both columns for a consistent schema; the white paper will note the identity.
- For September, the two are nearly identical, because May–August is close to dry.
- Label each season by its ending year, e.g. season `2019/20` = October 2019 – April 2020. Store both start and end dates of every window in the output.
- The earliest window needed is October 2017 (January 2019 observation), well inside the extraction range.

## Normals

All normals use 1991–2020, the current WMO standard reference period, also used by NOAA. Name them "ERA5-Land 1991–2020 reference climatology", not station normals. Compute them per cell, then join to sites.

| Normal | Values averaged | Data span used |
| --- | --- | --- |
| Monthly precipitation and temperature | Calendar months, years 1991–2020 | Jan 1991 – Dec 2020 |
| Wet-season precipitation | 30 seasons ending April 1991 – April 2020 (1990/91 – 2019/20) | Oct 1990 – Apr 2020 |
| Cumulative since October 1, per study month | Observation years 1991–2020, same window rule as the table above | Oct 1990 – Oct 2020 |

October 1990 is extracted only so the accumulation normals cover exactly 30 periods anchored to 1991–2020. The monthly normals do not use it.

**Precedent for the season rule.** USGS names its October–September water year by the calendar year in which it ends, the year holding most of its months ([USGS](https://on.doi.gov/30pdStR)). The October–April season follows the same logic: January–April is 4 of its 7 months. Cite this as precedent for naming a cross-year period by its ending year, without calling the season a water year.

For every normal, store: the mean, the sample standard deviation, the number of complete periods used, the first and last period, and a flag if fewer than 30 complete periods were available. Standard deviations are stored for possible later use; no standardized anomalies are computed now.

## Outputs and file schemas

Suggested location: `outputs/climate/`. Column names are suggestions; align them with the existing pipelines' style.

| File | Grain | Key columns |
| --- | --- | --- |
| `raw/<cell_id>/…nc` | As downloaded | Untouched API files; internal cache, not delivered |
| `site_cells.csv` | One row per site | site, centroid\_lat, centroid\_lon, cell\_id, cell\_lat, cell\_lon, distance\_km, shared\_with, substituted (bool) |
| `era5land_cells.gpkg` | One feature per cell | cell\_id, cell\_lat, cell\_lon, 0.1° box geometry (EPSG:4326) |
| `daily_climate.csv` | One row per cell and UTC date, Oct 1990 – Dec 2025 | cell\_id, cell\_lat, cell\_lon, date, precip\_mm, t2m\_mean\_24h\_c, t2m\_midrange\_c, precip\_hours, t2m\_hours, day\_complete |
| `climate_normals.csv` | One row per cell, measure and month or study month | cell\_id, measure, month, mean, sd, n\_periods, period\_first, period\_last, incomplete\_flag, near\_zero\_flag |
| `monthly_climate_summary.csv` | One row per site, year and study month (196 rows) | site, cell\_id, year, month, monthly metrics, wet-season window and metrics, cumulative window and metrics, missing-day counts, flags |

The daily file is per cell, not per site, so shared-cell data isn't duplicated; `site_cells.csv` links the two. The normals file is the authoritative source for normals; the monthly summary repeats each normal beside its observation for convenience. Cross-cell comparison needs no extra output: the PI can compare cells from the normals and daily files.

## Audit trail and quality checks

Record a download manifest (one row per request): cell ID, requested latitude/longitude, returned grid point, dataset name, exact request parameters, date range, download timestamp (UTC), `cdsapi` version, raw file path and file checksum. Never modify raw files; every derived product must be rebuildable from them and the config.

Automated checks:

- Each returned grid point matches the cell predicted from the centroid.
- Every day in the range has 24 hourly values per variable, or is flagged.
- Units are plausible: daily temperatures roughly −5 to 45 °C; daily precipitation non-negative and below a sanity cap (e.g. 200 mm).
- Day boundary check: for a few rainy days, the daily total matches the standard dataset's accumulated value at 00:00 on the following day, which is that day's full total.
- The monthly summary has 196 rows, and every site maps to exactly one cell.
- **Spot-check:** for one cell and one wet month, compare the monthly total and mean temperature against the standard `reanalysis-era5-land` dataset. This guards against the time-series entry's experimental status, mirroring the re-fetch check in the imagery pipeline.

## Scope guardrails

Start simple and expand only when the data shows a need. Parameterize only what is likely to change: the near-zero threshold, the reference period, the extraction range and the study months.

Deferred until needed:

- Fallback to a neighbouring cell when a centroid cell has no data.
- The fallback download path through the standard `reanalysis-era5-land` dataset.
- Percentile ranks, standardized anomalies and any cross-cell comparison tables.

Out of scope: correlation tests, regression models and local-time day definitions.

## Suggested white paper outline

A rough outline for the scripting agent, mirroring the structure of the two existing papers. Settings live in `configs/climate.yaml`; the paper documents method and rationale without duplicating them.

1. **Purpose.** Descriptive climate context for vegetation index trajectories. Explain the logic: regional climate is shared across sites, so a sharp change at one site in a climatically ordinary period points away from climate as the cause.
2. **Scope and data.** ERA5-Land hourly time series, variables and units, extraction period from October 1990, access and licence.
3. **Notation.**
4. **Method.**
   1. Site-to-cell assignment: centroid rule, cell size versus site size, shared cells, map of sites over cells.
   2. Daily derivation: period-ending timestamps, UTC days, 24-hour mean and midrange temperature.
   3. Monthly summaries and metrics, including the near-zero rule.
   4. Reference climatology: periods, statistics stored, ERA5-Land versus station normals.
   5. Accumulation measures: the window table and the season-labelling precedent.
   6. Completeness rules and flags.
5. **Quality checks.** Manifest, automated checks, spot-check against the standard dataset.
6. **Assumptions and notes.** Reanalysis versus station data; 9 km resolution means the data describes regional, not site-level, climate; recent warming makes positive temperature anomalies likely at every site; hourly max/min understate true extremes; May cumulative equals wet-season total; experimental dataset status.
7. **Reported outputs.** The files in the schema table above.
