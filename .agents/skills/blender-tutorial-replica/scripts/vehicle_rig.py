"""Own vehicle rig (no third-party rig add-ons): drives a car along a path with baked keyframes.

    import vehicle_rig
    vehicle_rig.bake(body="CAR_body", wheels={"FL": "CAR_wheel_FL", "FR": "CAR_wheel_FR",
                     "RL": "CAR_wheel_RL", "RR": "CAR_wheel_RR"}, path="PATH_road",
                     frame_start=1, frame_end=390, speed_kmh=40, wheel_radius=0.33,
                     wheelbase=2.45, bounce=0.012)

Everything is baked to keyframes (no drivers), so motion blur, render farms and other machines see
exactly the same motion. Per frame:
  - root follows the path at the given speed (eased in/out), heading = path tangent
  - wheels spin by distance / radius  (radians), around their local X axis
  - front wheels steer by atan(wheelbase * curvature), clamped to ±35°
  - body bounces and rolls with a smooth deterministic noise scaled by speed (gravel)
Wheels spin around their own local X axis in their rest orientation (set axle="Y"/"Z" if the
wheel was modelled differently). Steering turns around the car's up axis. Parenting is done by bake().
"""
import math

import bpy
from mathutils import Matrix, Vector


def _polyline(path_obj, resolution=64):
    # sample the curve finely (temporarily raise its resolution) so curvature isn't quantised per segment
    old = path_obj.data.resolution_u
    path_obj.data.resolution_u = max(old, resolution)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = path_obj.evaluated_get(deps)
    mesh = ev.to_mesh()
    pts = [path_obj.matrix_world @ v.co for v in mesh.vertices]
    ev.to_mesh_clear()
    path_obj.data.resolution_u = old
    if len(pts) < 2:
        raise ValueError("path has no geometry")
    # order follows the curve's vertex order; resample to even arc length
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    return pts, cum


def _sample(pts, cum, d):
    d = max(0.0, min(d, cum[-1]))
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= d:
            lo = mid
        else:
            hi = mid
    seg = cum[hi] - cum[lo] or 1e-9
    t = (d - cum[lo]) / seg
    return pts[lo].lerp(pts[hi], t), (pts[hi] - pts[lo]).normalized()


def _noise(x, seed):
    return (math.sin(x * 1.7 + seed) * 0.5 + math.sin(x * 3.1 + seed * 2.3) * 0.3
            + math.sin(x * 7.3 + seed * 0.7) * 0.2)


def _ease(u):
    return u * u * (3 - 2 * u)


def bake(body, wheels, path, frame_start=1, frame_end=250, speed_kmh=30.0, wheel_radius=0.33,
         wheelbase=2.5, bounce=0.01, ease_frames=24, seed=7, root_name="RIG_car", axle="X"):
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    body_o = bpy.data.objects[body]
    wheel_o = {k: bpy.data.objects[v] for k, v in wheels.items()}
    path_o = bpy.data.objects[path]
    pts, cum = _polyline(path_o)

    root = bpy.data.objects.get(root_name)
    if root is None:
        root = bpy.data.objects.new(root_name, None)
        scene.collection.objects.link(root)
    root.animation_data_clear()
    for o in [body_o, *wheel_o.values()]:
        o.animation_data_clear()
        if o.parent != root:
            mw = o.matrix_world.copy()
            o.parent = root
            o.matrix_parent_inverse = root.matrix_world.inverted()
            o.matrix_world = mw
    rest = {k: o.rotation_euler.to_matrix() for k, o in wheel_o.items()}
    prev_eul = {k: o.rotation_euler.copy() for k, o in wheel_o.items()}
    body_rest = (body_o.location.copy(), body_o.rotation_euler.copy())

    v = speed_kmh / 3.6
    n = frame_end - frame_start
    dist = 0.0
    prev_heading = None
    for i in range(n + 1):
        f = frame_start + i
        # eased speed profile: accelerate over ease_frames at start, decelerate at end
        k = min(1.0, _ease(min(i, ease_frames) / max(ease_frames, 1)), _ease(min(n - i, ease_frames) / max(ease_frames, 1)))
        if i > 0:
            dist += v * k / fps
        pos, tan = _sample(pts, cum, dist)
        heading = math.atan2(tan.y, tan.x) - math.pi / 2          # car forward = +Y
        root.location = pos
        root.rotation_euler = (0, 0, heading)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)

        # curvature = heading change per metre over a window around the car (wheelbase-sized)
        win = max(wheelbase, 2.0)
        _, t_a = _sample(pts, cum, dist - win / 2)
        _, t_b = _sample(pts, cum, dist + win / 2)
        dh = math.atan2(t_b.y, t_b.x) - math.atan2(t_a.y, t_a.x)
        dh = (dh + math.pi) % (2 * math.pi) - math.pi
        steer = max(-0.61, min(0.61, math.atan(wheelbase * dh / win)))   # bicycle model

        spin = -dist / wheel_radius
        for key, o in wheel_o.items():
            m = rest[key] @ Matrix.Rotation(spin, 3, axle)                 # spin around the axle
            if key.upper().startswith("F"):
                m = Matrix.Rotation(steer, 3, "Z") @ m                    # steer around car up
            eul = m.to_euler("XYZ", prev_eul[key])                        # continuous, no flips
            prev_eul[key] = eul
            o.rotation_euler = eul
            o.keyframe_insert("rotation_euler", frame=f)

        amp = bounce * min(1.0, v * k / 8.0)
        x = dist * 2.0
        body_o.location = body_rest[0] + Vector((0, 0, amp * _noise(x, seed)))
        body_o.rotation_euler = (body_rest[1].x + amp * 1.5 * _noise(x + 11, seed),
                                 body_rest[1].y + amp * 2.0 * _noise(x + 23, seed) - steer * 0.02 * k,
                                 body_rest[1].z)
        body_o.keyframe_insert("location", frame=f)
        body_o.keyframe_insert("rotation_euler", frame=f)

    # unwrap heading so the root never spins 360° between keys
    for fc in root.animation_data.action.fcurves if hasattr(root.animation_data.action, "fcurves") else []:
        if fc.data_path == "rotation_euler" and fc.array_index == 2:
            prev = None
            for kp in fc.keyframe_points:
                if prev is not None:
                    while kp.co.y - prev > math.pi:
                        kp.co.y -= 2 * math.pi
                    while kp.co.y - prev < -math.pi:
                        kp.co.y += 2 * math.pi
                prev = kp.co.y
    return {"distance_m": dist, "path_length_m": cum[-1], "frames": n + 1}
