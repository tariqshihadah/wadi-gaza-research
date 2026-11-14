# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair estimates are relative to their respective averages. An asterisk marks estimates whose 95% confidence interval excludes zero.

The models use weighted regression to account for uncertainty in the estimated index changes, and report 95% confidence intervals and joint checks of site and year-pair effects.

## NDVI (primary)

### Site + period model

**Caption.** NDVI site effects, year-pair effects, and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the site + period model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of NDVI change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. Site and year-pair estimates are relative to their respective averages. The site joint p-value checks whether sites differ overall in average change, after accounting for year-to-year differences. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The site tests did not indicate an overall difference among sites in these months. The year-pair tests indicated differences among years in every listed month, supporting the use of year-to-year adjustments. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 0.008 | 0.002 | 0.001 | -0.000 |
| BesorStream | -0.032 | -0.001 | -0.000 | -0.001 |
| HaBesorNationalPark | -0.005 | -0.002 | -0.001 | -0.001 |
| HolotNizzanim | 0.007 | -0.003 | -0.002 | -0.000 |
| HolotPalmahim | 0.005 | -0.001 | -0.001 | -0.001 |
| NahalRubin | 0.008 | -0.006 | -0.006 | -0.000 |
| WadiGaza | 0.009 | 0.011 | 0.009 | 0.003 |
| Joint p (sites) | 0.935 | 0.800 | 0.684 | 1.000 |
| 2019–20 | -0.031 | 0.014* | 0.005 | 0.021* |
| 2020–21 | 0.044 | -0.008 | 0.004 | -0.024* |
| 2021–22 | 0.025 | 0.007 | 0.006 | 0.013 |
| 2022–23 | -0.003 | 0.017* | 0.002 | 0.019* |
| 2023–24 | 0.048 | -0.014* | -0.002 | -0.025* |
| 2024–25 | -0.083* | -0.016* | -0.015* | -0.004 |
| Joint p (year pairs) | 0.009 | 0.001 | 0.048 | 0.000 |
| beta (2023–24) (95% CI) | -0.099 (-0.268, 0.071) | -0.095 (-0.141, -0.049)* | -0.111 (-0.162, -0.060)* | -0.132 (-0.195, -0.069)* |
| beta' (2024–25) (95% CI) | -0.090 (-0.255, 0.076) | -0.039 (-0.087, 0.008) | -0.044 (-0.095, 0.006) | -0.015 (-0.078, 0.048) |
| sigma_u | 0.063 | 0.015 | 0.010 | 0.018 |

### Period only model

**Caption.** NDVI year-pair effects and WadiGaza's 2023–24 event and 2024–25 persistence estimates by calendar month under the period-only model, with 95% confidence intervals.

**Explanation.** Each column is a calendar month of NDVI change (later year minus earlier year, averaged over valid pixels), fitted separately; supplementary months are flagged in their label. This model has no site effects, so the shared year-pair changes are the only baseline. The year-pair joint p-value checks whether average changes differ across years, after accounting for the other model terms. The year-pair tests indicated differences among years in every listed month, supporting the use of year-to-year adjustments. beta is WadiGaza's departure from the expected change in 2023–24; beta' is the same departure in 2024–25, so a value near zero means the change held without recovering and a positive value indicates recovery. Brackets give 95% confidence intervals; an asterisk marks an interval excluding zero. sigma_u summarizes unexplained variation among site-year observations.

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| 2019–20 | -0.031 | 0.014* | 0.006 | 0.021* |
| 2020–21 | 0.044* | -0.008 | 0.005 | -0.024* |
| 2021–22 | 0.026 | 0.008 | 0.007 | 0.013* |
| 2022–23 | -0.002 | 0.018* | 0.003 | 0.020* |
| 2023–24 | 0.046* | -0.015* | -0.004 | -0.025* |
| 2024–25 | -0.083* | -0.017* | -0.016* | -0.005 |
| Joint p (year pairs) | 0.004 | 0.000 | 0.005 | 0.000 |
| beta (2023–24) (95% CI) | -0.088 (-0.234, 0.058) | -0.082 (-0.123, -0.040)* | -0.101 (-0.148, -0.053)* | -0.128 (-0.185, -0.072)* |
| beta' (2024–25) (95% CI) | -0.081 (-0.222, 0.060) | -0.026 (-0.069, 0.016) | -0.034 (-0.082, 0.014) | -0.010 (-0.067, 0.046) |
| sigma_u | 0.059 | 0.014 | 0.010 | 0.016 |

### Event estimates and placebo tests

**Caption.** NDVI event and persistence estimates with their t-test p-value, sigma_u, and placebo-in-space and placebo-in-space-and-time p-values, by model specification and calendar month.

**Explanation.** The table repeats beta (2023–24) and beta' (2024–25) from the model tables above with 95% CIs, adds the two-sided t-test p-value for beta, and adds two placebo diagnostics. Space placebos reassign the event and persistence indicators to comparison sites after excluding WadiGaza. Space-and-time placebos omit the 2024–25 pair and reassign a single event indicator among unaffected site-year-pair cells, excluding the real event cell from each placebo fit. Both placebo p-values are lower-tail rank proportions for a decline, including the real assignment, so the smallest attainable value is one over the number of ranked assignments. The space-and-time p-value uses its own reduced-sample real refit, which can differ from the main estimate. Interpreting the ranks inferentially requires comparable assignments; treat them as a diagnostic alongside the model interval.

| Model | Month | beta 2023–24 (95% CI) | p | beta' 2024–25 (95% CI) | sigma_u | Placebo-space p | Placebo-space-time p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Site + period | January (supplementary) | -0.099 (-0.268, 0.071) | 0.24 | -0.090 (-0.255, 0.076) | 0.0629 | 0.143 | 0.086 |
| Site + period | May | -0.095 (-0.141, -0.049) | 0.00023 | -0.039 (-0.087, 0.008) | 0.0150 | 0.143 | 0.029 |
| Site + period | September | -0.111 (-0.162, -0.060) | 0.00011 | -0.044 (-0.095, 0.006) | 0.0104 | 0.143 | 0.029 |
| Site + period | November | -0.132 (-0.195, -0.069) | 0.00019 | -0.015 (-0.078, 0.048) | 0.0180 | 0.143 | 0.029 |
| Period only | January (supplementary) | -0.088 (-0.234, 0.058) | 0.23 | -0.081 (-0.222, 0.060) | 0.0592 | 0.143 | 0.057 |
| Period only | May | -0.082 (-0.123, -0.040) | 0.0003 | -0.026 (-0.069, 0.016) | 0.0143 | 0.143 | 0.029 |
| Period only | September | -0.101 (-0.148, -0.053) | 0.00015 | -0.034 (-0.082, 0.014) | 0.0096 | 0.143 | 0.029 |
| Period only | November | -0.128 (-0.185, -0.072) | 5.4e-05 | -0.010 (-0.067, 0.046) | 0.0161 | 0.143 | 0.029 |
