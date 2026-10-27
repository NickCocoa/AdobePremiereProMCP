"""Spawn a building blueprint per footprint from osm_to_footprints.py output.

Run in Unreal Editor (Python Editor Script Plugin):

  py "C:/path/spawn_footprints.py" --json C:/data/footprints.json \
     --blueprint /Game/City/Buildings/BP_Building \
     --styles commercial=City.Buildings.Commercial residential=City.Buildings.Residential \
              industrial=City.Buildings.Industrial generic=City.Buildings.Generic \
     --limit 200

Contract with the building blueprint (adjust names with the flags):
  * one closed Spline Component (the footprint), points set here in local space;
  * a Blueprint-callable function `ApplyPresetByName(Name)` that turns the style string
    into its preset gameplay tag (Request Gameplay Tag) and applies the preset;
  * optional float variables `Height` (cm) and int `Floors`;
  * a PCG component, regenerated after setup.
Actors are put in the folder given by --folder so they are easy to select or delete.
"""
import argparse
import json
import sys

import unreal

sys.path.append(__import__("os").path.dirname(__file__))
from _ue_common import actor_subsystem, call_if_present, components, generate_pcg, log  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--blueprint", required=True, help="content path of the building blueprint")
    ap.add_argument("--styles", nargs="*", default=[], metavar="STYLE=TAG")
    ap.add_argument("--preset-function", default="ApplyPresetByName")
    ap.add_argument("--folder", default="City/Buildings")
    ap.add_argument("--z", type=float, default=0.0, help="ground height in cm")
    ap.add_argument("--limit", type=int, default=0, help="spawn at most N (0 = all)")
    ap.add_argument("--no-generate", action="store_true")
    args = ap.parse_args(argv)

    style_tags = dict(s.split("=", 1) for s in args.styles)
    with open(args.json, encoding="utf-8") as fh:
        data = json.load(fh)
    buildings = data["buildings"][: args.limit or None]

    cls = unreal.EditorAssetLibrary.load_blueprint_class(args.blueprint)
    if cls is None:
        raise RuntimeError(f"blueprint not found: {args.blueprint}")

    spawned = 0
    with unreal.ScopedSlowTask(len(buildings), "Spawning buildings") as task:
        task.make_dialog(True)
        for b in buildings:
            if task.should_cancel():
                break
            task.enter_progress_frame(1)
            pts = b["points"]
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            actor = actor_subsystem().spawn_actor_from_class(
                cls, unreal.Vector(cx, cy, args.z), unreal.Rotator(0, 0, 0))
            if actor is None:
                continue
            actor.set_folder_path(args.folder)
            actor.set_actor_label(f"Building_{b.get('id') or spawned}")

            splines = components(actor, unreal.SplineComponent)
            if not splines:
                unreal.log_warning(f"{args.blueprint} has no spline component")
                actor_subsystem().destroy_actor(actor)
                return
            spline = splines[0]
            local = [unreal.Vector(p[0] - cx, p[1] - cy, 0.0) for p in pts]
            spline.set_spline_points(local, unreal.SplineCoordinateSpace.LOCAL, True)
            for i in range(len(local)):
                spline.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
            spline.set_closed_loop(True, True)

            for prop, value in (("Height", b.get("height_cm")), ("Floors", b.get("levels"))):
                if value is not None:
                    try:
                        actor.set_editor_property(prop, value)
                    except Exception:
                        pass

            tag = style_tags.get(b.get("style", "generic")) or style_tags.get("generic")
            if tag:
                call_if_present(actor, args.preset_function, tag)
            if not args.no_generate:
                generate_pcg(actor)
            spawned += 1

    log(f"spawned {spawned} of {len(buildings)} buildings from {args.json}")


main(sys.argv[1:])
