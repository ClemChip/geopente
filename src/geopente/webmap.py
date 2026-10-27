"""Génération de la carte Leaflet (HTML autonome)."""

from __future__ import annotations

import base64
import json
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.errors import NotGeoreferencedWarning
from rasterio.warp import transform_bounds

LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"

# Rampe de couleurs : vert -> jaune -> rouge
_RAMP = np.array(
    [[26, 152, 80], [166, 217, 106], [255, 255, 140], [253, 174, 97], [215, 25, 28]],
    dtype="float64",
)


def slope_to_rgba(slope: np.ndarray, vmax: float = 45.0, alpha: int = 170) -> np.ndarray:
    """Convertit une pente (degrés) en image RGBA uint8 de forme (4, H, W)."""
    if vmax <= 0:
        raise ValueError("vmax doit être > 0")
    valid = ~np.isnan(slope)
    t = np.clip(np.nan_to_num(slope, nan=0.0) / vmax, 0.0, 1.0)
    pos = t * (len(_RAMP) - 1)
    lo = np.floor(pos).astype(int).clip(0, len(_RAMP) - 2)
    frac = (pos - lo)[..., None]
    rgb = _RAMP[lo] * (1 - frac) + _RAMP[lo + 1] * frac
    rgba = np.zeros((*slope.shape, 4), dtype="uint8")
    rgba[..., :3] = rgb.round().astype("uint8")
    rgba[..., 3] = np.where(valid, alpha, 0)
    return np.moveaxis(rgba, -1, 0)


def rgba_to_png_bytes(rgba: np.ndarray) -> bytes:
    """Encode un tableau (4, H, W) uint8 en PNG avec rasterio."""
    _, height, width = rgba.shape
    with warnings.catch_warnings():
        # Un PNG n'est pas géoréférencé : l'avertissement est attendu ici.
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.MemoryFile() as mem:
            with mem.open(
                driver="PNG", width=width, height=height, count=4, dtype="uint8"
            ) as dst:
                dst.write(rgba)
            return mem.read()


def to_wgs84_bounds(bounds: tuple[float, float, float, float], crs: str | CRS):
    """(left, bottom, right, top) -> [[sud, ouest], [nord, est]] pour Leaflet."""
    west, south, east, north = transform_bounds(crs, "EPSG:4326", *bounds)
    return [[south, west], [north, east]]


def build_html(
    png_bytes: bytes,
    bounds_latlon: list[list[float]],
    polygons: gpd.GeoDataFrame,
    peaks: gpd.GeoDataFrame,
    title: str = "geopente",
    slope_threshold: float = 20.0,
) -> str:
    """Assemble une page HTML autonome (image + GeoJSON intégrés)."""
    img_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    poly_json = polygons.to_crs("EPSG:4326").to_json()
    peaks_json = peaks.to_crs("EPSG:4326").to_json()
    payload = {
        "image": img_uri,
        "bounds": bounds_latlon,
        "polygons": json.loads(poly_json),
        "peaks": json.loads(peaks_json),
        "threshold": slope_threshold,
    }
    data = json.dumps(payload).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{LEAFLET_CSS}">
<style>
  html, body, #map {{ height: 100%; margin: 0; }}
  .legend {{ background: #fff; padding: 8px 10px; border-radius: 6px;
             font: 12px/1.4 system-ui, sans-serif; box-shadow: 0 1px 4px rgba(0,0,0,.3); }}
  .legend .bar {{ width: 160px; height: 10px; margin: 4px 0;
                  background: linear-gradient(90deg,#1a9850,#a6d96a,#ffff8c,#fdae61,#d7191c); }}
  .legend .row {{ display: flex; justify-content: space-between; }}
</style>
</head>
<body>
<div id="map"></div>
<script src="{LEAFLET_JS}"></script>
<script>
const DATA = {data};
const map = L.map("map");
const satellite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}", {{
  maxZoom: 19, attribution: "Tiles &copy; Esri, Maxar, Earthstar Geographics"
}}).addTo(map);
const planIgn = L.tileLayer(
  "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
  + "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png"
  + "&TILEMATRIXSET=PM&TILEMATRIX={{z}}&TILEROW={{y}}&TILECOL={{x}}", {{
  maxZoom: 19, attribution: "&copy; IGN Géoportail"
}});

const slope = L.imageOverlay(DATA.image, DATA.bounds, {{ opacity: 0.8 }}).addTo(map);
const steep = L.geoJSON(DATA.polygons, {{
  style: {{ color: "#7f0000", weight: 1, fillOpacity: 0.05 }},
  onEachFeature: (f, l) => l.bindPopup("Pente &ge; " + DATA.threshold + "&deg;<br>Surface : "
    + Math.round(f.properties.area_m2).toLocaleString("fr-FR") + " m&sup2;")
}}).addTo(map);
const peaks = L.geoJSON(DATA.peaks, {{
  pointToLayer: (f, ll) => L.circleMarker(ll, {{ radius: 6, color: "#000", weight: 1,
                                                fillColor: "#fff", fillOpacity: 1 }}),
  onEachFeature: (f, l) => l.bindPopup("Sommet n&deg;" + f.properties.rang
    + "<br>Altitude : " + f.properties.altitude_m + " m")
}}).addTo(map);

L.control.layers({{ "Satellite (Esri)": satellite, "Plan IGN": planIgn }}, {{
  "Pentes (raster)": slope, "Zones raides (vecteur)": steep, "Sommets": peaks
}}).addTo(map);
L.control.scale({{ metric: true, imperial: false }}).addTo(map);

const legend = L.control({{ position: "bottomright" }});
legend.onAdd = () => {{
  const d = L.DomUtil.create("div", "legend");
  d.innerHTML = "<b>Pente</b><div class='bar'></div><div class='row'><span>0&deg;</span><span>45&deg;+</span></div>";
  return d;
}};
legend.addTo(map);

map.fitBounds(DATA.bounds);
</script>
</body>
</html>
"""


def write_html(html: str, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
