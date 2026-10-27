"""Pipeline complet : MNT -> pentes -> vecteurs -> carte Leaflet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd

from . import raster, vector, webmap


@dataclass(frozen=True)
class Result:
    dem_path: Path
    geojson_path: Path
    html_path: Path
    polygons: gpd.GeoDataFrame
    peaks: gpd.GeoDataFrame


def run(
    out_dir: str | Path,
    dem_path: str | Path | None = None,
    threshold: float = 20.0,
    n_peaks: int = 5,
    min_area: float = 2_700.0,  # 3 pixels de 30 m
    seed: int = 42,
) -> Result:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if dem_path is None:
        dem_path = raster.make_synthetic_dem(out_dir / "dem.tif", seed=seed)
    dem_path = Path(dem_path)

    dem, profile = raster.read_dem(dem_path)
    transform, crs = profile["transform"], profile["crs"]

    slope = raster.compute_slope(dem, xres=transform.a, yres=-transform.e)
    mask = raster.classify_slope(slope, threshold)

    polygons = vector.polygonize_mask(mask, transform, crs, min_area=min_area)
    peaks = vector.sample_elevation(dem_path, vector.top_peaks(dem, transform, crs, n_peaks))

    geojson_path = out_dir / "zones_raides.geojson"
    polygons.to_crs("EPSG:4326").to_file(geojson_path, driver="GeoJSON")

    height, width = dem.shape
    bounds = rasterio_bounds(transform, width, height)
    png = webmap.rgba_to_png_bytes(webmap.slope_to_rgba(slope))
    html = webmap.build_html(
        png,
        webmap.to_wgs84_bounds(bounds, crs),
        polygons,
        peaks,
        slope_threshold=threshold,
    )
    html_path = webmap.write_html(html, out_dir / "carte.html")
    return Result(dem_path, geojson_path, html_path, polygons, peaks)


def rasterio_bounds(transform, width: int, height: int) -> tuple[float, float, float, float]:
    left, top = transform @ (0, 0)
    right, bottom = transform @ (width, height)
    return (left, bottom, right, top)
