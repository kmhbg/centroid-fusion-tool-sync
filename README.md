# Centroid ↔ Fusion Tool Sync

<p align="center">
  <strong>Synka verktygsbibliotek från Centroid CNC till Autodesk Fusion 360</strong><br>
  <em>CSV-import eller live över nätverket via en Windows-bridge</em>
</p>

<p align="center">
  <a href="https://github.com/kmhbg/centroid-fusion-tool-sync"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-kmhbg%2Fcentroid--fusion--tool--sync-181717?logo=github"></a>
  <img alt="Fusion 360" src="https://img.shields.io/badge/Fusion%20360-Add--In-orange">
  <img alt="Centroid" src="https://img.shields.io/badge/Centroid-Acorn%20%2F%20CNC12-0e7490">
  <img alt="License" src="https://img.shields.io/badge/license-Use%20freely-lightgrey">
</p>

---

## Vad det löser

På Centroid Acorn (CNC12) har du ett verktygsbord med T-nummer, offsets, RPM och beskrivningar.  
I Fusion 360 vill du ha samma verktyg i ditt **lokala Tool Library** – utan att knappa in allt manuellt.

Det här projektet ger två vägar:

| | **v1 – CSV** | **v2 – Net** |
|---|---|---|
| Mapp | [`CentroidToolSync/`](CentroidToolSync/) | [`CentroidToolSyncNet/`](CentroidToolSyncNet/) |
| Källa | Exporterad `tools.csv` från Centroid | CSV **eller** live via bridge (IP) |
| Körs i | Fusion Add-In | Fusion Add-In + Windows-bridge på CNC-PC |
| Extra | — | Systemfacksikon, autostart, mock-läge |

Båda versionerna **mergar** på tool number: uppdatera befintliga, lägg till nya, **radera aldrig** verktyg som bara finns i Fusion.

---

## Välj rätt version

```text
Har du bara en CSV-export ibland?
  → v1 CentroidToolSync

Vill du hämta verktyg live från maskinen på samma LAN?
  → v2 CentroidToolSyncNet (+ bridge)
```

---

## Installation – v1 (CSV)

1. Symlinka eller kopiera `CentroidToolSync` till Fusion AddIns-mappen  
   (macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`)
2. I Fusion: **Scripts and Add-Ins → CentroidToolSync → Run**
3. Kör **Centroid Sync**, välj `tools.csv` och ett lokalt bibliotek

Full guide: [`CentroidToolSync/README.md`](CentroidToolSync/README.md)

---

## Installation – v2 (CSV + Bridge)

### På CNC-PC:n (Windows)

```text
CentroidToolSyncNet\bridge\install-bridge.bat
```

Det publicerar bryggan, sätter brandvägg (port **8765**), skapar autostart och startar en **systemfacksikon**.

Högerklick på ikonen:

| Meny | Funktion |
|------|----------|
| Status | Visar `/health` |
| Öppna /health | Webbläsare |
| Mock-läge | På/av utan att editera filer |
| Avsluta | Stoppar bridge + tray |

### På Fusion-datorn

1. Installera addonen `CentroidToolSyncNet`
2. Kör **Centroid Sync Net**
3. Välj **CSV-fil** eller **Centroid Bridge** (ange maskinens IP)

Full guide: [`CentroidToolSyncNet/README.md`](CentroidToolSyncNet/README.md) · Bridge: [`CentroidToolSyncNet/bridge/README.md`](CentroidToolSyncNet/bridge/README.md)

---

## Arkitektur (v2)

```text
┌─────────────────────────────┐         LAN          ┌──────────────────────────┐
│  CNC-PC (Windows)           │ ───────────────────► │  Mac / PC med Fusion     │
│  CNC12 + CentroidAPI.dll    │   GET /tools :8765   │  Centroid Sync Net       │
│  CentroidBridge + Tray      │                      │  → Local Tool Library    │
└─────────────────────────────┘                      └──────────────────────────┘
```

> CentroidAPI är en lokal DLL, inte ett nätverks-API. Därför behövs bryggan på CNC-PC:n.

---

## Sync-regler (båda versionerna)

- **Matchnyckel:** tool number (`T002` ↔ Fusion tool number `2`)
- **Update:** description, RPM, length/diameter offset, diameter  
- **Behålls:** GUID, holder, feeds, övrig geometry  
- **Add:** saknade T-nummer  
- **Delete:** aldrig  
- Tomma rader (blank description) hoppas över  

---

## Krav

- Autodesk Fusion 360 (Manufacture)
- Centroid CNC12 (Acorn m.fl.)
- **v2 bridge:** Windows + [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) på CNC-PC:n

---

## Bidra / feedback

Issues och PR:ar är välkomna. Projektet är byggt för verkstadens egen workflow – håll det enkelt.

## Licens

Använd fritt för egen CNC-/CAM-workflow.  
**Centroid**, **CNC12** och **Fusion 360** tillhör respektive tillverkare.
