# HELIOS — Action Intro / Shotliste v1

**Lengde:** ~92 sek · **Format:** 2.39:1, 24 fps · **Sluttleveranse:** Premiere

Kolonnen **Bygg** sier hvor shotet faktisk lages. Kolonnen **Tunge greier** er det
som koster tid — les den før du planlegger uker.

---

## AKT 1 — HAVET (0:00–0:18)

### S01 · 0:00–0:05 (5s) · Åpning
Kamera lavt, like over bølgetopp. Grålys, kald sjø. 3–4 langskip skjærer inn i
frame fra venstre på vei mot land. I horisonten ligger tåken som en vegg.

- **Kamera:** lang lens (85–135mm), lav høyde, svak roll med bølgen
- **Bygg:** Unreal (havet) — evt. AI-generert som du var inne på
- **Tunge greier:** havet. Se `docs/water.md` — dette er den ene tingen som kan spise uker

### S02 · 0:05–0:10 (5s) · Buene opp
Ombord. Mannskapet reiser buene. 3–4 raske klipp: hender som trekker streng,
pilespiss i fokus, vått lær, pust i kaldlufta.

- **Kamera:** hoftehøyde, håndholdt, 35mm
- **Bygg:** enklest som live action / AI. Nærbilder av hender er dyrt i 3D og
  billig å filme
- **Tunge greier:** ingen, hvis du ikke gjør det i 3D

### S03 · 0:10–0:14 (4s) · "FIRE!"
Lederen, vendt mot tåken. Roper. Kamera pusher inn på ham.

- **Kamera:** slow push-in, 50mm
- **Bygg:** samme som S02
- **Merk:** dette er siste ansikt vi ser før tåken. La det få lov å puste

### S04 · 0:14–0:18 (4s) · Salven går
Vidt, fra siden. Fra alle 3–4 båtene går pilregnet opp samtidig. Silhuetter mot
grå himmel.

- **Kamera:** statisk vidt, 24mm
- **Bygg:** Unreal — Niagara mesh-emitter, ~300–500 piler
- **Tunge greier:** pilene skal ha lett spredning og ulik avgangstid (2–3 frames
  jitter per båt), ellers ser det ut som en powerpoint-animasjon

---

## AKT 2 — GJENNOM TÅKEN (0:18–0:34)

### S05 · 0:18–0:26 (8s) · Pil-POV inn i tåken
Kamera låser seg på pilsvermen og følger den. Vi går inn i tåkeveggen. Lyset dør,
lyden dempes til bare fjærsus og vind.

- **Kamera:** kamera festet til én "hero"-pil, resten av svermen rundt
- **Bygg:** Unreal
- **Tunge greier:** volumetrisk tåke i dybden. Default Volumetric Fog Distance i
  UE er 6000 cm — altfor kort her. Se `docs/fog.md`
- **Lyd:** dette er shotet der du kutter mixen ned til nesten ingenting, så S08
  treffer hardt

### S06 · 0:26–0:34 (8s) · REVEAL — fjellveggen
Tåken tynnes. Den svarte islandske fjellveggen tårner opp foran oss. Høyt oppe i
veggen: en grotteinngang. Mørk, foreløpig.

- **Kamera:** fortsatt pil-POV, tilt oppover når veggen kommer
- **Bygg:** Unreal, Nanite. Basaltsøyler — Quixel/Fab har islandske cliff-scans
- **Tunge greier:** skalaen. Veggen må føles 300–400 m høy. Bruk tåkelag i dybden
  som skala-referanse, ikke bare størrelse
- **Merk:** dette er filmens første "oh shit". Ikke skynd deg gjennom det

---

## AKT 3 — MANNEN (0:34–0:50)

### S07 · 0:34–0:39 (5s) · Skikkelsen på kanten
Fortsatt pil-POV. Langt der fremme på fjellkanten: en liten menneskeskikkelse som
går mot kanten. Nesten for liten til å se.

- **Kamera:** pil-POV, lang lens-følelse
- **Bygg:** Unreal
- **Merk:** hold ham liten. Publikum skal måtte lete etter ham

### S08 · 0:39–0:43 (4s) · "DRACARYS!"
Ropet. Grotteinngangen lyser opp innenfra — glohet oransje som pulserer.

- **Bygg:** Unreal — emissive materiale + point light med light function inne i
  grotta, koblet mot volumetrisk tåke så lyset "blør" ut i lufta
- **Tunge greier:** lyset må treffe tåken, ikke bare geometrien. Det er hele
  effekten

### S09 · 0:43–0:47 (4s) · Skriket
Monstrøst drageskrik. Bass. Fugler letter fra veggen. Løs stein raser nedover.

- **Bygg:** Unreal — fugler og stein som Niagara
- **Lyd:** dette shotet er 80% lyd. Bygg bildet rundt lyden, ikke omvendt

### S10 · 0:47–0:50 (3s) · Pilene kommer ned
Nå fra mannen. Kamera ser oppover: pilregnet på vei ned mot ham.

- **Kamera:** low angle bak/ved ham, oppover
- **Bygg:** Unreal
- **Merk:** første gang vi bytter side. Vi har vært på pilene i 30 sek — nå er vi
  på den de skal treffe

---

## AKT 4 — ILDEN (0:50–1:02)

### S11 · 0:50–0:53 (3s) · BAAM
Ild spruter opp langs hele fjellkanten som en vegg.

- **Bygg:** Unreal — Niagara. Se `docs/fire.md` for valg mellom Niagara Fluids og
  billboard-basert ild
- **Tunge greier:** ild i denne skalaen. Fluids ser best ut og koster mest

### S12 · 0:53–0:58 (5s) · Pilene blir til støv
Slow-mo. Pilene treffer ildveggen, brenner bort, blir til aske som driver rolig i
lufta foran ansiktet hans.

- **Kamera:** slow-mo (render på 96–120 fps, retime i Premiere)
- **Bygg:** Unreal — dissolve/erosion-materiale på pilene, drevet av en scalar
  parameter; Niagara-aske spawner på pil-death
- **Tunge greier:** dette er signature-shotet i intron. Sett av mest tid her
- **Merk:** asken skal falle *rolig*. Kontrasten mot volden er hele poenget

### S13 · 0:58–1:02 (4s) · Løpet
Han løper. Fortere og fortere mot kanten.

- **Kamera:** håndholdt, lavt, bak ham. Øk kamerarystelse gradvis
- **Bygg:** Unreal
- **Merk:** klipp raskere og raskere frem mot S15

---

## AKT 5 — HOPPET (1:02–1:20)

### S14 · 1:02–1:06 (4s) · "Māzīs, Helios!"
Han roper på høyvalyrisk.

- **Replikk:** `Māzīs, Helios!` — "Kom, Helios!" (`māzigon` = å komme,
  imperativ `māzīs`). Se `docs/valyrian.md`
- **Bygg:** Unreal

### S15 · 1:06–1:10 (4s) · Hoppet
Han hopper over kanten. Kamera blir stående. Tomt frame — bare kanten, tåken,
himmelen. Kamera kryper sakte fremover mot kanten.

- **Kamera:** langsom dolly fremover. Ikke følg ham ned
- **Bygg:** Unreal

### S16 · 1:10–1:13 (3s) · Stille
Ingenting. Tre sekunder tomt frame.

- **Lyd:** total stillhet. Ikke vind engang
- **Merk:** dette er det modigste kuttet i hele intron. Ikke forkort det i
  redigering fordi det "føles langt" — det skal føles langt

### S17 · 1:13–1:20 (7s) · VOFF
Vingeslag. Dragen bryter opp i frame nedenfra med ham på ryggen, setter kurs mot
tåken.

- **Kamera:** statisk, la dragen fylle framet
- **Bygg:** Unreal — Fab-dragen. Flyanimasjon: se `docs/dragon.md`
- **Tunge greier:** vingeanimasjonen. Ett godt vingeslag-loop + Control Rig for
  bane er nok her

---

## AKT 6 — UT (1:20–1:32)

### S18 · 1:20–1:27 (7s) · Skyggen i tåken
Kamera zoomer ut. Dragen går inn i tåken. Vi ser bare skyggen — og glohet varme
innenfra som lyser opp tåken rundt den.

- **Bygg:** Unreal
- **Tunge greier:** samme lys-i-tåke-teknikk som S08, men i bevegelse. Emissivt
  volum inne i dragen som lyser tåken opp innenfra
- **Merk:** vi skal *miste* dragen i tåken, ikke se den fly bort. Den blir en glød

### S19 · 1:27–1:32 (5s) · BLACK
Kutt til svart. Tekst kommer på: **TO BE CONTINUED**.
Over svart, mannskapets stemmer:

> "Dragon —"
> "Where is it?!"
> "WATCH OUT!"

- **Bygg:** Premiere
- **Merk:** stemmene skal komme *etter* at teksten har stått en stund. Publikum
  skal rekke å tro at det er slutt

---

## Klippe-rytme

```
S01 ──────  5s   rolig
S02 ─────   5s   |
S03 ────    4s   | bygger
S04 ────    4s   |
S05 ────────8s   \  tåken = pust
S06 ────────8s   /  reveal
S07 ─────   5s   |
S08 ────    4s   | strammer
S09 ────    4s   |
S10 ───     3s   |
S11 ───     3s   ← BAAM
S12 █████   5s   ← signature, slow-mo
S13 ────    4s   løpet
S14 ────    4s   |
S15 ────    4s   hoppet
S16 ───     3s   ← STILLE
S17 ██████  7s   ← VOFF
S18 ██████  7s   ut
S19 ─────   5s   black
```

Formen er: rolig → tåke-pust → strammere og strammere → BAAM → stille → utbrudd.
Stillheten i S16 er det som gjør at S17 treffer. Ikke rør den.

---

## Åpne punkter

- **S02/S03** — live action, AI, eller 3D? Ansikter og hender i nærbilde er det
  dyreste du kan gjøre i 3D og det billigste å filme
- **S01** — hvor mye hav ser vi egentlig? Jo strammere lens, jo mindre vann må
  simuleres
- **Rettigheter:** «Dracarys», høyvalyrisk og drage-på-rygg-formatet ligger tett
  på Game of Thrones / HBO. Uproblematisk som portfolio- og fanarbeid;
  et lisensspørsmål hvis dette skal ut kommersielt eller monetiseres. Verdt å
  avklare før du legger måneder i det.
