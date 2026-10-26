from pathlib import Path

import pytest

from cds_pull.cells import (
    assign_cells,
    cell_box,
    cell_id,
    cells_geodataframe,
    grid_cells,
    load_sites,
    parse_cell_id,
    predict_cell,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("lat", "lon", "expected"),
    [
        (31.4527, 34.4043, (31.5, 34.4)),
        (31.449, 34.351, (31.4, 34.4)),
        (31.451, 34.349, (31.5, 34.3)),
        (31.45, 34.35, (31.5, 34.4)),
    ],
)
def test_predict_cell_rounds_to_nearest_tenth(lat, lon, expected):
    assert predict_cell(lat, lon) == expected


def test_cell_id_formats_hemispheres():
    assert cell_id(31.5, 34.4) == "N31.5_E34.4"
    assert cell_id(-0.1, -3.0) == "S0.1_W3.0"


def test_parse_cell_id_round_trips():
    assert parse_cell_id("N31.5_E34.4") == (31.5, 34.4)
    assert parse_cell_id(cell_id(-0.1, -3.0)) == (-0.1, -3.0)


def test_grid_cells_is_inclusive():
    grid = grid_cells((31.2, 32.0), (34.2, 34.8))

    assert len(grid) == 63
    assert {"N31.2_E34.2", "N32.0_E34.8"} <= set(grid["cell_id"])


def test_cell_box_is_one_tenth_degree():
    minx, miny, maxx, maxy = cell_box(31.5, 34.4).bounds

    assert maxx - minx == pytest.approx(0.1)
    assert maxy - miny == pytest.approx(0.1)
    assert (minx + maxx) / 2 == pytest.approx(34.4)


def test_assign_cells_uses_centroid_cells_and_overrides():
    sites = load_sites(ROOT / "sites" / "StudySites.gpkg", "site_name")
    overrides = {"HolotPalmahim": "N31.9_E34.8", "NahalRubin": "N31.9_E34.8"}
    table = assign_cells(sites, "site_name", overrides).set_index("site")

    centroid_cells = {
        "AlAhrashProtectorate": "N31.3_E34.2",
        "BesorStream": "N31.4_E34.5",
        "HaBesorNationalPark": "N31.3_E34.5",
        "HolotNizzanim": "N31.7_E34.6",
        "HolotPalmahim": "N31.9_E34.7",
        "NahalRubin": "N31.9_E34.7",
        "WadiGaza": "N31.5_E34.4",
    }
    assert table["centroid_cell_id"].to_dict() == centroid_cells
    assert table.loc["HolotPalmahim", "cell_id"] == "N31.9_E34.8"
    assert table.loc["NahalRubin", "cell_lon"] == 34.8
    assert table.loc[["HolotPalmahim", "NahalRubin"], "assignment"].eq("manual").all()
    assert table.loc["WadiGaza", "assignment"] == "centroid"
    assert table.loc["HolotPalmahim", "shared_with"] == "NahalRubin"
    assert table.loc["WadiGaza", "shared_with"] == ""
    assert (table.loc[table["assignment"] == "centroid", "distance_km"] < 7.5).all()


def test_assign_cells_rejects_unknown_override_site():
    sites = load_sites(ROOT / "sites" / "StudySites.gpkg", "site_name")

    with pytest.raises(ValueError, match="unknown sites"):
        assign_cells(sites, "site_name", {"Nowhere": "N31.9_E34.8"})


def test_cells_geodataframe_keeps_one_box_per_cell():
    cells = cells_geodataframe(grid_cells((31.2, 31.3), (34.2, 34.3)).assign(has_data=True))

    assert len(cells) == 4
    assert cells.crs.to_epsg() == 4326
    assert "has_data" in cells
