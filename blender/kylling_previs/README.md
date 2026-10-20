# Kylling-previs (Blender)

Previs av de to kyllingene i et Pixar-aktig malerverksted for barn.
De erter hverandre og kaster maling på hverandre.

![Kontaktark](contact_sheet.jpg)

Preview-video i lav oppløsning med temp-musikk (640×360, Cycles 4 samples): [`kylling_previs_preview.mp4`](kylling_previs_preview.mp4)

## Kjør

**I Blender (4.2+ / 5.x):** Scripting-fanen → *Open* → `kylling_previs.py` → *Run Script*.

**Fra terminal:**

```bash
blender -b -P kylling_previs.py -- --save kylling_previs.blend
```

`kylling_previs.blend` er ferdig bygget med Blender 5.2. Bruker du en eldre versjon, kjør heller skriptet.

Skriptet tømmer scenen og bygger alt på nytt hver gang det kjøres, så du kan endre tall og kjøre det igjen.

## Karakterene

| Figur | Karakter | Kropp | Forside |
|------|----------|-------|---------|
| `Gutt` | Gul kylling i oransje snekkerbukse | svart, med hårtust | rød |
| `Jente` | Gul kylling i korall kjole med sløyfe | hvit, med rosa sløyfe | rød |

- **Kyllingform med barnslige proporsjoner:** eggformet kropp og stort hode, 1,7 m høy, med origo nederst, så squash/stretch skjer fra gulvet. Formene settes av `BODY` og `HEAD` øverst i skriptet. I tillegg har de nebb, føtter og vinger med tre fjærtupper som «hender». Silhuetten og posene er dermed nær det AI-looken skal bli.
- **Rød forside:** ansiktet og magen er røde, så du alltid ser hvilken vei de ser. Overgangen er myk og styres av materialet (`front_mask_material()`). Malingsdrakten gutten får i balja dekker hode, rygg og skuldre, men aldri forsiden.
- **Øyne fra første bilde:** store øyne med pupill og lysrefleks. Pupillene følger et blikkmål (`Blikk_Gutt`, `Blikk_Jente`). De ser rett frem som standard, på den andre i relasjonsøyeblikkene og inn i kamera når de smiler til oss. Begge blunker med ujevne mellomrom. Dette styres i `build_acting()`.
- **Vinger:** begge har vinger gjennom hele sekvensen. De svinger når de løper, og brukes til å øse, kaste, peke, holde spannet, dukke, tørke linsa og klemme. Vingene henger to bilder etter kroppen (follow-through, `wing_drag()`).
- **Personlighet i bevegelsen:** broren løper tungt og klumsete med lave sprett og mye squash. Søsteren er lett og sprettende med høye sprett og store vingesving. Dette settes i `GAIT`.
- **Smil:** smilet under nebbet kommer når de smiler i kamera.
- **Navneskilt:** skiltet over hodet vises bare i viewport, ikke i render.

## Verkstedet

- Hvit cyclorama (gulvet bøyer seg opp i bakveggen), ingen synlig horisont.
- **Barnas malerverksted** (`build_set_dressing()`):
  - to staffelier med barnemalerier
  - presenning med malingsflekker
  - en stige
  - et bord med vannglass og pensler
  - malingstuber på trekassa

  Alt står utenfor løpeveiene og gir dybde og skala bak handlingen.
- **Planter og møbler** (`build_furniture()`), i samme rene og enkle stil som Pixars lampeintro: avrundede grunnformer, matte materialer, få varme farger (lyst tre, krem, terrakotta, grønt, sennep og dempet turkis) og god luft rundt hver ting.
  - **Planter:** sju planter i terrakottapotter (høye bladplanter, runde busker og fiolinfiken), langs kantene, i bakgrunnen og på bordet.
  - **Møbler:** en lav trebenk med pute, en sittesekk og en lav bokhylle med bøker.
  - **Lamper:** en gulvlampe og en bordlampe med varmt lys. De gir en praktisk lyskilde som også lyser i festen.

  Noen planter ligger i forgrunnen i følgeskuddet og løpe-nærbildet og gir dybde.
- Rekvisitter: trekasse, en stor regnbuebalje midt på gulvet (én kile i hver farge), et gult og et rosa malingsspann.
- Rommet blir gradvis mer malt. Det kommer flekker rundt hvert søl (kast, balja, risting, treff, tårnet, skliingen), og fargede fotavtrykk etter dem når de løper. Gutten drypper turkis og lilla etter dukkingen, og søster tråkker rosa. Dette lages i `build_paint_marks()`.
- **Malingen bygger seg opp på figurene og blir værende:**
  - søster får lilla på magen når hun treffes
  - søster får gult på ryggen når hun sklir i dammen
  - drakten hans smitter over på siden hennes i klemmen og hoppeklemmen
  - han får rosa i fjeset når han går pladask i en dam
  - drakten hans er våt maling i store, flytende fargeflekker

  Slik blir de renere i starten og stadig mer fargerike mot slutten.
- Malingen er i lyse, lekne farger: rosa, turkis, gul, lime, lilla, oransje og himmelblå.

## Lys og fargemanus

Tre-punkts område-lys (varm key, kjølig fill og kraftig rimlys bakfra som skiller figurene fra den hvite bakgrunnen). `color_script()` endrer fargen på lyset og verden etter historien:

| Del | Stemning |
|-----|----------|
| Åpning | varmt morgenlys |
| Søster kommer og malingskampen | kjøligere, mer kontrast |
| Jakten | lyst og nøytralt |
| Linsa og klemmen | gyllent |
| Leken | varmt og lekent |
| Festen | dempet lilla, strobelys i fire farger og dis (`Fest_Dis`) som gir synlige lysstråler |
| Slutten | lyst og varmt når de griper kameraet |

## Handling (24 fps, 1600 frames ≈ 67 sek)

| Frames | Del | Hva skjer |
|--------|-----|-----------|
| 1–215 | Åpning | Et følgeskudd bakfra følger gutten (svart) mens han løper inn og titter ned i balja. Over skulderen hans ser vi ned i regnbuemalingen. Han kaster maling rundt seg (total), et innklipp viser håndavtrykkene, og han står og beundrer verket sitt. |
| 216–369 | Søster kommer | Han ser søster komme. Hun sparker ham, og han havner med hodet først i balja. Hun ler godt av ham, og han spretter opp full av maling, rister seg og blir stående og stirre på henne. |
| 370–595 | Malingskamp | Han kaster på henne. Hun får sjokk og blir sint, ser spannet («aha!»), kaster og bommer. Han fryser («uh-oh»), og hun jager ham. Begge løper helt ut av bildet, kameraet panorerer raskt til høyre, og de kommer inn igjen. |
| 596–821 | Jakten dypt i rommet | De løper dypt inn i rommet. Hun river ned tårnet. Begge sklir i den gule dammen og ligger og ler hode mot hode, så kommer en piruett og et dunk. Til slutt erter hun ham. |
| 822–1177 | Linsa og klemmen | Hun løper mot kamera og dukker, og malingen hans treffer linsa. Gutten sier «oi!» og fniser. Hun tørker linsa, puster lettet ut og smiler. Han løper inn i bildet fra høyre og klemmer henne, de fniser sammen og gir et varmt smil i kamera. |
| 1178–1313 | Leken | Hun får en idé og hopper opp på broren (f1186). Han rister henne av seg, og hun flyr av og ler. Han lader opp og hopper på henne (f1258), men hun dukker unna, og han går pladask med nesa i gulvet (f1266). Hun ler så hun rister (sett fra gulvet). |
| 1314–1397 | Fest | Hun begynner å danse. Lyset i rommet dempes, og strobelys i fire farger starter. Han ruller over på ryggen og ligger og nikker i takt, med ansiktet mot oss (nærbilde), og så slenger han seg opp og danser også (f1374). |
| 1398–1600 | Slutten | Én og én danser de mot kamera med hvert sitt lave nærbilde: først gutten med robotdans, så søster som snurrer. Til slutt kommer begge helt frem og griper kameraet sammen (f1506). Strobelysene slukker, rommet blir lyst og varmt igjen, og de smiler rett inn i linsa. **Knappen:** han slipper kameraet og etterlater et turkis fjæravtrykk på linsa (f1522). De ser det, ser på hverandre og bryter ut i latter. Slutt. |

**Plant og payoff.** Kameraet etableres tidlig, så malingen på linsa og fjæravtrykket på slutten føles fortjent:
- Gutten kikker kort inn i kamera mens han beundrer verket sitt (f≈218).
- Søster erter mot kamera før hun dukker.
- Malingen på linsa midtveis kommer tilbake som fjæravtrykket i siste bilde.

**Pusterom og reaksjoner.** 16 pauser på 0,4–1,1 sekunder gir tid til reaksjonene og relasjonen mellom dem. Figurene puster mens de står:
1. Han ser ned i regnbuemalingen.
2. Han beundrer verket sitt.
3. Han ser søster komme.
4. Hun ler av ham i balja.
5. Han står dryppende og stirrer på henne.
6. Hun får sjokk når hun blir truffet.
7. Hun får øye på spannet.
8. «Uh-oh», han fryser.
9. De ligger og puster ut etter latteren.
10. Hun erter ham.
11. Han sier «oi!» og fniser.
12. Hun puster lettet ut etter linsa.
13. De fniser i klemmen.
14. Hun henger på ham, og han ser lurt opp.
15. Pladask: stille et øyeblikk.
16. Han ligger og får en idé før han slenger seg opp.

### Ting som veltes

Sju ting står plassert langs løpeveiene og veltes når figurene løper forbi. Malingsboksene søler maling på gulvet når de velter.

| Frame | Hvem | Hva |
|-------|------|-----|
| 31 | Gutten løper inn | Gul malingsboks velter og søler |
| 215 | Søster løper inn | Krakk velter |
| 507 | Gutten flykter | Kjegle velter |
| 517 | Gutten flykter | Eskestabel flyr |
| 624 | Søster dypt i rommet | Tårn av malingsbokser (rosa, blå, lime) raser og søler |
| 839 | Gutten jager henne | Lime malingsboks velter og søler |
| 859 | Søster løper mot kamera | Krakk velter |

Slutten med leken, festen med strobelys, solodansene og grepet om kameraet lages i `build_ending()`. Lyset styres av `light_level()`: det dempes når festen starter, og rommet blir lyst igjen når de griper kameraet.

Tingene lages i `build_knockables()`. `knock_over()` velter én ting, og `scatter()` sender en stabel flyvende.

### Shotliste

| Frame | Kamera | Shot |
|-------|--------|------|
| 1 | `CAM_00_Tracking` | SH010 Følger gutten bakfra til balja |
| 86 | `CAM_CU_15_Ned_I_Balja_OTS` | SH011b Over skulderen hans, ned i regnbuemalingen |
| 124 | `CAM_01_Wide` | SH012 Kaster maling rundt seg |
| 166 | `CAM_CU_10_Handavtrykk` | SH013 Innklipp: håndavtrykk på gulvet |
| 182 | `CAM_01_Wide` | SH014 Beundrer verket sitt |
| 226 | `CAM_CU_01_Gutt_OTS` | SH021 CU Gutten ser henne (OTS) |
| 248 | `CAM_02_Medium` | SH022 Spark, hodet ned i balja |
| 258 | `CAM_CU_11_Plask` | SH0225 CU Plask, hodet først i balja |
| 272 | `CAM_CU_02_Jente_Ler` | SH023 CU Søster ler av ham |
| 310 | `CAM_02_Medium` | SH024 Han spretter opp |
| 326 | `CAM_CU_03_Gutt` | SH025 CU Gutten full av maling |
| 370 | `CAM_01_Wide` | SH030 Han kaster tilbake |
| 387 | `CAM_CU_04_Jente_Treff` | SH031 CU Søster blir truffet, sint |
| 432 | `CAM_CU_12_Aha` | SH0315 CU Søster ser spannet: aha! |
| 460 | `CAM_01_Wide` | SH032 Hun henter spann |
| 474 | `CAM_CU_03_Gutt` | SH033 CU Gutten: uh-oh |
| 502 | `CAM_01_Wide` | SH034 Jakt ut av bildet |
| 596 | `CAM_03_Dyp` | SH040 Jakt dypt i rommet |
| 612 | `CAM_CU_08_Loep` | SH040b CU Søster raser forbi og river ned tårnet, han etter |
| 634 | `CAM_03_Dyp` | SH040c Jakt frem, de sklir |
| 706 | `CAM_CU_05_Liggende` | SH041 CU Ligger og ler sammen |
| 752 | `CAM_03_Dyp` | SH042 Piruett og dunk |
| 794 | `CAM_CU_06_Erting_OTS` | SH043 CU Søster erter ham (OTS) |
| 822 | `CAM_04_Ende` | SH060 Jakt mot kamera, maling på linsa |
| 902 | `CAM_CU_13_Oi` | SH0605 CU Gutten: oi! fniser |
| 932 | `CAM_04_Ende` | SH0607 Søster tørker linsa og smiler |
| 1072 | `CAM_CU_07_Klem` | SH061 CU Klem, fniser til hverandre |
| 1134 | `CAM_04_Ende` | SH062 Varmt smil i kamera |
| 1176 | `CAM_CU_14_Hoppeklem` | SH063 CU Hoppeklem, han rister henne av seg |
| 1248 | `CAM_18_Pladask` | SH064 Han hopper på henne, hun dukker, pladask |
| 1284 | `CAM_CU_19_Fra_Gulvet` | SH065 Hun ler av ham (fra gulvet ved hodet hans) |
| 1314 | `CAM_20_Fest` | SH066 Hun begynner å danse, lyset dempes, strobelys |
| 1332 | `CAM_CU_21_Nikker` | SH067 CU Han ligger på ryggen og nikker i takt |
| 1362 | `CAM_20_Fest` | SH068 Han slenger seg opp og danser |
| 1398 | `CAM_16_Dans_Gutt` | SH070 Guttens robotdans mot kamera (lav vinkel) |
| 1446 | `CAM_17_Dans_Jente` | SH071 Søster snurrer frem mot kamera (lav vinkel) |
| 1494 | `CAM_15_Dans` | SH072 De kommer helt frem og griper kameraet, rommet blir lyst |

Ingen skudd er lenger enn ca. 6 sekunder, bortsett fra det siste der de holder kameraet.

Over-skulder-bildene (OTS) har den andre figuren i forgrunnen, så relasjonen mellom dem er med i bildet.

### Pixar-kamera og look

Dette gjør `build_cinematic()`:
- **Følger hodene:** alle kameraer unntatt sluttkameraet har *Track To* mot et fokuspunkt i hodehøyde, `Fokus_Gutt`, `Fokus_Jente` eller `Fokus_Midt` mellom dem. Bildet panorerer mykt etter figurene og følger hodet også i salto og når de ligger.
- **Følgeskudd i åpningen:** `CAM_00_Tracking` henger etter gutten bakfra (Copy Location med offset) og sikter på hodet hans.
- **Wide panorerer etter handlingen:** først etter gutten, og etter begge når søster kommer inn. Det brukes der handlingen trenger oversikt.
- **Barnas øyehøyde:** wide, medium og nærbildene står i figurenes øyehøyde (ca. 1,4 m), og fokuspunktene sitter i øynene (`EYE_Z`).
- **Lengre linser på de emosjonelle nærbildene:** 45–55 mm i stedet for 34–42 mm (latter, treff, aha, oi, erting og klem). Kameraet er trukket bakover så utsnittet er likt, men bakgrunnen blir mykere og bildet mer intimt. Vidvinkel brukes til komikk og action.
- **Færre, lengre skudd:** de to korteste skuddene (0,4 s) er slått sammen med naboskuddene. Følgeskuddet går helt til balja, og søster kommer inn i wide.
- **Skjermretning:** jakten holder retningen (ut til venstre, inn igjen fra høyre etter piskepanoreringen).
- **Sakte innkjøringer:** hvert skudd skyver sakte innover, 0,15–1,2 m i løpet av skuddet.
- **Dybdeskarphet:** nærbilder på f/2.0 og løpe-nærbildet på f/2.8. Medium, dyp og sluttkameraet bruker f/4, og wide f/5.6. Fokus følger alltid hodene.
- **Bevegelsesuskarphet:** slått på for alle skudd.
- **Fargelook:** AgX med *Punchy*, for fyldigere og mer mettede farger.
- **Lys:** se *Lys og fargemanus* over.

Kamerabyttene ligger som markører på tidslinja, bundet til kameraene, så *Viewport Render Animation* og vanlig render klipper automatisk.

I tillegg ligger det markører som heter `Uttrykk …` (uten kamera). De angir hvilket ansiktsuttrykk figurene skal ha i den ferdige versjonen, for eksempel «ertende», «skrekkslagen», «lettet», «stort smil», «klem, latter» og «varmt smil i kamera». Hvert uttrykk har 1–3 sekunder å virke på.

## Musikk og takt (temp)

Skriptet lager et syntetisk temp-spor, `temp_musikk.wav` (120 BPM), og legger det i Video Sequencer på kanal 1. Det er bare en plassholder for rytmen og skal byttes ut med ekte musikk.
- **Gjennom historien:** lette plukk på hvert slag, og korte lydstikk på treffene: sparket, plask, treff, tårnet, skliing, linsa, klemmen, hoppet, pladask og knappen.
- **I festen:** fullt beat med kick, skarptromme, hihat og bass. Strobelysene blinker i sekstendedeler. Festen starter på et slag (f1314), og hvert danseskudd og grepet om kameraet ligger på hele slag (12 bilder per slag).
- **Når de griper kameraet:** et stort, varmt akkordløft, og en liten latterfrase på knappen.
- **Bytte musikk:** legg ekte musikk i 120 BPM med første slag i festen på f1314, så treffer klipp og lys fortsatt. `BEAT` og `make_temp_music()` styrer dette.

## Justere

- **Timing:** `animate_boy()` og `animate_girl()` er lister med `P(frame, x, y, z, len_frem, retning, squash)`. Løping lages med `run(figur, start, slutt, [(x, y), ...])` langs en rute.
  - `len_frem > 0` lener forsiden frem, `< 0` lener bakover.
  - `retning`: 90 = ser mot høyre, −90 = mot venstre, 0 = mot kamera.
  - `squash < 1` gir squash, `> 1` gir stretch.
  - `raw=True` bruker vinkelen udempet (salto, ligge på ryggen). `spin=True` gir hele piruetter.
- **Vinger:** `animate_boy_arms()` og `animate_girl_arms()` er lister med `(frame, venstre, høyre)`, der hver vinge får en navngitt pose fra `ARM_POSES` (for eksempel `heng`, `jubel`, `kast`-posene `bak`/`fram_opp`, `dukk`, `klem`) eller egne vinkler `(rx, ry, rz)`. Vingesvingen under løping legges inn automatisk av `run()`.
- **Blikk og blunk:** vinduene i `build_acting()` sier når hver av dem ser på den andre (`other`) eller i kamera (`cam`).
- **Lys:** stemningene og når de skifter står i `color_script()`.
- **Tempo:** `CUTS` i skriptet er en liste over tidsbiter som klippes ut. Alt etter et klipp flyttes frem automatisk, så du kan stramme eller løsne tempoet uten å flytte hver keyframe for hånd. Frame-tallene i animasjonskoden er de opprinnelige tallene, før klippene.
- **Pusterom:** `HOLDS` i skriptet er en liste over pauser `(frame, lengde)` som legges inn etter klippene. Alt står stille og figurene puster litt, mens sprut som er i lufta får fly ferdig. `END_HOLD` lar siste bilde stå litt før slutt.
- **Maling:** `build_paint_fx()` styrer klatter, dammer, håndavtrykk, malingsdrakten og malingen på linsa.
- **Farger:** konstantene øverst (`RED`, `BLACK`, `WHITE`) og malingsfargene i `PAINTS`. Hvilken farge hvert kast, hver dam og hver flekk har, settes i `build_paint_fx()`.
- **Render:** EEVEE, 1920×1080 på 50 %, AgX, med stempel for shotnavn og kamera. For rask playblast bruker du *View → Viewport Render Animation*.

## Til AI-look

Render en shot med EEVEE eller viewport-render, og bruk de to referansebildene som stil-/karakter-referanse i AI-verktøyet.
Gutten er den svarte kyllingen og jenta den hvite. Den røde forsiden og pupillene viser hvor hodet og blikket skal peke.
