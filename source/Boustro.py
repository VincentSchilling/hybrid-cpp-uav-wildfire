"""
Boustro.py
 
Boustrophedon-Baseline (V3) fuer die Coverage-Path-Planung.
Erzeugt ein regulaeres FOV-Gitter, weist Waldzellen den Gitterzentren zu
und plant eine serpentinenartige Route mit Budget-Constraint und Rueckweg.
"""
import Dijkstra
import math


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


def mark_fov_scanned(position, grid, general_cfg, drone_cfg):
    """Markiert alle Waldzellen im FOV um position als gescannt."""
    for (r, c) in fov_cells(position[0], position[1], general_cfg, drone_cfg):
        if grid[r][c].type == 2:
            grid[r][c].is_scanned = True


def get_urban_cells(grid, general_cfg):
    """Gibt alle urbanen Zellen als Liste zurueck."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    urban = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c].type == 8:
                urban.append((r, c))
    return urban


def generate_boustro_centers(general_cfg, drone_cfg):
    """Erzeugt ein regulaeres FOV-Gitter mit Schrittweite 2R+1 in Serpentinen-Reihenfolge."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    R = drone_cfg.fov_radius
    step = 2 * R + 1

    def positions(max_idx):
        pos = []
        start = R
        end = max_idx - 1 - R
        if end < start:
            return [max(0, min(max_idx - 1, R))]
        x = start
        while x <= end:
            pos.append(x)
            x += step
        if pos and pos[-1] != end:
            pos.append(end)
        if not pos:
            pos = [start, end] if start != end else [start]
        return pos

    row_pos = positions(rows)
    col_pos = positions(cols)

    centers = []
    for i, r in enumerate(row_pos):
        if i % 2 == 0:
            for c in col_pos:
                centers.append((r, c))
        else:
            for c in reversed(col_pos):
                centers.append((r, c))
    return centers


def nearest_free_cell(position, urban_set, general_cfg, drone_cfg):
    """Gibt die naechste nicht-urbane Zelle zu position zurueck; sucht ringfoermig bis Radius R."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    R = drone_cfg.fov_radius

    pr, pc = position
    for d in range(1, R + 1):
        r0 = max(0, pr - d)
        r1 = min(rows - 1, pr + d)
        c0 = max(0, pc - d)
        c1 = min(cols - 1, pc + d)
        for cc in range(c0, c1 + 1):
            if (r0, cc) not in urban_set:
                return (r0, cc)
            if (r1, cc) not in urban_set:
                return (r1, cc)
        for rr in range(r0 + 1, r1):
            if (rr, c0) not in urban_set:
                return (rr, c0)
            if (rr, c1) not in urban_set:
                return (rr, c1)
    return None


def build_center_assignments(centers, grid, urban_set, general_cfg, drone_cfg):
    """Weist jeder Waldzelle das erste Gitterzentrum zu das sie abdeckt; nicht abgedeckte Zellen erhalten Mikro-Zentren."""
    rows = general_cfg.rows
    cols = general_cfg.cols

    snapped = []
    idx_of = {}
    center_cover = []

    # Snap + FOV-Abdeckung pro Zentrum aufbauen
    for p0 in centers:
        if p0 in urban_set:
            p = nearest_free_cell(p0, urban_set, general_cfg, drone_cfg)
            if p is None:
                continue
        else:
            p = p0
        if p not in idx_of:
            forest_in_fov = [c for c in fov_cells(p[0], p[1], general_cfg, drone_cfg) if grid[c[0]][c[1]].type == 2]
            if forest_in_fov:
                idx_of[p] = len(snapped)
                snapped.append(p)
                center_cover.append(forest_in_fov)

    # Greedy-Zuordnung: erste Abdeckung gewinnt
    assigned = [[] for _ in range(len(snapped))]
    covered = set()
    for idx, p in enumerate(snapped):
        for cell in center_cover[idx]:
            if cell not in covered:
                assigned[idx].append(cell)
                covered.add(cell)

    # Mikro-Zentren fuer nicht abgedeckte Waldzellen
    for r in range(rows):
        for c in range(cols):
            if grid[r][c].type == 2 and (r, c) not in covered:
                p = (r, c)
                forest_in_fov = [cell for cell in fov_cells(p[0], p[1], general_cfg, drone_cfg) if grid[cell[0]][cell[1]].type == 2]
                
                idx_of[p] = len(snapped)
                snapped.append(p)
                center_cover.append(forest_in_fov)
                new_assigned = []
                for cell in forest_in_fov:
                    if cell not in covered:
                        new_assigned.append(cell)
                        covered.add(cell)
                assigned.append(new_assigned)

    return snapped, assigned


def sort_centers_serpentine(centers, drone_cfg):
    """Sortiert Zentren in Serpentinen-Reihenfolge nach Baendern der Hoehe 2R+1."""
    R = drone_cfg.fov_radius
    band_height = 2 * R + 1

    def serp_key(p):
        r, c = p
        band = r // band_height
        return (band, c if band % 2 == 0 else -c)

    return sorted(range(len(centers)), key=lambda i: serp_key(centers[i]))


def has_yield(idx, assigned, grid):
    """Prueft ob ein Zentrum noch ungescannte Waldzellen in seinen Assignments hat."""
    for (r, c) in assigned[idx]:
        if grid[r][c].type == 2 and not grid[r][c].is_scanned:
            return True
    return False


def plan_route(start, pads, grid, general_cfg, drone_cfg, pfm_cfg=None):
    """Plant eine Boustrophedon-Route mit Budget-Constraint und garantiertem Rueckweg."""
    urban = get_urban_cells(grid, general_cfg)
    urban_set = set(urban)

    # Distanzvorberechnung zum naechsten Landeplatz
    distances = Dijkstra.compute_distances_to_nearest_pad(pads, general_cfg, drone_cfg)

    # Vorberechnung: Zentren, Zuordnungen, Reihenfolge
    step_centers = generate_boustro_centers(general_cfg, drone_cfg)
    snapped, assigned = build_center_assignments(step_centers, grid, urban_set, general_cfg, drone_cfg)
    order = sort_centers_serpentine(snapped, drone_cfg)

    # Routenplanung
    route = [start]
    rem = drone_cfg.budget_steps
    cur = start

    # Sicherheitscheck: reicht Budget fuer Rueckweg?
    if distances.get(cur, float("inf")) > rem:
        backpath = Dijkstra.return_path_with_dijkstra(grid, cur, pads, urban, general_cfg, drone_cfg)
        if backpath and len(backpath) - 1 <= rem:
            route.extend(backpath[1:])
            for p in backpath[1:]:
                mark_fov_scanned(p, grid, general_cfg, drone_cfg)
        return route

    i = 0
    n = len(order)
    while rem > 0 and i < n:
        # Naechstes Zentrum mit ungescannten Waldzellen suchen
        found = None
        for j in range(i, n):
            if has_yield(order[j], assigned, grid):
                found = j
                break
        if found is None:
            break

        idx = order[found]
        target = snapped[idx]

        path = Dijkstra.return_path_with_dijkstra(grid, cur, [target], urban, general_cfg, drone_cfg)
        if not path:
            i = found + 1
            continue

        need = len(path) - 1
        ret_need = math.ceil(distances.get(path[-1], float("inf")))

        if need + ret_need > rem:
            # Budget reicht nicht mehr — Rueckweg einleiten
            backpath = Dijkstra.return_path_with_dijkstra(grid, cur, pads, urban, general_cfg, drone_cfg)
            if backpath and len(backpath) - 1 <= rem:
                route.extend(backpath[1:])
                for p in backpath[1:]:
                    mark_fov_scanned(p, grid, general_cfg, drone_cfg)
            return route

        # Zentrum anfliegen
        route.extend(path[1:])
        for p in path[1:]:
            mark_fov_scanned(p, grid, general_cfg, drone_cfg)
        rem -= need
        cur = route[-1]

        # Assignments als gescannt markieren
        for (r, c) in assigned[idx]:
            grid[r][c].is_scanned = True

        i = found + 1

    # Rueckweg
    backpath = Dijkstra.return_path_with_dijkstra(grid, cur, pads, urban, general_cfg, drone_cfg)
    if backpath:
        steps_back = len(backpath) - 1
        if steps_back <= rem:
            route.extend(backpath[1:])
            for p in backpath[1:]:
                mark_fov_scanned(p, grid, general_cfg, drone_cfg)
        else:
            route.extend(backpath[1:1 + rem])
    return route