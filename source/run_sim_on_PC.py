#!/usr/bin/env python3
"""
run_sim_on_PC.py
 
Testlaeufe auf dem Entwicklungsrechner.
Liest Versuchsparameter aus param.csv, fuehrt fuer jeden Eintrag eine
Routenplanung durch, misst die Laufzeit und schreibt die Ergebnisse
in results.csv. Keine Temperaturmessung (nur Raspberry Pi).
"""

import run_path_find
import csv
import os
from pathlib import Path
from datetime import datetime
import time
import json

output_file = "results.csv"
routes_dir = "routes"  # Ordner für Routendateien

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

def main():
    """Fuehrt alle Messlaeufe aus param.csv durch und schreibt Ergebnisse in results.csv."""
    file_exists = os.path.isfile(output_file)
    with open(output_file, mode="a", newline="", encoding="utf-8") as results_csv:
        fieldnames = ["timestamp", "startposition", "map_file", "algo", "duration_sec", "steps", "route_file"]
        writer = csv.DictWriter(results_csv, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        with open("param.csv", newline="", encoding="utf-8") as csvfile:
            params = list(csv.DictReader(csvfile))  # Liste, damit wir Index haben

            for idx, run in enumerate(params, start=1):
                startposition = run["startposition"]
                map_file = run["map_file"]
                algo = run["algo"]
                print("-----------------------------------------------------")
                print(f"Startposition: {startposition} | Map-Datei: {map_file}")

                start_time = time.perf_counter()
                result = run_path_find.path_find(int(startposition), map_file, int(algo))
                duration = time.perf_counter() - start_time
                print(f"Laufzeit: {duration:.3f} Sekunden")

                steps = len(result)

                # Route als JSON abspeichern
                route_path = save_route_json(result, routes_dir, startposition, map_file, idx)
                print(f"Route gespeichert: {route_path}")

                writer.writerow({
                    "timestamp": datetime.now().isoformat(timespec='seconds'),
                    "startposition": startposition,
                    "map_file": map_file,
                    "algo":algo,
                    "duration_sec": round(duration, 3),
                    "steps": steps,
                    "route_file": route_path
                })

if __name__ == "__main__":
    main()