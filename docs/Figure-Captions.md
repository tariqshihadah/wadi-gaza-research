# Figure captions

One-line paper captions and detailed explanations are generated next to the figures as `CAPTIONS.md`,
with relative image links, inline previews, source-notebook links, and method
references. Open a catalog in VS Code's Markdown preview to browse it.
Figure numbers belong to the manuscript, not to this catalog.
Each figure has a **Caption** for use beneath the figure in the paper and an
**Explanation** retaining the fuller methodological and interpretive notes.

## Browse the captions

- Change estimates: [NDVI](../outputs/change_ci/NDVI/plots/CAPTIONS.md),
  [GNDVI](../outputs/change_ci/GNDVI/plots/CAPTIONS.md),
  [SAVI](../outputs/change_ci/SAVI/plots/CAPTIONS.md),
  [NDRE](../outputs/change_ci/NDRE/plots/CAPTIONS.md), and
  [change correlograms](../outputs/change_ci/NDVI/plots/correlograms/CAPTIONS.md).
- Annual index levels: [NDVI](../outputs/index_ci/NDVI/plots/CAPTIONS.md).
- Comparison-model context:
  [NDVI](../outputs/change_did/NDVI/plots/CAPTIONS.md),
  [GNDVI](../outputs/change_did/GNDVI/plots/CAPTIONS.md),
  [SAVI](../outputs/change_did/SAVI/plots/CAPTIONS.md),
  [NDRE](../outputs/change_did/NDRE/plots/CAPTIONS.md).
- Site + period model:
  [NDVI](../outputs/change_did/NDVI/plots/site_period/CAPTIONS.md),
  [GNDVI](../outputs/change_did/GNDVI/plots/site_period/CAPTIONS.md),
  [SAVI](../outputs/change_did/SAVI/plots/site_period/CAPTIONS.md),
  [NDRE](../outputs/change_did/NDRE/plots/site_period/CAPTIONS.md).
- Period-only model:
  [NDVI](../outputs/change_did/NDVI/plots/period_only/CAPTIONS.md),
  [GNDVI](../outputs/change_did/GNDVI/plots/period_only/CAPTIONS.md),
  [SAVI](../outputs/change_did/SAVI/plots/period_only/CAPTIONS.md),
  [NDRE](../outputs/change_did/NDRE/plots/period_only/CAPTIONS.md).
- Cross-index comparisons: [levels](../outputs/index_comparison/plots/CAPTIONS.md),
  [site + period](../outputs/index_comparison/plots/site_period/CAPTIONS.md),
  [period-only](../outputs/index_comparison/plots/period_only/CAPTIONS.md).
- [Climate context](../outputs/climate/plots/CAPTIONS.md).

## One maintained source

Edit [figure-captions.yaml](figure-captions.yaml), not the generated catalogs.
One template covers a figure family across sites, indices, months, or model
specifications. Shared prose explains spatial intervals, model intervals, and
placebo procedures consistently. The white papers remain authoritative for
methods. Maintain a short, single-sentence `caption` and a separate detailed
`explanation` for each family; keep technical elaboration in the explanation.
Captions deliberately describe the figure rather than hard-coding
effect sizes or conclusions that could become stale.

The generator reads numerical method settings from saved output `config.json`
snapshots, **not** from the editable acquisition/analysis configuration files.
The literal `PLOT_INDEX`, `PLOT_MONTH`, `BASE_YEAR`, and `FOCUS_SITE` settings in
the saved visualization notebooks select the relevant figure variants.
Save notebook setting changes before regenerating captions. Dynamic expressions
for these settings require updating the generator; unsupported expressions fail
explicitly rather than guessing.

Only figures produced by the current notebook selections are included.
Superseded single-panel change heatmaps and figures from other selections are
excluded without deleting them. Archives and raw climate caches are not scanned.
Notebook 12 currently produces all-index monthly site panels and heatmaps, but
its correlograms and other focus figures use only `PLOT_INDEX`. Notebook 14 also
uses only `PLOT_INDEX`; notebook 31 produces all configured indices and models.

## Refresh and check

The final cells in visualization notebooks 12, 14, 22, and 31 regenerate the
catalogs automatically, including when those notebooks run through
[run_all.py](../notebooks/run_all.py). After running only selected plotting
cells, changing caption prose, or replacing figure files, run from the project
root with the project environment active:

```bash
python notebooks/generate_figure_captions.py
python notebooks/generate_figure_captions.py --check
```

The second command is read-only and exits unsuccessfully if a catalog is
missing/stale or a new figure has no unique caption template. New layouts need
a template, notebook and method references, and any filename captures required
by their prose. Intentionally retired layouts belong in the explicit `retired`
list; do not broaden that list to hide uncaptioned new work.

Catalogs are deterministic and version-controlled. Image hashes make a replaced
figure detectable by `--check`, even if its filename is unchanged. Deleted or
unselected figures disappear from regenerated catalogs; formerly generated
catalogs with no remaining selected figures say so. Manually maintained
catalogs are not overwritten.

**Review before publication.** The check establishes catalog coverage and
freshness, not that an image was recomputed from its accompanying saved
configuration. Rerun the affected analysis and visualization notebooks together
when inputs or methods change. When plotting semantics change (colors, error
bars, models, reference periods, etc.), update the template as part of the same
change. Spatial mean CIs, model-effect CIs, and climate interannual standard
deviations are different quantities and should not be interchanged. The
space-and-time placebo p-value uses a reduced-sample real refit, not necessarily
the main estimate shown in a combined-evidence panel.
