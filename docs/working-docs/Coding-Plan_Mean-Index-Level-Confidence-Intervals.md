# Coding Plan: Confidence Intervals for Mean Index Levels

## Goal

Add a parallel `index_ci` pipeline for site × index × month × observation-year spatial means, retaining the existing change-CI path and its outputs.

## Shared core

Extract Moran's I engines, correlogram records/workflow, effective-sample-size estimation, t intervals, raster discovery, and generic band reading into `src/spatial_ci/`. Keep `change_ci` compatibility modules as re-exports/adapters so existing imports and results remain stable. Notebook 10 validates the shared core directly, including a real single-year index raster.

## Index pipeline

- Read one index band from each dated raster; do not form year pairs or subtract rasters.
- Filter observations with `configs/index_ci.yaml`.
- For each index/site/month group, verify grid identity and use the intersection of valid pixels across selected years. Apply that exact mask to every observation before calculating means or correlograms.
- Write per-index results and correlograms under `outputs/index_ci/<INDEX>/`, with a config snapshot.
- Use `year` and `mean_index` fields; do not use pair identifiers or a change-specific zero-exclusion flag.

## Notebooks and figures

- Keep notebooks 11 and 12 as the current change-analysis workflow.
- Add `13_compute_index_confidence_intervals.ipynb` and `14_visualize_index_results.ipynb`.
- Visualize annual means with CI bands, Wadi Gaza highlighted against dotted comparison-site trajectories, site-by-year heatmaps by month with a shared color scale, effective sample size over time, and selected annual correlograms.
- Keep statistical calculations in the module; notebooks should configure, run, review, and plot saved outputs.

## Validation

Test that shared imports preserve the change pipeline; engine and estimator results are unchanged; common masks are identical across years; grid mismatches and invalid groups are reported; index result rows are per observation and threshold; outputs are saved independently; and plotting uses year-level values and CIs.
