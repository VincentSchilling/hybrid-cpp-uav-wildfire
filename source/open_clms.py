#!/usr/bin/env python3
"""
open_clms.py
 
Liest den Landbedeckungstyp aus einem CGLS-LC100 GeoTIFF
an einer gegebenen (lon, lat)-Koordinate aus.
"""

import os
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform

# Legende: CGLS-LC100-Code → Landbedeckungsklasse
LEGEND = {
    0:   "No input data available",
    20:  "Shrubs",
    30:  "Herbaceous vegetation",
    40:  "Cultivated and managed vegetation (cropland)",
    50:  "Urban / built up",
    60:  "Bare / sparse vegetation",
    70:  "Snow and Ice",
    80:  "Permanent water bodies",
    90:  "Herbaceous wetland",
    100: "Moss and lichen",
    111: "Closed forest, evergreen needle leaf",
    112: "Closed forest, evergreen broad leaf",
    113: "Closed forest, deciduous needle leaf",
    114: "Closed forest, deciduous broad leaf",
    115: "Closed forest, mixed",
    116: "Closed forest, unknown",
    121: "Open forest, evergreen needle leaf",
    122: "Open forest, evergreen broad leaf",
    123: "Open forest, deciduous needle leaf",
    124: "Open forest, deciduous broad leaf",
    125: "Open forest, mixed",
    126: "Open forest, unknown",
    200: "Open sea"
}

def get_value_at_lonlat(dataset_path: str, lon: float, lat: float, band: int = 1) -> int:
    """Liest den reinen Klassifikationscode an einer Lon/Lat-Position aus dem GeoTIFF."""
    with rasterio.open(dataset_path) as src:
        # Koords nur transformieren, wenn nicht EPSG:4326
        if src.crs.to_epsg() == 4326:
            x, y = lon, lat
        else:
            xs, ys = transform(
                CRS.from_epsg(4326),
                src.crs,
                [lon], [lat]
            )
            x, y = xs[0], ys[0]

        row, col = src.index(x, y)
        window = ((row, row+1), (col, col+1))
        arr = src.read(band, window=window)
        return int(arr[0, 0])

def get_landcover_label(dataset_path: str, lon: float, lat: float, band: int = 1) -> str:
    """Gibt den Legenden-Text zum Klassifikationscode an einer Lon/Lat-Position zurueck."""
    code = get_value_at_lonlat(dataset_path, lon, lat, band=band)
    return LEGEND.get(code, "Unbekannter Code")

def get_land_data(dataset_path: str, lon: float, lat: float, band: int = 1):
    """Gibt den CGLS-LC100-Klassifikationscode an einer Lon/Lat-Position zurueck."""
    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(f"Datei nicht gefunden: {dataset_path}")

    code = get_value_at_lonlat(dataset_path, lon, lat, band=band)
    return code
