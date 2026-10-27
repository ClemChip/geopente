import pytest

from geopente import raster


@pytest.fixture(scope="session")
def dem_path(tmp_path_factory):
    return raster.make_synthetic_dem(tmp_path_factory.mktemp("data") / "dem.tif", size=80)
