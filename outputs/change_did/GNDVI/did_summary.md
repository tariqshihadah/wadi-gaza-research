# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair estimates are relative to their respective averages. An asterisk marks estimates whose 95% confidence interval excludes zero.

The models use weighted regression to account for uncertainty in the estimated index changes, and report 95% confidence intervals and joint checks of site and year-pair effects.

## GNDVI (robustness)

### Site + period model

**Caption.** GNDVI site effects, year-pair effects, and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the site + period model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of GNDVI change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. Site and year-pair estimates are relative to their respective averages. The site joint p-value checks whether sites differ overall in average change, after accounting for year-to-year differences. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The site tests did not indicate an overall difference among sites in these months. The year-pair tests indicated differences among years in January, September, November, supporting the use of year-to-year adjustments for those months. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 0.007 | 0.003 | 0.001 | -0.000 |
| BesorStream | -0.020 | -0.003 | -0.002 | -0.000 |
| HaBesorNationalPark | -0.003 | -0.001 | -0.002 | -0.001 |
| HolotNizzanim | 0.004 | -0.002 | -0.000 | 0.000 |
| HolotPalmahim | 0.004 | -0.001 | -0.000 | -0.001 |
| NahalRubin | 0.003 | -0.004 | -0.002 | 0.001 |
| WadiGaza | 0.005 | 0.007 | 0.006 | 0.001 |
| Joint p (sites) | 0.948 | 0.972 | 0.986 | 1.000 |
| 2019–20 | -0.016 | 0.010 | 0.010 | 0.021* |
| 2020–21 | 0.017 | 0.004 | 0.007 | -0.014* |
| 2021–22 | 0.026 | 0.007 | 0.006 | 0.004 |
| 2022–23 | -0.011 | 0.007 | -0.006 | 0.010 |
| 2023–24 | 0.040* | -0.016* | -0.003 | -0.017* |
| 2024–25 | -0.055* | -0.012 | -0.014* | -0.005 |
| Joint p (year pairs) | 0.006 | 0.095 | 0.041 | 0.007 |
| beta (2023–24) (95% CI) | -0.080 (-0.192, 0.031) | -0.060 (-0.109, -0.010)* | -0.073 (-0.118, -0.029)* | -0.100 (-0.153, -0.046)* |
| beta' (2024–25) (95% CI) | -0.038 (-0.147, 0.071) | -0.014 (-0.064, 0.037) | -0.025 (-0.067, 0.017) | 0.005 (-0.041, 0.051) |
| sigma_u | 0.041 | 0.018 | 0.013 | 0.017 |

### Period only model

**Caption.** GNDVI year-pair effects and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the period-only model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of GNDVI change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. This model has no site effects, so the shared year-pair changes are the only baseline. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The year-pair tests indicated differences among years in every listed month, supporting the use of year-to-year adjustments. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| 2019–20 | -0.016 | 0.011 | 0.010* | 0.021* |
| 2020–21 | 0.017 | 0.005 | 0.007 | -0.013* |
| 2021–22 | 0.026 | 0.008 | 0.007 | 0.004 |
| 2022–23 | -0.010 | 0.007 | -0.005 | 0.010 |
| 2023–24 | 0.039* | -0.017* | -0.004 | -0.016* |
| 2024–25 | -0.055* | -0.014* | -0.015* | -0.005 |
| Joint p (year pairs) | 0.002 | 0.028 | 0.010 | 0.001 |
| beta (2023–24) (95% CI) | -0.075 (-0.170, 0.021) | -0.051 (-0.093, -0.010)* | -0.067 (-0.107, -0.027)* | -0.098 (-0.145, -0.052)* |
| beta' (2024–25) (95% CI) | -0.033 (-0.125, 0.060) | -0.005 (-0.048, 0.038) | -0.018 (-0.055, 0.019) | 0.007 (-0.031, 0.044) |
| sigma_u | 0.039 | 0.017 | 0.012 | 0.015 |

### Event estimates and placebo tests

**Caption.** GNDVI event and persistence estimates with their t-test p-value, sigma_u, and placebo-in-space and placebo-in-space-and-time p-values, by model specification and calendar month.

**Explanation.** The table repeats beta (2023–24) and beta' (2024–25) from the model tables above with 95% CIs, adds the two-sided t-test p-value for beta, and adds two placebo diagnostics. Space placebos reassign the event and persistence indicators to comparison sites after excluding WadiGaza. Space-and-time placebos omit the 2024–25 pair and reassign a single event indicator among unaffected site-year-pair cells, excluding the real event cell from each placebo fit. Both placebo p-values are lower-tail rank proportions for a decline, including the real assignment, so the smallest attainable value is one over the number of ranked assignments. The space-and-time p-value uses its own reduced-sample real refit, which can differ from the main estimate. Interpreting the ranks inferentially requires comparable assignments; treat them as a diagnostic alongside the model interval.

| Model | Month | beta 2023–24 (95% CI) | p | beta' 2024–25 (95% CI) | sigma_u | Placebo-space p | Placebo-space-time p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Site + period | January (supplementary) | -0.080 (-0.192, 0.031) | 0.15 | -0.038 (-0.147, 0.071) | 0.0413 | 0.143 | 0.057 |
| Site + period | May | -0.060 (-0.109, -0.010) | 0.019 | -0.014 (-0.064, 0.037) | 0.0184 | 0.143 | 0.029 |
| Site + period | September | -0.073 (-0.118, -0.029) | 0.0021 | -0.025 (-0.067, 0.017) | 0.0133 | 0.143 | 0.029 |
| Site + period | November | -0.100 (-0.153, -0.046) | 0.00071 | 0.005 (-0.041, 0.051) | 0.0172 | 0.143 | 0.029 |
| Period only | January (supplementary) | -0.075 (-0.170, 0.021) | 0.12 | -0.033 (-0.125, 0.060) | 0.0385 | 0.143 | 0.029 |
| Period only | May | -0.051 (-0.093, -0.010) | 0.017 | -0.005 (-0.048, 0.038) | 0.0169 | 0.143 | 0.029 |
| Period only | September | -0.067 (-0.107, -0.027) | 0.0016 | -0.018 (-0.055, 0.019) | 0.0122 | 0.143 | 0.029 |
| Period only | November | -0.098 (-0.145, -0.052) | 0.00014 | 0.007 (-0.031, 0.044) | 0.0153 | 0.143 | 0.029 |
