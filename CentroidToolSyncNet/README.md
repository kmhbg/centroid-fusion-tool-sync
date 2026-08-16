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
| Update (maskin) | description, RPM, H/D-offset, diameter |
| Update (CAM) | explicita description-token skrivs; saknade/noll-fält gap-fylls |
| Behålls | GUID, holder, icke-noll geometry/feeds utan token |
| Add | saknade T-nummer (tokens + typ/diameter-defaults) |
| Delete | aldrig |

## Description-namnstandard (CAM)

Se den enkla guiden: [`NAMNSTANDARD.md`](../NAMNSTANDARD.md).

Centroid har ingen full CAM-geometri. Lägg tokens i **Description** så syncen fyller Fusion:

```text
<TYP> <DC>mm <F>f [R<re>] [SIG<deg>] [TA<deg>] [LCF<mm>] [LB<mm>] [OAL<mm>] [SFDM<mm>] [BMC] [fri text]
```

| Token | Betydelse |
|-------|-----------|
| `EM` / `BL` / `DR` / `CH` / `FM` / `PR` | Typ (eller `end mill`, `ball`, `drill`, …) |
| `6mm` | Diameter |
| `4f` | Antal skär |
| `LCF20` | Flute length (mm) |
| `LB40` | Body / stickout (mm) |
| `OAL75` | Overall length (mm) |
| `SFDM10` | Shank diameter |
| `SIG118` | Borrspetsvinkel |
| `R3` / `TA90` | Hörnradius / chamfer-vinkel |
| `CARB` / `carbide` / `HSS` | BMC |

Exempel:

```text
EM 6mm 4f LCF20 LB40 OAL75 CARB
DR 5mm SIG118 LCF50 OAL80 HSS
BL 6mm 2f R3 LCF12 OAL60
```

Korta namn som `6mm 2f end mill` fungerar fortfarande (typ/diameter/flutes). Utan `LCF`/`LB`/`OAL` rör syncen inte redan satta längder i Fusion.

**Obs:** Centroid probad `Offset` styr maskinens Z — den mappas **inte** till Fusion `OAL`.

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
python3 -m unittest tests.test_naming_standard -v
```

Snippet:

```bash
cd CentroidToolSyncNet
python3 -c "
from lib.centroid_parser import from_bridge_dict
from lib.tool_templates import build_tool_json, patch_tool_json
t = from_bridge_dict({'tool_number':2,'h_number':2,'d_number':4,'offset':0,'diameter':4,'coolant':'OFF','spindle':'CW','speed':3500,'description':'EM 6mm 4f LCF20 LB40 OAL75 CARB'})
print(t)
print(build_tool_json(t)['geometry']['LCF'], build_tool_json(t)['BMC'])
"
```

## Manuell checklista

- [ ] v1 och v2 syns som separata add-ins
- [ ] CSV-läge synkar som v1
- [ ] Bridge mock: `/health` och `/tools` fungerar
- [ ] Addon hämtar via IP och mergar
- [ ] Live Centroid på CNC-PC med CNC12 igång
