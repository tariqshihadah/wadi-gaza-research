"""Download the ERA5-Land time series for the configured region.

One CDS request covers every grid point in ``region_lat`` x ``region_lon``.
The box edges in the request are padded by half a cell, because the CDS
excludes grid points lying exactly on the northern and eastern edges. The
returned zip is kept untouched under ``<output_dir>/raw/region/``, its NetCDF
files are extracted beside it, and a ``request.json`` sidecar records the
request and provenance, which is also written to ``download_manifest.csv``.
An existing download is reused unless ``force=True``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pandas as pd

from .cells import GRID_STEP_DEG, grid_cells
from .config import ClimateConfig
from .io import cell_table, open_region

logger = logging.getLogger(__name__)

SIDECAR_NAME = "request.json"
DATA_FORMAT = "netcdf"


def request_date_range(config: ClimateConfig) -> str:
    """Return the CDS ``date`` value for the configured extraction range.

    Hourly precipitation is period-ending, so the last day's total needs the
    value stamped 00:00 on the following day. The request therefore ends one
    day after ``extraction_range[1]``.
    """
    start, end = config.extraction_range
    return f"{start.isoformat()}/{(end + timedelta(days=1)).isoformat()}"


def request_area(config: ClimateConfig) -> list[float]:
    """Return the CDS ``area`` value [north, west, south, east], padded by half a cell."""
    half = GRID_STEP_DEG / 2
    (south, north), (west, east) = config.region_lat, config.region_lon
    return [round(north + half, 2), round(west - half, 2), round(south - half, 2), round(east + half, 2)]


def build_request(config: ClimateConfig) -> dict[str, Any]:
    """Return the regional request body, using the dataset form's parameter names.

    NetCDF is used because a CSV area request exceeds the CDS size limit.
    """
    return {
        "variable": list(config.variables),
        "area": request_area(config),
        "date": [request_date_range(config)],
        "data_format": DATA_FORMAT,
    }


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ClimateDownloader:
    """Download and cache the regional ERA5-Land time series.

    Parameters
    ----------
    config : ClimateConfig
        Pipeline settings; raw files go under ``config.output_dir / "raw" / "region"``.
    client : object, optional
        A ``cdsapi.Client`` (or compatible object with ``retrieve``). Created
        lazily from ``~/.cdsapirc`` when omitted.
    """

    def __init__(self, config: ClimateConfig, client: Any | None = None) -> None:
        self.config = config
        self.raw_dir = config.output_dir / "raw" / "region"
        self._client = client

    @property
    def client(self) -> Any:
        """Return the CDS client, creating it on first use."""
        if self._client is None:
            import cdsapi

            self._client = cdsapi.Client()
        return self._client

    def download(self, *, force: bool = False) -> dict[str, Any]:
        """Download the region (or reuse the cache) and return its manifest record."""
        sidecar = self.raw_dir / SIDECAR_NAME
        if sidecar.exists() and not force:
            logger.info("Reusing cached regional download in %s", self.raw_dir)
            record = json.loads(sidecar.read_text(encoding="utf-8"))
            self._write_manifest(record)
            return record

        if self.raw_dir.exists():
            shutil.rmtree(self.raw_dir)
        self.raw_dir.mkdir(parents=True)
        request = build_request(self.config)
        archive = self.raw_dir / "region.zip"
        logger.info("Requesting %s for area %s", self.config.dataset, request["area"])
        self.client.retrieve(self.config.dataset, request).download(str(archive))

        with zipfile.ZipFile(archive) as bundle:
            names = sorted(name for name in bundle.namelist() if name.endswith(".nc"))
            for name in names:
                (self.raw_dir / Path(name).name).write_bytes(bundle.read(name))

        cells = cell_table(open_region(self.raw_dir))
        expected = set(grid_cells(self.config.region_lat, self.config.region_lon)["cell_id"])
        if set(cells["cell_id"]) != expected:
            raise ValueError(
                f"Returned grid does not match the configured region: "
                f"missing {sorted(expected - set(cells['cell_id']))}, "
                f"extra {sorted(set(cells['cell_id']) - expected)}"
            )

        record = {
            "dataset": self.config.dataset,
            "request": json.dumps(request, sort_keys=True),
            "area": json.dumps(request["area"]),
            "date_range": request["date"][0],
            "n_cells": len(cells),
            "n_cells_with_data": int(cells["has_data"].sum()),
            "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cdsapi_version": version("cdsapi"),
            "raw_path": str(archive.relative_to(self.config.output_dir)),
            "sha256": sha256(archive),
            "files": ";".join(Path(name).name for name in names),
        }
        sidecar.write_text(json.dumps(record, indent=2), encoding="utf-8")
        self._write_manifest(record)
        return record

    def _write_manifest(self, record: dict[str, Any]) -> None:
        pd.DataFrame([record]).to_csv(self.config.output_dir / "download_manifest.csv", index=False)
