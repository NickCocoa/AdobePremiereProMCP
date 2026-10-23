# Shot plan — <scene name>

Tutorial: <title, creator, URL>  ·  Assets: <link, licence>  ·  Credit line: "<scene> recreated from <creator>'s tutorial"
Target: <total length> s @ <fps> fps, <16:9 1920×1080 / 9:16 1080×1920>, render on <GPU / machine>

## Shots
| # | Frames (start–end) | Duration | Camera (type, lens, sensor) | Height / position | Movement & speed | In frame | Reference frames | Tutorial chapter |
|---|---|---|---|---|---|---|---|---|
| 1 | 1–96 | 3.2 s | perspective 24 mm, 36 mm sensor | 1.2 m, low behind car | follows car, 8 m/s | car on gravel path, birch forest | dense/f_00001–00096 | 1:12:30 |
| 2 | | | | | | | | |

## Build stages (each ends with a test render compared to its reference)
| Stage | What | Tutorial timestamp | Reference frame | Status |
|---|---|---|---|---|
| 1 | Terrain + ground textures | | | ☐ |
| 2 | Sky / HDRI / sun angle | | | ☐ |
| 3 | Large plants (trees) | | | ☐ |
| 4 | Mid plants (shrubs, ferns) | | | ☐ |
| 5 | Ground cover (grass, branches, leaves, pebbles) | | | ☐ |
| 6 | Path / road cut + masks | | | ☐ |
| 7 | Hero assets (vehicle, buildings) | | | ☐ |
| 8 | Animation (rig, timing) | | | ☐ |
| 9 | Cameras per shot | | | ☐ |
| 10 | Preview render → fixes → stills → final | | | ☐ |

## Techniques and dependencies found in the tutorial
| Technique / add-on | Used for | Our replacement (if third-party) |
|---|---|---|
| <paid scatter add-on> | plant distribution | `scripts/scatter.py` |
| <car rig add-on> | vehicle animation | `scripts/vehicle_rig.py` |

## Decisions and pivots
- <date>: <what changed and why>
