> **Working document.** Original PI guidance written to direct the imagery
> pipeline. Notes marked *Implementation note* record where the implemented
> process differs or clarifies; the authoritative description of what was
> done is the white paper
> [Imagery Acquisition and Preparation](../white-papers/Imagery-Acquisition-and-Preparation.md).

# Vegetation Indices

*Sentinel-2 L2A imagery from Copernicus Browser:*

Images should be of the area containing Wadi Gaza and the comparison sites (encompassing 48 and northeast Sinai Peninsula)

We want **monthly composites of September, November, January, and May of 2019 \- 2024 for days with \< 10% cloud cover** (5% was the cutoff used in my paper; it can possibly be up to 10%  if there are not enough days like this)  
\-**Composite is composed of median values**

**Download these bands** (some will be used later for land cover analysis)**:**

| Band | Name | Native Resolution | Purpose |
| :---: | :---: | :---: | :---: |
| B2 | Blue | 10 m | Land-cover classification |
| B3 | Green | 10 m | Land-cover classification, GNDVI |
| B4 | Red | 10 m | Land-cover classification, NDVI, SAVI |
| B5 | Red Edge 1 | 20 m | NDRE |
| B8 | Near Infrared (NIR) | 10 m | NDVI, GNDVI, SAVI |
| B8A | Narrow NIR | 20 m | NDRE |
| B11 | Short wave infrared 1 | 20 m | Land-cover classification |
| B12 | SWIR 2 | 20 m | Land-cover classification |

**Keep documentation of (I don’t know how to keep track of this) :**  
\-% cloud cover  
\-Scene Classification Layer (SCL, provided by Sentinel-2)  
\-number of images (days) used in each composite  
\-mean pixel standard deviation  
\-% pixels with no data

**Apply cloud mask** using SCL data for each image (use it to identify clouds, cloud shadows), set those pixels to NaN (still need to do this even after filtering for cloud cover on Copernicus)

**Apply scaling factor** to images to convert to actual reflectance values: **Divide pixel values by 10,000**

> *Implementation note:* no manual division is applied. Sentinel Hub returns
> L2A bands as surface reflectance (0–1) when requested in reflectance units,
> which is equivalent to dividing the stored digital numbers by 10,000.

**Calculate monthly median** for each band.

**Calculate indices for these median band composites** (all indices for Wadi Gaza, NDVI ONLY for other study sites):

> *Implementation note:* all four indices (NDVI, GNDVI, SAVI, NDRE) are produced
> for **every** study site. Each index is computed per scene and the per-pixel
> median is then taken across scenes (median of indices), rather than computing
> indices from median band composites.

| Vegetation Index | Formula | Sentinel-2 Bands Used | Native Resolution | Purpose |
| ----- | :---: | :---: | :---: | ----- |
| **NDVI** (Normalized Difference Vegetation Index) | (B8 − B4) / (B8 \+ B4) | B8 (NIR), B4 (Red) | 10 m | Measures overall vegetation vigor and greenness; widely used indicator of photosynthetic activity. |
| **GNDVI** (Green Normalized Difference Vegetation Index) | (B8 − B3) / (B8 \+ B3) | B8 (NIR), B3 (Green) | 10 m | More sensitive to chlorophyll concentration and canopy condition than NDVI. |
| **SAVI** (Soil Adjusted Vegetation Index) | ((B8 − B4) / (B8 \+ B4 \+ L)) × (1 \+ L) | B8 (NIR), B4 (Red) | 10 m | Reduces the influence of exposed soil, making it useful in sparsely vegetated areas such as Wadi Gaza. |
| **NDRE** (Normalized Difference Red Edge Index) | (B8A − B5) / (B8A \+ B5) | B8A (Narrow NIR), B5 (Red Edge 1\) | 20 m | Sensitive to chlorophyll content and vegetation stress, particularly in denser vegetation. |

*\*Where L is soil brightness correction factor: 0.428 (value from European Space Agency for implementation of Sentinel-2 for this)*

**Clip each calculated index raster to the study area polygons** I have from the WDPA (all four for Wadi Gaza, only NDVI for other areas)

> *Implementation note:* clipping is done at acquisition with a pixel-center
> rule: a 10 m pixel belongs to a site when its center lies inside the site
> polygon. Pixels outside are set to NaN in every saved composite.

# Land Cover Change Analysis

**Resample** all bands to be used in this analysis to **10m resolution:** 

**Create multiband raster** using monthly median of these bands/indices (Wadi Gaza only, September 2019-2024 only):

| Layer Type | Layer Name / Index | Sentinel-2 L2A Band | Spatial Resolution | Core Purpose for Your Classification |
| ----- | ----- | ----- | ----- | ----- |
| **Raw Band** | **Blue** | Band 2 | 10 meters | Penetrates water bodies; helps map deep water and urban shadows. |
| **Raw Band** | **Green** | Band 3 | 10 meters | Reflects off healthy vegetation; maps shallow water and turbidity. |
| **Raw Band** | **Red** | Band 4 | 10 meters | Absorbed heavily by plants; crucial baseline for NDVI and SAVI formulas. |
| **Raw Band** | **Standard NIR** (Near-Infrared) | Band 8 | 10 meters | Reflects intensely off plant cell structures; essential for detecting any vegetation. |
| **Raw Band** | **SWIR 1** (Shortwave Infrared) | Band 11 | 20 meters | Absorbed entirely by water; highly reflective for bare soil and concrete/roofs. |
| **Raw Band** | **SWIR 2** (Shortwave Infrared) | Band 12 | 20 meters | Absorbed by moisture; separates dry bare ground from urban structures. |
| **Calculated Index** | **NDVI** (Normalized Difference Vegetation Index) | Formula using B8 & B4 | 10 meters | Creates a distinct gradient to separate **dense vs. sparse vegetation**. |
| **Calculated Index** | **SAVI** (Soil Adjusted Vegetation Index) | Formula using B8 & B4 | 10 meters | Suppresses background soil noise to accurately isolate **sparse vegetation**. |

I will **create training polygons in QGIS** using these multiband stacks. I will provide:   
Geometry, class name, class ID for Water, Bare Ground, Urban/Built Up, Dense Vegetation, and Sparse Vegetation

*Questions:*

\-How many training polygons do I need for each class (20?)? How big should they be (Not very?)? How spread out should they be?

\-How many different days/images should I use for training/how many models should be made? (I’m guessing separate model for each year’s September composite)

\-In what format should I provide this? GeoPackage? GeoJSON?

\-What should be the ratio of training data to testing data?

\-Do we need to do spatial cross-validation for this particular study? Do we need to use Moran’s I afterward?

*In Python:*

\-**Extract** training samples  
\-**Split** training and testing data. Training and testing should be performed at the polygon level rather than by randomly splitting individual pixels to reduce the effects of spatial autocorrelation and avoid inflated accuracy estimates.   
\-**Train** Random Forest using **scikit-learn**  
\-**Classify** the image(s)

## Accuracy assessment:

\-**Confusion matrix**: table comparing the **known (reference)** land-cover class of each testing pixel with the **class predicted** by the Random Forest model. The diagonal values represent correctly classified pixels. Off-diagonal values represent classification errors. Serves as the basis for all subsequent accuracy metrics.

\-**Overall Accuracy (OA)**: measures the proportion of all testing pixels that were correctly classified: ***Number of correctly classified pixels ÷ Total number of testing pixels***   
Provides a simple summary of classification performance but does not indicate which classes are performing well or poorly. 

\-**Producer’s Accuracy (PA)**: evaluates how well the classifier correctly identifies each reference class. Low producer's accuracy indicates that many pixels belonging to a class were omitted or incorrectly classified as another class (an **omission error**).  
*"Of all the pixels that truly belong to this class, how many were correctly identified?"* 

\-**User’s Accuracy (UA)**: evaluates the reliability of the classified map.   
*"If the map says this pixel is wetland, how often is that actually true?"* Low user's accuracy indicates that many pixels assigned to a class actually belong to another class (a **commission error**). 

\-**Cohen’s Kappa Coefficient:** measures the agreement between the classified map and the reference data while accounting for agreement that could occur by random chance. provides a more conservative assessment of classifier performance, particularly when some classes are much more common than others. 

| Kappa | Interpretation |
| ----- | ----- |
| \< 0.20 | Poor agreement |
| 0.21–0.40 | Fair agreement |
| 0.41–0.60 | Moderate agreement |
| 0.61–0.80 | Substantial agreement |
| \> 0.80 | Almost perfect agreement |

## Land Classification Outputs:

1. **Classified raster**: GeoTIFF containing the predicted land-cover class for every pixel.   
2. **Confusion matrix**: CSV file  
3. **Accuracy summary**: CSV file containing:  
   1. Overall accuracy  
   2. Cohen’s Kappa  
   3. Number of training samples  
   4. Number of testing samples  
4. **Class Accuracy Table**: CSV containing, for every land-cover class:   
   1. Producer's Accuracy  
   2. User's Accuracy  
   3. Precision  
   4. Recall  
   5. F1-score  
   6. Support (number of testing pixels)  
5. **Feature Importance**: CSV showing the relative importance of each predictor variable used by the Random Forest. This helps identify which spectral bands and indices contributed most to the classification.   
6. **Classification Probability**: A raster showing the prediction confidence for each pixel. This can help identify areas where the classifier was uncertain and may warrant closer inspection.   
   

# Climate Data

\-Precipitation and ground temperature.

\-Not added before making other index/land cover rasters. Rainfall and temp will probably be nearly identical for all sites each day. We will add this data to the study later and add it to inform conclusions of the results of the other analyses.

# Analysis

\*shrug\*