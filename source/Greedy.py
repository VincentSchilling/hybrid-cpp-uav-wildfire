"""
Greedy.py
 
Hybrider Greedy+Dijkstra CPP-Algorithmus (V1/V2).
Planungsschleife mit lokalem Greedy-Schritt, Coverage-Hole-Erkennung
und Dijkstra-Spruengen zum naechsten Waldgebiet bzw. Hole-Eintrittspunkt.
"""

import Dijkstra, PFM
import hole_tools



def last_step_dir_from_path(path):
    """Gibt (dr, dc) des letzten Schritts in path zurück, sonst None."""
    if len(path) >= 2:
        (r0, c0), (r1, c1) = path[-2], path[-1]
        return (r1 - r0, c1 - c0)
    return None

def set_is_scanned(grid, scanned):
    """Setzt is_scanned = True fuer alle Zellen in der Liste."""
    for cell in scanned:
        grid[cell[0]][cell[1]].is_scanned = True

def set_is_frontier_cell(grid, border):
    """Erhoet den Frontier-Zaehler fuer alle ungescannten Grenzzellen."""
    for cell in border:
        if grid[cell[0]][cell[1]].is_scanned == False:
            grid[cell[0]][cell[1]].is_frontier_cell += 1   
    
def no_forest_in_new(grid, scanned):
    """Gibt True zurueck wenn keine der Zellen in scanned vom Typ Wald (2) ist."""
    no_forest = True
    for cell in scanned:
        if grid[cell[0]][cell[1]].type == 2:
            no_forest = False
    return no_forest 


def fov_border_cells(position, general_cfg, drone_cfg):
    """Gibt alle Zellen zurueck die genau eine Zelle ausserhalb des FOV-Radius liegen."""
    rows = general_cfg.rows
    cols = general_cfg.cols
    R = drone_cfg.fov_radius

    r, c = position
    border_cells = []

    for dr in range(-(R + 1), R + 2):
        for dc in range(-(R + 1), R + 2):
            nr, nc = r + dr, c + dc

            # Inneres FOV überspringen
            if abs(dr) <= R and abs(dc) <= R:
                continue

            # Nur gültige Zellen innerhalb der Karte hinzufügen
            if 0 <= nr < rows and 0 <= nc < cols:
                border_cells.append((nr, nc))

    return border_cells

def fov_cells(r, c, generel_cfg, drone_cfg):
    """Liefert alle Zellen im quadratischen Sichtfeld um (r, c)."""
    rows = generel_cfg.rows
    cols = generel_cfg.cols
    R = drone_cfg.fov_radius

    cells = []
    for dr in range(-R, R + 1):
        for dc in range(-R, R + 1):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                cells.append((nr, nc))
    return cells

def bbox_forest_uncleared(grid, bbox):
    """Gibt True zurueck wenn in der BBox noch ungescannte Waldzellen (type==2) vorhanden sind."""
    y0, x0, y1, x1 = bbox
    for r in range(y0, y1 + 1):
        row = grid[r]
        for c in range(x0, x1 + 1):
            t = row[c]
            if t.type == 2 and not t.is_scanned:
                return True
    return False

def point_in_hole(hole, pt):
    """Prueft ob pt=(y,x) in der Loch-Komponente hole liegt (via bbox + mask_local)."""
    if hole is None or "bbox" not in hole or "mask_local" not in hole:
        return False
    y, x = pt
    y0, x0, y1, x1 = hole["bbox"]
    if not (y0 <= y <= y1 and x0 <= x <= x1):
        return False
    # lokale Koords innerhalb der BBox
    ly = y - y0
    lx = x - x0
    ml = hole["mask_local"]
    if 0 <= ly < ml.shape[0] and 0 <= lx < ml.shape[1]:
        return bool(ml[ly, lx])
    return False

def plan_route(start, pads, grid, generel_cfg, drone_cfg, pfm_cfg):
    """Plant eine Greedy-Route mit Budget-Constraint, Hole-Erkennung und garantiertem Rueckweg."""
    rows = generel_cfg.rows         
    cols = generel_cfg.cols

    urban = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (grid[r][c].type == 8)
    ]
    
    moves = [(m["dr"], m["dc"], m["cost"]) for m in drone_cfg.moves]
    budget = drone_cfg.budget_steps
    turn_penalty    = 0.5
    reverse_penalty = 0.1
    prev_dir = None

    active_hole      = None
    active_hole_bbox = None
    rem_overhead      = 5
    pfm_count        = 0


    # ── Initialisierung ──────────────────────────────────────────────
    distances = Dijkstra.compute_distances_to_nearest_pad(pads, generel_cfg, drone_cfg)

    scanned = fov_cells(*start, generel_cfg, drone_cfg)
    set_is_scanned(grid, scanned)
    border = fov_border_cells(start, generel_cfg, drone_cfg)
    set_is_frontier_cell(grid, border)

    route = [start]
    current = start
    rem = budget
    calc_forest_path = False

    # PFM deaktiviert — war als globales Steuerelement evaluiert und verworfen (vgl. Abschnitt 4.5.4)
    # _ = PFM.get_PFM_score(rows, cols, grid, pfm_cfg)

    # --- Initialer Dijkstra-Sprung zum ersten Waldgebiet ---
    path = Dijkstra.shortest_path_to_nearest_forest(route[-1], grid, urban, generel_cfg, drone_cfg)

    cost = len(path) - 1
    if cost <= 0:
        rem = 0
    elif rem - cost < 0:
        rem = 0
        print("ERROR-Waldgebiet nicht erreichbar")
    else:
        prev_dir = last_step_dir_from_path(path)
        current = path[-1]
        route.extend(path[1:])
        rem -= (len(path) - 1)

        for cell in path[1:]:
            nr, nc = cell
            new_cells = fov_cells(nr, nc, generel_cfg, drone_cfg)
            set_is_scanned(grid, new_cells)
            border = fov_border_cells(cell, generel_cfg, drone_cfg)
            set_is_frontier_cell(grid, border)

    # --- Hauptschleife ---
    while rem > 0:

        if pfm_count < 5:
            pfm_count += 1
        else:
            pfm_count = 0
            # PFM-Neuberechnung deaktiviert — verletzt K5 (vgl. Abschnitt 4.5.4)
            # _ = PFM.get_PFM_score(rows, cols, grid, pfm_cfg)

        # --- (a) Sticky-Modus prüfen ---
        if active_hole_bbox is not None:
            if not bbox_forest_uncleared(grid, active_hole_bbox):
                active_hole = None
                active_hole_bbox = None
            else:
                pass

        # --- (b) Coverage-Hole-Detektion ---
        if active_hole_bbox is None:
            holes = hole_tools.detect_holes_local(
                grid,
                generel_cfg,
                center_yx        = current,
                window_radius    = 20,
                robot_radius_cells = 0,
                max_area_cells   = 70
            )

            if holes:
                H = hole_tools.select_best_hole(holes, robot_yx=current)

                if point_in_hole(H, current):
                    if bbox_forest_uncleared(grid, H["bbox"]):
                        active_hole = H
                        active_hole_bbox = H["bbox"]
                else:
                    tgt = H.get("entry_point")
                    if tgt is None:
                        cy, cx = H["centroid"]
                        tgt = (int(round(cy)), int(round(cx)))

                    path = Dijkstra.return_path_with_dijkstra_scan(
                        grid, current, pads=[tgt], urban=urban,
                        general_cfg=generel_cfg, drone_cfg=drone_cfg
                    )

                    if path:
                        cost = len(path) - 1
                        if cost + rem_overhead <= rem:
                            prev_dir = last_step_dir_from_path(path)
                            current = path[-1]
                            route.extend(path[1:])
                            rem -= (len(path) - 1)

                            for cell in path[1:]:
                                nr, nc = cell
                                new_cells = fov_cells(nr, nc, generel_cfg, drone_cfg)
                                set_is_scanned(grid, new_cells)
                                border = fov_border_cells(cell, generel_cfg, drone_cfg)
                                set_is_frontier_cell(grid, border)
                        else:
                            rem = 0

                    if rem > 0 and bbox_forest_uncleared(grid, H["bbox"]):
                        active_hole = H
                        active_hole_bbox = H["bbox"]

        # --- (c) Forest-Sprung oder Greedy-Schritt ---
        if calc_forest_path:
            calc_forest_path = False
            path = Dijkstra.shortest_path_to_nearest_forest(route[-1], grid, urban, generel_cfg, drone_cfg)
            cost = len(path) - 1
            if cost <= 0:
                rem = 0
            elif rem - cost - rem_overhead < 0:
                rem = 0
            else:
                prev_dir = last_step_dir_from_path(path)
                current = path[-1]
                route.extend(path[1:])
                rem -= (len(path) - 1)

                for cell in path:
                    nr, nc = cell
                    new_cells = fov_cells(nr, nc, generel_cfg, drone_cfg)
                    set_is_scanned(grid, new_cells)
                    border = fov_border_cells(cell, generel_cfg, drone_cfg)
                    set_is_frontier_cell(grid, border)

        else:
            # --- (d) Lokaler Greedy-Schritt ---
            best_move = None
            best_gain = float("-inf")
            best_dr   = None
            best_dc   = None
            current_fov = set(fov_cells(current[0], current[1], generel_cfg, drone_cfg))

            for dr, dc, base_cost in moves:
                nr, nc = current[0] + dr, current[1] + dc
                reward = 0.0

                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                if grid[nr][nc].type == 8:
                    continue

                extra = 0
                if prev_dir is not None:
                    if (dr, dc) != prev_dir:
                        extra += turn_penalty
                    if (dr, dc) == (-prev_dir[0], -prev_dir[1]):
                        extra += reverse_penalty

                eff_cost = base_cost + extra

                if eff_cost > rem:
                    continue
                if distances.get((nr, nc), float("inf")) > rem - eff_cost:
                    continue

                fov       = fov_cells(nr, nc, generel_cfg, drone_cfg)
                delta_fov = list(set(fov) - current_fov)
                new_cells = [cell for cell in fov if not grid[cell[0]][cell[1]].is_scanned]

                for r_, c_ in fov:
                    if grid[r_][c_].type == 8:
                        reward -= 3

                for r_, c_ in delta_fov:
                    # PFM-Bias deaktiviert: reward += grid[r_][c_].PFM
                    reward += drone_cfg.rewards.get(grid[r_][c_].type, 0.0) * 10
                    if grid[r_][c_].type == 2:
                        reward += (grid[r_][c_].is_frontier_cell) / 10
                    if not grid[r_][c_].is_scanned:
                        reward += 5
                    else:
                        reward -= 7

                gain = reward / eff_cost if eff_cost > 0 else 0.0

                if gain > best_gain:
                    best_gain = gain
                    best_move = (nr, nc, eff_cost, new_cells)
                    best_dr   = dr
                    best_dc   = dc

            if not best_move:
                break

            nr, nc, eff_cost, new_cells = best_move
            if no_forest_in_new(grid, new_cells):
                calc_forest_path = True
            else:
                current = (nr, nc)
                route.append(current)
                set_is_scanned(grid, new_cells)
                border = fov_border_cells(current, generel_cfg, drone_cfg)
                set_is_frontier_cell(grid, border)
                rem     -= eff_cost
                prev_dir = (best_dr, best_dc)

    # --- Rückweg ---
    backpath = Dijkstra.return_path_with_dijkstra(grid, current, pads, urban, generel_cfg, drone_cfg)

    for cell in backpath:
        nr, nc = cell
        new_cells = fov_cells(nr, nc, generel_cfg, drone_cfg)
        set_is_scanned(grid, new_cells)
        border = fov_border_cells(cell, generel_cfg, drone_cfg)
        set_is_frontier_cell(grid, border)

    route.extend(backpath)

    return route