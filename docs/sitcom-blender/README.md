# Vaktskiftet — varemottaket i Blender

Byggeskript for location-en. Kjør `build_set.py`, så får du hele settet: skall, reoler, port, arbeidsbord, oppslagsvegg med plakaten, gulvmerking, lysrigg, proxy-figurer og de fire kameraene i beat 1.

Verifisert mot **Blender 5.2 LTS** (bpy 5.2.2), skrevet defensivt for 4.x.

---

## Kjør det

I Blender, fanen Scripting → åpne `build_set.py` → Run.

Headless:

```bash
blender --background --python build_set.py -- --save varemottaket.blend
blender --background --python build_set.py -- --still CAM_1_3_POSTER /tmp/test.png
```

Skriptet tømmer scenen først. Det er idempotent — kjør det igjen så er du tilbake til utgangspunktet.

---

## Rommet

14 × 10 × 6 meter. Z opp, origo midt på gulvet. +X øst, +Y nord.

```
   N  +Y
        ┌──────────────────────────┐
        │                    ░░░░░ │   ░  pallereoler, østveggen
   W −X │ ▓                  ░░░░░ │ +X E
        │ ▓  oppslagsvegg     ░░░░ │
        │ ▭  arbeidsbord           │
        └──────────▓▓▓─────────────┘
   S  −Y        rulleport, halvåpen
```

**Geografien er dramaturgi.** Han kommer inn gjennom porten i sør og skal til bordet på vestveggen. Oppslagsveggen ligger på veien. Det er derfor han stopper — ikke fordi manuset sier det, men fordi rommet gjør det uunngåelig.

Alle mål ligger som konstanter øverst i skriptet. Endre `ROOM_X`, så følger reoler, port, merking og vegger etter.

---

## Beat 1, de fire kameraene

| Kamera | Linse | Frames | Innhold |
|---|---|---|---|
| `CAM_1_1_EMPTY` | 28 mm | 1–125 | Tomt rom. Port, gård og lysrørene over. Holdes for lenge |
| `CAM_1_2_ENTER` | 35 mm | 126–250 | Han krysser fra porten og stopper. Kamera finner ham et slag for sent |
| `CAM_1_3_POSTER` | 65 mm | 251–375 | Over skulderen, klar av hodet. Han retter på arket |
| `CAM_1_4_PHONE` | 40 mm | 376–500 | Fra siden. Han fotograferer, sletter, går. Ingen reaksjonsbilde |

Markører på tidslinja er bundet til kameraene, så du kan skrubbe gjennom hele beaten. **Render hvert klipp som eget område** — restyle tåler ikke kutt inne i et klipp.

Hvert kamera har `shot_note`, `frame_start` og `frame_end` som custom properties.

Alle har litt rull lagt inn, så bildet ikke står i vater. Det er dokumentarspråket, ikke slurv.

---

## Plakaten

`PROP_POSTER_BLANK` er **blank**. Ingen tekst.

Teksten komponeres på i etterarbeid, med `PROP_POSTER_TRACK` som referanse og objektindeks **10** for matte. Tre grunner:

- Modeller setter tekst upålitelig, og restyle ødelegger den
- Du får en perfekt track gratis — noe generering aldri gir deg
- Slagordet kan byttes per kunde uten én ny render

Samme prinsipp gjelder all skilting. Det som varierer per kunde, holdes utenfor rendret piksel.

**Objektindekser:** plakat `10`, vest `11`, port `12`.

---

## Lyset

To familier som krangler. Det er rommets karakter, og restyle bevarer luminansforhold i stedet for å finne opp lys — så verdistrukturen må være riktig her, ikke senere.

- **Seks lysrør** i taket, 5,7 m. Svakt grønnlige. **Ett av dem er trøtt** — halv styrke og grønnere
- **Pre-dawn** utenfor porten. Kaldt blått, lavt. Det eneste dagslyset
- **Natrium** i gården. Den eneste varme tingen i bildet
- **Verden er nesten svart.** Ambient fill flater ut rommet og stjeler jobben de to familiene skal slåss om

Hvis porten klipper i høylysene: dra `EXT_PREDAWN` ned. Ikke bytt view transform — den står bevisst på `Standard` for å gi restylen et nøytralt, uklassifisert bilde inn.

---

## Render

| | |
|---|---|
| Motor | EEVEE. Dette er et kontrollpass, ikke et beauty-pass |
| Oppløsning | 1920 × 1080 |
| Framerate | 25 fps, låst |
| Kliplengde | 125 frames = 5 sekunder |
| View transform | `Standard`, look `None` |
| Pass | Z, object index, cryptomatte object, mist |

Vertikale utsnitt rendres som **egne kameraer**, aldri beskjæres.

---

## Proxy-figurer

`PROXY_TOMERIK` er en blokkeringsproxy i riktig høyde (1,82 m), ikke en figur. Vesten ligger på egen objektindeks så hi-vis kan holdes stabil gjennom restylen.

`PATH_TOMERIK_00` til `05` er gangveien hans fra porten til oppslagsveggen. Bruk dem som nøkler når du animerer.

Legg til flere med `proxy(navn, lokasjon, retning_grader, M, coll, height)`.

---

## Rekkefølgen herfra

1. Ekte stemmeopptak, klippet til dialogspor
2. Animer mot ferdig lyd — aldri motsatt
3. Render beat 1, fire klipp
4. **Se på det uten restyle.** Holder kaldåpningen på timing alene?
5. Først da: restyle-pass

Punkt 4 er hele poenget med å bygge dette. Et restyle-pass gjør ikke en død scene morsom, og det er billigere å finne ut her enn etter seks figurark.

---

## Detaljnivå

Settet er bygget som arbeidsgreybox: riktige mål, riktige posisjoner, riktige lysverdier, enkle volumer.

Detaljarbeid lønner seg i **geometri, props og lys** — det restylen leser og bevarer. Det lønner seg minst i **teksturfinish**, som restylen overskriver. Bygg videre i den rekkefølgen.

Naturlige neste steg i settet: ekte reolstiger og avsperring, kabelbro i taket, sprinkelrør, søppeldunk ved porten, slitasje i gulvmerkingen, en pall med skjev film.
