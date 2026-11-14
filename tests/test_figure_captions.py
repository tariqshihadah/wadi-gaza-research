import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_figure_captions", ROOT / "notebooks" / "generate_figure_captions.py"
)
assert SPEC is not None and SPEC.loader is not None
captions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(captions)


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    write(tmp_path / captions.SOURCE, (ROOT / captions.SOURCE).read_text(encoding="utf-8"))
    for path in (ROOT / "docs" / "white-papers").glob("*.md"):
        write(tmp_path / "docs" / "white-papers" / path.name, "Method reference")
    settings = {
        "12_visualize_change_results.ipynb": "PLOT_INDEX = 'NDVI'",
        "14_visualize_index_results.ipynb": (
            "PLOT_INDEX = 'NDVI'\nPLOT_MONTH = '09'\nBASE_YEAR = 2019"
        ),
        "22_visualize_climate_context.ipynb": "FOCUS_SITE = 'WadiGaza'",
        "31_visualize_did_results.ipynb": "",
    }
    for name, code in settings.items():
        write(tmp_path / "notebooks" / name, json.dumps({
            "cells": [{"cell_type": "code", "source": [code]}],
        }))
    config = {
        "alpha": 0.1, "tau": 0.06, "tau_sensitivity": [0.02, 0.06, 0.1],
        "min_n_eff": 25, "fill_n_eff": 4, "affected_site": "WadiGaza",
        "event_pairs": [[2023, 2024], [2024, 2025]],
        "reference_period": [1991, 2020], "study_years": [2019, 2025],
        "near_zero_normal_mm": 10,
    }
    for group in ("change_ci/NDVI", "change_ci/SAVI", "index_ci/NDVI",
                  "change_did/NDVI", "climate"):
        write(tmp_path / "outputs" / group / "config.json", json.dumps(config))
    return tmp_path


def test_catalogs_select_current_figures_and_use_saved_settings(project):
    selected = [
        "change_ci/NDVI/plots/WadiGaza_mean_change_timeseries.png",
        "change_ci/SAVI/plots/WadiGaza_SAVI_mean_change_month_panels.png",
        "change_did/NDVI/plots/period_only/combined_evidence.png",
        "climate/plots/regional_temperature_anomaly.png",
        "climate/plots/WadiGaza_temperature_anomaly.png",
        "index_ci/NDVI/plots/WadiGaza_vs_study_areas_index_change_from_2019.png",
    ]
    excluded = [
        "change_ci/SAVI/plots/WadiGaza_mean_change_timeseries.png",
        "change_ci/NDVI/plots/WadiGaza_mean_change_heatmap_01.png",
        "change_ci/NDVI/plots/study_area_mean_change_2023_2024_month_01.png",
        "index_ci/NDVI/plots/WadiGaza_vs_study_areas_index_change_from_2020.png",
        "_archive/prior/uncaptioned.png",
        "climate/raw/uncaptioned.png",
    ]
    for name in selected + excluded:
        write(project / "outputs" / name, name)
    assert captions.generate_catalogs(project) == len(selected)
    catalog = project / "outputs/change_ci/NDVI/plots/CAPTIONS.md"
    text = catalog.read_text()
    assert "90% Student's t" in text
    assert "tau = 0.06" in text
    assert "WadiGaza_mean_change_heatmap_01.png" not in text
    assert "![Wadi Gaza NDVI change trajectories]" in text
    model_text = (project / "outputs/change_did/NDVI/plots/period_only/CAPTIONS.md").read_text()
    assert "period-only model" in model_text
    assert "Period-Only-Control-Impact-Analysis.md" in model_text
    assert "reduced-sample real" in model_text
    for name in selected:
        catalog_text = (project / "outputs" / name).with_name("CAPTIONS.md").read_text()
        entries = catalog_text.split("**Caption.** ")[1:]
        for entry in entries:
            caption, remainder = entry.split("\n\n", 1)
            assert caption
            assert remainder.startswith("**Explanation.** ")
            assert len(caption.split()) <= 40
    assert captions.generate_catalogs(project, check=True) == len(selected)


@pytest.mark.parametrize("field", ["caption", "explanation"])
def test_check_detects_changes_to_either_text_field(project, field):
    figure = write(project / "outputs/climate/plots/regional_normals.png", "figure")
    captions.generate_catalogs(project)
    catalog = figure.with_name("CAPTIONS.md")
    original = catalog.read_text()
    source_path = project / captions.SOURCE
    source = yaml.safe_load(source_path.read_text())
    recipe = next(recipe for recipe in source["figures"]
                  if recipe["pattern"] == r"climate/plots/regional_normals\.png")
    recipe[field] = "Revised " + recipe[field]
    source_path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="out of date"):
        captions.generate_catalogs(project, check=True)
    assert catalog.read_text() == original
    captions.generate_catalogs(project)
    assert "Revised " in catalog.read_text().split(f"**{field.title()}.** ")[1]


@pytest.mark.parametrize("caption", ["", "First line.\nSecond line."])
def test_captions_require_a_nonempty_single_line(project, caption):
    write(project / "outputs/climate/plots/regional_normals.png", "figure")
    source_path = project / captions.SOURCE
    source = yaml.safe_load(source_path.read_text())
    recipe = next(recipe for recipe in source["figures"]
                  if recipe["pattern"] == r"climate/plots/regional_normals\.png")
    recipe["caption"] = caption
    source_path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="nonempty single line"):
        captions.generate_catalogs(project)
    assert not list(project.rglob("CAPTIONS.md"))


def test_check_detects_image_prose_and_selection_changes(project):
    figure = write(
        project / "outputs/index_ci/NDVI/plots/WadiGaza_mean_index_timeseries.png", "old"
    )
    captions.generate_catalogs(project)
    catalog = figure.with_name("CAPTIONS.md")
    original = catalog.read_text()
    figure.write_text("replacement")
    with pytest.raises(ValueError, match="out of date"):
        captions.generate_catalogs(project, check=True)
    assert catalog.read_text() == original
    captions.generate_catalogs(project)
    source = project / captions.SOURCE
    source.write_text(source.read_text().replace(
        "Annual spatial mean of the", "Annual site-average value of the"
    ))
    with pytest.raises(ValueError, match="out of date"):
        captions.generate_catalogs(project, check=True)
    captions.generate_catalogs(project)
    notebook = project / "notebooks/14_visualize_index_results.ipynb"
    notebook.write_text(notebook.read_text().replace("NDVI", "SAVI"))
    with pytest.raises(ValueError, match="out of date"):
        captions.generate_catalogs(project, check=True)
    assert captions.generate_catalogs(project) == 0
    assert "No figures in this folder" in catalog.read_text()


def test_unknown_or_ambiguous_figures_fail_before_any_writes(project):
    write(project / "outputs/climate/plots/new_layout.png", "new")
    write(project / "outputs/climate/plots/regional_normals.png", "known")
    with pytest.raises(ValueError, match="new_layout.png"):
        captions.generate_catalogs(project)
    assert not list(project.rglob("CAPTIONS.md"))
    (project / "outputs/climate/plots/new_layout.png").unlink()
    source_path = project / captions.SOURCE
    source = yaml.safe_load(source_path.read_text())
    source["figures"].append(next(
        recipe.copy() for recipe in source["figures"]
        if recipe["pattern"] == r"climate/plots/regional_normals\.png"
    ))
    source_path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="2 caption templates"):
        captions.generate_catalogs(project)
    assert not list(project.rglob("CAPTIONS.md"))


def test_missing_metadata_and_manual_catalog_are_not_silently_accepted(project):
    figure = write(project / "outputs/climate/plots/regional_normals.png", "figure")
    config = project / "outputs/climate/config.json"
    saved = config.read_text()
    config.unlink()
    with pytest.raises(FileNotFoundError):
        captions.generate_catalogs(project)
    config.write_text(saved)
    catalog = write(figure.with_name("CAPTIONS.md"), "Hand-edited caption")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        captions.generate_catalogs(project)
    assert catalog.read_text() == "Hand-edited caption"


def test_deleted_figure_does_not_leave_a_stale_caption(project):
    figure = write(project / "outputs/climate/plots/regional_normals.png", "figure")
    captions.generate_catalogs(project)
    figure.unlink()
    with pytest.raises(ValueError, match="out of date"):
        captions.generate_catalogs(project, check=True)
    captions.generate_catalogs(project)
    assert "Figure:" not in figure.with_name("CAPTIONS.md").read_text()


def test_dynamic_notebook_selections_fail_explicitly(project):
    notebook = project / "notebooks/14_visualize_index_results.ipynb"
    notebook.write_text(notebook.read_text().replace(
        "BASE_YEAR = 2019", "BASE_YEAR = choose_year()"
    ))
    with pytest.raises(ValueError):
        captions.generate_catalogs(project)
