# Interiors

One procedural solution for every interior gets fragile. Split the job: work out the room layout from data, then fill each room with a small pre-made **room subgraph**.

## Room data from panels

1. Panels in the kit carry booleans for interior points (room corner, door, wall break). The building graph emits those points with the panel's floor and side.
2. Resolve the room shapes from those points. Most buildings are **residential** or **commercial** layouts; start with those two.
3. Give every room a **unique ID** (floor index × 100 + room index works).
4. A **room spaces** struct array on the building maps room IDs to pre-made PCG room graphs (bar, office, shop floor, flat), assigned in order or at random with a seed.
5. Interior walls can follow **world** or **local** space; pick per building.
6. Footprint changes update the interior spline layout automatically. Save good layouts as part of the building preset.

## Simple interior recipe (nine nodes)

The core of every room graph is moving PCG points around:

1. **Get Spline Data** on the room or building spline.
2. **Spline Sampler**, default settings: the spline's points (plus subdivisions).
3. **Spline Sampler** with *Dimension* set to **On Interior**: points filling the room. Use them for tables, chairs, pillars.
4. **Point Filter** (for example by index, keeping index 0 on one output and the rest on the other) to pick individual corners.
5. **Merge** two chosen points → **Create Spline** → **Spline Sampler** by distance with **Fit to Curve** on (points spread evenly). That line is a wall run. Repeat per side if each wall differs.
6. Offset copies of the same points (**Transform Points**) for wall lights, booths, the bar counter; sample the bar again for stools.

Spawning, by type:

| Node | For |
|---|---|
| **Static Mesh Spawner** | plain meshes: stools, tables, clutter |
| **Spawn Actor** | blueprints: lights, interactive doors |
| **Spawn Spline Mesh** | meshes that bend along a spline: counters, curved walls |

## Floors the player can't enter

Use an **interior parallax (interior mapping) material** on the windows instead of geometry. It fakes a room behind the glass that shifts with the camera, for almost no cost. Vary the room texture per window with a custom primitive data index.
