# Vaktskiftet — pipeline: Blender → restyle

Blender eier **kontroll**. Restyle eier **look**. Ingenting annet.

Blender kjøres lokalt og frittstående — ikke drevet gjennom Higgsfield. Higgsfield (eller tilsvarende video-til-video) får bare ferdige renders inn og leverer det fotorealistiske passet ut.

---

## 1. Hvorfor denne delingen er riktig

Det vanskeligste i AI-produksjon av sitcom er ikke å lage ett pent bilde. Det er å lage **førti klipp i samme rom med samme seks ansikter**, over seks episoder, uten at rommet reoppfinner seg selv for hver generering.

Ren tekst-til-video feiler nøyaktig der. Blender løser det strukturelt, ikke statistisk:

| | Ren generering | Blender → restyle |
|---|---|---|
| Rommet | Nytt hver gang, prompt-flaks | Identisk ved konstruksjon |
| Eyelines og geografi | Tilfeldig | Ekte. Plakaten er alltid på samme vegg |
| Timing | 5-sekunders klumper du slåss med | Til frame |
| Pauser | Kan ikke styres | Eksakte |
| Re-skin per kunde | Nytt manus for prompten | **Asset-swap** |

### Den siste raden er den viktigste

Formatbibelen sier at re-skin er fire felter. I 3D blir det bokstavelig: samme blockout, nye teksturer, nye skilt, nye props. Samme kamerabevegelser, ny kunde.

Marginalkostnaden for kunde nummer to går mot null — og det er lisensieringsmodellen som faktisk bærer forretningen. **Det alene kan rettferdiggjøre 3D-bygget, uavhengig av look-spørsmålet.**

---

## 2. Bygg greybox, ikke ferdig sett

Det store feilsporet her er å bygge et detaljert, teksturert, lyssatt sett og rigge seks figurer. Det er ukers arbeid, og restylen overskriver det meste av overflatearbeidet uansett.

**Bygg i stedet en greybox:**

- Riktige dimensjoner på rommet
- Riktige posisjoner på reoler, port, bord, vegg med oppslag
- Enkle volumer, ingen detaljmodellering
- Ingen teksturarbeid utover grove verdier
- Figurer som enkle proxy-volumer eller enkle mannequins

Det du faktisk kjøper er **kamera, geografi og timing**. Det er alt restylen trenger å få servert. Overflaten er restylens jobb.

En greybox av varemottaket er dager, ikke uker. Et ferdig sett er uker.

---

## 3. Lyssettingen er ikke valgfri

Dette er den vanligste tabben. Restyle bevarer **luminansforhold** — den finner ikke opp lys, den tolker det som er der.

Flat grå render inn gir ustabilt, oppfunnet lys ut, forskjellig fra klipp til klipp. Da mister du nøyaktig den kontinuiteten du bygde 3D for.

Så: selv i greybox skal verdistrukturen være riktig.

- Lysrør i taket, svakt grønnlig, ett av dem litt svakere
- Kaldt blått fra porten, pre-dawn
- De to lyskildene skal krige litt — det er rommets karakter
- Én flekk varm natrium fra gården
- Ingen cinematisk lyssetting. Ingen rim light. Ingen motivert pent lys

Riktige verdier og riktig kontrast. Ikke pene materialer.

---

## 4. Renderspesifikasjon

| | Krav |
|---|---|
| Oppløsning | Render direkte i restyle-verktøyets native input. Ikke skaler etterpå |
| Framerate | 25 fps, låst |
| Kliplengde | **5 sekunder per klipp.** Ingen kutt inne i et klipp |
| Format | 16:9 master. Vertikale utsnitt rendres som **egne kameraer**, ikke beskjæres |
| Beauty-pass | Flat, enkel, korrekte verdier. Ikke prøv å være fotoreal |
| Bevegelse | Rolig. Restyle drifter på rask bevegelse |

Fem sekunder per klipp er ikke en begrensning utenfra — formatets beats er allerede bygget av 5-sekunders klipp. Det passer.

### Tilleggspass som er verdt å rendre

Restylen spiser bare RGB, men disse gir deg comp-kontroll etterpå:

- **Depth** — for atmosfære og for å holde dybde stabil
- **Object ID / cryptomatte** — for å maskere ansikter, holde hi-vis-fargen stabil, isolere props
- **Plakat-matte** — egen matte for plakaten alene

---

## 5. Plakaten: 3D-fordelen

Formatbibelen sier at det som varierer per kunde holdes utenfor genererte piksler. I 3D får du det nesten gratis.

- Render plakaten som **blank hvit laminert flate**
- Render en **egen matte** for den
- Legg teksten på i comp, med riktig perspektiv, riktig lyswrap, riktig refleks i laminatet

Du får en perfekt track gratis — noe generering aldri gir deg. Og teksten kan byttes per kunde uten én ny render.

Samme prinsipp for alt skiltverk, logo og oppslag på veggen.

---

## 6. Ansiktene — det eneste reelle problemet

3D-ansikter som bærer subtilt komisk spill er det vanskeligste i hele CG. Restyle hjelper, men introduserer sin egen fare: identitetsflimmer fra frame til frame.

Formatet er heldigvis allerede bygget rundt å unngå dette. Håndter beat for beat:

| Beat | Ansiktsbehov | Løsning |
|---|---|---|
| **1** Kaldåpning | Nesten ingen | Over skulder, bakfra. **Rendres rett fram i 3D** |
| **2** Overleveringen | Munn skjult allerede | Over skulder, ned i perm, mot vegg. 3D holder |
| **4** Vendingen | Samme | Samme |
| **3** Driften | Ensemble, ansikter, subtilt spill | Vanskeligst. Vurder stilisert look, eller generert med låst figurreferanse |
| **5** Knappen | **Ett ansikt avgjør alt** | Se under |

### Beat 5 bør filmes ekte

Beat 5 er én person, ett nært utsnitt, tjue sekunder, to korte replikker. Hele episodens emosjonelle last ligger der — det er replikken som gjør reklamen til en reklame.

Det er også det billigste tenkelige opptaket: én skuespiller, en vegg, et telefonkamera, tjue minutter.

**Film den ekte og comp den inn i 3D-platen.** Du får et virkelig menneskeansikt i det ene bildet som trenger det, for omtrent ingenting. Resten av episoden kan være 3D og restyle.

Det er samme logikk som hele formatet bygger på: bruk det dyreste virkemiddelet bare der det avgjør noe.

---

## 7. Restyle-passet

- Bruk **samme stilreferansebilde hver gang.** Stilnøkkelen i `docs/sitcom-genereringspakke.md` seksjon 1 er den referansen — den overlever uendret inn i denne pipelinen.
- Én stil, låst, hele sesongen. Det er det som gjør at seks episoder ser ut som én serie.
- Restyle klipp for klipp, aldri en hel sammensatt sekvens. Kutt forvirrer modellen.
- Kjør samme klipp to-tre ganger og velg. Drift varierer mellom kjøringer.
- Sjekk alltid første og siste frame mot hverandre for identitetsdrift før du godtar et klipp.

Higgsfield har video-til-video restyle som gjør nøyaktig dette (Genjutsu Styles — navngitte looks som tegner om din egen video og beholder bevegelsen). Andre verktøy gjør tilsvarende; jeg har bare verifisert at dette finnes i oppsettet ditt.

---

## 8. Rekkefølgen

Lyd først gjelder fortsatt, og gjelder enda sterkere nå: å animere mot ferdig lyd er gratis, å regenerere en studiodag er det ikke.

```
1. Ekte stemmeopptak                   ← ingen blokker, ingen kreditter
2. Lydklipp til dialogspor
3. Greybox av varemottaket             ← ingen blokker, ingen kreditter
4. Blocking + kamera mot ferdig lyd
5. Render, 5s-klipp, 25 fps
6. Restyle-pass                        ← krever Higgsfield-kreditter
7. Comp: plakattekst, beat 5-ansikt, grade
8. Cutdowns, vertikalt, merking
```

**Steg 1 til 5 koster ingenting i kreditter.** Det er der arbeidet ligger, og det kan starte nå.

Kredittbehovet kommer først i steg 6 — og da vet du allerede om formatet holder, fordi greybox-renderen med ekte lyd på allerede forteller deg om timingen og komikken fungerer. Et restyle-pass gjør ikke en død scene morsom.

---

## 9. Test i denne rekkefølgen

1. **Beat 1 som greybox-render med ekte romlyd.** Ingen restyle. Holder kaldåpningen på timing alene?
2. Hvis ja: restyle de fire klippene. Holder looken?
3. Hvis ja: bygg beat 2 og 4.
4. Beat 3 og 5 sist — de vanskeligste.

Stopp etter 1. En kaldåpning som ikke fungerer i greybox fungerer ikke i fotoreal heller.
