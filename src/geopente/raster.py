"""Création et analyse d'un modèle numérique de terrain (MNT) avec rasterio."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

NODATA = -9999.0
DEFAULT_CRS = "EPSG:32630"  # UTM 30N, adapté à la Bretagne
DEFAULT_ORIGIN = (386_024.0, 5_365_791.0)  # coin supérieur gauche (x, y), centré sur Brest (48.4085, -4.4996)



def make_synthetic_dem(
    path: str | Path,
    size: int = 200,
    resolution: float = 30.0,
    origin: tuple[float, float] = DEFAULT_ORIGIN,
    crs: str = DEFAULT_CRS,
    seed: int = 42,
) -> Path:
    """Écrit un MNT synthétique reproductible (somme de gaussiennes + bruit)."""
    if size < 3:
        raise ValueError("size doit être >= 3")
    if resolution <= 0:
        raise ValueError("resolution doit être > 0")

    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype("float64")
    dem = np.zeros((size, size), dtype="float64")

    for _ in range(6):
        cx, cy = rng.uniform(0.15, 0.85, 2) * size
        sigma = rng.uniform(0.05, 0.12) * size
        height = rng.uniform(200.0, 450.0)
        dem += height * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2))

    dem += rng.normal(0.0, 0.5, dem.shape)
    dem = dem.astype("float32")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": size,
        "width": size,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": from_origin(origin[0], origin[1], resolution, resolution),
        "nodata": NODATA,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(dem, 1)
    return path


def read_dem(path: str | Path) -> tuple[np.ndarray, dict]:
    """Lit un MNT. Les pixels nodata sont convertis en NaN."""
    with rasterio.open(path) as src:
        dem = src.read(1, masked=True).astype("float64").filled(np.nan)
        profile = src.profile.copy()
    return dem, profile


def compute_slope(dem: np.ndarray, xres: float, yres: float) -> np.ndarray:
    """Pente en degrés (différences centrées). NaN propagés."""
    if dem.ndim != 2:
        raise ValueError("dem doit être un tableau 2D")
    if xres <= 0 or yres <= 0:
        raise ValueError("xres et yres doivent être > 0")
    dz_dy, dz_dx = np.gradient(dem, yres, xres)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    slope[np.isnan(dem)] = np.nan
    return slope


def classify_slope(slope: np.ndarray, threshold: float) -> np.ndarray:
    """Masque uint8 : 1 si pente >= seuil (degrés), 0 sinon (NaN inclus)."""
    if not 0 <= threshold < 90:
        raise ValueError("threshold doit être dans [0, 90[")
    with np.errstate(invalid="ignore"):
        return (np.nan_to_num(slope, nan=0.0) >= threshold).astype("uint8")
