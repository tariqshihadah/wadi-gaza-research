# Confidence Intervals for Mean Index Levels Under Spatial Autocorrelation

## Purpose

This method estimates a confidence interval for the spatial mean of an index raster for one study area, month, and observation year. Adjacent pixels are spatially autocorrelated, so treating every valid pixel as independent would understate uncertainty. The procedure estimates an effective sample size from the raster's Moran's I correlogram and uses it in a Student-t interval.

The shared engine and estimators live in `src/spatial_ci/`. The change and index pipelines supply their respective raster metric and write different result records.

## Observation and common support

Each observation is one named index band from one composite raster. For temporal comparisons, all years for a given study area, month, and index use the intersection of valid pixels across the configured observation years. This holds the spatial support fixed across years. A run should report the common valid-pixel count and review it if it is unexpectedly small.

Let $x_i$ be the index value at valid pixel $i$, and let $N$ be the number of pixels on this common support. For each observation:

$$
\bar{x} = \frac{1}{N}\sum_{i=1}^{N}x_i,\qquad
s_X = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(x_i-\bar{x})^2}.
$$

## Moran's I and effective sample size

The spatial autocorrelation calculation uses the shared `spatial_ci` implementation: binary Chebyshev rings, ordered pair counts, and the FFT engine by default. For each lag $k$, Moran's I is calculated from deviations $x_i-\bar{x}$ with the same ring weights and normalization used by the change analysis.

The maximum lag is one quarter of the smaller dimension of the valid-pixel bounding box. The range is the first lag $R$ at which $I_k < \tau$, with $\tau=0.05$ as the primary threshold and 0.02 and 0.10 as sensitivity checks. The effective sample size is:

$$
n_{\mathrm{eff}} = \frac{N}{1 + \sum_{k=1}^{R-1}(W_k/N)I_k},
$$

where $W_k$ is the number of valid ordered pairs at lag $k$. If no range is found, the adjusted CI is not reported and the observation is flagged.

## Confidence interval

With $\nu=n_{\mathrm{eff}}-1$ and significance level $\alpha=0.05$:

$$
\mathrm{SE}(\bar{x}) = \frac{s_X}{\sqrt{n_{\mathrm{eff}}}},\qquad
\bar{x} \pm t_{1-\alpha/2,\nu}\mathrm{SE}(\bar{x}).
$$

The naive interval using $N$ in place of $n_{\mathrm{eff}}$ is also saved for comparison. Low effective sample size ($n_{\mathrm{eff}}<30$), undefined range, and per-observation failures are explicitly flagged.

## Interpretation and limitations

The interval describes the spatial mean for one raster observation under the correlogram and stationarity assumptions. It does not represent uncertainty in the temporal trajectory, nor is a set of per-year intervals a formal test of year effects. Year-to-year contrasts require their own inference and must account for temporal dependence and covariance between observations. In particular, overlap of two year-level CIs is not a substitute for a direct contrast.

As with the change method, the CI treats the observed spatial variation as the basis for uncertainty and adjusts only for spatial autocorrelation. It does not separately model sensor error, temporal sampling, or uncertainty in the composite.
