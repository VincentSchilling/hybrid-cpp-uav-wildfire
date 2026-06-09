#!/usr/bin/env python3
"""
create_real_map.py
 
Erzeugt eine Rasterkarte als JSON aus realen Geodaten (CGLS-LC100 GeoTIFF).
Liest fuer jede Gitterzelle den Landbedeckungstyp aus und speichert das
Ergebnis als 2D-Liste von Tile-Objekten.
"""
import random
import os
from typing import Tuple, List
import json


import make_grid, open_clms
from classes import Tile, GeneralConfig, clmsConfig

def select_landing_pads(tiles, min_pads: int = 2, max_pads: int = 7):
    """Waehlt zufaellig zwischen min_pads und max_pads Tiles als Landeplaetze aus und gibt ihre (row, col)-Koordinaten zurueck."""    

    flat_tiles = [tile for row in tiles for tile in row]
    num_pads = min(random.randint(min_pads, max_pads), len(flat_tiles))

    # Gleichmäßig ohne Dopplungen auswählen
    chosen = random.sample(flat_tiles, num_pads)
    # Flag setzen und Koordinaten sammeln
    coords: List[Tuple[int, int]] = []
    for tile in chosen:
        tile.is_landing_pad = True
        coords.append((tile.row, tile.col))
    return coords


def make_tiles(general_cfg, clms_cfg):
    """Erzeugt das Tile-Grid aus Geodaten: Koordinatengitter via make_grid, Landtypen via open_clms."""
    height =general_cfg.height
    width = general_cfg.width
    cell_size = clms_cfg.grid_size
    coord_1 = clms_cfg.coord_1
    input_tif = clms_cfg.data_path
    
    _, _, grid = make_grid.get_grid(coord_1, width, height, cell_size)
    r_len = len(grid) -1 
    c_len = len(grid[0]) -1
    tiles: List[List[Tile]] = []

    for r in range(r_len):
        r_tiles: List[Tile] = []
        for c in range(c_len):
            tile_coord: Tuple[float, float] = grid[r_len - r][c]
            map_type = clms_cfg.map_type.get(
                open_clms.get_land_data(input_tif, tile_coord[1], tile_coord[0])
            )
            r_tiles.append(Tile(r, c, grid[r_len - r][c], map_type, False, False))
        tiles.append(r_tiles)

    landing_pads = select_landing_pads(tiles)
    return tiles, landing_pads

def save_grid_to_json(grid: List[List[Tile]], filename: str) -> None:
    """Speichert das Grid (2D-Liste von Tiles) in eine JSON-Datei."""
    serializable = [ [tile.to_dict() for tile in row] for row in grid ]
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def load_grid_from_json(filename: str) -> List[List[Tile]]:
    """Laedt das Grid aus einer JSON-Datei als 2D-Liste von Tile-Objekten."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [ [Tile.from_dict(cell) for cell in row] for row in data ]

if __name__ == "__main__":
    
    # Pfad zum CGLS-LC100 GeoTIFF — individuell anpassen
    INPUT_TIF = r"PROBAV_LC100_global_v3.0.1_2019-nrt_Discrete-Classification-map_EPSG-4326.tif"
    
    # Zentrumskoordinate der AOI (lat, lon) — individuell anpassen
    coord = (0, 0)
    
    general_cfg = GeneralConfig()
    clms_cfg = clmsConfig(coord_1=coord, data_path= INPUT_TIF)
    grid, landing_positions = make_tiles(general_cfg , clms_cfg)
    print(landing_positions)
    save_grid_to_json(grid,"map.json")