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
from mathutils import Vector

FPS = 24
FRAME_START = 1
FRAME_END = 768  # 32 sek

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
PAINT = (0.11, 0.035, 0.015)  # sjokoladebrun maling som på referansene
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


def pose(ob, f, x, y, z=0.0, rx=0.0, rz=0.0, sq=1.0, raw=False, spin=False):
    """Karakter-positur. rx>0 = len fremover, rx<0 = len bakover.
    rz = retning i grader (90 = mot +X, -90 = mot -X, 0 = mot kamera).
    sq = squash/stretch (z-skala), xy kompenseres for volum.
    raw: bruk rx uten demping (salto, ligge på ryggen).
    spin: bruk rz som den er; ellers velges korteste vei fra forrige retning."""
    if not spin and ob.name in _last_rz:
        prev = _last_rz[ob.name]
        rz = prev + (rz - prev + 180.0) % 360.0 - 180.0
    _last_rz[ob.name] = rz
    xy = 1.0 / math.sqrt(sq)
    key(ob, f, loc=(x, y, z), rot=(rx if raw else rx * LEAN, 0.0, rz), scale=(xy, xy, sq))


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

    area("Lys_Key", (-4.5, -5.0, 6.0), (0, 0, 0.6), 700, 5.0, (1.0, 0.93, 0.84))
    area("Lys_Fill", (5.5, -4.5, 3.0), (0, 0, 0.6), 220, 6.0, (0.86, 0.91, 1.0))
    area("Lys_Rim", (2.0, 5.0, 5.0), (0, 0, 0.8), 450, 3.0, (1.0, 0.97, 0.92))

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

    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=32, radius=r1 + (r2 - r1) * 0.85)
    paint = mesh_object(name + "_Maling", bm, coll, [paint_mat])
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
        ob = blob_mesh(f"{name}_{i}", coll, mat, radius=0.045)
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
    ob = mesh_object("Gutt_Malingsdrakt", bm, coll, [mat])
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments = 0.06, 3
    ob.parent = target
    ob.location = (0, 0, CHAR_H + 0.03 - h / 2)
    pop(ob, f_on, overshoot=1.1)
    return ob


def build_smile(target, coll, f_on):
    """Smil og øyne på forsiden, dukker opp i siste shot."""
    white = material("M_Smil", (0.95, 0.95, 0.95), rough=0.3)
    cu = bpy.data.curves.new("Jente_Smil", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.025
    sp = cu.splines.new("POLY")
    n = 9
    sp.points.add(n - 1)
    for i, p in enumerate(sp.points):
        a = math.pi + 0.35 + i * (math.pi - 0.7) / (n - 1)
        p.co = (0.15 * math.cos(a), 0.0, 0.11 * math.sin(a), 1.0)
    smile = bpy.data.objects.new("Jente_Smil", cu)
    coll.objects.link(smile)
    cu.materials.append(white)
    smile.parent = target
    smile.location = (0, -FRONT - 0.03, 1.45)
    pop(smile, f_on)
    for side in (-1, 1):
        eye = blob_mesh(f"Jente_Oye_{'V' if side < 0 else 'H'}", coll, white)
        eye.parent = target
        eye.location = (0.11 * side, -FRONT - 0.02, 1.6)
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
    for ft, tgt in ((104, (-2.6, -1.4)), (122, (-0.5, -2.0)), (140, (-2.2, 1.8))):
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
    run(b, 388, 436, [(-0.8, 0.4), (-3.0, -0.3), (-8.5, -0.6)])  # flykter ut
    teleport(b, 437, 470, (-8.5, -0.6, 0))

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

    # SH060: Finner spannet og heller maling i kamera
    P(660, 0.6, -2.9, 0, 0, 460, 1.1)                  # ser spannet
    P(664, 1.25, -2.8, 0.25, 10, 460, 1.0)
    P(668, 1.25, -2.8, 0, 40, 460, 0.9)
    P(672, 1.25, -2.8, 0, -5, 460, 1.05)
    P(676, 1.25, -2.8, 0, 0, 360, 1.0)                 # mot kamera
    run(b, 678, 694, [(1.25, -2.8), (0.3, -4.4)], lean=12)
    P(698, 0.3, -4.4, 0, -22, 360, 1.15)               # løfter spannet
    P(702, 0.3, -4.4, 0, 25, 360, 0.95)                # HELLER
    P(708, 0.3, -4.4, 0, 10, 360, 1.0)
    P(712, 0.3, -4.4, 0, 0, 360, 1.0)
    P(720, 1.4, -3.4, 0, 0, 345, 1.0)                  # trekker seg unna, ler
    for i, f in enumerate(range(724, 768, 5)):
        P(f, 1.4, -3.4, 0, -12 if i % 2 == 0 else 2, 345, 1.1 if i % 2 == 0 else 0.92)
    P(FRAME_END, 1.4, -3.4, 0, 0, 345, 1.0)


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
    run(g, 400, 448, [(2.95, 0.95), (1.2, -0.4), (-3.0, -0.6), (-8.5, -0.7)])
    teleport(g, 449, 456, (-8.5, -0.7, 0))

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

    # SH060: Ser på, gjemt bak malingen på linsa, tørker den av og smiler
    P(664, -0.5, -2.9, 0, 0, 420, 1.0)
    P(700, -0.5, -2.9, 0, -8, 400, 1.1)                # "nei, ikke gjør det!"
    P(708, -0.5, -2.9, 0, 0, 400, 1.0)
    P(714, -2.2, -6.1, 0, 0, 360, 1.0)                 # skjult bak malingen
    P(716, -2.2, -6.1, 0, 0, 360, 1.0)
    P(724, 0.0, -6.1, 0.05, 10, 360, 1.05)             # TØRKER linsa
    P(728, 0.0, -5.6, 0, 0, 360, 1.0)
    P(734, 0.0, -5.0, 0, 0, 360, 1.0)                  # smiler
    P(738, 0.0, -5.0, 0, 0, 360, 0.85)
    P(744, 0.0, -5.0, 0.3, -5, 360, 1.15)              # glad hopp
    P(750, 0.0, -5.0, 0, 0, 360, 0.85)
    P(756, 0.0, -5.0, 0, 0, 360, 1.03)
    P(FRAME_END, 0.0, -5.0, 0, 0, 360, 1.0)


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
    K(bucket_b, 668, loc=(1.7, -2.7, 0), rot=(0, 0, 0))
    K(bucket_b, 672, loc=(1.69, -2.72, 0.85), rot=(0, 0, 0))
    K(bucket_b, 678, loc=(1.25, -3.25, 0.95), rot=(0, 0, 0))
    K(bucket_b, 686, loc=(0.78, -4.05, 1.05), rot=(0, 0, 0))
    K(bucket_b, 694, loc=(0.3, -4.85, 0.95), rot=(0, 0, 0))
    K(bucket_b, 698, loc=(0.3, -4.2, 2.2), rot=(-35, 0, 0))
    K(bucket_b, 702, loc=(0.3, -4.9, 1.8), rot=(80, 0, 0))
    K(bucket_b, 708, loc=(0.3, -4.85, 1.2), rot=(110, 0, 0))
    K(bucket_b, 712, loc=(0.3, -4.85, 1.0), rot=(120, 0, 0))
    K(bucket_b, 720, loc=(1.4, -3.85, 0.9), rot=(120, 0, 0))


def build_paint_fx(coll, paint, boy, girl, cam_end):
    # Gutten kaster maling rundt seg fra balja
    for i, (ft, tgt) in enumerate(((104, (-2.6, -1.4)), (122, (-0.5, -2.0)), (140, (-2.2, 1.8)))):
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
        floor_puddle(f"Handavtrykk_{i}", coll, paint, (x, -1.45), f, size=0.16, grow=3)

    # Plask i balja + malingsdrakt
    splash("Sprut_Balje_V", coll, paint, (-0.2, 0.4, 0.6), 246, toward_x=-1, count=8, seed=20)
    splash("Sprut_Balje_H", coll, paint, (0.2, 0.4, 0.6), 246, toward_x=1, count=8, seed=21)
    floor_puddle("Dam_Balje", coll, paint, (0.0, 0.15), 248, size=0.75, grow=20)
    build_paint_coat(boy, coll, paint, 278)
    floor_puddle("Dam_Gutt_Drypp", coll, paint, (-1.0, 0.25), 288, size=0.45, grow=25)
    splash("Sprut_Rister_V", coll, paint, (-1.0, 0.4, 1.4), 292, toward_x=-1, count=10, seed=22)
    splash("Sprut_Rister_H", coll, paint, (-1.0, 0.4, 1.4), 292, toward_x=1, count=10, seed=23)

    # Gutten kaster tilbake: treffer jenta
    throw_blob("Klatt_GuttTilJente", coll, paint, (-0.35, 0.4, 1.75), (1.62, 0.35, 1.1), 316, 326)
    splat_on(girl, "Flekk_Jente", coll, paint, 326, (0.0, 1.1))
    splash("Sprut_Jente", coll, paint, (1.6, 0.25, 1.1), 326, toward_x=-1, seed=24)
    floor_puddle("Dam_Jente", coll, paint, (1.5, -0.1), 328, size=0.3)

    # Jenta kaster med spann, bommer
    throw_blob("Klatt_JenteTilGutt", coll, paint, (2.55, 0.95, 1.8), (-1.3, 0.3, 0.05), 386, 396)
    floor_puddle("Dam_Bom", coll, paint, (-1.3, 0.3), 396, size=0.5, grow=10)
    splash("Sprut_Bom", coll, paint, (-1.3, 0.3, 0.05), 396, toward_x=-1, seed=25)
    floor_puddle("Dam_Spann_Jente", coll, paint, (-1.85, -1.75), 412, size=0.45, grow=25)

    # Avslutning: maling i kamera, tørkes av
    fwd = cam_end.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    lens = cam_end.location + fwd * 0.3
    throw_blob("Klatt_IKamera", coll, paint, (0.3, -4.9, 1.9), tuple(lens), 702, 708, height=0.35)
    lens_paint(cam_end, coll, paint, 708, 716, 724)


def lens_paint(cam, coll, mat, f_hit, f_wipe0, f_wipe1):
    """Maling som treffer linsa (foreldret til kamera) og tørkes av mot høyre."""
    blobs = [((0, 0), (0.26, 0.17)), ((-0.14, 0.07), (0.1, 0.08)),
             ((0.13, -0.07), (0.11, 0.07)), ((0.06, 0.1), (0.08, 0.06))]
    for i, ((x, y), (sx, sy)) in enumerate(blobs):
        ob = blob_mesh(f"Kamera_Maling_{i}", coll, mat)
        ob.parent = cam
        z = -0.2 + i * 0.002
        pop(ob, f_hit + (i > 0), full=(sx, sy, 0.004), overshoot=1.0 if i == 0 else 1.2)
        key(ob, f_wipe0, loc=(x, y, z))
        key(ob, f_wipe1, loc=(x + 0.65, y, z))
    for i, x in enumerate((-0.06, 0.03, 0.08)):        # drypp som renner nedover
        ob = blob_mesh(f"Kamera_Drypp_{i}", coll, mat)
        ob.parent = cam
        pop(ob, f_hit + 2, full=(0.012, 0.02, 0.004), overshoot=1.0)
        key(ob, f_hit + 2, loc=(x, -0.02, -0.199))
        key(ob, f_wipe0, loc=(x, -0.07 - 0.01 * i, -0.199))
        key(ob, f_wipe1, loc=(x + 0.65, -0.07 - 0.01 * i, -0.199))


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
        "wide": cam("CAM_01_Wide", (0, -9.5, 2.4), (0.2, 0, 1.0), 32),
        "medium": cam("CAM_02_Medium", (1.6, -5.0, 1.7), (0.6, 0.4, 1.1), 35),
        "deep": cam("CAM_03_Dyp", (0.5, -8.5, 1.2), (0, 1.5, 1.0), 30),
        "end": cam("CAM_04_Ende", (0, -7.5, 1.5), (0.3, -3.5, 1.25), 24),
    }

    scene = bpy.context.scene
    shots = [
        (1, "wide", "SH010 Gutten leker og søler"),
        (212, "medium", "SH020 Spark, hodet ned i balja"),
        (296, "wide", "SH030 Malingskamp og jakt ut"),
        (452, "deep", "SH040 Jakt dypt i rommet, sklir, moro"),
        (662, "end", "SH060 Maling i kamera, tørkes av, smil"),
    ]
    for f, cam_key, label in shots:
        m = scene.timeline_markers.new(label, frame=f)
        m.camera = cams[cam_key]
    scene.camera = cams["wide"]
    return cams


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

    paint = material("M_Maling", PAINT, rough=0.12)
    metal = material("M_Metall", METAL, rough=0.3, metallic=1.0)

    boy = build_character("Gutt", "GUTT", BLACK, c_char, c_label)
    girl = build_character("Jente", "JENTE", WHITE, c_char, c_label)
    tub = build_bucket("Balje", c_props, paint, metal, r1=0.4, r2=0.47, depth=0.6)
    bucket_b = build_bucket("Spann_Gutt", c_props, paint, metal)
    bucket_g = build_bucket("Spann_Jente", c_props, paint, metal)
    build_smile(girl, c_char, 734)

    _last_rz.clear()
    animate_boy(boy)
    animate_girl(girl)
    animate_props(tub, bucket_g, bucket_b)
    cams = build_cameras(c_cam)
    build_paint_fx(c_fx, paint, boy, girl, cams["end"])
    setup_render()

    args = parse_args()
    if "save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args["save"]))
        print("Lagret:", args["save"])


if __name__ == "__main__":
    main()
