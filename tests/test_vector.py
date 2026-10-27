import numpy as np
import pytest
from rasterio.transform import from_origin

from geopente import raster, vector

TRANSFORM = from_origin(0, 100, 10, 10)
CRS = "EPSG:32630"


def test_polygonize_two_blocks_with_areas():
    mask = np.zeros((10, 10), dtype="uint8")
    mask[1:3, 1:3] = 1   # 2x2 pixels -> 400 m2
    mask[6:9, 5:8] = 1   # 3x3 pixels -> 900 m2
    gdf = vector.polygonize_mask(mask, TRANSFORM, CRS)
    assert len(gdf) == 2
    assert sorted(gdf["area_m2"].round().tolist()) == [400, 900]
    assert gdf.crs.to_string() == CRS


def test_polygonize_min_area_filters_small_zones():
    mask = np.zeros((10, 10), dtype="uint8")
    mask[0, 0] = 1
    mask[4:7, 4:7] = 1
    gdf = vector.polygonize_mask(mask, TRANSFORM, CRS, min_area=500)
    assert len(gdf) == 1
    assert gdf.iloc[0]["area_m2"] == pytest.approx(900)


def test_polygonize_empty_mask_gives_empty_frame():
    gdf = vector.polygonize_mask(np.zeros((5, 5), dtype="uint8"), TRANSFORM, CRS)
    assert gdf.empty
    assert "area_m2" in gdf.columns


def test_top_peaks_sorted_and_located():
    dem = np.zeros((10, 10))
    dem[2, 3] = 50
    dem[7, 8] = 80
    gdf = vector.top_peaks(dem, TRANSFORM, CRS, n=2)
    assert gdf["rang"].tolist() == [1, 2]
    first, second = gdf.geometry
    # centre du pixel (ligne 7, colonne 8) : x = 85, y = 100 - 75 = 25
    assert (first.x, first.y) == (85.0, 25.0)
    assert (second.x, second.y) == (35.0, 75.0)


def test_top_peaks_ignores_nan_and_caps_n():
    dem = np.full((2, 2), np.nan)
    dem[0, 0] = 1.0
    gdf = vector.top_peaks(dem, TRANSFORM, CRS, n=10)
    assert len(gdf) == 4
    assert gdf.geometry.iloc[0].x == 5.0


def test_top_peaks_rejects_bad_n():
    with pytest.raises(ValueError):
        vector.top_peaks(np.zeros((3, 3)), TRANSFORM, CRS, n=0)


def test_sample_elevation_matches_array(dem_path):
    dem, profile = raster.read_dem(dem_path)
    peaks = vector.top_peaks(dem, profile["transform"], profile["crs"], n=3)
    sampled = vector.sample_elevation(dem_path, peaks)
    assert sampled["altitude_m"].tolist() == pytest.approx(
        [round(float(np.sort(dem.ravel())[-i]), 1) for i in (1, 2, 3)], abs=0.11
    )
