# Vaktskiftet — genereringspakke

Klar-til-fyring prompts for første generering av piloten «Slagordet». Skrevet for Higgsfield.

Rekkefølge: **stilnøkkel → figurark → beat 1.** Ikke hopp over stilnøkkelen — alt annet refererer til den.

---

## 0. Forutsetninger

| | Status |
|---|---|
| Higgsfield-kreditter | **0 — blokkert.** Trenger plan |
| Norske preset-stemmer | Finnes ikke. Må klones fra ekte opptak |
| Artlist | Ikke autorisert |

Estimert kredittbruk for én ferdig episode: **700–900** ved realistisk retry-rate (3–4 forsøk per brukbart klipp). Anslag ut fra plantabellenes egne tall, ikke målt.

---

## 1. Stilnøkkelen

Genereres **én gang**. Alle senere bilder og klipp refererer til dette.

### Masterbilde av rommet

> Interior of a Norwegian regional distribution depot goods-in bay, 05:38 in late October. Bare concrete floor with faded yellow floor markings, grey steel pallet racking three levels high, a roller door standing half open onto a dark loading yard. Overhead fluorescent tubes, slightly green, one of them a little dimmer than the others. Cold blue pre-dawn light bleeding in from the yard, mixing badly with the fluorescent. A scuffed work table with a handheld barcode scanner on a coiled cable and a ring binder. On the side wall a cluster of worn A4 notices: safety posters, a shift rota, a curled Christmas greeting nobody took down.
>
> Shot on 35mm lens, handheld documentary framing, slightly off-level. Flat naturalistic exposure, no cinematic colour grade, no lens flare, no haze, no god rays. Muted palette: concrete grey, hi-vis orange, worn blue workwear, one patch of warm sodium from the yard. Unglamorous, slightly ugly, completely real. Looks like a frame from an observational documentary, not an advertisement.
>
> 16:9. No people in frame. No text legible on any poster.

**Modell:** nano_banana_pro eller seedream (høyest oppløsning tilgjengelig)
**Generer:** 4 varianter. Velg én. **Den er låst.**

### Negativt — gjelder alle prompts

> No cinematic teal-and-orange grade. No shallow depth of field on wide shots. No lens flare, no haze, no volumetric light shafts. No glossy surfaces. No smiling. No one looking at camera. No modern glass-and-steel architecture. No American warehouse signage. No visible brand logos other than the one specified.

---

## 2. Figurark — Tom-Erik

Trengs for beat 1. De fem andre genereres etterpå, samme oppskrift.

> Character reference sheet, four views of the same man: front, three-quarter, profile, and from behind over the shoulder.
>
> Norwegian man, 41, night-shift warehouse worker. Thin face, slightly hollow under the eyes. Three-day stubble, uneven. Dark blond hair, flattened on one side from a cap. Pale, tired skin with visible pores, a little shine on the forehead, broken capillaries on the cheeks. Ears slightly prominent. Mouth naturally neutral, not expressive. He is not handsome and he is not ugly.
>
> Wearing a faded orange hi-vis vest over a navy blue fleece with the zip half down, and grey work trousers with a worn knee. Carries an empty coffee mug.
>
> Expression across all four views: awake too long. Not sad, not comic — vacant in the specific way of someone who has been up since 22:00 and is thinking about something unrelated.
>
> Flat even lighting, neutral grey background, no stylisation. Unretouched photographic realism: skin texture, asymmetry, real pores, no beauty retouching, no smoothing, no makeup. Shot like a casting polaroid, not a portrait.

**Modell:** samme som stilnøkkelen
**Generer:** 4 varianter. Velg én. **Låst** — brukes som referansebilde i hvert klipp han er i.

---

## 3. Beat 1 — kaldåpningen

20 sekunder, ingen dialog. **Dette er første ting som genereres**, fordi det ikke trenger stemme i det hele tatt.

Fire klipp à 5 sekunder. Alle refererer stilnøkkelen + Tom-Erik-arket.

### Klipp 1.1 — det tomme rommet · 5s

> The empty goods-in bay. Static handheld, slight breathing movement in the frame. Fluorescent hum. Nothing happens. In the background through the half-open roller door, a forklift idles out of sight, its hydraulics ticking.
>
> Hold. No camera move, no subject. The shot is too long on purpose.

### Klipp 1.2 — han kommer inn og stopper · 5s

> The same bay. The man in the orange hi-vis vest walks in from frame left carrying an empty mug, heading across the room. Two steps in he stops. He has seen something on the side wall. He turns his head toward it.
>
> Handheld, following him loosely, a beat late — the camera finds him after he has already stopped.

### Klipp 1.3 — plakaten · 5s

> Over his shoulder from behind, slightly out of focus foreground of his vest. On the wall, among the worn A4 notices, one new sheet: crisp white, laminated, much more white space than the others, a small logo slightly too large in the corner. He reaches up and straightens it. It was not crooked.
>
> The laminate catches the fluorescent light for a moment as it moves.

### Klipp 1.4 — bildet han sletter · 5s

> Medium, from his side. He has stepped back. He looks at the sheet. He takes out a phone, raises it, photographs the sheet. Lowers the phone. Looks at the screen. His thumb moves once. He puts the phone away and walks out of frame.
>
> Static handheld. He is never in profile to camera long enough for his mouth to matter. No reaction shot — the camera does not reward us.

**Modell:** kling3_0 eller seedance (test begge på klipp 1.3 først — det er det vanskeligste)
**Rekkefølge:** generer 1.3 først. Hvis plakaten ikke ser ekte ut, stopper alt der.

### Plakaten er kritisk

Teksten **VI FLYTTER MER ENN VARER.** skal ikke genereres som del av bildet — AI-modeller setter tekst upålitelig. Generer plakaten som tom hvit laminert flate, og legg teksten på i etterarbeid. Da er den også riktig font hver gang, og kan byttes per kunde uten ny generering.

Det er samme logikk som re-skin-laget i formatbibelen: det som skal variere per kunde, holdes utenfor generert bilde.

---

## 4. Lyd

Beat 1 trenger ingen stemme. Men den trenger romlyd, og den bør være ekte:

- Lysrørsummen
- Trucken som durer utenfor
- Skritt på betong
- Laminatet som smeller svakt mot veggen

Dette er billigere og bedre tatt opp på telefon i et hvilket som helst lager enn generert.

### For beat 2 og framover

Ingen norske preset-stemmer tilgjengelig. Veien til norsk tale går gjennom **stemmekloning fra ekte opptak** — som er det du ville uansett. Rekkefølgen blir:

1. Ta opp de ekte stemmene i bås
2. Klipp lyden til dialogspor
3. **Så** generer bildet mot ferdig lyd

Med AI-generert bilde er lyd-først enda mer riktig enn med ekte opptak: å regenerere et klipp koster kreditter, en studiodag med en kjendis koster penger. Den dyreste ressursen låses først.

---

## 5. Hva som genereres etter beat 1

| Steg | Innhold | Avhenger av |
|---|---|---|
| 1 | Stilnøkkel | — |
| 2 | Tom-Erik-ark | Stilnøkkel |
| 3 | **Beat 1, fire klipp** | 1 + 2 |
| 4 | Fem figurark til | Stilnøkkel |
| 5 | Stemmeopptak, ekte | Ingenting teknisk |
| 6 | Beat 2–5 | Alt over |
| 7 | Cutdowns, vertikalt, merking | Ferdig episode |

Stopp etter steg 3 og se på det. Hvis kaldåpningen ikke holder, er det billigere å finne ut der enn etter seks figurark.
