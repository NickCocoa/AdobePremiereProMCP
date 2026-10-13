# Kylling-previs (Blender)

Blokking-previs av de to kyllingene i et hvitt, Pixar-aktig studio.
De erter hverandre og kaster maling på hverandre.

![Kontaktark](contact_sheet.jpg)

Preview-video i lav oppløsning (640×360, Cycles 4 samples): [`kylling_previs_preview.mp4`](kylling_previs_preview.mp4)

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
- Rekvisitter: trekasse, en stor regnbuebalje midt på gulvet (én kile i hver farge), et gult og et rosa malingsspann.
- Malingen er i lyse, lekne farger: rosa, turkis, gul, lime, lilla, oransje og himmelblå. Hvert kast har sin egen farge, håndavtrykkene går i regnbuerekkefølge, og gutten blir dekket av flere farger når han dukkes i balja.

## Handling (24 fps, 984 frames ≈ 41 sek)

| Frames | Shot / kamera | Hva skjer |
|--------|---------------|-----------|
| 1–211 | SH010 `CAM_01_Wide` | Gutten (svart) løper inn fra venstre, gjør en piruett og finner malingsbalja. Han kaster maling rundt seg og maler på gulvet med hendene. Han rygger for å beundre verket sitt. |
| 212–295 | SH020 `CAM_02_Medium` | Søster (hvit) løper inn fra høyre og sparker ham (f230). Han flyr i salto og havner med hodet ned i balja (f246). Han spreller, spretter opp full av maling og rister seg som en hund. |
| 296–451 | SH030 `CAM_01_Wide` | Gutten kaster maling på henne (treff f326). Hun stamper, finner et spann ved trekassa og kaster, men bommer. Så kaster hun hele spannet etter ham og jager ham ut av bildet til venstre. |
| 452–661 | SH040 `CAM_03_Dyp` | Hun kommer først inn igjen fra høyre, og han løper etter. De løper dypt inn i rommet og frem igjen, sklir i malingsdammen og glir på ryggen. De ligger og ler, spretter opp, tar en felles piruett og dunker borti hverandre. |
| 662–984 | SH060 `CAM_04_Ende` | Søster erter ham og løper dypt inn i rommet og så rett mot kamera. Gutten øser maling fra balja og kaster. Hun dukker unna, og malingen treffer linsa (f742). Hun tørker av linsa (f768–778), puster lettet ut og smiler i kamera. Gutten kommer løpende inn og klemmer henne (f870), og begge smiler og ler inn i kamera mens kameraet zoomer sakte inn. Slutt. |

### Shotliste med nærbilder

| Frame | Kamera | Shot |
|-------|--------|------|
| 1 | `CAM_01_Wide` | SH010 Gutten leker og søler |
| 212 | `CAM_02_Medium` | SH020 Søster kommer |
| 222 | `CAM_CU_01_Gutt_OTS` | SH021 **CU** Gutten ser henne, over skulderen hennes |
| 228 | `CAM_02_Medium` | SH022 Spark, hodet ned i balja |
| 240 | `CAM_CU_02_Jente_Ler` | SH023 **CU** Søster ler av ham, med beina hans i forgrunnen |
| 272 | `CAM_02_Medium` | SH024 Han spretter opp |
| 288 | `CAM_CU_03_Gutt` | SH025 **CU** Gutten full av maling, rister seg |
| 306 | `CAM_01_Wide` | SH030 Han kaster tilbake |
| 323 | `CAM_CU_04_Jente_Treff` | SH031 **CU** Søster blir truffet og blir sint |
| 356 | `CAM_01_Wide` | SH032 Hun henter spann |
| 378 | `CAM_CU_03_Gutt` | SH033 **CU** Gutten: «uh-oh» |
| 390 | `CAM_01_Wide` | SH034 Jakt ut av bildet |
| 452 | `CAM_03_Dyp` | SH040 Jakt dypt i rommet, de sklir |
| 594 | `CAM_CU_05_Liggende` | SH041 **CU** ovenfra: de ligger hode mot hode og ler sammen |
| 618 | `CAM_03_Dyp` | SH042 Piruett og dunk |
| 660 | `CAM_CU_06_Erting_OTS` | SH043 **CU** Søster erter ham, over skulderen hans |
| 672 | `CAM_04_Ende` | SH060 Jakt mot kamera, maling på linsa, hun tørker og smiler, klem |
| 904 | `CAM_CU_07_Klem` | SH061 **CU** Klem, de fniser |
| 946 | `CAM_04_Ende` | SH062 Varmt smil i kamera, slutt |

Nærbildene er statiske kameraer (35–40 mm) som sikter mot hodehøyde. Over-skulder-bildene (OTS) har den andre figuren i forgrunnen, så relasjonen mellom dem er med i bildet.

Kamerabyttene ligger som markører på tidslinja, bundet til kameraene, så *Viewport Render Animation* og vanlig render klipper automatisk.

I tillegg ligger det markører som heter `Uttrykk …` (uten kamera). De angir hvilket ansiktsuttrykk figurene skal ha i den ferdige versjonen, for eksempel «ertende», «skrekkslagen», «lettet», «stort smil», «klem, latter» og «varmt smil i kamera». Hvert uttrykk har 1–3 sekunder å virke på.

## Justere

- **Timing:** `animate_boy()` og `animate_girl()` er lister med `P(frame, x, y, z, len_frem, retning, squash)`. Løping lages med `run(figur, start, slutt, [(x, y), ...])` langs en rute.
  - `len_frem > 0` lener forsiden frem, `< 0` lener bakover.
  - `retning`: 90 = ser mot høyre, −90 = mot venstre, 0 = mot kamera.
  - `squash < 1` gir squash, `> 1` gir stretch.
  - `raw=True` bruker vinkelen udempet (salto, ligge på ryggen). `spin=True` gir hele piruetter.
- **Maling:** `build_paint_fx()` styrer klatter, dammer, håndavtrykk, malingsdrakten og malingen på linsa.
- **Farger:** konstantene øverst (`RED`, `BLACK`, `WHITE`) og malingsfargene i `PAINTS`. Hvilken farge hvert kast, hver dam og hver flekk har, settes i `build_paint_fx()`.
- **Render:** EEVEE, 1920×1080 på 50 %, AgX, med stempel for shotnavn og kamera. For rask playblast bruker du *View → Viewport Render Animation*.

## Til AI-look

Render en shot med EEVEE eller viewport-render, og bruk de to referansebildene som stil-/karakter-referanse i AI-verktøyet.
Gutten er den svarte blokken og jenta den hvite. Den røde forsiden og blokkens retning viser hvor hodet og blikket skal peke.
