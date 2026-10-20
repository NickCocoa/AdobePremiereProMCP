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
import os
import random
import sys
import tempfile
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

FPS = 24
FRAME_START = 1
PLAY = 990        # leken etter klemmen: hoppeklem, riste av, hopp, pladask
PARTY = 1100      # hun begynner å danse: lyset dempes, strobelys
DANCE = 1160      # én og én danser de mot kamera
FRAME_END = 1350  # før klipp (CUTS) og pauser (HOLDS)
BEAT = 12         # 120 BPM ved 24 fps: festen og dansen ligger på taktslagene

# Karakter-proporsjoner (meter): kyllingform med barnslige proporsjoner,
# eggformet kropp og stort hode. Total høyde CHAR_H, origo nederst.
CHAR_W = 0.7   # bredde (kropp)
CHAR_D = 0.5   # dybde, brukes til å ligge på gulvet
CHAR_H = 1.7   # høyde
FRONT = CHAR_D / 2  # omtrentlig avstand fra senter til forsiden
LEAN = 0.7     # demper lening, høye figurer vipper mye i toppen
# Ellipsoider (senter-z, radius x, radius y, radius z)
# Proporsjoner fra karakterarkene: hodet er omtrent halve høyden, liten kropp,
# korte tykke bein og store tunge støvler.
BODY = (0.52, 0.34, 0.30, 0.32)
HEAD = (1.12, 0.46, 0.40, 0.50)
EYE_Z = 1.20   # øyehøyde, kameraer og fokus sikter hit
MOUTH_Z = 0.96
LIE_LIFT = HEAD[2] + 0.02 - 0.25  # ekstra høyde når de ligger, så det store hodet ikke går i gulvet

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


def front_mask_material(name, body_color, rough=0.45):
    """Kroppsfarge med rødt ansikt og mage der flaten peker fremover (lokal -Y).
    Myk overgang styrt av objektets normal, uavhengig av hvor tett meshen er."""
    m = material(name, body_color, rough)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = -0.77, -0.73
    rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 1.0, 0.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*body_color, 1.0)
    mix.inputs["B"].default_value = (*RED, 1.0)
    nt.links.new(tex.outputs["Normal"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
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
POSE_LOG = {}  # figurnavn -> liste med positurer, brukes til forventning og settle


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
    if raw:                                            # det store hodet skal ikke gå gjennom gulvet
        z += LIE_LIFT * abs(math.sin(math.radians(rx)))
    POSE_LOG.setdefault(ob.name, []).append((f, x, y, z, rx if raw else rx * LEAN, ry, rz, sq, raw))
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
    area("Lys_Rim", (2.0, 5.0, 5.0), (0, 0, 0.8), 1100, 3.0, (1.0, 0.92, 0.80))

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

def ellipsoid_bm(bm, ell, grow=0.0, segs=(48, 28)):
    """Legg til en ellipsoide (senter-z, rx, ry, rz) i bm."""
    zc, rx, ry, rz = ell
    geom = bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    verts = geom["verts"]
    bmesh.ops.scale(bm, vec=(rx + grow, ry + grow, rz + grow), verts=verts)
    bmesh.ops.translate(bm, vec=(0, 0, zc), verts=verts)
    return verts


def surface_point(phi, z, grow=0.0):
    """Punkt og normal på kyllingens overflate i høyde z, vinkel phi rundt Z
    (0 = forsiden (-Y), 90 = høyre side (+X), 180 = ryggen). Lokale koordinater."""
    best = None
    for zc, rx, ry, rz in (BODY, HEAD):
        t = 1.0 - ((z - zc) / rz) ** 2
        if t <= 0.0:
            continue
        a, b = rx * math.sqrt(t), ry * math.sqrt(t)
        p = Vector((a * math.sin(math.radians(phi)), -b * math.cos(math.radians(phi)), z))
        if best is None or p.xy.length > best[0].xy.length:
            n = Vector((p.x / rx ** 2, p.y / ry ** 2, (z - zc) / rz ** 2)).normalized()
            best = (p, n)
    p, n = best
    return p + n * grow, n


def build_character(name, label, body_color, coll, label_coll):
    """Kylling med origo nederst: eggformet kropp og stort hode i kroppsfarge,
    rød forside (ansikt og mage) som viser hvilken vei den ser."""
    bm = bmesh.new()
    ellipsoid_bm(bm, BODY)
    ellipsoid_bm(bm, HEAD)
    bm.normal_update()
    for f in bm.faces:
        f.material_index = 1                           # kropp med rød forside (myk maske)
    ob = mesh_object(name, bm, coll, [
        material(f"M_{name}_Kropp", body_color, rough=0.45),   # vinger, tust
        front_mask_material(f"M_{name}_Forside", body_color),
    ])
    smooth(ob)

    orange = bpy.data.materials.get("M_Nese") or material("M_Nese", (1.0, 0.42, 0.18), rough=0.35)
    blush = bpy.data.materials.get("M_Rodme") or material("M_Rodme", (1.0, 0.35, 0.35), rough=0.6)
    boot_mat = bpy.data.materials.get("M_Stovel") or material("M_Stovel", (0.32, 0.16, 0.07), rough=0.55)
    sole_mat = bpy.data.materials.get("M_Sale") or material("M_Sale", (0.10, 0.06, 0.03), rough=0.7)
    # Liten nese og rosa kinn
    p, n = surface_point(0, 1.09)
    nose = blob_mesh(f"{name}_Nese", coll, orange)
    nose.parent, nose.location, nose.scale = ob, p - n * 0.015, (0.05, 0.035, 0.035)
    for side in (-1, 1):
        p, n = surface_point(42 * side, 1.02)
        ck = blob_mesh(f"{name}_Kinn_{'V' if side < 0 else 'H'}", coll, blush)
        ck.parent, ck.location = ob, p - n * 0.01
        ck.rotation_euler = n.to_track_quat("-Y", "Z").to_euler()
        ck.scale = (0.1, 0.012, 0.075)
    # Korte bein og store støvler (støvlene tråkker, se run())
    boots = {}
    for side in (-1, 1):
        tag = "V" if side < 0 else "H"
        leg = cyl_mesh(f"{name}_Bein_{tag}", coll, 0.075, 0.07, 0.22, ob.data.materials[0])
        leg.parent, leg.location = ob, (0.15 * side, 0, 0.12)
        boot = blob_mesh(f"{name}_Stovel_{tag}", coll, boot_mat)
        boot.parent, boot.location, boot.scale = ob, (0.15 * side, -0.06, 0.085), (0.135, 0.21, 0.09)
        sole = blob_mesh(f"{boot.name}_Sale", coll, sole_mat)
        sole.parent, sole.location, sole.scale = boot, (0, 0, -0.55), (1.05, 1.03, 0.35)
        boots[side] = boot
    BOOTS[name] = boots

    # Hår og tilbehør henger på svingpunkter som får etterslep (se hair_follow_through())
    top = HEAD[0] + HEAD[3]
    pivots = []
    if name == "Jente":                                # musefletter, hårbånd med sløyfe, kjole
        bow = bpy.data.materials.get("M_Sloyfe") or material("M_Sloyfe", (1.0, 0.25, 0.3), rough=0.4)
        for side in (-1, 1):
            tag = "V" if side < 0 else "H"
            pv = empty(f"{name}_Flette_Pivot_{tag}", coll, (0.4 * side, 0.05, 1.32), ob)
            for k in range(5):                         # dusk av hårstrå
                a = math.radians(-60 + k * 30)
                tuft = blob_mesh(f"{name}_Flette_{tag}_{k}", coll, ob.data.materials[0])
                tuft.parent = pv
                tuft.location = (side * 0.13 * math.cos(a) + side * 0.06, 0, 0.13 * math.sin(a))
                tuft.scale = (0.12, 0.05, 0.035)
                tuft.rotation_euler = (0, -side * a, 0)
            pivots.append(pv)
        pv = empty(f"{name}_Sloyfe_Pivot", coll, (0, 0.0, top - 0.05), ob)
        band = cyl_mesh(f"{name}_Haarbaand", coll, HEAD[1] - 0.06, HEAD[1] - 0.09, 0.07, bow, segs=48, caps=False)
        band.modifiers.new("Tykkelse", "SOLIDIFY").thickness = 0.02
        band.parent, band.location = ob, (0, 0.04, top - 0.16)
        band.scale = (1.0, (HEAD[2] + 0.012) / (HEAD[1] + 0.012) * 0.9, 1.0)
        band.rotation_euler = (math.radians(-18), 0, 0)
        for side in (-1, 1):
            b = blob_mesh(f"{name}_Sloyfe_{'V' if side < 0 else 'H'}", coll, bow)
            b.parent = pv
            b.location = (0.12 * side, 0.0, 0.02)
            b.scale = (0.12, 0.05, 0.08)
            b.rotation_euler = (0, math.radians(-20 * side), 0)
        knot = blob_mesh(f"{name}_Sloyfe_Knute", coll, bow)
        knot.parent, knot.location, knot.scale = pv, (0, 0.0, 0.0), (0.05, 0.05, 0.05)
        pivots.append(pv)
        # Kjole med volang: kort, utsvingt skjørt i kroppsfarge med rød forside
        skirt = cyl_mesh(f"{name}_Kjole", coll, 0.44, 0.33, 0.3, ob.data.materials[1], segs=48)
        skirt.parent, skirt.location = ob, (0, 0, 0.22)
        ruffle = cyl_mesh(f"{name}_Volang", coll, 0.47, 0.44, 0.05, ob.data.materials[1], segs=48)
        ruffle.parent, ruffle.location = ob, (0, 0, 0.2)
    else:                                              # stor, bustete hårtust
        pv = empty(f"{name}_Tust_Pivot", coll, (0, 0.03, top - 0.06), ob)
        rnd = random.Random(3)
        for i in range(9):
            tilt_x, tilt_y = rnd.uniform(-35, 20), -50 + i * 12.5
            bm = bmesh.new()
            h = rnd.uniform(0.18, 0.3)
            bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.04, radius2=0.0, depth=h)
            bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
            tuft = mesh_object(f"{name}_Tust_{i}", bm, coll, [ob.data.materials[0]])
            tuft.parent = pv
            tuft.location = (rnd.uniform(-0.05, 0.05), rnd.uniform(-0.04, 0.04), 0)
            tuft.rotation_euler = (math.radians(tilt_x), math.radians(tilt_y), 0)
        pivots.append(pv)
    HAIR[name] = pivots

    # Rekvisitter fra prop-arket i lomma
    props_in_pocket(ob, coll)

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


ARMS = {}  # figurnavn -> {-1: venstre arm, 1: høyre arm}
BOOTS = {}  # figurnavn -> {-1: venstre støvel, 1: høyre støvel}
HAIR = {}   # figurnavn -> svingpunkter for hår og tilbehør


def cyl_mesh(name, coll, r1, r2, h, mat, segs=24, caps=True):
    """Sylinder/kjegle med origo nederst (caps=False gir et åpent rør, f.eks. et bånd)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=segs, radius1=r1, radius2=r2, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
    ob = mesh_object(name, bm, coll, [mat])
    smooth(ob)
    return ob


def props_in_pocket(ob, coll):
    """Gutten: fastnøkkel og rød tusj i lomma. Jenta: pensel og prestekrage."""
    metal = bpy.data.materials.get("M_Prop_Metall") or material("M_Prop_Metall", (0.7, 0.7, 0.72), 0.3, 1.0)
    red = bpy.data.materials.get("M_Prop_Rod") or material("M_Prop_Rod", (0.85, 0.05, 0.05), 0.35)
    wood = bpy.data.materials.get("M_Prop_Skaft") or material("M_Prop_Skaft", (0.85, 0.15, 0.1), 0.5)
    bristle = bpy.data.materials.get("M_Prop_Bust") or material("M_Prop_Bust", (0.45, 0.28, 0.12), 0.7)
    petal = bpy.data.materials.get("M_Prop_Kronblad") or material("M_Prop_Kronblad", (0.95, 0.95, 0.92), 0.5)
    yellow = bpy.data.materials.get("M_Prop_Gul") or material("M_Prop_Gul", (1.0, 0.75, 0.05), 0.5)
    pocket = lambda side: surface_point(32 * side, 0.6)
    if ob.name == "Gutt":
        p, n = pocket(-1)                              # fastnøkkel
        w = cyl_mesh(f"{ob.name}_Fastnokkel", coll, 0.02, 0.02, 0.2, metal, segs=8)
        w.parent, w.location = ob, p - n * 0.02 + Vector((0, 0, -0.05))
        head = blob_mesh(f"{ob.name}_Fastnokkel_Hode", coll, metal)
        head.parent, head.location, head.scale = w, (0, 0, 0.2), (0.045, 0.015, 0.035)
        p, n = pocket(1)                               # rød tusj
        pen = cyl_mesh(f"{ob.name}_Tusj", coll, 0.022, 0.022, 0.17, red, segs=10)
        pen.parent, pen.location = ob, p - n * 0.02 + Vector((0, 0, -0.04))
    else:
        p, n = pocket(1)                               # pensel
        br = cyl_mesh(f"{ob.name}_Pensel", coll, 0.012, 0.012, 0.22, wood, segs=8)
        br.parent, br.location = ob, p - n * 0.02 + Vector((0, 0, -0.05))
        tip = blob_mesh(f"{ob.name}_Pensel_Bust", coll, bristle)
        tip.parent, tip.location, tip.scale = br, (0, 0, 0.24), (0.025, 0.015, 0.04)
        p, n = pocket(-1)                              # prestekrage
        f = blob_mesh(f"{ob.name}_Prestekrage", coll, yellow)
        f.parent, f.location, f.scale = ob, p - n * 0.04 + Vector((0, 0, 0.08)), (0.025, 0.012, 0.025)
        f.rotation_euler = n.to_track_quat("-Y", "Z").to_euler()
        for k in range(8):
            a = math.radians(k * 45)
            pt = blob_mesh(f"{ob.name}_Prestekrage_{k}", coll, petal)
            pt.parent = f
            pt.location = (math.cos(a) * 2.2, 0, math.sin(a) * 2.2)
            pt.scale = (1.4, 0.5, 0.55)
            pt.rotation_euler = (0, -a, 0)


def build_arms(ob, coll):
    """To vinger i kroppsfarge med fjærtupp som «hånd», med hele sekvensen.
    Origo i skulderen, vingen peker opp (+Z) i hvilestilling uten rotasjon."""
    arms = {}
    for side in (-1, 1):
        bm = bmesh.new()
        ellipsoid_bm(bm, (0.19, 0.08, 0.055, 0.21), segs=(16, 10))
        arm = mesh_object(f"{ob.name}_Vinge_{'V' if side < 0 else 'H'}", bm, coll, [ob.data.materials[0]])
        smooth(arm)
        arm.parent = ob
        arm.location = (side * (BODY[1] + 0.05), 0, 0.62)
        for k, tilt in enumerate((-28, 0, 28)):        # tre fjærtupper
            bm = bmesh.new()
            ellipsoid_bm(bm, (0.07, 0.045, 0.03, 0.09), segs=(12, 8))
            tip = mesh_object(f"{arm.name}_Fjaer_{k}", bm, coll, [ob.data.materials[0]])
            smooth(tip)
            tip.parent = arm
            tip.location = (0.0, 0, 0.36)
            tip.rotation_euler = (0, math.radians(tilt), 0)
        arms[side] = arm
    ARMS[ob.name] = arms
    return arms


# Armposer som (rx, ry, rz) i grader for side s (-1 venstre, 1 høyre).
# Fra hengende arm: +rx svinger fremover, ry løfter ut til siden.
ARM_POSES = {
    "heng": lambda s: (0, 170 * s, 0),
    "ut": lambda s: (0, 95 * s, 0),          # rett ut til siden
    "halvut": lambda s: (0, 135 * s, 0),
    "jubel": lambda s: (0, 25 * s, 0),       # opp og ut
    "fram_ned": lambda s: (45, 170 * s, 0),  # øser, maler på gulvet
    "fram": lambda s: (90, 170 * s, 0),      # peker, holder spannet
    "fram_opp": lambda s: (150, 170 * s, 0), # kaster
    "bak": lambda s: (-110, 170 * s, 0),     # lader opp kastet
    "ansikt": lambda s: (155, 160 * s, 0),   # hendene mot ansiktet
    "dukk": lambda s: (170, 150 * s, 0),     # hendene over hodet
    "hofte": lambda s: (-15, 140 * s, 0),
    "mage": lambda s: (35, 175 * s, -20 * s),
    "sint": lambda s: (-20, 165 * s, 0),
    "klem": lambda s: (0, 100 * s, 40 * s),  # rundt ryggen på den andre
}


def arm_key(ob, f, left, right):
    """Key begge armene til ob. left/right er navn i ARM_POSES eller (rx, ry, rz)."""
    for side, p in ((-1, left), (1, right)):
        arm = ARMS[ob.name][side]
        rot = ARM_POSES[p](side) if isinstance(p, str) else p
        arm.rotation_euler = [math.radians(a) for a in rot]
        arm.keyframe_insert("rotation_euler", frame=f)


def arm_beats(ob, beats):
    for f, left, right in beats:
        arm_key(ob, f, left, right)


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


def splat_on(target, name, coll, mat, f_hit, local_xz, size=(0.22, 0.18), phi=None):
    """Flat malingsflekk som ligger på kroppen. local_xz = (x, z) på forsiden,
    eller phi = vinkel rundt kroppen (0 forside, 90 høyre, 180 rygg) med z = local_xz[1]."""
    z = local_xz[1]
    if phi is None:
        p0, _ = surface_point(0, z)
        half = max(abs(surface_point(90, z)[0].x), 0.05)
        phi = math.degrees(math.asin(max(-0.95, min(0.95, local_xz[0] / half))))
    p, n = surface_point(phi, z, grow=0.004)
    ob = blob_mesh(name, coll, mat)
    ob.parent = target
    ob.location = p
    ob.rotation_euler = n.to_track_quat("-Y", "Z").to_euler()
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
    """Malingsdrakt over hode, rygg og skuldre etter at gutten dukkes i balja.
    Forsiden holdes fri, så den røde forsiden alltid synes."""
    mats = list(mat) if isinstance(mat, (list, tuple)) else [mat]
    bm = bmesh.new()
    ellipsoid_bm(bm, BODY, grow=0.035, segs=(48, 28))
    ellipsoid_bm(bm, HEAD, grow=0.035, segs=(48, 28))
    bm.normal_update()
    drop = [f for f in bm.faces if f.normal.y < -0.45 or f.calc_center_median().z < 0.6]
    bmesh.ops.delete(bm, geom=drop, context="FACES_ONLY")
    ob = mesh_object("Gutt_Malingsdrakt", bm, coll, [paint_blend_material("M_Malingsdrakt", mats)])
    smooth(ob)
    ob.parent = target
    pop(ob, f_on, overshoot=1.06)
    # Noen fargeflekker på den røde forsiden i stedet for full drakt
    for i, (xz, size) in enumerate((((-0.22, 1.42), (0.1, 0.08)), ((0.2, 0.7), (0.1, 0.12)),
                                    ((-0.12, 0.45), (0.1, 0.08)))):
        splat_on(target, f"Gutt_Forside_Flekk_{i}", coll, pick(mats, i + 1), f_on, xz, size=size)
    return ob


def paint_blend_material(name, mats):
    """Våt maling i store, flytende fargeflekker (støytekstur), ikke ruter."""
    cols = [tuple(m.diffuse_color[:3]) for m in mats]
    m = material(name, cols[0], rough=0.15)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 1.5
    noise.inputs["Distortion"].default_value = 0.8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    while len(els) < len(cols):
        els.new(0.5)
    for i, (el, c) in enumerate(zip(els, cols)):
        el.position = 0.3 + 0.4 * i / len(cols)        # støyen ligger mest rundt 0,3–0,7
        el.color = (*c, 1.0)
    els[0].position = 0.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def _curve(name, coll, pts, bevel, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1.0)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    cu.materials.append(mat)
    return ob


def _on_surface(name, coll, target, phi, z, inset=0.0):
    """Tomt svingpunkt på kroppens overflate, rettet langs normalen (lokal -Y ut)."""
    p, n = surface_point(phi, z)
    pv = empty(name, coll, tuple(p - n * inset), target)
    pv.rotation_euler = n.to_track_quat("-Y", "Z").to_euler()
    return pv


# Uttrykk: bryn (løft, vinkel innerst ned) og munn (form, skala)
EXPR = {
    "noytral":  dict(brow=(0.0, 0), mouth="smil", ms=(0.7, 0.6)),
    "glad":     dict(brow=(0.025, -4), mouth="smil", ms=(1.0, 1.0)),
    "latter":   dict(brow=(0.035, -8), mouth="aapen", ms=(1.0, 1.0)),
    "overrask": dict(brow=(0.075, -4), mouth="o", ms=(1.0, 1.0)),
    "sjokk":    dict(brow=(0.085, -12), mouth="o", ms=(1.3, 1.5)),
    "sint":     dict(brow=(-0.02, 24), mouth="smil", ms=(0.8, -0.8)),
    "bestemt":  dict(brow=(-0.012, 14), mouth="smil", ms=(0.8, 0.15)),
    "lur":      dict(brow=(0.01, 10), mouth="smil", ms=(0.85, 0.7), sly=True),
    "bekymret": dict(brow=(0.04, -20), mouth="o", ms=(0.6, 0.5)),
    "knip":     dict(brow=(-0.03, 8), mouth="smil", ms=(0.7, 0.15)),
}
FACE = {}  # figurnavn -> dict med bryn og munner


def build_face_rig(target, coll):
    """Bryn og munner fra arkene: kraftige bryn, åpent smil med to fortenner og tunge."""
    brown = bpy.data.materials.get("M_Bryn") or material("M_Bryn", (0.12, 0.06, 0.02), rough=0.6)
    dark = bpy.data.materials.get("M_Munn") or material("M_Munn", (0.22, 0.02, 0.03), rough=0.5)
    tongue = bpy.data.materials.get("M_Tunge") or material("M_Tunge", (0.95, 0.35, 0.4), rough=0.4)
    tooth = bpy.data.materials.get("M_Tann") or material("M_Tann", (0.97, 0.96, 0.92), rough=0.3)
    rig = {"brows": {}}
    for side in (-1, 1):
        tag = "V" if side < 0 else "H"
        pv = _on_surface(f"{target.name}_Bryn_Pivot_{tag}", coll, target, 19 * side, EYE_Z + 0.16, inset=-0.01)
        pts = [(0.075 * math.cos(a), 0, 0.025 * math.sin(a)) for a in [math.pi * (1 - k / 8) for k in range(9)]]
        brow = _curve(f"{target.name}_Bryn_{tag}", coll, pts, 0.016, brown)
        brow.parent = pv
        rig["brows"][side] = brow
    mp = _on_surface(f"{target.name}_Munn_Pivot", coll, target, 0, MOUTH_Z, inset=-0.005)
    smile_pts = []
    for k in range(11):
        a = math.pi + 0.35 + k * (math.pi - 0.7) / 10
        smile_pts.append((0.15 * math.cos(a), 0.012 * abs(math.cos(a)), 0.08 * math.sin(a) + 0.04))
    smile = _curve(f"{target.name}_Munn_Smil", coll, smile_pts, 0.016, dark)
    smile.parent = mp
    opened = blob_mesh(f"{target.name}_Munn_Aapen", coll, dark)
    opened.parent, opened.location = mp, (0, 0, -0.02)
    for name, mat, loc, sc in ((f"{target.name}_Tunge", tongue, (0, -0.25, -0.45), (0.6, 0.4, 0.4)),
                               (f"{target.name}_Tann_V", tooth, (-0.11, -0.5, 0.58), (0.12, 0.35, 0.36)),
                               (f"{target.name}_Tann_H", tooth, (0.11, -0.5, 0.58), (0.12, 0.35, 0.36))):
        part = blob_mesh(name, coll, mat)
        part.parent, part.location, part.scale = opened, loc, sc
    o_mouth = blob_mesh(f"{target.name}_Munn_O", coll, dark)
    o_mouth.parent, o_mouth.location = mp, (0, 0, -0.01)
    rig.update(smile=smile, aapen=opened, o=o_mouth)
    FACE[target.name] = rig


def animate_expressions(ob_name, timeline):
    """Uttrykkene skifter raskt (2 bilder) og holdes til neste: pose-to-pose i ansiktet."""
    rig = FACE[ob_name]
    full = {"smil": None, "aapen": (0.2, 0.03, 0.1), "o": (0.055, 0.03, 0.065)}
    prev = None
    for f, state in timeline:
        for when, st in (((f - 2), prev), (f, state)):
            if st is None:
                continue
            e = EXPR[st]
            lift, tilt = e["brow"]
            for side, brow in rig["brows"].items():
                l, t = lift, tilt
                if e.get("sly"):                       # det ene brynet høyt, det andre lavt
                    l, t = (0.06, -6) if side < 0 else (-0.01, 16)
                brow.location = (0, 0, l)
                brow.rotation_euler = (0, math.radians(-t * side), 0)
                brow.keyframe_insert("location", frame=when)
                brow.keyframe_insert("rotation_euler", frame=when)
            for shape in ("smil", "aapen", "o"):
                obj = rig["smile" if shape == "smil" else shape]
                on = e["mouth"] == shape
                if shape == "smil":
                    sx, sz = e["ms"]
                    obj.scale = (sx, 1, sz) if on else (0, 0, 0)
                    obj.rotation_euler = (0, math.radians(8 if e.get("sly") else 0), 0)
                    obj.keyframe_insert("rotation_euler", frame=when)
                else:
                    sx, sz = e["ms"]
                    obj.scale = (full[shape][0] * sx, full[shape][1], full[shape][2] * sz) if on else (0, 0, 0)
                obj.keyframe_insert("scale", frame=when)
        prev = state
    for obj in (rig["smile"], rig["aapen"], rig["o"]):  # munnen bytter form momentant
        for fc in fcurves_of(obj):
            if fc.data_path == "scale":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


# Uttrykkstidslinje gjennom hele historien (opprinnelige frames)
EXPR_TIMELINE = {
    "Gutt": [(1, "glad"), (76, "overrask"), (88, "latter"), (100, "glad"), (122, "latter"), (152, "bestemt"),
             (204, "latter"), (216, "glad"), (224, "overrask"), (230, "sjokk"), (286, "bekymret"),
             (296, "sint"), (308, "lur"), (318, "latter"), (372, "glad"), (384, "bekymret"), (390, "sjokk"),
             (470, "bestemt"), (578, "sjokk"), (594, "latter"), (620, "glad"), (664, "sint"), (680, "bestemt"),
             (726, "lur"), (746, "sjokk"), (752, "latter"), (790, "noytral"), (866, "latter"), (892, "glad"),
             (906, "latter"), (946, "glad"), (990, "overrask"), (1003, "latter"), (1024, "lur"),
             (1050, "bestemt"), (1064, "lur"), (1073, "sjokk"), (1078, "knip"), (1094, "bekymret"),
             (1100, "glad"), (1130, "lur"), (1142, "latter"), (1172, "bestemt"), (1260, "latter"),
             (1298, "overrask"), (1310, "latter")],
    "Jente": [(1, "glad"), (196, "lur"), (227, "bestemt"), (232, "latter"), (316, "glad"), (324, "overrask"),
              (326, "sjokk"), (336, "sint"), (356, "overrask"), (360, "lur"), (382, "bestemt"), (398, "latter"),
              (460, "glad"), (562, "sjokk"), (586, "latter"), (620, "glad"), (660, "lur"), (672, "latter"),
              (733, "bekymret"), (738, "knip"), (764, "bestemt"), (786, "glad"), (792, "latter"),
              (800, "lur"), (810, "glad"), (852, "overrask"), (868, "latter"), (892, "glad"),
              (910, "latter"), (946, "glad"), (990, "lur"), (998, "latter"), (1050, "glad"),
              (1066, "overrask"), (1080, "latter"), (1100, "glad"), (1220, "latter"), (1298, "overrask"),
              (1310, "latter")],
}


EYES = {}  # figurnavn -> liste med øyeobjekter (hvite og pupiller) til blunking
EYE_SHINE = {}  # figurnavn -> [(pupill, lysrefleks)] til skinnende øyne


def eyes_shine(ob, coll, f0, f1, colors):
    """Øynene skinner: pupillene utvider seg, lysrefleksene vokser og gløder, regnbuen
    speiles i pupillene og små stjerner glitrer rundt øynene."""
    for pupil, glint in EYE_SHINE[ob.name]:
        for obj, k in ((pupil, 1.3), (glint, 1.9)):
            base = tuple(obj.scale)
            for f, m in ((f0 - 3, 1.0), (f0 + 2, k * 1.08), (f0 + 5, k), (f1 - 3, k), (f1 + 3, 1.0)):
                obj.scale = tuple(v * m for v in base)
                obj.keyframe_insert("scale", frame=f)
            obj.scale = base
        for i, col in enumerate(colors):               # regnbuemalingen speiles i pupillen
            a = math.radians(200 + i * 28)
            dot = blob_mesh(f"{pupil.name}_Speiling_{i}", coll, col)
            dot.parent = pupil
            dot.location = (0.55 * math.cos(a), -0.85, 0.55 * math.sin(a))
            pop(dot, f0, full=(0.14, 0.12, 0.14), f_off=f1 + 2, overshoot=1.3)


def sparkle_stars(ob, coll, f0, f1):
    """Små stjerner som glitrer rundt øynene. Keyes i ferdige frames (etter HOLDS),
    så de fortsetter å blinke også mens bildet holdes."""
    shine = bpy.data.materials["M_Glans"]
    rnd = random.Random(4)
    for i, (side, dz) in enumerate(((-1, 0.14), (1, 0.18), (1, -0.02), (-1, 0.02))):
        p, n = surface_point(34 * side, EYE_Z + dz, grow=0.05)
        star = bpy.data.objects.new(f"{ob.name}_Glitter_{i}", None)
        coll.objects.link(star)
        star.parent, star.location = ob, p
        star.rotation_euler = n.to_track_quat("-Y", "Z").to_euler()
        for k, rot in enumerate((0, 90)):              # firtakket stjerne
            arm = blob_mesh(f"{star.name}_{k}", coll, shine)
            arm.parent, arm.scale = star, (0.008, 0.004, 0.05)
            arm.rotation_euler = (0, math.radians(rot), 0)
        t0 = f0 + 2 + i * 2
        star.scale = (0, 0, 0)
        star.keyframe_insert("scale", frame=FRAME_START)
        star.keyframe_insert("scale", frame=t0 - 1)
        for f in range(t0, f1, 4):                     # blinker av og på
            s_ = rnd.uniform(0.9, 1.4) if (f - t0) % 8 == 0 else 0.35
            star.scale = (s_,) * 3
            star.keyframe_insert("scale", frame=f)
        star.scale = (0, 0, 0)
        star.keyframe_insert("scale", frame=f1 + 2)


def build_face(target, coll, gaze):
    """Store øyne fra første bilde. Pupillene følger blikkmålet `gaze`."""
    white = bpy.data.materials.get("M_Oyehvitt") or material("M_Oyehvitt", (0.95, 0.95, 0.95), rough=0.2)
    black = bpy.data.materials.get("M_Pupill") or material("M_Pupill", (0.12, 0.05, 0.015), rough=0.15)  # brun iris
    parts = []
    for side in (-1, 1):
        tag = "V" if side < 0 else "H"
        p, n = surface_point(19 * side, EYE_Z)
        eye = blob_mesh(f"{target.name}_Oye_{tag}", coll, white)
        eye.parent = target
        eye.location = p - n * 0.02
        eye.scale = (0.095, 0.07, 0.115)
        pivot = bpy.data.objects.new(f"{target.name}_Oyepivot_{tag}", None)
        coll.objects.link(pivot)
        pivot.parent = target
        pivot.location = eye.location
        c = pivot.constraints.new("DAMPED_TRACK")
        c.target, c.track_axis = gaze, "TRACK_NEGATIVE_Y"
        c.influence = 0.55                             # pupillen holder seg foran på øyet
        pupil = blob_mesh(f"{target.name}_Pupill_{tag}", coll, black)
        pupil.parent = pivot
        pupil.location = (0, -0.07, 0)
        pupil.scale = (0.052, 0.03, 0.062)
        shine = bpy.data.materials.get("M_Glans") or material("M_Glans", (1, 1, 1), rough=0.1, emission=2.0)
        glint = blob_mesh(f"{target.name}_Glans_{tag}", coll, shine)  # lysrefleks gir liv
        glint.parent = pupil
        glint.location = (0.35, -0.9, 0.4)
        glint.scale = (0.3, 0.3, 0.3)
        EYE_SHINE.setdefault(target.name, []).append((pupil, glint))
        parts += [eye, pupil]
    EYES[target.name] = parts


def blink(ob_name, frames):
    """Rask blunk: øynene klemmes sammen i to bilder."""
    for part in EYES[ob_name]:
        full = tuple(part.scale)
        for f in frames:
            for df, k in ((-1, 1.0), (1, 0.1), (3, 1.0)):
                part.scale = (full[0], full[1], full[2] * k)
                part.keyframe_insert("scale", frame=f + df)
        part.scale = full


# --------------------------------------------------------------------------
# Animasjon
# --------------------------------------------------------------------------

def heading(dx, dy):
    """Retning (rz i grader) som får forsiden (-Y) til å peke langs (dx, dy)."""
    return math.degrees(math.atan2(dx, -dy))


# Personlighet i gangen: broren tung og klumsete, søsteren lett og sprettende
GAIT = {"Gutt": dict(hop=0.75, lean=0.85, swing=32, squash=1.4, waddle=7),
        "Jente": dict(hop=1.3, lean=1.1, swing=55, squash=0.8, waddle=3)}
BOOT_REST = (0.15, -0.06, 0.085)


def key_boot(ob, side, f, y_off=0.0, lift=0.0):
    boot = BOOTS[ob.name][side]
    boot.location = (BOOT_REST[0] * side, BOOT_REST[1] + y_off, BOOT_REST[2] + lift)
    boot.keyframe_insert("location", frame=f)


def run(ob, f0, f1, path, stride=6, lean=22, hop=0.16):
    """Løp langs en polylinje med jevn fart og sprett hvert halve steg."""
    gait = GAIT.get(ob.name, dict(hop=1.0, lean=1.0, swing=45, squash=1.0, waddle=0))
    hop, lean = hop * gait["hop"], lean * gait["lean"]
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
        f = round(f0 + (f1 - f0) * t)
        sq = 0.06 * gait["squash"]
        c = math.cos(math.pi * i / 2)
        waddle = gait["waddle"] * c                    # vagger fra side til side (buer i hodet)
        pose(ob, f, p.x, p.y, hop if up else 0.0, lean, rz, 1 + sq if up else 1 - sq, ry=waddle)
        if ob.name in ARMS:                            # armene svinger i takt med stegene
            sw = gait["swing"] * c
            arm_key(ob, f, (sw, -165, 0), (-sw, 165, 0))
        if ob.name in BOOTS:                           # støvlene tråkker: den som står, glir bakover
            reach = min(0.28, total / n)               # i lokalt rom mens kroppen går fremover
            key_boot(ob, -1, f, -reach * c, 0.09 if i % 4 == 3 else 0.0)
            key_boot(ob, 1, f, reach * c, 0.09 if i % 4 == 1 else 0.0)
    if ob.name in BOOTS:                               # stå i ro før og etter løpet
        for side in (-1, 1):
            key_boot(ob, side, f0 - 2)
            key_boot(ob, side, f1 + 3)


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
    run(b, 388, 440, [(-0.8, 0.4), (-3.0, 0.4), (-13.0, 0.2)])  # flykter helt ut av bildet
    teleport(b, 441, 470, (-13.0, 0.2, 0))

    # SH040: Kommer inn igjen fra høyre og jager henne dypt i rommet og frem
    P(470, 8.5, 0.5, 0, 0, -90)
    run(b, 476, 576, [(8.5, 0.5), (4.5, 3.0), (1.0, 5.0), (-2.5, 5.0),
                      (-3.8, 2.5), (-2.5, 0.0), (-0.2, -1.8)])
    hd = heading(2.3, -1.8)
    P(578, -0.05, -2.0, 0.85, -75, hd, 1.08, raw=True)  # sklir! beina til værs
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
    P(746, 0.95, 0.4, 0, -12, -7, 1.16)                # «oi!»
    P(752, 0.95, 0.4, 0, 12, -7, 0.9)                  # holder seg for munnen
    for i, f in enumerate(range(756, 767, 4)):         # fniser
        P(f, 0.95, 0.4, 0, -8 if i % 2 == 0 else 4, -7, 1.08 if i % 2 == 0 else 0.94)
    teleport(b, 767, 836, (7.5, -4.6, 0))              # godt utenfor bildet til høyre

    # Løper inn og klemmer søsteren, smiler i kamera
    run(b, 836, 868, [(7.5, -4.6), (0.55, -5.0)], lean=18)  # synlig løp inn i bildet
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
    run(g, 400, 452, [(2.95, 0.95), (1.5, 1.6), (-0.3, 1.9), (-3.0, 1.3), (-13.0, 1.5)])  # egen bane
    teleport(g, 453, 456, (-13.0, 1.5, 0))

    # SH040: Kommer først inn fra høyre, løper dypt i rommet og frem
    P(456, 8.5, 0.5, 0, 0, -90)
    run(g, 460, 560, [(8.5, 0.5), (4.5, 3.0), (1.0, 5.0), (-2.5, 5.0),
                      (-3.8, 2.5), (-2.5, 0.0), (-0.8, -1.7)])
    hd = heading(1.7, -1.7)
    P(562, -0.7, -1.9, 0.85, -75, hd, 1.08, raw=True)  # sklir i malingen, beina til værs
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
    P(642, -0.5, -2.9, 0.75, 0, -180, 1.18, spin=True)   # snurrer motsatt vei og litt etter ham
    P(648, -0.5, -2.9, 0, 0, -360, 0.8, spin=True)
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
    P(752, -0.6, -5.5, 0.12, 0, 0, 1.06)               # småhopper ut til siden bak malingen
    P(756, -1.2, -5.8, 0, 0, 0, 0.92)
    P(760, -1.8, -6.0, 0.12, 0, 0, 1.06)
    P(764, -2.2, -6.1, 0, 0, 0, 1.0)                   # skjult bak malingen
    P(767, -2.2, -6.1, 0, 0, 0, 1.0)
    P(770, -1.6, -6.1, 0.14, 0, 0, 1.08)               # småhopper sidelengs inn i bildet
    P(772, -1.2, -6.1, 0, 0, 0, 0.92)
    P(775, -0.6, -6.1, 0.12, 0, 0, 1.06)
    P(778, 0.0, -6.1, 0.05, 10, 0, 1.05)               # TØRKER linsa
    P(786, -0.3, -5.0, 0, 0, 0, 1.0)
    P(792, -0.3, -5.0, 0, -6, 0, 1.1)                  # puh! (lettet)
    P(800, -0.3, -5.0, 0, 0, 0, 0.98)
    P(810, -0.3, -5.0, 0, 0, 0, 1.0)                   # smiler
    P(816, -0.3, -5.0, 0, 0, 0, 0.88)
    P(822, -0.3, -5.0, 0.25, -5, 0, 1.15)              # glad hopp
    P(828, -0.3, -5.0, 0, 0, 0, 0.88)
    P(834, -0.3, -5.0, 0, 0, 0, 1.02)
    P(846, -0.3, -5.0, 0, 0, 0, 1.0)
    P(852, -0.3, -5.0, 0, 0, 25, 1.04)                 # hører ham komme
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


def animate_boy_arms(b):
    """Armene til gutten gjennom historien (løpene keyes i run())."""
    beats = [
        (1, "heng", "heng"),
        (50, "ut", "ut"), (54, "heng", "heng"),                     # bremser
        (60, "jubel", "jubel"), (66, "ut", "ut"), (70, "heng", "heng"),  # piruett
        (76, "fram_ned", "fram_ned"), (84, "fram_ned", "fram_ned"),  # titter nedi
        (88, "jubel", "jubel"),                                      # «jippi!»
    ]
    for ft in (104, 122):                                            # øser og kaster
        beats += [(ft - 10, "fram_ned", "fram_ned"), (ft - 5, "ut", "bak"),
                  (ft, "heng", "fram_opp"), (ft + 4, "heng", "fram")]
    beats += [(148, "heng", "heng"), (152, "fram_ned", "fram_ned")]
    for i, f in enumerate(range(160, 196, 6)):                       # maler med hendene
        beats.append((f, (60 if i % 2 else 25, -170, 0), (25 if i % 2 else 60, 170, 0)))
    beats += [
        (198, "heng", "heng"), (204, "jubel", "jubel"), (210, "heng", "heng"),
        (216, "hofte", "hofte"), (222, "hofte", "hofte"),            # beundrer verket
        (224, "ut", "ut"), (228, "ut", "ut"), (230, "jubel", "jubel"),  # SPARK
    ]
    for i, f in enumerate(range(236, 276, 4)):                       # spreller i balja
        beats.append((f, "ut" if i % 2 else "jubel", "jubel" if i % 2 else "ut"))
    beats += [(280, "jubel", "jubel"), (286, "ut", "ut"), (290, "heng", "heng")]
    for i, f in enumerate(range(292, 304, 2)):                       # rister seg
        beats.append((f, "ut" if i % 2 else "halvut", "halvut" if i % 2 else "ut"))
    beats += [(304, "heng", "heng"),
              (308, "fram_ned", "fram_ned"), (312, "ut", "bak"),     # kaster tilbake
              (316, "heng", "fram_opp"), (322, "heng", "fram")]
    for i, f in enumerate(range(328, 352, 4)):                       # holder seg på magen og ler
        beats.append((f, "mage" if i % 2 else "heng", "mage" if i % 2 else "heng"))
    beats += [(372, "heng", "heng"), (384, "ansikt", "ansikt")]     # uh-oh
    beats += [
        (470, "heng", "heng"),
        (578, "jubel", "jubel"), (582, "ut", "ut"), (594, "ut", "ut"),  # sklir
    ]
    for i, f in enumerate(range(598, 618, 4)):                       # ligger og ler
        beats.append((f, "ut" if i % 2 else "halvut", "ut" if i % 2 else "halvut"))
    beats += [
        (620, "jubel", "jubel"), (626, "heng", "heng"),
        (640, "ut", "ut"), (646, "ut", "ut"), (650, "heng", "heng"),
        (664, "hofte", "hofte"), (674, "hofte", "hofte"),            # blir ertet
        (716, "fram_ned", "fram_ned"), (722, "fram_ned", "fram_ned"),
        (726, "ut", "bak"), (730, "heng", "fram_opp"), (736, "heng", "fram"),
        (742, "heng", "heng"), (746, "ansikt", "ansikt"),             # «oi!»
        (766, "ansikt", "ansikt"),
        (870, "klem", "heng"), (966, "klem", "heng"),                 # klemmen
    ]
    arm_beats(b, beats)


def animate_girl_arms(g):
    beats = [
        (1, "heng", "heng"),
        (224, "ut", "ut"), (227, "ut", "ut"), (230, "ut", "ut"),     # SPARK
        (236, "heng", "heng"),
    ]
    for i, f in enumerate(range(242, 302, 5)):                       # peker og ler av ham
        beats.append((f, "mage" if i % 2 else "heng", "fram" if i % 2 else (80, 170, 0)))
    beats += [
        (316, "heng", "heng"), (324, "ansikt", "ansikt"),            # ser klatten
        (326, "ut", "ut"), (330, "ut", "ut"), (336, "heng", "heng"), (340, "heng", "heng"),
    ]
    for i, f in enumerate(range(343, 355, 3)):                       # sint stamping
        beats.append((f, "sint" if i % 2 else "heng", "sint" if i % 2 else "heng"))
    beats += [
        (358, "heng", "jubel"),                                      # aha!
        (370, "fram_ned", "fram_ned"), (374, (70, -170, 0), (70, 170, 0)),  # løfter spannet
        (378, (70, -170, 0), (70, 170, 0)), (382, "fram_ned", "fram_ned"),
        (386, "fram_opp", "fram_opp"), (392, (70, -170, 0), (70, 170, 0)),
        (396, "fram_opp", "fram_opp"),                               # hele spannet
        (456, "heng", "heng"),
        (562, "jubel", "jubel"), (566, "ut", "ut"), (576, "ut", "ut"),  # sklir
    ]
    for i, f in enumerate(range(586, 618, 4)):                       # ligger og ler
        beats.append((f, "ut" if i % 2 else "halvut", "ut" if i % 2 else "halvut"))
    beats += [
        (620, "jubel", "jubel"), (626, "heng", "heng"),
        (640, "ut", "ut"), (646, "ut", "ut"), (650, "heng", "heng"), (660, "heng", "heng"),
        (664, (160, -150, 0), (160, 150, 0)), (668, (160, -120, 0), (160, 120, 0)),  # erter
        (735, "ut", "ut"), (738, "dukk", "dukk"), (746, "dukk", "dukk"),  # dukker
        (764, "heng", "heng"), (768, "heng", (95, 170, -40)),        # tørker linsa
        (778, "heng", (95, 170, 40)), (786, "heng", "heng"),
        (792, "heng", "ansikt"), (800, "heng", "heng"),              # puh!
        (852, "heng", "heng"), (870, "heng", "klem"), (966, "heng", "klem"),
    ]
    arm_beats(g, beats)


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
# Flere malingsmerker: fotavtrykk og flekker som hoper seg opp i rommet
# --------------------------------------------------------------------------

def footprints(name, coll, mats, path, f0, f1, every=4, from_frame=None):
    """Fargede fotavtrykk langs en løperute (dukker opp når foten treffer)."""
    pts = [Vector((x, y, 0.0)) for x, y in path]
    segs = list(zip(pts, pts[1:]))
    total = sum((b - a).length for a, b in segs)
    n = 0
    for i, f in enumerate(range(f0, f1 + 1, every)):
        if from_frame and f < from_frame:
            continue
        d = (f - f0) / (f1 - f0) * total
        for a, b in segs:
            length = (b - a).length
            if d <= length or (a, b) == segs[-1]:
                p = a.lerp(b, min(d / length, 1.0))
                dirv = (b - a).normalized()
                break
            d -= length
        side = Vector((-dirv.y, dirv.x, 0)) * (0.13 if i % 2 else -0.13)
        ob = blob_mesh(f"{name}_{n}", coll, pick(mats, n // 2))
        ob.location = p + side
        ob.rotation_euler.z = math.atan2(dirv.y, dirv.x)
        pop(ob, f, full=(0.13, 0.07, 0.008), overshoot=1.0)
        n += 1


def splat_marks(name, coll, mats, center, f, count, radius, seed):
    """En sky av små flekker på gulvet rundt et søl."""
    rnd = random.Random(seed)
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(rnd.random())
        ob = blob_mesh(f"{name}_{i}", coll, pick(mats, i))
        ob.location = (center[0] + r * math.cos(a), center[1] + r * math.sin(a), 0.0)
        sz = rnd.uniform(0.06, 0.17)
        pop(ob, f + rnd.randint(0, 4), full=(sz, sz * rnd.uniform(0.6, 1.0), 0.01), overshoot=1.15)


def build_paint_marks(coll, pm):
    rainbow = list(pm.values())
    coat = [pm["Turkis"], pm["Lilla"]]
    # Flekker rundt hvert søl
    splat_marks("Flekker_Kast1", coll, [pm["Rosa"]], (-2.6, -1.4), 116, 8, 0.7, 41)
    splat_marks("Flekker_Kast2", coll, [pm["Gul"]], (-0.5, -2.0), 134, 10, 1.0, 42)
    splat_marks("Flekker_Balje", coll, rainbow, (0.0, 0.4), 248, 16, 1.4, 43)
    splat_marks("Flekker_Rister", coll, rainbow, (-1.0, 0.4), 294, 18, 1.6, 44)
    splat_marks("Flekker_Treff", coll, [pm["Lilla"]], (1.9, 0.0), 328, 7, 0.6, 45)
    splat_marks("Flekker_Bom", coll, [pm["Rosa"]], (-1.3, 0.3), 398, 8, 0.7, 46)
    splat_marks("Flekker_Taarn", coll, [pm["Rosa"], pm["Himmelblaa"], pm["Lime"]], (-1.1, 5.7), 526, 12, 1.0, 47)
    splat_marks("Flekker_Skli", coll, rainbow, (-0.3, -2.5), 566, 14, 1.1, 48)
    splash("Sprut_Skli_Jente", coll, rainbow, (-0.7, -1.9, 0.1), 562, toward_x=1, count=8, seed=49)
    splash("Sprut_Skli_Gutt", coll, rainbow[2:] + rainbow[:2], (-0.05, -2.0, 0.1), 578, toward_x=1, count=8, seed=50)
    # Fotavtrykk: gutten drypper maling etter dukkingen, hun etter å ha tråkket i søl
    footprints("Spor_Gutt_Flukt", coll, coat, [(-0.8, 0.4), (-3.0, 0.4), (-13.0, 0.2)], 388, 440)
    footprints("Spor_Jente_Jakt", coll, [pm["Rosa"]],
               [(2.95, 0.95), (1.5, 1.6), (-0.3, 1.9), (-3.0, 1.3), (-13.0, 1.5)], 400, 452)
    deep = [(8.5, 0.5), (4.5, 3.0), (1.0, 5.0), (-2.5, 5.0), (-3.8, 2.5), (-2.5, 0.0)]
    footprints("Spor_Jente_Dyp", coll, [pm["Rosa"], pm["Himmelblaa"]], deep + [(-0.8, -1.7)], 460, 560,
               from_frame=514)
    footprints("Spor_Gutt_Dyp", coll, coat, deep + [(-0.2, -1.8)], 476, 576)
    footprints("Spor_Jente_Slutt", coll, rainbow,
               [(-0.5, -2.9), (-2.8, -2.2), (-2.2, 1.6), (-1.2, 2.2), (-0.8, -1.5), (-0.2, -4.3)], 672, 732)
    footprints("Spor_Gutt_Slutt", coll, coat, [(0.6, -2.9), (1.6, -1.0), (0.95, 0.4)], 680, 712)


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
                     size=1.2 if i == 1 else 0.4, grow=12)
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
    splat_on(girl, "Flekk_Jente", coll, pm["Lilla"], 326, (0.12, 0.68))
    splash("Sprut_Jente", coll, pm["Lilla"], (1.6, 0.25, 1.1), 326, toward_x=-1, seed=24)
    floor_puddle("Dam_Jente", coll, pm["Lilla"], (1.5, -0.1), 328, size=0.3)

    # Jenta kaster med spann, bommer
    throw_blob("Klatt_JenteTilGutt", coll, pm["Rosa"], (2.55, 0.95, 1.8), (-1.3, 0.3, 0.05), 386, 396)
    floor_puddle("Dam_Bom", coll, pm["Rosa"], (-1.3, 0.3), 396, size=0.5, grow=10)
    splash("Sprut_Bom", coll, pm["Rosa"], (-1.3, 0.3, 0.05), 396, toward_x=-1, seed=25)
    floor_puddle("Dam_Spann_Jente", coll, pm["Rosa"], (-1.85, -1.75), 412, size=0.45, grow=25)

    # Malingen bygger seg opp og blir værende (kontinuitet gjennom filmen)
    # Begge sklir i den gule dammen: gult på ryggen hennes
    for i, (phi, z, size) in enumerate(((170, 0.7, (0.2, 0.16)), (200, 1.25, (0.14, 0.12)))):
        splat_on(girl, f"Flekk_Jente_Rygg_{i}", coll, pm["Gul"], 566, (0, z), size=size, phi=phi)
    # Klemmen: maling fra drakten hans smitter over på høyre side av henne
    for i, (z, col) in enumerate(((1.0, "Turkis"), (0.62, "Rosa"))):
        splat_on(girl, f"Flekk_Jente_Klem_{i}", coll, pm[col], 872, (0, z), size=(0.13, 0.11), phi=75)
    # Hoppeklemmen: mer smitte på siden hennes
    splat_on(girl, "Flekk_Jente_Hoppeklem", coll, pm["Lime"], PLAY + 13, (0, 0.85), size=(0.14, 0.12), phi=100)
    # Pladask: han lander med ansiktet i en dam og får maling i fjeset
    floor_puddle("Dam_Pladask", coll, pm["Rosa"], (-1.5, -5.0), 742, size=0.55, grow=4)
    for i, (xz, col) in enumerate((((-0.15, 1.42), "Rosa"), ((0.22, 1.12), "Rosa"), ((0.05, 0.55), "Gul"))):
        splat_on(boy, f"Flekk_Gutt_Pladask_{i}", coll, pm[col], PLAY + 76, xz, size=(0.11, 0.09))

    # Avslutning: maling i kamera, tørkes av
    fwd = cam_end.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    lens = cam_end.location + fwd * 0.3
    throw_blob("Klatt_IKamera", coll, pm["Oransje"], (0.9, -0.05, 1.8), tuple(lens), 730, 742, height=0.8)
    lens_paint(cam_end, coll, [pm["Oransje"], pm["Rosa"], pm["Gul"], pm["Himmelblaa"]], 742, 768, 778)

    # Sakte innzoom på ansiktene mot slutten
    for f, lens_mm in ((786, 24.0), (990, 34.0)):
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
        pop(ob, f_hit + (i > 0), full=(sx, sy, 0.004), f_off=f_wipe1 + 1, overshoot=1.0 if i == 0 else 1.2)
        key(ob, f_wipe0, loc=(x, y, z))
        key(ob, f_wipe1, loc=(x + 0.65, y, z))
    for i, x in enumerate((-0.06, 0.03, 0.08)):        # drypp som renner nedover
        ob = blob_mesh(f"Kamera_Drypp_{i}", coll, pick(mat, i + 1))
        ob.parent = cam
        pop(ob, f_hit + 2, full=(0.012, 0.02, 0.004), f_off=f_wipe1 + 1, overshoot=1.0)
        key(ob, f_hit + 2, loc=(x, -0.02, -0.199))
        key(ob, f_wipe0, loc=(x, -0.07 - 0.01 * i, -0.199))
        key(ob, f_wipe1, loc=(x + 0.65, -0.07 - 0.01 * i, -0.199))


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
    head_b = empty("Fokus_Gutt", coll, (0, 0, EYE_Z), boy)
    head_g = empty("Fokus_Jente", coll, (0, 0, EYE_Z), girl)
    mid = empty("Fokus_Midt", coll)
    copy_loc(mid, head_b)
    copy_loc(mid, head_g, 0.5)                         # midt mellom hodene

    # Wide: panorerer mykt etter gutten, og etter begge når søster er med
    aim_w = empty("Sikte_Wide", coll, (0.2, 0, 1.0))
    key_influence(copy_loc(aim_w, head_b), [(1, 0.45), (414, 0.45), (424, 0.0)])
    key_influence(copy_loc(aim_w, head_g), [(1, 0.0), (210, 0.0), (224, 0.33), (414, 0.33), (424, 0.0)])
    # Kameraet blir stående mot venstre mens de løper ut, så piskepanorering til høyre
    for f, loc in ((1, (0.2, 0, 1.0)), (414, (0.2, 0, 1.0)), (424, (-3.2, 0.7, 1.0)),
                   (449, (-3.2, 0.7, 1.0)), (455, (6.5, 1.8, 1.0)), (470, (6.0, 2.0, 1.0)),
                   (484, (4.2, 2.6, 1.0))):
        aim_w.location = loc
        aim_w.keyframe_insert("location", frame=f)
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
    push(cams["deep"], [(484, 500, 0.4), (522, 660, 1.2)])

    # Nærbilder: følger hodet, grunn dybdeskarphet, liten innkjøring
    cu = [
        ("cu_boy_ots", head_b, [(222, 228, 0.15)]),
        ("cu_girl_laugh", head_g, [(240, 272, 0.35)]),
        ("cu_boy_front", head_b, [(288, 306, 0.3), (378, 390, 0.25)]),
        ("cu_girl_hit", head_g, [(323, 356, 0.35)]),
        ("cu_lying", mid, [(594, 618, 0.4)]),
        ("cu_tease", head_g, [(660, 672, 0.2)]),
        ("cu_hug", mid, [(904, 946, 0.4)]),
        ("cu_run", mid, [(500, 522, 0.3)]),  # f/2.8 under, raske bevegelser
        ("cu_splash", head_b, [(238, 252, 0.2)]),
        ("cu_aha", head_g, [(354, 364, 0.15)]),
        ("cu_oops", head_b, [(752, 766, 0.2)]),
        ("cu_jump", mid, [(PLAY - 2, PLAY + 58, 0.3)]),
        ("dance", mid, [(DANCE, DANCE + 100, 0.3)]),
        ("cu_ots_tub", empty("Fokus_Balje", coll, (0.0, 0.4, 0.5)), [(80, 86, 0.1)]),
        ("cu_eyes", head_b, [(86, 92, 0.05)]),
        ("fall", mid, [(PLAY + 58, PLAY + 80, 0.3)]),
        ("cu_floor", head_g, [(PLAY + 80, PARTY, 0.15)]),
        ("party", mid, [(PARTY, PARTY + 18, 0.3), (PARTY + 36, DANCE + 12, 0.4)]),
        ("cu_nod", head_b, [(PARTY + 18, PARTY + 36, 0.15)]),
        ("dance_boy", head_b, [(DANCE + 12, DANCE + 60, 0.4)]),
        ("dance_girl", head_g, [(DANCE + 60, DANCE + 108, 0.4)]),
    ]
    for key_, target, windows in cu:
        aim(cams[key_], target)
        dof(cams[key_], target, 2.8 if key_ == "cu_run" else 2.0)
        push(cams[key_], windows)

    # Følgeskudd bakfra: kameraet henger etter gutten (x/y), fast høyde, sikter på hodet
    tr = cams["track"]
    c = tr.constraints.new("COPY_LOCATION")
    c.target = boy
    c.use_z = False
    c.use_offset = True
    aim(tr, head_b)
    dof(tr, head_b, 2.8)

    # Innklipp av håndavtrykkene: rett ovenfra, sakte ned mot gulvet
    push(cams["cu_prints"], [(156, 172, 0.25)])

    # Sluttkameraet har egne nøkler, bare fokus her
    dof(cams["end"], mid, 4.0)


def windows_influence(c, windows, ramp=3):
    """Influence 1 innenfor hvert (f0, f1)-vindu, 0 ellers, med korte overganger."""
    keys = [(FRAME_START, 0.0)]
    for f0, f1 in windows:
        keys += [(f0 - ramp, 0.0), (f0, 1.0), (f1, 1.0), (f1 + ramp, 0.0)]
    key_influence(c, keys)


def build_acting(boy, girl, coll):
    """Blikkretning og blunking. Pupillene ser rett frem som standard,
    på den andre i relasjonsøyeblikkene og inn i kamera når de smiler til oss."""
    look_cam = empty("Blikk_Kamera", coll, (0, -7.5, 1.5))
    for f, loc in ((1, (0, -7.5, 1.5)), (PLAY, (0, -7.5, 1.5)), (PARTY, (0.6, -9.2, 0.9)),
                   (DANCE, (0.05, -10.1, 1.4))):
        look_cam.location = loc
        look_cam.keyframe_insert("location", frame=f)
    for fc in fcurves_of(look_cam):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
    head = {"Gutt": bpy.data.objects["Fokus_Jente"], "Jente": bpy.data.objects["Fokus_Gutt"]}
    plan = {
        "Gutt": dict(
            other=[(222, 236), (288, 388), (598, 680), (744, 766), (870, 890), (906, 944),
                   (PLAY, PLAY + 66), (DANCE + 136, DANCE + 148)],
            cam=[(212, 222), (892, 904), (950, 990), (PARTY + 4, PARTY + 40),
                 (DANCE + 12, DANCE + 134), (DANCE + 150, FRAME_END)]),
        "Jente": dict(
            other=[(224, 300), (316, 330), (378, 398), (586, 672), (852, 890), (906, 944),
                   (PLAY, PLAY + 66), (PLAY + 76, PARTY - 2), (DANCE + 136, DANCE + 148)],
            cam=[(662, 672), (778, 850), (892, 904), (950, 990), (PARTY + 2, DANCE + 134),
                 (DANCE + 150, FRAME_END)]),
    }
    lead = 3                                           # øynene flytter seg før hodet snur
    tub_look = copy_loc(bpy.data.objects["Blikk_Gutt"], bpy.data.objects["Fokus_Balje"])
    windows_influence(tub_look, [(76 - lead, 100 - lead)])            # han stirrer ned i malingen
    for ob in (boy, girl):
        g = bpy.data.objects[f"Blikk_{ob.name}"]
        for kind in ("other", "cam"):
            target = head[ob.name] if kind == "other" else look_cam
            windows_influence(copy_loc(g, target), [(a - lead, b - lead) for a, b in plan[ob.name][kind]])
    rnd = random.Random(11)
    for ob, offset in ((boy, 0), (girl, 37)):
        frames, f = [], 30 + offset
        while f < FRAME_END - 6:
            frames.append(f)
            f += rnd.randint(55, 95)
        # blunk i blikkskiftene, som når man snur hodet
        turns = [a - lead for kind in ("other", "cam") for a, _ in plan[ob.name][kind]]
        frames = sorted(set(frames + turns))
        kept = []
        for f in frames:
            if not kept or f - kept[-1] > 12:
                kept.append(f)
        blink(ob.name, kept)


# --------------------------------------------------------------------------
# Slutten: lek, pladask, fest med strobelys, dans mot kamera, grep om kameraet
# --------------------------------------------------------------------------

def key_arm(arm, f, ry, rx=0.0):
    """ry: sidelengs (>0 mot +X), rx: fremover mot kamera (>0)."""
    arm.rotation_euler = (math.radians(rx), math.radians(ry), 0)
    arm.keyframe_insert("rotation_euler", frame=f)


def light_level(f, level):
    """Studiolys og verden i prosent av fullt lys (keyes på frame f)."""
    full = {"Lys_Key": 750, "Lys_Fill": 200, "Lys_Rim": 1100}
    for name, e in full.items():
        ld = bpy.data.objects[name].data
        ld.energy = e * level
        ld.keyframe_insert("energy", frame=f)
    w = bpy.context.scene.world
    bg = w.node_tree.nodes.get("Background") if w.node_tree else None
    if bg:
        bg.inputs["Strength"].default_value = 0.35 * level
        bg.inputs["Strength"].keyframe_insert("default_value", frame=f)


def build_ending(boy, girl, coll_char, coll_light, cam):
    B = lambda *a, **k: pose(boy, *a, **k)
    G = lambda *a, **k: pose(girl, *a, **k)
    J = PLAY

    # --- Hoppeklem: hun får en idé og hopper opp på broren
    # Hun henger på siden av ham (ikke oppå), begge vipper bort fra hoppet
    G(J, -0.45, -5.0, 0, -10, 45, 0.8, ry=0)
    B(J + 6, 0.55, -5.0, 0, 0, -30, 1.05)
    G(J + 8, -0.25, -5.0, 0.7, 0, 60, 1.18, ry=8)                 # HOPPER
    G(J + 13, -0.17, -5.0, 0.35, 0, 60, 0.9, ry=10)               # henger på ham
    B(J + 13, 0.72, -5.0, 0, -8, -50, 0.85, ry=10)
    G(J + 18, -0.15, -5.0, 0.3, 0, 55, 1.03, ry=10)
    B(J + 18, 0.75, -5.0, 0, -4, -45, 0.95, ry=10)
    # --- Han rister henne av seg
    for k, f in enumerate(range(J + 24, J + 46, 3)):
        sgn = 1 if k % 2 else -1
        B(f, 0.75, -5.0, 0.05 if k % 2 else 0, 0, -50 + 20 * sgn, 1.0, ry=10 + 8 * sgn)
        G(f, -0.15 + 0.03 * sgn, -5.0, 0.3 + 0.05 * (k % 2), 0, 55 + 20 * sgn, 1.0, ry=10 + 8 * sgn)
    G(J + 50, -0.6, -5.1, 0.6, -20, 40, 1.1, ry=-10)              # flyr av
    G(J + 55, -0.95, -5.2, 0, -25, 30, 0.8)                       # lander, vakler
    G(J + 60, -0.95, -5.2, 0, 0, 20, 1.0)
    B(J + 50, 0.65, -5.0, 0, 0, -40, 1.05)                        # børster seg av
    B(J + 60, 0.62, -5.0, 0, 0, -90, 1.0)                         # snur seg mot henne
    # --- Han hopper på henne, hun dukker unna, han går pladask
    B(J + 64, 0.66, -5.0, 0, -10, -90, 0.8)                       # lader opp
    G(J + 66, -1.0, -5.4, 0.15, 0, 20, 1.05)                      # dukker unna
    B(J + 68, 0.0, -5.0, 0.7, 20, -90, 1.2)                       # HOPPER
    G(J + 70, -1.3, -5.9, 0, -10, 30, 0.9)
    B(J + 73, -0.4, -5.0, 0.5, 60, -90, 1.0, raw=True)
    B(J + 76, -0.35, -5.0, 0.25, 90, -90, 0.9, raw=True)          # PLADASK, nesa i gulvet
    B(J + 80, -0.45, -5.0, 0.25, 90, -90, 1.0, raw=True)
    # --- Hun ler av ham
    for k, f in enumerate(range(J + 80, PARTY, 5)):
        G(f, -1.3, -5.9, 0, -15 if k % 2 == 0 else 0, 120, 1.1 if k % 2 == 0 else 0.92)
    # --- Han ruller over på ryggen (rull rundt lengdeaksen), så ansiktet ses
    B(PARTY - 10, -0.45, -5.0, 0.25, 90, -90, 1.0, raw=True)
    B(PARTY - 5, -0.45, -5.0, 0.3, 90, -90, 1.0, raw=True, ry=100)
    B(PARTY, -0.45, -5.0, 0.25, 90, -90, 1.0, raw=True, ry=180)

    ab, ag = ARMS[boy.name], ARMS[girl.name]
    arm_beats(girl, [
        (J, "heng", "heng"), (J + 4, "fram_ned", "fram_ned"),       # får en idé
        (J + 8, "jubel", "jubel"), (J + 13, "jubel", "klem"), (J + 18, "jubel", "klem"),
    ] + [(f, "jubel" if k % 2 else "ut", "klem") for k, f in enumerate(range(J + 24, J + 46, 3))] + [
        (J + 50, "ut", "ut"), (J + 55, "ut", "ut"), (J + 60, "heng", "heng"),
        (J + 66, "dukk", "dukk"), (J + 70, "heng", "heng"),
    ] + [(f, "mage" if k % 2 else "heng", "fram" if k % 2 == 0 else (75, 170, 0))
         for k, f in enumerate(range(J + 80, PARTY - 4, 5))])        # peker og ler
    arm_beats(boy, [
        (J, "klem", "heng"), (J + 6, "heng", "heng"),
        (J + 13, "ut", "ut"), (J + 18, "halvut", "halvut"),
    ] + [(f, "ut" if k % 2 else "halvut", "halvut" if k % 2 else "ut")
         for k, f in enumerate(range(J + 24, J + 46, 3))] + [
        (J + 50, "heng", "fram"), (J + 60, "heng", "heng"),          # børster seg av
        (J + 64, "bak", "bak"), (J + 68, "fram_opp", "fram_opp"),   # superhelt-hopp
        (J + 73, (0, -10, 0), (0, 10, 0)), (J + 76, (0, -10, 0), (0, 10, 0)),
        (J + 80, (0, -75, 0), (0, 75, 0)), (PARTY - 10, (0, -75, 0), (0, 75, 0)),  # sjøstjerne
    ])

    # --- Fest: hun begynner å danse mot kameraet, han ligger på ryggen og nikker i takt
    rzg = _last_rz[girl.name]
    rzg += (30 - rzg + 180) % 360 - 180                # mot festkameraet
    for k, f in enumerate(range(PARTY, PARTY + 40, 6)):
        if k % 4 == 3:
            rzg += 360                                 # rask piruett, forsiden ses nesten hele tiden
        G(f, -1.3 + (0.1 if k % 2 else -0.1), -5.9, 0.08 if k % 2 else 0, 0, rzg + (12 if k % 2 else -12),
          1.05 if k % 2 else 0.95, ry=10 if k % 2 else -10, spin=True)
        key_arm(ag[-1], f, -20 if k % 2 else -50)
        key_arm(ag[1], f, 20 if k % 2 else 50)
        B(f, -0.45, -5.0, 0.25 + (0.04 if k % 2 else 0), 90 + (10 if k % 2 else 0), -90, 1.0,
          raw=True, ry=180)                            # nikker: hodet løftes fra gulvet
        key_arm(ab[-1], f, -75 if k % 2 else -95)      # tromming i gulvet
        key_arm(ab[1], f, 95 if k % 2 else 75)
    # --- Han slenger seg opp og danser
    UP = PARTY + 42
    B(UP, -0.45, -5.0, 0.2, 90, -90, 0.9, raw=True, ry=180)
    B(UP + 6, -0.6, -5.0, 0.9, 0, -20, 1.2, raw=True)              # SLENGER SEG OPP
    B(UP + 12, -0.7, -5.0, 0, 0, 0, 0.8)
    for arms in (ab,):
        key_arm(arms[-1], UP + 6, -40)
        key_arm(arms[1], UP + 6, 40)
    B(UP + 17, -0.1, -5.05, 0.1, 0, 20, 1.05)
    B(DANCE, 0.5, -5.1, 0, 0, 0, 1.0)
    rzg = round(rzg / 360) * 360
    G(UP + 10, -0.9, -5.6, 0.08, 0, rzg + 20, 1.05, ry=8, spin=True)
    G(DANCE, -0.4, -5.1, 0, 0, rzg, 1.0, spin=True)

    # --- Lyset: dempes til fest, strobelys, lyst igjen når de griper kameraet
    solo_b, solo_g, come, grab = DANCE + 12, DANCE + 60, DANCE + 108, DANCE + 120
    for f, level in ((PARTY - 4, 1.0), (PARTY + 4, 0.22), (grab - 4, 0.22), (grab + 4, 1.15)):
        light_level(f, level)
    colors = [PAINTS["Rosa"], PAINTS["Turkis"], PAINTS["Gul"], PAINTS["Lilla"]]
    spots = [(-4.0, -10.0, 4.0), (4.0, -10.0, 4.0), (-3.0, -3.0, 5.0), (3.0, -3.0, 5.0)]
    for i, (pos, col) in enumerate(zip(spots, colors)):
        ld = bpy.data.lights.new(f"Lys_Strobe_{i}", "SPOT")
        ld.color, ld.spot_size, ld.spot_blend = col, math.radians(70), 0.2
        ob = bpy.data.objects.new(f"Lys_Strobe_{i}", ld)
        coll_light.objects.link(ob)
        ob.location = pos
        look_at(ob, (-0.3, -6.3, 0.9))
        ld.energy = 0
        ld.keyframe_insert("energy", frame=FRAME_START)
        for k, f in enumerate(range(PARTY, grab, 3)):
            ld.energy = 2400 if (k + i) % 4 in (0, 1) else 0
            ld.keyframe_insert("energy", frame=f)
        ld.energy = 0
        ld.keyframe_insert("energy", frame=grab)
        for fc in fcurves_of(ld):                      # av/på, ingen myke overganger
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"

    # --- Solo 1: gutten robotdanser mot kamera, søster vugger i bakgrunnen
    steps = list(range(solo_b, solo_g, 6))
    for k, f in enumerate(steps):
        y = -5.1 - 2.1 * (k + 1) / len(steps)
        B(f, 0.75 if k % 2 else 0.45, y, 0.06 if k % 2 else 0, 0, 30 if k % 4 in (0, 1) else -30,
          0.92 if k % 2 else 1.06)
        key_arm(ab[1], f, 90 if k % 2 else 10)
        key_arm(ab[-1], f, -10 if k % 2 else -90)
        G(f, -0.4 + (0.08 if k % 2 else -0.08), -5.1, 0, 0, rzg, 0.97 if k % 2 else 1.02,
          ry=8 if k % 2 else -8, spin=True)
        key_arm(ag[-1], f, -40 if k % 2 else -25)
        key_arm(ag[1], f, 40 if k % 2 else 25)

    # --- Solo 2: søster snurrer frem mot kamera, gutten vugger der han står
    steps = list(range(solo_g, come, 6))
    for k, f in enumerate(steps):
        y = -5.1 - 2.1 * (k + 1) / len(steps)
        if k % 4 == 3:
            rzg += 360                                 # rask piruett, ellers forsiden mot kamera
        G(f, -0.65 if k % 2 else -0.35, y, 0.1 if k % 2 else 0, 0, rzg, 1.05 if k % 2 else 0.95,
          ry=10 if k % 2 else -10, spin=True)
        key_arm(ag[-1], f, -20 if k % 2 else -50)
        key_arm(ag[1], f, 20 if k % 2 else 50)
        B(f, 0.55 + (0.06 if k % 2 else -0.06), -7.2, 0, 0, -10 if k % 2 else 10,
          0.97 if k % 2 else 1.03, ry=-6 if k % 2 else 6)
        key_arm(ab[1], f, 40 if k % 2 else 25)
        key_arm(ab[-1], f, -40 if k % 2 else -25)

    # --- Sammen helt frem til kamera, og de griper det med hver sin hånd
    rzg = round(rzg / 360) * 360
    G(come, -0.4, -7.4, 0, 0, rzg, 1.0, spin=True)
    B(come, 0.45, -7.4, 0, 0, 0, 1.0)
    G(come + 10, -0.38, -8.3, 0.12, 10, rzg, 1.05, spin=True)
    B(come + 10, 0.42, -8.3, 0.12, 10, 0, 1.05)
    G(grab - 2, -0.38, -8.6, 0, 15, rzg, 0.9, spin=True)
    B(grab - 2, 0.42, -8.6, 0, 15, 0, 0.9)
    for arms, outer in ((ag, -1), (ab, 1)):
        key_arm(arms[outer], come, outer * 20)
        key_arm(arms[-outer], come, -outer * 20)
        key_arm(arms[outer], grab - 2, outer * 30, rx=60)
        key_arm(arms[outer], grab, outer * 25, rx=82)       # ytterhånd griper kameraet
        key_arm(arms[-outer], grab, -outer * 100)          # innerarmen rundt den andre
    for k, f in enumerate(range(grab, DANCE + 136, 8)):    # holder kameraet, smiler
        sq = 1.02 if k % 2 else 0.98
        G(f, -0.38, -8.6, 0, 5, rzg + (3 if k % 2 else -3), sq, ry=4, spin=True)
        B(f, 0.42, -8.6, 0, 5, 3 if k % 2 else -3, sq, ry=-4)

    # --- Knappen: han slipper kameraet og etterlater et fjæravtrykk på linsa
    #     (payoff på malingen på linsa tidligere). De ser det, ser på hverandre og ler.
    rel = DANCE + 136
    key_arm(ab[1], rel - 4, 25, rx=82)
    key_arm(ab[1], rel + 4, 40)
    print_mat = bpy.data.materials.get("M_Maling_Turkis")
    for k, tilt in enumerate((-25, 0, 25)):
        fp = blob_mesh(f"Kamera_Fjaeravtrykk_{k}", coll_char, print_mat)
        fp.parent = cam
        fp.location = (0.135 + 0.014 * (k - 1), 0.06 + 0.008 * abs(k - 1), -0.2)
        fp.rotation_euler = (0, 0, math.radians(tilt - 20))
        pop(fp, rel + 1, full=(0.008, 0.02, 0.002), overshoot=1.15)
    G(rel + 6, -0.38, -8.6, 0, 0, rzg + 25, 1.0, ry=2, spin=True)    # ser på hverandre
    B(rel + 6, 0.42, -8.6, 0, 0, -25, 1.0, ry=-2)
    G(rel + 12, -0.38, -8.6, 0, 0, rzg + 28, 1.04, ry=2, spin=True)
    B(rel + 12, 0.42, -8.6, 0, 0, -28, 1.04, ry=-2)
    for k, f in enumerate(range(rel + 14, FRAME_END + 1, 4)):   # bryter ut i latter
        sq = 1.07 if k % 2 == 0 else 0.93
        G(f, -0.38, -8.6, 0.04 if k % 2 == 0 else 0, -10 if k % 2 == 0 else 3, rzg + 5, sq, ry=3, spin=True)
        B(f, 0.42, -8.6, 0.04 if k % 2 == 0 else 0, -10 if k % 2 == 0 else 3, -5, sq, ry=-3)

    # --- Kameraet blir grepet: vidvinkel, et lite rykk, litt håndholdt skjelving
    for f, mm in ((come, 28.0), (grab, 18.0)):
        cam.data.lens = mm
        cam.data.keyframe_insert("lens", frame=f)
    rnd = random.Random(7)
    bpy.context.scene.frame_set(grab - 1)              # der innkjøringen slapp
    home = cam.location.copy()
    cam.keyframe_insert("location", frame=grab - 1)
    for k, f in enumerate(range(grab, FRAME_END + 1, 2)):
        amp = 0.05 if k < 2 else 0.008
        cam.location = home + Vector((rnd.uniform(-amp, amp), rnd.uniform(-amp, amp) * 0.5,
                                      rnd.uniform(-amp, amp)))
        cam.keyframe_insert("location", frame=f)
    cam.location = home


def anticipation_and_settle(ob):
    """Forventning før hvert hopp (sammenkrøket, lener seg tilbake) og settle etter
    landing (squash, liten overshoot, ro). Legges bare inn der det er plass."""
    log = sorted(POSE_LOG.get(ob.name, []), key=lambda k: k[0])
    frames = [k[0] for k in log]
    free = lambda a, b: not any(a <= f <= b for f in frames)
    for k0, k1 in zip(log, log[1:]):
        f0, x0, y0, z0, rx0, ry0, rz0, sq0, raw0 = k0
        f1, z1, raw1 = k1[0], k1[3], k1[8]
        if raw0 or raw1:
            continue
        if z0 < 0.05 and z1 >= 0.3 and f1 - f0 <= 8 and free(f0 - 5, f0 - 1):   # sats
            xy = 1 / math.sqrt(0.8)
            key(ob, f0 - 3, loc=(x0, y0, 0.0), rot=(rx0 - 6, ry0, rz0), scale=(xy, xy, 0.8))
        if z0 >= 0.3 and z1 < 0.05 and f1 - f0 <= 10 and free(f1 + 1, f1 + 8):   # landing
            for df, sq in ((2, 0.86), (5, 1.06), (8, 1.0)):
                xy = 1 / math.sqrt(sq)
                key(ob, f1 + df, scale=(xy, xy, sq))


def break_twinning(ob, windows, delay=3):
    """Unngå at de gjør akkurat det samme samtidig: hennes bevegelser i disse vinduene
    kommer litt etter hans."""
    objs = [ob] + list(ARMS[ob.name].values()) + list(BOOTS[ob.name].values())
    for o in objs:
        for fc in fcurves_of(o):
            for kp in sorted(fc.keyframe_points, key=lambda k: -k.co.x):
                if any(a < kp.co.x < b - delay - 1 for a, b in windows):
                    kp.co.x += delay
                    kp.handle_left.x += delay
                    kp.handle_right.x += delay
            fc.update()


def hair_follow_through(ob, stiffness=0.25, damping=0.72, gain=120.0):
    """Etterslep i hår, musefletter og sløyfe: en fjær som reagerer på kroppens
    akselerasjon (overlapping action). Simuleres bilde for bilde."""
    curves = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(ob)}

    def world(f):
        loc = Vector([curves[("location", i)].evaluate(f) if ("location", i) in curves else 0 for i in range(3)])
        rot = [curves[("rotation_euler", i)].evaluate(f) if ("rotation_euler", i) in curves else 0
               for i in range(3)]
        return loc, Euler(rot).to_matrix()

    for pv in HAIR.get(ob.name, []):
        off = Vector(pv.location)
        pts, mats = [], []
        for f in range(FRAME_START - 1, FRAME_END + 2):
            loc, m = world(f)
            pts.append(loc + m @ off)
            mats.append(m)
        ang = Vector((0.0, 0.0))
        vel = Vector((0.0, 0.0))
        keys = []
        for i in range(1, len(pts) - 1):
            acc = mats[i].transposed() @ (pts[i + 1] - 2 * pts[i] + pts[i - 1])   # i figurens rom
            target = Vector((acc.y * gain, -acc.x * gain))                       # lener seg bakover
            vel = vel * damping + (target - ang) * stiffness
            ang += vel
            ang.x = max(-35.0, min(35.0, ang.x))
            ang.y = max(-35.0, min(35.0, ang.y))
            keys.append((FRAME_START - 1 + i, ang.x, ang.y))
        base = Euler(pv.rotation_euler)
        for f, ax, ay in keys[::2]:
            pv.rotation_euler = (base.x + math.radians(ax), base.y + math.radians(ay), base.z)
            pv.keyframe_insert("rotation_euler", frame=f)
        pv.rotation_euler = base


def wing_drag(*chars, lag=2):
    """Etterslep (follow-through): vingene henger litt etter kroppen."""
    for ob in chars:
        for arm in ARMS[ob.name].values():
            for fc in fcurves_of(arm):
                for kp in fc.keyframe_points:
                    kp.co.x += lag
                    kp.handle_left.x += lag
                    kp.handle_right.x += lag
                fc.update()


def color_script(coll):
    """Fargemanus: lysstemningen følger historien (key, fill, rim, verden)."""
    morning = ((1.0, 0.80, 0.60), (0.72, 0.84, 1.0), (1.0, 0.82, 0.62), (0.96, 0.90, 0.82))
    clash = ((0.90, 0.94, 1.0), (0.60, 0.74, 1.0), (1.0, 0.88, 0.75), (0.85, 0.88, 0.93))
    chase = ((1.0, 0.92, 0.82), (0.75, 0.85, 1.0), (1.0, 0.90, 0.78), (0.92, 0.90, 0.87))
    golden = ((1.0, 0.72, 0.46), (0.95, 0.82, 0.72), (1.0, 0.76, 0.48), (0.98, 0.86, 0.72))
    play = ((1.0, 0.84, 0.66), (0.80, 0.86, 1.0), (1.0, 0.84, 0.66), (0.96, 0.91, 0.84))
    party = ((0.70, 0.55, 1.0), (0.55, 0.45, 1.0), (1.0, 0.45, 0.85), (0.30, 0.24, 0.45))
    finale = ((1.0, 0.86, 0.68), (0.85, 0.88, 1.0), (1.0, 0.86, 0.66), (1.0, 0.94, 0.86))
    grab = DANCE + 120
    script = [(1, morning), (200, morning), (216, clash), (456, clash), (476, chase), (744, chase),
              (772, golden), (PLAY, golden), (PLAY + 24, play), (PARTY - 4, play),
              (PARTY + 4, party), (grab - 4, party), (grab + 4, finale)]
    names = ("Lys_Key", "Lys_Fill", "Lys_Rim")
    w = bpy.context.scene.world
    bg = w.node_tree.nodes.get("Background") if w.node_tree else None
    for f, look in script:
        for name, col in zip(names, look):
            ld = bpy.data.objects[name].data
            ld.color = col
            ld.keyframe_insert("color", frame=f)
        if bg:
            bg.inputs["Color"].default_value = (*look[3], 1.0)
            bg.inputs["Color"].keyframe_insert("default_value", frame=f)

    # Dis i festen, så strobelysene får synlige lysstråler
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    haze = mesh_object("Fest_Dis", bm, coll, [])
    haze.location, haze.scale = (0, -6.0, 3.0), (16, 10, 6)
    mat = bpy.data.materials.new("M_Dis")
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nodes = mat.node_tree.nodes
    for n in list(nodes):
        if n.type != "OUTPUT_MATERIAL":
            nodes.remove(n)
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.035
    out = [n for n in nodes if n.type == "OUTPUT_MATERIAL"][0]
    mat.node_tree.links.new(vol.outputs[0], out.inputs["Volume"])
    haze.data.materials.append(mat)
    for f, hidden in ((FRAME_START, True), (PARTY, False), (grab + 4, True)):
        haze.hide_render = hidden
        haze.keyframe_insert("hide_render", frame=f)
        haze.hide_viewport = hidden
        haze.keyframe_insert("hide_viewport", frame=f)


# --------------------------------------------------------------------------
# Barnemalerier: Mona Lisa og Van Goghs Stjernenatt, tegnet av skriptet
# --------------------------------------------------------------------------

class KidCanvas:
    """Enkel «fargestift»-tegneflate i numpy (0..1 RGB, y=0 øverst)."""

    def __init__(self, w, h, bg, seed):
        import numpy as np
        self.np, self.w, self.h = np, w, h
        self.img = np.ones((h, w, 3)) * np.array(bg)
        self.yy, self.xx = np.mgrid[0:h, 0:w] / float(h)   # koordinater i høyde-enheter
        self.rnd = np.random.default_rng(seed)

    def _paint(self, mask, col, wobble=0.08):
        np = self.np
        grain = 1.0 + wobble * (self.rnd.random(mask.shape) - 0.5)     # ujevn farge som fargestift
        self.img[mask] = (np.array(col) * grain[mask][:, None]).clip(0, 1)

    def ellipse(self, cx, cy, rx, ry, col, wobble=0.08):
        m = ((self.xx - cx) / rx) ** 2 + ((self.yy - cy) / ry) ** 2 <= 1.0
        self._paint(m, col, wobble)

    def poly(self, pts, col):
        np = self.np
        m = np.ones_like(self.xx, dtype=bool)
        n = len(pts)
        sign = None
        for i in range(n):                             # konveks polygon via halvplan
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            c = (x1 - x0) * (self.yy - y0) - (y1 - y0) * (self.xx - x0)
            if sign is None:
                cx = sum(p[0] for p in pts) / n
                cy = sum(p[1] for p in pts) / n
                sign = 1 if (x1 - x0) * (cy - y0) - (y1 - y0) * (cx - x0) > 0 else -1
            m &= c * sign >= 0
        self._paint(m, col)

    def stroke(self, pts, width, col):
        """Tykk strek gjennom punktene (rundt pensel)."""
        np = self.np
        pts = np.array(pts)
        for a, b in zip(pts, pts[1:]):
            steps = max(2, int(np.linalg.norm(b - a) / (width * 0.4)))
            for t in np.linspace(0, 1, steps):
                p = a + (b - a) * t
                self.ellipse(p[0], p[1], width, width, col, wobble=0.15)

    def to_image(self, name):
        np = self.np
        rgba = np.concatenate([self.img[::-1], np.ones((self.h, self.w, 1))], axis=2)  # Blender: nederst først
        img = bpy.data.images.new(name, self.w, self.h)
        img.pixels.foreach_set(rgba.astype("float32").ravel())
        img.pack()
        return img


def paint_mona_lisa():
    import numpy as np
    W, H = 400, 520
    c = KidCanvas(W, H, (0.42, 0.50, 0.30), seed=1)
    a = W / H                                          # bredde i høyde-enheter
    for k in range(10):                                # himmel og landskap i striper
        y = k * 0.06
        c.poly([(0, y), (a, y), (a, y + 0.07), (0, y + 0.07)],
               (0.55 + 0.03 * k, 0.62 - 0.01 * k, 0.40 - 0.02 * k))
    c.stroke([(0.05, 0.42), (0.18, 0.36), (0.12, 0.30), (0.22, 0.24)], 0.012, (0.70, 0.60, 0.35))  # sti
    c.stroke([(0.62, 0.30), (0.70, 0.26), (0.66, 0.20)], 0.012, (0.35, 0.50, 0.60))           # elv
    c.poly([(0.08, 1.0), (0.17, 0.62), (a - 0.17, 0.62), (a - 0.08, 1.0)], (0.12, 0.09, 0.06))  # kjole
    c.ellipse(a / 2, 0.36, 0.20, 0.26, (0.16, 0.10, 0.06))                   # hår
    c.ellipse(a / 2, 0.36, 0.13, 0.18, (0.86, 0.68, 0.45))                   # ansikt
    c.poly([(a / 2 - 0.07, 0.55), (a / 2 + 0.07, 0.55), (a / 2 + 0.05, 0.64), (a / 2 - 0.05, 0.64)],
           (0.86, 0.68, 0.45))                                               # hals
    for dx in (-0.05, 0.05):                                                # øyne
        c.ellipse(a / 2 + dx, 0.33, 0.022, 0.012, (0.15, 0.10, 0.06))
    t = np.linspace(-0.05, 0.05, 12)                                        # det mystiske smilet
    c.stroke([(a / 2 + x, 0.45 - 6 * x * x + 0.004) for x in t], 0.006, (0.55, 0.25, 0.20))
    c.ellipse(a / 2 - 0.02, 0.88, 0.09, 0.05, (0.86, 0.68, 0.45))           # hender
    c.ellipse(a / 2 + 0.06, 0.86, 0.09, 0.05, (0.86, 0.68, 0.45))
    c.stroke([(0.02, 0.02), (a - 0.02, 0.02), (a - 0.02, 0.98), (0.02, 0.98), (0.02, 0.02)],
             0.012, (0.85, 0.20, 0.25))                                      # barnets rosa ramme
    return c.to_image("Maleri_Mona_Lisa")


def paint_starry_night():
    import numpy as np
    W, H = 520, 400
    c = KidCanvas(W, H, (0.05, 0.12, 0.40), seed=2)
    a = W / H
    for k in range(9):                                 # virvlende himmel
        cx, cy = 0.2 + 0.15 * k, 0.25 + 0.05 * math.sin(k)
        r0 = 0.05 + 0.02 * (k % 3)
        pts = [(cx + r0 * (1 + 0.6 * t) * math.cos(6 * t), cy + 0.5 * r0 * (1 + 0.6 * t) * math.sin(6 * t))
               for t in np.linspace(0, 1.4, 20)]
        c.stroke(pts, 0.008, (0.35, 0.55, 0.95) if k % 2 else (0.75, 0.85, 1.0))
    for x, y, r in ((0.15, 0.12, 0.04), (0.42, 0.08, 0.035), (0.62, 0.18, 0.03), (0.85, 0.10, 0.035),
                    (1.05, 0.22, 0.03), (0.30, 0.30, 0.03), (0.75, 0.36, 0.028)):
        c.ellipse(x, y, r * 1.8, r * 1.8, (0.95, 0.85, 0.35))                # glorie
        c.ellipse(x, y, r, r, (1.0, 0.95, 0.55))                             # stjerne
    c.ellipse(1.2, 0.12, 0.08, 0.08, (1.0, 0.75, 0.15))                      # måne
    c.ellipse(1.235, 0.10, 0.065, 0.065, (0.05, 0.12, 0.40))
    c.poly([(0, 0.72), (a, 0.62), (a, 1.0), (0, 1.0)], (0.10, 0.20, 0.35))   # åser
    for i, x in enumerate((0.55, 0.68, 0.80, 0.92, 1.04)):                   # landsby
        c.poly([(x, 0.80), (x + 0.09, 0.80), (x + 0.09, 0.90), (x, 0.90)], (0.30, 0.30, 0.45))
        c.poly([(x - 0.01, 0.80), (x + 0.1, 0.80), (x + 0.045, 0.74)], (0.15, 0.15, 0.30))
        c.ellipse(x + 0.045, 0.85, 0.012, 0.012, (1.0, 0.85, 0.3))
    c.poly([(0.08, 1.0), (0.27, 1.0), (0.19, 0.22), (0.16, 0.22)], (0.05, 0.08, 0.04))  # sypress
    c.stroke([(0.17, 0.95), (0.12, 0.72), (0.2, 0.52), (0.15, 0.32), (0.175, 0.24)], 0.04, (0.08, 0.14, 0.06))
    c.stroke([(0.2, 0.9), (0.23, 0.7), (0.17, 0.55)], 0.02, (0.12, 0.22, 0.08))
    c.stroke([(0.02, 0.02), (a - 0.02, 0.02), (a - 0.02, 0.98), (0.02, 0.98), (0.02, 0.02)],
             0.012, (0.95, 0.55, 0.05))                                      # barnets oransje ramme
    return c.to_image("Maleri_Stjernenatt")


def painting_plane(name, coll, image, parent, size):
    """Bildeflate med maleriet, litt foran lerretet (forsiden er -Y)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5, calc_uvs=True)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    m = material(f"M_{name}", (1, 1, 1), rough=0.85)
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    m.node_tree.links.new(tex.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    ob = mesh_object(name, bm, coll, [m])
    ob.parent = parent
    ob.location = (0, -0.7, 0)                          # i lerretets lokale (skalerte) rom
    ob.scale = size
    return ob


def build_set_dressing(coll, pm, metal):
    """Barnas malerverksted: staffelier med malerier, stige, bord med glass og pensler,
    presenning og malingstuber. Alt står utenfor løpeveiene."""
    wood = bpy.data.materials.get("M_Tre")
    canvas = material("M_Lerret", (0.92, 0.90, 0.85), rough=0.8)
    cloth = material("M_Presenning", (0.75, 0.68, 0.55), rough=0.9)
    paints = list(pm.values())

    def box(name, size, loc, rot=(0, 0, 0), mat=wood):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        ob = mesh_object(name, bm, coll, [mat])
        ob.scale, ob.location = size, loc
        ob.rotation_euler = [math.radians(a) for a in rot]
        return ob

    def easel(name, xy, rz, image, landscape):
        root = bpy.data.objects.new(name, None)
        coll.objects.link(root)
        root.location, root.rotation_euler = (*xy, 0), (0, 0, math.radians(rz))
        for i, (x, y, tilt) in enumerate(((-0.35, 0, (-8, -6)), (0.35, 0, (-8, 6)), (0, 0.45, (14, 0)))):
            leg = box(f"{name}_Bein_{i}", (0.05, 0.05, 1.9), (x, y, 0.93), (tilt[0], tilt[1], 0))
            leg.parent = root
        dims = (0.95, 0.04, 0.75) if landscape else (0.72, 0.04, 0.93)
        board = box(f"{name}_Lerret", dims, (0, -0.14, 1.35), (-8, 0, 0), canvas)
        board.parent = root
        painting_plane(f"{name}_Maleri", coll, image, board, (0.94, 1, 0.94))
        return root

    # Søster har malt Mona Lisa, broren Van Goghs Stjernenatt
    easel("Staffeli_Mona_Lisa", (-5.0, 3.8), 20, paint_mona_lisa(), landscape=False)
    easel("Staffeli_Stjernenatt", (6.0, 3.6), -25, paint_starry_night(), landscape=True)

    # Presenning med malingsflekker under staffeliet til venstre
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    tarp = mesh_object("Presenning", bm, coll, [cloth])
    tarp.location, tarp.scale = (-5.0, 3.4, 0.004), (1.4, 1.1, 1)
    tarp.rotation_euler.z = math.radians(12)
    rnd = random.Random(9)
    for k in range(7):
        d = blob_mesh(f"Presenning_Flekk_{k}", coll, pick(paints, k))
        d.location = (-5.0 + rnd.uniform(-1.1, 1.1), 3.4 + rnd.uniform(-0.8, 0.8), 0.008)
        d.scale = (rnd.uniform(0.08, 0.2), rnd.uniform(0.08, 0.2), 0.005)

    # Stige som lener seg mot bakveggen (der cycloramaen går loddrett opp, y = 7)
    lad = bpy.data.objects.new("Stige", None)
    coll.objects.link(lad)
    foot_y, length = 5.8, 3.0
    lean = math.asin((7.0 - 0.05 - foot_y) / length)   # toppen hviler mot veggen
    lad.location = (-5.6, foot_y, 3.0 - math.sqrt(9.0 - (foot_y - 4.0) ** 2))
    lad.rotation_euler = (-lean, 0, 0)
    for x in (-0.25, 0.25):
        box(f"Stige_Vange_{'V' if x < 0 else 'H'}", (0.06, 0.06, length), (x, 0, length / 2)).parent = lad
    for k in range(9):
        box(f"Stige_Trinn_{k}", (0.5, 0.05, 0.04), (0, 0, 0.3 + k * 0.3)).parent = lad

    # Bord med vannglass og pensler til høyre
    top = box("Bord_Plate", (1.2, 0.7, 0.05), (6.4, -1.2, 0.72))
    for x in (-0.55, 0.55):
        for y in (-0.3, 0.3):
            box(f"Bord_Bein_{x}_{y}", (0.05, 0.05, 0.7), (6.4 + x, -1.2 + y, 0.35))
    for k, (x, y) in enumerate(((-0.35, -0.1), (0.0, 0.12), (0.32, -0.08))):
        jar = build_bucket(f"Bord_Glass_{k}", coll, pick(paints, k + 2), metal, r1=0.06, r2=0.07, depth=0.16)
        jar.location = (6.4 + x, -1.2 + y, 0.745)
        for j in range(2):
            brush = box(f"Bord_Pensel_{k}_{j}", (0.015, 0.015, 0.3), (6.4 + x + 0.02 * j, -1.2 + y, 0.9),
                        (0, 12 - 24 * j, 0))
    # Malingstuber på trekassa
    for k, (x, y, rz) in enumerate(((3.95, 1.4, 20), (4.25, 1.7, -35), (4.5, 1.45, 70))):
        tube = blob_mesh(f"Tube_{k}", coll, pick(paints, k + 4))
        tube.location, tube.scale = (x, y, 0.95), (0.05, 0.13, 0.04)
        tube.rotation_euler.z = math.radians(rz)


def floor_z(y):
    """Gulvhøyden i cycloramaen (flatt til y=4, så bøyer det seg opp mot bakveggen)."""
    return 0.0 if y <= 4.0 else 3.0 - math.sqrt(max(0.0, 9.0 - (y - 4.0) ** 2))


# Løpeveier (fra animasjonen) og kamerabaner som plantene må holde seg unna
PLANT_PATHS = [
    [(-8.5, -0.4), (-1.2, -0.4)], [(-0.8, 0.4), (-3.0, 0.4), (-13.0, 0.2)],
    [(8.5, 0.5), (4.5, 3.0), (1.0, 5.0), (-2.5, 5.0), (-3.8, 2.5), (-2.5, 0.0), (-0.2, -1.8)],
    [(0.6, -2.9), (1.6, -1.0), (0.95, 0.4)], [(7.5, -4.6), (0.55, -5.0)],
    [(8.5, 0.6), (2.1, 0.35)], [(2.95, 0.95), (1.5, 1.6), (-0.3, 1.9), (-3.0, 1.3), (-13.0, 1.5)],
    [(-0.5, -2.9), (-2.8, -2.2), (-2.2, 1.6), (-1.2, 2.2), (-0.8, -1.5), (-0.2, -4.3)],
    [(-10.9, -1.0), (-3.6, -1.0)],                     # følgekameraet bak gutten
]
# (x, y, radius): kameraer, møbler, rekvisitter og selve scenen der handlingen skjer
PLANT_KEEP_OUT = [
    (-5.0, 4.6, 1.3), (0.9, -4.0, 1.2), (-0.2, -5.35, 1.0), (2.6, -7.6, 1.3), (3.3, -0.6, 1.0),
    (-1.93, -0.95, 1.0), (3.9, 1.7, 1.0), (-1.45, -0.95, 1.0),
    (-5.0, 3.8, 1.1), (6.0, 3.6, 1.1), (-5.0, 3.4, 1.3), (-5.6, 5.8, 0.9), (6.4, -1.2, 1.0),
    (5.3, 5.0, 1.1), (-7.2, 3.4, 0.8), (7.7, 3.2, 1.0), (4.2, 1.6, 0.9),
    (3.3, 1.2, 0.6), (-4.5, -0.75, 0.6), (5.0, 0.25, 0.6), (-3.6, 0.5, 0.7), (1.1, -1.95, 0.6),
]


def _seg_dist(p, a, b):
    ab, ap = b - a, p - a
    t = max(0.0, min(1.0, ap.dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def plant_spots(rnd, step=1.0, min_gap=1.05):
    """Plasser på flatt gulv i et rutenett med litt tilfeldighet, utenfor alt som må holdes fritt."""
    spots = []
    y = -7.2
    while y <= 4.2:
        x = -9.4
        while x <= 9.4:
            p = Vector((x + rnd.uniform(-0.3, 0.3), min(4.2, y + rnd.uniform(-0.3, 0.3))))
            ok = not (abs(p.x) < 4.3 and p.y < 4.3)         # midten er scenen for handlingen
            ok = ok and all(_seg_dist(p, Vector(a), Vector(b)) > 1.1
                            for path in PLANT_PATHS for a, b in zip(path, path[1:]))
            ok = ok and all((p - Vector((kx, ky))).length > kr for kx, ky, kr in PLANT_KEEP_OUT)
            ok = ok and all((p - q).length > min_gap for q in spots)
            if ok and rnd.random() < 0.8:                 # litt luft innimellom
                spots.append(p)
            x += step
        y += step
    return [(p.x, p.y) for p in spots]


def build_furniture(coll):
    """Planter og møbler i en ren, enkel stil (som i Pixars lampeintro): avrundede
    grunnformer, matte materialer, få varme farger og god luft rundt hver ting."""
    wood = material("M_Lys_Tre", (0.55, 0.36, 0.20), rough=0.6)
    cream = material("M_Krem", (0.86, 0.82, 0.76), rough=0.7)
    clay = material("M_Terrakotta", (0.62, 0.24, 0.11), rough=0.75)
    leaf = [material("M_Blad_Mork", (0.10, 0.32, 0.08), rough=0.55),
            material("M_Blad_Lys", (0.22, 0.50, 0.12), rough=0.55)]
    teal = material("M_Dempet_Turkis", (0.10, 0.35, 0.38), rough=0.65)
    mustard = material("M_Sennep", (0.80, 0.52, 0.10), rough=0.7)

    def ell(name, center, radii, mat, rot=(0, 0, 0), parent=None):
        bm = bmesh.new()
        ellipsoid_bm(bm, (0.0, *radii), segs=(24, 14))
        ob = mesh_object(name, bm, coll, [mat])
        smooth(ob)
        ob.parent = parent
        ob.location = center
        ob.rotation_euler = [math.radians(a) for a in rot]
        return ob

    def cyl(name, center, r1, r2, h, mat, parent=None, segs=32):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r1, radius2=r2, depth=h)
        bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
        ob = mesh_object(name, bm, coll, [mat])
        smooth(ob)
        ob.parent = parent
        ob.location = center
        bev = ob.modifiers.new("Bevel", "BEVEL")
        bev.width, bev.segments, bev.limit_method = 0.012, 2, "ANGLE"
        return ob

    def box(name, center, size, mat, parent=None, rz=0):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        ob = mesh_object(name, bm, coll, [mat])
        ob.parent = parent
        ob.scale, ob.location = size, center
        ob.rotation_euler.z = math.radians(rz)
        bev = ob.modifiers.new("Bevel", "BEVEL")
        bev.width, bev.segments = 0.02, 3
        return ob

    def root(name, xy, rz=0.0):
        ob = bpy.data.objects.new(name, None)
        coll.objects.link(ob)
        ob.location = (xy[0], xy[1], floor_z(xy[1]))
        ob.rotation_euler.z = math.radians(rz)
        return ob

    soil = material("M_Jord", (0.12, 0.07, 0.04), rough=0.9)
    petal = material("M_Solsikke_Kronblad", (1.0, 0.72, 0.04), rough=0.5)
    seeds = material("M_Solsikke_Midt", (0.22, 0.11, 0.03), rough=0.8)
    stem_mat = material("M_Stilk", (0.20, 0.42, 0.10), rough=0.6)
    cactus = material("M_Kaktus", (0.25, 0.45, 0.22), rough=0.6)
    bloom = material("M_Kaktusblomst", (0.95, 0.35, 0.55), rough=0.5)

    def stalk(name, base, direction, length, radius, mat, parent):
        """Tynn stilk fra base i retning direction."""
        ob = cyl(name, (0, 0, 0), radius, radius * 0.7, length, mat, parent, segs=10)
        ob.location = base
        ob.rotation_euler = Vector(direction).to_track_quat("Z", "Y").to_euler()
        return Vector(base) + Vector(direction).normalized() * length

    def sunflower(name, r, base, height, rnd, facing):
        top = stalk(f"{name}_Stilk", base, (rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.04), 1), height,
                    0.035, stem_mat, r)
        for k in range(4):                              # hjerteformede blader oppover stilken
            z = base[2] + height * (0.25 + 0.17 * k)
            side = 1 if k % 2 else -1
            lf = ell(f"{name}_Blad_{k}", (side * 0.16, 0, z), (0.16, 0.02, 0.11), pick(leaf, k), parent=r)
            lf.rotation_euler = (0, math.radians(side * 30), 0)
        head = bpy.data.objects.new(f"{name}_Hode", None)
        coll.objects.link(head)
        head.parent, head.location = r, top
        head.rotation_euler = (math.radians(95), 0, math.radians(facing))   # ser fremover og litt ned
        rad = rnd.uniform(0.2, 0.28)
        ell(f"{name}_Midt", (0, 0, 0), (rad, rad, 0.06), seeds, parent=head)
        for k in range(18):
            a = math.radians(k * 20)
            p = ell(f"{name}_Kronblad_{k}", (math.cos(a) * rad * 1.45, math.sin(a) * rad * 1.45, -0.01),
                    (rad * 0.55, rad * 0.16, 0.02), petal, parent=head)
            p.rotation_euler = (0, 0, a)

    def plant(name, xy, kind, size=1.0, seed=0):
        r = root(name, xy, rz=seed * 37)
        rnd = random.Random(seed)
        pot_r = 0.23 * min(size, 1.6)
        pot_h = 0.42 * min(size, 1.6)
        cyl(f"{name}_Potte", (0, 0, 0), pot_r * 0.75, pot_r, pot_h, clay, r)
        cyl(f"{name}_Jord", (0, 0, pot_h - 0.03), pot_r * 0.92, pot_r * 0.92, 0.02, soil, r)
        top = pot_h
        if kind == "hoy":                              # høye, slanke blader i vifte
            for k in range(11):
                a = k * 33 + rnd.uniform(-10, 10)
                tilt = rnd.uniform(6, 26)
                h = rnd.uniform(0.5, 0.9) * size
                lf = ell(f"{name}_Blad_{k}", (0, 0, 0), (0.07 * size, 0.02 * size, h), pick(leaf, k), parent=r)
                lf.rotation_euler = (math.radians(tilt), 0, math.radians(a))
                lf.location = Vector((0, 0, top)) + lf.rotation_euler.to_matrix() @ Vector((0, 0, h * 0.9))
        elif kind == "busk":                           # rund, myk busk av kuler
            for k in range(6):
                a = math.radians(k * 67)
                rr = rnd.uniform(0.18, 0.32) * size
                ell(f"{name}_Busk_{k}", (math.cos(a) * 0.15 * size, math.sin(a) * 0.15 * size,
                                         top + rnd.uniform(0.2, 0.55) * size), (rr,) * 3, pick(leaf, k), parent=r)
        elif kind == "fiken":                          # fiolinfiken: stamme og store runde blader
            stem_h = 1.3 * size
            cyl(f"{name}_Stamme", (0, 0, top), 0.03 * size, 0.02 * size, stem_h, wood, r, segs=12)
            for k in range(11):
                a = k * 137.5
                z = top + stem_h * (0.35 + 0.065 * k)
                d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
                lf = ell(f"{name}_Blad_{k}", tuple(d * 0.18 * size + Vector((0, 0, z))),
                         (0.15 * size, 0.022 * size, 0.2 * size), pick(leaf, k), parent=r)
                lf.rotation_euler = (math.radians(-35), 0, math.radians(a + 90))
        elif kind == "monstera":                       # store, runde blader på lange stilker
            for k in range(7):
                a = k * 51 + rnd.uniform(-8, 8)
                d = Vector((math.cos(math.radians(a)) * 0.6, math.sin(math.radians(a)) * 0.6, 1.0))
                end = stalk(f"{name}_Stilk_{k}", (0, 0, top), d, rnd.uniform(0.5, 0.9) * size, 0.015 * size,
                            stem_mat, r)
                lf = ell(f"{name}_Blad_{k}", tuple(end), (0.24 * size, 0.022 * size, 0.2 * size),
                         pick(leaf, k), parent=r)
                lf.rotation_euler = (math.radians(-55), 0, math.radians(a + 90))
        elif kind == "palme":                          # tre slanke stammer med buede blader
            for t in range(3):
                a0 = t * 120 + rnd.uniform(-20, 20)
                d = Vector((math.cos(math.radians(a0)) * 0.12, math.sin(math.radians(a0)) * 0.12, 1.0))
                end = stalk(f"{name}_Stamme_{t}", (0, 0, top), d, rnd.uniform(1.0, 1.5) * size, 0.022 * size,
                            stem_mat, r)
                for k in range(7):
                    a = math.radians(k * 51 + t * 17)
                    lf = ell(f"{name}_Blad_{t}_{k}", (0, 0, 0), (0.05 * size, 0.012 * size, 0.42 * size),
                             pick(leaf, k), parent=r)
                    lf.rotation_euler = (math.radians(65), 0, a)
                    lf.location = end + lf.rotation_euler.to_matrix() @ Vector((0, 0, 0.38 * size))
        elif kind == "kaktus":                         # rund kaktus med armer og en blomst
            h = 0.55 * size
            ell(f"{name}_Kropp", (0, 0, top + h), (0.17 * size, 0.17 * size, h), cactus, parent=r)
            for k, side in enumerate((-1, 1)):
                ell(f"{name}_Arm_{k}", (side * 0.2 * size, 0, top + h * (1.05 + 0.25 * k)),
                    (0.07 * size, 0.07 * size, 0.2 * size), cactus, parent=r)
            ell(f"{name}_Blomst", (0, 0, top + 2 * h), (0.06 * size, 0.06 * size, 0.04 * size), bloom, parent=r)
        else:                                          # solsikker: tre høye i en stor potte
            for k in range(3):
                a = math.radians(k * 120 + 30)
                sunflower(f"{name}_{k}", r, (math.cos(a) * 0.12, math.sin(a) * 0.12, top),
                          rnd.uniform(1.6, 2.5) * min(size, 1.2), rnd, facing=-r.rotation_euler.z * 57.3 + rnd.uniform(-25, 25))
        return r

    # Rommet fylles med planter, store og små, alle på gulvet. Plassene velges
    # automatisk utenfor løpeveiene, kamerabanene og møblene (se PLANT_KEEP_OUT).
    # De største plantene og solsikkene står ut mot kantene og bakover.
    rnd = random.Random(21)
    spots = plant_spots(rnd)
    small = ("busk", "kaktus", "hoy", "monstera")
    big = ("fiken", "palme", "monstera", "hoy")
    for i, (x, y) in enumerate(spots):
        edge = min(1.0, max(0.0, (abs(x) - 4.0) / 4.5))
        size = rnd.uniform(0.7, 1.1) + 1.0 * edge * rnd.random()
        if abs(x) > 7.0 and y > -1.5 and i % 3 == 0:
            kind = "solsikke"
        else:
            kind = (big if size > 1.25 else small)[i % 4]
        plant(f"Plante_{i:02d}", (x, y), kind, size, seed=100 + i)

    # Lav trebenk med en pute
    bench = root("Benk", (5.3, 5.0), -20)
    box("Benk_Sete", (0, 0, 0.42), (1.6, 0.42, 0.07), wood, bench)
    for x in (-0.65, 0.65):
        box(f"Benk_Bein_{x}", (x, 0, 0.2), (0.07, 0.36, 0.4), wood, bench)
    ell("Benk_Pute", (-0.35, 0, 0.53), (0.26, 0.17, 0.07), mustard, parent=bench)

    # Sittesekk
    ell("Sittesekk", (0, 0, 0.3), (0.5, 0.48, 0.32), teal, parent=root("Sittesekk_Rot", (-7.2, 3.4)))

    # Lav bokhylle med bøker
    shelf = root("Bokhylle", (7.7, 3.2), -100)
    box("Bokhylle_Kropp", (0, 0, 0.45), (1.3, 0.38, 0.9), cream, shelf)
    box("Bokhylle_Hylle", (0, -0.02, 0.45), (1.22, 0.36, 0.03), wood, shelf)
    rnd = random.Random(12)
    x = -0.55
    for k in range(9):
        w = rnd.uniform(0.05, 0.09)
        h = rnd.uniform(0.24, 0.34)
        z0 = 0.47 if k < 5 else 0.06
        if k == 5:
            x = -0.55
        box(f"Bok_{k}", (x + w / 2, -0.04, z0 + h / 2), (w, 0.26, h),
            [teal, mustard, clay, cream][k % 4], shelf, rz=0 if k % 3 else 6)
        x += w + 0.015


# --------------------------------------------------------------------------
# Kamera og shots
# --------------------------------------------------------------------------

def build_cameras(coll):
    def cam(name, loc, target, lens, was=None):
        """was: tidligere brennvidde; kameraet trekkes bakover så utsnittet blir likt
        med lengre linse (mykere bakgrunn, mer intimt)."""
        if was:
            loc = Vector(target) + (Vector(loc) - Vector(target)) * (lens / was)
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
        "wide": cam("CAM_01_Wide", (0, -9.0, 1.45), (0.2, 0, 1.0), 32),
        "medium": cam("CAM_02_Medium", (1.6, -5.0, 1.45), (0.6, 0.4, 1.1), 35),
        "deep": cam("CAM_03_Dyp", (0.5, -8.5, 1.2), (0, 1.5, 1.0), 30),
        "end": cam("CAM_04_Ende", (0, -7.5, 1.5), (0.3, -3.5, 1.25), 24),
        # Nærbilder på relasjonen mellom dem (statiske, siktet mot hodehøyde)
        "cu_boy_ots": cam("CAM_CU_01_Gutt_OTS", (3.3, -0.6, 1.75), (1.0, 0.35, 1.3), 38),
        "cu_girl_laugh": cam("CAM_CU_02_Jente_Ler", (-0.9, -0.6, 1.5), (1.85, 0.35, 1.3), 55, was=40),
        "cu_boy_front": cam("CAM_CU_03_Gutt", (0.6, -0.9, 1.45), (-0.9, 0.4, 1.3), 50, was=36),
        "cu_girl_hit": cam("CAM_CU_04_Jente_Treff", (0.5, -1.0, 1.45), (2.1, 0.35, 1.3), 50, was=38),
        "cu_lying": cam("CAM_CU_05_Liggende", (-1.0, -2.7, 2.6), (-1.0, -1.85, 0.3), 32),
        "cu_tease": cam("CAM_CU_06_Erting_OTS", (1.6, -3.6, 1.6), (-0.4, -2.9, 1.3), 45, was=34),
        "cu_hug": cam("CAM_CU_07_Klem", (0.6, -6.6, 1.42), (0.06, -5.0, 1.4), 50, was=35),
        "cu_run": cam("CAM_CU_08_Loep", (-5.0, 4.6, 0.9), (0.0, 5.0, 1.0), 26),
        # Følger gutten bakfra (posisjonen er en offset fra ham, se build_cinematic)
        "track": cam("CAM_00_Tracking", (-2.4, -0.6, 1.5), (0, 0.4, 1.0), 30),
        "cu_prints": cam("CAM_CU_10_Handavtrykk", (-0.2, -2.7, 1.1), (-0.25, -1.45, 0.0), 30),
        "cu_splash": cam("CAM_CU_11_Plask", (1.2, -1.1, 0.9), (0.0, 0.4, 0.9), 28),
        "cu_aha": cam("CAM_CU_12_Aha", (3.9, 1.7, 1.4), (2.25, 0.35, 1.4), 50, was=40),
        "cu_oops": cam("CAM_CU_13_Oi", (0.8, -1.5, 1.42), (0.95, 0.4, 1.35), 55, was=42),
        "cu_jump": cam("CAM_CU_14_Hoppeklem", (0.3, -7.9, 1.5), (0.3, -5.0, 1.4), 28),
        "dance": cam("CAM_15_Dans", (0.05, -10.1, 1.4), (0.05, -6.0, 1.3), 28),
        "cu_ots_tub": cam("CAM_CU_15_Ned_I_Balja_OTS", (-1.45, -0.95, 2.35), (0.0, 0.4, 0.5), 30),
        # Ekstremt nærbilde av øynene hans sett fra malingen i balja
        "cu_eyes": cam("CAM_CU_16_Oyne_Skinner", (0.62, 0.3, 0.95), (-0.4, 0.4, 1.15), 55),
        "fall": cam("CAM_18_Pladask", (2.6, -7.6, 1.1), (-0.6, -5.2, 0.8), 28),
        "cu_floor": cam("CAM_CU_19_Fra_Gulvet", (-0.2, -5.35, 0.35), (-1.3, -5.9, 1.45), 24),
        "party": cam("CAM_20_Fest", (0.6, -9.2, 0.7), (-0.8, -5.5, 0.9), 24),
        "cu_nod": cam("CAM_CU_21_Nikker", (0.9, -4.0, 2.1), (-1.8, -5.0, 0.4), 30),
        "dance_boy": cam("CAM_16_Dans_Gutt", (1.8, -9.0, 0.9), (0.6, -6.5, 1.4), 32),
        "dance_girl": cam("CAM_17_Dans_Jente", (-1.8, -9.0, 0.9), (-0.5, -6.5, 1.4), 32),
    }

    scene = bpy.context.scene
    shots = [
        (1, "track", "SH010 Følger gutten bakfra til balja"),
        (80, "cu_ots_tub", "SH011b Over skulderen hans, ned i regnbuemalingen"),
        (86, "cu_eyes", "SH011c ECU Øynene skinner når han ser regnbuemalingen"),
        (92, "wide", "SH012 Kaster maling rundt seg"),
        (156, "cu_prints", "SH013 Innklipp: håndavtrykk på gulvet"),
        (190, "wide", "SH014 Beundrer verket sitt"),
        (222, "cu_boy_ots", "SH021 CU Gutten ser henne (OTS)"),
        (228, "medium", "SH022 Spark, hodet ned i balja"),
        (238, "cu_splash", "SH0225 CU Plask, hodet først i balja"),
        (252, "cu_girl_laugh", "SH023 CU Søster ler av ham"),
        (272, "medium", "SH024 Han spretter opp"),
        (288, "cu_boy_front", "SH025 CU Gutten full av maling"),
        (306, "wide", "SH030 Han kaster tilbake"),
        (323, "cu_girl_hit", "SH031 CU Søster blir truffet, sint"),
        (354, "cu_aha", "SH0315 CU Søster ser spannet: aha!"),
        (364, "wide", "SH032 Hun henter spann"),
        (378, "cu_boy_front", "SH033 CU Gutten: uh-oh"),
        (390, "wide", "SH034 Jakt ut av bildet"),
        (484, "deep", "SH040 Jakt dypt i rommet"),
        (500, "cu_run", "SH040b CU Søster raser forbi og river ned tårnet, han etter"),
        (522, "deep", "SH040c Jakt frem, de sklir"),
        (594, "cu_lying", "SH041 CU Ligger og ler sammen"),
        (618, "deep", "SH042 Piruett og dunk"),
        (660, "cu_tease", "SH043 CU Søster erter ham (OTS)"),
        (672, "end", "SH060 Jakt mot kamera, maling på linsa"),
        (752, "cu_oops", "SH0605 CU Gutten: oi! fniser"),
        (766, "end", "SH0607 Søster tørker linsa og smiler"),
        (904, "cu_hug", "SH061 CU Klem, fniser til hverandre"),
        (946, "end", "SH062 Varmt smil i kamera"),
        (PLAY - 2, "cu_jump", "SH063 CU Hoppeklem, han rister henne av seg"),
        (PLAY + 58, "fall", "SH064 Han hopper på henne, hun dukker, pladask"),
        (PLAY + 80, "cu_floor", "SH065 Hun ler av ham (fra gulvet ved hodet hans)"),
        (PARTY, "party", "SH066 Hun begynner å danse, lyset dempes, strobelys"),
        (PARTY + 18, "cu_nod", "SH067 CU Han ligger på ryggen og nikker i takt"),
        (PARTY + 36, "party", "SH068 Han slenger seg opp og danser"),
        (DANCE + 12, "dance_boy", "SH070 Guttens robotdans mot kamera (lav vinkel)"),
        (DANCE + 60, "dance_girl", "SH071 Søster snurrer frem mot kamera (lav vinkel)"),
        (DANCE + 108, "dance", "SH072 De kommer helt frem og griper kameraet, rommet blir lyst"),
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
        (852, "Uttrykk J: overrasket, hører ham"),
        (870, "Uttrykk G+J: klem, latter"),
        (892, "Uttrykk G+J: smiler i kamera"),
        (910, "Uttrykk G+J: fniser, ser på hverandre"),
        (946, "Uttrykk G+J: ekstra klem, øynene igjen"),
        (966, "Uttrykk G+J: varmt smil i kamera, hold"),
        (PLAY, "Uttrykk J: får en idé, glitrende øyne"),
        (PLAY + 8, "Uttrykk J: hopper, stor jubel"),
        (PLAY + 24, "Uttrykk G: lurt «nå skal du få»; J: hyler av latter"),
        (PLAY + 64, "Uttrykk G: lurt, lader opp"),
        (PLAY + 66, "Uttrykk J: dukker unna, overrasket og fornøyd"),
        (PLAY + 76, "Uttrykk G: pladask! nesa i gulvet"),
        (PLAY + 82, "Uttrykk J: ler så hun rister"),
        (PARTY, "Uttrykk J: begynner å danse, øynene igjen"),
        (PARTY + 12, "Uttrykk G: ligger på ryggen og nikker i takt, smiler opp"),
        (PARTY + 40, "Uttrykk G: slenger seg opp, «min tur!»"),
        (DANCE + 14, "Uttrykk G: kul og konsentrert robotdans, stolt"),
        (DANCE + 62, "Uttrykk J: lykkelig, snurrer med øynene igjen"),
        (DANCE + 120, "Uttrykk G+J: griper kameraet, store smil rett inn i linsa"),
        (DANCE + 136, "Uttrykk G+J: ser fjæravtrykket på linsa, ser på hverandre"),
        (DANCE + 158, "Uttrykk G+J: bryter ut i latter. Slutt"),
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
    (134, 148),   # tredje kast er tatt ut
    (172, 190),   # halvparten av malingen med hendene
    (199, 211),   # stolt hopp
    (814, 832),   # søsters glade hopp etter linsa
]


def fcurves_of(idb):
    ad = getattr(idb, "animation_data", None)
    if not ad or not ad.action:
        return []
    act = ad.action
    if getattr(act, "layers", None):                   # Blender 4.4+ (slotted actions)
        return [fc for layer in act.layers for strip in layer.strips
                for bag in strip.channelbags for fc in bag.fcurves]
    return list(act.fcurves)


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


# Pusterom: (frame etter CUTS, antall frames). Alt fryses og holdes ved frame,
# og figurene puster litt mens de står. Alt etterpå skyves bakover.
HOLDS = [
    (84, 16),     # over skulderen: han ser regnbuemalingen
    (90, 24),     # øynene skinner, så jubler han
    (160, 24),    # står og beundrer verket sitt før søster kommer
    (180, 16),    # han ser søster komme (over skulderen hennes)
    (214, 18),    # søster ler av ham, han sitter fast i balja
    (262, 26),    # dryppende av maling, stirrer på henne før han slår tilbake
    (290, 14),    # søster er truffet: sjokk, så sinne
    (312, 18),    # søster stopper opp når hun får øye på spannet
    (340, 16),    # «uh-oh», han fryser
    (572, 22),    # de ligger og puster ut etter latteren
    (620, 16),    # søster erter ham, han ser på henne
    (712, 16),    # gutten: «oi!», fniser
    (748, 20),    # søster puster lettet ut etter at linsa er tørket
    (854, 20),    # klemmen: de fniser og ser på hverandre
    (950, 12),    # hun klemmer ham, han ser lurt opp
    (1006, 14),    # pladask: stille et øyeblikk
    (1074, 12),   # han ligger og får en idé før han slenger seg opp (ett taktslag)
]
END_HOLD = 24     # siste bilde står litt før det er slutt


def apply_holds():
    scene = bpy.context.scene
    chars = [bpy.data.objects.get(n) for n in ("Gutt", "Jente")]
    # Stabil nøkkel per kurve (Python-id-er for RNA-objekter gjenbrukes og kan ikke brukes)
    fkey = lambda fc: (fc.id_data.name, fc.data_path, fc.array_index)
    fx = [ob for ob in bpy.data.objects if ob.name.startswith(("Sprut", "Flekker", "Klatt"))]
    for at, n in sorted(HOLDS, reverse=True):
        # Sprut og klatter som er i lufta akkurat nå, får fly ferdig i stedet for å fryse
        skip = set()
        for ob in fx:
            curves = fcurves_of(ob)
            frames = [kp.co.x for fc in curves for kp in fc.keyframe_points]
            if frames and min(frames) < at <= max(frames):
                skip.update(fkey(fc) for fc in curves)
        for fc in iter_fcurves():
            if fkey(fc) in skip:
                continue
            v = fc.evaluate(at)
            before = [kp for kp in fc.keyframe_points if kp.co.x < at]
            interp = max(before, key=lambda kp: kp.co.x).interpolation if before else "BEZIER"
            for kp in fc.keyframe_points:
                if kp.co.x >= at:
                    kp.co.x += n
                    kp.handle_left.x += n
                    kp.handle_right.x += n
            for f in (at, at + n):                     # holdet arver interpolasjonen
                kp = fc.keyframe_points.insert(f, v)   # (CONSTANT forblir CONSTANT)
                kp.interpolation = interp
            fc.update()
        for ob in chars:                               # litt pust i holdet
            if not ob:
                continue
            for fc in fcurves_of(ob):
                if fc.data_path == "scale":
                    v = fc.evaluate(at)
                    fc.keyframe_points.insert(at + n // 2, v * (1.025 if fc.array_index == 2 else 0.988))
                    fc.update()
        for m in scene.timeline_markers:
            if m.frame >= at:
                m.frame += n
        scene.frame_end += n
    scene.frame_end += END_HOLD


def final_frame(f):
    """Ferdig frame (etter CUTS og HOLDS) for en opprinnelig frame."""
    r = retime(f)
    return r + sum(n for at, n in HOLDS if r >= at)


# --------------------------------------------------------------------------
# Temp-musikk: syntetisk plassholder i 120 BPM, laget av skriptet selv
# --------------------------------------------------------------------------

def make_temp_music(path):
    """Lager temp_musikk.wav: lette plukk gjennom historien, lydstikk på treffene,
    fullt beat i festen og et stort akkordløft når de griper kameraet.
    Bytt den ut med ekte musikk i 120 BPM; taktslagene ligger på festens første frame."""
    import wave
    import numpy as np
    sr = 44100
    end = bpy.context.scene.frame_end
    n = int(end / FPS * sr) + sr
    out = np.zeros(n)
    t_of = lambda frame: (frame - 1) / FPS
    hz = lambda midi: 440.0 * 2 ** ((midi - 69) / 12)

    def add(t0, sig, gain):
        i = int(t0 * sr)
        if 0 <= i < n:
            seg = sig[: n - i]
            out[i:i + len(seg)] += gain * seg

    def env(dur, attack=0.005, decay=None):
        tt = np.arange(int(dur * sr)) / sr
        e = np.minimum(tt / attack, 1.0)
        return tt, e * np.exp(-tt / (decay or dur / 4))

    def pluck(midi, dur=0.4):
        tt, e = env(dur, decay=0.12)
        f = hz(midi)
        return e * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt))

    def kick():
        tt, e = env(0.25, attack=0.001, decay=0.08)
        f = 45 + 80 * np.exp(-tt * 30)
        return e * np.sin(2 * np.pi * np.cumsum(f) / sr)

    def noise(dur, decay):
        tt, e = env(dur, attack=0.001, decay=decay)
        return e * np.random.default_rng(int(dur * 1e4)).uniform(-1, 1, len(tt))

    def chord(midis, dur, decay=None, attack=0.02):
        tt, e = env(dur, attack=attack, decay=decay or dur / 2)
        return e * sum(np.sin(2 * np.pi * hz(m) * tt) for m in midis) / len(midis)

    party, grab = final_frame(PARTY), final_frame(DANCE + 120)
    beat = BEAT / FPS
    prog = [(48, [60, 64, 67]), (45, [57, 60, 64]), (41, [57, 60, 65]), (43, [59, 62, 67])]  # C Am F G
    melody = [72, 76, 79, 76, 74, 79, 77, 74]

    # Historien: plukk på hvert slag, bass på 1 og 3, takten går bakover fra festen
    k = -int((party - 1) / BEAT)
    while True:
        frame = party + k * BEAT
        if frame >= party:
            break
        if frame >= 1:
            bar, b = divmod(k, 4)
            root, notes = prog[bar % 4]
            add(t_of(frame), pluck(melody[k % 8]), 0.16)
            if b % 2 == 0:
                add(t_of(frame), pluck(root - 12 + 24, 0.6), 0.14)
            add(t_of(frame + BEAT / 2), noise(0.04, 0.01), 0.025)
        k += 1

    # Festen: fullt beat frem til de griper kameraet
    k = 0
    while party + k * BEAT < grab:
        frame = party + k * BEAT
        bar, b = divmod(k, 4)
        root, notes = prog[bar % 4]
        add(t_of(frame), kick(), 0.5)
        if b in (1, 3):
            add(t_of(frame), noise(0.18, 0.05), 0.22)
        for h in (0, 0.5):
            add(t_of(frame + h * BEAT), noise(0.05, 0.012), 0.06)
            add(t_of(frame + h * BEAT), pluck(root - 12, 0.25), 0.25)
        if b in (1, 3):
            add(t_of(frame + BEAT / 2), chord([m + 12 for m in notes], 0.2, 0.06), 0.18)
        k += 1

    # Grepet om kameraet: rommet blir lyst, stort varmt akkordløft
    add(t_of(grab), chord([48, 60, 64, 67, 72, 76], (end - grab) / FPS + 0.5, attack=0.05), 0.5)

    # Lydstikk på treffene (opprinnelige frames)
    stings = [(230, "dunk"), (246, "plask"), (326, "plask"), (396, "plask"), (512, "brak"),
              (562, "skli"), (578, "skli"), (742, "plask"), (870, "varm"), (PLAY + 8, "hopp"),
              (PLAY + 76, "dunk"), (DANCE + 137, "plink"), (DANCE + 150, "latter")]
    stings += [(f, "klonk") for f in (31, 215, 507, 517, 689, 709)]
    for f, kind in stings:
        t0 = t_of(final_frame(f))
        if kind == "dunk":
            add(t0, kick(), 0.6)
        elif kind == "plask":
            add(t0, noise(0.35, 0.09), 0.3)
            add(t0, pluck(60, 0.3), 0.1)
        elif kind == "brak":
            for i in range(3):
                add(t0 + 0.07 * i, noise(0.2, 0.05), 0.25)
                add(t0 + 0.07 * i, pluck(84 - 5 * i, 0.2), 0.15)
        elif kind == "skli":
            tt, e = env(0.5, decay=0.3)
            add(t0, e * np.sin(2 * np.pi * np.cumsum(900 - 1200 * tt) / sr), 0.12)
        elif kind == "varm":
            add(t0, chord([60, 64, 67, 72], 2.5, attack=0.3), 0.35)
        elif kind == "hopp":
            tt, e = env(0.4, decay=0.2)
            add(t0, e * np.sin(2 * np.pi * np.cumsum(300 + 900 * tt) / sr), 0.2)
        elif kind == "plink":
            add(t0, pluck(96, 0.5), 0.35)
        elif kind == "latter":
            for i, m in enumerate((72, 76, 79, 84, 88)):
                add(t0 + 0.09 * i, pluck(m, 0.4), 0.25)
        elif kind == "klonk":
            add(t0, pluck(79, 0.15), 0.2)
            add(t0, noise(0.08, 0.02), 0.12)

    out /= max(1e-6, np.abs(out).max()) / 0.8
    data = (out * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data)
    return path


def add_music_strip(path):
    scene = bpy.context.scene
    ed = scene.sequence_editor or scene.sequence_editor_create()
    strips = ed.strips if hasattr(ed, "strips") else ed.sequences
    for st in list(strips):
        strips.remove(st)
    strips.new_sound("Temp_musikk", path, 1, FRAME_START)


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
    for ob in (boy, girl):
        build_face_rig(ob, c_char)
        animate_expressions(ob.name, EXPR_TIMELINE[ob.name])
    for ob in (boy, girl):                             # blikkmål rett frem, styres i build_acting()
        build_face(ob, c_char, empty(f"Blikk_{ob.name}", c_char, (0, -4.0, EYE_Z), ob))
    ARMS.clear()
    build_arms(boy, c_char)
    build_arms(girl, c_char)

    _last_rz.clear()
    animate_boy(boy)
    animate_girl(girl)
    animate_boy_arms(boy)
    animate_girl_arms(girl)
    animate_props(tub, bucket_g, bucket_b)
    cams = build_cameras(c_cam)
    build_cinematic(cams, boy, girl, c_cam)
    build_acting(boy, girl, c_char)
    build_paint_fx(c_fx, pm, boy, girl, cams["end"])
    build_knockables(c_props, c_fx, pm, metal)
    build_paint_marks(c_fx, pm)
    build_ending(boy, girl, c_char, c_light, cams["dance"])
    eyes_shine(boy, c_char, 86, 92, [pm[c] for c in ("Rosa", "Gul", "Turkis", "Lilla")])
    for ob in (boy, girl):
        anticipation_and_settle(ob)
    break_twinning(girl, [(586, 620), (636, 660), (904, 946), (DANCE + 120, DANCE + 136),
                          (DANCE + 150, FRAME_END)])
    wing_drag(boy, girl)
    for ob in (boy, girl):
        hair_follow_through(ob)
    color_script(c_light)
    build_set_dressing(c_set, pm, metal)
    build_furniture(c_set)
    setup_render()
    apply_cuts()
    apply_holds()
    sparkle_stars(boy, c_char, final_frame(86), final_frame(92))

    args = parse_args()
    out_dir = os.path.dirname(os.path.abspath(bpy.path.abspath(args["save"]))) if "save" in args \
        else (os.path.dirname(bpy.data.filepath) or tempfile.gettempdir())
    music = make_temp_music(os.path.join(out_dir, "temp_musikk.wav"))
    add_music_strip(music)
    if "save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(args["save"]))
        print("Lagret:", args["save"])


if __name__ == "__main__":
    main()
