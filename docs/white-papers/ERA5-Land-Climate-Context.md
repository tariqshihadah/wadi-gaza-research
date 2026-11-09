# ERA5-Land Climate Context for Vegetation Index Change

## 1. Purpose

This document describes how monthly climate context is produced for the study region and for each vegetation index composite. For every grid cell in the region, and for every site, study year and study month, it reports precipitation and 2 m air temperature against an ERA5-Land 1991–2020 reference climatology, along with two seasonal rainfall measures.

The aim is interpretive, not inferential. Regional climate is largely shared across the study sites. If one site changes sharply in a period that was climatically ordinary across the region, climate is unlikely to be the main cause. If a period was unusually dry or hot everywhere, changes at all sites should be read with that in mind. The outputs are descriptive only. No correlation tests or regression models link climate to index change.

The executable settings are maintained in [`configs/climate.yaml`](../../configs/climate.yaml); this paper documents the method and rationale without duplicating that configuration. The implementation is the `cds_pull` package and notebooks `20_` to `23_`.

## 2. Scope and Data

**Coverage.** A rectangular study region of ERA5-Land grid points from 31.2° N to 32.0° N and 34.2° E to 34.8° E (63 points, 36 with data), covering all seven study sites. Study years are 2019–2025 and the study months are January, May, September and November. The site summary has one row per imagery composite: $7 \times 7 \times 4 = 196$ rows. A regional summary gives the same metrics for every cell with data.

**Source.** The ERA5-Land hourly time-series dataset (`reanalysis-era5-land-timeseries`) on the Copernicus Climate Data Store (CDS) ([dataset page](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries); [product user guide](https://confluence.ecmwf.int/x/Dg32Hw)). ERA5-Land is a land-surface reanalysis at 0.1° (about 9 km) resolution, hourly from 1950 to near real time. The time-series entry serves the full hourly record for a point or a small area in one request. It is marked experimental, so every raw download is archived and the derived daily values are checked against the standard gridded dataset (`reanalysis-era5-land`; Section 5).

**Variables.** Total precipitation (`tp`, metres of water per hour) and 2 m air temperature (`t2m`, kelvin). Outputs are reported in millimetres and degrees Celsius.

**Period.** Hourly data from 1990-10-01 through 2026-01-01 00:00 UTC, which gives complete daily values from 1990-10-01 through 2025-12-31. October–December 1990 is needed only so that the seasonal normals cover exactly 30 periods (Section 4.4). The final 00:00 value closes 2025-12-31 (Section 4.2).

**Access and licence.** Data are requested with the `cdsapi` Python client, using a personal CDS token kept outside the repository. The whole region is fetched in a single NetCDF area request. The CDS rates each request against a size limit of 500 units: the regional request costs 94 in NetCDF, while the same request as CSV would cost 2,350 and be rejected. The request box is padded by half a cell on every side, because the CDS leaves out grid points lying exactly on its northern and eastern edges. ERA5-Land is distributed under the CC-BY-4.0 licence, which is accepted once per account on the dataset page and places no limit on data volume.

## 3. Notation

| Symbol | Meaning |
|---|---|
| $D$ | A UTC calendar day |
| $p(t)$ | Hourly precipitation (m) stamped at time $t$, covering the hour ending at $t$ |
| $T(t)$ | Instantaneous 2 m temperature (K) at time $t$ |
| $P_D$ | Daily precipitation total for day $D$ (mm) |
| $\bar{T}_D$ | Daily 24-hour mean temperature (°C) |
| $\tilde{T}_D$ | Daily midrange temperature, (max + min) / 2 (°C) |
| $y$, $m$ | Observation year and calendar month |
| $X_{y,m}$ | An observed monthly or window value (a total in mm or a mean in °C) |
| $\mu_m$, $s_m$ | Normal (mean) and sample standard deviation of the same measure over the reference periods |
| $A_{y,m}$ | Anomaly, $X_{y,m} - \mu_m$ |
| $\%N_{y,m}$ | Percent of normal, $100\,X_{y,m} / \mu_m$ |
| $\theta$ | Near-zero threshold for percent of normal (mm) |

## 4. Method

### 4.1 Region grid and site-to-cell assignment

**Region grid.** All ERA5-Land grid points within the configured region are downloaded. Each grid point is treated as the centre of a 0.1° cell (edges at ±0.05°) and labelled by its centre, e.g. `N31.5_E34.4`. At about 31.5° N a cell measures roughly 11.1 km north–south by 9.5 km east–west (about 105 km²). Daily values, normals and the regional summary are computed for every cell with data, which supports regional maps and lets any site be compared with its neighbouring cells.

**Land and sea points.** ERA5-Land has values only at points it treats as land. Points it treats as sea are present in the download but empty; 27 of the 63 points in the region are empty. Along the coast, this classification does not follow the coastline closely. For example, N32.0_E34.7, whose cell is mostly over the Mediterranean, has data, while N31.9_E34.7, whose cell is more than half land, does not. ERA5-Land is produced on an octahedral reduced Gaussian grid (TCo1279, about 9 km) and distributed on the CDS after interpolation to the regular 0.1° grid ([ERA5-Land data documentation](https://confluence.ecmwf.int/display/CKB/ERA5-Land%3A+data+documentation)). The published 0.1° land-sea mask does not predict which points have data: N32.0_E34.7 has a land fraction of 0.36 and has data, while N31.9_E34.7 has 0.57 and does not. The land or sea status therefore appears to come from the native model grid, whose points do not line up with the 0.1° grid. ECMWF does not document the exact rule. In practice, a coastal 0.1° point with data represents the nearby land surface of the model, not the conditions at its geographic centre.

**Site assignment.** Each site uses the cell containing its polygon centroid. The centroid is computed in the sites' projected CRS (EPSG:32636) and transformed to WGS84, and the cell is found by rounding to the nearest 0.1°. Invalid site geometry is repaired with `make_valid` first, as in the imagery pipeline. The largest site, Holot Nizzanim, covers about 12 km², so each site occupies a small part of one cell. Climate values therefore describe the area around each site, not conditions within the site itself.

**Manual assignment.** Holot Palmahim and Nahal Rubin share a centroid cell, N31.9_E34.7, which has no data. Both sites are manually assigned to the adjacent cell to the east, N31.9_E34.8, so that each has data and the two neighbouring sites share one climate record. The assignment is set in the configuration (`site_cell_overrides`) and recorded in `site_cells.csv` (`assignment = manual`, with the centroid cell in `centroid_cell_id`).

| Site | Centroid (lat, lon) | Centroid cell | Cell used | Centroid to cell centre (km) | Assignment |
|---|---|---|---|---|---|
| Al Ahrash Protectorate | 31.303, 34.220 | N31.3_E34.2 | N31.3_E34.2 | 1.9 | Centroid |
| Besor Stream | 31.357, 34.470 | N31.4_E34.5 | N31.4_E34.5 | 5.6 | Centroid |
| HaBesor National Park | 31.283, 34.493 | N31.3_E34.5 | N31.3_E34.5 | 2.0 | Centroid |
| Holot Nizzanim | 31.746, 34.618 | N31.7_E34.6 | N31.7_E34.6 | 5.4 | Centroid |
| Holot Palmahim | 31.915, 34.726 | N31.9_E34.7 (no data) | N31.9_E34.8 | 7.2 | Manual |
| Nahal Rubin | 31.938, 34.720 | N31.9_E34.7 (no data) | N31.9_E34.8 | 8.7 | Manual |
| Wadi Gaza | 31.453, 34.404 | N31.5_E34.4 | N31.5_E34.4 | 5.3 | Centroid |

The reference layer `era5land_cells.gpkg` holds a 0.1° box for every grid point in the region, flagged by whether it has data and whether a site uses it. Notebook `22_` maps the sites over this grid.

### 4.2 Daily derivation

Days are UTC calendar days. Local time (UTC+2/+3) is not used: ERA5-Land is distributed in UTC, and the offset moves only the two or three hours at each end of a month between neighbouring months.

**Precipitation.** In the time-series product, precipitation is already converted from accumulations to hourly amounts, and each value is stamped at the **end** of its hour. The value stamped 00:00 therefore belongs to the previous day. The daily total sums the 24 values stamped $D$ 01:00 through $D{+}1$ 00:00:

$$
P_D = 1000 \sum_{h=1}^{24} p\left(D\ 00{:}00 + h\ \text{hours}\right) \tag{1}
$$

Summing 00:00–23:00 on $D$ instead would shift every day by one hour. A small number of hourly values are slightly negative because of numerical noise in the conversion from accumulations. These are set to zero before summing and counted in `precip_clamped`. The largest was $-6\times10^{-5}$ mm, and the clamped values total less than 0.07 mm per cell over the whole record.

**Temperature.** Two daily values are computed from the 24 instantaneous values stamped $D$ 00:00 through $D$ 23:00, after subtracting 273.15:

$$
\bar{T}_D = \frac{1}{24}\sum_{h=0}^{23} T\left(D\ 00{:}00 + h\ \text{hours}\right),
\qquad
\tilde{T}_D = \frac{\max_h T + \min_h T}{2} \tag{2}
$$

The 24-hour mean is the more complete summary of the daily cycle. The midrange matches the convention of most weather-station records. The daily cycle is asymmetric, so the two differ: averaged by cell and calendar month over the record, the midrange runs from about 0.05 °C cooler to 0.7 °C warmer than the 24-hour mean, and warmer in most cases (notebook `22_`). Both are carried through every later step as parallel columns. Because the maximum and minimum are taken from hourly samples, they slightly understate the true daily extremes.

### 4.3 Monthly summaries and metrics

For each cell and calendar month, the monthly precipitation is the sum of daily totals, and the monthly temperature is the mean of daily values, for each method. Each observation is compared with its normal (Section 4.4):

$$
A_{y,m} = X_{y,m} - \mu_m, \qquad \%N_{y,m} = 100\,\frac{X_{y,m}}{\mu_m} \tag{3}
$$

Precipitation is reported as a total, normal, anomaly (mm) and percent of normal. Temperature is reported as a mean, normal and anomaly (°C) for each method.

**Near-zero rule.** Percent of normal is unstable when the normal is very small: 3 mm against a 1 mm normal would read as 300%. When $\mu_m < \theta$, percent of normal is left blank and a near-zero flag is set; the absolute anomaly is still reported. The same rule applies to the wet-season and cumulative measures. With $\theta = 10$ mm it applies to every May and September at every site.

### 4.4 Reference climatology

All normals use 1991–2020, the current World Meteorological Organization standard reference period. They are labelled "ERA5-Land 1991–2020 reference climatology" to distinguish them from station normals. Normals are computed per cell and joined to sites.

| Normal | Values averaged | Data span |
|---|---|---|
| Monthly precipitation and temperature | Calendar month, years 1991–2020 | Jan 1991 – Dec 2020 |
| Wet-season precipitation | 30 seasons ending April 1991 – April 2020 (1990/91 to 2019/20) | Oct 1990 – Apr 2020 |
| Cumulative since October 1, per study month | Observation years 1991–2020, same window rule as Section 4.5 | Oct 1990 – Oct 2020 |

For each normal, `climate_normals.csv` stores the mean $\mu_m$, the sample standard deviation $s_m$, the number of complete periods, the first and last period, and a flag when fewer than 30 complete periods were available. Standard deviations are stored for possible later use. No standardized anomalies or percentile ranks are computed.

### 4.5 Accumulation measures

Vegetation responds to rain over the preceding months, not only in the observation month. Two seasonal rainfall measures are therefore reported for every observation, each with its normal, anomaly, percent of normal and missing-day count.

- **Wet-season precipitation:** the total for the most recently completed October–April season before the observation month.
- **Cumulative precipitation since October 1:** the total from October 1 through the last day of the month before the observation month. It is deliberately not called a water year or hydrological year.

| Observation month (year $y$) | Wet season used | Cumulative since October 1 |
|---|---|---|
| January | Oct $y{-}2$ – Apr $y{-}1$ | Oct 1 – Dec 31, $y{-}1$ |
| May | Oct $y{-}1$ – Apr $y$ | Oct 1, $y{-}1$ – Apr 30, $y$ |
| September | Oct $y{-}1$ – Apr $y$ | Oct 1, $y{-}1$ – Aug 31, $y$ |
| November | Oct $y{-}1$ – Apr $y$ | Oct 1 – Oct 31, $y$ |

For January, the most recently completed season ended nine months earlier, because the current season is still under way; the cumulative measure captures the October–December rain instead. For May, the two measures cover the same days and are identical; both are kept for a consistent schema. For September they differ only by the near-dry May–August months.

Seasons are labelled by their ending year: season `2019/20` runs from October 2019 to April 2020. This follows the U.S. Geological Survey's practice of naming its October–September water year by the calendar year in which it ends, the year that holds most of its months ([USGS](https://on.doi.gov/30pdStR)). The October–April season follows the same logic, since January–April are 4 of its 7 months. Start and end dates of every window are stored in the summary.

### 4.6 Completeness rules and flags

Missing data are counted and flagged, never filled or treated as zero.

- A day is complete for a variable only when all 24 hourly values are present. An incomplete day keeps its row and hour counts in `daily_climate.csv`, but its daily value for that variable is left blank.
- A month or accumulation window with any incomplete precipitation day has a blank total and blank derived metrics, because a partial sum understates rainfall. Monthly temperature is the mean of complete days. Missing-day counts and a `month_incomplete` flag are reported.
- A normal is computed from complete periods only and flagged if fewer than 30 remain.
- Every incomplete day is listed in `missing_days.csv` so it can be reviewed.

In the current run, all 36 cells with data are complete for every day from 1990-10-01 to 2025-12-31, so no metric is blanked.

## 5. Quality Checks

**Download manifest.** `download_manifest.csv` records the regional request: dataset, exact request and area, date range, number of grid points and of points with data, UTC download time, `cdsapi` version, raw file path and SHA-256 checksum. A JSON sidecar beside the raw files holds the same record. Raw files are never modified; every derived product can be rebuilt from them and the configuration.

**Automated checks** (`checks.csv`, notebook `21_`):

- The downloaded grid matches the configured region, and every site's cell has data. Manual assignments are listed with the site's centroid cell.
- In every cell with data, every day has 24 hourly values per variable, or is listed in `missing_days.csv`.
- Daily temperatures lie within −5 to 45 °C, and daily precipitation is non-negative and below 200 mm. Clamped negative hourly values are counted.
- Every normal uses 30 complete periods.
- The summary has 196 rows, each site maps to exactly one cell, and no study month is incomplete.

**Validation against the standard dataset** (`validation_checks.csv`, notebook `23_`). For one cell and one wet month (Wadi Gaza, January 2020), the same data are requested from the standard `reanalysis-era5-land` dataset. In that dataset precipitation is accumulated from 00 UTC, so its 00:00 value on $D{+}1$ is the full total for day $D$. This tests the day boundary in Equation (1) directly. The monthly precipitation total and mean temperature are compared as a spot-check of the experimental time-series entry. In the current run, all 17 rainy days agree within 0.00002 mm. The monthly total is 122.63 mm in both products, and the mean temperature is 12.910 °C in both.

## 6. Assumptions and Notes

**Reanalysis, not observations.** ERA5-Land is a model reanalysis driven by assimilated observations. It is spatially and temporally complete but can differ from rain-gauge and station records, especially for convective rainfall and along coasts.

**Regional, not site-level, climate.** At about 9 km resolution, a single cell represents the area around a site. Climate values are best compared across sites and years, not read as conditions inside a specific site polygon.

**Cell choice.** The centroid rule is simple and reproducible, but a site near a cell edge could reasonably be assigned to a neighbouring cell. Normals change considerably between neighbouring cells along the region's rainfall gradient: annual precipitation ranges from about 140 mm in the south-east to about 450 mm along the northern coast. Relative measures are much less sensitive. The Wadi Gaza centroid lies about 300 m inside the southern edge of N31.5_E34.4. Compared with the cell to the south, N31.4_E34.4, its wet-season normal is higher (302 mm against 237 mm), but across the 28 study months its wet-season percent of normal differs by at most 7 percentage points, and its temperature anomaly by at most 0.2 °C (notebook `22_`). The manually assigned Holot Palmahim and Nahal Rubin use a cell 7–9 km from their centroids.

**Warming trend.** Because the reference period ends in 2020 and the region has warmed, positive temperature anomalies are expected at most sites in most study months. A warm anomaly is informative mainly when it stands out from those at other sites or in other years.

**Hourly extremes.** Daily maximum and minimum come from hourly samples and slightly understate true extremes, so the midrange is an approximation of the station convention.

**Identical May measures.** For May observations, wet-season and cumulative precipitation cover the same days.

**Experimental dataset.** The time-series entry may change format or be withdrawn. The archived raw files, manifest and validation against the standard dataset protect the reproducibility of this run.

## 7. Reported Outputs

All outputs are written to `outputs/climate/`.

| File | Grain | Contents |
|---|---|---|
| `raw/region/` | One regional download | Untouched zip from the CDS, extracted NetCDF files and `request.json` sidecar (local cache, not version-controlled) |
| `download_manifest.csv` | One row | Provenance and checksum of the regional download (Section 5) |
| `site_cells.csv` | One row per site | Centroid, centroid cell, cell used, distance to cell centre, assignment and shared cells |
| `era5land_cells.gpkg` | One feature per grid point in the region | 0.1° cell box, `has_data` and `used` (EPSG:4326) |
| `daily_climate.csv` | One row per cell with data and UTC day | Precipitation, both temperature methods, hourly counts, clamp count and completeness |
| `missing_days.csv` | One row per incomplete day | Cell, date and hourly counts per variable |
| `climate_normals.csv` | One row per cell, measure and month | Mean, SD, number of periods, period span and flags |
| `monthly_climate_summary.csv` | One row per site, year and study month (196 rows) | Monthly, wet-season and cumulative values with normals, anomalies, percent of normal, window dates, missing-day counts and flags |
| `regional_climate_summary.csv` | One row per cell with data, year and study month | The same columns as the site summary, keyed by cell |
| `checks.csv` | One row per check and scope | Automated checks (Section 5) |
| `validation_daily.csv`, `validation_checks.csv` | Validation month | Day-by-day comparison with the standard dataset and the resulting checks |
| `config.json` | One per run | Snapshot of the configuration used |
| `plots/` | Figures | Descriptive figures from notebook `22_` |
