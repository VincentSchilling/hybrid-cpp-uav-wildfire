# Hybrider Coverage-Path-Planning-Ansatz für UAVs im Waldbrandmanagement

Digitaler Anhang zur Masterarbeit:

> **„Entwicklung und experimentelle Analyse eines hybriden Coverage-Path-Planning-Ansatzes für UAVs im Kontext des Waldbrandmanagements"**
> Vincent Schilling, Technische Universität Berlin, 2025

---

## Überblick

Dieses Repository enthält den vollständigen Quellcode der o.g. Masterarbeit. Der entwickelte Algorithmus plant Überwachungsrouten für unbemannte Luftfahrzeuge (UAVs) auf einem Rastergitter und kombiniert eine Greedy-Heuristik mit Dijkstra-basierten Sprüngen.

Drei Varianten wurden implementiert und evaluiert:

| Variante | Beschreibung                    |
| -------- | ------------------------------- |
| **V1**   | Hybrid (Greedy + Dijkstra)      |
| **V2**   | V1 + Potenzialfeldmethode (PFM) |
| **V3**   | Boustrophedon-Baseline          |

Die Evaluation erfolgte auf 10 Testkarten (7 reale Geodaten, 3 synthetische) mit je 5 Startpositionen auf einem Raspberry Pi 2B.

---

## Verzeichnisstruktur

```
hybrid-cpp-uav-wildfire/
├── README.md
├── requirements.txt
├── .gitignore
│
├── maps/                          # Rasterkarten als JSON (reale und synthetische Gebiete)
│
├── messergebnisse/                # Messergebnisse aller Versuchsläufe
│   ├── V1/                        # Greedy+Dijkstra
│   │   └── routes/                # Routen-JSONs
│   ├── V2/                        # Greedy+Dijkstra+PFM
│   │   └── routes/
│   ├── V3/                        # Boustrophedon-Baseline
│   │   └── routes/
│   ├── PFM_2/                     # PFM-Parameterstudie (gain=2)
│   │   └── routes/
│   ├── PFM_3/                     # PFM-Parameterstudie (gain=3)
│   │   └── routes/
│   └── PFM_5/                     # PFM-Parameterstudie (gain=5)
│       └── routes/
│
└── source/                        # Quellcode
    ├── routes/                    # Routen-JSONs lokaler Testläufe
    ├── classes.py                 # Datenstrukturen: Tile, GeneralConfig, DroneConfig, pfmConfig
    ├── Greedy.py                  # Greedy-Heuristik mit Dijkstra-Integration (V1/V2)
    ├── Dijkstra.py                # Dijkstra-Pfadplanung und Distanzvorberechnung
    ├── Boustro.py                 # Boustrophedon-Baseline (V3)
    ├── PFM.py                     # Potenzialfeldmethode (V2-Erweiterung)
    ├── hole_tools.py              # Erkennung und Verwaltung von Coverage Holes
    ├── make_grid.py               # Geografisches Koordinatengitter (TM-Projektion)
    ├── create_map.py              # Synthetische Kartengenerierung
    ├── create_real_map.py         # Kartengenerierung aus realen Geodaten
    ├── open_clms.py               # CGLS-LC100-Landbedeckungsdaten einlesen
    ├── Simulation.py              # Interaktive Visualisierungsumgebung (pygame)
    ├── run_path_find.py           # Dispatcher: Routenplanung für alle Varianten
    ├── run_sim_on_PC.py           # Batch-Testläufe auf dem Entwicklungsrechner
    ├── run_sim_on_raspi.py        # Batch-Messläufe auf dem Raspberry Pi 2B
    ├── run_remote.py              # Remote-Steuerung des Raspberry Pi per SSH
    ├── run_analyze.py             # Auswertung der Messergebnisse (Metriken, CSV-Export)
    ├── analyze_path.py            # Kernmodul zur Routenanalyse
    ├── results.csv                # Messergebnisse der Versuchsläufe
    └── param.csv                  # Versuchsparameter (Karte, Startposition, Algorithmus)
```

---

## Abhängigkeiten

Python 3.x, getestet auf Raspberry Pi 2B (Raspberry Pi OS) und Windows (PC-Simulation).

```
numpy
pygame
rasterio
pyproj
paramiko
```

Installation:
```bash
pip install -r requirements.txt
```

Standardbibliotheken (kein Install nötig): `heapq`, `csv`, `json`, `os`, `math`, `random`, `collections`, `pathlib`, `datetime`, `time`, `subprocess`, `statistics`

---

## Schnellstart

### Routenplanung

```python
from run_path_find import path_find

# algo: 0 = V1/V2 (Greedy+Dijkstra), 1 = V3 (Boustrophedon)
route = path_find(lp=0, map_json="maps/map_Missen_Wilhams.json", algo=0)
```

### Simulation auf dem PC (mit pygame-Visualisierung)

```bash
python Simulation.py
```

### Batch-Testläufe auf dem PC

```bash
python run_sim_on_PC.py
```

### Batch-Messläufe auf dem Raspberry Pi

```bash
python run_sim_on_raspi.py
```

### Auswertung

```bash
python run_analyze.py
```

---

## Kartengenerierung

**Reale Karten** werden mit `create_real_map.py` aus CGLS-LC100 GeoTIFF-Daten erzeugt. Pfad zur TIF-Datei und Zentrumskoordinate der AOI sind im `__main__`-Block anzupassen.

**Synthetische Karten** werden mit `create_map.py` erzeugt.

Verwendete Geodaten:
- **CGLS-LC100** — Copernicus Global Land Service Land Cover (100 m Auflösung)
- Koordinatensystem: WGS84 (EPSG:4326)

---

## Ausblick: Konzeptionelle Hardwarekonfiguration für den Realbetrieb

> **Hinweis:** Die Routenplanung wurde ausschließlich in der Simulation sowie hinsichtlich der Laufzeit auf einem Raspberry Pi 2B evaluiert. Der folgende Abschnitt skizziert eine mögliche Konfiguration für den realen UAV-Betrieb auf Basis von Open-Source-Komponenten. Es handelt sich um eine konzeptionelle Einordnung — keine im Rahmen dieser Arbeit realisierte oder getestete Hardware.

### Flugsteuerung und Firmware

| Komponente | Beschreibung | Link |
|---|---|---|
| **Pixhawk** | Open-Source-Hardwarestandard für Flight Controller | [pixhawk.org](https://pixhawk.org/) |
| **Cube Orange** | Professionelles Pixhawk-kompatibles Board mit dreifach redundanten IMUs und Schwingungsentkopplung | [cubepilot.com](https://www.cubepilot.com/#/cube/features) |
| **ArduPilot** | Quelloffene Firmware; unterstützt vollständige Wegpunktmissionen | [ardupilot.org](https://ardupilot.org/) |
| **PX4** | Alternative quelloffene Firmware | [px4.io](https://px4.io/) |
| **MAVLink** | Kommunikationsprotokoll zwischen Flight Controller und Rechenmodul | [mavlink.io](https://mavlink.io/en/) |

Die Firmware unterstützt vollständige Wegpunktmissionen einschließlich automatischer Höhenanpassung. Die in dieser Arbeit erzeugten Routen können direkt als Missionsdateien über [Mission Planner](https://ardupilot.org/planner/) oder [QGroundControl](http://qgroundcontrol.com/) übertragen werden.

### Rechenmodul

Die Pfadplanung wird auf einem separaten Rechenmodul ausgeführt und übergibt die Wegpunkte über MAVLink an die Flugsteuerung. Die Laufzeitanalyse dieser Arbeit auf dem Raspberry Pi 2B belegt die Eignung eines kompakten Einplatinenrechners für diese Aufgabe. Die Anbindung erfolgt typischerweise über eine serielle Verbindung zwischen dem `TELEM2`-Port der Flugsteuerung und der seriellen Schnittstelle des Rechenmoduls.

| Komponente | Link |
|---|---|
| **Raspberry Pi 2B** (evaluierte Plattform) | [raspberrypi.com](https://www.raspberrypi.com/) |
| **Companion Computer Setup (ArduPilot)** | [ardupilot.org/dev/docs/companion-computers](https://ardupilot.org/dev/docs/companion-computers.html) |

### Sensorik

| Komponente | Beschreibung | Link |
|---|---|---|
| **FLIR Boson** | Kompakte Wärmebildkamera, bis zu 640 × 512 Pixel, für Detektion von Glutnestern und Brandherden | [teledyneflir.com](https://www.teledyneflir.com/products/thermal-camera-cores/boson/) |
| **RTK-GNSS** | Zentimetergenaue Positionierung für präzise Geolokalisierung | [ardupilot.org/copter/docs/common-gps-blending](https://ardupilot.org/copter/docs/common-gps-blending.html) |

### Kommunikation

Für Telemetrie- und Missionsdaten zwischen UAV und Bodenstation kommen MAVLink-basierte Funkmodule zum Einsatz. Für größere Reichweiten (BVLOS-Betrieb) kann alternativ eine Mobilfunkverbindung genutzt werden.

| Komponente | Link |
|---|---|
| **SiK Telemetry Radio** | [ardupilot.org/copter/docs/common-sik-telemetry-radio](https://ardupilot.org/copter/docs/common-sik-telemetry-radio.html) |

### Einbindung der entwickelten Software

```
Rechenmodul (Raspberry Pi)          Flight Controller (Cube Orange / Pixhawk)
┌─────────────────────────┐         ┌──────────────────────────────┐
│  run_path_find.py       │         │  ArduPilot / PX4             │
│  → Greedy + Dijkstra    │──MAVLink─▶  Wegpunktmission            │
│  → Routenausgabe (JSON) │  serial  │  Flugregelung / IMU          │
└─────────────────────────┘         └──────────────────────────────┘
```

Die entwickelte Software fügt sich über das MAVLink-Protokoll als Planungsebene in dieses System ein. Integration, Erprobung und Zertifizierung eines solchen Systems übersteigen den Rahmen dieser Arbeit.

---

## Lizenz

© 2025 Vincent Schilling, Technische Universität Berlin
