import numpy as np
import pytest
import rasterio

from geopente import raster


def test_synthetic_dem_metadata(dem_path):
    with rasterio.open(dem_path) as src:
        assert src.crs.to_string() == "EPSG:32630"
        assert (src.width, src.height) == (80, 80)
        assert src.res == (30.0, 30.0)
        assert src.nodata == raster.NODATA


def test_synthetic_dem_is_reproducible(tmp_path):
    a = raster.make_synthetic_dem(tmp_path / "a.tif", size=30, seed=1)
    b = raster.make_synthetic_dem(tmp_path / "b.tif", size=30, seed=1)
    c = raster.make_synthetic_dem(tmp_path / "c.tif", size=30, seed=2)
    da, _ = raster.read_dem(a)
    db, _ = raster.read_dem(b)
    dc, _ = raster.read_dem(c)
    assert np.array_equal(da, db)
    assert not np.array_equal(da, dc)


@pytest.mark.parametrize("kwargs", [{"size": 2}, {"resolution": 0}])
def test_synthetic_dem_rejects_bad_args(tmp_path, kwargs):
    with pytest.raises(ValueError):
        raster.make_synthetic_dem(tmp_path / "x.tif", **kwargs)


def test_read_dem_converts_nodata_to_nan(tmp_path):
    path = raster.make_synthetic_dem(tmp_path / "d.tif", size=10)
    with rasterio.open(path, "r+") as dst:
        data = dst.read(1)
        data[0, 0] = raster.NODATA
        dst.write(data, 1)
    dem, _ = raster.read_dem(path)
    assert np.isnan(dem[0, 0])
    assert not np.isnan(dem[1, 1])


def test_slope_of_tilted_plane_is_exact():
    angle = 10.0
    res = 30.0
    cols = np.arange(50) * res
    dem = np.tile(cols * np.tan(np.radians(angle)), (50, 1))
    slope = raster.compute_slope(dem, res, res)
    assert np.allclose(slope, angle, atol=1e-9)


def test_slope_of_flat_terrain_is_zero():
    assert np.all(raster.compute_slope(np.full((10, 10), 5.0), 30, 30) == 0)


def test_slope_propagates_nan():
    dem = np.ones((5, 5))
    dem[2, 2] = np.nan
    slope = raster.compute_slope(dem, 1, 1)
    assert np.isnan(slope[2, 2])


def test_slope_rejects_bad_input():
    with pytest.raises(ValueError):
        raster.compute_slope(np.zeros(5), 1, 1)
    with pytest.raises(ValueError):
        raster.compute_slope(np.zeros((3, 3)), 0, 1)


def test_classify_slope_threshold_and_nan():
    slope = np.array([[5.0, 20.0], [35.0, np.nan]])
    mask = raster.classify_slope(slope, 20.0)
    assert mask.dtype == np.uint8
    assert mask.tolist() == [[0, 1], [1, 0]]


@pytest.mark.parametrize("threshold", [-1, 90, 120])
def test_classify_slope_rejects_bad_threshold(threshold):
    with pytest.raises(ValueError):
        raster.classify_slope(np.zeros((2, 2)), threshold)
