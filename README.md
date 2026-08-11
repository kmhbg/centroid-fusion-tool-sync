# Centroid ↔ Fusion Tool Sync

Synca verktygsbibliotek från **Centroid CNC (Acorn/CNC12)** till **Autodesk Fusion 360**.

## Versioner

| Mapp | Beskrivning |
|------|-------------|
| [`CentroidToolSync/`](CentroidToolSync/) | **v1** – Fusion-addon: importera Centroid `tools.csv` och merga till lokalt Tool Library |
| [`CentroidToolSyncNet/`](CentroidToolSyncNet/) | **v2** – Samma merge + **Windows-bridge** (HTTP) så Fusion kan hämta verktyg live via IP, med systemfacksikon och autostart |

## Exempelfiler

- `tools.csv` – Centroid Acorn-export
- `Library 260122.*` – exempel på Fusion Tool Library-export (referensformat)

## Snabbstart

### v1 (CSV)
Se [`CentroidToolSync/README.md`](CentroidToolSync/README.md).

### v2 (CSV eller Bridge)
1. På CNC-PC:n: `CentroidToolSyncNet/bridge/install-bridge.bat`
2. I Fusion: installera addonen `CentroidToolSyncNet` och kör **Centroid Sync Net**
3. Välj CSV eller Bridge (IP till maskinen)

Detaljer: [`CentroidToolSyncNet/README.md`](CentroidToolSyncNet/README.md) och [`CentroidToolSyncNet/bridge/README.md`](CentroidToolSyncNet/bridge/README.md).

## Licens

Använd fritt för egen CNC-/CAM-workflow. CentroidAPI och Fusion tillhör respektive tillverkare.
