# Centroid Tool Sync Net (v2)

Fusion-addon + Windows-bridge. Synkar Centroid-verktyg till ett **lokalt** Fusion Tool Library via:

1. **CSV-fil** (manuell export, samma idé som v1)
2. **Centroid Bridge** (live över LAN – fyll i IP till CNC-PC:n)

v1 [`CentroidToolSync`](../CentroidToolSync/) lämnas orörd. Denna addon har eget kommando: **Centroid Sync Net**.

## Arkitektur

```text
CNC-PC (Windows)                     Mac (Fusion)
CNC12 + CentroidAPI.dll
        ↓
CentroidBridge :8765  ----HTTP----→  CentroidToolSyncNet
                                     → Local Tool Library
tools.csv --------------filval----→  (CSV-läge)
```

## Installation – Fusion-addon (macOS)

```bash
ln -s "/Users/nille/Documents/Dev/toolImport/CentroidToolSyncNet" \
  "$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/CentroidToolSyncNet"
```

I Fusion: **Utilities → Scripts and Add-Ins → Add-Ins → CentroidToolSyncNet → Run**.

## Installation – Bridge (CNC-PC)

Se [`bridge/README.md`](bridge/README.md). Enklast:

```text
Dubbelklicka: CentroidToolSyncNet\bridge\install-bridge.bat
```

Det publicerar bryggan + systemfacks-app, sätter autostart vid inloggning och startar tray (ikon i aktivitetsfältet).

## Användning i Fusion

1. Kör **Centroid Sync Net**
2. Välj källa:
   - **CSV-fil** → Välj CSV…
   - **Centroid Bridge** → ange IP + port (8765) → **Anslut / Hämta**
3. Välj målbibliotek
4. Kontrollera preview
5. OK (update + add, ingen radering)

## Sync-regler

| Regel | Beteende |
|-------|----------|
| Match | Tool number |
| Update | description, RPM, offsets, diameter |
| Behålls | GUID, holder, feeds, övrig geometry |
| Add | saknade T-nummer |
| Delete | aldrig |

## Projektstruktur

```text
CentroidToolSyncNet/
  CentroidToolSyncNet.py / .manifest
  commands/sync_command.py
  lib/… (parser, merge, bridge_client, …)
  bridge/  (C# .NET 8 HTTP-tjänst)
  README.md
```

## Test utan Fusion

```bash
cd CentroidToolSyncNet
python3 -c "
from lib.bridge_client import fetch_tools
from lib.centroid_parser import from_bridge_payload
# kräver att bridge körs, annars testa payload-mappning:
from lib.centroid_parser import from_bridge_dict
t = from_bridge_dict({'tool_number':2,'h_number':2,'d_number':4,'offset':0,'diameter':4,'coolant':'OFF','spindle':'CW','speed':3500,'description':'4mm 2f end mill'})
print(t)
"
```

## Manuell checklista

- [ ] v1 och v2 syns som separata add-ins
- [ ] CSV-läge synkar som v1
- [ ] Bridge mock: `/health` och `/tools` fungerar
- [ ] Addon hämtar via IP och mergar
- [ ] Live Centroid på CNC-PC med CNC12 igång
