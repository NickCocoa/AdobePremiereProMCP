"""
Kylling-previs: to blokk-karakterer som leker og kaster maling på hverandre.

Handling: Gutten løper inn, leker og søler maling. Søster sparker ham hodet
først ned i balja. Malingskamp og jakt ut av bildet, inn igjen og dypt i
rommet. De sklir i malingen og har det gøy. Gutten heller maling i kamera,
søster tørker linsa og smiler.

Kjør i Blender (4.x / 5.x):
  * Scripting-fanen -> Open -> denne fila -> Run Script
  * eller fra terminal:
      blender -b -P kylling_previs.py -- --save kylling_previs.blend

Skriptet tømmer scenen og bygger alt på nytt hver gang det kjøres.

Karakterer (blokking):
  GUTT  = svart blokk (gul kylling i oransje snekkerbukse)
  JENTE = hvit blokk  (gul kylling i korall kjole med sløyfe)
  Forsiden (lokal -Y) er rød på begge, så du alltid ser hvor de ser.
"""

import math
import random
import sys
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Quaternion, Vector

FPS = 24
FRAME_START = 1
FRAME_END = 1104  # 46 sek

# Karakter-proporsjoner (meter): høy blokk som leses som en person
CHAR_W = 0.7   # bredde (skulder til skulder)
CHAR_D = 0.5   # dybde (forside til bakside)
CHAR_H = 1.7   # høyde
FRONT = CHAR_D / 2  # avstand fra senter til den røde forsiden
LEAN = 0.7     # demper lening, høye blokker vipper mye i toppen

# Farger (lineære RGB)
RED = (0.80, 0.03, 0.03)
BLACK = (0.02, 0.02, 0.02)
WHITE = (0.85, 0.85, 0.85)
STUDIO_WHITE = (0.90, 0.88, 0.86)
# Lyse, lekne malingsfarger
PAINTS = {
    "Rosa": (0.95, 0.10, 0.42),
    "Turkis": (0.0, 0.62, 0.62),
    "Gul": (1.0, 0.68, 0.02),
    "Lime": (0.30, 0.80, 0.04),
    "Lilla": (0.38, 0.08, 0.88),
    "Oransje": (1.0, 0.28, 0.02),
    "Himmelblaa": (0.08, 0.40, 1.0),
}
METAL = (0.55, 0.55, 0.56)
WOOD = (0.35, 0.22, 0.12)


# --------------------------------------------------------------------------
# Hjelpere
# --------------------------------------------------------------------------

def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                       bpy.data.lights, bpy.data.curves, bpy.data.actions,
                       bpy.data.worlds):
        for b in list(datablocks):
            datablocks.remove(b)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    bpy.context.scene.timeline_markers.clear()


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def material(name, color, rough=0.5, metallic=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)  # farge i Solid-visning
    m.roughness = rough
    m.metallic = metallic
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
        if emission:
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission
    return m


def pick(mat, i):
    """Velg materiale i fra en liste (rundt og rundt), eller bruk det ene."""
    return mat[i % len(mat)] if isinstance(mat, (list, tuple)) else mat


def mesh_object(name, bm, coll, mats=()):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True


def look_at(ob, target):
    direction = Vector(target) - ob.location
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


@contextmanager
def interpolation(mode):
    """Midlertidig standard-interpolasjon for nye keyframes."""
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = mode
    try:
        yield
    finally:
        prefs.keyframe_new_interpolation_type = old


def key(ob, f, loc=None, rot=None, scale=None):
    """rot er i grader."""
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if rot is not None:
        ob.rotation_euler = [math.radians(a) for a in rot]
        ob.keyframe_insert("rotation_euler", frame=f)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert("scale", frame=f)


_last_rz = {}


def pose(ob, f, x, y, z=0.0, rx=0.0, rz=0.0, sq=1.0, raw=False, spin=False, ry=0.0):
    """Karakter-positur. rx>0 = len fremover, rx<0 = len bakover.
    rz = retning i grader (90 = mot +X, -90 = mot -X, 0 = mot kamera).
    sq = squash/stretch (z-skala), xy kompenseres for volum.
    raw: bruk rx uten demping (salto, ligge på ryggen).
    spin: bruk rz som den er; ellers velges korteste vei fra forrige retning.
    ry: vipp sidelengs (>0 = toppen mot +X når figuren ser mot kamera)."""
    if not spin and ob.name in _last_rz:
        prev = _last_rz[ob.name]
        rz = prev + (rz - prev + 180.0) % 360.0 - 180.0
    _last_rz[ob.name] = rz
    xy = 1.0 / math.sqrt(sq)
    key(ob, f, loc=(x, y, z), rot=(rx if raw else rx * LEAN, ry, rz), scale=(xy, xy, sq))


def teleport(ob, f_out, f_in, loc_out):
    """Hold posisjonen utenfor bildet til f_in, uten å gli over scenen."""
    with interpolation("CONSTANT"):
        key(ob, f_out, loc=loc_out)
        key(ob, f_in - 1, loc=loc_out)


def pop(ob, f_on, full=(1, 1, 1), f_off=None, overshoot=1.25):
    """Skjult (skala 0) til f_on, spretter inn, evt. forsvinner etter f_off."""
    with interpolation("CONSTANT"):
        key(ob, FRAME_START, scale=(0, 0, 0))
        key(ob, f_on - 1, scale=(0, 0, 0))
    key(ob, f_on, scale=tuple(s * overshoot for s in full))
    key(ob, f_on + 3, scale=full)
    if f_off is not None:
        with interpolation("CONSTANT"):
            key(ob, f_off, scale=full)
        key(ob, f_off + 1, scale=(0, 0, 0))


# --------------------------------------------------------------------------
# Studio
# --------------------------------------------------------------------------

def build_studio(coll):
    """Hvit cyclorama (gulv som bøyer seg opp i bakvegg)."""
    profile = []
    for i in range(6):  # gulv fra kamera mot bakvegg
        profile.append((-30 + i * 6.8, 0.0))
    r, cy = 3.0, 4.0
    for i in range(1, 12):  # myk bue
        a = math.radians(-90 + i * 90 / 12)
        profile.append((cy + r * math.cos(a), r + r * math.sin(a)))
    profile += [(cy + r, r), (cy + r, 20.0)]

    bm = bmesh.new()
    xs = (-40.0, 40.0)
    rows = [[bm.verts.new((x, y, z)) for x in xs] for (y, z) in profile]
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    cyc = mesh_object("Studio_Cyclorama", bm, coll,
                      [material("M_Studio", STUDIO_WHITE, rough=0.8)])
    smooth(cyc)

    # Rekvisitter fra referansebildene: trekasse til høyre
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=bm.verts)
    crate = mesh_object("Prop_Trekasse", bm, coll, [material("M_Tre", WOOD, 0.7)])
    crate.location = (4.2, 1.6, 0)
    crate.scale = (1.1, 0.9, 0.9)
    crate.rotation_euler.z = math.radians(-12)
    bev = crate.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments = 0.03, 2


def build_lights(coll):
    def area(name, loc, target, energy, size, color):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(name, ld)
        coll.objects.link(ob)
        ob.location = loc
        look_at(ob, target)
        return ob

    area("Lys_Key", (-4.5, -5.0, 6.0), (0, 0, 0.6), 750, 5.0, (1.0, 0.88, 0.74))
    area("Lys_Fill", (5.5, -4.5, 3.0), (0, 0, 0.6), 200, 6.0, (0.80, 0.88, 1.0))
    area("Lys_Rim", (2.0, 5.0, 5.0), (0, 0, 0.8), 800, 3.0, (1.0, 0.92, 0.80))

    world = bpy.data.worlds.new("Studio_World")
    bpy.context.scene.world = world
    world.color = STUDIO_WHITE
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = world.node_tree.nodes.get("Background") if world.node_tree else None
    if bg:
        bg.inputs["Color"].default_value = (*STUDIO_WHITE, 1.0)
        bg.inputs["Strength"].default_value = 0.35


# --------------------------------------------------------------------------
# Karakterer og rekvisitter
# --------------------------------------------------------------------------

def build_character(name, label, body_color, coll, label_coll):
    """Blokk CHAR_W x CHAR_D x CHAR_H med origo nederst.
    Alle sider i kroppsfarge, forsiden (-Y) rød."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(CHAR_W, CHAR_D, CHAR_H), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, CHAR_H / 2), verts=bm.verts)
    bm.normal_update()
    for f in bm.faces:
        f.material_index = 1 if f.normal.y < -0.9 else 0
    ob = mesh_object(name, bm, coll, [
        material(f"M_{name}_Kropp", body_color, rough=0.45),
        material(f"M_{name}_Forside", RED, rough=0.4),
    ])
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments = 0.04, 3
    bev.limit_method = "ANGLE"

    # Navneskilt over hodet (kun i viewport, ikke i render)
    cu = bpy.data.curves.new(f"{name}_Navn", "FONT")
    cu.body = label
    cu.align_x = "CENTER"
    cu.size = 0.22
    txt = bpy.data.objects.new(f"{name}_Navn", cu)
    label_coll.objects.link(txt)
    txt.data.materials.append(material(f"M_{name}_Navn", (0.05, 0.05, 0.05)))
    txt.location = (0, 0, CHAR_H + 0.35)
    txt.rotation_euler = (math.radians(90), 0, 0)
    c = txt.constraints.new("COPY_LOCATION")
    c.target, c.use_offset = ob, True
    c.use_z = False
    txt.hide_render = True
    return ob


def build_bucket(name, coll, paint_mat, metal_mat, r1=0.19, r2=0.23, depth=0.36):
    """Malingsspann, origo midt i bunnen, åpning opp (+Z)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=r1,
                          radius2=r2, depth=depth)
    bmesh.ops.translate(bm, vec=(0, 0, depth / 2), verts=bm.verts)
    bm.normal_update()
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=top, context="FACES_ONLY")
    ob = mesh_object(name, bm, coll, [metal_mat])
    smooth(ob)
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.012

    mats = list(paint_mat) if isinstance(paint_mat, (list, tuple)) else [paint_mat]
    r = r1 + (r2 - r1) * 0.85
    bm = bmesh.new()
    center = bm.verts.new((0, 0, 0))
    segs = 36
    ring = [bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), 0))
            for i in range(segs)]
    for i in range(segs):                              # én kile per farge
        f = bm.faces.new((center, ring[i], ring[(i + 1) % segs]))
        f.material_index = (i * len(mats)) // segs
    paint = mesh_object(name + "_Maling", bm, coll, mats)
    paint.parent = ob
    paint.location = (0, 0, depth * 0.83)
    return ob


def blob_mesh(name, coll, mat, radius=1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=radius)
    ob = mesh_object(name, bm, coll, [mat])
    smooth(ob)
    return ob


def throw_blob(name, coll, mat, start, end, f0, f1, height=0.6, side=0.0):
    """Malingsklatt i bue fra start til end (frame f0 -> f1)."""
    ob = blob_mesh(name, coll, mat, radius=0.13)
    s, e = Vector(start), Vector(end)
    with interpolation("LINEAR"):
        for f in range(f0, f1 + 1):
            t = (f - f0) / (f1 - f0)
            p = s.lerp(e, t)
            arc = 4 * t * (1 - t)
            p.z += height * arc
            p.y += side * arc
            key(ob, f, loc=p)
    pop(ob, f0, full=(1.0, 1.0, 0.85), f_off=f1, overshoot=1.0)
    return ob


def splat_on(target, name, coll, mat, f_hit, local_xz, size=(0.22, 0.18)):
    """Flat malingsflekk på forsiden (lokal -Y) av en karakter."""
    ob = blob_mesh(name, coll, mat)
    ob.parent = target
    ob.location = (local_xz[0], -FRONT, local_xz[1])
    pop(ob, f_hit, full=(size[0], 0.035, size[1]))
    return ob


def floor_puddle(name, coll, mat, xy, f_on, size=0.35, grow=8):
    ob = blob_mesh(name, coll, mat)
    ob.location = (xy[0], xy[1], 0.0)
    full = (size, size * 0.8, 0.012)
    with interpolation("CONSTANT"):
        key(ob, FRAME_START, scale=(0, 0, 0))
        key(ob, f_on - 1, scale=(0, 0, 0))
    key(ob, f_on, scale=tuple(v * 0.3 for v in full))
    key(ob, f_on + grow, scale=full)
    return ob


def splash(name, coll, mat, origin, f_hit, toward_x, count=6, seed=0):
    """Små dråper som spruter ut ved treff."""
    rnd = random.Random(seed)
    o = Vector(origin)
    for i in range(count):
        ob = blob_mesh(f"{name}_{i}", coll, pick(mat, i), radius=0.045)
        v = Vector((toward_x * rnd.uniform(0.04, 0.10),
                    rnd.uniform(-0.09, 0.05),
                    rnd.uniform(0.04, 0.12)))
        last = f_hit
        with interpolation("LINEAR"):
            for k in range(0, 16):
                p = o + v * k
                p.z -= 0.006 * k * k
                last = f_hit + k
                key(ob, last, loc=(p.x, p.y, max(p.z, 0.01)))
                if p.z <= 0.01:
                    break
        pop(ob, f_hit, full=(1, 1, 1), f_off=last, overshoot=1.0)


# --------------------------------------------------------------------------
# Ekstra karakter-elementer
# --------------------------------------------------------------------------

def build_paint_coat(target, coll, mat, f_on):
    """Malingsdrakt over hode og overkropp etter at gutten dukkes i balja."""
    h = CHAR_H * 0.65
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(CHAR_W + 0.05, CHAR_D + 0.05, h), verts=bm.verts)
    mats = list(mat) if isinstance(mat, (list, tuple)) else [mat]
    for i, f in enumerate(bm.faces):
        f.material_index = i % len(mats)
    ob = mesh_object("Gutt_Malingsdrakt", bm, coll, mats)
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments = 0.06, 3
    ob.parent = target
    ob.location = (0, 0, CHAR_H + 0.03 - h / 2)
    pop(ob, f_on, overshoot=1.1)
    return ob


def build_smile(target, coll, f_on, prefix, depth=FRONT + 0.03):
    """Smil og øyne på forsiden, dukker opp i siste shot."""
    white = bpy.data.materials.get("M_Smil") or material("M_Smil", (0.95, 0.95, 0.95), rough=0.3)
    cu = bpy.data.curves.new(f"{prefix}_Smil", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.025
    sp = cu.splines.new("POLY")
    n = 9
    sp.points.add(n - 1)
    for i, p in enumerate(sp.points):
        a = math.pi + 0.35 + i * (math.pi - 0.7) / (n - 1)
        p.co = (0.15 * math.cos(a), 0.0, 0.11 * math.sin(a), 1.0)
    smile = bpy.data.objects.new(f"{prefix}_Smil", cu)
    coll.objects.link(smile)
    cu.materials.append(white)
    smile.parent = target
    smile.location = (0, -depth, 1.45)
    pop(smile, f_on)
    for side in (-1, 1):
        eye = blob_mesh(f"{prefix}_Oye_{'V' if side < 0 else 'H'}", coll, white)
        eye.parent = target
        eye.location = (0.11 * side, -depth + 0.01, 1.6)
        pop(eye, f_on, full=(0.04, 0.02, 0.05))


# --------------------------------------------------------------------------
# Animasjon
# --------------------------------------------------------------------------

def heading(dx, dy):
    """Retning (rz i grader) som får forsiden (-Y) til å peke langs (dx, dy)."""
    return math.degrees(math.atan2(dx, -dy))


def run(ob, f0, f1, path, stride=6, lean=22, hop=0.16):
    """Løp langs en polylinje med jevn fart og sprett hvert halve steg."""
    pts = [Vector((x, y, 0.0)) for x, y in path]
    segs = list(zip(pts, pts[1:]))
    total = sum((b - a).length for a, b in segs)
    n = max(2, round((f1 - f0) / (stride / 2)))
    for i in range(n + 1):
        t = i / n
        d = t * total
        for a, b in segs:
            length = (b - a).length
            if d <= length or (a, b) == segs[-1]:
                p = a.lerp(b, min(d / length, 1.0))
                rz = heading(*(b - a).xy)
                break
            d -= length
        up = i % 2 == 1 and i < n
        pose(ob, round(f0 + (f1 - f0) * t), p.x, p.y, hop if up else 0.0,
             lean, rz, 1.06 if up else 0.94)


def animate_boy(b):
    P = lambda *a, **k: pose(b, *a, **k)
    tub = (0.0, 0.4)
    # SH010: Løper inn fra venstre og leker
    P(1, -8.5, -0.4, 0, 0, 90)
    run(b, 12, 46, [(-8.5, -0.4), (-1.2, -0.4)])
    P(50, -1.2, -0.4, 0, -8, 90, 0.8)                  # bremser
    P(54, -1.2, -0.4, 0, 0, 90, 0.85)
    P(60, -1.2, -0.4, 0.8, 0, 270, 1.2, spin=True)     # piruett-hopp
    P(66, -1.2, -0.4, 0, 0, 450, 0.8, spin=True)
    P(70, -1.2, -0.4, 0, 0, 450, 1.0, spin=True)
    P(76, -1.05, 0.0, 0.3, 10, 90, 1.1)                # oppdager balja
    P(80, -0.9, 0.4, 0, 10, 90, 0.88)
    P(84, -0.9, 0.4, 0, 30, 90, 1.0)                   # titter nedi
    P(88, -0.9, 0.4, 0, -5, 90, 1.15)                  # "jippi!"

    # Kaster maling rundt seg: øs fra balja, snu, kast
    hand = lambda tgt: Vector(tgt) - Vector((-0.9, 0.4))
    for ft, tgt in ((104, (-2.6, -1.4)), (122, (-0.5, -2.0))):
        rz = heading(*hand(tgt))
        P(ft - 10, -0.9, 0.4, 0, 40, 90, 0.88)         # øser
        P(ft - 5, -0.9, 0.4, 0, -15, rz, 1.12)         # oppladning
        P(ft, -0.9, 0.4, 0, 25, rz, 0.95)              # KAST
        P(ft + 4, -0.9, 0.4, 0, 5, rz, 1.0)

    # Maler på gulvet med hendene
    P(148, -0.75, -0.25, 0.3, 0, 0, 1.1)
    P(152, -0.6, -0.9, 0, 10, 0, 0.88)
    P(156, -0.6, -0.9, 0, 45, 0, 0.9)
    for i, f in enumerate(range(160, 196, 6)):
        x = -0.6 + 0.27 * (i + 1)
        P(f, x, -0.9, 0, 50 if i % 2 else 38, 8 if i % 2 else -8, 0.9 if i % 2 else 1.0)
    P(198, 1.0, -0.9, 0, 0, 0, 1.05)                   # reiser seg
    P(204, 1.0, -0.9, 0.3, -8, 0, 1.15)                # stolt hopp
    P(210, 1.0, -0.9, 0, 0, 0, 0.82)
    P(216, 1.0, -0.3, 0.1, -6, 0, 1.0)                 # rygger for å beundre
    P(222, 1.0, 0.35, 0, 0, 0, 1.0)

    # SH020: Søster sparker ham på hodet ned i balja
    P(224, 1.0, 0.35, 0, -5, 90, 1.12)                 # snur, ser henne
    P(228, 1.0, 0.35, 0, -5, 90, 1.1)
    P(230, 1.0, 0.35, 0, -20, 90, 0.8, raw=True)       # TREFF
    P(234, 0.95, 0.38, 1.0, -70, 90, 1.1, raw=True)
    P(238, 0.55, 0.4, 1.95, -130, 90, 1.0, raw=True)
    P(242, 0.1, 0.4, 2.15, -172, 90, 1.0, raw=True)
    P(246, *tub, 1.85, -180, 90, 0.9, raw=True)        # PLASK, hodet først
    P(250, *tub, 1.92, -180, 90, 1.05, raw=True)
    for i, f in enumerate(range(254, 272, 4)):         # spreller med beina
        P(f, *tub, 1.9 if i % 2 else 1.86, -180, 72 if i % 2 else 108, 1.0, raw=True)
    P(274, *tub, 1.8, -180, 90, 0.88, raw=True)
    P(280, -0.45, 0.4, 1.5, -90, 90, 1.1, raw=True)    # spretter opp
    P(286, -1.0, 0.4, 0, 0, 90, 0.8, raw=True)         # full av maling
    P(290, -1.0, 0.4, 0, 0, 90, 1.0)
    for i, f in enumerate(range(292, 304, 2)):         # rister seg som en hund
        P(f, -1.0, 0.4, 0, 0, 70 if i % 2 else 110, 1.0)
    P(304, -0.8, 0.4, 0, 0, 90, 1.0)

    # SH030: Kaster tilbake
    P(308, -0.8, 0.4, 0, 40, 90, 0.9)
    P(312, -0.8, 0.4, 0, -20, 90, 1.12)
    P(316, -0.8, 0.4, 0, 25, 90, 0.95)                 # KAST
    P(322, -0.8, 0.4, 0, 8, 90, 1.0)
    for i, f in enumerate(range(328, 352, 4)):         # ler
        P(f, -0.8, 0.4, 0, -12 if i % 2 == 0 else 2, 90, 1.1 if i % 2 == 0 else 0.92)
    P(372, -0.8, 0.4, 0, 0, 90, 1.0)
    P(384, -0.8, 0.4, 0, -10, 90, 1.18)                # ser spannet: uh-oh
    run(b, 388, 436, [(-0.8, 0.4), (-3.0, 0.5), (-8.5, 0.9)])  # flykter ut
    teleport(b, 437, 470, (-8.5, 0.9, 0))

    # SH040: Kommer inn igjen fra høyre og jager henne dypt i rommet og frem
    P(470, 8.5, 0.5, 0, 0, -90)
    run(b, 476, 576, [(8.5, 0.5), (4.5, 3.0), (1.0, 5.0), (-2.5, 5.0),
                      (-3.8, 2.5), (-2.5, 0.0), (-0.2, -1.8)])
    hd = heading(2.3, -1.8)
    P(578, -0.05, -2.0, 0.5, -60, hd, 1.0, raw=True)   # sklir!
    P(582, 0.15, -2.35, 0.25, -90, hd, 1.0, raw=True)
    P(590, 0.6, -2.75, 0.25, -90, hd, 1.0, raw=True)
    P(594, 0.65, -2.8, 0.25, -90, hd, 1.0, raw=True)
    for i, f in enumerate(range(598, 618, 4)):         # ligger og ler
        P(f, 0.65, -2.8, 0.32 if i % 2 == 0 else 0.25, -90, hd + (8 if i % 2 else -8), 1.0, raw=True)

    # SH050: Opp igjen, hopper og dunker borti henne
    P(620, 0.55, -2.9, 0.6, 0, 0, 1.15, raw=True)
    P(626, 0.55, -2.9, 0, 0, 0, 0.8)
    P(630, 0.55, -2.9, 0, 0, 0, 1.0)
    P(634, 0.55, -2.9, 0, 0, 0, 0.85)
    P(640, 0.55, -2.9, 0.7, 0, 180, 1.15, spin=True)
    P(646, 0.55, -2.9, 0, 0, 360, 0.8, spin=True)
    P(650, 0.5, -2.9, 0, 0, 350, 0.9)                  # side-dunk
    P(656, 0.6, -2.9, 0, 0, 360, 1.0)

    # SH060: Jager jenta, øser fra balja og kaster, hun dukker, maling i kamera
    P(664, 0.6, -2.9, 0, -10, 380, 1.1)                # blir ertet
    P(672, 0.6, -2.9, 0, 0, 340, 0.9)
    run(b, 680, 712, [(0.6, -2.9), (1.6, -1.0), (0.95, 0.4)])
    P(716, 0.95, 0.4, 0, 40, -90, 0.88)                # øser fra balja
    P(722, 0.95, 0.4, 0, -5, -90, 1.05)
    P(726, 0.95, 0.4, 0, -22, -7, 1.15)                # oppladning mot jenta/kamera
    P(730, 0.95, 0.4, 0, 28, -7, 0.92)                 # KAST
    P(736, 0.95, 0.4, 0, 8, -7, 1.0)
    P(742, 0.95, 0.4, 0, 0, -7, 1.0)
    teleport(b, 743, 850, (4.5, -4.6, 0))              # ut av bildet bak malingen

    # Løper inn og klemmer søsteren, smiler i kamera
    run(b, 850, 866, [(4.5, -4.6), (0.55, -5.0)], lean=18)
    P(870, 0.53, -5.0, 0, 10, -60, 0.88, ry=-7)        # KLEM (dunker inn i henne)
    P(876, 0.55, -5.0, 0, 0, -45, 1.04, ry=-5)
    P(884, 0.55, -5.0, 0, 0, -45, 1.0, ry=-5)
    P(892, 0.55, -5.0, 0, 0, -12, 1.0, ry=-5)          # ser i kamera
    P(898, 0.55, -5.0, 0, 0, -12, 1.06, ry=-5)
    for i, f in enumerate(range(906, 944, 8)):         # ler sammen
        P(f, 0.55, -5.0, 0, -6 if i % 2 == 0 else 0, -12, 1.06 if i % 2 == 0 else 0.97, ry=-5)
    P(946, 0.53, -5.0, 0, 0, -14, 0.93, ry=-7)         # ekstra klem
    P(954, 0.55, -5.0, 0, 0, -12, 1.02, ry=-5)
    P(966, 0.55, -5.0, 0, 0, -12, 1.0, ry=-5)          # varmt smil, hold
    P(FRAME_END, 0.55, -5.0, 0, 0, -12, 1.01, ry=-5)


def animate_girl(g):
    P = lambda *a, **k: pose(g, *a, **k)
    # Venter utenfor bildet til høyre
    P(1, 8.5, 0.6, 0, 0, -90)
    P(196, 8.5, 0.6, 0, 0, -90)
    run(g, 196, 222, [(8.5, 0.6), (2.1, 0.35)], lean=26)
    P(224, 2.1, 0.35, 0, -10, -90, 0.85)               # bremser
    P(227, 2.2, 0.35, 0, -40, -90, 1.12)               # oppladning
    P(230, 1.8, 0.35, 0.05, 50, -90, 0.95)             # SPARK
    P(236, 1.85, 0.35, 0, 0, -90, 1.0)
    for i, f in enumerate(range(242, 302, 5)):         # ler av ham
        P(f, 1.85, 0.35, 0, -15 if i % 2 == 0 else 0, -90, 1.1 if i % 2 == 0 else 0.92)
    P(316, 1.85, 0.35, 0, 0, -90, 1.0)
    P(324, 1.85, 0.35, 0, 0, -90, 1.08)                # ser klatten
    P(326, 1.85, 0.35, 0, -30, -90, 0.75)              # TREFF
    P(330, 2.2, 0.35, 0.05, -35, -90, 0.85)
    P(336, 2.25, 0.35, 0, 5, -90, 1.05)
    P(340, 2.25, 0.35, 0, 0, -90, 1.0)
    for i, f in enumerate(range(343, 355, 3)):         # sint stamping
        P(f, 2.25, 0.35, 0.2 if i % 2 == 0 else 0, 0, -90, 1.15 if i % 2 == 0 else 0.8)
    P(358, 2.25, 0.35, 0, 0, heading(1.05, 0.85), 1.12)  # ser spannet
    run(g, 360, 366, [(2.25, 0.35), (3.0, 0.95)])
    P(370, 3.0, 0.95, 0, 40, heading(1.05, 0.85), 0.88)
    P(374, 3.0, 0.95, 0, -5, heading(1.05, 0.85), 1.05)
    P(378, 3.0, 0.95, 0, 0, -90, 1.0)
    P(382, 3.1, 0.95, 0, -22, -90, 1.15)               # oppladning
    P(386, 2.95, 0.95, 0, 25, -90, 0.92)               # KAST (bommer)
    P(392, 2.95, 0.95, 0, 5, -90, 1.0)
    P(396, 2.95, 0.95, 0, 35, -90, 0.9)                # kaster hele spannet
    run(g, 400, 448, [(2.95, 0.95), (1.5, 1.6), (-0.3, 1.9), (-3.0, 0.9), (-8.5, 0.9)])
    teleport(g, 449, 456, (-8.5, 0.9, 0))

    # SH040: Kommer først inn fra høyre, løper dypt i rommet og frem
    P(456, 8.5, 0.5, 0, 0, -90)
    run(g, 460, 560, [(8.5, 0.5), (4.5, 3.0), (1.0, 5.0), (-2.5, 5.0),
                      (-3.8, 2.5), (-2.5, 0.0), (-0.8, -1.7)])
    hd = heading(1.7, -1.7)
    P(562, -0.7, -1.9, 0.5, -60, hd, 1.0, raw=True)    # sklir i malingen
    P(566, -0.55, -2.3, 0.25, -90, hd, 1.0, raw=True)
    P(576, -0.3, -2.9, 0.25, -90, hd, 1.0, raw=True)
    P(580, -0.25, -3.0, 0.25, -90, hd, 1.0, raw=True)
    for i, f in enumerate(range(586, 618, 4)):         # ligger og ler
        P(f, -0.25, -3.0, 0.32 if i % 2 == 0 else 0.25, -90, hd + (8 if i % 2 else -8), 1.0, raw=True)

    # SH050: Opp, felles piruett, side-dunk
    P(620, -0.5, -2.9, 0.6, 0, 0, 1.15, raw=True)
    P(626, -0.5, -2.9, 0, 0, 0, 0.8)
    P(630, -0.5, -2.9, 0, 0, 0, 1.0)
    P(634, -0.5, -2.9, 0, 0, 0, 0.85)
    P(640, -0.5, -2.9, 0.7, 0, 180, 1.15, spin=True)
    P(646, -0.5, -2.9, 0, 0, 360, 0.8, spin=True)
    P(650, -0.2, -2.9, 0, 0, 370, 0.9)                 # side-dunk
    P(656, -0.5, -2.9, 0, 0, 360, 1.0)

    # SH060: Erter ham og løper; dypt i rommet og mot kamera, dukker unna
    P(660, -0.5, -2.9, 0, 0, 400, 1.0)                 # snur seg mot ham
    P(664, -0.4, -2.9, 0, 20, 400, 1.05)               # erter
    P(668, -0.4, -2.9, 0, -10, 400, 1.12)
    run(g, 672, 732, [(-0.5, -2.9), (-2.8, -2.2), (-2.2, 1.6), (-1.2, 2.2),
                      (-0.8, -1.5), (-0.2, -4.3)])
    P(735, -0.1, -4.7, 0.1, -10, 160, 1.1)             # ser seg tilbake
    P(738, -0.05, -5.0, 0, 25, 30, 0.6)                # DUKKER
    P(742, 0.0, -5.2, 0, 30, 20, 0.55)
    P(746, 0.0, -5.2, 0, 30, 20, 0.55)
    P(764, -2.2, -6.1, 0, 0, 0, 1.0)                   # skjult bak malingen
    P(767, -2.2, -6.1, 0, 0, 0, 1.0)
    P(778, 0.0, -6.1, 0.05, 10, 0, 1.05)               # TØRKER linsa
    P(786, -0.3, -5.0, 0, 0, 0, 1.0)
    P(792, -0.3, -5.0, 0, -6, 0, 1.1)                  # puh! (lettet)
    P(800, -0.3, -5.0, 0, 0, 0, 0.98)
    P(810, -0.3, -5.0, 0, 0, 0, 1.0)                   # smiler
    P(816, -0.3, -5.0, 0, 0, 0, 0.88)
    P(822, -0.3, -5.0, 0.25, -5, 0, 1.15)              # glad hopp
    P(828, -0.3, -5.0, 0, 0, 0, 0.88)
    P(834, -0.3, -5.0, 0, 0, 0, 1.02)
    P(850, -0.3, -5.0, 0, 0, 0, 1.0)
    P(862, -0.3, -5.0, 0, 0, 25, 1.04)                 # hører ham komme
    P(870, -0.45, -5.0, 0, -8, 40, 0.9, ry=7)         # KLEM
    P(876, -0.42, -5.0, 0, 0, 40, 1.04, ry=5)
    P(884, -0.42, -5.0, 0, 0, 35, 1.0, ry=5)
    P(892, -0.42, -5.0, 0, 0, 12, 1.0, ry=5)            # ser i kamera
    P(898, -0.42, -5.0, 0, 0, 12, 1.06, ry=5)
    for i, f in enumerate(range(910, 944, 8)):         # ler sammen
        P(f, -0.42, -5.0, 0, -6 if i % 2 == 0 else 0, 12, 1.06 if i % 2 == 0 else 0.97, ry=5)
    P(946, -0.4, -5.0, 0, 0, 14, 0.93, ry=7)         # ekstra klem
    P(954, -0.42, -5.0, 0, 0, 12, 1.02, ry=5)
    P(966, -0.42, -5.0, 0, 0, 12, 1.0, ry=5)
    P(FRAME_END, -0.42, -5.0, 0, 0, 12, 1.01, ry=5)


def animate_props(tub, bucket_g, bucket_b):
    K = key
    K(tub, 1, loc=(0, 0.4, 0), rot=(0, 0, 0))
    K(tub, 246, scale=(1, 1, 1))
    K(tub, 248, scale=(1.08, 1.08, 0.9))               # PLASK
    K(tub, 252, scale=(1, 1, 1))

    # Jentas spann ved trekassa
    K(bucket_g, 1, loc=(3.3, 1.2, 0), rot=(0, 0, 0))
    K(bucket_g, 370, loc=(3.3, 1.2, 0), rot=(0, 0, 0))
    K(bucket_g, 374, loc=(3.32, 1.27, 0.85), rot=(0, 0, 0))
    K(bucket_g, 378, loc=(2.55, 0.95, 0.95), rot=(0, 0, 0))
    K(bucket_g, 382, loc=(3.35, 0.95, 2.2), rot=(0, 35, 0))
    K(bucket_g, 386, loc=(2.55, 0.95, 1.75), rot=(0, -75, 0))
    K(bucket_g, 392, loc=(2.6, 0.95, 1.0), rot=(0, -110, 0))
    K(bucket_g, 396, loc=(2.5, 0.95, 1.5), rot=(0, -60, 0))
    K(bucket_g, 402, loc=(0.4, -0.5, 2.2), rot=(60, -400, 0))
    K(bucket_g, 408, loc=(-1.8, -1.3, 0.23), rot=(90, -720, 40))
    K(bucket_g, 411, loc=(-1.82, -1.32, 0.3), rot=(85, -720, 43))
    K(bucket_g, 414, loc=(-1.83, -1.33, 0.23), rot=(90, -720, 45))

    # Guttens spann foran til høyre
    K(bucket_b, 1, loc=(1.7, -2.7, 0), rot=(0, 0, 0))


# --------------------------------------------------------------------------
# Ting som veltes når de løper forbi
# --------------------------------------------------------------------------

def key_rot(ob, f, loc, rot):
    ob.location = loc
    ob.rotation_euler = rot
    ob.keyframe_insert("location", frame=f)
    ob.keyframe_insert("rotation_euler", frame=f)


def knock_over(ob, f_hit, d, lie_z, slide=0.3):
    """Velter en stående ting (origo i bunnen) i retning d."""
    d = Vector((d[0], d[1], 0)).normalized()
    axis = Vector((-d.y, d.x, 0))
    base = Vector(ob.location)
    up = Vector((0, 0, 1))
    key_rot(ob, FRAME_START, base, (0, 0, 0))
    key_rot(ob, f_hit, base, (0, 0, 0))
    key_rot(ob, f_hit + 3, base + d * 0.12 + up * 0.08, Quaternion(axis, math.radians(50)).to_euler())
    lie = Quaternion(axis, math.radians(90)).to_euler()
    key_rot(ob, f_hit + 7, base + d * slide + up * lie_z, lie)
    key_rot(ob, f_hit + 10, base + d * (slide + 0.05) + up * (lie_z + 0.06), lie)
    key_rot(ob, f_hit + 13, base + d * (slide + 0.07) + up * lie_z, lie)


def scatter(objs, f_hit, d, size, seed=0):
    """Sender en stabel med ting flyvende i retning d."""
    rnd = random.Random(seed)
    d = Vector((d[0], d[1], 0)).normalized()
    side = Vector((-d.y, d.x, 0))
    for i, ob in enumerate(objs):
        base = Vector(ob.location)
        end = base + d * (0.5 + 0.35 * i) + side * rnd.uniform(-0.35, 0.35)
        end.z = size / 2
        mid = base.lerp(end, 0.5)
        mid.z = base.z + 0.45 + 0.15 * i
        spin = (math.radians(90 * rnd.randint(1, 3)), math.radians(90 * rnd.randint(0, 2)),
                math.radians(rnd.uniform(-60, 60)))
        key_rot(ob, FRAME_START, base, (0, 0, 0))
        key_rot(ob, f_hit + i, base, (0, 0, 0))
        key_rot(ob, f_hit + 5 + i, mid, tuple(a * 0.5 for a in spin))
        key_rot(ob, f_hit + 10 + i, end, spin)
        key_rot(ob, f_hit + 13 + i, end + Vector((0, 0, 0.05)), spin)
        key_rot(ob, f_hit + 15 + i, end, spin)


def build_knockables(coll, fx_coll, pm, metal):
    wood = bpy.data.materials.get("M_Tre")
    card = material("M_Papp", (0.55, 0.36, 0.18), rough=0.8)
    cone_mat = material("M_Kjegle", (1.0, 0.25, 0.02), rough=0.5)

    def can(name, xy, color):
        ob = build_bucket(name, coll, pm[color], metal)
        ob.location = (*xy, 0)
        return ob

    def stool(name, xy):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.2, radius2=0.2, depth=0.45)
        bmesh.ops.translate(bm, vec=(0, 0, 0.225), verts=bm.verts)
        ob = mesh_object(name, bm, coll, [wood])
        ob.location = (*xy, 0)
        return ob

    def cone(name, xy):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.17, radius2=0.03, depth=0.5)
        bmesh.ops.translate(bm, vec=(0, 0, 0.25), verts=bm.verts)
        ob = mesh_object(name, bm, coll, [cone_mat])
        smooth(ob)
        ob.location = (*xy, 0)
        return ob

    def box_stack(name, xy, n=3, size=0.35):
        out = []
        for i in range(n):
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=size)
            ob = mesh_object(f"{name}_{i}", bm, coll, [card])
            ob.location = (*xy, size / 2 + i * size)
            out.append(ob)
        return out

    def can_stack(name, xy, colors):
        out = []
        for i, c in enumerate(colors):
            ob = build_bucket(f"{name}_{i}", coll, pm[c], metal)
            ob.location = (*xy, i * 0.36)
            out.append(ob)
        return out

    # (ting, frame den treffes, retning den faller, hvem)
    # Gutten løper inn: velter en gul malingsboks
    c = can("Velt_Boks_Gul", (-4.5, -0.75), "Gul")
    knock_over(c, 31, (0.5, -0.85), 0.21)
    floor_puddle("Dam_Velt_Gul", fx_coll, pm["Gul"], (-4.2, -1.3), 38, size=0.4, grow=25)
    # Søster løper inn: velter en krakk
    knock_over(stool("Velt_Krakk_1", (5.0, 0.25)), 211, (-0.5, -0.85), 0.2)
    # Gutten flykter: velter en kjegle og en eskestabel
    knock_over(cone("Velt_Kjegle", (-1.9, 0.15)), 395, (-0.1, -1.0), 0.15)
    scatter(box_stack("Velt_Esker", (-3.6, 0.5)), 405, (-0.5, -0.85), 0.35, seed=31)
    # Søster løper dypt i rommet: river ned et tårn av malingsbokser
    tower = can_stack("Velt_Boksetaarn", (-0.75, 5.3), ["Rosa", "Himmelblaa", "Lime"])
    scatter(tower, 512, (-0.6, 0.8), 0.42, seed=32)
    for i, col in enumerate(["Rosa", "Himmelblaa", "Lime"]):
        floor_puddle(f"Dam_Taarn_{i}", fx_coll, pm[col], (-1.1 - 0.3 * i, 5.75 + 0.2 * i), 524 + i,
                     size=0.35, grow=20)
    # Siste jakt: gutten velter en lime boks, søster velter en krakk
    c = can("Velt_Boks_Lime", (1.1, -1.95), "Lime")
    knock_over(c, 689, (0.7, 0.7), 0.21)
    floor_puddle("Dam_Velt_Lime", fx_coll, pm["Lime"], (1.45, -1.6), 696, size=0.4, grow=25)
    knock_over(stool("Velt_Krakk_2", (-0.95, 1.0)), 709, (0.6, -0.8), 0.2)


def build_paint_fx(coll, pm, boy, girl, cam_end):
    rainbow = list(pm.values())
    # Gutten kaster maling rundt seg fra balja
    for i, (ft, tgt, col) in enumerate(((104, (-2.6, -1.4), "Rosa"), (122, (-0.5, -2.0), "Gul"))):
        paint = pm[col]
        d = (Vector(tgt) - Vector((-0.9, 0.4))).normalized()
        start = (-0.9 + d.x * 0.45, 0.4 + d.y * 0.45, 1.7)
        throw_blob(f"Klatt_Rundt_{i}", coll, paint, start, (*tgt, 0.05), ft, ft + 10, height=0.8)
        floor_puddle(f"Dam_Rundt_{i}", coll, paint, tgt, ft + 10,
                     size=0.8 if i == 1 else 0.4, grow=12)
        splash(f"Sprut_Rundt_{i}", coll, paint, (*tgt, 0.05), ft + 10,
               toward_x=-1 if tgt[0] < -0.9 else 1, count=4, seed=10 + i)

    # Håndavtrykk på gulvet
    for i, f in enumerate(range(160, 196, 6)):
        x = -0.6 + 0.27 * (i + 1) + (0.1 if i % 2 else -0.1)
        floor_puddle(f"Handavtrykk_{i}", coll, pick(rainbow, i), (x, -1.45), f, size=0.16, grow=3)

    # Plask i balja + malingsdrakt
    splash("Sprut_Balje_V", coll, rainbow, (-0.2, 0.4, 0.6), 246, toward_x=-1, count=8, seed=20)
    splash("Sprut_Balje_H", coll, rainbow[3:] + rainbow[:3], (0.2, 0.4, 0.6), 246, toward_x=1, count=8, seed=21)
    floor_puddle("Dam_Balje", coll, pm["Turkis"], (0.0, 0.15), 248, size=0.75, grow=20)
    build_paint_coat(boy, coll, [pm["Turkis"], pm["Rosa"], pm["Gul"], pm["Lilla"], pm["Lime"], pm["Oransje"]], 278)
    floor_puddle("Dam_Gutt_Drypp", coll, pm["Lilla"], (-1.0, 0.25), 288, size=0.45, grow=25)
    splash("Sprut_Rister_V", coll, rainbow, (-1.0, 0.4, 1.4), 292, toward_x=-1, count=10, seed=22)
    splash("Sprut_Rister_H", coll, rainbow[2:] + rainbow[:2], (-1.0, 0.4, 1.4), 292, toward_x=1, count=10, seed=23)

    # Gutten kaster tilbake: treffer jenta
    throw_blob("Klatt_GuttTilJente", coll, pm["Lilla"], (-0.35, 0.4, 1.75), (1.62, 0.35, 1.1), 316, 326)
    splat_on(girl, "Flekk_Jente", coll, pm["Lilla"], 326, (0.0, 1.1))
    splash("Sprut_Jente", coll, pm["Lilla"], (1.6, 0.25, 1.1), 326, toward_x=-1, seed=24)
    floor_puddle("Dam_Jente", coll, pm["Lilla"], (1.5, -0.1), 328, size=0.3)

    # Jenta kaster med spann, bommer
    throw_blob("Klatt_JenteTilGutt", coll, pm["Rosa"], (2.55, 0.95, 1.8), (-1.3, 0.3, 0.05), 386, 396)
    floor_puddle("Dam_Bom", coll, pm["Rosa"], (-1.3, 0.3), 396, size=0.5, grow=10)
    splash("Sprut_Bom", coll, pm["Rosa"], (-1.3, 0.3, 0.05), 396, toward_x=-1, seed=25)
    floor_puddle("Dam_Spann_Jente", coll, pm["Rosa"], (-1.85, -1.75), 412, size=0.45, grow=25)

    # Avslutning: maling i kamera, tørkes av
    fwd = cam_end.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    lens = cam_end.location + fwd * 0.3
    throw_blob("Klatt_IKamera", coll, pm["Oransje"], (0.9, -0.05, 1.8), tuple(lens), 730, 742, height=0.8)
    lens_paint(cam_end, coll, [pm["Oransje"], pm["Rosa"], pm["Gul"], pm["Himmelblaa"]], 742, 768, 778)

    # Sakte innzoom på ansiktene mot slutten
    for f, lens_mm in ((786, 24.0), (990, 34.0), (FRAME_END, 27.0)):
        cam_end.data.lens = lens_mm
        cam_end.data.keyframe_insert("lens", frame=f)


def lens_paint(cam, coll, mat, f_hit, f_wipe0, f_wipe1):
    """Maling som treffer linsa (foreldret til kamera) og tørkes av mot høyre."""
    blobs = [((0, 0), (0.26, 0.17)), ((-0.14, 0.07), (0.1, 0.08)),
             ((0.13, -0.07), (0.11, 0.07)), ((0.06, 0.1), (0.08, 0.06))]
    for i, ((x, y), (sx, sy)) in enumerate(blobs):
        ob = blob_mesh(f"Kamera_Maling_{i}", coll, pick(mat, i))
        ob.parent = cam
        z = -0.2 + i * 0.002
        pop(ob, f_hit + (i > 0), full=(sx, sy, 0.004), overshoot=1.0 if i == 0 else 1.2)
        key(ob, f_wipe0, loc=(x, y, z))
        key(ob, f_wipe1, loc=(x + 0.65, y, z))
    for i, x in enumerate((-0.06, 0.03, 0.08)):        # drypp som renner nedover
        ob = blob_mesh(f"Kamera_Drypp_{i}", coll, pick(mat, i + 1))
        ob.parent = cam
        pop(ob, f_hit + 2, full=(0.012, 0.02, 0.004), overshoot=1.0)
        key(ob, f_hit + 2, loc=(x, -0.02, -0.199))
        key(ob, f_wipe0, loc=(x, -0.07 - 0.01 * i, -0.199))
        key(ob, f_wipe1, loc=(x + 0.65, -0.07 - 0.01 * i, -0.199))


# --------------------------------------------------------------------------
# Avslutning: mørkt rundt dem, spot ovenfra, kamera trekker seg bak, de vinker
# --------------------------------------------------------------------------

def build_finale(boy, girl, cam, coll, f_dark=990, f_wave=1012):
    scene = bpy.context.scene
    f_dark_done = f_dark + 18

    # Studiolyset dimmes ned, verden blir nesten svart
    for name in ("Lys_Key", "Lys_Fill", "Lys_Rim"):
        ld = bpy.data.objects[name].data
        full = ld.energy
        ld.keyframe_insert("energy", frame=f_dark)
        ld.energy = full * 0.02
        ld.keyframe_insert("energy", frame=f_dark_done)
        ld.energy = full
    bg = scene.world.node_tree.nodes.get("Background") if scene.world.node_tree else None
    if bg:
        strength = bg.inputs["Strength"]
        full = strength.default_value
        strength.keyframe_insert("default_value", frame=f_dark)
        strength.default_value = 0.0
        strength.keyframe_insert("default_value", frame=f_dark_done)
        strength.default_value = full

    # Spot rett ovenfra på dem
    ld = bpy.data.lights.new("Lys_Spot_Finale", "SPOT")
    ld.spot_size = math.radians(32)
    ld.spot_blend = 0.3
    ld.color = (1.0, 0.95, 0.85)
    spot = bpy.data.objects.new("Lys_Spot_Finale", ld)
    coll.objects.link(spot)
    spot.location = (0.06, -5.0, 6.5)                  # peker rett ned (-Z)
    ld.energy = 0.0
    ld.keyframe_insert("energy", frame=f_dark + 4)
    ld.energy = 2500.0
    ld.keyframe_insert("energy", frame=f_dark_done + 4)

    # Kamera trekker seg rolig bakover og litt opp
    target = (0.06, -5.0, 1.1)
    cam.keyframe_insert("location", frame=f_dark)
    cam.keyframe_insert("rotation_euler", frame=f_dark)
    start_loc = cam.location.copy()
    start_rot = cam.rotation_euler.copy()
    cam.location = (0.0, -10.5, 2.4)
    look_at(cam, target)
    cam.keyframe_insert("location", frame=FRAME_END)
    cam.keyframe_insert("rotation_euler", frame=FRAME_END)
    cam.location, cam.rotation_euler = start_loc, start_rot

    # Vinke-armer (enkle blokker i kroppsfarge) og vinking
    for ob, side, base_ry in ((girl, -1, 5), (boy, 1, -5)):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.12, 0.12, 0.5), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0, 0, 0.25), verts=bm.verts)
        arm = mesh_object(f"{ob.name}_Vinkearm", bm, coll, [ob.data.materials[0]])
        bev = arm.modifiers.new("Bevel", "BEVEL")
        bev.width, bev.segments = 0.03, 2
        arm.parent = ob
        arm.location = (side * (CHAR_W / 2 + 0.07), 0, 1.15)
        pop(arm, f_wave - 4, overshoot=1.15)
        for i, f in enumerate(range(f_wave, FRAME_END - 6, 6)):
            a = side * (20 + (25 if i % 2 else -15))
            arm.rotation_euler = (0, math.radians(a), 0)
            arm.keyframe_insert("rotation_euler", frame=f)
        # kroppen vugger litt med vinkingen
        x, y = ob.location.x, ob.location.y
        for i, f in enumerate(range(f_wave, FRAME_END - 6, 12)):
            pose(ob, f, x, y, 0.08 if i % 2 else 0, 0, -12 * side, 1.04 if i % 2 else 0.98,
                 ry=base_ry + (4 if i % 2 else -4) * side)
        pose(ob, FRAME_END, x, y, 0, 0, -12 * side, 1.0, ry=base_ry)


# --------------------------------------------------------------------------
# Pixar-kamera: myke panoreringer, sakte innkjøringer, dybdeskarphet
# --------------------------------------------------------------------------

def empty(name, coll, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None)
    coll.objects.link(ob)
    ob.empty_display_size = 0.15
    ob.parent = parent
    ob.location = loc
    return ob


def copy_loc(ob, target, influence=1.0):
    c = ob.constraints.new("COPY_LOCATION")
    c.target = target
    c.influence = influence
    return c


def key_influence(c, frames_values):
    for f, v in frames_values:
        c.influence = v
        c.keyframe_insert("influence", frame=f)


def aim(cam, target):
    c = cam.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return c


def dof(cam, focus, fstop):
    d = cam.data.dof
    d.use_dof = True
    d.focus_object = focus
    d.aperture_fstop = fstop


def push(cam, windows):
    """Sakte innkjøring mot motivet i hvert vindu (f0, f1, meter)."""
    home = cam.location.copy()
    fwd = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    for f0, f1, dist in windows:
        cam.location = home
        cam.keyframe_insert("location", frame=f0)
        cam.location = home + fwd * dist
        cam.keyframe_insert("location", frame=f1)
    cam.location = home


def build_cinematic(cams, boy, girl, coll):
    # Fokuspunkter i hodehøyde (følger hodet også i salto og når de ligger)
    head_b = empty("Fokus_Gutt", coll, (0, 0, 1.45), boy)
    head_g = empty("Fokus_Jente", coll, (0, 0, 1.45), girl)
    mid = empty("Fokus_Midt", coll)
    copy_loc(mid, head_b)
    copy_loc(mid, head_g, 0.5)                         # midt mellom hodene

    # Wide: panorerer mykt etter gutten, og etter begge når søster er med
    aim_w = empty("Sikte_Wide", coll, (0.2, 0, 1.0))
    key_influence(copy_loc(aim_w, head_b), [(1, 0.45)])
    key_influence(copy_loc(aim_w, head_g), [(1, 0.0), (210, 0.0), (224, 0.33)])
    aim(cams["wide"], aim_w)
    dof(cams["wide"], mid, 5.6)
    push(cams["wide"], [(1, 211, 0.9)])

    # Medium og dyp: følger midtpunktet mellom dem, sakte innkjøring
    for key_, base, inf, f in (("medium", (0.6, 0.4, 1.1), 0.7, 4.0), ("deep", (0, 1.5, 1.0), 0.5, 4.0)):
        a = empty(f"Sikte_{key_}", coll, base)
        copy_loc(a, mid, inf)
        aim(cams[key_], a)
        dof(cams[key_], mid, f)
    push(cams["medium"], [(212, 228, 0.3), (228, 305, 0.6)])
    push(cams["deep"], [(452, 500, 0.8), (536, 660, 1.2)])

    # Nærbilder: følger hodet, grunn dybdeskarphet, liten innkjøring
    cu = [
        ("cu_boy_ots", head_b, [(222, 228, 0.15)]),
        ("cu_girl_laugh", head_g, [(240, 272, 0.35)]),
        ("cu_boy_front", head_b, [(288, 306, 0.3), (378, 390, 0.25)]),
        ("cu_girl_hit", head_g, [(323, 356, 0.35)]),
        ("cu_lying", mid, [(594, 618, 0.4)]),
        ("cu_tease", head_g, [(660, 672, 0.2)]),
        ("cu_hug", mid, [(904, 946, 0.4)]),
        ("cu_run", mid, [(500, 536, 0.3)]),  # f/2.8 under, raske bevegelser
    ]
    for key_, target, windows in cu:
        aim(cams[key_], target)
        dof(cams[key_], target, 2.8 if key_ == "cu_run" else 2.0)
        push(cams[key_], windows)

    # Sluttkameraet har egne nøkler, bare fokus her
    dof(cams["end"], mid, 4.0)


# --------------------------------------------------------------------------
# Kamera og shots
# --------------------------------------------------------------------------

def build_cameras(coll):
    def cam(name, loc, target, lens):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start = 0.05
        cd.passepartout_alpha = 0.85
        ob = bpy.data.objects.new(name, cd)
        coll.objects.link(ob)
        ob.location = loc
        look_at(ob, target)
        return ob

    cams = {
        "wide": cam("CAM_01_Wide", (0, -9.0, 1.7), (0.2, 0, 1.0), 32),
        "medium": cam("CAM_02_Medium", (1.6, -5.0, 1.7), (0.6, 0.4, 1.1), 35),
        "deep": cam("CAM_03_Dyp", (0.5, -8.5, 1.2), (0, 1.5, 1.0), 30),
        "end": cam("CAM_04_Ende", (0, -7.5, 1.5), (0.3, -3.5, 1.25), 24),
        # Nærbilder på relasjonen mellom dem (statiske, siktet mot hodehøyde)
        "cu_boy_ots": cam("CAM_CU_01_Gutt_OTS", (3.3, -0.6, 1.75), (1.0, 0.35, 1.3), 38),
        "cu_girl_laugh": cam("CAM_CU_02_Jente_Ler", (-0.9, -0.6, 1.75), (1.85, 0.35, 1.3), 40),
        "cu_boy_front": cam("CAM_CU_03_Gutt", (0.6, -0.9, 1.5), (-0.9, 0.4, 1.3), 36),
        "cu_girl_hit": cam("CAM_CU_04_Jente_Treff", (0.5, -1.0, 1.55), (2.1, 0.35, 1.3), 38),
        "cu_lying": cam("CAM_CU_05_Liggende", (-1.0, -2.7, 2.6), (-1.0, -1.85, 0.3), 32),
        "cu_tease": cam("CAM_CU_06_Erting_OTS", (1.6, -3.6, 1.6), (-0.4, -2.9, 1.3), 34),
        "cu_hug": cam("CAM_CU_07_Klem", (0.6, -6.6, 1.55), (0.06, -5.0, 1.45), 35),
        "cu_run": cam("CAM_CU_08_Loep", (-2.2, 4.2, 1.4), (0.5, 5.0, 1.2), 30),
    }

    scene = bpy.context.scene
    shots = [
        (1, "wide", "SH010 Gutten leker og søler"),
        (212, "medium", "SH020 Søster kommer"),
        (222, "cu_boy_ots", "SH021 CU Gutten ser henne (OTS)"),
        (228, "medium", "SH022 Spark, hodet ned i balja"),
        (240, "cu_girl_laugh", "SH023 CU Søster ler av ham"),
        (272, "medium", "SH024 Han spretter opp"),
        (288, "cu_boy_front", "SH025 CU Gutten full av maling"),
        (306, "wide", "SH030 Han kaster tilbake"),
        (323, "cu_girl_hit", "SH031 CU Søster blir truffet, sint"),
        (356, "wide", "SH032 Hun henter spann"),
        (378, "cu_boy_front", "SH033 CU Gutten: uh-oh"),
        (390, "wide", "SH034 Jakt ut av bildet"),
        (452, "deep", "SH040 Jakt dypt i rommet"),
        (500, "cu_run", "SH040b CU Søster raser forbi og river ned tårnet, han etter"),
        (536, "deep", "SH040c Jakt frem, de sklir"),
        (594, "cu_lying", "SH041 CU Ligger og ler sammen"),
        (618, "deep", "SH042 Piruett og dunk"),
        (660, "cu_tease", "SH043 CU Søster erter ham (OTS)"),
        (672, "end", "SH060 Jakt mot kamera, maling på linsa"),
        (904, "cu_hug", "SH061 CU Klem, fniser til hverandre"),
        (946, "end", "SH062 Varmt smil i kamera, mørkt, spot, de vinker"),
    ]
    for f, cam_key, label in shots:
        m = scene.timeline_markers.new(label, frame=f)
        m.camera = cams[cam_key]

    # Ansiktsuttrykk til ferdig versjon (bare notater, bytter ikke kamera)
    expressions = [
        (668, "Uttrykk J: ertende, rekker tunge"),
        (733, "Uttrykk J: skrekkslagen, ser seg tilbake"),
        (738, "Uttrykk J: kniper øynene, dukker"),
        (792, "Uttrykk J: lettet, puh!"),
        (800, "Uttrykk J: lurt, fornøyd blikk i kamera"),
        (810, "Uttrykk J: stort smil"),
        (862, "Uttrykk J: overrasket, hører ham"),
        (870, "Uttrykk G+J: klem, latter"),
        (892, "Uttrykk G+J: smiler i kamera"),
        (910, "Uttrykk G+J: fniser, ser på hverandre"),
        (946, "Uttrykk G+J: ekstra klem, øynene igjen"),
        (966, "Uttrykk G+J: varmt smil i kamera, hold"),
        (996, "Uttrykk G+J: ser opp på spotlyset, forundret"),
        (1012, "Uttrykk G+J: vinker og smiler farvel"),
    ]
    for f, label in expressions:
        scene.timeline_markers.new(label, frame=f)
    scene.camera = cams["wide"]
    return cams


# --------------------------------------------------------------------------
# Tempo: klipp ut tidsbiter og skyv alt etterpå bakover
# --------------------------------------------------------------------------

# (fra, til) i opprinnelige frames. Alt innenfor fjernes, alt etter flyttes frem.
CUTS = [
    (82, 92),     # kortere "oppdager balja"
    (134, 148),   # tredje kast er tatt ut
    (172, 190),   # halvparten av malingen med hendene
    (199, 211),   # stolt hopp
    (814, 832),   # søsters glade hopp etter linsa
    (836, 850),   # venting før gutten kommer
]


def iter_fcurves():
    ids = (list(bpy.data.objects) + list(bpy.data.cameras) + list(bpy.data.lights)
           + list(bpy.data.materials) + list(bpy.data.worlds)
           + [w.node_tree for w in bpy.data.worlds if w.node_tree])
    seen = set()
    for idb in ids:
        ad = getattr(idb, "animation_data", None)
        if not ad or not ad.action or ad.action.name in seen:
            continue
        act = ad.action
        seen.add(act.name)
        if getattr(act, "layers", None):               # Blender 4.4+ (slotted actions)
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        yield from bag.fcurves
        else:
            yield from act.fcurves


def retime(f):
    """Ny frame for en opprinnelig frame som ligger utenfor klippene."""
    return f - sum(min(e, f) - s for s, e in CUTS if f > s)


def apply_cuts():
    inside = lambda f: any(s <= f < e for s, e in CUTS)
    for fc in iter_fcurves():
        pts = fc.keyframe_points
        for i in reversed(range(len(pts))):
            if inside(pts[i].co.x):
                pts.remove(pts[i])
        for kp in pts:
            d = retime(kp.co.x) - kp.co.x
            kp.co.x += d
            kp.handle_left.x += d
            kp.handle_right.x += d
        fc.update()
    scene = bpy.context.scene
    for m in list(scene.timeline_markers):
        if inside(m.frame):
            scene.timeline_markers.remove(m)
        else:
            m.frame = int(retime(m.frame))
    scene.frame_end = int(retime(FRAME_END))


# --------------------------------------------------------------------------
# Render / viewport
# --------------------------------------------------------------------------

def setup_render():
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.frame_set(FRAME_START)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 50
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    for vt in ("AgX", "Filmic"):
        try:
            scene.view_settings.view_transform = vt
            break
        except TypeError:
            continue
    try:
        scene.view_settings.look = "AgX - Punchy"            # fyldigere, Pixar-aktige farger
    except TypeError:
        pass
    scene.render.use_motion_blur = True
    for attr, val in (("use_raytracing", True), ("use_gtao", True)):
        if hasattr(scene.eevee, attr):
            setattr(scene.eevee, attr, val)
    scene.render.filepath = "//render/kylling_previs_"
    scene.render.use_stamp = True
    scene.render.use_stamp_marker = True
    scene.render.use_stamp_camera = True
    scene.render.use_stamp_filename = False
    scene.render.use_stamp_date = False

    # Solid-visning med materialfarger = rask previs i viewport
    screen = getattr(bpy.context, "screen", None)
    if screen:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                shading = area.spaces.active.shading
                shading.type = "SOLID"
                shading.color_type = "MATERIAL"
                shading.light = "STUDIO"


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {}
    if "--save" in argv:
        out["save"] = argv[argv.index("--save") + 1]
    return out


def main():
    clear_scene()
    c_set = collection("Studio")
    c_light = collection("Lys")
    c_char = collection("Karakterer")
    c_label = collection("Navneskilt")
    c_props = collection("Rekvisitter")
    c_fx = collection("Maling_FX")
    c_cam = collection("Kamera")

    build_studio(c_set)
    build_lights(c_light)

    pm = {k: material(f"M_Maling_{k}", c, rough=0.12) for k, c in PAINTS.items()}
    metal = material("M_Metall", METAL, rough=0.3, metallic=1.0)

    boy = build_character("Gutt", "GUTT", BLACK, c_char, c_label)
    girl = build_character("Jente", "JENTE", WHITE, c_char, c_label)
    tub = build_bucket("Balje", c_props, list(pm.values()), metal, r1=0.4, r2=0.47, depth=0.6)
    bucket_b = build_bucket("Spann_Gutt", c_props, pm["Gul"], metal)
    bucket_g = build_bucket("Spann_Jente", c_props, pm["Rosa"], metal)
    build_smile(girl, c_char, 810, "Jente")
    build_smile(boy, c_char, 892, "Gutt", depth=FRONT + 0.06)

    _last_rz.clear()
    animate_boy(boy)
    animate_girl(girl)
    animate_props(tub, bucket_g, bucket_b)
    cams = build_cameras(c_cam)
    build_cinematic(cams, boy, girl, c_cam)
    build_paint_fx(c_fx, pm, boy, girl, cams["end"])
    build_knockables(c_props, c_fx, pm, metal)
    build_finale(boy, girl, cams["end"], c_char)
    setup_render()
    apply_cuts()

    args = parse_args()
    if "save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args["save"]))
        print("Lagret:", args["save"])


if __name__ == "__main__":
    main()
