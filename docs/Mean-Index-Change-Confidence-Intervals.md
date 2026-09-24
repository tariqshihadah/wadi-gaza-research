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
| $X^{(0)}$, $X^{(1)}$ | Index rasters for the earlier and later date of a pair |
| $D$ | Difference raster, $D = X^{(1)} - X^{(0)}$ |
| $d_i$ | Value of $D$ at valid pixel $i$ |
| $r_i$, $c_i$ | Row and column of pixel $i$ |
| $N$ | Number of valid pixels |
| $\bar{d}$ | Mean of $D$ |
| $s_D$ | Sample standard deviation of $D$ |
| $k$ | Lag, in pixels |
| $w_{ij}^{(k)}$ | Binary ring weight between pixels $i$ and $j$ at lag $k$ |
| $W_k$ | Number of valid ordered pixel pairs at lag $k$ |
| $I_k$ | Moran's I of $D$ at lag $k$ |
| $K_{\max}$ | Maximum lag evaluated |
| $n_{\mathrm{rows}}$, $n_{\mathrm{cols}}$ | Dimensions of the study area's bounding box, in pixels |
| $\tau$ | Near-zero threshold defining the range |
| $R$ | Range (decorrelation distance), in pixels |
| $n_{\mathrm{eff}}$ | Effective sample size |
| $\nu$ | Degrees of freedom for the CI |
| $\alpha$ | Significance level (CI level is $1 - \alpha$) |

## 4. Method

### 4.1 Difference raster and summary statistics

For each date pair, the difference is computed at every valid pixel:

$$
{d_i = X_i^{(1)} - X_i^{(0)}}
\tag{1}
$$

The mean and sample standard deviation of $D$ are:

$$
\bar{d} = \frac{1}{N} \sum_{i=1}^{N} d_i
\tag{2}
$$

$$
s_D = \sqrt{ \frac{1}{N-1} \sum_{i=1}^{N} \left( d_i - \bar{d} \right)^2 }
\tag{3}
$$

The standard deviation uses the actual pixel count $N$. It describes the pixel-to-pixel spread of the change, which is not reduced by autocorrelation. The effective sample size enters only through the standard error of the mean (Section 4.5). All subsequent steps operate on $D$, since the relevant autocorrelation is that of the change, not of either date individually.

### 4.2 Moran's I correlogram

Spatial autocorrelation of $D$ is measured with a Moran's I correlogram, in which Moran's I is computed separately at each lag $k = 1, 2, \ldots, K_{\max}$.

Each lag uses binary ring (annular) weights on Chebyshev distance:

$$
w_{ij}^{(k)} =
\begin{cases}
1 & \text{if } \max\left( \lvert r_i - r_j \rvert ,\, \lvert c_i - c_j \rvert \right) = k \\
0 & \text{otherwise}
\end{cases}
\tag{4}
$$

Each lag therefore captures only pixel pairs exactly $k$ steps apart, including diagonals, and lag 1 is equivalent to queen contiguity. Weights are not row-standardized. Pairs involving a pixel outside the mask are excluded, so pixels near edges and mask boundaries simply contribute fewer pairs.

The total weight at lag $k$ is the number of valid ordered pairs:

$$
W_k = \sum_{i=1}^{N} \sum_{j \neq i} w_{ij}^{(k)}
\tag{5}
$$

Moran's I at lag $k$ is:

$$
I_k = \frac{N}{W_k} \cdot
\frac{ \sum_{i=1}^{N} \sum_{j \neq i} w_{ij}^{(k)} \left( d_i - \bar{d} \right) \left( d_j - \bar{d} \right) }
     { \sum_{i=1}^{N} \left( d_i - \bar{d} \right)^2 }
\tag{6}
$$

With binary ring weights, $I_k$ equals the average product of paired deviations at lag $k$, divided by the variance of $D$. It therefore serves directly as the spatial autocorrelation at that lag.

The maximum lag is one quarter of the smaller dimension of the study area's bounding box:

$$
K_{\max} = \left\lfloor \frac{1}{4} \min\left( n_{\mathrm{rows}} ,\, n_{\mathrm{cols}} \right) \right\rfloor
\tag{7}
$$

Beyond this distance, too few pairs remain for reliable estimates. Lags are evaluated at 1-pixel steps. For very large rasters, lags may be spaced more widely at larger distances, with the correlogram interpolated between them.

### 4.3 Range

The range $R$ is the first lag at which autocorrelation becomes negligible:

$$
R = \min \{ k \in \{1, \ldots, K_{\max}\} \,:\, I_k < \tau \},
\qquad \tau = 0.05
\tag{8}
$$

Since $\tau > 0$, this also captures the first lag at which $I_k$ reaches or crosses zero. A fixed magnitude threshold is used instead of a significance test. With large $N$, even negligible autocorrelation is statistically significant, so a significance-based cutoff would not identify a meaningful range. $R$ is reported in both pixels and map units ($R$ multiplied by the cell size).

### 4.4 Effective sample size

Autocorrelation inflates the variance of the mean. Summing the correlation contributed by each lag below the range gives:

$$
n_{\mathrm{eff}} = \frac{N}{ 1 + \sum_{k=1}^{R-1} \frac{W_k}{N} \, I_k }
\tag{9}
$$

The ratio $W_k / N$ is the average number of valid neighbors per pixel at lag $k$. Because it is measured from the data, it accounts for edges and the irregular mask. Only lags $1$ through $R-1$ are included, and every $I_k$ in that span is at least $\tau$. The denominator is therefore at least 1, so $n_{\mathrm{eff}} \le N$ holds automatically. If $R = 1$, the sum is empty and $n_{\mathrm{eff}} = N$.

### 4.5 Confidence interval

The degrees of freedom are:

$$
\nu = n_{\mathrm{eff}} - 1
\tag{10}
$$

The $(1 - \alpha)$ CI for the mean change is:

$$
\mathrm{CI} = \bar{d} \pm t_{1-\alpha/2,\,\nu} \cdot \frac{s_D}{\sqrt{n_{\mathrm{eff}}}},
\qquad \alpha = 0.05
\tag{11}
$$

Here $t_{1-\alpha/2,\,\nu}$ is the $(1 - \alpha/2)$ quantile of Student's t-distribution with $\nu$ degrees of freedom.

## 5. Sensitivity and Quality Checks

**Threshold sensitivity.** Equations (8) through (11) are recomputed for $\tau \in \{0.02, 0.05, 0.10\}$. Because $W_k$ grows with lag, small correlations at larger lags can noticeably affect $n_{\mathrm{eff}}$. Stable results across thresholds indicate the CI is robust to this choice.

**Flags.** A pair is flagged for review under either of two conditions:

- No lag up to $K_{\max}$ satisfies Equation (8), so $R$ is undefined. This typically indicates a broad trend across the study area rather than local clustering, meaning the effective number of independent units is very small.
- The effective sample size falls below 30 ($n_{\mathrm{eff}} < 30$).

## 6. Assumptions and Notes

**Stationarity.** A single correlogram is assumed to describe the autocorrelation structure of $D$ across the whole study area.

**Independence of pairs.** Each date pair is analyzed separately. Its correlogram, $R$, and $n_{\mathrm{eff}}$ are specific to that pair.

**Multiple comparisons.** Because many pairs are evaluated across study areas, individual CIs should be interpreted with the number of comparisons in mind.

## 7. Reported Outputs (per date pair)

For each pair, the reported outputs are:

- the mean change $\bar{d}$, the standard deviation $s_D$, and the pixel count $N$
- the range $R$, in pixels and map units
- the effective sample size $n_{\mathrm{eff}}$ and the 95% CI
- the sensitivity results for each value of $\tau$
- any flags raised
- the correlogram, i.e. $I_k$ versus $k$