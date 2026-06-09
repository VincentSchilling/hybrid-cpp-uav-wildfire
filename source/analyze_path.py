"""
analyze_path.py
 
Kernmodul zur Auswertung berechneter UAV-Routen.
Berechnet Routenlaenge, Wenden, U-Turns, Coverage-Metriken
und Overlap-Raten auf Basis der Frontier-Methode.
"""
from typing import Dict, Tuple, List, Set
import json, math
from pathlib import Path

from classes import Tile, GeneralConfig, DroneConfig, clmsConfig

def fov_cells(r, c, general_cfg, drone_cfg):
    """Liefert alle Zellen im quadratischen Sichtfeld um (r, c)."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    R = drone_cfg.fov_radius

    cells = []
    for dr in range(-R, R + 1):
        for dc in range(-R, R + 1):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                cells.append((nr, nc))
    return cells


def _get_forest(grid, general_cfg):
    """Gibt alle Waldzellen (type == 2) des Grids als Liste von (row, col)-Tupeln zurueck."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    forest_tiles = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (grid[r][c].type == 2)
    ]
    return forest_tiles

def load_grid_from_json(filename: str) -> List[List[Tile]]:
    """Laedt das Grid aus einer JSON-Datei als 2D-Liste von Tile-Objekten."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [ [Tile.from_dict(cell) for cell in row] for row in data ]

def load_path_from_json(filename: str):
    """Laedt eine Route aus einer JSON-Datei und gibt sie als Liste von (row, col)-Tupeln zurueck."""
    with Path(filename).open("r", encoding="utf-8") as f:
        r = json.load(f)
    path: List[Tuple[int, int]] = [tuple(p) for p in r["route"]]
    if not path:
        raise ValueError("Route enthält keine Punkte.")
    return path

def analyze_path(route_path: str | Path,
                  map_path: str | Path,
                ) -> Dict:
    """Analysiert eine Route und gibt alle Metriken als Dictionary zurueck."""
    general_cfg = GeneralConfig()
    drone_cfg = DroneConfig()
    clms_cfg = clmsConfig()

    grid = load_grid_from_json(map_path)
    rows = len(grid)
    cols = len(grid[0])

    path = load_path_from_json(route_path)

    general_cfg.rows = rows
    general_cfg.cols = cols

    forest_tiles = set(_get_forest(grid, general_cfg))
    total_forest = len(forest_tiles)

    scanned_all: Set[Tuple[int, int]] = set()
    scanned_forest: Set[Tuple[int, int]] = set()

    total_scan_events = total_scan_events_forest = 0
    duplicate_scans_all = duplicate_scans_forest = 0
    turns = 0
    u_turns = 0
    route_length=0

    prev_fov: Set[Tuple[int, int]] = set ()
    delta_fov: Set[Tuple[int, int]] = set ()
    prev_direct = None
    prev_step = None 

    for r ,c in path:
        fov = set(fov_cells(r,c ,general_cfg, drone_cfg))
        delta_fov = fov-prev_fov

        # alle Tiles
        for cell in delta_fov:
            total_scan_events += 1
            if cell in scanned_all:
                duplicate_scans_all += 1

        # nur Wald
        forest_frontier = delta_fov & forest_tiles
        total_scan_events_forest += len(forest_frontier)
        for cell in forest_frontier:
            if cell in scanned_forest:
                duplicate_scans_forest += 1
        
        # calc turns
        if prev_step is not None:
            r0, c0 = prev_step
            dr, dc = (r - r0), (c - c0)
            direct = (dr, dc)

            # --- Route-Länge ---
            step_len = math.hypot(dr, dc)
            route_length += step_len

            # --- Turns & U-Turns ---
            if prev_direct is not None:
                if prev_direct != direct:
                    turns += 1
                    if prev_direct == (-direct[0], -direct[1]):
                        u_turns += 1
            prev_direct = direct

        prev_step = (r,c)
        scanned_all.update(delta_fov)
        scanned_forest.update(forest_frontier)
        prev_fov = fov

    forest_coverage_rate = (len(scanned_forest) / total_forest) if total_forest else float("nan")
    overlap_rate_all = (duplicate_scans_all / total_scan_events) if total_scan_events else 0.0
    overlap_rate_forest = (duplicate_scans_forest / duplicate_scans_all) if total_scan_events_forest else 0.0
    scanned_forest_rate = (total_scan_events_forest / total_scan_events) if total_scan_events else 0.0

    route_length = route_length * float(clms_cfg.grid_size)

    return {
        # Setup
        "map_rows": rows, "map_cols": cols,
        "fov_radius": drone_cfg.fov_radius,
        "cell_size_m": clms_cfg.grid_size,
        # Route
        "route_points": len(path),
        "route_steps": max(0, len(path) - 1),
        "route_length_meters": route_length,
        "turns_total": turns,
        "uturns_total": u_turns,
        # Coverage & Overlap (Frontier)
        "total_forest_cells": total_forest,
        "forest_coverage_rate": forest_coverage_rate,
        "total_scan_events": total_scan_events,
        "scanned_forest_rate": scanned_forest_rate,
        "overlap_rate": overlap_rate_all,
        "overlap_rate_forest": overlap_rate_forest,
        # Referenzen
        "route_file": str(route_path),
        "map_file": str(map_path),
    }
