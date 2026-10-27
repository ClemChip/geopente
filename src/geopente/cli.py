"""Interface en ligne de commande."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .pipeline import run


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geopente", description=__doc__)
    parser.add_argument("--out", default="build", help="dossier de sortie (défaut : build)")
    parser.add_argument("--dem", default=None, help="MNT GeoTIFF existant (sinon synthétique)")
    parser.add_argument("--threshold", type=float, default=20.0, help="seuil de pente en degrés")
    parser.add_argument("--peaks", type=int, default=5, help="nombre de sommets")
    parser.add_argument("--seed", type=int, default=42, help="graine du MNT synthétique")
    args = parser.parse_args(argv)

    res = run(args.out, args.dem, args.threshold, args.peaks, seed=args.seed)
    print(f"{len(res.polygons)} zones raides, {len(res.peaks)} sommets")
    print(f"Carte : {res.html_path}")
    return 0
