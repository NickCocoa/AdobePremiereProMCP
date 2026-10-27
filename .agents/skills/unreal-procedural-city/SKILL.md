---
name: unreal-procedural-city
description: Build procedural cities in Unreal Engine 5.8 or newer with PCG and Geometry Script, following the Lucid Games workflow from Unreal Fest Chicago 2026 ("Procedural Cities for Tech Artists"). Covers grammar-based buildings from spline footprints (stackable panel kits in data assets, per-side floor styles, sockets, colour via custom primitive data, Nanite-safe glass, dynamic roofs, curved corners), procedural and parallax interiors, a block-first city block processor (sidewalks, curbs, street furniture, material spline cuts, boolean cutouts), a tiled road manager, road markings, snap-to-ground on landscapes, OpenStreetMap footprints, presets driven by gameplay tags, and Editor Utility Widget tooling. Use when the user wants a city, street, block, building generator, facade, PCG grammar, road network, OSM import or PCG/Geometry Script tool in Unreal.
---

# Unreal procedural city (UE 5.8+)

The workflow from Lucid Games' talk [Procedural Cities for Tech Artists: Geometry Scripting & PCG](https://www.youtube.com/watch?v=7uuFPOKIw8I), turned into steps Claude can follow and scripts it can run. Everything stays inside Unreal: no Houdini, and as few steps as possible for the artist using the tool.

## Requirements

- **Unreal Engine 5.8 or newer.** The grammar syntax and node names here were checked against the 5.8 docs. Node names can move between versions: if a node is missing, search the PCG palette for the words in its name before building a workaround.
- **Plugins** (Edit → Plugins): *Procedural Content Generation Framework (PCG)*, *PCG Geometry Script Interop*, *Geometry Script*, *Editor Scripting Utilities*, *Python Editor Script Plugin*. Optional: *PCGEx* (PCG Extended Toolkit, free on Fab/GitHub) for bevel, socket sampling and path-finding nodes. Without PCGEx, see the fallbacks in the references.
- Ship the tools as **one project plugin** (Content + Source) so they move between projects and get improved over time instead of being rebuilt per project.

## The five tools and their order

Build them in this order. Each one is useful on its own.

| # | Tool | What it makes | Reference |
|---|---|---|---|
| 1 | **Building tool** (PCG grammar) | Buildings from a closed spline footprint: panels per floor and side, trims, sockets, colours, roof, interiors | `references/building-tool.md`, `references/interiors.md` |
| 2 | **Block processor** (PCG + Geometry Script) | A city block from its boundary spline: sidewalk mesh, curbs, lamps, drains, railings, decals, material cuts, cutouts | `references/block-processor.md` |
| 3 | **World tiles / road manager** | A grid of dynamic-mesh road tiles with the blocks boolean-subtracted out, baked per tile | `references/roads-and-markings.md` |
| 4 | **Road markings** | Lane lines, chevrons, crosshatch boxes as meshes from PCG data collections | `references/roads-and-markings.md` |
| 5 | **Editor Utility Widget** | Generate, bake, refresh, presets, random styles, all in one panel | `references/editor-tools.md` |

Then feed it data: hand-drawn splines, or OpenStreetMap footprints (`scripts/osm_to_footprints.py`).

## How to work

1. **Ask for the target.** City type (grid like Chicago, or organic like Liverpool), era and style of the buildings, flat or hilly, playable interiors or not, which assets exist. Don't build all five tools when the user needs one street.
2. **Plan the data before the graphs.** Write the data assets and structs first (`templates/data-assets.md`): panel kits, floor styles, building presets, socket tables, room graphs. Every later choice reads from these.
3. **Write grammars and test them offline** with `scripts/grammar_check.py` before touching the editor: it parses a grammar string, fills a facade width with your module widths and shows what PCG would place, including leftover gaps.
4. **Build one graph at a time** in the editor and check each in the viewport. Turn on PCG debug display on the nodes you're testing.
5. **Profile early.** Open the PCG profiler (Window → PCG Profiling, or the profiling panel in the PCG editor) once a graph works on one building. Then run it on a full street before scaling up (`references/performance.md`).
6. **Bake, don't keep live.** Dynamic meshes are baked to static meshes from the editor widget, so nothing generates at runtime (`scripts/unreal/bake_dynamic_meshes.py`).
7. **Talk to the end user** (environment artists, level designers) after each tool. A tool they don't reach for is a failed tool, however clever.

## Rules that save the most time

- **Block first, roads second.** Draw the block boundary; derive the road from what's left. Road-first tools break on irregular intersections.
- **Kits, not buildings.** A small library of interchangeable panels per architectural style, stacked from several data assets, beats a unique asset per building. Expect thousands of buildings from tens of panels.
- **Grammar strings live in data**, per side and per floor position, so the front can be decorative and the back plain.
- **Colour and wear through custom primitive data** (the Instance Data Packer on the Static Mesh Spawner), not extra material instances.
- **Nanite on everything opaque.** Glass is a separate mesh attached by socket, so the panel stays Nanite.
- **Turn off "Run Construction Script on Drag"** on every spline blueprint that drives PCG or Geometry Script (Class Settings), or the editor locks up while you drag spline points.
- **Avoid the Generated Dynamic Mesh Actor class** for heavy tools: it rebuilds on every move. Use a plain Dynamic Mesh Actor or component and rebuild from a button.
- **Remesh around booleans**: a low-resolution remesh before a boolean or snap, and a remesh after to clean shards.
- **Snap with a low-poly pass first**: remesh low, line-trace every vertex down, then remesh higher.
- **Ask before overwriting**: every destructive button in the widget shows a confirm dialog.
- **Flush the PCG cache** (`pcg.FlushCache`) before a refresh so stale data doesn't leak into the regenerated building.

## Scripts

| Script | Where it runs | What it does |
|---|---|---|
| `scripts/grammar_check.py` | Any Python 3 | Parses a PCG grammar string and simulates filling a width with module sizes; reports placements and the unfilled remainder; `--print-tree` like the Print Grammar node |
| `scripts/osm_to_footprints.py` | Any Python 3 | Turns Overpass JSON or GeoJSON into closed footprint loops in Unreal centimetres (X east, Y south), with height, levels and a style key per building, plus road centrelines |
| `scripts/unreal/spawn_footprints.py` | Unreal Python | Spawns your building blueprint per footprint, sets its spline, assigns a preset tag by style and generates |
| `scripts/unreal/regenerate_selected.py` | Unreal Python | Flushes the PCG cache and regenerates the PCG components on the selected actors; `--random-preset` assigns a random style first |
| `scripts/unreal/bake_dynamic_meshes.py` | Unreal Python | Bakes the selected actors' dynamic meshes to static mesh assets and swaps the actors, keeping their splines |
| `tests/test_tools.py` | Any Python 3 | Tests for the two offline scripts |

Run the Unreal scripts from the editor's Python console (`py "path/to/script.py" --args`) or from an Editor Utility Widget button through *Execute Python Script*. They need the Python Editor Script Plugin. They have not been run in Unreal by the skill's author: run them on a test level first and read what they print.

## What this skill doesn't do

- It doesn't create `.uasset` graphs or blueprints for you. It gives exact node chains and settings to build them, and scripts to drive them once they exist.
- It doesn't replace World Partition streaming setup, HLODs, or gameplay logic for interiors.
