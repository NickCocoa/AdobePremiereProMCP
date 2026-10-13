# Blender previs — HELIOS

Blockout-previs av hele 115-sekunders intron. 25 kameraer bundet til
timeline-markorer, sa du kan spille av fra frame 1 og se klippet kutte seg
selv gjennom alle shots.

Alt er generert fra script. Vil du endre noe, endre `previs_build.py` og kjor
den pa nytt — ikke rediger `.blend`-fila og hap at du husker hva du gjorde.

## Komme i gang

```bash
# Blockout — gra kasser, bygger pa sekunder
blender --background --python previs_build.py -- --out helios_previs.blend

# Med den ekte lokasjonen: basaltsoyler, grotte, plata, sjostabler, hav
blender --background --python previs_build.py -- --landscape --out helios_full.blend

# Bare landskapet, uten shots og kameraer
blender --background --python landscape_build.py -- --out helios_land.blend
```

Begge `.blend`-filene ligger ferdig bygget her hvis du bare vil se pa dem.

Bruk blockouten til a teste timing og klipperytme — den bygger og rendrer
raskt. Bruk `--landscape` nar du vil se hvordan shotene faktisk sitter i
terrenget.

## Rendre

```bash
# Ett bilde per shot — rask sjekk av blocking
blender -b helios_previs.blend --python render_previs.py -- --contact out/

# Hele animaticen, klar for Premiere
blender -b helios_previs.blend --python render_previs.py -- --all out/ --pct 50
```

Med GPU gar dette i sekunder per frame. Hele animaticen pa 2760 frames er en
kaffepause, ikke en natt.

## Hva som er i scenen

| Collection | Innhold |
|---|---|
| `OCEAN` | Havplan |
| `BOATS` | Fire langskip med mannskapskasser og en leder fremst pa skip 1 |
| `LOCATION` | Fjellmasse, basaltsoyler, grotteinngang med glod, kanten pa toppen |
| `FIRE` | Ildveggen i S17/S18 |
| `CHAR_MAN` | Mannen (1,8 m blockout) |
| `DRAGON` | Blockout-drage, 22 m vingespenn |
| `ARROWS` | 90 piler som en sverm |
| `FOG` | Takebank, havdis, global dis |
| `CAMERAS` | 25 kameraer + look-at-targets |
| `LANDSCAPE` | Med `--landscape`: den ekte lokasjonen, erstatter `LOCATION` og `OCEAN` |

## Landskapet (`landscape_build.py`)

Prosedyregeometri, ~87 000 flater, bygget med `from_pydata` i stedet for
`bpy.ops` per objekt — rundt 900 soyler som enkeltobjekter tar minutter, som
ett mesh tar det sekunder.

| Objekt | Hva det er |
|---|---|
| `CLIFF_columns` | Sekskantpakkede basaltsoyler over hele veggen |
| `CLIFF_face` | Forvitret veggflate, med grotteapningen trukket inn i geometrien |
| `CLIFF_body` | Massen bak. Starter pa y=+178, bak veggflatens dypeste punkt |
| `CAVE_tunnel` | Gangen innover i fjellet |
| `CAVE_glow` | Glodeflaten. Tennes paa ropet i S14 |
| `PLATEAU` | Toppen. Flat i spillflaten, erodert utenfor |
| `TALUS` | Ur der veggen moter sjoen |
| `SEA_STACKS` | Reynisdrangar-aktige skjaer ute i sjoen |
| `OCEAN` | Bolgesatt havflate |

**Spillflaten paa plataet er helt flat paa `GROUND_Z`.** Det er ikke
kosmetikk: previs plasserer mannen og fem kameraer paa den hoyden, og en
myk utflating som bare naermer seg 352 m la terrenget over kameraene og
rendret fem shots svarte. Kjernen (|x| < 87 m, y < 93 m fra kanten) er
tvunget flat, og terrenget faar forst karakter utenfor den.

## Dragens flybane — rediger den i viewporten

Dragen ligger pa en Bezier-kurve, `DRAGON_PATH`, ikke pa keyframede
posisjoner. Velg kurven, gaa i Edit Mode, og dra i kontrollpunktene — hele
flyvningen folger med, og en Follow Path-constraint sorger for at dragen
peker dit den faktisk flyr. Du trenger ikke rore rotasjon.

Seks kontrollpunkter, i flyretning:

| # | Hva det styrer |
|---|---|
| 1 | Startposisjon under kanten, ute av bildet |
| 2 | Der hun bryter opp forbi kanten |
| 3 | Toppen av buen over stupet |
| 4 | Der hun legger seg over og svinger ut |
| 5 | Inngangen i takebanken |
| 6 | Sluttposisjonen, borte inne i taken |

Handtakene staar paa AUTO, saa de folger med av seg selv naar du flytter et
punkt. Vil du ha en skarpere sving, sett det punktets handtak til `Free`
eller `Aligned` og dra i dem.

**Tempoet er skilt fra formen.** Naar dragen er hvor paa banen styres av
`eval_time` paa kurvedataen, med tre nokler: start paa S23, 30 % ved slutten
av S23 (utbruddet), og full bane ved slutten av S25. Vil du at hun skal
komme senere eller akselerere hardere, flytt de noklene — banen beholder
formen.

**Pass paa hoyden.** AUTO-handtakene skyter litt over kontrollpunktet, saa
buen topper hoyere enn punkt 3. Med dagens verdier naar hun 379 m, og
S23-kameraets ramme slutter rundt 392 m. Drar du punkt 3 oppover, sjekk at
hun ikke klatrer ut av bildet midt i shotet.

## Tre ting som er verdt a vite

**Vingeslaget er satt bevisst sakte.** `WINGBEAT_SEC = 2.0` — ett fullt slag
per to sekunder. Det foles tregt nar du scrubber, og det er riktig. For raskt
vingeslag er den enkeltfeilen som odelegger skalaen mest. Se `../docs/dragon.md`.

**Kameraene som filmer mannen er festet til ham** (`parent="MAN"` i shotlista).
Faste kameraer bommet pa ham fordi han gar mens de star. Det samme gjelder
S03/S04/S06/S08, som er festet til `BOAT_1` — batene seiler gjennom hele Akt 1.

**Regn pa avstand for du plasserer kamera:**

```
bredde_i_frame = avstand * 36mm / brennvidde
hoyde_i_frame  = avstand * 15.06mm / brennvidde     (2.39:1)
```

For a fa hele den 352 m hoye veggen inn pa 32 mm trenger du ~740 m avstand.
Forste utkast sto pa 172 m og vi sa bare striper.

## Tune den

Alt i `CONFIG` ovst i `previs_build.py` er ment a endres: avstander,
fjellhoyde, takens tetthet og plassering, vingespenn, vingeslagfrekvens.
`SHOTS`-tabellen under er hele klippet — varighet, brennvidde, kamerabane og
look-at per shot. Endrer du en varighet, flytter alt nedstroms seg automatisk.

Vil du teste om Akt 1 holder pa 33 sekunder i stedet for 41: sett `S05` til
0 sek eller slett linja, og kort `S02` og `S06`. Bygg pa nytt, se pa det.
Det er hele poenget med a ha klippet som data.

## Versjonskompatibilitet

Testet pa Blender 5.2.2 LTS. `iter_fcurves()` handterer bade slotted actions
(Blender 4.4+) og den gamle flate `action.fcurves` (4.3 og eldre), sa scriptet
skal ga pa begge.
