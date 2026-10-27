# geopente

Analyse du relief de Brest avec **Python 3.12**, **rasterio** et **geopandas**, testée avec
**pytest** et visualisée sur une carte **Leaflet**.

**Objectif du projet :** évaluer la difficulté des routes à vélo à Brest selon la pente.
Aujourd'hui, le projet cartographie les pentes du terrain (voir "État actuel").
Le calcul de difficulté par route est la prochaine étape (voir "Feuille de route").

## État actuel

À partir d'un modèle numérique de terrain (MNT), le pipeline :

1. lit un MNT GeoTIFF (réel, RGE ALTI de l'IGN) ou génère un relief synthétique pour les tests ;
2. calcule la pente en degrés (numpy, différences centrées) ;
3. vectorise les zones de pente supérieure ou égale à un seuil (`rasterio.features.shapes`, GeoDataFrame) ;
4. repère les sommets les plus hauts et échantillonne leur altitude (`src.sample`) ;
5. produit `build/carte.html`, une page Leaflet autonome : raster des pentes, zones raides cliquables,
   sommets, légende, fonds Esri Satellite et Plan IGN.

## Installation

Prérequis : Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest        # 29 tests
```

## Utilisation avec le vrai relief de Brest (RGE ALTI, IGN)

1. Téléchargez le **RGE ALTI 5 m**, département 29 (Finistère), sur `geoservices.ign.fr/rgealti`
   (format ASCII, Lambert-93) et extrayez l'archive avec 7-Zip.
2. Découpez 6 km autour de Brest :

```powershell
python prepare_dem.py "chemin\vers\le\dossier\RGEALTI"   # crée brest_mnt.tif
```

3. Générez la carte :

```powershell
geopente --dem brest_mnt.tif --out build --threshold 15
start build\carte.html
```

Options principales : `--threshold` (seuil de pente en degrés), `--peaks` (nombre de sommets),
`--out` (dossier de sortie). Sans `--dem`, un MNT synthétique est généré (démo et tests).

La carte nécessite une connexion internet (Leaflet et fonds de carte).

## Feuille de route : difficulté des routes à vélo

Pas encore implémenté :

1. **Réseau routier** : récupérer les rues et pistes cyclables de Brest (OpenStreetMap ou BD TOPO IGN).
2. **Pente par tronçon** : échantillonner le MNT le long de chaque route (pente moyenne,
   pente maximale, dénivelé positif).
3. **Classement de difficulté**, avec des seuils en pourcentage adaptés au vélo :

| Pente moyenne | Difficulté |
|---------------|------------|
| moins de 3 %  | facile |
| 3 à 6 %       | modérée |
| 6 à 10 %      | difficile |
| plus de 10 %  | très difficile |

4. **Couche Leaflet** des routes colorées par difficulté, avec popup (pente moyenne, maximale, dénivelé).

## Limites

- Le MNT représente le sol : la pente est fausse sous les ponts et dans les tunnels de Brest
  (ex. pont de Recouvrance). Ces tronçons devront être repérés et exclus.
- Le seuil par défaut de `--threshold` est en degrés (15° correspond à environ 27 %), adapté à
  l'analyse du terrain et non à la pratique du vélo.
- `prepare_dem.py` découpe une zone fixe autour de Brest ; pour une autre ville, modifier `bounds`
  (coordonnées Lambert-93, EPSG:2154).
- Le RGE ALTI n'est plus mis à jour depuis 2024.

## Structure

```
prepare_dem.py   découpe le MNT réel autour de Brest
src/geopente/    raster.py (MNT, pente) | vector.py (polygones, points)
                 webmap.py (Leaflet)    | pipeline.py | cli.py
tests/           un fichier de tests par module, plus un test de bout en bout
```

## Données et licences

- Altimétrie : RGE ALTI, © IGN, Licence Ouverte.
- Fonds de carte : © Esri, Maxar, Earthstar Geographics ; © IGN Géoportail.