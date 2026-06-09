"""
classes.py
 
Zentrale Datenstrukturen: Konfigurationsklassen und Tile-Modell.
"""
import pygame
import math
import random
from dataclasses import dataclass, field
from typing import Dict, Tuple, List

@dataclass
class GeneralConfig:
    """Allgemeine Simulationskonfiguration: Kartengroesse, Darstellung und Farben."""
    width: int = 6000   #in Metern
    height: int = 3000  #in Metern
    tile_size: int = 7
    cols: int = 0
    rows: int = 0
    fps: int = 20
    colors = {
        0: (255, 0, 0),         # Unknown – Rot
        1: (144, 238, 144),     # Nature – Hellgrün
        2: (0, 100, 0),         # Forest – Dunkelgrün
        3: (0, 191, 255),       # Water – Blau
        4: (210, 180, 140),     # Rock/Bare – Beige
        5: (255, 250, 250),     # Ice/Snow – Weiß
        7: (0, 206, 209),       # Wetland – Türkis
        8: (128, 128, 128),     # Urban – Grau
    }
    landing_color: Tuple[int, int, int] = (255, 215, 0)
    drone_color: Tuple[int, int, int] = (0, 0, 255)
    scan_border: Tuple[int, int, int] = (255, 255, 255)
    path_color: Tuple[int, int, int] = (0, 0, 0)
    path_width: int = 1


@dataclass
class SpawnConfig:
    """Konfiguration fuer die Erzeugung synthetischer Karten (Feuer, Wasser, Landeplaetze)."""
    num_pads: int = 5
    num_fire: int = 4
    max_fire_spread: int = 30
    num_water: int = field(default_factory=lambda: random.randint(1, 3))
    max_water_spread: int = 40


@dataclass
class DroneConfig:
    """Drohnenkonfiguration: Flugbudget, Sichtfeld, Bewegungskosten und AHP-Gewichte."""
    budget_steps: int = 666     # maximale Schritte zb. 266 bei 8km flug bei 30m raster
    num_flights: int = 20       # anzahl der Flüge
    fov_radius: int = 2         # Sichtfeld-Radius in Kacheln
    new_bonus: float = 0.1      # Reward pro neues Feld
    extra_cost: float = 1       # extra kosten für djkstra bei überfliegen bekanter gebiete

    rewards ={
        0: 0.22344,  # Unknown
        1: 0.12719,  # Nature
        2: 0.44098,  # Forest
        3: 0.02729,  # Water
        4: 0.06207,  # Rock
        5: 0.02729,  # Ice
        7: 0.06082,  # Wetland
        8: 0.03092,  # Urban
    }
    
    moves: List[Dict[str, float]] = field(
        default_factory=lambda: [
            {"dr": -1, "dc": 0, "cost": 1},
            {"dr": 1, "dc": 0, "cost": 1},
            {"dr": 0, "dc": -1, "cost": 1},
            {"dr": 0, "dc": 1, "cost": 1}
            # ,{"dr": -1, "dc": -1, "cost": math.sqrt(2)},
            # {"dr": -1, "dc": 1, "cost": math.sqrt(2)},
            # {"dr": 1, "dc": -1, "cost": math.sqrt(2)},
            # {"dr": 1, "dc": 1, "cost": math.sqrt(2)},
        ]
    )

    moves_dijkstra: List[Dict[str, float]] = field(
        default_factory=lambda: [
            {"dr": -1, "dc": 0, "cost": 1},
            {"dr": 1, "dc": 0, "cost": 1},
            {"dr": 0, "dc": -1, "cost": 1},
            {"dr": 0, "dc": 1, "cost": 1},
            {"dr": -1, "dc": -1, "cost": math.sqrt(2)},
            {"dr": -1, "dc": 1, "cost": math.sqrt(2)},
            {"dr": 1, "dc": -1, "cost": math.sqrt(2)},
            {"dr": 1, "dc": 1, "cost": math.sqrt(2)},
        ]
    )
@dataclass
class pfmConfig:
    """Konfigurationsparameter fuer die Potenzialfeldmethode (V2)."""
    e = 1
    pfm_radius = 10
    type = 2
    gain = 6
    blur_sigma = 50
    blur_sigma_partiel = 0.3
    blur_sigma_recalc = 1

@dataclass
class clmsConfig:
    """Konfiguration fuer den CGLS-LC100-Datenzugriff und die Landklassen-Zuordnung."""
    coord_1: Tuple[float, float] = (0, 0)
    data_path: str = ""
    grid_size :int = 30 # in meter
    map_type = {
        0: 0,  # unknown
        20: 1,  # natur
        30: 1, 
        40: 1,
        50: 8,  # urban
        60: 4,  # gestein
        70: 5,  # ice
        80: 3,  # water
        90: 7,  # wetland
        100: 7,
        111: 2,  # forest
        112: 2,
        113: 2,
        114: 2,
        115: 2,
        116: 2,
        121: 2,
        122: 2,
        123: 2,
        124: 2,
        125: 2,
        126: 2,
        200: 3,  # water
    }

class Tile:
    """Repraesentiert eine einzelne Rasterzelle mit Typ, Position, Zustand und Koordinate."""
    def __init__(
        self, row, col, coordinate, tile_type, is_landing_pad=False, is_scanned=False, is_frontier_cell=0
    ):
        self.row: int = row
        self.col: int = col
        self.coordinate: Tuple[float, float] = coordinate
        self.type: int = tile_type
        self.is_landing_pad: bool = is_landing_pad
        self.is_scanned: bool = is_scanned
        self.is_frontier_cell: int =is_frontier_cell
        self.PFM: float = 0.0

    def to_dict(self) -> dict:
        """Serialisiert das Tile-Objekt in ein JSON-kompatibles Dict."""
        return {
            "row": self.row,
            "col": self.col,
            "coordinate": list(self.coordinate),  # Tuple -> Liste für JSON
            "type": self.type,
            "is_landing_pad": self.is_landing_pad,
            "is_scanned": self.is_scanned,
            "is_frontier_cell": self.is_frontier_cell,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tile":
        """Erzeugt ein Tile-Objekt aus einem dict (z.B. aus JSON geladen)."""
        return cls(
            row=data["row"],
            col=data["col"],
            coordinate=tuple(data["coordinate"]),
            tile_type=data.get("type", 0),
            is_landing_pad=data.get("is_landing_pad", False),
            is_scanned=data.get("is_scanned", False),
        )

    def draw(self, surface, scanned_tiles, general_cfg):
        """Zeichnet das Tile auf die pygame-Oberflaeche, gescannte Felder erhalten einen Rahmen."""
        tile_size = general_cfg.tile_size
        x = self.col * tile_size
        y = self.row * tile_size
        color = (
            general_cfg.landing_color
            if self.is_landing_pad
            else general_cfg.colors.get(self.type, (0, 0, 0))
        )
        pygame.draw.rect(
            surface,
            color,
            (x, y, tile_size, tile_size),
        )

        # Markiere gescannte Felder
        if (self.row, self.col) in scanned_tiles:
            pygame.draw.rect(
                surface, general_cfg.scan_border, (x, y, tile_size, tile_size), 1
            )
