# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair effects use deviation (sum-to-zero) coding, so each is relative to the average site or year pair, with an asterisk where the 95% CI excludes zero.

Fits use statsmodels OLS/WLS with the leverage-adjusted Hedges (HE) method-of-moments variance estimator. Inverse estimated total-variance weights are treated as fixed, with covariance scale = 1, Student-t coefficient inference, and Wald F-tests.

## SAVI (robustness)

### Site + period model

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
