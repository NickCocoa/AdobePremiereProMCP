# HELIOS — Action Intro / Shotliste v2

**Lengde:** ~1:55 (115 sek) · **Format:** 2.39:1, 24 fps · **Sluttleveranse:** Premiere

Endret i v2: båtsekvensen utvidet fra 18s til 41s etter ønske. Alle timecodes
nedstrøms forskjøvet. Shotnummer renummerert (25 shots totalt).

Kolonnen **Bygg** sier hvor shotet lages. **Tunge greier** er det som koster tid.
Shots merket **[TRIM]** er de du kutter først hvis båtsekvensen skal ned mot 30s.

---

## AKT 1 — HAVET (0:00–0:41)

### S01 · 0:00–0:06 (6s) · Åpning — og kroken
Tom havflate. Grålys, kald sjø. Tåkeveggen ligger i horisonten. Lyd: bare sjø og
vind. Så driver noe forbi i forgrunnen — vrakrester, et brent skjold, en åre.
Rett etterpå bryter en stevn inn i frame.

- **Kamera:** lavt, like over bølgetopp, 85mm
- **Bygg:** Unreal (hav) eller AI
- **Merk:** dette er den viktigste endringen i v2. Med 41 sekunder båt før noe
  skjer, *må* publikum vite innen 6 sekunder at det er noe galt. Vrakgodset gjør
  de neste 35 sekundene til spenning istedenfor venting. Uten det er de bare
  fire båter som seiler

### S02 · 0:06–0:11 (5s) · Formasjonen
Vidt. Fire langskip i formasjon skjærer gjennom grå sjø, kurs mot tåkeveggen.

- **Kamera:** høyt og vidt, 35mm, langsom sidelengs drift
- **Bygg:** Unreal / AI
- **Tunge greier:** havet. Se `docs/water.md`

### S03 · 0:11–0:15 (4s) · Ombord
Skip 1. Årer i takt. Ansikter. Vått tre, is i skjegget, pust som damper.

- **Kamera:** hoftehøyde, håndholdt, 35mm
- **Bygg:** live action eller AI — ikke 3D

### S04 · 0:15–0:18 (3s) · Lederen speider
Han ser mot tåken. Ser ingenting. Det er verre enn å se noe.

- **Kamera:** 50mm, nær, statisk
- **Bygg:** live action / AI

### S05 · 0:18–0:22 (4s) · Ordren går **[TRIM]**
Håndsignal fra skip til skip nedover rekka. Ingen snakker.

- **Kamera:** følger signalet i pan, båt til båt
- **Bygg:** Unreal / AI

### S06 · 0:22–0:27 (5s) · Buene opp
Serie nærbilder: hånd om grepet, streng som trekkes, pilespiss, våt lærhanske,
pust som holdes.

- **Kamera:** makro/nært, 4–5 raske klipp innenfor shotet
- **Bygg:** live action / AI

### S07 · 0:27–0:31 (4s) · Alle fire
Statisk vidt. Fire skip, alle buer hevet mot tåken. Ingen beveger seg.

- **Kamera:** statisk, 24mm
- **Bygg:** Unreal
- **Merk:** hold dette lenger enn det føles behagelig

### S08 · 0:31–0:35 (4s) · "FIRE!"
Lederen. Push-in. Ropet.

- **Kamera:** slow push-in, 50mm
- **Bygg:** live action / AI
- **Merk:** siste ansikt vi ser før tåken

### S09 · 0:35–0:38 (3s) · Salven
Fra alle fire båter går pilregnet opp samtidig.

- **Bygg:** Unreal — Niagara mesh-emitter, ~300–500 piler
- **Tunge greier:** 2–3 frames jitter i avgangstid per båt, ellers ser det ut
  som en powerpoint-animasjon

### S10 · 0:38–0:41 (3s) · Opp
Pilene stiger mot grå himmel. Kamera tilter opp og låser seg på svermen.

- **Bygg:** Unreal
- **Merk:** overgangen til pil-POV. Låsen må skje her, ikke i S11

---

## AKT 2 — GJENNOM TÅKEN (0:41–0:57)

### S11 · 0:41–0:49 (8s) · Pil-POV inn i tåken
Kamera følger svermen inn i tåkeveggen. Lyset dør, lyden dempes til fjærsus og
vind.

- **Bygg:** Unreal
- **Tunge greier:** volumetrisk tåke i dybden. Default Volumetric Fog Distance i
  UE er 6000 cm — altfor kort her. Se `docs/fog.md`
- **Lyd:** her kutter du mixen ned til nesten ingenting, så S14 treffer

### S12 · 0:49–0:57 (8s) · REVEAL — fjellveggen
Tåken tynnes. Den svarte islandske fjellveggen tårner opp. Høyt i veggen: en
grotteinngang. Mørk, foreløpig.

- **Bygg:** Unreal, Nanite. Quixel/Fab har islandske basalt-scans
- **Tunge greier:** skalaen. Veggen må føles 300–400 m høy. Bruk tåkelag i dybden
  som skalareferanse, ikke bare størrelse
- **Merk:** filmens første «oh shit». Ikke skynd deg

---

## AKT 3 — MANNEN (0:57–1:13)

### S13 · 0:57–1:02 (5s) · Skikkelsen på kanten
Langt der fremme på fjellkanten: en menneskeskikkelse på vei mot kanten. Nesten
for liten til å se.

- **Bygg:** Unreal
- **Merk:** hold ham liten. Publikum skal måtte lete

### S14 · 1:02–1:06 (4s) · "DRACARYS!"
Ropet. Grotteinngangen lyser opp innenfra — glohet oransje som pulserer.

- **Replikk:** `Dracarys` — se `docs/valyrian.md` (du skrev «Dacaris»)
- **Bygg:** Unreal — emissivt materiale + point light med light function, koblet
  mot volumetrisk tåke så lyset blør ut i lufta
- **Tunge greier:** lyset må treffe tåken, ikke bare geometrien. Det er effekten

### S15 · 1:06–1:10 (4s) · Skriket
Monstrøst drageskrik. Bass. Fugler letter fra veggen. Løs stein raser.

- **Bygg:** Unreal — fugler og stein som Niagara
- **Lyd:** 80% lyd. Bygg bildet rundt lyden, ikke omvendt

### S16 · 1:10–1:13 (3s) · Pilene kommer ned
Fra mannen. Kamera ser oppover: pilregnet på vei ned mot ham.

- **Bygg:** Unreal
- **Merk:** første sidebytte. Vi har vært på pilene i 30 sek — nå er vi på den de
  skal treffe

---

## AKT 4 — ILDEN (1:13–1:25)

### S17 · 1:13–1:16 (3s) · BAAM
Ild spruter opp langs hele fjellkanten som en vegg.

- **Bygg:** Unreal — Niagara. Se `docs/fire.md`
- **Tunge greier:** ild i denne skalaen

### S18 · 1:16–1:21 (5s) · Pilene blir til støv
Slow-mo. Pilene treffer ildveggen, brenner bort, blir til aske som driver rolig i
lufta foran ansiktet hans.

- **Kamera:** render på 96–120 fps, retime i Premiere
- **Bygg:** Unreal — dissolve/erosion-materiale drevet av scalar parameter;
  Niagara-aske spawner på pil-death
- **Tunge greier:** signature-shotet. Sett av mest tid her
- **Merk:** asken skal falle *rolig*. Kontrasten mot volden er hele poenget

### S19 · 1:21–1:25 (4s) · Løpet
Han løper. Fortere og fortere mot kanten.

- **Kamera:** håndholdt, lavt, bak ham. Økende rystelse
- **Bygg:** Unreal

---

## AKT 5 — HOPPET (1:25–1:43)

### S20 · 1:25–1:29 (4s) · "Māzīs, Helios!"
Han roper på høyvalyrisk.

- **Replikk:** `Naejot māzīs, Helios!` — se `docs/valyrian.md`
- **Bygg:** Unreal

### S21 · 1:29–1:33 (4s) · Hoppet
Han hopper over kanten. Kamera blir stående. Tomt frame — kanten, tåken,
himmelen. Kamera kryper sakte fremover.

- **Kamera:** langsom dolly fremover. Ikke følg ham ned
- **Bygg:** Unreal

### S22 · 1:33–1:36 (3s) · Stille
Ingenting. Tre sekunder tomt frame.

- **Lyd:** total stillhet. Ikke vind engang
- **Merk:** modigste kuttet i filmen. Ikke forkort det i redigering fordi det
  «føles langt» — det *skal* føles langt

### S23 · 1:36–1:43 (7s) · VOFF
Vingeslag. Dragen bryter opp i frame nedenfra med ham på ryggen, kurs mot tåken.

- **Kamera:** statisk, la dragen fylle framet
- **Bygg:** Unreal — Fab-dragen. Se `docs/dragon.md`
- **Tunge greier:** dette og S24 er de eneste shotene der dragen er synlig.
  ~10 sekunder totalt. Det er lite, og det er med vilje — les `docs/dragon.md`

---

## AKT 6 — UT (1:43–1:55)

### S24 · 1:43–1:50 (7s) · Skyggen i tåken
Kamera zoomer ut. Dragen går inn i tåken. Vi ser bare skyggen — og glohet varme
innenfra som lyser tåken opp rundt den.

- **Bygg:** Unreal
- **Merk:** vi skal *miste* dragen i tåken, ikke se den fly bort. Den blir en glød

### S25 · 1:50–1:55 (5s) · BLACK
Kutt til svart. Tekst: **TO BE CONTINUED**. Over svart, mannskapets stemmer:

> "Dragon —"
> "Where is it?!"
> "WATCH OUT!"

- **Bygg:** Premiere
- **Merk:** stemmene kommer *etter* at teksten har stått. Publikum skal rekke å
  tro at det er slutt

---

## Klipperytme

```
AKT 1 — HAVET                     41s
S01 ──────   6s   kroken: vrakgods
S02 ─────    5s   |
S03 ────     4s   |
S04 ───      3s   | bygger sakte
S05 ────     4s   | [TRIM]
S06 █████    5s   |
S07 ────     4s   stillhet før ordren
S08 ────     4s   "FIRE!"
S09 ───      3s   salven
S10 ───      3s   lås på svermen

AKT 2 — TÅKEN                     16s
S11 ████████ 8s   \ pust
S12 ████████ 8s   / REVEAL

AKT 3 — MANNEN                    16s
S13 ─────    5s   |
S14 ────     4s   | strammer
S15 ────     4s   |
S16 ───      3s   |

AKT 4 — ILDEN                     12s
S17 ───      3s   ← BAAM
S18 █████    5s   ← signature, slow-mo
S19 ────     4s   løpet

AKT 5 — HOPPET                    18s
S20 ────     4s   |
S21 ────     4s   hoppet
S22 ───      3s   ← STILLE
S23 ██████   7s   ← VOFF

AKT 6 — UT                        12s
S24 ██████   7s   glød i tåke
S25 ─────    5s   black
```

Formen: kald åpning med noe galt → 35s stigende press → tåke-pust → strammere →
BAAM → stille → utbrudd.

Stillheten i S22 er det som gjør at S23 treffer. Ikke rør den.

---

## Om lengden — én ærlig innvending

**115 sekunder er ikke en intro lenger, det er en kortfilm.** Og 41 sekunder er
lang tid å bruke på båter før noe faktisk skjer.

Det er ditt valg, og strukturen over leverer 41s slik du ba om. Men to ting du
bør vite:

**Kroken i S01 er ikke valgfri når sekvensen er så lang.** Vrakgodset (eller noe
tilsvarende galt) er det eneste som holder de 41 sekundene oppe. Kutter du den,
kollapser akten.

**Vil du ned mot 30s:** kutt S05 (–4s), ta S02 til 3s (–2s) og S06 til 3s (–2s).
Det gir 33s uten å miste noe strukturelt. Alle tre er reine pusteshots.

Min anbefaling er 32–35s. Men bygg animaticen først (se `docs/start-here.md`) —
da ser du det selv på en ettermiddag istedenfor å diskutere det.

---

## Åpne punkter

- **S03/S04/S06/S08** — live action, AI eller 3D? Ansikter og hender i nærbilde er
  det dyreste i 3D og billigste å filme
- **S01/S02** — hvor mye hav ser vi? Jo strammere lens, jo mindre vann å simulere
- **Rettigheter:** «Dracarys» og høyvalyrisk ligger tett på GoT/HBO. Fint som
  portfolio- og fanarbeid, lisensspørsmål hvis det skal monetiseres. Se
  `docs/valyrian.md`
