#!/usr/bin/env python3
"""
create_map.py
 
Erzeugt eine synthetische 2D-Rasterkarte als Textdatei (map.txt).
Tiles:
  0 = Wald
  1 = Brennend
  2 = Verbrannt
  3 = Wasser
  L = Landeplatz
"""

import random

OUTPUT_FILE = "map.txt"


def generate_map(general_cfg, spawn_cfg):
    """Erzeugt ein zufaelliges 2D-Grid mit Feuer-, Wasser- und Landeplatz-Tiles."""
    cols = general_cfg.cols
    rows = general_cfg.rows
    # Erstelle leere Karte mit Wald
    grid = [[0 for _ in range(cols)] for _ in range(rows)]

    all_positions = [(r, c) for r in range(rows) for c in range(cols)]

    # 1) Brennende Felder
    fire_positions = random.sample(all_positions, spawn_cfg.num_fire)
    for r, c in fire_positions:
        spread = random.randint(1, spawn_cfg.max_fire_spread)
        for dy in range(spread):
            for dx in range(spread):
                nr, nc = r + dy, c + dx
                if 0 <= nr < rows and 0 <= nc < cols:
                    grid[nr][nc] = 1

    # 2) Wasser-Felder
    water_positions = random.sample(all_positions, spawn_cfg.num_water)
    for r, c in water_positions:
        spread = random.randint(1, spawn_cfg.max_water_spread)
        for dy in range(spread):
            for dx in range(spread):
                nr, nc = r + dy, c + dx
                if 0 <= nr < rows and 0 <= nc < cols:
                    grid[nr][nc] = 3

    # 3) Landeplätze
    landing_positions = random.sample(all_positions, spawn_cfg.num_pads)
    for r, c in landing_positions:
        grid[r][c] = "L"

    return grid, landing_positions


def write_map_to_file(grid, filename):
    """Schreibt das Grid als Textdatei mit leerzeichen-getrennten Tile-Werten."""
    with open(filename, "w") as f:
        for row in grid:
            line = " ".join(str(cell) for cell in row)
            f.write(line + "\n")
    pad_count = sum(1 for row in grid for cell in row if cell == "L")
    print(
        f"Karte in '{filename}' geschrieben ({len(grid)}×{len(grid[0])}, Pads: {pad_count})"
    )


def creat_map(GENERAL_CONFIG, SPAWN_CONFIG):
    """Erzeugt eine zufaellige Karte und speichert sie als map.txt."""
    grid, landing_positions = generate_map(GENERAL_CONFIG, SPAWN_CONFIG)

    write_map_to_file(grid, OUTPUT_FILE)
    return landing_positions
