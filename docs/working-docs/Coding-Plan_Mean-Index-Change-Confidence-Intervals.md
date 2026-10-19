# Coding Plan: Confidence Intervals for Mean Index Change (Step 1X)

## 1. Purpose

This plan describes the code needed to implement the methodology in
[`Mean-Index-Change-Confidence-Intervals.md`](../white-papers/Mean-Index-Change-Confidence-Intervals.md) (the methodology document). That document is the
authoritative reference for all formulas. Equation numbers below, e.g. (Eq. 6), refer to it.

The work produces three notebooks and a small supporting module. Together, they:

1. validate and benchmark the correlogram computation;
2. compute spatial-autocorrelation-adjusted confidence intervals (CIs) for mean index change between date pairs;
3. visualize the results.

## 2. Repository Context

- The existing notebook `00_acquire_imagery.ipynb` and its supporting package handle imagery acquisition. **This step must not depend on any acquisition-step code** (e.g., AOI loading or the site geopackage). Its only inputs are the GeoTIFFs.
- Notebooks follow the step-numbered, verb-led naming convention. This is major step 1, so its notebooks are numbered `1X_`.
- Reusable functionality goes in a new module or subpackage alongside the existing package. The suggested name is `change_ci`, but the agent should match existing repository structure and conventions.

## 3. Input Data

**File layout:** `[StudyAreaName]/[StudyAreaName]_[YYYY]-[MM].tif`, under a configurable data root.

**Coverage:** Months are `01`, `05`, `09`, and `11`; years are 2019–2025. There are multiple study areas.

**Raster properties:**

- Multiband GeoTIFFs with named index bands; the selected index is read by its
  band description.
- Typically about 500×500 pixels, and at most about 1000×1000.
- Paired rasters within a study area share the same CRS, transform, and shape.
  Valid pixels are intersected separately for each index and date pair.

**Invalid pixels** are NaN or the declared NoData value. They are almost entirely the pixels outside the study area. No separate mask product exists, and none should be created. (Acquisition masks each composite to its site's pixel-center footprint, so NaN already encodes "outside the study area"; see [Imagery Acquisition and Preparation](../white-papers/Imagery-Acquisition-and-Preparation.md).)

## 4. Pair Definition

Comparisons are **same month, consecutive years**: for each month, the pairs are 2019→2020, 2020→2021, …, 2024→2025. That gives 6 pairs per month and 24 per study area. The difference is always **later minus earlier** (Eq. 1).

Runs are phased, so the configuration must allow filtering by study area, month, and year range:

- **Phase 1:** September, 2023→2024.
- **Phase 2:** January, May, and November, 2023→2024.
- **Phase 3:** all remaining year pairs.

## 5. Coding Standards

- **Structure:** Pythonic, production-quality code. Use classes where state and data flow matter, and pure functions for stateless calculations.
- **Documentation:** Concise NumPy-style docstrings on every public class, method, and function, covering purpose, parameters, returns, and raised exceptions. Avoid verbosity. Where a function implements a formula, reference the equation number.
- **Type hints** throughout. Use `dataclasses` for configuration and result records.
- **I/O:** Use `pathlib` for all paths. Use `logging` rather than `print` in module code.
- **No hidden or global state.** Behavior is driven by an explicit configuration object.
- **Never use `np.roll`** for lagged comparisons. It wraps around the raster edges.
- **Tests:** pytest tests for all module logic (Section 10).

## 6. Dependencies

| Package | Use |
|---|---|
| `numpy` | All array computation |
| `scipy` | FFT correlation (`scipy.signal.correlate`), t quantiles (`scipy.stats.t`), synthetic test data (`scipy.ndimage`) |
| `rasterio` | Reading GeoTIFFs and grid metadata |
| `pandas` | Results tables and CSV input/output |
| `matplotlib` | Plotting |
| `libpysal`, `esda` | **Optional, validation only.** Imported lazily inside the PySAL engine. |
| `pytest` | Tests (development only) |

## 7. Module Design

### 7.1 Configuration — `AnalysisConfig`

`AnalysisConfig` loads and validates the current run settings, including the
`index_bands` batch, from [`configs/change_ci.yaml`](../../configs/change_ci.yaml).
That file is the editable source of analysis parameters. Each index is written
to `outputs/change_ci/<INDEX>/` with its own `results.csv`,
`correlograms.csv`, and `config.json` snapshot for auditability.

### 7.2 File discovery — pure functions

`discover_rasters(data_root) -> list[RasterRecord]`
: Scans for files matching the layout and parses the study area, year, and month with a regular expression. It logs a warning for any `.tif` that doesn't match. `RasterRecord` is a small dataclass with `study_area`, `year`, `month`, and `path`.

`build_pairs(records, config) -> list[PairSpec]`
: Forms same-month, consecutive-year pairs within the configured filters. It logs any pair skipped because a file is missing. `PairSpec` holds the study area, month, start and end years, and both paths.

### 7.3 `RasterPair` (class)

`RasterPair` loads and holds one date pair.

**Loading:** reads the configured named index band from each file with
`rasterio`, converts to float64, and fills masked values with NaN.

**Validation:** raises a clear error if the CRS, transform, or shape differ between the two rasters.

**Exposes:**

- `values`: D, with NaN for invalid pixels (Eq. 1). A pixel is valid if it is finite in both rasters.
- `n`: the number of valid pixels.
- `mean`: the mean of D (Eq. 2).
- `sd`: the sample standard deviation of D, with `ddof=1` (Eq. 3).
- `cell_size`: from `src.res`. Log a warning if the pixels are not square.
- `k_max`: from the bounding box of the valid pixels (Eq. 7).
- identifying metadata: study area, index, month, and years.

The raster may be cropped to the valid-pixel bounding box before further processing. Results are unchanged, and it reduces FFT padding. The class raises an error if fewer than 2 pixels are valid.

### 7.4 Correlogram engines (swappable)

The engine is the only part of the pipeline that depends on how the correlogram is computed. It is defined by a `typing.Protocol` (or an abstract base class):

```python
class CorrelogramEngine(Protocol):
    def compute(self, values: np.ndarray, max_lag: int) -> CorrelogramData: ...
```

`CorrelogramData` is a dataclass holding three arrays: `lags` (1…`max_lag`), `moran_i` (I_k), and `pair_counts` (W_k).

**Contract that every engine must satisfy** (so the engines are interchangeable):

- **Input:** a 2D float array where NaN marks invalid pixels.
- **Mean and variance:** computed over valid pixels only.
- **Weights:** binary, Chebyshev ring weights (Eq. 4), not row-standardized.
- **Pair counts:** W_k counts ordered pairs, so each pair is counted in both directions (Eq. 5).
- **Rings:** defined on the full grid, then restricted to valid pixels, so rings always follow Chebyshev distance and never route around gaps.
- **Moran's I:** computed per Eq. 6. If W_k = 0 at some lag, I_k is NaN.

**Engine registry:** `ENGINES = {"fft": FFTEngine, "bruteforce": BruteForceEngine, "pysal": PySALEngine}`, with `get_engine(name)` returning an instance. Switching engines is a configuration change only.

**`FFTEngine` (production default).** Follows the FFT-based approach of Marcotte (1996):

1. Build the deviation array: dᵢ − mean at valid pixels, 0 elsewhere. Build a 0/1 validity mask.
2. `S = correlate(dev, dev, mode="full", method="fft")` gives the sum of paired deviation products at every offset.
3. `C = correlate(mask, mask, mode="full", method="fft")` gives the valid pair count at every offset. Round it to integers to remove floating-point noise.
4. Crop both maps to offsets within `max_lag`. Label each offset by its Chebyshev distance, max(|dy|, |dx|).
5. Sum `S` and `C` by label (e.g., with `np.bincount`) to get the numerator and W_k for each lag. Then apply Eq. 6.

`mode="full"` already includes both (dy, dx) and (−dy, −dx), so these are ordered pairs, consistent with Eq. 5.

**`BruteForceEngine` (reference and teaching implementation).** Written for readability, not speed:

- Loop over lags, and over every offset (dy, dx) in ring k.
- Align two sliced views of the array for each offset, multiply the paired deviations where both pixels are valid, and accumulate the sums and counts.
- Comment each step against Eqs. 4–6. This engine doubles as the plain-language explanation of the method.

**`PySALEngine` (independent external validation).**

1. Import `libpysal` and `esda` inside the class.
2. Build full-grid queen lattice weights with `lat2W(nrows, ncols, rook=False)`.
3. Get ring-k weights with `higher_order(w, k)`. On a queen lattice, shortest-path order k equals Chebyshev distance k.
4. Subset the weights to the valid pixels.
5. Compute `esda.Moran(y, w_k, transformation="B", permutations=0)`, and take W_k from the weights' `s0`.

Handle pixels with no neighbors at a lag ("islands") without failing. Include a size guard parameter (e.g., `max_pixels`, default around 40,000) that raises an informative error for large inputs, because PySAL's memory and run time grow quickly with raster size and lag.

### 7.5 `MoranCorrelogram` (class)

`MoranCorrelogram` holds one pair's correlogram.

- **Constructor:** `MoranCorrelogram.from_raster_pair(pair, engine, max_lag=None)`. Runs the engine once, using `pair.k_max` if `max_lag` is None. Stores the `CorrelogramData` and `n`.
- **`effective_n(tau)`:** convenience method that calls `estimate_effective_n` (Section 7.6).
- **`to_frame()`:** returns tidy correlogram rows for the correlogram CSV.
- **`plot(ax=None, tau=None, range_px=None)`:** plots the correlogram, delegating to the plotting module.

### 7.6 Estimation — pure functions

Each function implements one equation, so each can be tested independently.

`find_range(moran_i, tau) -> int | None` (Eq. 8)
: Returns the first lag with I_k < τ, or `None` if no lag qualifies. Lags are 1-indexed.

`effective_sample_size(moran_i, pair_counts, n, range_px) -> float` (Eq. 9)
: Sums the lags from 1 to R−1. If R = 1, it returns n.

`estimate_effective_n(correlogram_data, n, tau) -> EffectiveNResult`
: Combines the two functions above. Returns the range, n_eff, and the no-range flag. If no range is found, n_eff is NaN.

`confidence_interval(mean, sd, n_eff, alpha) -> CIResult` (Eqs. 10–11)
: Returns the lower and upper bounds, the standard error, the degrees of freedom, and the t critical value.

The naive CI is the same function called with `n` in place of `n_eff`.

**Decision:** when no range is found, report n_eff and the adjusted CI as NaN with `flag_no_range = True`, rather than produce a misleading number.

### 7.7 Results and orchestration

**`ChangeCIResult` (dataclass).** One record per pair per τ, with fields matching the columns in Section 8. It has a `to_dict()` method.

**`ChangeCIAnalysis` (class).** Initialized with an `AnalysisConfig`.

- **`run_pair(spec, index_band)`:** loads the selected `RasterPair`, computes
  its correlogram once, then loops over `tau_sensitivity` to produce the
  results records and correlogram rows.
- **`run(specs)`:** repeats the analysis independently for every configured
  index and pair. Both result tables carry an `index` column.
- **`run(specs)`:** catches and logs per-index pair errors so one bad pair
  doesn't halt the run. The failure is recorded in an `error` column.
- **`save(results, correlograms)`:** writes each index to
  `output_dir/<INDEX>/`, with its own CSVs and `config.json`.

## 8. Outputs

For each index, outputs are written to `output_dir/<INDEX>/`:

- `results.csv`
- `correlograms.csv`
- `config.json`
- `plots/`

**`results.csv`** has one row per index × study area × month × year pair × τ.

| Column | Description |
|---|---|
| `study_area`, `index`, `month`, `year_start`, `year_end` | Pair identifiers |
| `tau`, `is_primary_tau` | Threshold used, and whether it is the primary one |
| `engine` | Engine used |
| `n`, `mean_change`, `sd` | Eqs. 1–3 |
| `k_max`, `cell_size` | Eq. 7 and grid metadata |
| `range_px`, `range_map_units` | Eq. 8 |
| `n_eff` | Eq. 9 |
| `df`, `t_crit`, `se`, `ci_low`, `ci_high` | Eqs. 10–11 |
| `naive_se`, `naive_ci_low`, `naive_ci_high` | Same calculation using `n`, for comparison |
| `ci_excludes_zero` | Boolean |
| `flag_no_range`, `flag_low_n_eff` | Quality flags (methodology Section 5) |
| `error` | Empty unless the pair failed |

**`correlograms.csv`** has one row per index × pair × lag, with columns
`study_area`, `index`, `month`, `year_start`, `year_end`, `lag`, `moran_i`,
and `pair_count`. Because this table is stored, correlograms can be re-plotted
and n_eff recomputed without reprocessing the rasters.

## 9. Notebooks

### `10_validate_correlogram_engines.ipynb`

1. **Worked example:** apply `BruteForceEngine` to a tiny synthetic array (e.g., 7×7). Visualize one ring and walk through a single I_k calculation in plain terms.
2. **Synthetic sanity checks:**
   - Uncorrelated noise should give I_k ≈ 0 and n_eff ≈ N.
   - Spatially smoothed noise (`scipy.ndimage.gaussian_filter`) should give a decaying correlogram and n_eff much smaller than N.
3. **Three-engine agreement:** run all three engines on a 100×100 window at lags 1–10, both with and without NaN pixels (e.g., an irregular masked region). Assert that I_k agrees to within floating-point tolerance and that W_k matches exactly.
4. **Full-size check:** compare FFT and brute force on one real, full-size pair across all lags up to `k_max`.
5. **Benchmark:** time each engine across window sizes (e.g., 100, 250, 500, and full size). Run PySAL at small sizes only. Present the timings as a table and a plot.

### `11_compute_change_confidence_intervals.ipynb`

1. Define the `AnalysisConfig`, selecting the phase.
2. Discover the rasters, build the pairs, and display the pair list.
3. Run the analysis.
4. Save the outputs.
5. Display a summary table and list any flagged or failed pairs.

The notebook should contain minimal logic; all computation lives in the module.

### `12_visualize_change_results.ipynb`

Loads the CSVs and produces the plots in Section 9.1. It must not recompute any statistics.

### 9.1 Plotting functions (`plotting.py`)

All plotting functions are pure: they take a DataFrame, accept an optional `ax`, and return the figure and axes. They default to the primary τ and include a save helper.

`plot_change_timeseries(results, group_by="month" | "study_area", filters..., show_ci_for="all" | None | list, ax=None)`
: The x-axis is the year pair, labeled like "2019→20". The y-axis is mean change, drawn as markers joined by a thin dashed line, with CI error bars. A solid line at zero marks no change. When there are multiple series, each is offset slightly along the x-axis so error bars don't overlap. `show_ci_for` controls which series get error bars; for example, error bars for one highlighted study area and means only for the others.

`plot_change_small_multiples(results, facet_by, ...)`
: A grid of panels, one per month or study area, each drawn as the time-series plot with a shared y-axis. This is the fallback when a single plot gets crowded.

`plot_change_heatmap(results, month, ...)`
: Rows are study areas and columns are year pairs, colored by mean change on a diverging colormap centered at zero (`TwoSlopeNorm`). A marker shows cells where `ci_excludes_zero` is true.

`plot_correlogram(correlograms, results, pair, ...)`
: Plots I_k against lag, with horizontal lines at each τ and the range marked.

`plot_n_eff(results, ...)`
: Plots n_eff across pairs, with the `min_n_eff` threshold drawn as a line.

`plot_tau_sensitivity(results, ...)`
: For each pair, shows the CI under each τ side by side.

## 10. Tests (`tests/`)

**Estimation functions:**

- **n_eff:** `effective_sample_size` with I = (0.6, 0.3, 0.1) and W_k = N·(8, 16, 24) returns N / 13.
- **Range:** `find_range` handles the edge cases: R = 1, no range found, and I_k exactly equal to τ.
- **CI:** `confidence_interval` matches a hand calculation using `scipy.stats.t`.

**Engines:**

- FFT and brute force agree on small random arrays, with and without NaNs.
- W_k matches exactly between engines.
- On a fully valid grid, W_k at lag 1 equals the expected queen count, accounting for edges.
- PySAL tests are skipped automatically if PySAL isn't installed.

**Discovery and pairs:**

- Filename parsing works, and non-matching files are ignored with a warning.
- Only consecutive-year, same-month pairs are formed.
- Missing files cause the pair to be skipped and logged.

**`RasterPair`:**

- Mismatched grids raise an error.
- The valid mask requires a pixel to be finite in both rasters.

These tests can use small temporary GeoTIFFs written with `rasterio`.

## 11. Out of Scope

- Any dependency on acquisition-step code, AOI polygons, or the site geopackage.
- Coverage or missing-data checks within the study area. Acquisition requirements already prevent missing data there.
- Block-based alternatives, such as block means or block bootstrap.
- Multiple-comparisons adjustment. It is noted in the methodology document but not implemented.

## 12. Reference

Marcotte, D. (1996). Fast variogram computation with FFT. *Computers & Geosciences*, 22(10), 1175–1186. https://doi.org/10.1016/S0098-3004(96)00026-X
