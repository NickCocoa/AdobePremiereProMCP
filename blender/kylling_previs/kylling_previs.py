"""
Kylling-previs: to blokk-karakterer som erter hverandre og kaster maling.

Kjør i Blender (4.x / 5.x):
  * Scripting-fanen -> Open -> denne fila -> Run Script
  * eller fra terminal:
      blender -b -P kylling_previs.py -- --save kylling_previs.blend

Skriptet tømmer scenen og bygger alt på nytt hver gang det kjøres.

Karakterer (blokking):
  GUTT  = svart kube  (gul kylling i oransje snekkerbukse)
  JENTE = hvit kube   (gul kylling i korall kjole med sløyfe)
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
FRAME_END = 288  # 12 sek

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


def pose(ob, f, x, y, z=0.0, rx=0.0, rz=0.0, sq=1.0):
    """Karakter-positur. rx>0 = len fremover, rx<0 = len bakover.
    sq = squash/stretch (z-skala), xy kompenseres for volum."""
    xy = 1.0 / math.sqrt(sq)
    key(ob, f, loc=(x, y, z), rot=(rx, 0.0, rz), scale=(xy, xy, sq))


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
    """Kube 1x1x1 med origo nederst. Alle sider i kroppsfarge, forsiden (-Y) rød."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=bm.verts)
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
    txt.location = (0, 0, 1.45)
    txt.rotation_euler = (math.radians(90), 0, 0)
    c = txt.constraints.new("COPY_LOCATION")
    c.target, c.use_offset = ob, True
    c.use_z = False
    txt.hide_render = True
    return ob


def build_bucket(name, coll, paint_mat, metal_mat):
    """Malingsspann, origo midt i bunnen, åpning opp (+Z)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.19,
                          radius2=0.23, depth=0.36)
    bmesh.ops.translate(bm, vec=(0, 0, 0.18), verts=bm.verts)
    bm.normal_update()
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=top, context="FACES_ONLY")
    ob = mesh_object(name, bm, coll, [metal_mat])
    smooth(ob)
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.012

    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=0.215)
    paint = mesh_object(name + "_Maling", bm, coll, [paint_mat])
    paint.parent = ob
    paint.location = (0, 0, 0.3)
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


def splat_on(target, name, coll, mat, f_hit, local_xz, size=(0.24, 0.2)):
    """Flat malingsflekk på forsiden (lokal -Y) av en karakter."""
    ob = blob_mesh(name, coll, mat)
    ob.parent = target
    ob.location = (local_xz[0], -0.5, local_xz[1])
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
# Animasjon
# --------------------------------------------------------------------------

def animate_boy(b):
    # Gutt (svart) starter til venstre og ser mot høyre (+X)
    P = lambda *a: pose(b, *a)
    P(1, -1.6, 0, 0, 0, 90, 1.0)
    P(10, -1.6, 0, 0, 0, 90, 1.03)
    P(16, -1.6, 0, 0, -5, 90, 0.82)          # antisipasjon
    P(22, -1.1, 0, 0.45, 8, 90, 1.15)        # hopp frem
    P(28, -0.65, 0, 0, 10, 90, 0.85)         # lander nese mot nese
    P(32, -0.65, 0, 0, 6, 90, 1.0)
    for f, rz in ((35, 70), (38, 110), (41, 70), (44, 110), (47, 90)):
        P(f, -0.65, 0, 0, 6, rz, 1.0)        # "nænænæ"-vrikk
    P(50, -0.85, 0, 0, -12, 90, 0.9)         # oppladning til dytt
    P(55, -0.42, 0, 0, 22, 90, 1.1)          # DYTT
    P(60, -0.45, 0, 0, 15, 90, 1.0)
    P(66, -0.6, 0, 0, 0, 90, 0.85)
    P(72, -0.6, 0, 0.5, -10, 90, 1.2)        # skryte-hopp
    P(78, -0.6, 0, 0, 0, 90, 0.8)
    P(82, -0.6, 0, 0, 0, 90, 1.0)
    P(88, -0.6, 0, 0, 0, 10, 1.0)            # snur seg mot publikum
    for f, rz, sq in ((92, -15, 0.95), (96, 25, 1.05), (100, -15, 0.95), (104, 25, 1.05)):
        P(f, -0.6, 0, 0, 0, rz, sq)          # rumpevrikk mot kamera
    P(110, -0.6, 0, 0, 0, 70, 1.0)
    P(114, -0.6, 0, 0, 0, 90, 1.08)          # ser klatten komme
    P(116, -0.6, 0, 0, -22, 90, 0.75)        # TREFF 1
    P(120, -1.0, 0, 0.1, -26, 90, 0.85)
    P(126, -1.1, 0, 0, 5, 90, 1.05)
    P(132, -1.1, 0, 0, 0, 90, 0.95)
    for f, z, sq in ((136, 0.25, 1.15), (140, 0, 0.8), (144, 0.25, 1.15), (148, 0, 0.8)):
        P(f, -1.1, 0, z, 0, 90, sq)          # sint stamping
    P(152, -1.55, -0.25, 0.35, 5, 15, 1.1)   # hopper til spannet sitt
    P(156, -2.0, -0.5, 0, 10, -59, 0.85)
    P(160, -2.0, -0.5, 0, 30, -59, 0.9)      # bøyer seg
    P(164, -2.0, -0.5, 0, -5, -59, 1.05)     # løfter spannet
    P(168, -1.55, -0.25, 0.35, 0, 15, 1.1)
    P(172, -1.1, 0, 0, 0, 90, 0.85)
    P(176, -1.2, 0, 0, -22, 90, 1.15)        # oppladning
    P(180, -1.0, 0, 0, 25, 90, 0.95)         # KAST
    P(184, -1.0, 0, 0, 10, 90, 1.0)
    for f, rx, sq in ((194, -10, 1.1), (198, 0, 0.9), (202, -10, 1.1)):
        P(f, -1.0, 0, 0, rx, 90, sq)         # ler
    P(206, -1.0, 0, 0, 32, 90, 0.85)         # øser maling fra gulvet
    P(212, -1.1, 0, 0, -20, 90, 1.15)
    P(216, -0.95, 0, 0, 22, 90, 0.95)        # KAST (samtidig)
    P(226, -0.95, 0, 0, 8, 90, 1.0)
    P(228, -0.95, 0, 0, -28, 90, 0.75)       # TREFF 2
    P(232, -1.3, 0, 0.05, -30, 90, 0.85)
    P(238, -1.35, 0, 0, 4, 90, 1.05)
    for f, rx, sq in ((242, -12, 1.12), (246, 4, 0.9), (250, -12, 1.12), (254, 4, 0.9)):
        P(f, -1.35, 0, 0, rx, 90, sq)        # ler seg skakk
    P(258, -1.35, 0, 0, 0, 90, 0.8)
    P(264, -1.0, -0.3, 0.55, 0, 35, 1.15)    # hopp til sluttpose
    P(270, -0.65, -0.6, 0, 0, 15, 0.82)
    P(276, -0.65, -0.6, 0, 0, 15, 1.03)
    P(282, -0.65, -0.6, 0, 0, 15, 1.0)
    P(288, -0.65, -0.6, 0, 0, 15, 1.0)


def animate_girl(g):
    # Jente (hvit) starter til høyre og ser mot venstre (-X)
    P = lambda *a: pose(g, *a)
    P(1, 1.6, 0, 0, 0, -90, 1.0)
    P(12, 1.6, 0, 0, 0, -90, 1.03)
    P(18, 1.6, 0, 0, -5, -90, 0.82)
    P(24, 1.1, 0, 0.4, 8, -90, 1.15)
    P(30, 0.65, 0, 0, 8, -90, 0.87)
    P(34, 0.65, 0, 0, -8, -90, 1.0)          # irritert
    P(40, 0.65, 0, 0, -4, -90, 1.02)
    P(46, 0.65, 0, 0, -8, -90, 0.98)
    P(53, 0.65, 0, 0, -2, -90, 1.0)
    P(55, 0.68, 0, 0, -15, -90, 0.85)        # blir dyttet
    P(60, 1.5, 0, 0.2, -28, -90, 1.1)
    P(66, 1.9, 0, 0, 8, -90, 0.8)
    P(72, 1.9, 0, 0, -3, -90, 1.05)
    P(76, 1.9, 0, 0, 0, -90, 1.0)
    P(80, 1.9, 0, 0, 0, 32, 1.0)             # ser spannet
    P(84, 1.95, -0.05, 0, 32, 32, 0.88)      # bøyer seg
    P(90, 1.9, 0, 0, -5, 32, 1.05)           # løfter
    P(96, 1.9, 0, 0, 0, -90, 1.0)
    P(102, 2.0, 0, 0, -22, -90, 1.15)        # oppladning
    P(106, 1.85, 0, 0, 25, -90, 0.92)        # KAST
    P(112, 1.85, 0, 0, 10, -90, 1.0)
    P(118, 1.85, 0, 0, 0, -90, 0.85)
    P(124, 1.85, 0, 0.5, -10, -90, 1.2)      # jubel-hopp
    P(130, 1.85, 0, 0, 0, -90, 0.82)
    P(136, 1.85, 0, 0, 0, -90, 1.0)
    for f, rz, sq in ((142, -75, 1.04), (148, -105, 0.96), (154, -75, 1.04),
                      (160, -105, 0.96), (166, -90, 1.0)):
        P(f, 1.85, 0, 0, 0, rz, sq)          # seiersdans
    P(172, 1.9, 0, 0, 0, -20, 1.0)           # skryter til kamera
    P(182, 1.9, 0, 0, 0, -70, 1.0)
    P(186, 1.9, 0, 0, 0, -90, 1.1)
    P(190, 1.9, 0, 0, -22, -90, 0.75)        # TREFF 1
    P(194, 2.35, 0, 0.1, -26, -90, 0.85)
    P(200, 2.1, 0, 0, 5, -90, 1.05)
    P(204, 2.0, 0, 0, 0, -90, 0.95)
    P(206, 2.0, 0, 0, 32, -90, 0.85)         # øser maling
    P(212, 2.1, 0, 0, -20, -90, 1.15)
    P(216, 1.95, 0, 0, 22, -90, 0.95)        # KAST (samtidig)
    P(226, 1.95, 0, 0, 8, -90, 1.0)
    P(228, 1.95, 0, 0, -28, -90, 0.75)       # TREFF 2
    P(232, 2.3, 0, 0.05, -30, -90, 0.85)
    P(238, 2.35, 0, 0, 4, -90, 1.05)
    for f, rx, sq in ((244, -12, 1.12), (248, 4, 0.9), (252, -12, 1.12), (256, 4, 0.9)):
        P(f, 2.35, 0, 0, rx, -90, sq)
    P(258, 2.35, 0, 0, 0, -90, 0.8)
    P(264, 1.5, -0.3, 0.55, 0, -35, 1.15)
    P(270, 0.65, -0.6, 0, 0, -15, 0.82)
    P(276, 0.65, -0.6, 0, 0, -15, 1.03)
    P(282, 0.65, -0.6, 0, 0, -15, 1.0)
    P(288, 0.65, -0.6, 0, 0, -15, 1.0)


def animate_buckets(bucket_g, bucket_b):
    K = key
    # Jentas spann: står på gulvet, plukkes opp, kastes, slippes på siden
    K(bucket_g, 1, loc=(2.55, -0.85, 0), rot=(0, 0, 0))
    K(bucket_g, 84, loc=(2.55, -0.85, 0), rot=(0, 0, 0))
    K(bucket_g, 90, loc=(2.22, -0.51, 0.45), rot=(0, 0, 0))
    K(bucket_g, 96, loc=(1.3, 0, 0.55), rot=(0, 0, 0))
    K(bucket_g, 102, loc=(2.15, 0, 1.45), rot=(0, 35, 0))
    K(bucket_g, 106, loc=(1.3, 0, 1.1), rot=(0, -75, 0))
    K(bucket_g, 112, loc=(1.35, 0, 0.7), rot=(0, -110, 0))
    K(bucket_g, 124, loc=(1.35, 0, 1.2), rot=(0, -100, 0))
    K(bucket_g, 127, loc=(2.0, -0.4, 0.9), rot=(40, -40, 0))
    K(bucket_g, 131, loc=(2.5, -0.75, 0.23), rot=(90, 0, 25))
    K(bucket_g, 134, loc=(2.52, -0.77, 0.3), rot=(85, 0, 28))
    K(bucket_g, 137, loc=(2.53, -0.78, 0.23), rot=(90, 0, 30))

    # Guttens spann
    K(bucket_b, 1, loc=(-2.55, -0.85, 0), rot=(0, 0, 0))
    K(bucket_b, 160, loc=(-2.55, -0.85, 0), rot=(0, 0, 0))
    K(bucket_b, 164, loc=(-2.45, -0.78, 0.45), rot=(0, 0, 0))
    K(bucket_b, 168, loc=(-1.39, -0.83, 0.8), rot=(0, 0, 0))
    K(bucket_b, 172, loc=(-0.5, 0, 0.55), rot=(0, 0, 0))
    K(bucket_b, 176, loc=(-1.35, 0, 1.45), rot=(0, -35, 0))
    K(bucket_b, 180, loc=(-0.45, 0, 1.1), rot=(0, 75, 0))
    K(bucket_b, 186, loc=(-0.5, 0, 0.7), rot=(0, 110, 0))
    K(bucket_b, 192, loc=(-0.9, -0.3, 0.9), rot=(40, 40, 0))
    K(bucket_b, 197, loc=(-1.55, -0.85, 0.23), rot=(90, 0, -25))
    K(bucket_b, 200, loc=(-1.56, -0.86, 0.3), rot=(85, 0, -28))
    K(bucket_b, 203, loc=(-1.57, -0.87, 0.23), rot=(90, 0, -30))


def build_paint_fx(coll, paint, boy, girl):
    # Treff 1: Jenta kaster på gutten
    throw_blob("Klatt_A_JenteTilGutt", coll, paint, (1.3, 0, 1.15), (-0.08, 0, 0.6), 106, 116)
    splat_on(boy, "Flekk_Gutt_1", coll, paint, 116, (0.0, 0.55))
    splash("Sprut_A", coll, paint, (-0.1, -0.1, 0.6), 116, toward_x=1, seed=1)
    floor_puddle("Dam_A", coll, paint, (-0.2, -0.65), 118, size=0.3)

    # Treff 2: Gutten kaster på jenta
    throw_blob("Klatt_B_GuttTilJente", coll, paint, (-0.45, 0, 1.15), (1.38, 0, 0.6), 180, 190)
    splat_on(girl, "Flekk_Jente_1", coll, paint, 190, (0.0, 0.55))
    splash("Sprut_B", coll, paint, (1.4, -0.1, 0.6), 190, toward_x=-1, seed=2)
    floor_puddle("Dam_B", coll, paint, (1.5, -0.65), 192, size=0.3)

    # Malingskrig: begge kaster samtidig, klattene krysser hverandre
    throw_blob("Klatt_C_GuttTilJente", coll, paint, (-0.45, 0, 1.15), (1.43, 0, 0.85),
               216, 228, height=0.5, side=0.25)
    throw_blob("Klatt_D_JenteTilGutt", coll, paint, (1.45, 0, 1.15), (-0.43, 0, 0.85),
               216, 228, height=0.5, side=-0.25)
    splat_on(girl, "Flekk_Jente_2", coll, paint, 228, (0.2, 0.82), size=(0.17, 0.15))
    splat_on(boy, "Flekk_Gutt_2", coll, paint, 228, (-0.2, 0.82), size=(0.17, 0.15))
    splash("Sprut_C", coll, paint, (1.45, -0.1, 0.85), 228, toward_x=-1, seed=3)
    splash("Sprut_D", coll, paint, (-0.45, -0.1, 0.85), 228, toward_x=1, seed=4)

    # Søl fra spannene som slippes (som på referansebildene)
    floor_puddle("Dam_Spann_Jente", coll, paint, (2.5, -1.3), 133, size=0.55, grow=30)
    floor_puddle("Dam_Spann_Gutt", coll, paint, (-1.55, -1.4), 200, size=0.55, grow=30)


# --------------------------------------------------------------------------
# Kamera og shots
# --------------------------------------------------------------------------

def build_cameras(coll):
    def cam(name, loc, target, lens):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.passepartout_alpha = 0.85
        ob = bpy.data.objects.new(name, cd)
        coll.objects.link(ob)
        ob.location = loc
        look_at(ob, target)
        return ob

    cams = {
        "wide": cam("CAM_01_Wide", (0, -8.5, 2.0), (0.2, 0, 0.7), 32),
        "girl": cam("CAM_02_Jente_OTS", (-2.3, -3.2, 1.3), (1.9, 0, 0.75), 42),
        "boy": cam("CAM_03_Gutt_OTS", (2.8, -3.4, 1.3), (-1.2, -0.2, 0.7), 40),
        "hero": cam("CAM_04_Hero", (0, -6.2, 1.1), (0, -0.6, 0.6), 38),
    }

    scene = bpy.context.scene
    shots = [
        (1, "wide", "SH010 Erting og dytt"),
        (74, "girl", "SH020 Jenta henter spann og kaster"),
        (108, "boy", "SH030 Gutten blir truffet, henter spann"),
        (178, "girl", "SH040 Jenta blir truffet"),
        (200, "wide", "SH050 Malingskrig"),
        (258, "hero", "SH060 Sluttpose"),
    ]
    for f, cam_key, label in shots:
        m = scene.timeline_markers.new(label, frame=f)
        m.camera = cams[cam_key]
    scene.camera = cams["wide"]


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
    bucket_b = build_bucket("Spann_Gutt", c_props, paint, metal)
    bucket_g = build_bucket("Spann_Jente", c_props, paint, metal)

    animate_boy(boy)
    animate_girl(girl)
    animate_buckets(bucket_g, bucket_b)
    build_paint_fx(c_fx, paint, boy, girl)
    build_cameras(c_cam)
    setup_render()

    args = parse_args()
    if "save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args["save"]))
        print("Lagret:", args["save"])


if __name__ == "__main__":
    main()
