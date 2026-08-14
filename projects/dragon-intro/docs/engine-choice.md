# Motorvalg — Unreal vs Blender

Kort svar: **Unreal for filmen, Blender som modelleringsverktøy ved siden av.**
Men det er én reell grunn til å velge Blender likevel, og den handler om hvor mye
av jobben jeg kan gjøre for deg. Les begge seksjoner før du bestemmer.

---

## Hva som faktisk definerer denne intron visuelt

Tre ting bærer hele filmen:

1. **Volumetrisk tåke med lys som blør inni den** — S06 (reveal), S08 (grotta
   lyser opp), S18 (dragen som glød i tåka). Dette er ikke pynt, det er selve
   ideen i intron.
2. **Ild i stor skala** — S11, ildvegg langs hele fjellkanten.
3. **Hav i bevegelse** — S01, det du selv flagget som tidssluk.

Alle tre er sanntid og gratis i Unreal. Alle tre er tunge i Cycles.

---

## Rendertid — der forskjellen blir brutal

92 sekunder på 24 fps = **~2 200 frames**. Med slow-mo-shotet (S12 rendret på
96–120 fps) lander du nærmere 2 600.

| | Blender / Cycles | Unreal / MRQ |
|---|---|---|
| Volumetrisk tåke i dybden | Volumestøy krever høy sample-count. 8–25 min/frame ved 4K er realistisk på de tåkeshotene | Sanntid. Sekunder per frame med høy Temporal Sample Count |
| Ild i stor skala | Mantaflow. Timevis med baking før du i det hele tatt ser resultatet, og du må re-bake for hver justering | Niagara Fluids: tungt, men interaktivt. Billboard-basert ild: nesten gratis |
| Hav | Ocean modifier + skum. Baking + tung shading | Water plugin / Single Layer Water, eller ferdig Fab-asset |
| Fjellvegg i full oppløsning | Displacement koster minne og tid | Nanite. Megascan-basalt i full res uten LOD-arbeid |

Regnestykket: 2 600 frames × 12 min = **~22 døgn** sammenhengende rendering på én
maskin. Samme sekvens i Unreal ligger i timer, ikke uker. Og det verste er ikke
selve rendringen — det er at hver gang du vil endre noe, betaler du prisen på
nytt. I Unreal ser du endringen med en gang.

Legg til at Lumen gjør akkurat den effekten intron er bygget rundt: emissivt lys
som sprer seg inn i volumetrisk tåke, i sanntid. S08 og S18 er nesten
gratis-shots i Unreal og blant de dyreste i Cycles.

Og dragen din fra Fab ligger med all sannsynlighet allerede som UE-asset med
skjelett og animasjoner.

---

## Grunnen til å velge Blender likevel

Det handler ikke om resultatet. Det handler om arbeidsfordelingen mellom oss.

**Velger du Blender:** jeg kan skrive `bpy`-scripts som bygger hele lokasjonen fra
ingenting — fjellvegg, grotteinngang, tåkevolumer, kameraer med de bevegelsene
som står i shotlisten, lysrigg, og pilsystemene som geometry nodes. Du åpner en
`.blend` som allerede er satt opp og begynner å justere. Alt er kode, alt ligger
i git, alt kan itereres ved at jeg endrer scriptet.

**Velger du Unreal:** jeg kan skrive Python-scripts for editoren (level-oppsett,
fog-parametere, Niagara-konfig, Sequencer-kameraer, MRQ-innstillinger) og
detaljerte oppskrifter — men jeg har ingen Unreal-editor her til å verifisere at
de faktisk kjører. Mer av det manuelle arbeidet lander på deg.

Så: **Blender = jeg gjør mer av jobben, du venter lenger på hver render.
Unreal = bedre resultat mye raskere, men mer klikking på deg.**

---

## Anbefalingen

**Unreal for filmen.** Rendertiden alene avgjør det — 22 døgn per iterasjon er
ikke et prosjekt du fullfører, og du har allerede pekt på vann som ditt
bekymringspunkt. Unreal fjerner nettopp det problemet.

**Blender ved siden av** til det den er best på: modellere og skulpturere
fjellveggen og grotteinngangen, så eksporter til Unreal som Nanite-mesh. Der kan
jeg fortsatt skrive scriptet som bygger geometrien.

**Hybrid som faktisk fungerer:**

| Shot | Hvor |
|---|---|
| S01 båter/hav | Unreal, eller AI som du var inne på |
| S02–S03 mannskap nært | Live action eller AI — ikke 3D |
| S04–S18 | Unreal |
| Fjellvegg + grotte (modellering) | Blender → Nanite-export → Unreal |
| S19 + hele klippen | Premiere |

---

## Hvis du vil unngå å binde deg ennå

Det finnes en tredje vei: **bygg blockout-previs i Blender først.** Grå kasser,
riktige proporsjoner, riktige kamerabevegelser, riktig timing — rendret i
EEVEE på sekunder per frame. Du får hele intron å se på som en 92-sekunders
animatic før du har brukt en time på tåke eller ild.

Det er der jeg kan gjøre mest for deg umiddelbart, og det er ikke bortkastet
uansett hvilken motor du lander på: kamerabanene og timingen overføres til
Unreal, og du får sett om klipperytmen i shotlisten faktisk holder før du bygger
noe pent.

Det er min anbefaling for neste steg uansett hva du velger til slutt.
