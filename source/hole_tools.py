"""
hole_tools.py

Lokale Coverage-Hole-Erkennung fuer den hybriden CPP-Algorithmus.
Erkennt ungescannte Waldzellen-Inseln im lokalen Suchfenster
und berechnet Eintrittspunkte fuer gezielte Dijkstra-Spruenge.
"""
from collections import deque
from typing import Dict, List, Tuple, Optional
import math
import numpy as np

DIR4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def clip_window(center: Tuple[int, int], radius: int, rows: int, cols: int) -> Tuple[int, int, int, int]:
    """Begrenzt ein quadratisches Fenster um center auf die Kartengrenzen."""
    cy, cx = center
    y0 = max(0, cy - radius)
    x0 = max(0, cx - radius)
    y1 = min(rows - 1, cy + radius)
    x1 = min(cols - 1, cx + radius)
    return y0, x0, y1, x1


def binary_dilate(mask: np.ndarray, r: int) -> np.ndarray:
    """Quadratische Dilatation mit Radius r (ohne SciPy). r=0 gibt unveraenderte Kopie zurueck."""
    if r <= 0:
        return mask.copy()
    H, W = mask.shape
    out = mask.copy()
    for y in range(H):
        xs = np.where(mask[y])[0]
        if xs.size == 0:
            continue
        row = out[y]
        for x in xs:
            x0 = max(0, x - r)
            x1 = min(W - 1, x + r)
            row[x0:x1 + 1] = True
    col_true = np.where(out.any(axis=1))[0]
    if col_true.size == 0:
        return out
    base = out.copy()
    for dy in range(1, r + 1):
        up = np.vstack([base[dy:], np.zeros((dy, base.shape[1]), dtype=bool)])
        dn = np.vstack([np.zeros((dy, base.shape[1]), dtype=bool), base[:-dy]])
        out |= up | dn
    return out


def label_components(mask: np.ndarray) -> np.ndarray:
    """4-Nachbarschaft-Labeling per BFS. Gibt Label-Array zurueck: 0 = Hintergrund, 1..K = Komponenten."""
    H, W = mask.shape
    labels = np.zeros((H, W), dtype=int)
    lid = 0
    for r in range(H):
        for c in range(W):
            if mask[r, c] and labels[r, c] == 0:
                lid += 1
                q = deque([(r, c)])
                labels[r, c] = lid
                while q:
                    y, x = q.popleft()
                    for dy, dx in DIR4:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and labels[ny, nx] == 0:
                            labels[ny, nx] = lid
                            q.append((ny, nx))
    return labels


def component_descriptors(labels: np.ndarray, lid: int, y0: int, x0: int) -> Dict:
    """Berechnet Flaeche, Bounding Box und Schwerpunkt einer Komponente in globalen Koordinaten."""
    ys, xs = np.where(labels == lid)
    area = int(ys.size)
    yy0, xx0 = int(ys.min()), int(xs.min())
    yy1, xx1 = int(ys.max()), int(xs.max())
    g_y0, g_x0, g_y1, g_x1 = y0 + yy0, x0 + xx0, y0 + yy1, x0 + xx1
    cy, cx = (y0 + ys.mean(), x0 + xs.mean())
    return {
        "area": area,
        "bbox": (g_y0, g_x0, g_y1, g_x1),
        "centroid": (float(cy), float(cx)),
        "local_mask_bbox": (yy0, xx0, yy1, xx1),
        "local_pixels": (ys, xs)
    }


def frontier_seeds_for_component(obst_roi: np.ndarray, hole_labels: np.ndarray, lid: int,
                                  y0: int, x0: int) -> np.ndarray:
    """Gibt freie 4-Nachbarn der Hole-Zellen als globale Koordinaten zurueck (Frontier-Seeds)."""
    H, W = hole_labels.shape
    ys, xs = np.where(hole_labels == lid)
    seeds: set = set()
    for y, x in zip(ys, xs):
        for dy, dx in DIR4:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                if (not obst_roi[ny, nx]) and (hole_labels[ny, nx] != lid):
                    seeds.add((y0 + ny, x0 + nx))
    if not seeds:
        return np.empty((0, 2), dtype=int)
    arr = np.fromiter((coord for rc in seeds for coord in rc), dtype=int).reshape(-1, 2)
    return arr


def nearest_point(points: np.ndarray, ref: Tuple[int, int]) -> Optional[Tuple[int, int]]:
    """Gibt den naechsten Punkt in points zur Referenzposition ref zurueck."""
    if points.size == 0:
        return None
    py = points[:, 0].astype(float)
    px = points[:, 1].astype(float)
    dy = py - ref[0]
    dx = px - ref[1]
    idx = int(np.argmin(dy * dy + dx * dx))
    return int(py[idx]), int(px[idx])


def detect_holes_local(
    grid,
    general_cfg,
    center_yx: Tuple[int, int],
    window_radius: int = 10,
    robot_radius_cells: int = 0,
    min_area_cells: int = 0,
    max_area_cells: Optional[int] = 40,
) -> List[Dict]:
    """
    Erkennt ungescannte Waldzellen-Inseln (Holes) in einem lokalen Fenster um center_yx.

    Hindernisse = alle Nicht-Wald-Zellen (tile.type != 2).
    Holes = ungescannte Zellen ohne Verbindung zum Fensterrand.
    Gibt eine Liste von Hole-Dicts zurueck mit area, bbox, centroid, frontier_seeds,
    entry_point und mask_local.
    """
    rows, cols = general_cfg.rows, general_cfg.cols
    cy, cx = center_yx
    y0, x0, y1, x1 = clip_window(center_yx, window_radius, rows, cols)

    H, W = (y1 - y0 + 1), (x1 - x0 + 1)
    if H <= 0 or W <= 0:
        return []

    scanned = np.zeros((H, W), dtype=bool)
    obst = np.zeros((H, W), dtype=bool)

    for ry in range(H):
        gy = y0 + ry
        row_tiles = grid[gy]
        for rx in range(W):
            gx = x0 + rx
            t = row_tiles[gx]
            if getattr(t, "is_scanned", False):
                scanned[ry, rx] = True
            if getattr(t, "type", 0) != 2:
                obst[ry, rx] = True

    inflated = binary_dilate(obst, robot_radius_cells)
    unknown = (~scanned) & (~inflated)

    outside = np.zeros_like(unknown, dtype=bool)
    vis = np.zeros_like(unknown, dtype=bool)
    q = deque()

    for rx in range(W):
        if unknown[0, rx] and not vis[0, rx]:
            vis[0, rx] = True
            outside[0, rx] = True
            q.append((0, rx))
        if unknown[H - 1, rx] and not vis[H - 1, rx]:
            vis[H - 1, rx] = True
            outside[H - 1, rx] = True
            q.append((H - 1, rx))
    for ry in range(H):
        if unknown[ry, 0] and not vis[ry, 0]:
            vis[ry, 0] = True
            outside[ry, 0] = True
            q.append((ry, 0))
        if unknown[ry, W - 1] and not vis[ry, W - 1]:
            vis[ry, W - 1] = True
            outside[ry, W - 1] = True
            q.append((ry, W - 1))

    while q:
        y, x = q.popleft()
        for dy, dx in DIR4:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not vis[ny, nx] and unknown[ny, nx]:
                vis[ny, nx] = True
                outside[ny, nx] = True
                q.append((ny, nx))

    hole_mask = unknown & (~outside)
    if not hole_mask.any():
        return []

    labels = label_components(hole_mask)

    holes: List[Dict] = []
    lids = np.unique(labels)
    lids = lids[lids > 0]
    for lid in lids:
        desc = component_descriptors(labels, lid, y0, x0)

        if desc["area"] < min_area_cells:
            continue
        if (max_area_cells is not None) and (desc["area"] > max_area_cells):
            continue

        seeds = frontier_seeds_for_component(obst, labels, lid, y0, x0)

        ys_local, xs_local = desc["local_pixels"]
        hole_cells_global = np.column_stack((y0 + ys_local, x0 + xs_local)).astype(int)
        entry = nearest_point(hole_cells_global, (cy, cx))

        yy0, xx0, yy1, xx1 = desc["local_mask_bbox"]
        mask_local = (labels[yy0:yy1 + 1, xx0:xx1 + 1] == lid)

        holes.append({
            "area": desc["area"],
            "bbox": desc["bbox"],
            "centroid": desc["centroid"],
            "frontier_seeds": seeds,
            "entry_point": entry,
            "mask_local": mask_local,
        })
    return holes


def select_best_hole(holes: List[Dict], robot_yx: Tuple[int, int]) -> Optional[Dict]:
    """
    Waehlt das naechstgelegene Hole anhand eines Distanz-Scores aus und gibt es zurueck.
    Stellt sicher dass entry_point gesetzt ist (Fallback: Frontier-Seed oder BBox-Mitte).
    """
    if not holes:
        return None

    ry, rx = robot_yx
    w_d = 1.0
    w_a = 0.0

    best = None
    best_score = -1e18

    for hole in holes:
        (y0, x0, y1, x1) = hole["bbox"]
        cy = (y0 + y1) / 2.0
        cx = (x0 + x1) / 2.0
        d2 = (cy - ry) * (cy - ry) + (cx - rx) * (cx - rx)
        score = w_d * (1.0 / (math.sqrt(d2) + 1.0)) + w_a * float(hole["area"])
        if score > best_score:
            best_score = score
            best = hole

    if best is not None:
        if best.get("entry_point") is None:
            seeds = best.get("frontier_seeds", np.empty((0, 2), dtype=int))
            tgt = nearest_point(seeds, robot_yx)
            if tgt is None:
                y0, x0, y1, x1 = best["bbox"]
                tgt = (int(round((y0 + y1) / 2)), int(round((x0 + x1) / 2)))
            best["entry_point"] = tgt

    return best