# Roads, world tiles, markings and snapping

## World tiles manager

- An editor tool (run from the widget) that lays a **grid of dynamic mesh actors** over the city, with attributes (tile index, bounds, road material set).
- Each tile has its own **Bake** button.
- Baking a tile:
  1. Fetch all blocks in the scene and keep those inside or overlapping the tile bounds (plus a margin).
  2. Start from the tile's flat (or snapped) road surface.
  3. **Boolean subtract** each block's footprint mesh from it.
  4. **Remesh** to remove shards and slivers from the booleans; good topology matters for shading, materials and physics.
  5. Bake to a static mesh, destroy the dynamic mesh.
- Change a block, re-bake only the tiles it touches.

## Snap to ground

Roads, blocks and markings conform to the landscape or a world tile:

1. **Remesh low** (keep the vertex count small so the traces are fast).
2. For each vertex, **line trace straight down**, then set the vertex position to the hit point.
3. **Remesh again** at higher density to restore detail and smooth the result.

Local versus world space: curbs and the surface follow the ground; railings and street lights stay **upright in world space**. With a rotated or hilly landscape, decide this per asset.

The landscape can be hand-sculpted or real elevation data, so cities on hills work.

## Road markings

Lane lines, chevrons, yellow crosshatch boxes and other large markings are generated, not placed by hand:

1. Build the marking splines in PCG. For chevrons on a freeway split, PCGEx path-finding nodes can find the closed **convex boundaries** between lane splines; that gives the centre piece.
2. Pack the shapes into a **PCG data collection** and pass it to the dynamic mesh blueprint through the *PCG Geometry Script Interop*.
3. In Geometry Script: triangulate, assign materials, UVs and attributes.
4. **Snap to ground**, then bake to a static mesh.

Run it from the widget like every other tool.

## OpenStreetMap

- Read roads, building footprints and their attributes (height, levels, building type) and feed them to the tools.
- `scripts/osm_to_footprints.py` turns Overpass JSON or GeoJSON into footprints in Unreal centimetres; `scripts/unreal/spawn_footprints.py` spawns a building per footprint with a preset chosen by style.
- Get data with the Overpass API (for example `way["building"](bbox);out geom;`) or export from openstreetmap.org. OSM data is © OpenStreetMap contributors under the ODbL: credit it in the project.
