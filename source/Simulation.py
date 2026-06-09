#!/usr/bin/env python3
"""
Simulation.py
 
Interaktive Visualisierungsumgebung fuer die Routenplanung.
Laedt eine Karte aus einer JSON-Datei, berechnet eine vollstaendige Route
und stellt den Flugverlauf per pygame dar.
 
Konfiguration: lp, map_path und algo am Anfang der Datei anpassen.
algo: 0 = Greedy+Dijkstra (V1/V2), 1 = Boustrophedon (V3)
"""
import pygame
import sys
import os
from typing import Tuple, List
from pathlib import Path
import json

import create_real_map, Greedy, Boustro
from classes import Tile, GeneralConfig, DroneConfig, pfmConfig


# --- Konfiguration ---
lp = 0                  # Index des Startlandeplatzes (0 ... Anzahl Landeplätzet-1)
map_path= "map.json"    # individuel anpassen
algo = 0                # 0 = Greedy+Dijkstra, 1 = Boustrophedon
routes_dir = "routes"   # Ordner für Routendateien

def save_route_json(route, folder, startposition, map_file, run_index):
    """Speichert eine Route (Liste aus 2er-Tupeln) als JSON."""
    if not route:
        return None

    os.makedirs(folder, exist_ok=True)

    filename = f"route_{run_index:03d}.json"  # route_001.json, route_002.json ...
    filepath = Path(folder) / filename

    data = {
        "startposition": int(startposition),
        "map_file": map_file,
        "route": route  # Python-Tupel werden beim json.dump automatisch Listen
    }

    with open(filepath, mode="w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return str(filepath)

def draw_grid(surface, grid, scanned_tiles, general_cfg):
    """Zeichnet alle Tiles des Grids auf die pygame-Oberflaeche."""
    for row in grid:
        for tile in row:
            tile.draw(surface, scanned_tiles, general_cfg)


# --- Sichtfeld scannen ---
def scan_fov(x, y, scanned_tiles, general_cfg, drone_cfg):
    """Markiert alle Zellen im quadratischen FOV um (x, y) als gescannt."""
    fov_radius = drone_cfg.fov_radius
    for dr in range(-fov_radius, fov_radius + 1):
        for dc in range(-fov_radius, fov_radius + 1):
            rr, cc = y + dr, x + dc
            if 0 <= rr < general_cfg.rows and 0 <= cc < general_cfg.cols:
                scanned_tiles.add((rr, cc))


def get_landing_position(grid):
    """Gibt alle Landeplatz-Koordinaten des Grids als Liste von (row, col)-Tupeln zurueck."""
    landing_positions = []
    for row in grid:
        for tile in row:
            r = tile.row
            c = tile.col
            if tile.is_landing_pad:
                landing_positions.append((r , c))

    return landing_positions
     
     
def main():
    """Laedt Karte und Konfiguration, berechnet Route und startet den pygame-Visualisierungsloop."""

    general_cfg = GeneralConfig()
    drone_cfg = DroneConfig()
    pfm_cfg = pfmConfig()

    grid = create_real_map.load_grid_from_json(map_path)
    general_cfg.rows = len(grid)
    general_cfg.cols = len(grid[0])

    landing_positions = get_landing_position(grid)
    tile_size = general_cfg.tile_size

    print(f"Karte geladen: {general_cfg.cols} x {general_cfg.rows} Zellen")
    
    pygame.init()
    screen = pygame.display.set_mode((general_cfg.cols * general_cfg.tile_size, general_cfg.rows * general_cfg.tile_size))
    pygame.display.set_caption("2D-Karte mit Drohne und FOV")
    clock = pygame.time.Clock()

    scanned_tiles = set()
    route = [landing_positions[lp]]

    for _ in range(DroneConfig.num_flights):
        if algo == 0:
            next_part = Greedy.plan_route(route[-1], landing_positions, grid, general_cfg, drone_cfg,pfm_cfg)
        else:
            next_part = Boustro.plan_route(route[-1], landing_positions, grid, general_cfg, drone_cfg, pfm_cfg)
        
        if not next_part:
            break
        else:
            route.extend(next_part)

    save_route_json(route, "routes", lp, map_path, 0)
    
    print(f"Route berechnet: {len(route)} Schritte")

    drone_idx = 0
    
    # Pygame-Loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1) Drohnen-Position entlang der Route updaten
        if drone_idx < len(route):
            drone_r, drone_c = route[drone_idx]
            drone_idx += 1
            # FOV um die neue Position scannen
            scan_fov(drone_c, drone_r, scanned_tiles, general_cfg, drone_cfg)

        # 2) Rendering
        screen.fill((0, 0, 0))
        # Zeichne alle Tiles (die .draw() markiert automatisch gescannte Felder)
        draw_grid(screen, grid, scanned_tiles, general_cfg)

        # (Optional) kompletten Pfad einzeichnen
        if len(route) > 1:
            pts = [
                (
                    c * tile_size + tile_size // 2,
                    r * tile_size + tile_size // 2,
                )
                for r, c in route
            ]
            pygame.draw.lines(
                screen,
                general_cfg.path_color,
                False,
                pts,
                general_cfg.path_width,
            )

        # 3) Drohne zeichnen
        pygame.draw.rect(
            screen,
            general_cfg.drone_color,
            (
                drone_c * tile_size,
                drone_r * tile_size,
                tile_size,
                tile_size,
            ),
        )

        # 4) Display aktualisieren und Frame-Rate einhalten
        pygame.display.flip()
        clock.tick(general_cfg.fps)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
