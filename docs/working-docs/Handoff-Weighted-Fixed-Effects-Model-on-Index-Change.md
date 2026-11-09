# Handoff: Weighted Fixed-Effects Model on NDVI Change

Nov 8, 2026 · @Tariq

## Purpose and context

Build a script that tests whether Wadi Gaza's NDVI change in 2023–24 was anomalous relative to its own baseline years and to six comparison sites. The main test is a weighted two-way fixed-effects difference-in-differences model fit to site-level mean changes, with weights that carry the spatial-autocorrelation-adjusted standard errors already computed upstream.

The unit of analysis is the site × year-pair mean change, not the pixel. Each site-year contributes one observation, so pixel counts never inflate the degrees of freedom. Within-site spatial autocorrelation enters through each observation's standard error, `se = sd / sqrt(n_eff)`, which the upstream correlogram analysis produced. This is the direct response to a reviewer's concern that earlier inference treated pixels as independent.

Background methods are in the project's white papers: *Imagery Acquisition and Preparation* and *Confidence Intervals for Mean Index Change Under Spatial Autocorrelation*. The upstream threshold for the correlogram range is called τ in those papers; this brief keeps τ for that threshold only and uses σ\_u² for the model's site-year variance.

## Scope

Build four components and run each for every index (NDVI, GNDVI, SAVI, NDRE) and every month:

1. **Main model:** weighted fixed-effects model, run separately for each month (January, May, September, November) at the primary τ = 0.05.
2. **Placebo-in-space:** refit with each comparison site as the fake affected site.
3. **Placebo-in-space-and-time:** refit with every unaffected site × year-pair cell as a fake event.
4. **Sensitivity reruns of the main model:** τ ∈ {0.02, 0.05, 0.10} and three ways of handling missing SEs.

January runs through everything but is labeled supplementary in all outputs. Its NDVI is driven by wet-season rainfall, so its noise is three to five times larger than other months; the PI plans to report it in the supplement.

NDVI is the primary index; GNDVI, SAVI and NDRE are robustness checks and should be labeled that way in every output. Out of scope for now: the levels model and event-study figure, leave-one-site-out, and climate data. Do not modify upstream data or the correlogram code.

## Input data

The input is the change-CI results: 504 rows per index, one per site × month × year pair × τ (7 × 4 × 6 × 3). The current `results.csv` holds NDVI only. The other indices may arrive in the same file or one file per index, so the config should accept a list of input paths and concatenate them. NDRE carries 20 m detail resampled to 10 m; its upstream n\_eff already reflects that, so it needs no special handling.

| Column | Use |
| --- | --- |
| `study_area` | Site; the affected site is `WadiGaza` |
| `index` | `Loop over NDVI, GNDVI, SAVI, NDRE` |
| `month` | Run each month separately (1, 5, 9, 11) |
| `year_start`, `year_end` | Year pair; consecutive pairs 2019–20 through 2024–25 |
| `tau` | Correlogram threshold; 0.05 is primary |
| `mean_change` | Outcome: site mean of the NDVI difference raster |
| `se` | Measurement SE, `sd / sqrt(n_eff)`; missing when no range was found |
| `sd` | Pixel SD of the change; used only for one sensitivity fill |
| `flag_no_range` | True where `se` is missing |

Run these checks on load and stop with a clear message if any fail:

- Each index × month × τ subset has exactly 42 rows (7 sites × 6 pairs), with no duplicate site × pair.
- `year_end = year_start + 1` for every row.
- `se` is missing exactly where `flag_no_range` is true; `mean_change` is never missing.
- At τ = 0.05 there are 22 flagged rows in total (5 each in May, September and November; 7 in January). That count is for NDVI; counts for the other indices are not yet known. Report the count for every index; a different NDVI count is a warning, not an error.

## Main model

For one month and one τ, the 42 observations are site *s* × year pair *t*:

```latex
\Delta_{s,t} = \alpha_s + \gamma_t + \beta \, D^{23\text{–}24}_{s,t} + \beta' \, D^{24\text{–}25}_{s,t} + u_{s,t} + e_{s,t}
```

- Δ is `mean_change`.
- α\_s are site fixed effects (7 sites, one dropped as reference). In a change model these are each site's typical year-to-year drift.
- γ\_t are year-pair fixed effects (6 pairs, one dropped). They absorb what all sites shared that year.
- D^23–24 is 1 only for Wadi Gaza in 2023–24; D^24–25 is 1 only for Wadi Gaza in 2024–25. β is the estimate of interest; β′ is reported as the persistence estimate.
- u is real site-year variation with variance σ\_u², estimated from the data.
- e is measurement error with known variance `se²`.

That gives 14 parameters (intercept, 6 site, 5 pair, 2 indicators) and 28 residual degrees of freedom.

**Fitting steps:**

1. **Fill missing SEs** with the largest non-missing `se` in the same month × τ subset. Record which rows were filled.
2. **Fit ordinary least squares** on the same design. Take the residual variance s² = RSS / df.
3. **Estimate σ\_u²** by subtracting average measurement variance from s², using all rows except Wadi Gaza 2023–24:

```latex
\hat\sigma_u^2 = \max\left(0,\; s^2 - \overline{se^2}\right)
```

4. **Weight** each row by w = 1 / (σ\_u² + se²).
5. **Fit weighted least squares** with the weights treated as known inverse variances, so the covariance is (XᵀWX)⁻¹ with no extra scale factor:

```latex
\hat\theta = (X^\top W X)^{-1} X^\top W y, \qquad \operatorname{Cov}(\hat\theta) = (X^\top W X)^{-1}
```

6. **Report** β and β′ with SE, a 95% CI using t with 28 df, a two-sided p-value, σ\_u, df, and the number of filled SEs. If σ\_u² is clipped to zero, log a warning: it means the SEs exceed the total scatter.

Reference implementation of steps 2–6 (`X` holds the intercept, site and pair dummies, and both indicators; `treated` marks the Wadi Gaza 2023–24 row):

```python
import numpy as np
from scipy import stats

def fit_weighted(X, y, se, treated, term_idx):
    n, k = X.shape
    dof = n - k
    b_ols = np.linalg.lstsq(X, y, rcond=None)[0]
    s2 = ((y - X @ b_ols) ** 2).sum() / dof
    sigma_u2 = max(0.0, s2 - (se[~treated] ** 2).mean())
    w = 1.0 / (sigma_u2 + se ** 2)
    XtW = X.T * w
    cov = np.linalg.inv(XtW @ X)
    b = cov @ XtW @ y
    est, sd_b = b[term_idx], np.sqrt(cov[term_idx, term_idx])
    t_crit = stats.t.ppf(0.975, dof)
    p = 2 * stats.t.sf(abs(est / sd_b), dof)
    return est, sd_b, est - t_crit * sd_b, est + t_crit * sd_b, p, np.sqrt(sigma_u2), dof
```

Optional cross-check: R's `metafor::rma(yi, sei = se, mods = ~ factor(site) + factor(pair) + d2324 + d2425, method = "REML", test = "knha")` fits the same model with a more formal σ\_u² estimate. Estimates should be close but not identical.

## Placebo tests

Both tests ask how large an estimate the same model produces where nothing happened. Run both for every month at τ = 0.05 with the largest-SE fill. Each refit re-estimates σ\_u² and the weights, excluding the indicated cell(s) from the σ\_u² step.

**Placebo-in-space (7 estimates).**

1. Wadi Gaza's real β comes from the main model.
2. For each of the six comparison sites: drop all Wadi Gaza rows (leaving 36 rows), put both indicators on that site's 2023–24 and 2024–25 cells, refit, and record its β for 2023–24. Design: 13 parameters, 23 df.
3. One-sided p-value (the hypothesis is a decline, specified in advance): the number of the seven estimates that are less than or equal to Wadi Gaza's, divided by 7. The smallest possible value is 1/7 ≈ 0.14, so also report the ratio of Wadi Gaza's β to the largest absolute placebo β.

**Placebo-in-space-and-time (35 estimates).**

1. Drop the 2024–25 pair entirely, leaving 7 sites × 5 pairs = 35 rows (2019–20 through 2023–24).
2. Real estimate: one indicator on Wadi Gaza 2023–24, fit on all 35 rows. Design: 12 parameters, 23 df.
3. Placebos: drop the Wadi Gaza 2023–24 row (leaving 34 rows). For each of those 34 cells, put a single indicator on that cell, refit, and record β. This includes Wadi Gaza's own pre-event pairs and every comparison site's 2023–24 cell.
4. One-sided p-value: (1 + the number of placebo estimates ≤ the real estimate) / 35. The smallest possible value is 1/35 ≈ 0.029.

Output every placebo estimate, not just the p-value, so the distribution can be plotted against the real estimate.

## Sensitivity reruns

Rerun the main model only (not the placebos) for every month under these variants, changing one thing at a time from the primary setup (τ = 0.05, largest-SE fill):

| Variant | What changes |
| --- | --- |
| τ = 0.02 | Use the `tau == 0.02` rows; fill as primary |
| τ = 0.10 | Use the `tau == 0.10` rows; fill as primary |
| Exclude flagged | Drop rows with missing `se` instead of filling. If Wadi Gaza 2024–25 is dropped, remove the D^24–25 column for that month |
| n\_eff = 5 fill | Fill missing `se` with `sd / sqrt(5)` from the same row |

The purpose is to show the conclusion does not depend on the τ threshold or on how pairs without a range are handled.

## Validation targets

These values come from a reference run of exactly this specification on the current `results.csv`. The script should reproduce them to within ±0.001. A mismatch means the design, the fill or the σ\_u² step differs from this brief. Targets exist for NDVI only: validate the code on NDVI, then run the other indices unchanged.

**Main model (τ = 0.05, largest-SE fill, 28 df):**

| Month | β, 2023–24 (95% CI) | p | β′, 2024–25 (95% CI) | σ\_u |
| --- | --- | --- | --- | --- |
| January | −0.099 (−0.268, 0.071) | 0.24 | −0.090 (−0.255, 0.075) | 0.0628 |
| May | −0.095 (−0.141, −0.049) | 2.2×10⁻⁴ | −0.039 (−0.087, 0.008) | 0.0149 |
| September | −0.111 (−0.161, −0.061) | 9.5×10⁻⁵ | −0.044 (−0.094, 0.006) | 0.0100 |
| November | −0.132 (−0.195, −0.070) | 1.7×10⁻⁴ | −0.015 (−0.077, 0.048) | 0.0177 |

**Placebo tests:**

| Month | Space: comparison-site range | Space p | WG ÷ largest placebo | Space-and-time real β | Space-and-time placebo range | Space-and-time p |
| --- | --- | --- | --- | --- | --- | --- |
| January | −0.078 to +0.137 | 0.143 | 0.7 | −0.096 | −0.121 to +0.137 | 0.086 |
| May | −0.030 to +0.022 | 0.143 | 3.1 | −0.095 | −0.036 to +0.049 | 0.029 |
| September | −0.014 to +0.019 | 0.143 | 5.9 | −0.111 | −0.029 to +0.043 | 0.029 |
| November | −0.019 to +0.019 | 0.143 | 6.8 | −0.132 | −0.072 to +0.058 | 0.029 |

**Sensitivity, β for 2023–24 (95% CI):**

| Month | τ = 0.02 | τ = 0.10 | Exclude flagged (df) | n\_eff = 5 fill |
| --- | --- | --- | --- | --- |
| January | −0.100 (−0.268, 0.067) | −0.099 (−0.267, 0.069) | −0.087 (−0.256, 0.081) (21) | −0.098 (−0.265, 0.069) |
| May | −0.095 (−0.141, −0.048) | −0.094 (−0.138, −0.049) | −0.096 (−0.144, −0.048) (23) | −0.095 (−0.139, −0.052) |
| September | −0.113 (−0.160, −0.066) | −0.109 (−0.158, −0.061) | −0.112 (−0.163, −0.061) (24) | −0.112 (−0.161, −0.062) |
| November | −0.132 (−0.192, −0.072) | −0.131 (−0.193, −0.070) | −0.132 (−0.196, −0.067) (24) | −0.132 (−0.190, −0.073) |

## Outputs, conventions and open decisions

**Outputs.** Write four CSVs plus a short summary, each row tagged with index, a `role` column (primary for NDVI, robustness for the others), month, τ, fill method and a `supplementary` flag (true for January):

| File | One row per |
| --- | --- |
| `did_main.csv` | Month × variant × term (β, β′): estimate, SE, CI, p, σ\_u, df, filled-SE count, σ\_u-clipped warning |
| `did_placebo_space.csv` | Month × site: estimate, real/placebo label; plus p and ratio per month |
| `did_placebo_spacetime.csv` | Month × cell: site, pair, estimate, real/placebo label; plus p per month |
| `did_summary.md` | Index × month: the main-model row and both placebo p-values, in plain text |

**Conventions.** Follow the repository's existing pattern: run settings (input path, index, months, τ values, affected site, event pairs) in a config file alongside `configs/change_ci.yaml`, not hard-coded. Use the same Python stack as the upstream code. Add a test that runs the validation targets above.

**Known issue, not for this script.** Holot Nizzanim's pixel count is about 119,600–119,900, versus 139,638 footprint pixels in the imagery white paper. It does not affect this model, which uses site means, but the PI is reconciling it separately.

**Open decisions for the PI** (the script should not resolve these, only make them easy to change in config):

- [ ] Event timing for November. The indicators treat 2023–24 as the first affected pair in every month. If the disturbance began in October 2023, November 2023 is already post-onset; the data show no drop from November 2022 to 2023, so the current coding is consistent with the data.
- [ ] Whether to report the space-and-time placebo in the main text or the supplement.

## Update (2026-11-09): two model specifications

The PI requested the full pipeline (main model, both placebo tests, sensitivity reruns) for **two model specifications**, for all four indices and all four months, including January, with every output row labeled with its model:

1. **Site + period model** (`site_period`, the specification above). Intercept, 6 site effects, 5 year-pair effects, and the two Wadi Gaza indicators (2023–24 and 2024–25): 14 parameters, 28 residual df.
2. **Period-only model** (`period_only`, new). The same without site effects: intercept, 5 year-pair effects, and the two indicators: 8 parameters, 34 residual df.

Everything else about fitting and inference (weights, missing-SE fill, CIs, placebo and sensitivity procedures) is unchanged. The placebos use the same model as the run they belong to.

**Change to Step 3 (σ̂\_u², both models).** When computing σ̂\_u² = max(0, s² − mean(SE²)), exclude *both* Wadi Gaza post-event rows (2023–24 and 2024–25) from the mean of SE², not just 2023–24. Both rows are fit exactly by their own indicators, so neither contributes to s². The implementation applies the same rule to the placebo refits: every cell with its own indicator is excluded from mean(SE²).

**Coding for reporting.** Site and year-pair effects are reported with deviation (sum-to-zero) coding, so each effect is relative to the average site or year pair; the omitted level's effect is minus the sum of the block's coefficients. The event terms β and β′ are identical under either coding. Joint Wald F-tests (b′S⁻¹b/q against F(q, residual df)) are reported for the site effects (site + period model only) and for the year-pair effects.

**Summary table, one per model per index** (columns January, May, September, November): site effects, one row per site (site + period model only) plus the joint-test p-value; year-pair effects, one row per pair plus the joint-test p-value; β (2023–24) and β′ (2024–25), each with its 95% CI; σ\_u. Estimates to three decimals, with an asterisk where the 95% CI excludes zero. Each table is saved as `did_summary_<model>.csv` (formatted and numeric columns) and rendered in `did_summary.md`; the tidy per-effect rows are in `did_effects.csv`.

**Validation targets** (NDVI, τ = 0.05, largest-SE fill, with the σ̂\_u² change). These replace the main-model targets above; the earlier placebo and sensitivity targets no longer apply exactly, so the new values are reported rather than matched.

| Month | Site + period β (95% CI) | Period-only β (95% CI) |
| --- | --- | --- |
| January | −0.099 (−0.268, 0.071) | −0.088 (−0.234, 0.058) |
| May | −0.095 (−0.141, −0.049) | −0.082 (−0.123, −0.040) |
| September | −0.111 (−0.162, −0.060) | −0.101 (−0.148, −0.053) |
| November | −0.132 (−0.195, −0.069) | −0.128 (−0.185, −0.072) |
