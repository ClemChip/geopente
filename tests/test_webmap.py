import json
import re

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, box

from geopente import webmap


def test_slope_to_rgba_shape_alpha_and_extremes():
    slope = np.array([[0.0, 45.0], [np.nan, 90.0]])
    rgba = webmap.slope_to_rgba(slope, vmax=45.0, alpha=200)
    assert rgba.shape == (4, 2, 2) and rgba.dtype == np.uint8
    assert rgba[3, 0, 0] == 200 and rgba[3, 1, 1] == 200
    assert rgba[3, 1, 0] == 0                       # NaN -> transparent
    assert rgba[:3, 0, 0].tolist() == [26, 152, 80]   # vert
    assert rgba[:3, 0, 1].tolist() == [215, 25, 28]   # rouge
    assert rgba[:3, 1, 1].tolist() == [215, 25, 28]   # saturé


def test_slope_to_rgba_rejects_bad_vmax():
    with pytest.raises(ValueError):
        webmap.slope_to_rgba(np.zeros((2, 2)), vmax=0)


def test_png_roundtrip_has_png_signature():
    png = webmap.rgba_to_png_bytes(webmap.slope_to_rgba(np.linspace(0, 40, 16).reshape(4, 4)))
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_to_wgs84_bounds_near_brest():
    bounds = webmap.to_wgs84_bounds((407000, 5356000, 413000, 5362000), "EPSG:32630")
    (south, west), (north, east) = bounds
    assert 48.0 < south < north < 49.0
    assert -5.0 < west < east < -4.0


def _frames():
    polys = gpd.GeoDataFrame(
        {"area_m2": [900.0]}, geometry=[box(408000, 5360000, 408090, 5360090)], crs="EPSG:32630"
    )
    peaks = gpd.GeoDataFrame(
        {"rang": [1], "altitude_m": [123.4]}, geometry=[Point(409000, 5359000)], crs="EPSG:32630"
    )
    return polys, peaks


def test_build_html_is_self_contained_and_valid_json():
    polys, peaks = _frames()
    png = webmap.rgba_to_png_bytes(webmap.slope_to_rgba(np.zeros((4, 4))))
    html = webmap.build_html(png, [[48.3, -4.6], [48.4, -4.5]], polys, peaks, title="Test")
    assert "leaflet.js" in html and "<title>Test</title>" in html
    assert "arcgisonline.com" in html and "tile.openstreetmap.org" not in html
    raw = re.search(r"const DATA = (.*?);\nconst map", html, re.S).group(1)
    data = json.loads(raw.replace("<\\/", "</"))
    assert data["image"].startswith("data:image/png;base64,")
    assert data["polygons"]["features"][0]["properties"]["area_m2"] == 900.0
    lon, lat = data["peaks"]["features"][0]["geometry"]["coordinates"]
    assert -5 < lon < -4 and 48 < lat < 49   # reprojeté en WGS84
