# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair effects use deviation (sum-to-zero) coding, so each is relative to the average site or year pair, with an asterisk where the 95% CI excludes zero.

## SAVI (robustness)

### Site + period model

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 0.006 | 0.001 | 0.001 | -0.000 |
| BesorStream | -0.024 | -0.001 | -0.000 | 0.000 |
| HaBesorNationalPark | -0.002 | -0.001 | -0.002 | 0.000 |
| HolotNizzanim | 0.007 | -0.002 | -0.001 | 0.000 |
| HolotPalmahim | 0.005 | -0.001 | -0.001 | -0.000 |
| NahalRubin | 0.003 | -0.005 | -0.003 | -0.001 |
| WadiGaza | 0.005 | 0.009 | 0.007 | 0.001 |
| Joint p (sites) | 0.944 | 0.779 | 0.687 | 1.000 |
| 2019–20 | -0.037* | 0.013* | -0.001 | 0.007 |
| 2020–21 | 0.035* | -0.008 | 0.006* | -0.010* |
| 2021–22 | 0.018 | 0.005 | 0.003 | 0.003 |
| 2022–23 | 0.003 | 0.009* | -0.001 | 0.009* |
| 2023–24 | 0.037 | -0.005 | 0.003 | -0.006 |
| 2024–25 | -0.056* | -0.014* | -0.010* | -0.002 |
| Joint p (year pairs) | 0.008 | 0.002 | 0.039 | 0.051 |
| beta (2023–24) (95% CI) | -0.086 (-0.214, 0.041) | -0.080 (-0.115, -0.044)* | -0.082 (-0.115, -0.049)* | -0.075 (-0.111, -0.039)* |
| beta' (2024–25) (95% CI) | -0.032 (-0.159, 0.094) | -0.027 (-0.062, 0.008) | -0.029 (-0.062, 0.004) | -0.005 (-0.035, 0.025) |
| sigma_u | 0.048 | 0.012 | 0.008 | 0.012 |

### Period only model

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| 2019–20 | -0.037* | 0.014* | -0.000 | 0.007 |
| 2020–21 | 0.035* | -0.008 | 0.006* | -0.010* |
| 2021–22 | 0.019 | 0.006 | 0.004 | 0.003 |
| 2022–23 | 0.003 | 0.010* | -0.001 | 0.009* |
| 2023–24 | 0.036* | -0.007 | 0.002 | -0.006 |
| 2024–25 | -0.056* | -0.015* | -0.011* | -0.003 |
| Joint p (year pairs) | 0.003 | 0.000 | 0.010 | 0.021 |
| beta (2023–24) (95% CI) | -0.080 (-0.188, 0.028) | -0.069 (-0.101, -0.038)* | -0.074 (-0.105, -0.043)* | -0.074 (-0.105, -0.043)* |
| beta' (2024–25) (95% CI) | -0.028 (-0.134, 0.079) | -0.016 (-0.047, 0.015) | -0.021 (-0.052, 0.010) | -0.004 (-0.028, 0.020) |
| sigma_u | 0.045 | 0.011 | 0.007 | 0.011 |

### Event estimates and placebo tests

| Model | Month | beta 2023–24 (95% CI) | p | beta' 2024–25 (95% CI) | sigma_u | Placebo-space p | Placebo-space-time p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Site + period | January (supplementary) | -0.086 (-0.214, 0.041) | 0.18 | -0.032 (-0.159, 0.094) | 0.0482 | 0.143 | 0.057 |
| Site + period | May | -0.080 (-0.115, -0.044) | 7.7e-05 | -0.027 (-0.062, 0.008) | 0.0117 | 0.143 | 0.029 |
| Site + period | September | -0.082 (-0.115, -0.049) | 2.5e-05 | -0.029 (-0.062, 0.004) | 0.0076 | 0.143 | 0.029 |
| Site + period | November | -0.075 (-0.111, -0.039) | 0.00019 | -0.005 (-0.035, 0.025) | 0.0117 | 0.143 | 0.029 |
| Period only | January (supplementary) | -0.080 (-0.188, 0.028) | 0.14 | -0.028 (-0.134, 0.079) | 0.0451 | 0.143 | 0.029 |
| Period only | May | -0.069 (-0.101, -0.038) | 8.4e-05 | -0.016 (-0.047, 0.015) | 0.0112 | 0.143 | 0.029 |
| Period only | September | -0.074 (-0.105, -0.043) | 3.1e-05 | -0.021 (-0.052, 0.010) | 0.0072 | 0.143 | 0.029 |
| Period only | November | -0.074 (-0.105, -0.043) | 2.6e-05 | -0.004 (-0.028, 0.020) | 0.0106 | 0.143 | 0.029 |
