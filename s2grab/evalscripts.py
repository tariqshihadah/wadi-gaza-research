"""Evalscripts — a small hybrid system for building Process API evalscripts.

Three tiers, from simplest to most flexible:

1. Presets by name: ``resolve("true_color")``, ``"indices"``, ``"full"``.
2. Generated on demand: ``make_evalscript(bands=["B04","B08"], indices=["NDVI"])``.
3. Raw passthrough: hand any ``//VERSION=3`` string straight through.

The generator (:func:`make_evalscript`) unions the input bands an evalscript
needs, emits a correct ``setup()`` / ``evaluatePixel()``, and produces a matching
list of band names — so the output band count and names can never desync (the
bug class that plagued the old monolithic script).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Union


@dataclass(frozen=True)
class Index:
    """A spectral index: its name, the bands it needs, and its JS expression.

    ``expr`` is a JavaScript expression referencing sample bands as ``s.Bxx``.
    """

    name: str
    bands: tuple[str, ...]
    expr: str


@dataclass(frozen=True)
class EvalScript:
    """A ready evalscript string plus the band names it produces (in order)."""

    script: str
    band_names: Union[tuple[str, ...], None] = None


# Library of known indices. Add a line here to make a new index available.
INDEX_LIBRARY: dict[str, Index] = {
    "NDVI": Index("NDVI", ("B08", "B04"), "(s.B08 - s.B04) / (s.B08 + s.B04)"),
    "NDWI": Index("NDWI", ("B03", "B08"), "(s.B03 - s.B08) / (s.B03 + s.B08)"),
    "NDMI": Index("NDMI", ("B08", "B11"), "(s.B08 - s.B11) / (s.B08 + s.B11)"),
    "EVI": Index(
        "EVI",
        ("B08", "B04", "B02"),
        "2.5 * (s.B08 - s.B04) / (s.B08 + 6.0 * s.B04 - 7.5 * s.B02 + 1.0)",
    ),
    "GNDVI": Index("GNDVI", ("B08", "B03"), "(s.B08 - s.B03) / (s.B08 + s.B03)"),
    # SAVI soil-adjusted vegetation index. L = 0.428 (ESA value for Sentinel-2);
    # standard form multiplies by (1 + L) = 1.428.
    "SAVI": Index(
        "SAVI",
        ("B08", "B04"),
        "((s.B08 - s.B04) / (s.B08 + s.B04 + 0.428)) * 1.428",
    ),
    "NDRE": Index("NDRE", ("B8A", "B05"), "(s.B8A - s.B05) / (s.B8A + s.B05)"),
}

# All optical reflectance bands, in canonical order.
OPTICAL_BANDS = (
    "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12",
)

# Scene Classification (SCL) classes treated as unusable when masking clouds:
# 0 no-data, 1 saturated/defective, 3 cloud shadow, 8/9 cloud med/high,
# 10 thin cirrus, 11 snow/ice. Class 2 (dark area) is deliberately kept to
# avoid over-masking dark arid surfaces; the PI may revise this set.
DEFAULT_SCL_MASK = (0, 1, 3, 8, 9, 10, 11)

# Temporal reducers: each defines a JS ``agg(a)`` over an array of per-scene
# values (already filtered to finite numbers upstream). Used when ``reduce`` is
# set on :func:`make_evalscript` to composite many scenes into one pixel.
# Pixels with no valid observation return NaN so no-data is distinguishable
# from a genuine zero (important for QA metrics like % no-data).
REDUCERS: dict[str, str] = {
    "median": (
        "function agg(a){var b=a.filter(function(x){return isFinite(x);});"
        "if(!b.length)return NaN;b.sort(function(x,y){return x-y;});"
        "var m=b.length>>1;return (b.length&1)?b[m]:(b[m-1]+b[m])/2;}"
    ),
    "mean": (
        "function agg(a){var b=a.filter(function(x){return isFinite(x);});"
        "if(!b.length)return NaN;var s=0;for(var i=0;i<b.length;i++)s+=b[i];"
        "return s/b.length;}"
    ),
    "max": (
        "function agg(a){var b=a.filter(function(x){return isFinite(x);});"
        "if(!b.length)return NaN;var m=b[0];for(var i=1;i<b.length;i++)"
        "if(b[i]>m)m=b[i];return m;}"
    ),
    "min": (
        "function agg(a){var b=a.filter(function(x){return isFinite(x);});"
        "if(!b.length)return NaN;var m=b[0];for(var i=1;i<b.length;i++)"
        "if(b[i]<m)m=b[i];return m;}"
    ),
    # Population standard deviation across scenes; used for QA (composite
    # stability), not usually as a deliverable band.
    "std": (
        "function agg(a){var b=a.filter(function(x){return isFinite(x);});"
        "if(!b.length)return NaN;var m=0,i;for(i=0;i<b.length;i++)m+=b[i];"
        "m/=b.length;var v=0;for(i=0;i<b.length;i++){var d=b[i]-m;v+=d*d;}"
        "return Math.sqrt(v/b.length);}"
    ),
}


def make_evalscript(
    bands: Sequence[str] = (),
    indices: Sequence[Union[str, Index]] = (),
    *,
    sample_type: str = "FLOAT32",
    include_scl: bool = False,
    include_datamask: bool = False,
    reduce: Union[str, None] = None,
    mask_scl: Union[Sequence[int], bool, None] = None,
) -> EvalScript:
    """Generate an :class:`EvalScript` from reflectance bands and indices.

    Parameters
    ----------
    bands: reflectance bands to output, in order (e.g. ["B04", "B03", "B02"]).
    indices: index names (from :data:`INDEX_LIBRARY`) or :class:`Index` objects.
    sample_type: output sample type; FLOAT32 keeps physical reflectance/index values.
    include_scl: append the scene-classification band (integer classes).
    include_datamask: append the validity mask (1 where data exists, else 0).
    reduce: temporal reducer from :data:`REDUCERS` ("median", "mean", "max",
        "min"). When set, the script composites *all* scenes in the request
        window into one pixel (invalid pixels are skipped via dataMask). When
        None (default), a single scene/mosaic is returned.
    mask_scl: SCL classes to treat as unusable (clouds/shadows/etc.). Pass
        ``True`` for :data:`DEFAULT_SCL_MASK`, or an explicit sequence of class
        integers. In reduce mode these samples are skipped before compositing;
        in single-scene mode masked pixels are set to NaN. ``None`` (default)
        disables SCL masking.

    Returns
    -------
    EvalScript with a generated script and a matching ``band_names`` tuple.
    """
    bands = list(bands)
    index_objs = [
        idx if isinstance(idx, Index) else INDEX_LIBRARY[idx] for idx in indices
    ]

    if mask_scl is True:
        scl_classes: tuple[int, ...] = tuple(DEFAULT_SCL_MASK)
    elif mask_scl:
        scl_classes = tuple(mask_scl)
    else:
        scl_classes = ()

    # Union of every band the script must request as input (order-stable).
    input_bands: list[str] = []

    def _add_input(band: str) -> None:
        if band not in input_bands:
            input_bands.append(band)

    for b in bands:
        _add_input(b)
    for idx in index_objs:
        for b in idx.bands:
            _add_input(b)
    if include_scl:
        _add_input("SCL")
    # SCL is also needed as an input (not necessarily an output) when masking.
    if scl_classes:
        _add_input("SCL")
    # dataMask is needed as an output and, in reduce mode, to skip invalid pixels.
    if include_datamask or reduce is not None:
        _add_input("dataMask")

    # Output values + their names, in a deterministic order.
    output_exprs: list[str] = []
    band_names: list[str] = []
    for b in bands:
        output_exprs.append(f"s.{b}")
        band_names.append(b)
    for idx in index_objs:
        output_exprs.append(idx.expr)
        band_names.append(idx.name)
    if include_scl:
        output_exprs.append("s.SCL")
        band_names.append("SCL")
    if include_datamask:
        output_exprs.append("s.dataMask")
        band_names.append("dataMask")

    if not output_exprs:
        raise ValueError("make_evalscript() requires at least one band or index.")

    input_list = ", ".join(f'"{b}"' for b in input_bands)
    n_out = len(output_exprs)
    scl_skip = " || ".join(f"s.SCL === {c}" for c in scl_classes)

    if reduce is None:
        return_list = ", ".join(output_exprs)
        nan_list = ", ".join("NaN" for _ in output_exprs)
        mask_line = f"  if ({scl_skip}) return [{nan_list}];\n" if scl_classes else ""
        script = (
            "//VERSION=3\n"
            "function setup() {\n"
            "  return {\n"
            f"    input: [{{ bands: [{input_list}] }}],\n"
            f'    output: {{ bands: {n_out}, sampleType: "{sample_type}" }}\n'
            "  };\n"
            "}\n"
            "function evaluatePixel(s) {\n"
            f"{mask_line}"
            f"  return [{return_list}];\n"
            "}\n"
        )
    else:
        if reduce not in REDUCERS:
            raise ValueError(
                f"Unknown reducer '{reduce}'. Available: {sorted(REDUCERS)}"
            )
        push_lines = "\n".join(
            f"    acc[{j}].push({expr});" for j, expr in enumerate(output_exprs)
        )
        return_list = ", ".join(f"agg(acc[{j}])" for j in range(n_out))
        skip_line = f"    if ({scl_skip}) continue;\n" if scl_classes else ""
        script = (
            "//VERSION=3\n"
            "function setup() {\n"
            "  return {\n"
            f"    input: [{{ bands: [{input_list}] }}],\n"
            f'    output: {{ bands: {n_out}, sampleType: "{sample_type}" }},\n'
            '    mosaicking: "ORBIT"\n'
            "  };\n"
            "}\n"
            f"{REDUCERS[reduce]}\n"
            "function evaluatePixel(samples) {\n"
            "  var acc = [];\n"
            f"  for (var k = 0; k < {n_out}; k++) acc.push([]);\n"
            "  for (var i = 0; i < samples.length; i++) {\n"
            "    var s = samples[i];\n"
            "    if (s.dataMask === 0) continue;\n"
            f"{skip_line}"
            f"{push_lines}\n"
            "  }\n"
            f"  return [{return_list}];\n"
            "}\n"
        )
    return EvalScript(script=script, band_names=tuple(band_names))


# Named presets, all built from the generator so nothing is hand-desynced.
PRESETS: dict[str, EvalScript] = {
    "true_color": make_evalscript(bands=["B04", "B03", "B02"]),
    "ndvi": make_evalscript(indices=["NDVI"]),
    "indices": make_evalscript(indices=["NDVI", "EVI", "NDWI", "NDMI"]),
    "full": make_evalscript(
        bands=list(OPTICAL_BANDS),
        indices=["NDVI", "EVI", "NDWI", "NDMI"],
        include_scl=True,
        include_datamask=True,
    ),
}


def resolve(product: Union[str, EvalScript]) -> EvalScript:
    """Resolve a product into an :class:`EvalScript`.

    Accepts a preset name, an :class:`EvalScript`, or a raw ``//VERSION=3``
    evalscript string (whose band names are unknown, so left as None).
    """
    if isinstance(product, EvalScript):
        return product
    if isinstance(product, str):
        if product in PRESETS:
            return PRESETS[product]
        if "//VERSION" in product:
            return EvalScript(script=product, band_names=None)
        raise KeyError(
            f"Unknown product '{product}'. Presets: {sorted(PRESETS)}"
        )
    raise TypeError(f"product must be str or EvalScript, got {type(product)!r}")


# --- Back-compatible helpers (used by earlier examples) ----------------------
def get(name: str) -> str:
    """Return the evalscript string for a preset name."""
    return resolve(name).script


BAND_NAMES: dict[str, list[str]] = {
    name: list(es.band_names or []) for name, es in PRESETS.items()
}
