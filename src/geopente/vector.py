"""Vectorisation et échantillonnage avec rasterio + geopandas."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.transform import Affine, xy
from shapely.geometry import Point, shape


def polygonize_mask(
    mask: np.ndarray,
    transform: Affine,
    crs: str | None,
    min_area: float = 0.0,
) -> gpd.GeoDataFrame:
    """Transforme les pixels == 1 d'un masque en polygones (GeoDataFrame)."""
    if mask.dtype != np.uint8:
        mask = mask.astype("uint8")
    geoms = [
        shape(geom)
        for geom, value in shapes(mask, mask=mask == 1, transform=transform)
        if value == 1
    ]
    gdf = gpd.GeoDataFrame({"geometry": geoms}, geometry="geometry", crs=crs)
    gdf["area_m2"] = gdf.geometry.area if len(gdf) else np.array([], dtype="float64")
    return gdf[gdf["area_m2"] >= min_area].reset_index(drop=True)


def top_peaks(
    dem: np.ndarray, transform: Affine, crs: str | None, n: int = 5
) -> gpd.GeoDataFrame:
    """Les n pixels les plus hauts, sous forme de points."""
    if n < 1:
        raise ValueError("n doit être >= 1")
    flat = np.where(np.isnan(dem), -np.inf, dem).ravel()
    n = min(n, flat.size)
    idx = np.argpartition(flat, -n)[-n:]
    idx = idx[np.argsort(flat[idx])[::-1]]
    rows, cols = np.unravel_index(idx, dem.shape)
    xs, ys = xy(transform, rows, cols, offset="center")
    gdf = gpd.GeoDataFrame(
        {"rang": np.arange(1, n + 1), "geometry": [Point(x, y) for x, y in zip(xs, ys)]},
        geometry="geometry",
        crs=crs,
    )
    return gdf


def sample_elevation(dem_path: str | Path, points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ajoute la colonne `altitude_m` en échantillonnant le raster aux points."""
    with rasterio.open(dem_path) as src:
        coords = [(p.x, p.y) for p in points.geometry]
        values = [float(v[0]) for v in src.sample(coords)]
    out = points.copy()
    out["altitude_m"] = np.round(values, 1)
    return out
