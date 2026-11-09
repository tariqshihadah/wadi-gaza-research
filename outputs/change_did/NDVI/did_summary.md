# Weighted fixed-effects model on index change

Primary specification: tau = 0.05, largest-SE fill, affected site WadiGaza. NDVI is the primary index; other indices are robustness checks. Supplementary months are flagged in their month label. Each model specification (site + period, and period only without site effects) is reported separately; site and year-pair effects use deviation (sum-to-zero) coding, so each is relative to the average site or year pair, with an asterisk where the 95% CI excludes zero.

## NDVI (primary)

### Site + period model

| Term | January (supplementary) | May | September | November |
| --- | --- | --- | --- | --- |
| AlAhrashProtectorate | 0.008 | 0.002 | 0.001 | -0.000 |
| BesorStream | -0.032 | -0.001 | -0.000 | -0.001 |
| HaBesorNationalPark | -0.005 | -0.002 | -0.001 | -0.001 |
| HolotNizzanim | 0.007 | -0.003 | -0.002 | -0.000 |
| HolotPalmahim | 0.005 | -0.001 | -0.001 | -0.001 |
| NahalRubin | 0.008 | -0.006 | -0.006 | -0.000 |
| WadiGaza | 0.009 | 0.011 | 0.009 | 0.003 |
| Joint p (sites) | 0.935 | 0.800 | 0.685 | 1.000 |
| 2019–20 | -0.031 | 0.014* | 0.005 | 0.021* |
| 2020–21 | 0.044 | -0.008 | 0.004 | -0.024* |
| 2021–22 | 0.025 | 0.007 | 0.006 | 0.013 |
| 2022–23 | -0.003 | 0.017* | 0.002 | 0.019* |
| 2023–24 | 0.048 | -0.014* | -0.002 | -0.025* |
| 2024–25 | -0.083* | -0.016* | -0.015* | -0.004 |
| Joint p (year pairs) | 0.009 | 0.001 | 0.049 | 0.000 |
| beta (2023–24) (95% CI) | -0.099 (-0.268, 0.071) | -0.095 (-0.141, -0.049)* | -0.111 (-0.162, -0.060)* | -0.132 (-0.195, -0.069)* |
| beta' (2024–25) (95% CI) | -0.090 (-0.255, 0.076) | -0.039 (-0.087, 0.008) | -0.044 (-0.095, 0.006) | -0.015 (-0.078, 0.048) |
| sigma_u | 0.063 | 0.015 | 0.010 | 0.018 |

### Period only model

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

| Model | Month | beta 2023–24 (95% CI) | p | beta' 2024–25 (95% CI) | sigma_u | Placebo-space p | Placebo-space-time p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Site + period | January (supplementary) | -0.099 (-0.268, 0.071) | 0.24 | -0.090 (-0.255, 0.076) | 0.0629 | 0.143 | 0.086 |
| Site + period | May | -0.095 (-0.141, -0.049) | 0.00023 | -0.039 (-0.087, 0.008) | 0.0150 | 0.143 | 0.029 |
| Site + period | September | -0.111 (-0.162, -0.060) | 0.00011 | -0.044 (-0.095, 0.006) | 0.0105 | 0.143 | 0.029 |
| Site + period | November | -0.132 (-0.195, -0.069) | 0.00019 | -0.015 (-0.078, 0.048) | 0.0180 | 0.143 | 0.029 |
| Period only | January (supplementary) | -0.088 (-0.234, 0.058) | 0.23 | -0.081 (-0.222, 0.060) | 0.0592 | 0.143 | 0.057 |
| Period only | May | -0.082 (-0.123, -0.040) | 0.0003 | -0.026 (-0.069, 0.016) | 0.0143 | 0.143 | 0.029 |
| Period only | September | -0.101 (-0.148, -0.053) | 0.00015 | -0.034 (-0.082, 0.014) | 0.0096 | 0.143 | 0.029 |
| Period only | November | -0.128 (-0.185, -0.072) | 5.3e-05 | -0.010 (-0.067, 0.046) | 0.0161 | 0.143 | 0.029 |
