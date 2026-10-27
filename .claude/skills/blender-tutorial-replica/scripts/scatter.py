"""Own scatter system (replaces paid scatter add-ons): geometry-nodes instancing, run inside Blender.

    import scatter
    scatter.scatter(target="ENV_terrain", source_collection="SRC_ferns", name="SCAT_ferns",
                    density=4.0, min_distance=0.3, scale=(0.7, 1.3), seed=1,
                    mask_attribute="ferns_mask", viewport_ratio=0.1, align_to_normal=0.3)

- Instances stay instances (no realize), so hundreds of thousands of plants stay light in memory.
- viewport_ratio shows only a fraction in the viewport; renders always use the full density.
- mask_attribute: name of a float attribute / vertex group on the target (0..1) that scales density;
  paint it, or create it with a geometry-nodes or Python pass (e.g. "not on the path", "on slopes < 30°").
- Each layer (trees, ferns, shrubs, grass, branches, leaves, pebbles) is its own modifier with its own seed.
Safe to rerun: an existing modifier/node group with the same name is rebuilt in place.
"""
import bpy


def _node_group(name):
    ng = bpy.data.node_groups.get(name)
    if ng is None:
        ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.nodes.clear()
    for item in list(ng.interface.items_tree):
        ng.interface.remove(item)
    return ng


def scatter(target, source_collection, name, density=1.0, min_distance=0.0, scale=(0.8, 1.2), seed=0,
            mask_attribute=None, viewport_ratio=0.1, align_to_normal=0.0, max_tilt=0.15):
    tgt = bpy.data.objects[target] if isinstance(target, str) else target
    col = bpy.data.collections[source_collection] if isinstance(source_collection, str) else source_collection

    ng = _node_group("GN_" + name)
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gin, gout = N.new("NodeGroupInput"), N.new("NodeGroupOutput")

    dist = N.new("GeometryNodeDistributePointsOnFaces")
    dist.distribute_method = "POISSON" if min_distance > 0 else "RANDOM"
    dist.inputs["Seed"].default_value = seed
    if min_distance > 0:
        dist.inputs["Distance Min"].default_value = min_distance
        dens_socket = dist.inputs["Density Max"]
    else:
        dens_socket = dist.inputs["Density"]

    # density = base * (viewport ? ratio : 1) [* mask]
    is_vp = N.new("GeometryNodeIsViewport")
    sw = N.new("GeometryNodeSwitch"); sw.input_type = "FLOAT"
    sw.inputs["False"].default_value = density
    sw.inputs["True"].default_value = density * viewport_ratio
    L.new(is_vp.outputs[0], sw.inputs["Switch"])
    L.new(sw.outputs[0], dens_socket)
    if mask_attribute:
        attr = N.new("GeometryNodeInputNamedAttribute"); attr.data_type = "FLOAT"
        attr.inputs["Name"].default_value = mask_attribute
        if min_distance > 0:
            L.new(attr.outputs["Attribute"], dist.inputs["Density Factor"])
        else:
            mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
            L.new(sw.outputs[0], mul.inputs[0]); L.new(attr.outputs["Attribute"], mul.inputs[1])
            L.new(mul.outputs[0], dens_socket)

    # orientation: blend between world-up and the surface normal, random yaw, small random tilt
    align_up = N.new("FunctionNodeAlignEulerToVector"); align_up.axis = "Z"
    mix_n = N.new("ShaderNodeMix"); mix_n.data_type = "VECTOR"
    mix_n.inputs["Factor"].default_value = align_to_normal
    mix_n.inputs["A"].default_value = (0, 0, 1)
    L.new(dist.outputs["Normal"], mix_n.inputs["B"])
    L.new(mix_n.outputs["Result"], align_up.inputs["Vector"])
    yaw = N.new("FunctionNodeRandomValue"); yaw.data_type = "FLOAT_VECTOR"
    yaw.inputs["Min"].default_value = (-max_tilt, -max_tilt, 0)
    yaw.inputs["Max"].default_value = (max_tilt, max_tilt, 6.2832)
    yaw.inputs["Seed"].default_value = seed + 1
    rot = N.new("FunctionNodeRotateEuler")
    L.new(align_up.outputs["Rotation"], rot.inputs[0])
    L.new(yaw.outputs["Value"], rot.inputs[1])

    rnd_s = N.new("FunctionNodeRandomValue"); rnd_s.data_type = "FLOAT"
    rnd_s.inputs["Min"].default_value, rnd_s.inputs["Max"].default_value = scale
    rnd_s.inputs["Seed"].default_value = seed + 2

    info = N.new("GeometryNodeCollectionInfo")
    info.inputs["Collection"].default_value = col
    info.inputs["Separate Children"].default_value = True
    info.inputs["Reset Children"].default_value = True
    inst = N.new("GeometryNodeInstanceOnPoints")
    inst.inputs["Pick Instance"].default_value = True
    rnd_i = N.new("FunctionNodeRandomValue"); rnd_i.data_type = "INT"
    rnd_i.inputs["Min"].default_value, rnd_i.inputs["Max"].default_value = 0, max(0, len(col.all_objects) - 1)
    rnd_i.inputs["Seed"].default_value = seed + 3

    join = N.new("GeometryNodeJoinGeometry")
    L.new(gin.outputs["Geometry"], dist.inputs["Mesh"])
    L.new(dist.outputs["Points"], inst.inputs["Points"])
    L.new(info.outputs["Instances"], inst.inputs["Instance"])
    L.new(rnd_i.outputs["Value"], inst.inputs["Instance Index"])
    L.new(rot.outputs[0], inst.inputs["Rotation"])
    L.new(rnd_s.outputs["Value"], inst.inputs["Scale"])
    L.new(gin.outputs["Geometry"], join.inputs["Geometry"])
    L.new(inst.outputs["Instances"], join.inputs["Geometry"])
    L.new(join.outputs["Geometry"], gout.inputs["Geometry"])

    mod = tgt.modifiers.get(name) or tgt.modifiers.new(name, "NODES")
    mod.node_group = ng
    col.hide_render = True          # the source objects themselves must not render
    col.hide_viewport = False
    return mod


def instance_count(obj):
    """Count instances currently produced on obj (viewport density in the UI, render density in background renders)."""
    deps = bpy.context.evaluated_depsgraph_get()
    return sum(1 for inst in deps.object_instances if inst.is_instance and inst.parent and inst.parent.original == obj)
