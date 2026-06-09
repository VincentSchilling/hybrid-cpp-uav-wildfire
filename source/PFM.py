"""
PFM.py

Potenzialfeldmethode (PFM) fuer den hybriden CPP-Algorithmus (V2).
Berechnet fuer jede Rasterzelle einen Attraktions- bzw. Repulsionswert
basierend auf BFS-Distanzen zu Wald- und Urbanzellen.
"""
from collections import deque
from classes import pfmConfig


def get_mask(rows, cols, grid, mask_typ, visited_mask):
    """Erzeugt eine binaere Maske fuer Zellen des angegebenen Typs die noch nicht gescannt sind."""
    mask = []
    for r in range(rows):
        line = []
        for c in range(cols):
            tile = grid[r][c]
            if tile.type == mask_typ and (not tile.is_scanned):
                line.append(1)
                visited_mask[r][c] = True
            else:
                line.append(0)
        mask.append(line)
    return mask, visited_mask


def create_BFS_queue(rows, cols, mask, distance):
    """Initialisiert BFS-Queue und Distanz-Array aus einer binaeren Maske."""
    queue = deque()
    for r in range(rows):
        for c in range(cols):
            if mask[r][c] == 1:
                queue.append((r, c))
                distance[r][c] = 0
    return queue, distance


def BFS(rows, cols, mask, visited):
    """Fuehrt BFS aus und gibt eine Distanzmatrix zur naechsten Masken-Zelle zurueck."""
    distance = [[0] * cols for _ in range(rows)]
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    queue, distance = create_BFS_queue(rows, cols, mask, distance)
    distance_counter = 0

    if len(queue) == 0:
        return []

    while queue:
        new_queue = deque()
        while queue:
            r, c = queue.popleft()
            distance[r][c] = distance_counter
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                    visited[nr][nc] = True
                    new_queue.append((nr, nc))
        queue = new_queue
        distance_counter += 1

    return distance


def PFM(grid, distance, e, PFM_score, gain, polarity):
    """Berechnet den PFM-Score fuer alle Zellen basierend auf der BFS-Distanzmatrix."""
    for row in grid:
        for tile in row:
            r = tile.row
            c = tile.col
            BFS_score = distance[r][c]
            if polarity:
                PFM_score[r][c] = ((1 / (BFS_score + e)) * gain)
            else:
                PFM_score[r][c] = (-(1 / (BFS_score + e)) * gain)
    return PFM_score


def get_PFM_score(rows, cols, grid, pfm_cfg):
    """Berechnet den kombinierten PFM-Score (Wald-Attraktion + Urban-Repulsion) fuer das gesamte Grid."""
    mask_type = pfm_cfg.type

    visited_mask = [[False] * cols for _ in range(rows)]
    forest_PFM_score = [[0] * cols for _ in range(rows)]
    urban_PFM_score = [[0] * cols for _ in range(rows)]

    mask, visited_mask = get_mask(rows, cols, grid, mask_type, visited_mask)
    distance = BFS(rows, cols, mask, visited_mask)

    if len(distance) == 0:
        PFM_score = []
    else:
        forest_PFM_score = PFM(grid, distance, pfm_cfg.e, forest_PFM_score, pfm_cfg.gain, True)

    visited_mask = [[False] * cols for _ in range(rows)]
    urban_mask, visited_mask = get_mask(rows, cols, grid, 8, visited_mask)
    distance = BFS(rows, cols, urban_mask, visited_mask)

    if len(distance) == 0:
        pass
    else:
        urban_PFM_score = PFM(grid, distance, pfm_cfg.e, urban_PFM_score, 1, False)

    PFM_score = [[0] * cols for _ in range(rows)]
    for row in grid:
        for tile in row:
            r = tile.row
            c = tile.col
            tile.PFM = forest_PFM_score[r][c] + urban_PFM_score[r][c]
            PFM_score[r][c] = tile.PFM

    return PFM_score