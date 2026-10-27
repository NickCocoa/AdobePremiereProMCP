"""Bake the selected actors' dynamic meshes to static mesh assets.

  py "C:/path/bake_dynamic_meshes.py" --dest /Game/City/Baked
  py "C:/path/bake_dynamic_meshes.py" --dest /Game/City/Baked --overwrite

* A plain Dynamic Mesh Actor is replaced by a Static Mesh Actor at the same transform.
* A tool blueprint (block, tile, roof) that has a Static Mesh Component tagged `Baked`
  keeps its spline: the baked mesh goes into that component and the dynamic mesh is
  cleared, so the shape can be edited and baked again later.
Existing assets are only replaced with --overwrite, after a confirmation dialog.
Needs the Geometry Script plugin (and Editor Scripting Utilities).
"""
import argparse
import sys

import unreal

sys.path.append(__import__("os").path.dirname(__file__))
from _ue_common import actor_subsystem, components, log, selected_actors  # noqa: E402


def new_asset_lib():
    for name in ("GeometryScript_NewAssetUtils", "GeometryScript_AssetUtils"):
        lib = getattr(unreal, name, None)
        if lib and hasattr(lib, "create_new_static_mesh_asset_from_mesh"):
            return lib
    raise RuntimeError("Geometry Script asset functions not found: enable the Geometry Script plugin")


def bake_mesh(dyn_mesh, asset_path):
    opts = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    for prop, value in (("enable_recompute_normals", False), ("enable_recompute_tangents", False),
                        ("enable_nanite", True)):
        try:
            opts.set_editor_property(prop, value)
        except Exception:
            pass
    result = new_asset_lib().create_new_static_mesh_asset_from_mesh(dyn_mesh, asset_path, opts)
    mesh = result[0] if isinstance(result, (tuple, list)) else result
    if mesh is None:
        raise RuntimeError(f"bake failed for {asset_path}")
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    return mesh


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="/Game/City/Baked")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    actors = [a for a in selected_actors() if components(a, unreal.DynamicMeshComponent)]
    if not actors:
        unreal.EditorDialog.show_message("City tools", "Select actors with a dynamic mesh to bake.",
                                         unreal.AppMsgType.OK)
        return

    paths = {a: f"{args.dest}/SM_{a.get_actor_label()}" for a in actors}
    existing = [p for p in paths.values() if unreal.EditorAssetLibrary.does_asset_exist(p)]
    if existing:
        if not args.overwrite:
            unreal.log_warning(f"{len(existing)} baked asset(s) already exist; rerun with --overwrite to replace them")
            actors = [a for a in actors if paths[a] not in existing]
        else:
            answer = unreal.EditorDialog.show_message(
                "City tools", f"Overwrite {len(existing)} existing baked mesh(es)?", unreal.AppMsgType.YES_NO)
            if answer != unreal.AppReturnType.YES:
                return
            for p in existing:
                unreal.EditorAssetLibrary.delete_asset(p)

    baked = 0
    for actor in actors:
        dmc = components(actor, unreal.DynamicMeshComponent)[0]
        mesh = bake_mesh(dmc.get_dynamic_mesh(), paths[actor])
        target = [c for c in components(actor, unreal.StaticMeshComponent) if c.component_has_tag("Baked")]
        if target:
            target[0].set_static_mesh(mesh)
            dmc.get_dynamic_mesh().reset()
        else:
            sm_actor = actor_subsystem().spawn_actor_from_class(
                unreal.StaticMeshActor, actor.get_actor_location(), actor.get_actor_rotation())
            sm_actor.set_actor_scale3d(actor.get_actor_scale3d())
            sm_actor.static_mesh_component.set_static_mesh(mesh)
            sm_actor.set_actor_label(actor.get_actor_label())
            sm_actor.set_folder_path(actor.get_folder_path())
            actor_subsystem().destroy_actor(actor)
        baked += 1
    log(f"baked {baked} actor(s) to {args.dest}")


main(sys.argv[1:])
