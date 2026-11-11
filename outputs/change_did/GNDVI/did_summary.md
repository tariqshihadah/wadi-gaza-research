# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair effects use deviation (sum-to-zero) coding, so each is relative to the average site or year pair, with an asterisk where the 95% CI excludes zero.

Fits use statsmodels OLS/WLS with the leverage-adjusted Hedges (HE) method-of-moments variance estimator. Inverse estimated total-variance weights are treated as fixed, with covariance scale = 1, Student-t coefficient inference, and Wald F-tests.

## GNDVI (robustness)

### Site + period model

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
