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

## Handling (24 fps, 1078 frames ≈ 45 sek)

| Frames | Shot / kamera | Hva skjer |
|--------|---------------|-----------|
| 1–157 | SH010 `CAM_01_Wide` | Gutten (svart) løper inn fra venstre, gjør en piruett og finner malingsbalja. Han kaster maling rundt seg to ganger og maler litt på gulvet med hendene. Han rygger for å beundre verket sitt. |
| 158–241 | SH020 `CAM_02_Medium` | Søster (hvit) løper inn fra høyre og sparker ham (f176). Han flyr i salto og havner med hodet ned i balja (f192). Han spreller, spretter opp full av maling og rister seg som en hund. |
| 242–397 | SH030 `CAM_01_Wide` | Gutten kaster maling på henne (treff f272). Hun stamper, finner et spann ved trekassa og kaster, men bommer. Så kaster hun hele spannet etter ham og jager ham ut av bildet til venstre. |
| 398–607 | SH040 `CAM_03_Dyp` | Hun kommer først inn igjen fra høyre, og han løper etter. De løper dypt inn i rommet og frem igjen, sklir i malingsdammen og glir på ryggen. De ligger og ler, spretter opp, tar en felles piruett og dunker borti hverandre. |
| 608–1078 | SH060 `CAM_04_Ende` | Søster erter ham og løper dypt inn i rommet og så rett mot kamera. Gutten øser maling fra balja og kaster. Hun dukker unna, og malingen treffer linsa (f688). Hun tørker av linsa (f714–724), puster lettet ut og smiler i kamera. Gutten kommer løpende inn og klemmer henne (f784), og begge smiler og ler inn i kamera mens kameraet zoomer sakte inn. Så blir det mørkt rundt dem (f904–922), og et spotlys ovenfra lyser dem opp. Kameraet trekker seg rolig bakover og litt opp mens de vinker farvel. Til slutt får søster en idé, hopper opp og klemmer broren (f1010). Han tar imot henne, vakler litt, og de står og klemmer og ler i spotlyset. Slutt. |

### Ting som veltes

Sju ting står plassert langs løpeveiene og veltes når figurene løper forbi. Malingsboksene søler maling på gulvet når de velter.

| Frame | Hvem | Hva |
|-------|------|-----|
| 31 | Gutten løper inn | Gul malingsboks velter og søler |
| 157 | Søster løper inn | Krakk velter |
| 341 | Gutten flykter | Kjegle velter |
| 351 | Gutten flykter | Eskestabel flyr |
| 458 | Søster dypt i rommet | Tårn av malingsbokser (rosa, blå, lime) raser og søler |
| 635 | Gutten jager henne | Lime malingsboks velter og søler |
| 655 | Søster løper mot kamera | Krakk velter |

Avslutningen med mørke, spotlys, kameraet som trekker seg bak, vinkingen og hoppeklemmen lages i `build_finale()`.

Tingene lages i `build_knockables()`. `knock_over()` velter én ting, og `scatter()` sender en stabel flyvende.

### Shotliste med nærbilder

| Frame | Kamera | Shot |
|-------|--------|------|
| 1 | `CAM_01_Wide` | SH010 Gutten leker og søler |
| 158 | `CAM_02_Medium` | SH020 Søster kommer |
| 168 | `CAM_CU_01_Gutt_OTS` | SH021 **CU** Gutten ser henne, over skulderen hennes |
| 174 | `CAM_02_Medium` | SH022 Spark, hodet ned i balja |
| 186 | `CAM_CU_02_Jente_Ler` | SH023 **CU** Søster ler av ham, med beina hans i forgrunnen |
| 218 | `CAM_02_Medium` | SH024 Han spretter opp |
| 234 | `CAM_CU_03_Gutt` | SH025 **CU** Gutten full av maling, rister seg |
| 252 | `CAM_01_Wide` | SH030 Han kaster tilbake |
| 269 | `CAM_CU_04_Jente_Treff` | SH031 **CU** Søster blir truffet og blir sint |
| 302 | `CAM_01_Wide` | SH032 Hun henter spann |
| 324 | `CAM_CU_03_Gutt` | SH033 **CU** Gutten: «uh-oh» |
| 336 | `CAM_01_Wide` | SH034 Jakt ut av bildet |
| 398 | `CAM_03_Dyp` | SH040 Jakt dypt i rommet |
| 446 | `CAM_CU_08_Loep` | SH040b **CU** Søster raser forbi kameraet og river ned tårnet, han like etter |
| 482 | `CAM_03_Dyp` | SH040c Jakt frem, de sklir |
| 540 | `CAM_CU_05_Liggende` | SH041 **CU** ovenfra: de ligger hode mot hode og ler sammen |
| 564 | `CAM_03_Dyp` | SH042 Piruett og dunk |
| 606 | `CAM_CU_06_Erting_OTS` | SH043 **CU** Søster erter ham, over skulderen hans |
| 618 | `CAM_04_Ende` | SH060 Jakt mot kamera, maling på linsa, hun tørker og smiler, klem |
| 818 | `CAM_CU_07_Klem` | SH061 **CU** Klem, de fniser |
| 860 | `CAM_04_Ende` | SH062 Varmt smil i kamera. Det blir mørkt, et spotlys ovenfra lyser dem opp, kameraet trekker seg bak og de vinker. Søster hopper opp og klemmer broren. Slutt |

Over-skulder-bildene (OTS) har den andre figuren i forgrunnen, så relasjonen mellom dem er med i bildet.

### Pixar-kamera og look

Dette gjør `build_cinematic()`:
- **Følger hodene:** alle kameraer unntatt sluttkameraet har *Track To* mot et fokuspunkt i hodehøyde, `Fokus_Gutt`, `Fokus_Jente` eller `Fokus_Midt` mellom dem. Bildet panorerer mykt etter figurene og følger hodet også i salto og når de ligger.
- **Wide panorerer etter handlingen:** først etter gutten, og etter begge når søster kommer inn. Det står i øyehøyde (1,7 m) i stedet for ovenfra.
- **Sakte innkjøringer:** hvert skudd skyver sakte innover, 0,15–1,2 m i løpet av skuddet.
- **Dybdeskarphet:** nærbilder på f/2.0 og løpe-nærbildet på f/2.8. Medium, dyp og sluttkameraet bruker f/4, og wide f/5.6. Fokus følger alltid hodene.
- **Bevegelsesuskarphet:** slått på for alle skudd.
- **Fargelook:** AgX med *Punchy*, for fyldigere og mer mettede farger.
- **Lys:** varmere key, kjøligere fill og sterkere varmt rimlys, så figurene skiller seg fra bakgrunnen.

Kamerabyttene ligger som markører på tidslinja, bundet til kameraene, så *Viewport Render Animation* og vanlig render klipper automatisk.

I tillegg ligger det markører som heter `Uttrykk …` (uten kamera). De angir hvilket ansiktsuttrykk figurene skal ha i den ferdige versjonen, for eksempel «ertende», «skrekkslagen», «lettet», «stort smil», «klem, latter» og «varmt smil i kamera». Hvert uttrykk har 1–3 sekunder å virke på.

## Justere

- **Timing:** `animate_boy()` og `animate_girl()` er lister med `P(frame, x, y, z, len_frem, retning, squash)`. Løping lages med `run(figur, start, slutt, [(x, y), ...])` langs en rute.
  - `len_frem > 0` lener forsiden frem, `< 0` lener bakover.
  - `retning`: 90 = ser mot høyre, −90 = mot venstre, 0 = mot kamera.
  - `squash < 1` gir squash, `> 1` gir stretch.
  - `raw=True` bruker vinkelen udempet (salto, ligge på ryggen). `spin=True` gir hele piruetter.
- **Tempo:** `CUTS` i skriptet er en liste over tidsbiter som klippes ut. Alt etter et klipp flyttes frem automatisk, så du kan stramme eller løsne tempoet uten å flytte hver keyframe for hånd. Frame-tallene i animasjonskoden er de opprinnelige tallene, før klippene.
- **Maling:** `build_paint_fx()` styrer klatter, dammer, håndavtrykk, malingsdrakten og malingen på linsa.
- **Farger:** konstantene øverst (`RED`, `BLACK`, `WHITE`) og malingsfargene i `PAINTS`. Hvilken farge hvert kast, hver dam og hver flekk har, settes i `build_paint_fx()`.
- **Render:** EEVEE, 1920×1080 på 50 %, AgX, med stempel for shotnavn og kamera. For rask playblast bruker du *View → Viewport Render Animation*.

## Til AI-look

Render en shot med EEVEE eller viewport-render, og bruk de to referansebildene som stil-/karakter-referanse i AI-verktøyet.
Gutten er den svarte blokken og jenta den hvite. Den røde forsiden og blokkens retning viser hvor hodet og blikket skal peke.
