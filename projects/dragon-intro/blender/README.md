# Blender previs — HELIOS

Blockout-previs av hele 115-sekunders intron. 25 kameraer bundet til
timeline-markorer, sa du kan spille av fra frame 1 og se klippet kutte seg
selv gjennom alle shots.

Alt er generert fra script. Vil du endre noe, endre `previs_build.py` og kjor
den pa nytt — ikke rediger `.blend`-fila og hap at du husker hva du gjorde.

## Komme i gang

```bash
# Bygg scenen
blender --background --python previs_build.py -- --out helios_previs.blend

# Apne den og spill av
blender helios_previs.blend
```

`helios_previs.blend` ligger ferdig bygget her hvis du bare vil se pa den.

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
