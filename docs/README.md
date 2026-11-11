# Documentation

- [white-papers/](white-papers/): methodology write-ups describing what the project does and why, intended to inform the paper.
- [working-docs/](working-docs/): contemporaneous materials such as PI guidance and coding plans written to direct implementation. They record intent at the time and may differ from the final methods; the white papers are authoritative.

The index-level confidence interval method is described in [Mean-Index-Level-Confidence-Intervals](white-papers/Mean-Index-Level-Confidence-Intervals.md), with implementation guidance in [Coding-Plan_Mean-Index-Level-Confidence-Intervals](working-docs/Coding-Plan_Mean-Index-Level-Confidence-Intervals.md).

The change-comparison models are documented in [Before-After-Control-Impact-Analysis](white-papers/Before-After-Control-Impact-Analysis.md) and [Period-Only-Control-Impact-Analysis](white-papers/Period-Only-Control-Impact-Analysis.md). They use statsmodels OLS/WLS with the leverage-adjusted Hedges (HE) variance estimator and fixed-scale t/F inference. This supersedes the arithmetic-mean variance subtraction in the historical [handoff brief](working-docs/Handoff-Weighted-Fixed-Effects-Model-on-Index-Change.md). The exported `fit_weighted` function no longer accepts `exclude_from_sigma`: residual leverages account for saturated indicator cells automatically.
