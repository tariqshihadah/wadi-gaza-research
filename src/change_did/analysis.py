"""End-to-end orchestration of the weighted fixed-effects change model."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from plot_style import month_name

from .config import DidAnalysisConfig
from .data import fill_missing_se, flagged_se_report
from .fitting import compute_anomalies, fit_did
from .models import WeightedFitResult
from .placebo import EVENT_TERM, PERSIST_TERM, run_placebo_space, run_placebo_spacetime

LOGGER = logging.getLogger(__name__)

PRIMARY_VARIANT = "primary"
PRIMARY_FILL = "max_se"


@dataclass(frozen=True)
class DidResults:
    """Tabular outputs of one full fixed-effects analysis run."""

    main: pd.DataFrame
    placebo_space: pd.DataFrame
    placebo_spacetime: pd.DataFrame
    anomalies: pd.DataFrame
    flagged_report: pd.DataFrame


@dataclass(frozen=True)
class Variant:
    """One main-model specification: a tau threshold and a missing-SE policy."""

    name: str
    tau: float
    fill_method: str


class ChangeDidAnalysis:
    """Run the main model, placebo tests, and sensitivity reruns per the brief."""

    def __init__(self, config: DidAnalysisConfig):
        self.config = config

    def variants(self) -> tuple[Variant, ...]:
        """Return the primary specification followed by the sensitivity reruns."""
        variants = [Variant(PRIMARY_VARIANT, self.config.tau, PRIMARY_FILL)]
        for tau in self.config.tau_sensitivity:
            if not np.isclose(tau, self.config.tau):
                variants.append(Variant(f"tau_{tau:g}", tau, PRIMARY_FILL))
        variants.append(Variant("exclude_flagged", self.config.tau, "drop_flagged"))
        variants.append(Variant("n_eff_fill", self.config.tau, "n_eff_fill"))
        return tuple(variants)

    def run(self, frame: pd.DataFrame) -> DidResults:
        """Fit every index x month x variant plus the primary-variant placebos."""
        config = self.config
        event_pair, persist_pair = config.event_pairs
        indicators = {
            EVENT_TERM: (config.affected_site, event_pair),
            PERSIST_TERM: (config.affected_site, persist_pair),
        }
        main_rows: list[dict] = []
        space_frames: list[pd.DataFrame] = []
        spacetime_frames: list[pd.DataFrame] = []
        anomaly_frames: list[pd.DataFrame] = []
        for index in config.indices:
            for month in config.months:
                tags = {
                    "index": index,
                    "role": config.role(index),
                    "month": month,
                    "supplementary": config.is_supplementary(month),
                }
                for variant in self.variants():
                    subset = self._subset(frame, index, month, variant.tau)
                    handled, n_filled = fill_missing_se(
                        subset, variant.fill_method, config.fill_n_eff
                    )
                    fit = fit_did(
                        handled, indicators,
                        [(config.affected_site, event_pair)], config.alpha,
                    )
                    for term in fit.dropped_terms:
                        LOGGER.warning(
                            "Dropped indicator %s for %s month %s variant %s: "
                            "its cell is absent after SE handling",
                            term, index, month, variant.name,
                        )
                    main_rows.extend(
                        self._main_rows(tags, variant, fit, n_filled)
                    )
                    if variant.name == PRIMARY_VARIANT:
                        real_estimate = fit.terms[EVENT_TERM].estimate
                        space = run_placebo_space(handled, real_estimate, config)
                        spacetime = run_placebo_spacetime(handled, config)
                        anomalies = compute_anomalies(handled, fit)
                        anomalies = anomalies.rename(columns={"study_area": "site"})
                        anomalies["is_event_cell"] = anomalies["site"].eq(
                            config.affected_site
                        ) & anomalies["year_start"].isin(
                            [pair[0] for pair in config.event_pairs]
                        )
                        for tagged in (space, spacetime, anomalies):
                            for key, value in {
                                **tags,
                                "tau": variant.tau,
                                "fill_method": variant.fill_method,
                            }.items():
                                tagged[key] = value
                        space_frames.append(space)
                        spacetime_frames.append(spacetime)
                        anomaly_frames.append(anomalies)
        tag_columns = ["index", "role", "month", "supplementary", "tau", "fill_method"]
        space_results = pd.concat(space_frames, ignore_index=True)
        spacetime_results = pd.concat(spacetime_frames, ignore_index=True)
        anomaly_results = pd.concat(anomaly_frames, ignore_index=True)
        return DidResults(
            main=pd.DataFrame(main_rows),
            placebo_space=space_results[
                tag_columns
                + ["site", "is_real", "estimate", "p_value", "ratio_to_largest_placebo"]
            ],
            placebo_spacetime=spacetime_results[
                tag_columns
                + ["site", "year_start", "year_end", "is_real", "estimate", "p_value"]
            ],
            anomalies=anomaly_results[
                tag_columns
                + [
                    "site", "year_start", "year_end", "mean_change",
                    "counterfactual", "anomaly", "is_event_cell",
                ]
            ],
            flagged_report=flagged_se_report(frame, config),
        )

    def save(self, results: DidResults) -> None:
        """Write per-index CSV outputs, markdown summaries, and audit configurations."""
        for index in self.config.indices:
            output_dir = self.config.output_dir / index
            output_dir.mkdir(parents=True, exist_ok=True)
            for name, frame in (
                ("did_main.csv", results.main),
                ("did_placebo_space.csv", results.placebo_space),
                ("did_placebo_spacetime.csv", results.placebo_spacetime),
                ("did_anomalies.csv", results.anomalies),
                ("flagged_se_report.csv", results.flagged_report),
            ):
                frame.loc[frame["index"] == index].to_csv(
                    output_dir / name, index=False
                )
            with (output_dir / "did_summary.md").open("w", encoding="utf-8") as stream:
                stream.write(self.summarize(results, indices=(index,)))
            config = self.config.to_dict()
            config["index"] = index
            config["output_dir"] = str(output_dir)
            with (output_dir / "config.json").open("w", encoding="utf-8") as stream:
                json.dump(config, stream, indent=2)

    def summarize(
        self, results: DidResults, indices: tuple[str, ...] | None = None
    ) -> str:
        """Render the per-index, per-month summary of the primary specification."""
        config = self.config
        event_pair, persist_pair = config.event_pairs
        event_label = f"{event_pair[0]}\u2013{event_pair[1] % 100:02d}"
        persist_label = f"{persist_pair[0]}\u2013{persist_pair[1] % 100:02d}"
        lines = [
            "# Weighted fixed-effects model on index change",
            "",
            f"Primary specification: tau = {config.tau:g}, largest-SE fill, "
            f"affected site {config.affected_site}. {config.primary_index} is the "
            "primary index; other indices are robustness checks. Supplementary "
            "months are flagged in their month label.",
            "",
        ]
        main = results.main
        primary = main.loc[main["variant"] == PRIMARY_VARIANT]
        for index in indices or config.indices:
            lines.append(f"## {index} ({config.role(index)})")
            lines.append("")
            lines.append(
                f"| Month | beta {event_label} (95% CI) | p | "
                f"beta' {persist_label} (95% CI) | sigma_u | "
                "Placebo-space p | Placebo-space-time p |"
            )
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for month in config.months:
                rows = primary.loc[
                    (primary["index"] == index) & (primary["month"] == month)
                ].set_index("term")
                event = rows.loc[EVENT_TERM]
                label = month_name(month)
                if config.is_supplementary(month):
                    label += " (supplementary)"
                space_p = self._placebo_p(results.placebo_space, index, month)
                spacetime_p = self._placebo_p(results.placebo_spacetime, index, month)
                persist_cell = "--"
                if PERSIST_TERM in rows.index:
                    persist = rows.loc[PERSIST_TERM]
                    persist_cell = _estimate_cell(persist)
                lines.append(
                    f"| {label} | {_estimate_cell(event)} | {event['p_value']:.2g} "
                    f"| {persist_cell} | {event['sigma_u']:.4f} "
                    f"| {space_p:.3f} | {spacetime_p:.3f} |"
                )
            lines.append("")
        return "\n".join(lines)

    def _subset(
        self, frame: pd.DataFrame, index: str, month: int, tau: float
    ) -> pd.DataFrame:
        """Return one index x month x tau subset, raising if it is empty."""
        subset = frame.loc[
            frame["index"].eq(index)
            & frame["month"].eq(month)
            & np.isclose(frame["tau"], tau)
        ].reset_index(drop=True)
        if subset.empty:
            raise ValueError(f"No rows for index={index}, month={month}, tau={tau}")
        return subset

    def _main_rows(
        self, tags: dict, variant: Variant, fit: WeightedFitResult, n_filled: int
    ) -> list[dict]:
        """Convert one fit into tagged per-term output rows."""
        event_pair, persist_pair = self.config.event_pairs
        cells = {EVENT_TERM: event_pair, PERSIST_TERM: persist_pair}
        rows = []
        for name, term in fit.terms.items():
            rows.append({
                **tags,
                "variant": variant.name,
                "tau": variant.tau,
                "fill_method": variant.fill_method,
                "term": name,
                "event_year_start": cells[name][0],
                "event_year_end": cells[name][1],
                "estimate": term.estimate,
                "se": term.se,
                "ci_low": term.ci_low,
                "ci_high": term.ci_high,
                "p_value": term.p_value,
                "sigma_u": fit.sigma_u,
                "sigma_u_clipped": fit.sigma_u_clipped,
                "df": fit.df,
                "n_obs": fit.n_obs,
                "n_filled": n_filled,
            })
        return rows

    @staticmethod
    def _placebo_p(placebo: pd.DataFrame, index: str, month: int) -> float:
        """Return the month's placebo p-value for one index."""
        rows = placebo.loc[placebo["index"].eq(index) & placebo["month"].eq(month)]
        return float(rows["p_value"].iloc[0])


def _estimate_cell(row: pd.Series) -> str:
    """Format one estimate with its confidence interval for the summary table."""
    return f"{row['estimate']:.3f} ({row['ci_low']:.3f}, {row['ci_high']:.3f})"
