# Sentinel-2 Imagery Acquisition and Preparation for Mean Index Change Analysis

## 1. Purpose

This document describes how the Sentinel-2 imagery used in the study is acquired and prepared. It covers scene selection, per-pixel cloud masking, monthly median compositing, vegetation index calculation, and the rule that defines which pixels belong to each study site. The output is one masked, multi-band composite per study site and monthly window. Those composites are the input to the mean index change analysis described in [Confidence Intervals for Mean Index Change Under Spatial Autocorrelation](Mean-Index-Change-Confidence-Intervals.md).

The goal is a process that is fully reproducible from the study-site polygons and the parameters listed here, with every masking decision made once, by a documented rule, before any analysis takes place.

## 2. Scope and Data

**Study sites.** Seven protected areas are analyzed: Wadi Gaza (the primary site) and six comparison sites (Al Ahrash Protectorate, Besor Stream, HaBesor National Park, Holot Nizzanim, Holot Palmahim, and Nahal Rubin). Site boundaries are polygons stored in `sites/StudySites.gpkg` (EPSG:32636), derived mainly from the World Database on Protected Areas (WDPA). One polygon (HaBesor National Park) contains self-intersecting rings and is repaired with a standard geometry repair (`make_valid`) before use. No other changes are made to the boundaries.

**Imagery.** Sentinel-2 Level-2A (bottom-of-atmosphere surface reflectance) data are retrieved through the Sentinel Hub Processing API on the Copernicus Data Space Ecosystem. Eight reflectance bands are retrieved:

| Band | Name | Native resolution |
|---|---|---|
| B02 | Blue | 10 m |
| B03 | Green | 10 m |
| B04 | Red | 10 m |
| B05 | Red Edge 1 | 20 m |
| B08 | Near infrared (NIR) | 10 m |
| B8A | Narrow NIR | 20 m |
| B11 | Shortwave infrared 1 | 20 m |
| B12 | Shortwave infrared 2 | 20 m |

The Scene Classification Layer (SCL, 20 m) is also read, but only to mask unusable observations; it is not saved.

**Time windows.** Composites are built for whole calendar months: January, May, September, and November of each year from 2019 to 2025, giving 28 windows per site.

## 3. Notation

| Symbol | Meaning |
|---|---|
| $P$ | Study-site polygon, in the output grid's coordinate system |
| $p$ | A pixel of the output grid |
| $c(p)$ | Center point of pixel $p$ |
| $F$ | Study-area footprint: the set of pixels assigned to the site |
| $w$ | A monthly window (one calendar month of one year) |
| $S_w$ | Scenes acquired over the site during $w$ that pass the scene cloud filter |
| $x_{p,s}$ | Value of a band or index at pixel $p$ in scene $s$ |
| $V_{p,w}$ | Valid observations of pixel $p$ in window $w$ (after cloud masking) |
| $\tilde{x}_{p,w}$ | Composite (median) value of pixel $p$ for window $w$ |

## 4. Method

### 4.1 Output grid

Each site is processed on its own fixed grid. The grid uses the UTM zone containing the polygon's centroid (zone 36N, EPSG:32636, for every site) and covers the polygon's bounding box. The number of rows and columns is the bounding-box size divided by 10 m and rounded, so pixel edges come out at 9.98–10.02 m, depending on the site. The same grid is used for every window, so all composites for a site are co-registered pixel for pixel.

The 20 m inputs (B05, B8A, B11, B12, and SCL) are upsampled to the 10 m grid with nearest-neighbor resampling. This aligns all layers without interpolating new values. Bands and indices built from 20 m inputs therefore still carry only 20 m detail.

### 4.2 Scene selection

The catalog is searched for Sentinel-2 L2A scenes that intersect the site polygon (not its bounding box) during the window. Scenes are kept only if their scene-level cloud cover is below 20%. The same 20% limit is applied when imagery is requested, so the composite draws on the scenes counted in the quality checks (Section 5).

The scene-level filter only removes heavily clouded acquisitions. Clouds within the remaining scenes are handled pixel by pixel (Section 4.3).

### 4.3 Per-pixel cloud masking

Every observation of every pixel is checked against its SCL class. Only observations classified as vegetation (class 4), bare soil (5), or water (6) are kept. All other classes are discarded: no data (0), saturated or defective (1), dark area or topographic shadow (2), cloud shadow (3), unclassified (7), medium- and high-probability cloud (8, 9), thin cirrus (10), and snow or ice (11). Observations with no data are also discarded.

Keeping only these three classes follows the PI's guidance. Class 2 is included in the discarded set because, on the flat terrain of the study area, dark-area classifications are more likely to be cloud shadow than true topographic shadow. A diagnostic of the masking for Nahal Rubin is kept in the acquisition notebook. It counts each pixel's observations by SCL class, which shows how much data each alternative class set would keep.

### 4.4 Compositing and reflectance values

All scenes in $S_w$ are composited pixel by pixel. For each pixel, the composite value is the median of its valid observations:

$$
\tilde{x}_{p,w} = \operatorname{median}\left\{ x_{p,s} : s \in V_{p,w} \right\}
\tag{1}
$$

With an even number of observations, the median is the mean of the two middle values. A pixel with no valid observation in the window is left without a value (NaN), so missing data is never confused with a real zero. The number of observations behind each pixel's median varies with acquisition dates and cloud cover.

Band values are surface reflectance on a 0–1 scale. Sentinel Hub returns Sentinel-2 bands in reflectance units by default, which is equivalent to dividing the stored digital numbers by 10,000, so no further scaling is applied. Sentinel Hub's default value harmonization is also left on, for two reasons: it keeps values comparable across the January 2022 processing-baseline change, and it clamps occasional negative reflectances to zero ([Sentinel Hub, Sentinel-2 L2A](https://docs.sentinel-hub.com/api/latest/data/sentinel-2-l2a/)).

### 4.5 Vegetation indices

Four indices are computed for **every** study site, from the reflectance of each individual observation. The composite index is then the per-pixel median of those per-observation values (Equation 1). This is a median of indices, not an index of median bands.

| Index | Formula | Native detail |
|---|---|---|
| NDVI | $(B08 - B04) / (B08 + B04)$ | 10 m |
| GNDVI | $(B08 - B03) / (B08 + B03)$ | 10 m |
| SAVI | $\left( (B08 - B04) / (B08 + B04 + L) \right) \times (1 + L)$, with $L = 0.428$ | 10 m |
| NDRE | $(B8A - B05) / (B8A + B05)$ | 20 m |

Undefined values (for example, a zero denominator) are discarded with the other invalid observations. The soil brightness factor $L = 0.428$ follows the ESA value used for Sentinel-2.

### 4.6 Study-area footprint

A pixel belongs to a study site when its center lies inside the site polygon:

$$
F = \left\{ p : c(p) \in P \right\}
\tag{2}
$$

The footprint is computed once per site from its polygon and output grid. It uses the standard rasterization in GDAL and rasterio (`all_touched=False`). During acquisition, imagery is requested for the full bounding box, and every pixel outside $F$ is set to NaN before the composite is saved. This is the only masking step for the study area. Later steps read missing values as "outside the study area or no valid observation" and never re-mask.

**Basis for the rule.** Treating each pixel as wholly inside or outside the polygon, decided by its center, is the default in widely used geospatial software:

- GDAL rasterization by default includes pixels "whose center point is within the polygon" ([GDAL `gdal_rasterize`](https://gdal.org/en/stable/programs/gdal_rasterize.html)).
- rasterio's `geometry_mask` and `rasterize` behave the same way by default ([rasterio.features](https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html)).
- Google Earth Engine includes a pixel in an unweighted regional count "if [its] centroid is in the region" ([Earth Engine `reduceRegion`](https://developers.google.com/earth-engine/guides/reducers_reduce_region)).
- QGIS zonal statistics and R's `raster` package also use a centroid test ([exactextract background](https://isciences.github.io/exactextract/background.html)).

The main alternative, including every pixel the polygon touches, adds edge cells "that may not be representative of the geometry" ([rasterstats manual](https://pythonhosted.org/rasterstats/manual.html#rasterization-strategy)). These sources are software documentation; they establish the rule as standard practice but are not a statistical proof that it is unbiased.

**Area check.** For each site, the footprint area (pixel count times pixel area) matches the polygon area to within 0.15%:

| Site | Footprint pixels | Polygon area (ha) | Footprint vs. polygon area |
|---|---|---|---|
| Al Ahrash Protectorate | 33,848 | 338.1 | +0.01% |
| Besor Stream | 11,318 | 113.1 | −0.06% |
| HaBesor National Park | 91,755 | 918.7 | −0.01% |
| Holot Nizzanim | 139,638 | 1,395.2 | +0.01% |
| Holot Palmahim | 62,192 | 620.8 | +0.01% |
| Nahal Rubin | 7,860 | 78.4 | +0.15% |
| Wadi Gaza | 28,413 | 284.2 | +0.05% |

**Alternatives considered.**

- *Server-side clipping by Sentinel Hub.* An earlier version of the process clipped imagery on the server. The server's rule is not documented. On these grids it kept every pixel-center pixel plus most of the pixels the boundary touches, overstating site area by 1.0–3.7%. It was replaced so that one documented rule is applied by the project itself.
- *All touched.* Includes every pixel crossed by the boundary. This systematically overstates area and adds more mixed edge pixels.
- *Fully inside only, or a polygon shrunk by half a pixel.* Removes mixed edge pixels but systematically understates area. This would be preferable only if edge contamination were shown to matter.
- *Area-weighted pixels.* Weights each pixel by the fraction of it inside the polygon. This is more exact, but it is not a simple in-or-out mask and is not supported by the change analysis.

### 4.7 Valid pixels

After acquisition, a pixel value in a composite is valid when it is finite. A pixel can be invalid for two reasons:

1. It lies outside the footprint $F$, for every window.
2. It lies inside $F$ but had no valid observation in that window (an interior gap, Section 4.4). These are rare and occur at only some sites and windows.

For the mean index change analysis, a pixel is used for a pair of dates only if it is valid in both composites. The pixel count $N$ in that analysis is therefore the footprint size minus any interior gaps on either date.

## 5. Quality Checks

For every composite, the acquisition step records:

- **Scenes used** (`n_scenes`): the number of catalog scenes that intersect the polygon and pass the 20% scene cloud filter.
- **Mean scene cloud cover** (`mean_cloud`): the average scene-level cloud cover of those scenes, in percent.
- **No-data percentage** (`pct_nodata`): the percentage of footprint pixels with no valid observation in any band.
- **Mean per-pixel standard deviation** (`mean_pixel_std`): a measure of composite stability. For each pixel and layer, it takes the population standard deviation of the valid observations across scenes, then averages over all footprint pixels and layers.

Every saved composite records its footprint rule (`FOOTPRINT_RULE = pixel_center`) and footprint size (`FOOTPRINT_PIXELS`) in its metadata. It also records the provenance: site, window, scene count, scene cloud limit, masked SCL classes, resampling method, and source polygon file. The summary-statistics step uses `FOOTPRINT_PIXELS` as its denominator, and it checks that the rule, footprint size, and grid are identical across all of a site's windows.

Automated tests check three things: the footprint matches an independent pixel-center calculation, no saved pixel outside the footprint holds a value, and the recorded footprint size matches the mask. Two test windows (Wadi Gaza, September 2024; Nahal Rubin, January 2020) were re-fetched with the final process. Inside the footprint, they reproduced the earlier server-clipped composites' values exactly.

## 6. Assumptions and Notes

**Mixed edge pixels.** Pixels on the boundary may include land outside the site. The pixel-center rule keeps those whose centers are inside, which balances inclusion and exclusion so area is preserved, but it does not remove mixed pixels. This matters most for narrow sites such as Wadi Gaza, Besor Stream, and Nahal Rubin.

**Fixed footprint.** Each site has one footprint for all windows. Changes in valid area between windows come only from interior gaps, never from a change in the site boundary.

**Varying observation counts.** Each composite pixel is the median of however many valid observations the window provided. Pixels and windows with few observations are more sensitive to residual cloud, haze, or misclassification.

**Classification limits.** Cloud masking relies on the SCL product, which can misclassify bright soils, thin cloud, and cloud edges. Keeping only classes 4, 5, and 6 is a deliberately conservative choice that discards some usable observations to reduce contamination.

**Resampled 20 m information.** NDRE, the shortwave infrared bands, and B05 and B8A are delivered at 10 m but carry 20 m detail.

## 7. Reported Outputs

For each site and window, the outputs are:

- **Composite GeoTIFF** (`outputs/composites/<site>/<site>_<YYYY>-<MM>.tif`): 12 float32 bands, in order B02, B03, B04, B05, B08, B8A, B11, B12, NDVI, GNDVI, SAVI, and NDRE. Pixels outside the footprint, and interior gaps, are NaN. Metadata tags hold the footprint rule, footprint size, and provenance.
- **QA manifest** (`outputs/composites/qa_manifest.csv`): one row per composite with the status, the four quality metrics, and the file path.
- **Imagery statistics** (`outputs/composites/imagery_stats.csv`): one row per site, window, and index, with:
  - valid pixel count, footprint size, and percentage valid
  - total and valid area
  - mean, sample standard deviation, and quartiles of the index
  - scene count and mean cloud cover

The NDVI band of these composites is the input to the mean index change analysis.
