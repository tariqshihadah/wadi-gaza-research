# Confidence Intervals for Mean Index Change Under Spatial Autocorrelation

## Methodology Overview

## 1. Purpose

This document describes the method used to estimate a confidence interval (CI) for the mean change in a raster-based index between two dates, while accounting for spatial autocorrelation. A standard CI treats every pixel as an independent observation. Neighboring pixels in raster data tend to be similar, so they carry partly redundant information. Treating them as independent understates the uncertainty. This method replaces the raw pixel count with an **effective sample size** derived from the measured spatial autocorrelation of the change.

## 2. Scope and Data

The analysis is applied to multiple study areas. For each study area, index rasters are available for several dates. Pairs of dates are compared, and each pair is analyzed independently using the identical procedure described here.

Within a study area, all rasters are co-registered: they share the same resolution, alignment, extent, and valid-pixel mask. Pixels outside the mask are excluded from every calculation.

## 3. Notation

| Symbol | Meaning |
|---|---|
| $X^{(0)}, X^{(1)}$ | Index rasters for the earlier and later date of a pair |
| $d_i$ | Change at valid pixel $i$: $d_i = X^{(1)}_i - X^{(0)}_i$ |
| $N$ | Number of valid pixels |
| $\bar{d}$, $s_D$ | Mean and sample standard deviation of the change |
| $k$ | Lag, in pixels |
| $w^{(k)}_{ij}$ | Binary ring weight between pixels $i$ and $j$ at lag $k$ |
| $W_k$ | Number of valid ordered pixel pairs at lag $k$ |
| $I_k$ | Moran's I at lag $k$ |
| $\tau$ | Near-zero threshold defining the range |
| $R$ | Range (decorrelation distance), in pixels |
| $n_{\text{eff}}$ | Effective sample size |

## 4. Method

### 4.1 Difference raster and summary statistics

For each date pair, compute the difference raster $D$ over valid pixels. Then compute:

$$\bar{d} = \frac{1}{N}\sum_{i=1}^{N} d_i, \qquad s_D = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(d_i - \bar{d})^2}$$

All subsequent steps operate on $D$, since the relevant autocorrelation is that of the change, not of either date individually.

### 4.2 Moran's I correlogram

Spatial autocorrelation of $D$ is measured with a Moran's I correlogram: Moran's I is computed separately at each lag $k = 1, 2, \dots, K_{\max}$.

At each lag, binary ring (annular) weights on Chebyshev distance are used. For pixel $i$ at row $r_i$ and column $c_i$:

$$w^{(k)}_{ij} = \begin{cases} 1 & \text{if } \max(|r_i - r_j|,\ |c_i - c_j|) = k \\ 0 & \text{otherwise} \end{cases}$$

Each lag therefore captures only pixel pairs exactly $k$ steps apart, including diagonals. Lag 1 is equivalent to queen contiguity. Weights are not row-standardized. Pairs involving any pixel outside the mask are excluded, so edge and mask-boundary pixels simply contribute fewer pairs.

The total weight at lag $k$ is the number of valid ordered pairs:

$$W_k = \sum_{i}\sum_{j \neq i} w^{(k)}_{ij}$$

Moran's I at lag $k$ is:

$$I_k = \frac{N}{W_k} \cdot \frac{\sum_{i}\sum_{j \neq i} w^{(k)}_{ij}\,(d_i - \bar{d})(d_j - \bar{d})}{\sum_{i}(d_i - \bar{d})^2}$$

With binary ring weights, $I_k$ equals the average product of paired deviations at lag $k$ divided by the overall variance. It therefore serves directly as the spatial autocorrelation at that lag.

The maximum lag is set to one quarter of the smaller dimension of the study area's bounding box, in pixels:

$$K_{\max} = \left\lfloor \tfrac{1}{4}\min(H, W) \right\rfloor$$

Beyond this distance, too few pairs remain for reliable estimates. Lags are evaluated at 1-pixel steps. For very large rasters, lags may be spaced more widely at larger distances and the correlogram interpolated between them.

### 4.3 Range

The range $R$ is the first lag at which autocorrelation becomes negligible:

$$R = \min\{\, k : I_k < \tau \ \text{ or } \ I_k \le 0 \,\}, \qquad \tau = 0.05$$

A fixed magnitude threshold is used instead of a significance test. With large $N$, even negligible autocorrelation is statistically significant, so a significance-based cutoff would not identify a meaningful range.

The range is reported in both pixels and map units ($R \times$ cell size).

### 4.4 Effective sample size

Autocorrelation inflates the variance of the mean. Summing the correlation contributed by each lag up to the range gives:

$$n_{\text{eff}} = \frac{N}{1 + \displaystyle\sum_{k=1}^{R-1} \frac{W_k}{N}\, I_k}$$

The term $W_k / N$ is the average number of valid neighbors per pixel at lag $k$. It is measured from the data, so it automatically accounts for edges and the irregular mask. Lags at or beyond $R$, including any negative values, are excluded from the sum.

The result is bounded so that $n_{\text{eff}} \le N$.

### 4.5 Confidence interval

The CI for the mean change uses the observed mean and standard deviation with the effective sample size:

$$\text{CI}_{1-\alpha} = \bar{d} \ \pm\ t_{1-\alpha/2,\ n_{\text{eff}}-1} \cdot \frac{s_D}{\sqrt{n_{\text{eff}}}}, \qquad \alpha = 0.05$$

## 5. Sensitivity and Quality Checks

**Threshold sensitivity.** Steps 4.3 through 4.5 are repeated for $\tau \in \{0.02,\ 0.05,\ 0.10\}$. The pair count $W_k$ grows with lag, so small correlations at larger lags can noticeably affect $n_{\text{eff}}$. Stable results across thresholds indicate the CI is robust to this choice.

**Flags.** A pair is flagged for review when either condition holds:

- $I_k$ does not fall below $\tau$ by $K_{\max}$. This typically indicates a broad trend across the study area rather than local clustering, and the effective number of independent units is very small.
- $n_{\text{eff}} < 30$.

## 6. Assumptions and Notes

**Stationarity.** A single correlogram is assumed to describe the autocorrelation structure across the whole study area for a given pair.

**Independence of pairs.** Each date pair is analyzed separately, and its correlogram, range, and $n_{\text{eff}}$ are specific to that pair.

**Multiple comparisons.** Because many pairs are evaluated across study areas, individual CIs should be interpreted with the number of comparisons in mind.

## 7. Reported Outputs (per date pair)

For each pair, the following are reported:

- the mean change $\bar{d}$
- the standard deviation $s_D$
- the pixel count $N$
- the range $R$, in pixels and map units
- the effective sample size $n_{\text{eff}}$
- the 95% CI
- the sensitivity results for each value of $\tau$
- any flags raised
- the correlogram ($I_k$ versus $k$)
