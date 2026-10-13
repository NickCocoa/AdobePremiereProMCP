"""
VAKTSKIFTET / THE HANDOVER — location build
Varemottaket, Nordvik Distribusjon · regionlager · 05:38

Builds the goods-in bay set: shell, racking, roller door, work table,
notice wall with the episode's poster, floor markings, the lighting rig,
proxy figures and the four cameras of beat 1.

Run from Blender's Scripting tab, or headless:
    blender --background --python build_set.py -- --save out.blend

Verified against Blender 5.2 LTS (bpy 5.2.2). Written defensively for 4.x.

Units are metres. Z is up. World origin sits at the centre of the floor.
Looking from above: +X east, +Y north. The roller door is in the south
wall, the notice wall and the work table are on the west wall.

    N  +Y
         ┌──────────────────────────┐
         │                    ░░░░░ │  ░ = pallet racking
    W −X │ ▓                  ░░░░░ │ +X E
         │ ▓ = notice wall     ░░░░ │
         │ ▭ = work table           │
         └──────────▓▓▓─────────────┘
    S  −Y          roller door
"""

import bpy
import bmesh
import math
import mathutils
import sys

# ─────────────────────────────────────────────────────────────────────
# Set dimensions — change these and everything else follows
# ─────────────────────────────────────────────────────────────────────

ROOM_X = 14.0          # east-west
ROOM_Y = 10.0          # north-south
ROOM_Z = 6.0           # floor to ceiling
WALL_T = 0.25          # wall thickness

DOOR_W = 4.50          # roller door opening width
DOOR_H = 4.50          # roller door opening height
DOOR_OPEN_Z = 2.30     # curtain hangs to this height: "half open"

RACK_DEPTH = 1.20
RACK_H = 5.20
RACK_BAY = 2.80        # upright spacing
BEAM_LEVELS = [0.15, 1.85, 3.50, 5.00]

TABLE_L = 2.40         # runs along Y against the west wall
TABLE_D = 0.80
TABLE_H = 0.90

# The notice wall. The poster is the episode's object: everything in
# beat 1 happens because it is on his path from the door to the table.
NOTICE_X = -ROOM_X / 2 + 0.02
NOTICE_Y0, NOTICE_Y1 = 0.20, 3.00
NOTICE_Z0, NOTICE_Z1 = 1.25, 2.15

POSTER_POS = (-ROOM_X / 2 + 0.025, 1.15, 1.78)   # sits proudly on top
POSTER_W, POSTER_H = 0.420, 0.297                # A3 landscape
POSTER_INDEX = 10                                # cryptomatte / object ID

VEST_INDEX = 11
DOOR_INDEX = 12

FPS = 25
SHOT_FRAMES = 125      # 5 seconds, the restyle window
RES_X, RES_Y = 1920, 1080


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in [bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.objects]:
        for item in list(coll):
            try:
                coll.remove(item)
            except Exception:
                pass
    for c in list(bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.unlink(c)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    bpy.context.scene.timeline_markers.clear()


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def put(obj, coll):
    """Move obj into coll, unlinking it from everywhere else."""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def _use_nodes(datablock):
    """use_nodes is required in 4.x and slated for removal in 6.0."""
    try:
        datablock.use_nodes = True
    except Exception:
        pass


def set_input(node, names, value):
    """Set the first input that exists. Principled socket names moved in 4.0."""
    if isinstance(names, str):
        names = [names]
    for n in names:
        if n in node.inputs:
            try:
                node.inputs[n].default_value = value
                return True
            except Exception:
                pass
    return False


def material(name, rgb, roughness=0.75, metallic=0.0):
    """Flat Principled material. Correct albedo values matter; finish does not —
    the restyle pass overwrites surface detail but preserves luminance."""
    mat = bpy.data.materials.new(name)
    _use_nodes(mat)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        set_input(bsdf, "Base Color", (*rgb, 1.0))
        set_input(bsdf, "Roughness", roughness)
        set_input(bsdf, "Metallic", metallic)
        set_input(bsdf, ["Specular IOR Level", "Specular"], 0.35)
    return mat


def emissive(name, rgb, strength):
    mat = bpy.data.materials.new(name)
    _use_nodes(mat)
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def box(name, size, loc, mat=None, rot=(0, 0, 0)):
    """Axis-aligned box. size is the full extent in (x, y, z)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (size[0], size[1], size[2])   # cube primitive extent is 1.0
    ob.rotation_euler = rot
    if mat:
        ob.data.materials.append(mat)
    return ob


def plane(name, w, h, loc, rot=(0, 0, 0), mat=None):
    """Flat quad of width w (local X) and height h (local Y)."""
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (w, h, 1.0)
    ob.rotation_euler = rot
    if mat:
        ob.data.materials.append(mat)
    return ob


def wall_sheet(name, width, height, loc, roll_deg=0.0, mat=None):
    """A sheet hung flat on the west wall, facing east (+X).

    width runs along the wall (world Y), height is vertical (world Z).
    Rotating a plane 90 degrees about Y sends its local X to world -Z, so the
    arguments have to be swapped going in or every sheet comes out on its side.
    """
    ob = plane(name, height, width, loc,
               rot=(0, math.radians(90), math.radians(roll_deg)), mat=mat)
    return ob


def cyl(name, r, depth, loc, mat=None, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth,
                                        location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_euler = rot
    if mat:
        ob.data.materials.append(mat)
    return ob


def look_at(cam, target, roll_deg=0.0):
    """Aim a camera, with optional roll so the frame sits slightly off-level."""
    loc = mathutils.Vector(cam.location)
    direction = mathutils.Vector(target) - loc
    quat = direction.to_track_quat("-Z", "Y")
    if roll_deg:
        roll = mathutils.Quaternion((0.0, 0.0, 1.0), math.radians(roll_deg))
        quat = quat @ roll
    cam.rotation_euler = quat.to_euler()


# ─────────────────────────────────────────────────────────────────────
# Materials
# ─────────────────────────────────────────────────────────────────────

def build_materials():
    return {
        "concrete":  material("MAT_concrete_floor", (0.175, 0.172, 0.168), 0.88),
        "wall":      material("MAT_wall_block", (0.345, 0.345, 0.330), 0.90),
        "ceiling":   material("MAT_ceiling_deck", (0.200, 0.205, 0.210), 0.85),
        "steel":     material("MAT_rack_steel", (0.200, 0.215, 0.240), 0.55, 0.60),
        "rackbeam":  material("MAT_rack_beam", (0.330, 0.175, 0.090), 0.60, 0.30),
        "galv":      material("MAT_door_galvanised", (0.300, 0.305, 0.315), 0.48, 0.70),
        "table":     material("MAT_table_scuffed", (0.245, 0.235, 0.215), 0.80),
        # The old notices are deliberately dingy so the new laminated sheet
        # separates from them without being lit differently.
        "paper":     material("MAT_notice_paper", (0.330, 0.322, 0.295), 0.88),
        "laminate":  material("MAT_poster_laminate", (0.930, 0.930, 0.925), 0.12),
        "yellow":    material("MAT_floor_marking", (0.420, 0.345, 0.095), 0.92),
        "vest":      material("MAT_hivis_vest", (0.620, 0.230, 0.030), 0.78),
        "workwear":  material("MAT_workwear_navy", (0.055, 0.070, 0.115), 0.84),
        "skin":      material("MAT_proxy_skin", (0.330, 0.255, 0.215), 0.70),
        "pallet":    material("MAT_pallet_wood", (0.280, 0.215, 0.140), 0.88),
        "wrap":      material("MAT_pallet_wrap", (0.520, 0.540, 0.530), 0.40),
        "tube":      emissive("MAT_fluoro_tube", (0.82, 1.00, 0.88), 6.0),
    }


# ─────────────────────────────────────────────────────────────────────
# Shell
# ─────────────────────────────────────────────────────────────────────

def build_shell(M, coll):
    hx, hy = ROOM_X / 2, ROOM_Y / 2

    put(plane("FLOOR", ROOM_X, ROOM_Y, (0, 0, 0), mat=M["concrete"]), coll)
    put(plane("CEILING", ROOM_X, ROOM_Y, (0, 0, ROOM_Z),
              rot=(math.pi, 0, 0), mat=M["ceiling"]), coll)

    # North, east and west walls are solid slabs.
    put(box("WALL_N", (ROOM_X + WALL_T * 2, WALL_T, ROOM_Z),
            (0, hy + WALL_T / 2, ROOM_Z / 2), M["wall"]), coll)
    put(box("WALL_E", (WALL_T, ROOM_Y, ROOM_Z),
            (hx + WALL_T / 2, 0, ROOM_Z / 2), M["wall"]), coll)
    put(box("WALL_W", (WALL_T, ROOM_Y, ROOM_Z),
            (-hx - WALL_T / 2, 0, ROOM_Z / 2), M["wall"]), coll)

    # South wall is built around the door opening, in four pieces, so the
    # opening is real geometry rather than a boolean that may fail.
    side_w = (ROOM_X - DOOR_W) / 2
    for sign in (-1, 1):
        cx = sign * (DOOR_W / 2 + side_w / 2)
        put(box(f"WALL_S_{'E' if sign > 0 else 'W'}",
                (side_w, WALL_T, ROOM_Z),
                (cx, -hy - WALL_T / 2, ROOM_Z / 2), M["wall"]), coll)
    put(box("WALL_S_HEAD", (DOOR_W, WALL_T, ROOM_Z - DOOR_H),
            (0, -hy - WALL_T / 2, DOOR_H + (ROOM_Z - DOOR_H) / 2),
            M["wall"]), coll)

    # The curtain, rolled down to DOOR_OPEN_Z. Slats read as horizontal
    # banding, which the restyle keeps.
    door = put(box("ROLLER_DOOR_CURTAIN",
                   (DOOR_W, 0.06, DOOR_H - DOOR_OPEN_Z),
                   (0, -hy - 0.04, DOOR_OPEN_Z + (DOOR_H - DOOR_OPEN_Z) / 2),
                   M["galv"]), coll)
    door.pass_index = DOOR_INDEX

    put(cyl("ROLLER_DOOR_BARREL", 0.22, DOOR_W + 0.4,
            (0, -hy - 0.10, DOOR_H + 0.28), M["galv"],
            rot=(0, math.pi / 2, 0)), coll)

    # The yard. Only a strip of ground and a forklift silhouette are needed:
    # everything beyond the door is read through a 2.3 m gap.
    put(plane("YARD_GROUND", 60.0, 40.0, (0, -hy - 20.0, -0.02),
              mat=M["concrete"]), coll)
    put(box("YARD_FORKLIFT_BODY", (1.25, 2.30, 1.55),
            (3.0, -hy - 2.6, 0.78), M["workwear"]), coll)
    put(box("YARD_FORKLIFT_MAST", (1.10, 0.18, 2.60),
            (3.0, -hy - 1.5, 1.30), M["steel"]), coll)
    return coll


# ─────────────────────────────────────────────────────────────────────
# Racking and dressing
# ─────────────────────────────────────────────────────────────────────

def build_racking(M, coll):
    hx, hy = ROOM_X / 2, ROOM_Y / 2
    x_face = hx - RACK_DEPTH          # aisle-side face of the east run
    y0, y1 = -hy + 0.8, hy - 0.8

    n_bays = int((y1 - y0) // RACK_BAY)
    for i in range(n_bays + 1):
        y = y0 + i * RACK_BAY
        for xo in (x_face + 0.08, hx - 0.08):
            put(box(f"RACK_UPRIGHT_{i}_{'A' if xo < hx - 0.5 else 'B'}",
                    (0.10, 0.10, RACK_H), (xo, y, RACK_H / 2), M["steel"]), coll)

    for li, z in enumerate(BEAM_LEVELS):
        for i in range(n_bays):
            yc = y0 + i * RACK_BAY + RACK_BAY / 2
            for xo in (x_face + 0.10, hx - 0.10):
                put(box(f"RACK_BEAM_L{li}_B{i}_{'A' if xo < hx - 0.5 else 'B'}",
                        (0.08, RACK_BAY - 0.12, 0.12),
                        (xo, yc, z), M["rackbeam"]), coll)

    # Part-filled bays. An empty rack reads as a render; a half-filled one
    # reads as a working building.
    fill = [(0, 0), (0, 1), (1, 0), (1, 2), (2, 1)]
    for bi, li in fill:
        if bi >= n_bays or li >= len(BEAM_LEVELS) - 1:
            continue
        yc = y0 + bi * RACK_BAY + RACK_BAY / 2
        z = BEAM_LEVELS[li] + 0.06
        put(box(f"PALLET_{bi}_{li}", (1.00, 1.15, 0.14),
                (x_face + 0.62, yc, z + 0.07), M["pallet"]), coll)
        put(box(f"PALLET_LOAD_{bi}_{li}", (0.92, 1.05, 0.85),
                (x_face + 0.62, yc, z + 0.14 + 0.43), M["wrap"]), coll)

    # Two pallets waiting on the floor by the door — the night shift's work.
    for i, (px, py) in enumerate([(1.6, -3.2), (0.2, -3.6)]):
        put(box(f"FLOOR_PALLET_{i}", (1.00, 1.20, 0.14),
                (px, py, 0.07), M["pallet"]), coll)
        put(box(f"FLOOR_PALLET_LOAD_{i}", (0.92, 1.10, 0.95),
                (px, py, 0.14 + 0.48), M["wrap"]), coll)
    return coll


def build_dressing(M, coll):
    hx = ROOM_X / 2

    # Work table against the west wall, below and left of the notices.
    tx = -hx + TABLE_D / 2 + 0.05
    put(box("TABLE_TOP", (TABLE_D, TABLE_L, 0.05),
            (tx, -1.40, TABLE_H), M["table"]), coll)
    for dy in (-TABLE_L / 2 + 0.12, TABLE_L / 2 - 0.12):
        for dx in (-TABLE_D / 2 + 0.08, TABLE_D / 2 - 0.08):
            put(box(f"TABLE_LEG_{dy:.2f}_{dx:.2f}",
                    (0.06, 0.06, TABLE_H),
                    (tx + dx, -1.40 + dy, TABLE_H / 2), M["steel"]), coll)

    put(box("SCANNER_CRADLE", (0.12, 0.20, 0.09),
            (tx + 0.10, -0.80, TABLE_H + 0.07), M["workwear"]), coll)
    put(box("RING_BINDER", (0.26, 0.32, 0.06),
            (tx - 0.02, -1.90, TABLE_H + 0.05), M["paper"]), coll)
    put(cyl("COFFEE_MUG", 0.042, 0.10,
            (tx + 0.22, -1.25, TABLE_H + 0.07), M["paper"]), coll)

    # Floor markings. A walkway down the west side and a hatched keep-clear
    # zone in front of the door.
    put(plane("MARK_WALKWAY", 0.10, ROOM_Y - 1.6,
              (-hx + 1.30, 0.0, 0.003), mat=M["yellow"]), coll)
    for i in range(7):
        put(plane(f"MARK_HATCH_{i}", 0.09, 1.50,
                  (-1.8 + i * 0.6, -ROOM_Y / 2 + 1.10, 0.003),
                  rot=(0, 0, math.radians(38)), mat=M["yellow"]), coll)
    return coll


# ─────────────────────────────────────────────────────────────────────
# The notice wall and the poster
# ─────────────────────────────────────────────────────────────────────

def build_notice_wall(M, coll):
    """Nine worn A4 notices, then the new laminated sheet in front of them.

    The poster carries no text. It is a blank laminated surface plus its own
    object index, so the slogan is composited in post with a free perfect
    track — and swapped per client without a single new render.
    """
    # y, z, roll, width, height. Mixed A4 portrait, A4 landscape and A5, hung
    # by different people over several years. An even grid reads as a render.
    rng = [(0.52, 1.44, -3.1, 0.210, 0.297), (1.02, 1.36,  2.2, 0.297, 0.210),
           (1.56, 1.47, -1.4, 0.210, 0.297), (0.60, 1.88,  1.7, 0.148, 0.210),
           (1.10, 1.92, -2.6, 0.210, 0.297), (1.70, 1.84,  0.9, 0.297, 0.210),
           (2.24, 1.50, -1.9, 0.210, 0.297), (2.34, 1.97,  2.8, 0.148, 0.210),
           (2.74, 1.68, -0.7, 0.210, 0.297)]
    for i, (y, z, rot_deg, w, h) in enumerate(rng):
        put(wall_sheet(f"NOTICE_{i:02d}", w, h,
                       (NOTICE_X, y, z), rot_deg, M["paper"]), coll)

    poster = wall_sheet("PROP_POSTER_BLANK", POSTER_W, POSTER_H,
                        POSTER_POS, 0.8, M["laminate"])
    poster.pass_index = POSTER_INDEX
    put(poster, coll)

    # A tracking card at each corner makes the post comp trivial.
    tr = bpy.data.objects.new("PROP_POSTER_TRACK", None)
    tr.empty_display_type = "PLAIN_AXES"
    tr.empty_display_size = 0.12
    tr.location = POSTER_POS
    put(tr, coll)
    return coll


# ─────────────────────────────────────────────────────────────────────
# Lighting rig
# ─────────────────────────────────────────────────────────────────────

def build_lights(M, coll):
    """Two light families that fight each other. That conflict is the room's
    character, and restyle preserves luminance relationships rather than
    inventing light — so the value structure has to be right here, not later.
    """
    hy = ROOM_Y / 2
    rows = (-2.5, 2.5)
    cols = (-4.0, 0.0, 4.0)

    for ri, y in enumerate(rows):
        for ci, x in enumerate(cols):
            dim = (ri == 1 and ci == 1)       # one tube is tired
            name = f"FLUORO_{ri}{ci}" + ("_DIM" if dim else "")

            ld = bpy.data.lights.new(name, type="AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = 1.50, 0.12
            # High-bay fluorescents at 5.7 m lose most of their output to
            # inverse square before they reach working height.
            ld.energy = 520.0 if dim else 1150.0
            ld.color = (0.78, 1.00, 0.84) if dim else (0.86, 1.00, 0.90)
            ob = bpy.data.objects.new(name, ld)
            ob.location = (x, y, ROOM_Z - 0.30)
            put(ob, coll)

            # Visible fixture, so the source is in shot where the camera sees it.
            put(box(f"FIXTURE_{ri}{ci}", (1.52, 0.14, 0.04),
                    (x, y, ROOM_Z - 0.28),
                    M["tube"]), coll)

    # Pre-dawn, through the door gap. Cold, low, and the only daylight.
    ld = bpy.data.lights.new("EXT_PREDAWN", type="AREA")
    ld.shape, ld.size, ld.size_y = "RECTANGLE", 9.0, 6.0
    ld.energy = 900.0
    ld.color = (0.55, 0.72, 1.00)
    ob = bpy.data.objects.new("EXT_PREDAWN", ld)
    ob.location = (0.0, -hy - 9.0, 3.0)
    look_at(ob, (0.0, 0.0, 1.6))
    put(ob, coll)

    # One patch of warm sodium out in the yard. The only warm thing in frame.
    ld = bpy.data.lights.new("EXT_SODIUM", type="POINT")
    ld.energy = 2600.0
    ld.color = (1.00, 0.60, 0.22)
    ld.shadow_soft_size = 0.5
    ob = bpy.data.objects.new("EXT_SODIUM", ld)
    ob.location = (6.2, -hy - 6.0, 4.0)   # inside the door's view cone
    put(ob, coll)

    world = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("WORLD_predawn")
    bpy.context.scene.world = world
    _use_nodes(world)
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        # Near-black. Ambient fill flattens the room and steals the job the
        # two practical families are supposed to be fighting over.
        bg.inputs["Color"].default_value = (0.016, 0.022, 0.038, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    return coll


# ─────────────────────────────────────────────────────────────────────
# Proxy figures
# ─────────────────────────────────────────────────────────────────────

def proxy(name, loc, facing_deg, M, coll, height=1.82):
    """Blocking proxy at correct height, with the vest on its own object
    index so hi-vis can be held stable through the restyle."""
    root = bpy.data.objects.new(f"PROXY_{name}", None)
    root.empty_display_type = "ARROWS"
    root.empty_display_size = 0.4
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(facing_deg))
    put(root, coll)

    s = height / 1.82
    parts = [
        ("LEG_L", cyl, dict(r=0.085, depth=0.86 * s), (-0.095, 0, 0.43 * s), M["workwear"]),
        ("LEG_R", cyl, dict(r=0.085, depth=0.86 * s), (0.095, 0, 0.43 * s), M["workwear"]),
        ("TORSO", None, (0.42, 0.24, 0.62 * s), (0, 0, 1.17 * s), M["workwear"]),
        ("VEST", None, (0.455, 0.275, 0.48 * s), (0, 0, 1.19 * s), M["vest"]),
        ("HEAD", None, (0.19, 0.21, 0.25 * s), (0, 0, 1.64 * s), M["skin"]),
    ]
    for pname, kind, arg, off, mat in parts:
        if kind is cyl:
            ob = cyl(f"PROXY_{name}_{pname}", arg["r"], arg["depth"], (0, 0, 0), mat)
        else:
            ob = box(f"PROXY_{name}_{pname}", arg, (0, 0, 0), mat)
        ob.location = off
        ob.parent = root
        if pname == "VEST":
            ob.pass_index = VEST_INDEX
        put(ob, coll)
    return root


def build_proxies(M, coll):
    # Where he stands in beat 1 shot 3. He is set left of the poster, not
    # square in front of it, so the over-shoulder has somewhere to look past.
    proxy("TOMERIK", (-5.55, 0.25, 0.0), 149, M, coll, height=1.82)
    # His path from the door, as empties, so blocking is visible in viewport.
    for i, p in enumerate([(0.0, -4.6), (-1.2, -3.4), (-2.6, -2.2),
                           (-4.0, -0.9), (-5.1, -0.2), (-5.55, 0.25)]):
        e = bpy.data.objects.new(f"PATH_TOMERIK_{i:02d}", None)
        e.empty_display_type = "SPHERE"
        e.empty_display_size = 0.10
        e.location = (p[0], p[1], 0.02)
        put(e, coll)
    return coll


# ─────────────────────────────────────────────────────────────────────
# Beat 1 cameras
# ─────────────────────────────────────────────────────────────────────

SHOTS = [
    dict(name="CAM_1_1_EMPTY", lens=28,
         loc=(-4.20, 3.40, 1.72), target=(1.80, -4.40, 2.70), roll=-0.9,
         note="The empty room. Door, yard and the tubes overhead. Hold too long."),
    dict(name="CAM_1_2_ENTER", lens=35,
         loc=(-1.90, -1.60, 1.55), target=(-5.90, 1.40, 1.95), roll=1.1,
         note="He crosses from the door and stops. Camera finds him a beat late."),
    dict(name="CAM_1_3_POSTER", lens=65,
         loc=(-3.95, -0.90, 2.02), target=POSTER_POS, roll=-0.6,
         note="Over his shoulder, clearing his head. He straightens the sheet. It was not crooked."),
    dict(name="CAM_1_4_PHONE", lens=40,
         loc=(-5.05, -1.35, 1.52), target=(-6.30, 1.10, 1.62), roll=0.7,
         note="From his side. He photographs it, deletes it, leaves. No reaction shot."),
]


def build_cameras(coll):
    scene = bpy.context.scene
    cams = []
    for i, s in enumerate(SHOTS):
        cd = bpy.data.cameras.new(s["name"])
        cd.lens = s["lens"]
        cd.sensor_width = 36.0
        cd.clip_start, cd.clip_end = 0.05, 200.0
        ob = bpy.data.objects.new(s["name"], cd)
        ob.location = s["loc"]
        look_at(ob, s["target"], s["roll"])
        ob["shot_note"] = s["note"]
        ob["frame_start"] = 1 + i * SHOT_FRAMES
        ob["frame_end"] = (i + 1) * SHOT_FRAMES
        put(ob, coll)
        cams.append(ob)

        # Bound marker, so scrubbing the timeline walks the beat.
        mk = scene.timeline_markers.new(s["name"], frame=1 + i * SHOT_FRAMES)
        mk.camera = ob

    scene.camera = cams[0]
    return cams


# ─────────────────────────────────────────────────────────────────────
# Render settings
# ─────────────────────────────────────────────────────────────────────

def configure_render():
    scene = bpy.context.scene
    r = scene.render

    # EEVEE is enough: this is a control pass, not a beauty pass.
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            r.engine = engine
            break
        except Exception:
            continue

    r.resolution_x, r.resolution_y = RES_X, RES_Y
    r.resolution_percentage = 100
    r.fps = FPS
    scene.frame_start = 1
    scene.frame_end = SHOT_FRAMES * len(SHOTS)

    r.image_settings.file_format = "PNG"
    r.film_transparent = False

    # Flat out. The style brief asks for naturalistic exposure and no grade,
    # and the restyle wants a neutral input. If the door clips, pull
    # EXT_PREDAWN down rather than reaching for a different view transform.
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
    except Exception:
        pass

    # Passes that earn their place in comp: depth for atmosphere, object
    # index and cryptomatte for the poster, the vest and the door.
    vl = scene.view_layers[0]
    for attr in ("use_pass_z", "use_pass_object_index",
                 "use_pass_cryptomatte_object", "use_pass_mist"):
        if hasattr(vl, attr):
            setattr(vl, attr, True)

    return scene


# ─────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────

def build():
    clear_scene()
    M = build_materials()

    c_shell = collection("SET_SHELL")
    c_rack = collection("SET_RACKING")
    c_dress = collection("SET_DRESSING")
    c_notice = collection("PROP_NOTICE_WALL")
    c_light = collection("LIGHTS")
    c_proxy = collection("PROXY_CHARS")
    c_cam = collection("CAMERAS")

    build_shell(M, c_shell)
    build_racking(M, c_rack)
    build_dressing(M, c_dress)
    build_notice_wall(M, c_notice)
    build_lights(M, c_light)
    build_proxies(M, c_proxy)
    cams = build_cameras(c_cam)
    configure_render()

    print("\n--- VAKTSKIFTET: varemottaket built ---")
    print(f"room          {ROOM_X} x {ROOM_Y} x {ROOM_Z} m")
    print(f"objects       {len(bpy.data.objects)}")
    print(f"materials     {len(bpy.data.materials)}")
    print(f"lights        {len([o for o in bpy.data.objects if o.type == 'LIGHT'])}")
    print(f"timeline      {bpy.context.scene.frame_end} frames @ {FPS} fps"
          f"  ({len(SHOTS)} shots x {SHOT_FRAMES})")
    print(f"poster index  {POSTER_INDEX}   vest {VEST_INDEX}   door {DOOR_INDEX}")
    print("\nshots:")
    for c in cams:
        print(f"  {c.name:18s} {c.data.lens:>4.0f}mm  "
              f"f{c['frame_start']}-{c['frame_end']}  {c['shot_note']}")
    print()
    return cams


if __name__ == "__main__":
    build()

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--save" in argv:
        path = argv[argv.index("--save") + 1]
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print(f"saved {path}")
    if "--still" in argv:
        i = argv.index("--still")
        cam_name, out = argv[i + 1], argv[i + 2]
        bpy.context.scene.camera = bpy.data.objects[cam_name]
        bpy.context.scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"rendered {cam_name} -> {out}")
