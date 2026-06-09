"""
Dijkstra.py

Dijkstra-basierte Pfadplanungsfunktionen fuer den hybriden CPP-Algorithmus.
Stellt kuerzeste Pfade zu Zielzellen sowie Multi-Source-Distanzvorberechnungen
zu Landepunkten bereit.
"""
import heapq
import math


def inflate_pads_offsets(pads, general_cfg, drone_cfg):
    """Expandiert eine Menge von Zielpositionen um den quadratischen FOV-Radius."""
    rows, cols = general_cfg.rows, general_cfg.cols
    R = int(drone_cfg.fov_radius)
    pads_set = pads if isinstance(pads, set) else set(pads)
    if R <= 0 or not pads_set:
        return set(pads_set)

    offsets = [(dr, dc) for dr in range(-R, R + 1) for dc in range(-R, R + 1)]

    inflated = set()
    for pr, pc in pads_set:
        for dr, dc in offsets:
            r, c = pr + dr, pc + dc
            if 0 <= r < rows and 0 <= c < cols:
                inflated.add((r, c))
    return inflated


def shortest_path_to_nearest_forest(start, grid, urban, general_cfg, drone_cfg):
    """Gibt den kuerzesten Pfad von start zur naechsten ungescannten Waldzelle zurueck."""
    rows, cols = general_cfg.rows, general_cfg.cols

    forest_tiles = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (grid[r][c].type == 2 and not grid[r][c].is_scanned)
    ]

    if not forest_tiles:
        return []

    return return_path_with_dijkstra_scan(grid, start, forest_tiles, urban, general_cfg, drone_cfg)


def return_path_with_dijkstra(grid, start, pads, urban, general_cfg, drone_cfg):
    """Gibt den kuerzesten Pfad von start zum naechsten Pad zurueck (Early-Exit Dijkstra)."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    moves = [(m["dr"], m["dc"], m["cost"]) for m in drone_cfg.moves_dijkstra]

    dist = {(r, c): float("inf") for r in range(rows) for c in range(cols)}
    prev = {}
    dist[start] = 0
    pq = [(0, start)]
    visited = set()
    target = None

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u in pads:
            target = u
            break

        for dr, dc, cost in moves:
            v = (u[0] + dr, u[1] + dc)
            if v in urban:
                continue
            if 0 <= v[0] < rows and 0 <= v[1] < cols:
                nd = d + cost
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

    if target is None:
        return []

    path = []
    u = target
    while u != start:
        path.append(u)
        u = prev[u]
    path.append(start)
    return path[::-1]


def return_path_with_dijkstra_scan(grid, start, pads, urban, general_cfg, drone_cfg):
    """Gibt den kuerzesten Pfad von start zur naechsten FOV-expandierten Zielzelle zurueck."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    moves = [(m["dr"], m["dc"], m["cost"]) for m in drone_cfg.moves_dijkstra]
    pads = inflate_pads_offsets(pads, general_cfg, drone_cfg)

    dist = {(r, c): float("inf") for r in range(rows) for c in range(cols)}
    prev = {}
    dist[start] = 0
    pq = [(0, start)]
    visited = set()
    target = None

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u in pads:
            target = u
            break

        for dr, dc, cost in moves:
            v = (u[0] + dr, u[1] + dc)
            if v in urban:
                continue
            if 0 <= v[0] < rows and 0 <= v[1] < cols:
                nd = d + cost
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

    if target is None:
        return []

    path = []
    u = target
    while u != start:
        path.append(u)
        u = prev[u]
    path.append(start)
    return path[::-1]


def compute_distances_to_nearest_pad(pads, general_cfg, drone_cfg):
    """Multi-Source Dijkstra: berechnet fuer jeden Gitterpunkt die Distanz zum naechsten Pad."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    moves = [(m["dr"], m["dc"], m["cost"]) for m in drone_cfg.moves_dijkstra]

    dist = {(r, c): float("inf") for r in range(rows) for c in range(cols)}

    pq = []
    for pad in pads:
        dist[pad] = 0
        heapq.heappush(pq, (0, pad))

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for dr, dc, cost in moves:
            v = (u[0] + dr, u[1] + dc)
            if not (0 <= v[0] < rows and 0 <= v[1] < cols):
                continue
            nd = d + cost
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))

    return dist