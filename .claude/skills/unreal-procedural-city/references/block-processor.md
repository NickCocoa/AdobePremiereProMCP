# Block processor (PCG + Geometry Script)

Generates a city block from its **boundary spline**. The block is drawn first; the road is whatever is left between blocks (see `roads-and-markings.md`). This handles both regular grids (Chicago) and organic layouts (Liverpool) without special intersection code.

## Actor

- A blueprint with a **spline component** (block boundary), a **Dynamic Mesh Component** (sidewalk surface, road-line meshes) and a **PCG component** (curbs, street furniture, decals).
- **Not** the *Generated Dynamic Mesh Actor* class: it rebuilds on every move, like a second construction script. Rebuilds happen only when the widget's *Generate* button is pressed.
- In Class Settings, untick **Run Construction Script on Drag**.
- After baking, the dynamic mesh becomes a static mesh actor, but **keep the spline** so the block shape stays editable and can be re-baked.

## Straight and curved data

1. Sample the boundary and split it into **straight** and **curved** sets by curvature (angle between neighbouring segments from **Spline To Segment** with *Extract Angles*, then a filter on the angle).
2. Straight sets: curbs, railings, lamp posts and drains at intervals, decal actors.
3. Curved sets: curved curb pieces with **Spawn Spline Mesh**.
4. Pass the same sets as PCG data into the dynamic mesh component (Geometry Script interop) to build the road-line meshes.

## Sidewalk surface

Geometry Script in the blueprint:

1. Polygon from the spline points → **Append Simple Extruded Polygon** (or triangulate a polygon list) for the sidewalk slab.
2. Inset for the curb edge if the curb is part of the mesh.
3. UVs: planar projection in world space so textures line up across blocks.
4. Low-resolution remesh if it will be booleaned or snapped next.

## Material spline cuts

A small blueprint with a spline and a material slot. Artists draw regions on a block or road tile: paving changes, painted areas, damage.

1. Each cut spline becomes a polygon mesh.
2. **Boolean intersect** it against the base surface to cut the shape into the mesh.
3. Assign the cut's material to the intersected triangles (material ID per region).
4. The same spline drives a **trim** (tar lines, kerb trim sheet) along the cut edge.
5. **Remesh** the surface to clean the topology.
6. Trim decals are **ray-cast down** onto the surface and baked as a separate mesh.

## Cutouts (subways, tunnels, points of interest)

- The object to cut (a subway entrance blueprint) holds a **tagged volume** (for example a box component tagged `BlockCut`) that defines the cut.
- The block gathers every tagged volume that overlaps it, turns each into a mesh, stores them in an array and **boolean subtracts** them from its dynamic mesh.
- Move the subway, re-bake the block, and the hole follows. The level stays playable.
- If booleans give bad topology, raise triangle density with a **low-resolution remesh** of the source first.

## Debugging Geometry Script

Allocate a **compute mesh** at chosen stages behind a debug toggle, append the intermediate result to it (for example the boolean cutter box) and look at it in the viewport. A cutter at the block's origin instead of the subway's means the wrong transform went in. Release compute meshes when done.

## Curb blending

After `road − block` booleans, the new edge loop is exactly where curb meets road. Paint **vertex colours** along those edges and use them in the material to blend world-space dirt, litter and damage masks right at the contact line.

## Editor flow (Generate Selected)

1. Clean up any existing procedural data for the selection.
2. For each selected block:
   - If it's already a baked static mesh: destroy the static mesh, spawn a temporary dynamic mesh and apply the procedural logic.
   - If it's dynamic: just apply the procedural logic.
3. Finalise: convert the dynamic mesh to a static mesh asset and save it, destroy temporary actors, final PCG cleanup.

`scripts/unreal/bake_dynamic_meshes.py` does the convert-and-swap step.
