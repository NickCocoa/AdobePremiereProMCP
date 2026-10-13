# Kylling-previs (Blender)

Blokking-previs av de to kyllingene i et hvitt, Pixar-aktig studio.
De erter hverandre og kaster maling på hverandre.

![Kontaktark](contact_sheet.jpg)

## Kjør

**I Blender (4.2+ / 5.x):** Scripting-fanen → *Open* → `kylling_previs.py` → *Run Script*.

**Fra terminal:**

```bash
blender -b -P kylling_previs.py -- --save kylling_previs.blend
```

`kylling_previs.blend` er ferdig bygget med Blender 5.2. Bruker du en eldre versjon, kjør heller skriptet.

Skriptet tømmer scenen og bygger alt på nytt hver gang det kjøres, så du kan endre tall og kjøre det igjen.

## Karakterene

| Blokk | Karakter | Kropp | Forside |
|------|----------|-------|---------|
| `Gutt` | Gul kylling i oransje snekkerbukse | svart | rød |
| `Jente` | Gul kylling i korall kjole med sløyfe | hvit | rød |

- Høy blokk på 0,7 × 0,5 × 1,7 m (bredde × dybde × høyde), så den leses som en person. Origo er i bunnen, så squash/stretch skjer fra gulvet. Mål endres i `CHAR_W`, `CHAR_D` og `CHAR_H` øverst i skriptet.
- Forsiden (lokal −Y) er rød, så du alltid ser hvilken vei de ser.
- Navneskilt over hodet vises bare i viewport, ikke i render.

## Studio

- Hvit cyclorama (gulvet bøyer seg opp i bakveggen), ingen synlig horisont.
- Tre-punkts område-lys: varm key, kjølig fill, rim bakfra.
- Rekvisitter fra referansene: trekasse, to malingsspann og brun maling som søles på gulvet.

## Handling (24 fps, 288 frames ≈ 12 sek)

| Frames | Shot / kamera | Hva skjer |
|--------|---------------|-----------|
| 1–73 | SH010 `CAM_01_Wide` | Begge hopper inn nese mot nese. Gutten vrikker «nænænæ», lader opp og dytter jenta bakover. Han skryte-hopper. |
| 74–107 | SH020 `CAM_02_Jente_OTS` | Gutten vrikker med rumpa mot kamera. Jenta henter spannet sitt, lader opp og kaster. |
| 108–177 | SH030 `CAM_03_Gutt_OTS` | **Treff** på gutten (f116). Jenta jubler og slipper spannet. Gutten stamper sint, henter sitt spann og kaster (f180). |
| 178–199 | SH040 `CAM_02_Jente_OTS` | **Treff** på jenta (f190). Gutten ler og slipper spannet. |
| 200–257 | SH050 `CAM_01_Wide` | Malingskrig: begge øser maling fra gulvet og kaster samtidig. Klattene krysser hverandre og begge blir truffet (f228). De ler seg skakke. |
| 258–288 | SH060 `CAM_04_Hero` | Begge hopper sammen og ender i sluttposen mot kamera, med malingsflekker på de røde forsidene. |

Kamerabyttene ligger som markører på tidslinja, bundet til kameraene, så *Viewport Render Animation* og vanlig render klipper automatisk.

## Justere

- **Timing:** `animate_boy()` og `animate_girl()` er lister med `P(frame, x, y, z, len_frem, retning, squash)`.
  - `len_frem > 0` lener forsiden frem, `< 0` lener bakover.
  - `retning`: 90 = ser mot høyre, −90 = mot venstre, 0 = mot kamera.
  - `squash < 1` gir squash, `> 1` gir stretch.
- **Malingskast:** `build_paint_fx()`. Her settes start, mål, frames og bue for hver klatt, og når flekkene dukker opp.
- **Farger:** konstantene øverst (`RED`, `BLACK`, `WHITE`, `PAINT` …).
- **Render:** EEVEE, 1920×1080 på 50 %, AgX, med stempel for shotnavn og kamera. For rask playblast bruker du *View → Viewport Render Animation*.

## Til AI-look

Render en shot med EEVEE eller viewport-render, og bruk de to referansebildene som stil-/karakter-referanse i AI-verktøyet.
Gutten er den svarte kuben og jenta den hvite. Den røde forsiden og kubens retning viser hvor hodet og blikket skal peke.
