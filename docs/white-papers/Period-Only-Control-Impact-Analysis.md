# Testing Whether Wadi Gaza's Index Change Was Anomalous: A Period-Only Comparison Analysis

Nov 9, 2026 · @Tariq

## 1. Purpose

This document describes how the study tests whether the change in a vegetation index at Wadi Gaza between 2023 and 2024 was anomalous, using a simplified **period-only** model specification. "Anomalous" here means the change differs from what all sites shared in the same period, judged against how far individual sites ordinarily depart from the shared change.

This paper is a companion to *Testing Whether Wadi Gaza's Index Change Was Anomalous: A Before-After-Control-Impact Analysis*, which describes the fuller **site + period** specification. The two papers share data, estimation machinery, placebo tests, and sensitivity checks; they differ in one modeling choice. The site + period model gives each site its own typical year-to-year drift; the period-only model does not, so each site's expected change in a year pair is simply that pair's shared change. Dropping the site effects trades six parameters for six residual degrees of freedom and treats any persistent site-specific drift as part of the ordinary site-year variation. Both specifications are run in full, and every output row is labeled with its model.

The analysis builds on Confidence Intervals for Mean Index Change Under Spatial Autocorrelation. That method produces, for each site and pair of years, a mean change and a standard error adjusted for spatial autocorrelation. Its confidence intervals answer whether a site changed. They cannot answer whether one site's change was unusual compared with others, which is the study's central question. This document describes the comparison that answers it.

The current executable run settings are maintained in `configs/change_did.yaml`; this paper documents the methodology and rationale without duplicating that configuration.

## 2. Scope and Data

**Sites.** Wadi Gaza is the affected site. The six comparison sites are Al Ahrash Protectorate, Besor Stream, HaBesor National Park, Holot Nizzanim, Holot Palmahim, and Nahal Rubin (Imagery Acquisition and Preparation, Section 2).

**Indices.** NDVI is the primary index. GNDVI, SAVI, and NDRE are analyzed the same way as robustness checks.

**Months.** Each month is analyzed separately: May, September, and November in the main analysis, and January as a supplementary analysis. January index values in this region are driven largely by the timing and amount of wet-season rain. Their year-to-year variation at every site is three to five times that of the other months, which makes a change of the expected size hard to detect.

**Year pairs.** Six consecutive pairs are used: 2019–20, 2020–21, 2021–22, 2022–23, 2023–24, and 2024–25. The first four are the baseline. 2023–24 is the event pair, the first pair spanning the event period. 2024–25 is the persistence pair, which shows whether the change continued, held, or reversed.

**Inputs.** For each site, month, and year pair, the input is taken from the confidence-interval analysis: the mean change in the index, its standard error adjusted for spatial autocorrelation, and a flag for pairs where no autocorrelation range was found. Each month and index therefore contributes 42 observations (7 sites × 6 year pairs).

## 3. Notation

| Symbol | Meaning |
| --- | --- |
| s | A site |
| t | A year pair |
| Δ\_{s,t} | Mean index change at site s for year pair t (the input mean change) |
| SE\_{s,t} | Standard error of Δ\_{s,t}, adjusted for spatial autocorrelation: s\_D / √n\_eff |
| γ\_t | Year-pair effect |
| E\_{s,t} | Event indicator: 1 for Wadi Gaza in 2023–24, otherwise 0 |
| P\_{s,t} | Persistence indicator: 1 for Wadi Gaza in 2024–25, otherwise 0 |
| β | Event effect: Wadi Gaza's departure from the shared change in 2023–24 |
| β′ | Persistence effect: the same departure in 2024–25 |
| u\_{s,t} | Real site-year variation not explained by the model |
| σ\_u² | Variance of u |
| e\_{s,t} | Measurement error in Δ\_{s,t}, with variance SE\_{s,t}² |
| w\_{s,t} | Weight of each observation |
| ν | Degrees of freedom |

There is no site effect α\_s in this specification; that is the single difference from the companion paper. The symbol τ keeps its meaning from the confidence-interval paper: the near-zero threshold that defines the autocorrelation range. It is not used for any quantity in this model.

## 4. Method

### 4.1 Design

The analysis compares the change at the impact site with the change shared by all sites over the same period, and checks that comparison against the same comparison in baseline years. This is the classical difference-in-differences design under a common-trend assumption: because the outcome is already a change, modeling only shared period effects corresponds, in index levels, to assuming all sites follow a common trend apart from their own year-to-year variation (Stewart-Oaten et al., 1986; Underwood, 1991). The companion site + period model relaxes this by allowing each site its own linear trend.

In its simplest form, the design subtracts the sites' shared change from Wadi Gaza's change, for every year pair. In baseline years that difference should be near zero, up to ordinary site-year variation. An effect appears as a 2023–24 difference that is far outside the baseline differences. The model in Section 4.3 performs this comparison for all sites and years at once and provides a confidence interval.

The unit of analysis is the site-year: one site's mean change for one year pair. Pixels are not observations in this model. Spatial autocorrelation among pixels therefore cannot inflate the number of observations; it enters only through each site-year's standard error (Section 4.2).

### 4.2 Observations and their uncertainty

Each site-year mean change carries two kinds of uncertainty:

- **Measurement uncertainty.** How precisely the pixels determine the site's mean change. This is the standard error from the confidence-interval analysis, SE\_{s,t} = s\_D / √n\_eff, which accounts for spatial autocorrelation through the effective sample size.
- **Real site-year variation.** Site means differ from year to year for reasons the model does not capture, such as local rainfall, grazing, or management. In this specification, any persistent site-specific drift is also part of this variation. Its variance, σ\_u², is estimated from the data.

The total variance of an observation is the sum of the two. Observations measured less precisely receive less weight, and their uncertainty carries into the confidence interval (Section 4.4).

### 4.3 Model

For one index and one month, the 42 observations are modeled as:

```latex
\Delta_{s,t} = \gamma_t + \beta E_{s,t} + \beta' P_{s,t} + u_{s,t} + e_{s,t} \tag{1}
```

- The **year-pair effect** γ\_t is the change shared by all sites in that pair, for example a regionally wet or dry year.
- The **event effect** β measures how far Wadi Gaza's 2023–24 change departs from that year's shared change. It is the main quantity of interest.
- The **persistence effect** β′ measures the same departure for 2024–25. Giving 2024–25 its own indicator also keeps a possibly affected year out of the baseline.

There are no site effects: a site's expected change in any pair is the pair's shared change. A site that persistently greens or browns a little every year is not modeled separately; that drift is absorbed by the site-year variation u.

The model has 8 parameters: an intercept, 5 year-pair effects (one pair serves as reference), β, and β′. With 42 observations, ν = 42 − 8 = 34 degrees of freedom.

For reporting, the year-pair effects use deviation (sum-to-zero) coding, so each reported effect is relative to the average year pair, and a joint Wald F-test of the year-pair effects is reported alongside them. β and β′ are identical under either coding.

### 4.4 Estimation

The model is fit in three steps.

**Step 1: estimate the real site-year variation.** Equation (1) is first fit by ordinary least squares. The Hedges method-of-moments estimator for meta-regression removes the expected measurement-error contribution from the residual sum of squares (Hedges, 1992; Viechtbauer, 2010):

```latex
\hat\sigma_u^2 = \max\left(0,\;
\frac{\mathrm{RSS} - \sum_i (1-h_i)SE_i^2}{n-k}\right),
\qquad H = X(X^\top X)^{-1}X^\top,\quad h_i = H_{ii} \tag{2}
```

Here i indexes site-year observations, n is their number, k is the full-rank design's parameter count, and hᵢ is each observation's unweighted OLS leverage. The correction accounts for unequal measurement variances and unequal leverages. Wadi Gaza's event and persistence cells are fit exactly by their own indicators: their leverages are one, so they contribute neither residual scatter nor measurement variance to this estimate. Negative estimates are set to zero and flagged (Section 5).

Under the model's independent-error assumptions, the expected residual sum of squares is (n − k)σ\_u² + Σᵢ(1 − hᵢ)SEᵢ². Equation (2) subtracts that measurement-error contribution; it replaces the arithmetic-mean variance subtraction used in the initial implementation.

**Step 2: weight each observation by its total variance.**

```latex
w_{s,t} = \frac{1}{\hat\sigma_u^2 + SE_{s,t}^2} \tag{3}
```

**Step 3: fit by weighted least squares.** These inverse estimated total-variance weights are treated as fixed for coefficient inference. The coefficients and their conditional covariance are:

```latex
\hat\theta = (X^\top W X)^{-1} X^\top W \Delta, \qquad \operatorname{Cov}(\hat\theta) = (X^\top W X)^{-1} \tag{4}
```

Here X holds the intercept, year-pair effects, and the two indicators; W is the diagonal matrix of weights; and Δ is the vector of 42 mean changes. The standard error of β̂ is the square root of its diagonal entry in the covariance.

This approach comes from meta-regression, combining estimates with supplied standard errors while allowing residual heterogeneity. OLS and WLS are implemented with statsmodels (Seabold & Perktold, 2010), using `cov_type="fixed scale"`, `cov_kwds={"scale": 1.0}`, and `use_t=True`. This avoids the additional residual-scale multiplier used by default WLS. Statsmodels also supplies linear contrasts and joint Wald F-tests. The installed software version and estimation settings are recorded in each output's `config.json`; the implementation was validated with statsmodels 0.15.0.

All 1,472 configured main, sensitivity, and placebo fits were independently reproduced with R 4.3.3 and metafor 4.4-0 using `method="HE"` and `test="t"`. Variance components, coefficients, covariance matrices, intervals, and tests agreed to floating-point precision. This is an implementation cross-check, not evidence that the inferential assumptions hold.

**Pairs without a range.** Where the confidence-interval analysis found no autocorrelation range, the effective sample size and standard error are undefined. These observations are kept, because their mean changes are valid, and given the largest standard error observed for that index and month. This gives them low weight without discarding them.

### 4.5 Confidence interval

The (1 − α) confidence interval for the event effect is:

```latex
\mathrm{CI} = \hat\beta \pm t_{1-\alpha/2,\,\nu} \cdot SE(\hat\beta), \qquad \alpha = 0.05, \; \nu = 34 \tag{5}
```

The same form gives the interval for β′. A two-sided p-value is reported for each. The 34 degrees of freedom apply to the complete primary design; sensitivity and placebo refits use their actual n − k. This is plug-in t inference, not a Knapp–Hartung adjustment or heteroskedasticity-, autocorrelation-, or cluster-robust covariance estimate.

### 4.6 Placebo tests

The confidence interval in Section 4.5 relies on the model's assumptions about variation, in particular that Wadi Gaza's year-to-year variation resembles the other sites'. Placebo tests assess how unusual the fitted effect is relative to effects assigned to unaffected sites and years. Interpreting their ranks as inferential p-values still requires comparability or exchangeability of those assignments; they are not assumption-free causal tests (Abadie et al., 2010).

Both tests are one-sided, because the study hypothesis, set before analysis, is a decline. Each refit repeats the full estimation in Section 4.4 with the same period-only model.

**Placebo in space.** Each comparison site is treated, in turn, as if it were the affected site:

1. Remove Wadi Gaza's observations, since it may truly be affected.
2. Place the event and persistence indicators on the chosen comparison site's 2023–24 and 2024–25 observations.
3. Fit the model and record that site's event estimate.

This gives six placebo estimates to compare with Wadi Gaza's real estimate. The p-value is the share of the seven estimates that are as negative as Wadi Gaza's or more so. With seven sites, the smallest possible p-value is 1/7 ≈ 0.14, even for an extreme result. The test is therefore also summarized by the ratio of Wadi Gaza's estimate to the largest placebo estimate in absolute value.

**Placebo in space and time.** Fake events are placed on every unaffected site-year, which gives a larger set of placebos:

1. Use the five year pairs from 2019–20 through 2023–24 (35 observations). The 2024–25 pair is left out.
2. Fit the model with a single indicator on Wadi Gaza in 2023–24 to obtain the real estimate.
3. Remove the Wadi Gaza 2023–24 observation. For each of the remaining 34 site-years, fit the model with a single indicator on that site-year and record its estimate. This includes Wadi Gaza's own baseline years and every comparison site's 2023–24.

The p-value is (1 + the number of placebo estimates as negative as the real one or more) / 35. Its smallest possible value is 1/35 ≈ 0.029.

The placebo in space is particularly informative for this specification: if some comparison site had a persistent drift large enough to matter, treating that site as affected would produce a large placebo estimate, and the real estimate would no longer stand out.

## 5. Sensitivity and Quality Checks

**Sensitivity.** The model in Sections 4.3–4.5 is refit under four variants, each changing one choice from the primary setup:

- the autocorrelation range threshold τ = 0.02 instead of 0.05;
- τ = 0.10;
- pairs without a range excluded rather than given the largest standard error;
- pairs without a range given a standard error that assumes n\_eff = 5.

For NDVI in May, September, and November, these variants changed the event estimate by at most 0.002, and every interval remained well below zero. The conclusion does not depend on the threshold or on the handling of pairs without a range.

**Checks on load.** The analysis stops if any index-month subset does not contain exactly 42 observations (7 sites × 6 consecutive pairs) or if any mean change is missing. It reports how many observations had no range.

**Flags.** An estimate is flagged when σ\_u² in Equation (2) is set to zero, which means the measurement standard errors are as large as all the scatter in the data.

## 6. Interpreting the Results

**Event effect (β).** β is in index units. A negative β means Wadi Gaza's index fell by that much more in 2023–24 than that year's shared change predicts. If its confidence interval excludes zero, the departure is larger than both measurement uncertainty and ordinary site-year variation can explain.

**Persistence effect (β′).** β′ shows what happened in the following year, relative to expectation. A recovery would appear as a positive β′. A β′ near zero means the change held without recovering. A negative β′ means the decline continued beyond expectation.

**Placebo tests.** These show whether an estimate of Wadi Gaza's size ever occurs where nothing happened. A placebo p-value at its floor (1/7 or 1/35) means Wadi Gaza's estimate is the most extreme of all those tested; the floor reflects the number of sites and years, not weak evidence. The ratio to the largest placebo shows how far outside the range of ordinary estimates the real one lies.

**Relation to the site + period model.** The two specifications bracket the treatment of site-specific drift: the site + period model removes it through fixed effects, while the period-only model counts it as ordinary variation. When both produce similar event estimates with intervals excluding zero, the conclusion does not depend on that modeling choice. For NDVI, the two specifications' estimates differ by at most 0.013 in any month, and the site + period model's joint test of its site effects never rejects (p ≥ 0.68), consistent with site drifts too small to matter.

**Relation to the per-pair confidence intervals.** The intervals from the confidence-interval paper show whether each site changed in each pair. Because site means are measured precisely, even small baseline changes can have intervals that exclude zero. Those intervals describe measurement precision. Whether Wadi Gaza's change was unusual is answered by β and the placebo tests, not by the per-pair intervals.

**Months and indices.** May, September, and November use the same pixels and the same years, so agreement among them is a consistent pattern, not three independent confirmations. Agreement across indices strengthens the result, since each index responds differently to vegetation and soil. A January result that does not exclude zero reflects that month's rain-driven variability, not evidence that no change occurred.

**What the analysis does and does not show.** It shows whether Wadi Gaza's change was unusual relative to the comparison sites and to its own history. It does not by itself identify the cause. Attribution rests on supporting evidence: the timing of the change, its spatial pattern within the site, and climate records.

**Example: NDVI, September.**

| Output | Value | Reading |
| --- | --- | --- |
| Event effect β (95% CI) | −0.101 (−0.148, −0.053), p < 0.001 | NDVI fell about 0.10 more than expected in 2023–24 |
| Persistence effect β′ (95% CI) | −0.034 (−0.082, 0.014) | No recovery in 2024–25; possibly a further decline |
| Placebo in space | Comparison sites −0.011 to +0.014; p = 1/7; ratio 7.1 | Wadi Gaza is the most extreme site, about seven times the largest placebo |
| Placebo in space and time | 34 placebos −0.023 to +0.034; p = 1/35 | Wadi Gaza 2023–24 is more negative than every other site-year |

## 7. Assumptions and Notes

**Expected change.** Without the event, Wadi Gaza's 2023–24 change would have equaled that year's shared regional change. The baseline years support this: in them, every site's change stays close to the shared change for its pair. In index levels, this corresponds to assuming all sites follow a common trend.

**No persistent site drift.** The specification assumes no site drifts steadily enough for a site-specific trend to matter. Persistent drift that does exist is not removed; it widens σ\_u² and therefore the confidence interval, making the test conservative in that respect. The companion site + period model removes drift explicitly; for NDVI its site effects are jointly indistinguishable from zero, which supports this simplification.

**Unaffected comparison sites.** The comparison sites are assumed not to be affected by the event. If they were, the estimate would understate the effect.

**No coinciding local event.** No other site-specific event is assumed to have changed Wadi Gaza's index by a similar amount in the same year. Local events at ordinary sites, such as restoration or grazing changes, are part of the site-year variation σ\_u². The placebo-in-space estimates show their typical size.

**Similar variation across sites.** The confidence interval assumes the real site-year variation σ\_u² is the same at every site. Placebo ranks provide a complementary diagnostic but require comparable site-year assignments for inferential interpretation.

**Plug-in uncertainty and dependence.** Coefficient covariance treats the estimated σ\_u² and supplied spatial SEs as fixed; their estimation uncertainty is not fully propagated. The diagonal variance model assumes independent residual site-year errors. Adjacent annual changes share a year and can be correlated, and spatial adjustment within a raster does not remove temporal or between-site dependence. Choosing t reference distributions does not by itself resolve these limitations or guarantee exact small-sample coverage.

**Shared weather between nearby sites.** The year-pair effect absorbs conditions shared by all sites. Correlation left between nearby sites would make the comparison sites act like somewhat fewer independent sites; the placebo tests are less affected by this.

**Sample size.** Each index-month has 42 observations and 34 degrees of freedom — six more than the site + period model, which slightly narrows the confidence intervals. There is still only one affected site, so the placebo p-values have the floors described in Section 4.6.

**Fixed footprints.** Each site uses one footprint in every window (Imagery Acquisition and Preparation, Section 6), so changes in the site means do not come from changes in site boundaries.

## 8. Reported Outputs

For each index and month, the reported outputs are:

- the event effect β and persistence effect β′, each with its standard error, 95% confidence interval, and p-value
- the deviation-coded year-pair effects with their joint Wald F-test p-value
- the estimated real site-year variation σ\_u, the degrees of freedom, the number of pairs without a range, and any flags
- the placebo-in-space estimates for all seven sites, the p-value, and the ratio of Wadi Gaza's estimate to the largest placebo
- the placebo-in-space-and-time estimates for all 35 site-years and the p-value
- the event effect under each sensitivity variant

Every output is labeled with its index (NDVI as primary; GNDVI, SAVI, and NDRE as robustness checks), marks January as supplementary, and carries the model label `period_only`. The same files hold the companion site + period rows under the label `site_period`.

| File | One row per |
| --- | --- |
| `did_main.csv` | Model × index × month × variant × effect (β or β′) |
| `did_effects.csv` | Model × index × month × fixed-effect level, plus the joint tests |
| `did_placebo_space.csv` | Model × index × month × site |
| `did_placebo_spacetime.csv` | Model × index × month × site-year |
| `did_summary_period_only.csv` | Index: the summary table for this model, months as columns |
| `did_summary.md` | Index: both models' summary tables and placebo p-values in plain text |

## References

Abadie, A., Diamond, A., & Hainmueller, J. (2010). Synthetic control methods for comparative case studies: Estimating the effect of California's tobacco control program. *Journal of the American Statistical Association*, 105(490), 493–505.

Hedges, L. V. (1992). Meta-analysis. *Journal of Educational Statistics*, 17(4), 279–296. https://doi.org/10.3102/10769986017004279

Seabold, S., & Perktold, J. (2010). statsmodels: Econometric and statistical modeling with Python. *Proceedings of the 9th Python in Science Conference*, 92–96.

Stewart-Oaten, A., Murdoch, W. W., & Parker, K. R. (1986). Environmental impact assessment: "Pseudoreplication" in time? *Ecology*, 67(4), 929–940.

Underwood, A. J. (1991). Beyond BACI: Experimental designs for detecting human environmental impacts on temporal variations in natural populations. *Australian Journal of Marine and Freshwater Research*, 42(5), 569–587.

Viechtbauer, W. (2010). Conducting meta-analyses in R with the metafor package. *Journal of Statistical Software*, 36(3), 1–48. https://doi.org/10.18637/jss.v036.i03

Verify reference details before publication. The HE estimator and inference settings are documented in the [metafor reference](https://wviechtb.github.io/metafor/reference/rma.uni.html); fixed-scale covariance is documented in the [statsmodels reference](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html).
