# Namnge verktyg i Centroid (för Fusion-sync)

När du synkar till Fusion läses **Description** i Centroid-verktygstabellen.
Skriv namnet enligt mallen nedan så fylls CAM-fält (typ, diameter, längder m.m.) automatiskt.

## Snabbmall

```text
TYP  diameter mm  antal skär  [längder]  [material]  [fritext]
```

**Exempel som räcker för de flesta fräsar:**

```text
EM 6mm 4f LCF20 LB40 OAL75 CARB
```

| Del | Betydelse | Obligatorisk? |
|-----|-----------|---------------|
| `EM` | Flat end mill | Rekommenderas |
| `6mm` | Diameter | Ja (eller sätt Diameter-kolumnen) |
| `4f` | Antal skär | Rekommenderas |
| `LCF20` | Skärlängd 20 mm | Rekommenderas för CAM |
| `LB40` | Stickout / body 40 mm | Rekommenderas för CAM |
| `OAL75` | Total längd 75 mm | Bra att ha |
| `CARB` | Karbid (annars `HSS`) | Valfritt |

## Typkoder

| Skriv | Blir i Fusion |
|-------|----------------|
| `EM` eller `end mill` | Flat end mill |
| `BL` eller `ball` | Ball end mill |
| `DR` eller `drill` | Drill |
| `CH` eller `chamfer` | Chamfer mill |
| `FM` eller `face` | Face mill |
| `PR` eller `probe` | Probe |

## Vanliga extras

| Token | Exempel | Vad det sätter |
|-------|---------|----------------|
| Hörnradius | `R3` | 3 mm radius (ball/bull) |
| Borrspets | `SIG118` | 118° |
| Chamfervinkel | `TA90` eller `90d` | 90° |
| Skaft | `SFDM10` | Shank 10 mm |
| Material | `CARB` / `carbide` / `HSS` | BMC i Fusion |

## Fler exempel

```text
EM 10mm 2f LCF25 LB45 OAL80 CARB rough
BL 6mm 2f R3 LCF12 OAL60 CARB
DR 5mm SIG118 LCF50 OAL80 HSS
CH 10mm 90d LCF5 TA90
EM 4mm 4f LCF15 LB30
```

Korta namn fungerar också, men ger **färre** Fusion-fält:

```text
6mm 2f end mill
```

→ typ, diameter och skär sätts; längder får defaults / lämnas orörda vid update.

## Vad du *inte* behöver i namnet

- **T-nummer, H, D, RPM, coolant** – finns redan som egna kolumner i Centroid och synkas separat.
- **Probad verktygslängd (Offset)** – styr maskinens Z, inte Fusion. Mät/prova som vanligt i CNC12.

## Tips i praktiken

1. Mät eller läs av skärlängd (`LCF`) och stickout (`LB`) från verktyget/hållaren.
2. Uppdatera Description i Centroid.
3. Kör **Centroid Sync** eller **Centroid Sync Net** i Fusion.
4. Finns token i namnet → Fusion uppdateras.  
   Saknas token → manuellt ifyllda längder i Fusion behålls.

Samma regler gäller för CSV-export (v1) och Bridge (v2).
