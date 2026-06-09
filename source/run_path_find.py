#!/usr/bin/env python3
"""
run_path_find.py
 
Dispatcher fuer die Routenplanung. Laedt eine Karte aus einer JSON-Datei,
instanziiert die Konfigurationen und plant eine vollstaendige Route
ueber alle Fluege.
 
algo: 0 = Greedy+Dijkstra (V1/V2), 1 = Boustrophedon (V3)
"""
from typing import List
import json
 
import Greedy, Boustro
from classes import Tile, GeneralConfig, DroneConfig, pfmConfig


def load_grid_from_json(filename: str) -> List[List[Tile]]:
    """Lädt das Grid aus einer JSON-Datei und gibt es als 2D-Liste von Tile-Objekten zurück."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [ [Tile.from_dict(cell) for cell in row] for row in data ]
    
    
def get_landing_position(grid: List[List[Tile]]):
    """Gibt alle Landeplatz-Koordinaten des Grids zurueck."""
    landing_positions: Tuple[int, int] = []
    for row in grid:
        for tile in row:
            r = tile.row
            c = tile.col
            if tile.is_landing_pad:
                landing_positions.append((r , c))

    return landing_positions

        
def path_find(lp,map_json,algo):
     """Plant eine vollstaendige Route fuer Startlandeplatz lp auf Karte map_json mit Algorithmus algo."""
    general_cfg = GeneralConfig()
    drone_cfg = DroneConfig()
    pfm_cfg = pfmConfig()

    grid = load_grid_from_json(map_json)
    rows = len(grid)
    cols = len(grid[0])
    general_cfg.rows = rows
    general_cfg.cols = cols

    landing_positions = get_landing_position(grid)
    route = [landing_positions[lp]]

    for - in range(DroneConfig.num_flights):
        if algo == 0:
            next_part = Greedy.plan_route(route[-1], landing_positions, grid, general_cfg, drone_cfg,pfm_cfg)
        else:
            next_part = Boustro.plan_route(route[-1], landing_positions, grid, general_cfg, drone_cfg, pfm_cfg)
        
        if not next_part:
            break
        else:
            route.extend(next_part)

    return route
