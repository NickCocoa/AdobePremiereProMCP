# Hva du bør gjøre først

Kort svar: **ikke bygg fjellet.** De to første tingene er en 3-sekunders
dragetest og en animatic. Begge er ferdige innen en uke, og til sammen fjerner de
all reell risiko i prosjektet.

Rekkefølgen under er sortert etter risiko, ikke etter hva som er gøyest.

---

## 1. Drage-spike — 1 til 3 dager

**3 sekunder. Grå bakgrunn. Ingen omgivelser. Dragen slår med vingene én–to
ganger.**

Dette er første oppgave i prosjektet fordi det er det eneste du ikke vet svaret
på: **er Fab-dragen god nok?**

Alt annet i filmen kan du løse med tid. Hvis riggen er dårlig, kan du ikke det —
og da må du bytte drage. Den beslutningen koster nesten ingenting i uke 1, og
velter prosjektet i uke 12 når fjellet står ferdig og alt er bygget rundt en
drage som ikke funker.

Full kriterieliste i `dragon.md`. Kortversjon: har den nok vingebein til
membrandeformasjon, følger det med brukbar flyanimasjon, og tåler membranen en
cloth-sim?

Ett tall å ta med: **ett fullt vingeslag skal ta cirka 2 sekunder.** Slår du
raskere, leser dyret som lite uansett hvor bra alt annet er.

---

## 2. Animatic — 2 til 4 dager

**Hele 115 sekunder. Grå kasser. Riktige proporsjoner, riktige kamerabevegelser,
riktig timing. Scratch-lyd på.**

Rendres i EEVEE eller rett fra Unreal-viewporten, sekunder per frame.

Du trenger den nå av tre grunner:

**Båtsekvensen er akkurat doblet.** Du gikk fra 18 til 41 sekunder. Ingen —
heller ikke jeg — kan si deg fra en tekstfil om 41 sekunder båt holder eller
kjeder. En animatic svarer på det på en ettermiddag. Min gjetning er at du
lander på 32–35s, men gjett sammen med bildene foran deg, ikke uten.

**Skalaen på fjellet må testes før du modellerer det.** S12 er filmens første
store øyeblikk, og alt der handler om at veggen føles 300–400 meter høy. Det er
et kamera- og tåkeproblem like mye som et modelleringsproblem, og grå kasser
tester det like godt som ferdig geometri.

**Stillheten i S22 må verifiseres.** Tre sekunder tomt frame er filmens modigste
valg. Det virker eller så virker det ikke, og du kan bare høre det.

Ingenting av dette arbeidet kastes: kamerabaner og timing følger med videre
uansett motor.

---

## 3. Ett shot helt ferdig — 1 til 2 uker

Velg **ett** shot og ta det hele veien til ferdig render. Lys, effekter, grading,
alt.

Anbefaling: **S18** (pilene som brenner til aske). Det er signature-shotet ditt,
det rører ved ild, partikler, materialer og slow-mo — og hvis det ikke sitter,
mister filmen sitt beste øyeblikk.

Poenget er ikke shotet. Poenget er at du etterpå vet **hvor lang tid ett ferdig
shot faktisk tar deg.** Gang det opp, så har du en ekte tidsplan istedenfor et
håp. Nesten alle soloprosjekter i denne størrelsen dør fordi det regnestykket
aldri ble gjort.

---

## 4. Så bygger du

Først her begynner produksjon i vanlig forstand — fjellvegg, grotte, tåkeoppsett,
havet, resten av shotene.

Rekkefølge derfra: fjell og grotte → tåkeoppsett → drageshotene → havet →
nærbildene av mannskap → klipp og lyd.

**Havet til slutt, med vilje.** Det er det du selv flagget som tidssluk, og det er
den delen som lettest kan løses med AI eller et ferdig asset hvis tiden renner
ut. Ikke la det blokkere resten.

---

## Hvorfor ikke bare begynne på fjellet

Fordi fjellet er den delen du *vet* du klarer. Det er ingen risiko der, bare
timer. Risiko ligger i dragen (kan vise seg umulig med denne riggen) og i timingen
(41 sekunder båt kan vise seg å være dødt).

Begynn med det du kan ta feil om.

---

## Status på dokumentene her

| Fil | Status |
|---|---|
| `previs/shotlist.md` | Ferdig — v2, 25 shots, 115s |
| `docs/dragon.md` | Ferdig |
| `docs/valyrian.md` | Ferdig |
| `docs/engine-choice.md` | Ferdig — anbefaling: Unreal, med Blender til modellering |
| `docs/water.md` | Ikke skrevet ennå |
| `docs/fog.md` | Ikke skrevet ennå |
| `docs/fire.md` | Ikke skrevet ennå |

De tre siste er avhengige av motorvalget ditt — oppskriftene er helt forskjellige
i Unreal og Blender, så det er ingen vits i å skrive begge sett. Si fra hvilken
vei du går, så skriver jeg dem.
