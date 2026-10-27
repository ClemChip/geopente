"""Découpe 6 km autour de Brest dans les dalles RGE ALTI (.asc) et écrit brest_mnt.tif.

Usage : python prepare_dem.py "C:\\chemin\\vers\\le\\dossier\\RGEALTI"
"""
import sys
from pathlib import Path

import rasterio
from rasterio.merge import merge

if len(sys.argv) < 2:
    sys.exit('Usage : python prepare_dem.py "chemin\\vers\\le\\dossier"')

dalles = sorted(Path(sys.argv[1]).rglob("*.asc"))
if not dalles:
    sys.exit("Aucun fichier .asc trouvé dans ce dossier.")
bounds = (142829, 6835360, 148829, 6841360)  # 6 km autour de Brest (EPSG:2154)

sources = [rasterio.open(p) for p in dalles]
data, transform = merge(sources, bounds=bounds, nodata=-99999.0)
profile = {
    "driver": "GTiff", "height": data.shape[1], "width": data.shape[2], "count": 1,
    "dtype": "float32", "crs": "EPSG:2154", "transform": transform,
    "nodata": -99999.0, "compress": "deflate",
}
with rasterio.open("brest_mnt.tif", "w", **profile) as dst:
    dst.write(data[0].astype("float32"), 1)
print("OK : brest_mnt.tif", data.shape)
