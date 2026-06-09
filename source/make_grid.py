#!/usr/bin/env python3
"""
make_grid.py
 
Erzeugt ein geografisches Koordinatengitter fuer eine rechteckige AOI.
Die AOI wird ueber eine Zentrumskoordinate sowie Breite und Hoehe in Metern definiert.
Verwendet eine lokal zentrierte Transversale-Mercator-Projektion (TM) zur
verzerrungsarmen metrischen Konstruktion der Bounding Box.
"""
import math
from pyproj import Transformer, CRS

def get_grid(center_coord, width, height, cell_size):
    """
    Erzeugt ein 2D-Koordinatengitter um eine Zentrumskoordinate.
 
    Parameter
    ----------
    center_coord : (lat, lon) des AOI-Zentrums in WGS84
    width        : Ost-West-Ausdehnung der AOI in Metern
    height       : Nord-Sued-Ausdehnung der AOI in Metern
    cell_size    : Rasterzellengroesse in Metern
 
    Rueckgabe
    ---------
    transformer, inverse_transformer, grid
    grid[row][col] = (lat, lon) des Zellmittelpunkts
    Zeile 0 = suedlichste Zeile (kleinster Lat-Wert)
    """
    lat_c, lon_c = center_coord
 
    proj_string = (
        f"+proj=tmerc +lat_0={lat_c} +lon_0={lon_c} "
        "+k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
 
    crs_metrisch = CRS.from_proj4(proj_string)
    crs_grad = CRS.from_epsg(4326)
 
    transformer = Transformer.from_crs(crs_grad, crs_metrisch, always_xy=True)
    inverse_transformer = Transformer.from_crs(crs_metrisch, crs_grad, always_xy=True)
 
    # AOI-Grenzen direkt im metrischen Raum: Zentrum liegt bei (0, 0)
    x_min = -width  / 2.0
    y_min = -height / 2.0
 
    x_cells = math.ceil(width  / cell_size)
    y_cells = math.ceil(height / cell_size)
 
    # Erster Zellmittelpunkt (SW-Ecke + halbe Zellgroesse)
    x_first = x_min + cell_size / 2.0
    y_first = y_min + cell_size / 2.0
 
    grid = []
    for row in range(y_cells):
        y = y_first + row * cell_size
        coords = []
        for col in range(x_cells):
            x = x_first + col * cell_size
            lon, lat = inverse_transformer.transform(x, y)
            coords.append((lat, lon))
        grid.append(coords)
 
    return transformer, inverse_transformer, grid
    