# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair estimates are relative to their respective averages. An asterisk marks estimates whose 95% confidence interval excludes zero.

The models use weighted regression to account for uncertainty in the estimated index changes, and report 95% confidence intervals and joint checks of site and year-pair effects.

## SAVI (robustness)

### Site + period model

**Caption.** SAVI site effects, year-pair effects, and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the site + period model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of SAVI change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. Site and year-pair estimates are relative to their respective averages. The site joint p-value checks whether sites differ overall in average change, after accounting for year-to-year differences. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The site tests did not indicate an overall difference among sites in these months. The year-pair tests indicated differences among years in January, May, September, supporting the use of year-to-year adjustments for those months. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 0.006 | 0.001 | 0.001 | -0.000 |
| BesorStream | -0.023 | -0.001 | -0.000 | 0.000 |
| HaBesorNationalPark | -0.002 | -0.001 | -0.001 | 0.000 |
| HolotNizzanim | 0.007 | -0.002 | -0.001 | 0.000 |
| HolotPalmahim | 0.005 | -0.001 | -0.001 | -0.000 |
| NahalRubin | 0.003 | -0.005 | -0.003 | -0.001 |
| WadiGaza | 0.005 | 0.009 | 0.006 | 0.001 |
| Joint p (sites) | 0.944 | 0.782 | 0.694 | 1.000 |
| 2019–20 | -0.037* | 0.013* | -0.001 | 0.006 |
| 2020–21 | 0.035* | -0.008 | 0.006* | -0.009* |
| 2021–22 | 0.018 | 0.005 | 0.003 | 0.003 |
| 2022–23 | 0.003 | 0.009* | -0.001 | 0.008 |
| 2023–24 | 0.036 | -0.005 | 0.003 | -0.005 |
| 2024–25 | -0.054* | -0.014* | -0.010* | -0.002 |
| Joint p (year pairs) | 0.007 | 0.002 | 0.033 | 0.072 |
| beta (2023–24) (95% CI) | -0.084 (-0.208, 0.039) | -0.078 (-0.113, -0.044)* | -0.079 (-0.111, -0.047)* | -0.072 (-0.106, -0.037)* |
| beta' (2024–25) (95% CI) | -0.030 (-0.152, 0.093) | -0.026 (-0.060, 0.008) | -0.028 (-0.060, 0.004) | -0.005 (-0.033, 0.024) |
| sigma_u | 0.047 | 0.011 | 0.007 | 0.011 |

### Period only model

**Caption.** SAVI year-pair effects and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the period-only model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of SAVI change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. This model has no site effects, so the shared year-pair changes are the only baseline. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The year-pair tests indicated differences among years in every listed month, supporting the use of year-to-year adjustments. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| 2019–20 | -0.037* | 0.014* | -0.001 | 0.006 |
| 2020–21 | 0.035* | -0.007 | 0.006* | -0.009* |
| 2021–22 | 0.018 | 0.006 | 0.003 | 0.003 |
| 2022–23 | 0.003 | 0.009* | -0.001 | 0.008* |
| 2023–24 | 0.035* | -0.006 | 0.003 | -0.005 |
| 2024–25 | -0.054* | -0.015* | -0.011* | -0.003 |
| Joint p (year pairs) | 0.003 | 0.000 | 0.009 | 0.033 |
| beta (2023–24) (95% CI) | -0.078 (-0.183, 0.026) | -0.068 (-0.098, -0.037)* | -0.072 (-0.102, -0.042)* | -0.071 (-0.101, -0.041)* |
| beta' (2024–25) (95% CI) | -0.025 (-0.129, 0.078) | -0.015 (-0.046, 0.015) | -0.020 (-0.050, 0.010) | -0.003 (-0.027, 0.020) |
| sigma_u | 0.044 | 0.011 | 0.007 | 0.010 |

### Event estimates and placebo tests

**Caption.** SAVI event and persistence estimates with their t-test p-value, sigma_u, and placebo-in-space and placebo-in-space-and-time p-values, by model specification and calendar month.

**Explanation.** The table repeats beta (2023–24) and beta' (2024–25) from the model tables above with 95% CIs, adds the two-sided t-test p-value for beta, and adds two placebo diagnostics. Space placebos reassign the event and persistence indicators to comparison sites after excluding WadiGaza. Space-and-time placebos omit the 2024–25 pair and reassign a single event indicator among unaffected site-year-pair cells, excluding the real event cell from each placebo fit. Both placebo p-values are lower-tail rank proportions for a decline, including the real assignment, so the smallest attainable value is one over the number of ranked assignments. The space-and-time p-value uses its own reduced-sample real refit, which can differ from the main estimate. Interpreting the ranks inferentially requires comparable assignments; treat them as a diagnostic alongside the model interval.

| Model | Month | beta 2023–24 (95% CI) | p | beta' 2024–25 (95% CI) | sigma_u | Placebo-space p | Placebo-space-time p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Site + period | January (supplementary) | -0.084 (-0.208, 0.039) | 0.17 | -0.030 (-0.152, 0.093) | 0.0468 | 0.143 | 0.057 |
| Site + period | May | -0.078 (-0.113, -0.044) | 7.4e-05 | -0.026 (-0.060, 0.008) | 0.0115 | 0.143 | 0.029 |
| Site + period | September | -0.079 (-0.111, -0.047) | 2.3e-05 | -0.028 (-0.060, 0.004) | 0.0074 | 0.143 | 0.029 |
| Site + period | November | -0.072 (-0.106, -0.037) | 0.0002 | -0.005 (-0.033, 0.024) | 0.0113 | 0.143 | 0.029 |
| Period only | January (supplementary) | -0.078 (-0.183, 0.026) | 0.14 | -0.025 (-0.129, 0.078) | 0.0438 | 0.143 | 0.057 |
| Period only | May | -0.068 (-0.098, -0.037) | 7.8e-05 | -0.015 (-0.046, 0.015) | 0.0109 | 0.143 | 0.029 |
| Period only | September | -0.072 (-0.102, -0.042) | 2.8e-05 | -0.020 (-0.050, 0.010) | 0.0070 | 0.143 | 0.029 |
| Period only | November | -0.071 (-0.101, -0.041) | 2.7e-05 | -0.003 (-0.027, 0.020) | 0.0102 | 0.143 | 0.029 |
