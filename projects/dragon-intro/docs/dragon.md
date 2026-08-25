# Dragen — hvordan komme nær GoT-kvalitet

## Det ærlige svaret først

Drageshotene i Game of Thrones ble laget av Pixomondo, Image Engine, Rodeo FX og
Scanline — team på titalls artister, over måneder, på episodebudsjetter rundt
15 millioner dollar. Riggen til Drogon hadde muskel- og vevssimulering, egen
simulering av vingemembranen, og animatorer som gjorde ingenting annet enn drage
i ukevis.

Du kommer ikke til å matche det med en Fab-drage og én person. Det er ikke en
motivasjonsgreie, det er regnestykket.

**Men det du faktisk har bedt om er innen rekkevidde**, av én grunn: shotlisten
din eksponerer dragen i cirka **10 sekunder totalt** — S23 (7s) og S24 (7s, der
den er en silhuett i tåke). Alt annet er lyd, ild, lys og antydning.

Det er nøyaktig strategien GoT selv brukte. Se etter det neste gang: dragene er
nesten alltid i røyk, natt, motlys eller delvis utenfor frame. De skjuler dem,
fordi det både er billigere *og* skumlere.

**Målet ditt bør være:** «leser som ekte i disse to shotene». Ikke: «tåler et
30-sekunders hero-shot i klart dagslys». Det andre er ikke oppnåelig solo, og
det står heller ikke i manuset ditt. Ikke la ambisjonen krype dit.

---

## De fem tingene som faktisk avgjør om den ser ekte ut

Rangert etter effekt per time du legger i det.

### 1. Vingeslagfrekvens — den største avsløreren

Dette er nummer én, og det er gratis å fikse.

Vingeslagfrekvens skalerer omvendt med masse (grovt `f ∝ m^-1/3`). En svane på
10 kg slår rundt 3 slag i sekundet. En drage på 3–5 tonn lander da på
**omtrent ett fullt vingeslag hvert andre sekund.**

I S23 (7 sekunder) betyr det **3–4 vingeslag. Ikke mer.**

Nesten all amatør-drageanimasjon slår altfor fort, og hjernen leser det
øyeblikkelig som «lite dyr» eller «leke». Ingenting annet du gjør redder et for
raskt vingeslag.

Unntaket: selve utbruddet i S23 er et kraftslag — det kan og bør være mer
voldsomt enn marsjfart. Men det som følger, roer seg ned.

### 2. Vingemembranen må deformere

Stiv membran = falsk, umiddelbart. Membranen skal fange luft, bule ut på
nedslaget, rippe og slakke på oppslaget.

- **Unreal:** Chaos Cloth på membranen. Fest (pin) langs fingerbeina og
  armkanten, la bakkanten være fri. Start med lav stiffness og øk til den slutter
  å flagre som et håndkle
- **Blender:** cloth-sim med pinned vertex group, samme prinsipp

Dette er den nest største avsløreren etter frekvensen, og det er der jeg ville
brukt mest teknisk tid.

### 3. Kameraet skal ikke være perfekt

Gratis, og undervurdert.

En ekte kameraoperatør klarer ikke å holde et 20-meters dyr perfekt innrammet.
Det er alltid litt etterslep, litt overshoot, litt for sen korrigering.
Perfekt innramming leser som CG. Upresis innramming leser som dokumentar.

Legg inn litt lag i kameraets følging av dragen i S23, og la den nesten gå ut av
frame én gang. Koster ingenting, gjør enormt mye.

### 4. Motion blur og lukkervinkel

GoT er 24 fps med 180° lukker. CG-drager uten nok motion blur ser ut som
videospill.

I Movie Render Queue: skru på motion blur, sett riktig shutter angle, og bruk
høy nok Temporal Sample Count (8–32) til at bevegelsesuskarpheten faktisk blir
glatt og ikke stroboskopisk.

### 5. Luften skal reagere

Når vingen slår ned, skal noe skje med lufta. Tåke som virvles, støv som blåses,
løs snø.

Dette er en gave i din film: S23 og S24 foregår begge i tåke. Du har allerede
mediet som gjør interaksjonen synlig. Bruk det — Niagara som pusher tåkedensitet
lokalt på nedslaget, eller bare et partikkelsystem som trigges på
vingeslag-frames.

Interaksjon med omgivelsene er det som binder et CG-dyr til scenen. Uten det
flyter det oppå bildet.

---

## Hvordan få kontroll over den i praksis

Det du bør vite før du velger metode: **du trenger to helt forskjellige typer
bevegelse**, og de løses ulikt.

**Bane** — hvor dragen er i rommet, over tid. Dette er lett. Sequencer-kurve
eller Control Rig, håndkeyframet. En times jobb.

**Kropp** — vingeslag, hode, hale, sekundærbevegelse. Dette er den vanskelige
delen, og det er her tiden går.

Anbefalt oppsett i Unreal:

1. **Sjekk hva Fab-dragen faktisk har.** Kommer den med vingeslag-animasjon? Er
   den rigget på et skjelett du kan bruke? Dette avgjør alt annet — se
   spike-testen under
2. **Ett godt vingeslag-loop** som base. Enten den som fulgte med, eller én du
   lager selv
3. **Control Rig** oppå for bane, hoderetning og halesleng
4. **Chaos Cloth** på membranen
5. **Additive lag** i Anim Blueprint for pustebevegelse og små korreksjoner

Med bare 10 sekunder synlig drage trenger du ikke et system. Du trenger
to shots som sitter. Håndanimer dem hvis du må.

---

## Gjør denne testen først — før alt annet

**3 sekunder. Grå bakgrunn. Ingen omgivelser. Bare dragen som slår med vingene
én til to ganger.**

Det er den viktigste dagen i hele prosjektet, av én grunn: **du vet ikke ennå om
Fab-riggen er god nok.** Hvis membranen ikke lar seg simulere, hvis skjelettet er
rart, hvis vingeanimasjonen som fulgte med er ubrukelig — da vil du vite det i
uke 1, ikke i uke 12 når fjellet er ferdig og du ikke kan bytte drage lenger.

Testen svarer på:

- Har riggen vinge-/fingerbein nok til å deformere membranen skikkelig?
- Følger det med brukbar flyanimasjon, eller må du animere fra bunnen?
- Tar Chaos Cloth på membranen uten å eksplodere?
- Ser ett vingeslag på 2 sekunder riktig ut på akkurat denne modellen?

Hvis svaret er nei på flere: bytt drage nå. Det er en billig beslutning i uke 1
og en katastrofe i uke 12.

---

## Realistisk tidsbruk

For én person som lærer dette underveis, for de to drageshotene:

| | |
|---|---|
| Spike-test (3s, grå) | 1–3 dager |
| S23 — utbruddet, til det sitter | 2–4 uker |
| S24 — silhuett i tåke | 3–5 dager (den er billig, det er hele poenget) |

S24 er lett fordi tåken gjør nesten hele jobben. S23 er der pengene ligger.

Hvis S23 viser seg å bli for tungt, finnes det en helt legitim redning som ligger
i manuset ditt allerede: la utbruddet skje **delvis utenfor frame** — vinge og
skulder fyller bildet, resten er utenfor. Da slipper du å selge hele kroppen.
Det er også et bedre shot.
