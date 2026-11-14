# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair estimates are relative to their respective averages. An asterisk marks estimates whose 95% confidence interval excludes zero.

The models use weighted regression to account for uncertainty in the estimated index changes, and report 95% confidence intervals and joint checks of site and year-pair effects.

## NDRE (robustness)

### Site + period model

**Caption.** NDRE site effects, year-pair effects, and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the site + period model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of NDRE change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. Site and year-pair estimates are relative to their respective averages. The site joint p-value checks whether sites differ overall in average change, after accounting for year-to-year differences. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The site tests did not indicate an overall difference among sites in these months. The year-pair tests indicated differences among years in every listed month, supporting the use of year-to-year adjustments. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 0.008 | 0.002 | 0.001 | 0.000 |
| BesorStream | -0.020 | -0.001 | -0.001 | -0.002 |
| HaBesorNationalPark | -0.005 | -0.002 | -0.002 | -0.002 |
| HolotNizzanim | 0.003 | -0.002 | -0.001 | -0.000 |
| HolotPalmahim | 0.003 | -0.001 | -0.001 | -0.001 |
| NahalRubin | 0.004 | -0.005 | -0.005 | 0.000 |
| WadiGaza | 0.006 | 0.008 | 0.009* | 0.005 |
| Joint p (sites) | 0.945 | 0.826 | 0.482 | 0.986 |
| 2019–20 | -0.024 | 0.010* | 0.009* | 0.015* |
| 2020–21 | 0.039* | -0.007 | -0.004 | -0.014* |
| 2021–22 | 0.001 | 0.006 | 0.004 | 0.004 |
| 2022–23 | 0.009 | 0.013* | 0.000 | 0.014* |
| 2023–24 | 0.038* | -0.008 | 0.004 | -0.015* |
| 2024–25 | -0.063* | -0.013* | -0.013* | -0.004 |
| Joint p (year pairs) | 0.002 | 0.003 | 0.004 | 0.000 |
| beta (2023–24) (95% CI) | -0.070 (-0.183, 0.044) | -0.069 (-0.104, -0.033)* | -0.093 (-0.133, -0.053)* | -0.113 (-0.161, -0.066)* |
| beta' (2024–25) (95% CI) | -0.090 (-0.201, 0.020) | -0.027 (-0.064, 0.010) | -0.033 (-0.074, 0.007) | -0.014 (-0.062, 0.033) |
| sigma_u | 0.041 | 0.012 | 0.008 | 0.011 |

### Period only model

**Caption.** NDRE year-pair effects and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the period-only model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of NDRE change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. This model has no site effects, so the shared year-pair changes are the only baseline. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The year-pair tests indicated differences among years in every listed month, supporting the use of year-to-year adjustments. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| 2019–20 | -0.024 | 0.010* | 0.010* | 0.015* |
| 2020–21 | 0.039* | -0.006 | -0.003 | -0.013* |
| 2021–22 | 0.001 | 0.007 | 0.005 | 0.005 |
| 2022–23 | 0.010 | 0.013* | 0.001 | 0.014* |
| 2023–24 | 0.036* | -0.009 | 0.002 | -0.016* |
| 2024–25 | -0.063* | -0.014* | -0.015* | -0.005 |
| Joint p (year pairs) | 0.001 | 0.000 | 0.001 | 0.000 |
| beta (2023–24) (95% CI) | -0.063 (-0.161, 0.036) | -0.059 (-0.090, -0.028)* | -0.083 (-0.121, -0.045)* | -0.108 (-0.152, -0.064)* |
| beta' (2024–25) (95% CI) | -0.084 (-0.179, 0.010) | -0.017 (-0.050, 0.016) | -0.023 (-0.061, 0.015) | -0.009 (-0.053, 0.035) |
| sigma_u | 0.038 | 0.011 | 0.008 | 0.010 |

### Event estimates and placebo tests

**Caption.** NDRE event and persistence estimates with their t-test p-value, sigma_u, and placebo-in-space and placebo-in-space-and-time p-values, by model specification and calendar month.

**Explanation.** The table repeats beta (2023–24) and beta' (2024–25) from the model tables above with 95% CIs, adds the two-sided t-test p-value for beta, and adds two placebo diagnostics. Space placebos reassign the event and persistence indicators to comparison sites after excluding WadiGaza. Space-and-time placebos omit the 2024–25 pair and reassign a single event indicator among unaffected site-year-pair cells, excluding the real event cell from each placebo fit. Both placebo p-values are lower-tail rank proportions for a decline, including the real assignment, so the smallest attainable value is one over the number of ranked assignments. The space-and-time p-value uses its own reduced-sample real refit, which can differ from the main estimate. Interpreting the ranks inferentially requires comparable assignments; treat them as a diagnostic alongside the model interval.

| Model | Month | beta 2023–24 (95% CI) | p | beta' 2024–25 (95% CI) | sigma_u | Placebo-space p | Placebo-space-time p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Site + period | January (supplementary) | -0.070 (-0.183, 0.044) | 0.22 | -0.090 (-0.201, 0.020) | 0.0408 | 0.143 | 0.086 |
| Site + period | May | -0.069 (-0.104, -0.033) | 0.00044 | -0.027 (-0.064, 0.010) | 0.0118 | 0.143 | 0.029 |
| Site + period | September | -0.093 (-0.133, -0.053) | 5.4e-05 | -0.033 (-0.074, 0.007) | 0.0082 | 0.143 | 0.029 |
| Site + period | November | -0.113 (-0.161, -0.066) | 3.9e-05 | -0.014 (-0.062, 0.033) | 0.0112 | 0.143 | 0.029 |
| Period only | January (supplementary) | -0.063 (-0.161, 0.036) | 0.2 | -0.084 (-0.179, 0.010) | 0.0383 | 0.143 | 0.057 |
| Period only | May | -0.059 (-0.090, -0.028) | 0.00051 | -0.017 (-0.050, 0.016) | 0.0112 | 0.143 | 0.029 |
| Period only | September | -0.083 (-0.121, -0.045) | 0.0001 | -0.023 (-0.061, 0.015) | 0.0077 | 0.143 | 0.029 |
| Period only | November | -0.108 (-0.152, -0.064) | 1.9e-05 | -0.009 (-0.053, 0.035) | 0.0101 | 0.143 | 0.029 |
