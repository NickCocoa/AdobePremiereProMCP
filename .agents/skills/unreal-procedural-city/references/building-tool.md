# Building tool (PCG grammar)

A blueprint actor with a closed **spline component** (the footprint) and a **PCG component** running the building graph. Everything the graph needs comes from data assets referenced by the blueprint; the artist edits the spline and picks a preset.

## Data

See `templates/data-assets.md` for the full structs. In short:

- **Panel kit data asset** (one per architectural style or kit): an array of panels, each with *static mesh*, *panel width*, *grammar symbol*, and booleans that mark interior room points (door, room corner, stair). This is an expanded version of the standard grammar module table.
- **Kit stack**: the building takes an **array** of panel kits. Symbols from all of them are available to its grammar strings, so a building can borrow a storefront from one kit and windows from another. Keep symbols unique across kits that are stacked together (prefix them: `NR_W`, `NR_D`, `IND_W`).
- **Floor style struct**: grammar string per side (front, back, left, right), floor height, and which floor positions it applies to (ground, first decorative tier, middle repeat, upper tier, top).
- **Building preset**: the kit stack, the floor styles, colours, roof style, socket densities and interior layout, saved as a data table row keyed by a **gameplay tag** (see `editor-tools.md`).

## Floor structure

Real buildings of one era share a layout. Model it as tiers:

1. Ground floor: shops or entrance.
2. Lower decorative tier.
3. Repeating middle floors (the only tier that repeats).
4. Upper decorative tier.
5. Roof (see *Dynamic roofs*).

Floors can have different heights; read the height per floor style and stack the Z offsets. Add **horizontal trims** between tiers and **vertical trims** at corners and between bays to cover panels that don't tile cleanly.

## Grammar syntax (checked against the 5.8 docs)

| Syntax | Meaning |
|---|---|
| `A` | place module A |
| `A, B` | place A then B |
| `A*` | place A as many times as fits |
| `A+` | place A at least once, then as many as fits |
| `[A, B]` | a group placed together |
| `[A, B]*` / `[A, B]+` / `[A, B]2` | repeat the group: fill / at least once / exactly twice |
| `<A, B, C>` | priority: A if it fits, otherwise B, then C |
| `{[A,P]:2, [B,P]:1}` | weighted random choice between groups (weights after `:`) |

Strings read left to right along the spline segment. Example facade, with A pillar, B window, C door, D right corner:

```
A, [B, B, C, B, B, A]*, D
```

Pillar at the start, then window-window-door-window-window-pillar repeated as far as the side allows, then the corner piece. Use 90° corner meshes so the corner wraps onto the next side; 45° pieces need the neighbouring side to supply the other half.

Check a grammar before building it: `python3 scripts/grammar_check.py "A,[B,B,C,B,B,A]*,D" --modules A=50 B=150 C=200 D=60 --width 2400`.

## Graph outline

1. **Get Spline Data** (the footprint) → **Clean Spline** (fuse colocated, remove collinear) → **Spline Direction** (*Force Clockwise*, so "outside" is consistent).
2. **Spline To Segment** with *Extract Angles* and *Extract Connectivity Info*: one segment per facade side. Tag each segment with its side (front is the segment facing the street; mark it from the blueprint or the OSM data).
3. For each floor position: copy the segments up by the accumulated floor height, then **Select Grammar** (key = side + floor position) to put the right grammar string on each segment.
4. **Subdivide Segment** with *Grammar As Attribute* and *Module Info as Input*, the module info coming from the kit stack (symbol, size). Turn on *Accept Incomplete Subdivision* only after fixing the grammar: a warning usually means a missing filler module.
5. Match symbols to meshes (attribute set from the kit's data) → **Static Mesh Spawner** with the mesh from the attribute.
6. Trims: a second, simpler grammar per tier line, or a **Spawn Spline Mesh** along the copied segment.

## Panels and Nanite

- Every opaque panel is Nanite.
- Glass is a **separate translucent mesh attached through a socket** on the panel (`SOCKET_Glass`). The graph samples that socket and spawns the glass mesh there, so the panel keeps Nanite.

## Sockets for detail

Tag sockets on panel meshes by category: `SOCKET_Balcony_01`, `SOCKET_Sign_02`, `SOCKET_Bin_01`, `SOCKET_Graffiti_03`, `SOCKET_Door_01`.

- Sample them with PCGEx **Sample : Socket**, which is much faster than reading sockets in Blueprint. Without PCGEx: a **Get Actor Data** on spawned components is slow; instead, store the socket transforms in the kit data asset once (an editor script can extract them) and transform them per point.
- Loop over a **socket data table** (category → meshes, density) and restructure into point data.
- Apply densities as **instance percentages** (a **Density Filter** or random cull per category), then spawn.
- **Local control**: per building, enable categories and set densities.
- **Global control**: a *neighbourhood* data asset overrides densities for a whole zone (more balconies in residential, bins and graffiti in industrial, signs and lights in commercial) with one data change.

## Colour variation (custom primitive data)

1. Colours are parameters on the building blueprint (wall, trim, window frame), or come from the preset.
2. In the graph, write them as point attributes (for example `WallColor` as a vector).
3. On the **Static Mesh Spawner**, set the *Instance Data Packer* to **By Attribute** and list the attributes. They become per-instance custom data.
4. In the material, read them with **PerInstanceCustomData** (one float per index; a colour takes three indices) and lerp or multiply the base colour.

The same channels can drive dirt, damage and decal masks.

## Dynamic roofs

- Roof styles (flat, industrial, pitched…) each have their own PCG placement graph and a Geometry Script modelling function.
- The footprint goes into the roof graph as a **PCG data collection**; through the *PCG Geometry Script Interop* it reaches the blueprint's Geometry Script, which builds the roof as a dynamic mesh.
- The roof is **baked to a static mesh**. When the footprint changes, the tool detects it, rebuilds and throws away the old bake.

## Curved corners

- Don't shape corners with Bézier handles: panels warp.
- Bevel the chosen footprint point with a fixed radius (PCGEx **Path : Bevel**; without PCGEx, replace the corner point with points on an arc in a small Blueprint or Geometry Script function).
- Resample by distance with *Fit to Curve* on, filter the curved part, and spawn it with **Spawn Spline Mesh** so the panels bend along it.

## Hills and slopes

- Use **adaptive panels** on the ground floor: their lower part extends down to the ground (a stretchable base, or a separate plinth mesh scaled per point to the ground hit).
- Entrances must meet the street level: add steps and railings from the same ground trace.
- Decorations that must stay vertical (lamps, railings) use world-up rotation; surfaces that follow the ground use the hit normal.

## Interiors

See `interiors.md`.
