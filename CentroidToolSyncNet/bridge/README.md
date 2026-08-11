# Centroid Bridge (Windows)

HTTP-brygga mellan Centroid CNC12 (`CentroidAPI.dll`) och Fusion-addonen **Centroid Tool Sync Net**.

Inkluderar **systemfacksikon** (tray) och **autostart vid inloggning** (schemalagd uppgift). Klassisk Windows-tjänst i Session 0 undviks medvetet – CentroidAPI/CNC12 kräver användarsession.

## Installera med script (rekommenderas)

På CNC-PC:n, i mappen `bridge`:

1. Dubbelklicka **`install-bridge.bat`**  
   eller i PowerShell:

```powershell
cd CentroidToolSyncNet\bridge
powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1
```

Scriptet (standard):

- Kontrollerar **.NET 8 SDK**
- Söker `CentroidAPI.dll` i `C:\cncm`, `C:\cnct`, `C:\cncr`, `C:\cncp`
- Uppdaterar `appsettings.json`
- Publicerar **CentroidBridge.exe** + **CentroidBridge.Tray.exe** till `publish\`
- Skapar brandväggsregel TCP **8765**
- Registrerar schemalagd uppgift **CentroidBridge** (AtLogOn)
- Startar tray direkt (ikon i systemfältet)

Hoppa över autostart:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1 -NoAutostart
```

### Systemfält (tray)

Högerklicka ikonen:

| Meny | Funktion |
|------|----------|
| **Status** | Visar `/health` (ok, source, toolCount, ForceMock) |
| **Öppna /health** | Öppnar webbläsare |
| **Mock-läge** | På/av – skriver `ForceMock` i `appsettings.json` och startar om bridge |
| **Avsluta** | Stoppar bridge + tray |

Efter omstart loggar du in → tray startar automatiskt via Task Scheduler.

Avinstallera autostart:

```powershell
Unregister-ScheduledTask -TaskName CentroidBridge -Confirm:$false
```

Manuell start:

```text
publish\start-bridge.bat
```

Test:

```powershell
curl http://127.0.0.1:8765/health
```

Om brandväggsregeln misslyckades, kör som administratör:

```powershell
netsh advfirewall firewall add rule name="CentroidBridge 8765" dir=in action=allow protocol=TCP localport=8765
```

## Endpoints

| Method | Path | Beskrivning |
|--------|------|-------------|
| GET | `/health` | `{ ok, source, toolCount, message }` |
| GET | `/tools` | `{ tools: [...], skipped_empty }` |

Port: **8765** (bind `0.0.0.0`). Ingen autentisering (endast LAN).

## Krav

- Windows-PC där CNC12 körs (Acorn-maskinen)
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) (för `install-bridge` / publish)
- `CentroidAPI.dll` (vanligen `C:\cncm\CentroidAPI.dll`) för live-läge
- CNC12 igång för live-läge

## Konfiguration

[`appsettings.json`](appsettings.json):

```json
{
  "Port": 8765,
  "CentroidApiDllPath": "C:\\cncm\\CentroidAPI.dll",
  "MockToolsPath": "mock-tools.json",
  "ForceMock": false
}
```

Sätt `ForceMock: true` för att alltid använda [`mock-tools.json`](mock-tools.json). Installationsscriptet sätter detta automatiskt om DLL saknas. Enklast: växla **Mock-läge** via systemfacksmenyn (ingen manuell fileditering behövs).

## Manuell bygg

```powershell
cd CentroidToolSyncNet\bridge
dotnet publish CentroidBridge.csproj -c Release -r win-x64 -o publish
dotnet publish tray\CentroidBridge.Tray.csproj -c Release -r win-x64 -o publish
.\publish\CentroidBridge.Tray.exe
```

## Test från Fusion-datorn

```bash
curl http://192.168.x.x:8765/health
```

## Beteende

1. Om `CentroidAPI.dll` finns och `ForceMock=false` → försök live via reflection
2. Om live misslyckas (CNC12 nere, API-fel) → fallback till mock
3. Tomma descriptions filtreras bort
4. Tray startar/övervakar `CentroidBridge.exe` och visar status i systemfältet
