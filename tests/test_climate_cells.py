from pathlib import Path

import pytest

from cds_pull.cells import (
    assign_cells,
    cell_box,
    cell_id,
    cells_geodataframe,
    load_sites,
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


def test_cell_box_is_one_tenth_degree():
    minx, miny, maxx, maxy = cell_box(31.5, 34.4).bounds

    assert maxx - minx == pytest.approx(0.1)
    assert maxy - miny == pytest.approx(0.1)
    assert (minx + maxx) / 2 == pytest.approx(34.4)


def test_assign_cells_matches_study_site_table():
    sites = load_sites(ROOT / "sites" / "StudySites.gpkg", "site_name")
    table = assign_cells(sites, "site_name").set_index("site")

    expected = {
        "AlAhrashProtectorate": "N31.3_E34.2",
        "BesorStream": "N31.4_E34.5",
        "HaBesorNationalPark": "N31.3_E34.5",
        "HolotNizzanim": "N31.7_E34.6",
        "HolotPalmahim": "N31.9_E34.7",
        "NahalRubin": "N31.9_E34.7",
        "WadiGaza": "N31.5_E34.4",
    }
    assert table["cell_id"].to_dict() == expected
    assert table.loc["HolotPalmahim", "shared_with"] == "NahalRubin"
    assert table.loc["NahalRubin", "shared_with"] == "HolotPalmahim"
    assert table.loc["WadiGaza", "shared_with"] == ""
    assert (table["distance_km"] < 7.5).all()
    assert not table["substituted"].any()
    assert len(cells_geodataframe(table.reset_index())) == 6
