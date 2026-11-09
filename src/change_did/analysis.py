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
from .fitting import (
    compute_anomalies,
    effect_levels,
    fit_did,
    joint_wald_test,
    omitted_level_term,
)
from .models import MODEL_PERIOD_ONLY, MODEL_SITE_PERIOD, WeightedFitResult
from .placebo import EVENT_TERM, PERSIST_TERM, run_placebo_space, run_placebo_spacetime

LOGGER = logging.getLogger(__name__)

PRIMARY_VARIANT = "primary"
PRIMARY_FILL = "max_se"
MODEL_LABELS = {
    MODEL_SITE_PERIOD: "Site + period",
    MODEL_PERIOD_ONLY: "Period only",
}


@dataclass(frozen=True)
class DidResults:
    """Tabular outputs of one full fixed-effects analysis run."""

    main: pd.DataFrame
    effects: pd.DataFrame
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
        """Fit every model x index x month x variant plus the primary placebos."""
        config = self.config
        event_pair, persist_pair = config.event_pairs
        indicators = {
            EVENT_TERM: (config.affected_site, event_pair),
            PERSIST_TERM: (config.affected_site, persist_pair),
        }
        main_rows: list[dict] = []
        effect_rows: list[dict] = []
        space_frames: list[pd.DataFrame] = []
        spacetime_frames: list[pd.DataFrame] = []
        anomaly_frames: list[pd.DataFrame] = []
        for model in config.models:
            site_effects = config.model_site_effects(model)
            for index in config.indices:
                for month in config.months:
                    tags = {
                        "model": model,
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
                            handled, indicators, config.alpha,
                            site_effects=site_effects,
                        )
                        for term in fit.dropped_terms:
                            LOGGER.warning(
                                "Dropped indicator %s for %s %s month %s variant %s: "
                                "its cell is absent after SE handling",
                                term, model, index, month, variant.name,
                            )
                        main_rows.extend(
                            self._main_rows(tags, variant, fit, n_filled)
                        )
                        if variant.name == PRIMARY_VARIANT:
                            effect_rows.extend(
                                self._effect_rows(tags, variant, handled, fit)
                            )
                            real_estimate = fit.terms[EVENT_TERM].estimate
                            space = run_placebo_space(
                                handled, real_estimate, config, site_effects
                            )
                            spacetime = run_placebo_spacetime(
                                handled, config, site_effects
                            )
                            anomalies = compute_anomalies(handled, fit)
                            anomalies = anomalies.rename(
                                columns={"study_area": "site"}
                            )
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
        tag_columns = [
            "model", "index", "role", "month", "supplementary", "tau", "fill_method",
        ]
        space_results = pd.concat(space_frames, ignore_index=True)
        spacetime_results = pd.concat(spacetime_frames, ignore_index=True)
        anomaly_results = pd.concat(anomaly_frames, ignore_index=True)
        return DidResults(
            main=pd.DataFrame(main_rows),
            effects=pd.DataFrame(effect_rows),
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
                ("did_effects.csv", results.effects),
                ("did_placebo_space.csv", results.placebo_space),
                ("did_placebo_spacetime.csv", results.placebo_spacetime),
                ("did_anomalies.csv", results.anomalies),
                ("flagged_se_report.csv", results.flagged_report),
            ):
                frame.loc[frame["index"] == index].to_csv(
                    output_dir / name, index=False
                )
            for model in self.config.models:
                self.summary_table(results, index, model).to_csv(
                    output_dir / f"did_summary_{model}.csv", index=False
                )
            with (output_dir / "did_summary.md").open("w", encoding="utf-8") as stream:
                stream.write(self.summarize(results, indices=(index,)))
            config = self.config.to_dict()
            config["index"] = index
            config["output_dir"] = str(output_dir)
            with (output_dir / "config.json").open("w", encoding="utf-8") as stream:
                json.dump(config, stream, indent=2)

    def summary_table(
        self, results: DidResults, index: str, model: str
    ) -> pd.DataFrame:
        """Build one model's per-index summary table with months as columns.

        Rows are the deviation-coded site effects (site + period model only)
        with their joint Wald p-value, the deviation-coded year-pair effects
        with their joint p-value, the event terms beta and beta' with 95% CIs,
        and sigma_u. Each month contributes a formatted column (estimates to
        three decimals, an asterisk where the 95% CI excludes zero) plus
        numeric estimate/ci_low/ci_high/p_value columns.
        """
        config = self.config
        main = results.main
        primary = main.loc[
            main["model"].eq(model)
            & main["index"].eq(index)
            & main["variant"].eq(PRIMARY_VARIANT)
        ]
        effects = results.effects
        effects = effects.loc[
            effects["model"].eq(model) & effects["index"].eq(index)
        ]
        event_pair, persist_pair = config.event_pairs
        rows: list[dict] = []
        groups = (["site"] if config.model_site_effects(model) else []) + ["pair"]
        for group in groups:
            group_rows = effects.loc[effects["group"] == group]
            for level in group_rows["level"].drop_duplicates():
                rows.append(self._summary_row(
                    f"{group}_effect",
                    _level_label(group, level),
                    {
                        month: _effect_cell(
                            group_rows.loc[
                                group_rows["level"].eq(level)
                                & group_rows["month"].eq(month)
                            ].iloc[0]
                        )
                        for month in config.months
                    },
                ))
            joint = effects.loc[effects["group"] == f"{group}_joint"]
            label = "sites" if group == "site" else "year pairs"
            rows.append(self._summary_row(
                f"{group}_joint",
                f"Joint p ({label})",
                {
                    month: _p_cell(joint.loc[joint["month"].eq(month)].iloc[0])
                    for month in config.months
                },
            ))
        for term, pair in ((EVENT_TERM, event_pair), (PERSIST_TERM, persist_pair)):
            beta = "beta" if term == EVENT_TERM else "beta'"
            term_rows = primary.loc[primary["term"] == term]
            rows.append(self._summary_row(
                "event",
                f"{beta} ({_pair_label(*pair)}) (95% CI)",
                {
                    month: _event_cell(
                        term_rows.loc[term_rows["month"].eq(month)].iloc[0]
                    )
                    for month in config.months
                },
            ))
        sigma_rows = primary.loc[primary["term"] == EVENT_TERM]
        rows.append(self._summary_row(
            "sigma_u",
            "sigma_u",
            {
                month: (
                    f"{sigma_rows.loc[sigma_rows['month'].eq(month), 'sigma_u'].iloc[0]:.3f}",
                    {"estimate": float(
                        sigma_rows.loc[sigma_rows["month"].eq(month), "sigma_u"].iloc[0]
                    )},
                )
                for month in config.months
            },
        ))
        return pd.DataFrame(rows)

    def summarize(
        self, results: DidResults, indices: tuple[str, ...] | None = None
    ) -> str:
        """Render the per-index summaries of both model specifications."""
        config = self.config
        event_pair, persist_pair = config.event_pairs
        event_label = _pair_label(*event_pair)
        persist_label = _pair_label(*persist_pair)
        lines = [
            "# Weighted fixed-effects model on index change",
            "",
            f"Primary specification: tau = {config.tau:g}, largest-SE fill, "
            f"affected site {config.affected_site}. {config.primary_index} is the "
            "primary index; other indices are robustness checks. Supplementary "
            "months are flagged in their month label. Each model specification "
            "(site + period, and period only without site effects) is reported "
            "separately; site and year-pair effects use deviation (sum-to-zero) "
            "coding, so each is relative to the average site or year pair, with "
            "an asterisk where the 95% CI excludes zero.",
            "",
        ]
        main = results.main
        primary = main.loc[main["variant"] == PRIMARY_VARIANT]
        month_labels = {}
        for month in config.months:
            label = month_name(month)
            if config.is_supplementary(month):
                label += " (supplementary)"
            month_labels[month] = label
        for index in indices or config.indices:
            lines.append(f"## {index} ({config.role(index)})")
            lines.append("")
            for model in config.models:
                lines.append(f"### {MODEL_LABELS[model]} model")
                lines.append("")
                table = self.summary_table(results, index, model)
                header = ["Term"] + [month_labels[month] for month in config.months]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("|" + " --- |" * len(header))
                for _, row in table.iterrows():
                    cells = [str(row["term"])] + [
                        str(row[month_name(month)]) for month in config.months
                    ]
                    lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
            lines.append("### Event estimates and placebo tests")
            lines.append("")
            lines.append(
                f"| Model | Month | beta {event_label} (95% CI) | p | "
                f"beta' {persist_label} (95% CI) | sigma_u | "
                "Placebo-space p | Placebo-space-time p |"
            )
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for model in config.models:
                for month in config.months:
                    rows = primary.loc[
                        primary["model"].eq(model)
                        & primary["index"].eq(index)
                        & primary["month"].eq(month)
                    ].set_index("term")
                    event = rows.loc[EVENT_TERM]
                    space_p = self._placebo_p(
                        results.placebo_space, model, index, month
                    )
                    spacetime_p = self._placebo_p(
                        results.placebo_spacetime, model, index, month
                    )
                    persist_cell = "--"
                    if PERSIST_TERM in rows.index:
                        persist_cell = _estimate_cell(rows.loc[PERSIST_TERM])
                    lines.append(
                        f"| {MODEL_LABELS[model]} | {month_labels[month]} "
                        f"| {_estimate_cell(event)} | {event['p_value']:.2g} "
                        f"| {persist_cell} | {event['sigma_u']:.4f} "
                        f"| {space_p:.3f} | {spacetime_p:.3f} |"
                    )
            lines.append("")
        return "\n".join(lines)

    def _summary_row(
        self, section: str, term: str, cells: dict[int, tuple[str, dict[str, float]]]
    ) -> dict:
        """Assemble one summary-table row from per-month formatted/numeric cells."""
        row: dict = {"section": section, "term": term}
        for month, (formatted, numbers) in cells.items():
            label = month_name(month)
            row[label] = formatted
            for key in ("estimate", "ci_low", "ci_high", "p_value"):
                row[f"{label}_{key}"] = numbers.get(key, np.nan)
        return row

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
        """Convert one fit's event indicators into tagged per-term output rows."""
        event_pair, persist_pair = self.config.event_pairs
        cells = {EVENT_TERM: event_pair, PERSIST_TERM: persist_pair}
        rows = []
        for name, pair in cells.items():
            if name not in fit.terms:
                continue
            term = fit.terms[name]
            rows.append({
                **tags,
                "variant": variant.name,
                "tau": variant.tau,
                "fill_method": variant.fill_method,
                "term": name,
                "event_year_start": pair[0],
                "event_year_end": pair[1],
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

    def _effect_rows(
        self,
        tags: dict,
        variant: Variant,
        handled: pd.DataFrame,
        fit: WeightedFitResult,
    ) -> list[dict]:
        """Convert one primary fit's fixed-effect blocks into tagged output rows.

        Each block contributes one deviation-coded effect per level (the
        omitted level's effect is derived as minus the block's sum) and one
        joint Wald F-test row.
        """
        base = {
            **tags,
            "variant": variant.name,
            "tau": variant.tau,
            "fill_method": variant.fill_method,
            "df": fit.df,
        }
        rows = []
        for block, levels in effect_levels(
            handled, site_effects=fit.site_effects
        ).items():
            block_columns = [column for _, column in levels if column is not None]
            for level, column in levels:
                if column is None:
                    term = omitted_level_term(
                        fit, block_columns, f"{block}_{level}", self.config.alpha
                    )
                else:
                    term = fit.terms[column]
                rows.append({
                    **base,
                    "group": block,
                    "level": level,
                    "estimate": term.estimate,
                    "se": term.se,
                    "ci_low": term.ci_low,
                    "ci_high": term.ci_high,
                    "p_value": term.p_value,
                    "significant": term.significant,
                    "derived": column is None,
                    "statistic": np.nan,
                    "df_num": np.nan,
                })
            test = joint_wald_test(fit, block_columns, block)
            rows.append({
                **base,
                "group": f"{block}_joint",
                "level": "",
                "estimate": np.nan,
                "se": np.nan,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "p_value": test.p_value,
                "significant": test.p_value < self.config.alpha,
                "derived": False,
                "statistic": test.statistic,
                "df_num": test.df_num,
            })
        return rows

    @staticmethod
    def _placebo_p(
        placebo: pd.DataFrame, model: str, index: str, month: int
    ) -> float:
        """Return the month's placebo p-value for one model and index."""
        rows = placebo.loc[
            placebo["model"].eq(model)
            & placebo["index"].eq(index)
            & placebo["month"].eq(month)
        ]
        return float(rows["p_value"].iloc[0])


def _estimate_cell(row: pd.Series) -> str:
    """Format one estimate with its confidence interval for the summary table."""
    return f"{row['estimate']:.3f} ({row['ci_low']:.3f}, {row['ci_high']:.3f})"


def _event_cell(row: pd.Series) -> tuple[str, dict[str, float]]:
    """Format one event term's summary cell with its numeric companions."""
    significant = row["ci_low"] > 0.0 or row["ci_high"] < 0.0
    return (
        _estimate_cell(row) + ("*" if significant else ""),
        {
            "estimate": float(row["estimate"]),
            "ci_low": float(row["ci_low"]),
            "ci_high": float(row["ci_high"]),
            "p_value": float(row["p_value"]),
        },
    )


def _effect_cell(row: pd.Series) -> tuple[str, dict[str, float]]:
    """Format one deviation-coded effect's summary cell with its numerics."""
    return (
        f"{row['estimate']:.3f}" + ("*" if bool(row["significant"]) else ""),
        {
            "estimate": float(row["estimate"]),
            "ci_low": float(row["ci_low"]),
            "ci_high": float(row["ci_high"]),
            "p_value": float(row["p_value"]),
        },
    )


def _p_cell(row: pd.Series) -> tuple[str, dict[str, float]]:
    """Format one joint-test p-value summary cell with its numerics."""
    return f"{row['p_value']:.3f}", {"p_value": float(row["p_value"])}


def _level_label(group: str, level: str) -> str:
    """Return the display label for one effect level."""
    if group == "pair":
        year_start, year_end = level.split("_")
        return _pair_label(int(year_start), int(year_end))
    return level


def _pair_label(year_start: int, year_end: int) -> str:
    """Format one year pair as 2023–24."""
    return f"{year_start}\u2013{year_end % 100:02d}"
