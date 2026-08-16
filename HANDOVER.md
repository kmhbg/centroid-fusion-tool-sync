# Handover: Centroid ↔ Fusion Tool Sync

Dokument för att starta en ny chat/agent utan att tappa kontext.

**Senast uppdaterad:** 2026-08-16  
**Lokal workspace:** `/Users/nille/Documents/Dev/toolImport`  
**GitHub (public):** https://github.com/kmhbg/centroid-fusion-tool-sync  
**Ägare GitHub:** `kmhbg`  
**Branch:** `main`

---

## TL;DR

Projektet synkar verktygsbibliotek från **Centroid CNC (Acorn/CNC12)** till **Autodesk Fusion 360** Tool Library.

| Version | Mapp | Vad den gör |
|---------|------|-------------|
| **v1** | `CentroidToolSync/` | Fusion Python add-in: välj Centroid `tools.csv` → merge till lokalt bibliotek |
| **v2** | `CentroidToolSyncNet/` | Samma merge + val **CSV eller Bridge (IP)**; Windows-bridge + tray + autostart |

**v1 ska inte ersättas** – v2 lever i egen mapp.

---

## Användarens mål och låsta beslut

- Matchnyckel: **tool number** (`T002` ↔ Fusion `post-process.number`)
- Sync: **update matching + add missing**
- **Aldrig auto-radera** Fusion-verktyg som saknas i källan
- Endast **lokala** Fusion Tool Libraries (inte Hub)
- Vid update: synka maskinfält (description, RPM, H/D-offset, diameter); behåll GUID/holder
- CAM-geometry: **description-namnstandard** (LCF/LB/OAL/…) + gap-fill av saknade/noll-fält; explicita token skrivs alltid
- Centroid probad `Offset` mappas **inte** till Fusion `OAL` (olika betydelse)
- UI på **svenska**
- Centroid API är **inte nätverksbaserat** (lokal .NET-DLL) → bridge krävs på CNC-PC
- Klassisk Windows Service (Session 0) **undviks** – CNC12/CentroidAPI kräver användarsession → **tray + Task Scheduler AtLogOn**

---

## Arkitektur (v2)

```text
CNC-PC (Windows)                         Mac/PC (Fusion)
CNC12 + CentroidAPI.dll
        ↓
CentroidBridge.exe :8765  ----HTTP----→  CentroidToolSyncNet add-in
CentroidBridge.Tray.exe (systemfält)     → Local Tool Library
  - Status / Mock-läge / Avsluta
  - Autostart via Task Scheduler "CentroidBridge"
```

### Bridge API

| Endpoint | Svar |
|----------|------|
| `GET /health` | `{ ok, source: "centroid"|"mock", toolCount, message }` |
| `GET /tools` | `{ tools: [...], skipped_empty }` |

Port default **8765**, bind `0.0.0.0`, ingen auth (LAN only).

JSON-fält per verktyg: `tool_number`, `h_number`, `d_number`, `offset`, `diameter`, `coolant`, `spindle`, `speed`, `description`.

### Mock-läge

- `ForceMock: true` i `appsettings.json` → läser `mock-tools.json` (ingen CNC12)
- Toggle från tray-menyn **Mock-läge** (skriver fil + startar om bridge)
- Live misslyckas → fallback till mock

---

## Viktiga filer

### v1 – `CentroidToolSync/`

- `CentroidToolSync.py` + `.manifest` – entrypoint
- `commands/sync_command.py` – dialog CSV + bibliotek + preview
- `lib/centroid_parser.py` – CSV-parse + description-namnstandard
- `lib/tool_templates.py` – JSON + `enrich_tool_json` (gap-fill)
- `lib/fusion_library.py` – lista/ladda/spara lokala libs
- `lib/merge.py` – update + add
- `tests/test_naming_standard.py` – parser + gap-fill-tester

### v2 – `CentroidToolSyncNet/`

- `commands/sync_command.py` – källa CSV **eller** Bridge (IP/port)
- `lib/bridge_client.py` – `urllib` → `/health` + `/tools`
- `lib/*` – merge-stack (+ `from_bridge_dict`, namnstandard-parser, `enrich_tool_json`)
- `tests/test_naming_standard.py` – parser + gap-fill-tester
- `bridge/` – .NET 8 Minimal API
  - `Program.cs`, `CentroidToolSource.cs` (reflection mot CentroidAPI.dll), `MockToolSource.cs`
  - `install-bridge.ps1` / `.bat` – install, publish, brandvägg, autostart, starta tray
  - `tray/` – WinForms NotifyIcon (`CentroidBridge.Tray`)
- `bridge/mock-tools.json` – testdata (behålls; personliga exempelfiler borttagna från repo-roten)

### Description-namnstandard (v2)

Se [`NAMNSTANDARD.md`](NAMNSTANDARD.md) (gäller v1 + v2).

```text
EM 6mm 4f LCF20 LB40 OAL75 CARB
DR 5mm SIG118 LCF50 OAL80 HSS
BL 6mm 2f R3 LCF12 OAL60
```

Se `CentroidToolSyncNet/README.md` för full tokenlista. P0/P1 för säker CAM: T/H/D, DC, typ, flutes, LCF/LB (+ tip SIG/RE/TA). Holder är P3 (manuellt).

### Specs (lokalt, ej i public repo – `.cursor/` är gitignored)

- `.cursor/specs/fusion/centroid_tool_sync_addon.md`
- `.cursor/specs/fusion/centroid_tool_sync_net.md`
- `.cursor/SPECS.md`

---

## Installation (för användaren)

### Fusion add-ins (macOS)

```bash
ln -s "/Users/nille/Documents/Dev/toolImport/CentroidToolSync" \
  "$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/CentroidToolSync"

ln -s "/Users/nille/Documents/Dev/toolImport/CentroidToolSyncNet" \
  "$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/CentroidToolSyncNet"
```

### Bridge (CNC Windows)

```text
Dubbelklicka CentroidToolSyncNet\bridge\install-bridge.bat
```

Kräver .NET 8 SDK. DLL söks i `C:\cncm|cnct|cncr|cncp\CentroidAPI.dll`.

---

## Git-status (vid handover)

- Remote: `origin` → `https://github.com/kmhbg/centroid-fusion-tool-sync.git`
- Senaste commits inkluderar: initial release, polish README + borttagna sample files (`tools.csv`, `Library 260122.*`)
- **Inte** i repo: `.cursor/`, `*.zip`, `publish/`, `bin/`, `obj/`

---

## Vad som är klart / inte klart

### Klart (kod)

- [x] v1 Fusion add-in (CSV merge)
- [x] v2 Fusion add-in (CSV + Bridge)
- [x] Windows bridge + mock + CentroidAPI via reflection
- [x] Tray med Status, /health, Mock-läge, Avsluta
- [x] Install-script med autostart (Scheduled Task)
- [x] Publikt GitHub-repo + förbättrad README
- [x] Description-namnstandard + gap-fill enrich (v1 + v2)

### Manuellt / ej verifierat i denna miljö

- [ ] Fusion add-in körning på användarens Mac
- [ ] Live `GetToolLibrary` mot riktig CNC12 (reflection kan behöva finjusteras beroende på DLL-version/Info-fält)
- [ ] `dotnet` fanns inte på utvecklings-Mac – bridge byggs på Windows CNC-PC
- [ ] Hub-bibliotek, auto-delete, bidirektionell sync – medvetet out of scope

---

## Vanliga fortsättningsuppgifter

1. Felsöka/finjustera `CentroidToolSource` mot riktig `CentroidAPI.dll` på maskinen
2. Uppdatera Centroid Description-fält enligt namnstandard (LCF/LB/OAL) på riktiga verktyg
3. Windows Service (avråds) vs tray – behåll tray om live ska fungera
4. Auth på bridge, eller Hub library-stöd
5. Packaging / installer (MSI) för bridge+tray
6. Holder-auto (out of scope tills vidare)

---

## Konventioner för ny agent

- Svara på **svenska** (användarpreferens)
- **Committa bara när användaren ber** om det; push bara när det efterfrågas eller följer explicit “lägg upp på GitHub”
- Ändra inte plan-filer under `.cursor/plans/` om användaren förbjuder det
- Rör inte v1 när du jobbar på v2 (såvida inte användaren vill)
- Spec-first finns i workspace rules under `.cursor` / globala Cursor-regler – skapa/uppdatera specs vid nya features om reglerna gäller

---

## Snabbstart för ny chat

Klistra in ungefär:

> Fortsätt på projektet `centroid-fusion-tool-sync` i `/Users/nille/Documents/Dev/toolImport`.  
> Läs `HANDOVER.md`. v1 = `CentroidToolSync`, v2 = `CentroidToolSyncNet` + bridge/tray.  
> GitHub: https://github.com/kmhbg/centroid-fusion-tool-sync  

Sedan beskriv önskad uppgift.
