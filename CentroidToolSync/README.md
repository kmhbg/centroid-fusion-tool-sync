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
| Update | Description, RPM, length/diameter offset, diameter |
| Behålls vid update | GUID, holder, feeds, övrig geometry |
| Add | Saknade T-nummer skapas från mall |
| Radering | Aldrig – verktyg som bara finns i Fusion lämnas orörda |
| Tomma CSV-rader | Hoppas över |

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
- [ ] Välj [tools.csv](../tools.csv) och ett lokalt bibliotek baserat på `Library 260122`
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
python3 -c "
from lib.centroid_parser import parse_centroid_csv, count_empty_rows
from lib.tool_templates import build_tool_json
tools = parse_centroid_csv('../tools.csv')
print(len(tools), 'tools,', count_empty_rows('../tools.csv'), 'empty')
print(tools[0])
print(build_tool_json(tools[1])['type'], build_tool_json(tools[1])['post-process'])
"
```
