import json

import geopandas as gpd

from geopente import pipeline
from geopente.cli import main


def test_pipeline_end_to_end(tmp_path):
    res = pipeline.run(tmp_path, threshold=15.0, n_peaks=4)
    assert res.dem_path.exists() and res.html_path.exists() and res.geojson_path.exists()
    assert len(res.peaks) == 4
    assert not res.polygons.empty

    gj = gpd.read_file(res.geojson_path)
    assert gj.crs.to_epsg() == 4326
    assert len(gj) == len(res.polygons)
    json.loads(res.geojson_path.read_text())  # GeoJSON valide

    html = res.html_path.read_text(encoding="utf-8")
    assert "L.imageOverlay" in html and "L.geoJSON" in html


def test_higher_threshold_gives_less_steep_area(tmp_path):
    low = pipeline.run(tmp_path / "low", threshold=10.0)
    high = pipeline.run(tmp_path / "high", threshold=30.0)
    assert high.polygons["area_m2"].sum() < low.polygons["area_m2"].sum()


def test_pipeline_accepts_existing_dem(tmp_path, dem_path):
    res = pipeline.run(tmp_path, dem_path=dem_path)
    assert res.dem_path == dem_path


def test_cli_runs(tmp_path, capsys):
    assert main(["--out", str(tmp_path), "--threshold", "15"]) == 0
    out = capsys.readouterr().out
    assert "zones raides" in out and "carte.html" in out
