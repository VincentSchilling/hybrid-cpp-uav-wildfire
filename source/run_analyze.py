#!/usr/bin/env python3
"""
run_analyze.py
--------------
Analysiert alle Läufe einer Versuchsvariante aus einer results.csv.

Ausgabe:
  - Eine CSV-Datei mit einer Zeile pro Messung (alle Metriken)
  - Konsole: Mittelwert und Standardabweichung aller Metriken

Konfiguration: nur die drei Pfad-Variablen unten anpassen.
"""

import csv
import statistics
from pathlib import Path

from analyze_path import analyze_path

# --- Konfiguration ---

RESULTS_CSV = "results.csv"
ROUTES_DIR  = "routes"
MAP_DIR     = "maps"
OUTPUT_CSV  = "analysis_output.csv"

# --- Energiemodell (vgl. §3.6.2) ---
E_SCHRITT_J  = 660.0   # Energie pro Schritt (30 m bei v=10 m/s, P=220 W)
STEP_SIZE_M  = 30.0    # Zellgröße in Metern


def e_gesamt(route_length_m: float, turns: int, uturns: int) -> float:
    """
    E_ges = ( L(P)/s  +  0.25 * (N(P) + N(P)_180°) ) * E_Schritt
    U-Turns werden durch den zusätzlichen N(P)_180°-Term effektiv doppelt gewichtet.
    """
    return (route_length_m / STEP_SIZE_M + 0.25 * (turns + uturns)) * E_SCHRITT_J


def std(values: list) -> float:
    """Berechnet die Stichproben-Standardabweichung (ddof=1); gibt 0.0 zurueck bei weniger als 2 Werten."""
    return statistics.stdev(values) if len(values) > 1 else 0.0

# --- Hauptprogramm ---

def main():
    """Liest results.csv, berechnet alle Metriken und schreibt Ergebnisse in analysis_output.csv."""
    results_path = Path(RESULTS_CSV)
    map_dir      = Path(MAP_DIR)
    output_path  = Path(OUTPUT_CSV)

    col_route   = []
    col_turns   = []
    col_uturns  = []
    col_eges    = []
    col_sfr     = []
    col_zeit    = []
    col_temp    = []
    col_overlap = []
    col_overlap_forest = []

    output_rows = []

    with results_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for run in reader:
            # Nur Dateiname aus CSV verwenden, Pfad aus ROUTES_DIR aufbauen
            route_path = Path(ROUTES_DIR) / Path(run["route_file"]).name
            map_path   = map_dir / Path(run["map_file"]).name

            # Routenanalyse
            res = analyze_path(str(route_path), str(map_path))

            # Metriken
            route_m   = res["route_length_meters"]
            turns     = res["turns_total"]
            uturns    = res["uturns_total"]
            sfr       = res["scanned_forest_rate"]
            zeit      = float(run["duration_sec"])
            temp_mean = (float(run["temp1"]) + float(run["temp2"])) / 2.0
            eges             = e_gesamt(route_m, turns, uturns)
            overlap          = res["overlap_rate"]
            overlap_forest   = res["overlap_rate_forest"]

            col_route.append(route_m)
            col_turns.append(turns)
            col_uturns.append(uturns)
            col_eges.append(eges)
            col_sfr.append(sfr)
            col_zeit.append(zeit)
            col_temp.append(temp_mean)
            col_overlap.append(overlap)
            col_overlap_forest.append(overlap_forest)

            output_rows.append({
                "map_file":              run["map_file"],
                "startposition":         run["startposition"],
                "route_length_m":        round(route_m, 2),
                "turns":                 turns,
                "uturns":                uturns,
                "E_gesamt_J":            round(eges, 1),
                "scanned_forest_rate":   round(sfr, 6),
                "duration_sec":          zeit,
                "overlap_rate":           round(overlap, 6),
                "overlap_rate_forest":    round(overlap_forest, 6),
                "temp_mean_C":            round(temp_mean, 2),
            })

    # --- CSV schreiben ---
    fieldnames = list(output_rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"CSV gespeichert: {output_path}")

    # --- Konsolenausgabe ----
    n = len(output_rows)
    print(f"\n=== Auswertung ({n} Messungen) ===")
    print(f"{'Metrik':<25} {'Mittelwert':>14} {'Std-Abw.':>12}")
    print("-" * 55)
    print(f"{'Routenlänge (m)':<25} {sum(col_route)/n:>14.2f} {std(col_route):>12.2f}")
    print(f"{'Turns':<25} {sum(col_turns)/n:>14.2f} {std(col_turns):>12.2f}")
    print(f"{'U-Turns':<25} {sum(col_uturns)/n:>14.2f} {std(col_uturns):>12.2f}")
    print(f"{'E_gesamt (J)':<25} {sum(col_eges)/n:>14.1f} {std(col_eges):>12.1f}")
    print(f"{'Scanned Forest Rate':<25} {sum(col_sfr)/n*100:>13.2f}% {std(col_sfr)*100:>11.2f}%")
    print(f"{'Rechenzeit (s)':<25} {sum(col_zeit)/n:>14.3f} {std(col_zeit):>12.3f}")
    print(f"{'Overlap (gesamt)':<25} {sum(col_overlap)/n*100:>13.2f}% {std(col_overlap)*100:>11.2f}%")
    print(f"{'Overlap (Wald)':<25} {sum(col_overlap_forest)/n*100:>13.2f}% {std(col_overlap_forest)*100:>11.2f}%")
    print(f"{'Temperatur Ø (°C)':<25} {sum(col_temp)/n:>14.2f} {std(col_temp):>12.2f}")

if __name__ == "__main__":
    main()