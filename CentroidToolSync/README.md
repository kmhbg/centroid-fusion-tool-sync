# Centroid Tool Sync – Fusion 360 Add-In

Synkar en Centroid Acorn-export (`tools.csv`) till ett valt **lokalt** Fusion Tool Library.

## Funktion

1. Öppna **Manufacture** i Fusion 360
2. Kör **Centroid Sync** (Scripts and Add-Ins-panelen)
3. Välj exporterad `tools.csv`
4. Välj målbibliotek i dropdown
5. Kontrollera preview (uppdateras / läggs till / hoppas över)
6. Tryck OK

### Sync-regler

| Regel | Beteende |
|-------|----------|
| Matchnyckel | Tool number (`T002` ↔ Fusion tool number 2) |
| Update (maskin) | Description, RPM, length/diameter offset, diameter |
| Update (CAM) | Explicita description-token skrivs; saknade/noll-fält gap-fylls |
| Behålls vid update | GUID, holder, icke-noll geometry/feeds utan token |
| Add | Saknade T-nummer skapas från mall + namnstandard |
| Radering | Aldrig – verktyg som bara finns i Fusion lämnas orörda |
| Tomma CSV-rader | Hoppas över |

### Description-namnstandard (CAM)

Se den enkla guiden: [`NAMNSTANDARD.md`](../NAMNSTANDARD.md).

Lägg tokens i Centroid **Description** så syncen fyller Fusion-geometri:

```text
<TYP> <DC>mm <F>f [R<re>] [SIG<deg>] [TA<deg>] [LCF<mm>] [LB<mm>] [OAL<mm>] [SFDM<mm>] [BMC] [fri text]
```

Exempel: `EM 6mm 4f LCF20 LB40 OAL75 CARB`

Samma standard som v2 (`CentroidToolSyncNet`). Korta namn som `6mm 2f end mill` fungerar fortfarande.

**Obs:** Centroid probad `Offset` mappas **inte** till Fusion `OAL`.

## Installation (macOS)

1. Hitta Fusion AddIns-mappen, vanligen:

```text
~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
```

2. Kopiera eller symlinka hela mappen `CentroidToolSync` dit:

```bash
ln -s "/Users/nille/Documents/Dev/toolImport/CentroidToolSync" \
  "$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/CentroidToolSync"
```

3. I Fusion: **Utilities → Scripts and Add-Ins → Add-Ins**
4. Markera **CentroidToolSync** och klicka **Run** (valfritt: Run on Startup)

## Installation (Windows)

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
```

Kopiera mappen `CentroidToolSync` dit och kör add-in som ovan.

## Manuell testchecklista

- [ ] Kommandot **Centroid Sync** syns i Manufacture
- [ ] Välj en Centroid `tools.csv` och ett lokalt Fusion Tool Library
- [ ] Preview visar rimliga updated/added-siffror
- [ ] Efter sync: befintliga T-nummer har uppdaterad description/RPM/offsets
- [ ] Holder/feeds på befintliga verktyg är oförändrade
- [ ] Nytt T-nummer i en CSV-kopia läggs till
- [ ] Tomma slots (T024+) skapar inga verktyg
- [ ] Andra synken skapar inga dubbletter

## Projektstruktur

```text
CentroidToolSync/
  CentroidToolSync.manifest
  CentroidToolSync.py
  commands/sync_command.py
  lib/centroid_parser.py
  lib/tool_templates.py
  lib/fusion_library.py
  lib/merge.py
  README.md
```

## Utveckling

Parser och mallar är rena Python-moduler och kan testas utan Fusion:

```bash
cd CentroidToolSync
python3 -m unittest tests.test_naming_standard -v
```

```bash
cd CentroidToolSync
python3 -c "
from lib.centroid_parser import parse_row
from lib.tool_templates import build_tool_json
t = parse_row({'Tool':'T002','H':'H002','D':'D004','Offset':'0','Diameter':'0','Coolant':'OFF','Spindle':'CW','Speed':'3500','Description':'EM 6mm 4f LCF20 LB40 OAL75 CARB'})
print(t)
print(build_tool_json(t)['geometry']['LCF'], build_tool_json(t)['BMC'])
"
```