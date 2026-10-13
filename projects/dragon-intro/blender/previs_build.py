#!/usr/bin/env python3
"""
previs_build.py — bygger blockout-previs for HELIOS action intro.

Lager hele 115-sekunders sekvensen som gra kasser: 25 kameraer bundet til
timeline-markorer, slik at du kan spille av fra frame 1 og se klippet kutte
seg selv gjennom alle shots.

Kjor i Blender:
    blender --background --python previs_build.py
    blender --background --python previs_build.py -- --out /path/helios.blend

Eller med bpy som pip-modul:
    python3 previs_build.py --out helios_previs.blend

Alt i CONFIG er ment a tunes. Det er hele poenget med previs.
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# CONFIG — verdenslayout i meter. Tun disse.
# ---------------------------------------------------------------------------

FPS = 24
RES = (2048, 858)          # 2.39:1
SEED = 7

CLIFF_FACE_Y = 0.0         # fjellveggens framside
CLIFF_TOP_Z = 352.0        # toppen av veggen / kanten mannen loper mot
CLIFF_WIDTH = 1400.0       # bredde i X
CLIFF_DEPTH = 500.0        # hvor langt innover landet massen gar
CAVE_Z = 205.0             # grotteinngangens hoyde i veggen
CAVE_W, CAVE_H = 46.0, 58.0

# Gangbart dekke pa toppen. Fjellmassen fyller opp TIL CLIFF_TOP_Z, sa alt
# som skal sta eller filmes der oppe ma ligge over denne — ikke pa den.
# Kameraer under dette havner inne i massen og rendrer svart.
GROUND_Z = CLIFF_TOP_Z
EYE_Z = GROUND_Z + 1.65    # oyehoyde staende
LOW_Z = GROUND_Z + 1.15    # lavt handholdt

BOAT_Y = -2400.0           # batenes startposisjon
BOAT_XS = (-70.0, -24.0, 24.0, 70.0)
FOG_FAR_Y = -1900.0        # takebankens ytterkant (mot batene)
FOG_NEAR_Y = -700.0        # takebankens innerkant (mot fjellet)
FOG_DENSITY = 0.0018       # takebanken
HAZE_DENSITY = 0.00022     # tynn global dis — gir dybde, koster ingenting

# Avstanden kameraet trenger for a fa et motiv pa plass i framet:
#
#     bredde_i_frame = avstand * 36mm / brennvidde
#     hoyde_i_frame  = avstand * (36/2.39)mm / brennvidde
#
# Det var her forste utkast rok: S12 sto 172 m fra en 352 m hoy vegg med
# 32 mm, som trenger ~740 m for a fa hele hoyden inn. Regn for du gjetter.

DRAGON_SPAN = 22.0         # vingespenn — styrer skalaen i S23/S24
WINGBEAT_SEC = 2.0         # ett fullt vingeslag. Se docs/dragon.md

# Shotliste: (id, varighet, brennvidde, kam start, kam slutt,
#             look-at start, look-at slutt, notat, parent)
#
# Posisjoner er (x, y, z) i meter. Er parent satt (f.eks. "BOAT_1") er
# koordinatene LOKALE til det objektet, og kameraet seiler med bat
# gjennom Akt 1 i stedet for a bli liggende igjen bak den.
SHOTS = [
    ("S01", 6.0, 85, (-150, -2455, 2.2), (-146, -2448, 2.4),
     (-70, -2412, 3.0), (-68, -2400, 3.2), "Apning: vrakgods, forste stevn", None),
    ("S02", 5.0, 35, (-190, -2600, 60), (-170, -2576, 55),
     (0, -2392, 6), (8, -2380, 6), "Formasjonen, fire langskip", None),
    ("S03", 4.0, 35, (0, -17, 3.5), (0, -14, 3.5),
     (0, -2, 3.0), (0, -2, 3.0), "Ombord: arer, ansikter", "BOAT_1"),
    ("S04", 3.0, 50, (-3.2, 20.5, 3.8), (-3.2, 19.5, 3.8),
     (0, 13.5, 3.4), (0, 13.5, 3.4), "Lederen speider mot taken", "BOAT_1"),
    ("S05", 4.0, 35, (0, -2480, 12), (0, -2480, 12),
     (-95, -2362, 4), (95, -2362, 4), "Ordren gar nedover rekka [TRIM]", None),
    ("S06", 5.0, 50, (-4.4, 6.2, 3.5), (-4.2, 5.6, 3.45),
     (-2.1, 2.2, 3.2), (-2.1, 2.2, 3.15), "Buene opp: hender, streng, spiss", "BOAT_1"),
    ("S07", 4.0, 24, (0, -2480, 16), (0, -2480, 16),
     (0, -2332, 7), (0, -2330, 7), "Alle fire, buer hevet. Statisk", None),
    ("S08", 4.0, 50, (-3.2, 19.5, 3.8), (-3.0, 17.0, 3.75),
     (0, 13.5, 3.4), (0, 13.5, 3.4), "FIRE! Push-in", "BOAT_1"),
    ("S09", 3.0, 35, (0, -2440, 26), (0, -2438, 28),
     (0, -2320, 50), (0, -2310, 72), "Salven gar fra alle fire", None),
    ("S10", 3.0, 35, (0, -2400, 10), (0, -2398, 11),
     (0, -2340, 40), (0, -2280, 165), "Pilene stiger, tilt opp, las pa svermen", None),
    ("S11", 8.0, 40, (0, -2250, 180), (0, -1250, 262),
     (0, -2050, 200), (0, -1000, 268), "Pil-POV inn i taken", None),
    # Pushen fra 900 m til 360 m er det som gir hoyden. Pa avstand ser vi
    # hele silhuetten komme ut av taken, naert tarner den over framet.
    ("S12", 8.0, 24, (0, -980, 170), (0, -400, 90),
     (0, -120, 230), (0, -50, 330), "REVEAL: fjellveggen. Tilt oppover", None),
    # Kameraet ma ligge over kanten, ellers skjuler toppen mannen bak den.
    ("S13", 5.0, 120, (0, -700, 404), (0, -692, 402),
     (0, 34, 353.5), (0, 32, 353.5), "Skikkelsen pa kanten. Hold ham liten", None),
    ("S14", 4.0, 70, (0, -700, 250), (0, -694, 248),
     (0, -4, 205), (0, -4, 205), "DRACARYS! Grotta lyser opp", None),
    ("S15", 4.0, 50, (-120, -760, 262), (-114, -752, 264),
     (0, -8, 232), (0, -8, 228), "Skriket. Fugler, lostein", None),
    ("S16", 3.0, 28, (0, 30, GROUND_Z + 1.3), (0, 27, GROUND_Z + 1.3),
     (0, -40, 430), (0, -36, 440), "Fra mannen: pilene kommer ned", None),
    ("S17", 3.0, 40, (0, -180, 345), (0, -172, 347),
     (0, -6, 362), (0, -6, 366), "BAAM: ildvegg langs kanten", None),
    ("S18", 5.0, 85, (2.6, 6.8, 1.78), (2.5, 6.4, 1.78),
     (0, 0.1, 1.70), (0, 0.1, 1.70), "Pilene blir til stov. Slow-mo", "MAN"),
    ("S19", 4.0, 35, (0.8, 9.5, 1.30), (0.6, 8.0, 1.28),
     (0, 0.2, 1.35), (0, 0.2, 1.35), "Lopet. Handholdt bak ham", "MAN"),
    ("S20", 4.0, 50, (1.2, -5.5, 1.80), (1.1, -5.0, 1.80),
     (0, 0, 1.75), (0, 0, 1.75), "Naejot mazis, Helios!", "MAN"),
    ("S21", 4.0, 35, (0, 42, EYE_Z), (0, 23, EYE_Z),
     (0, -30, GROUND_Z - 2), (0, -40, GROUND_Z - 4), "Hoppet. Kamera kryper fram", None),
    ("S22", 3.0, 35, (0, 23, EYE_Z), (0, 22, EYE_Z),
     (0, -40, GROUND_Z - 3), (0, -40, GROUND_Z - 3), "STILLE. Tomt frame i 3 sek", None),
    ("S23", 7.0, 28, (0, 26, GROUND_Z + 2.2), (0, 26, GROUND_Z + 2.2),
     (0, -40, GROUND_Z - 12), (0, -52, GROUND_Z + 40), "VOFF. Dragen bryter opp i frame", None),
    ("S24", 7.0, 50, (0, 70, 390), (0, 320, 470),
     (0, -60, 374), (0, -900, 280), "Zoom ut. Skyggen inn i taken", None),
    ("S25", 5.0, 50, (0, 340, 476), (0, 340, 476),
     (0, -1100, 250), (0, -1100, 250), "BLACK + tekst (gjores i Premiere)", None),
]


# ---------------------------------------------------------------------------
# Hjelpere
# ---------------------------------------------------------------------------

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.materials, bpy.data.meshes, bpy.data.cameras):
        for item in list(coll):
            coll.remove(item)


def collection(name):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def grey(name, value, emission=0.0):
    """Flat gra previs-shader. emission > 0 gir et lysende blokk."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:          # <= 4.x trenger use_nodes, 5.x har den alt
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emission > 0:
        shader = nt.nodes.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = (1.0, 0.42, 0.12, 1.0)
        shader.inputs["Strength"].default_value = emission
    else:
        shader = nt.nodes.new("ShaderNodeBsdfDiffuse")
        shader.inputs["Color"].default_value = (value, value, value, 1.0)
    nt.links.new(shader.outputs[0], out.inputs["Surface"])
    return mat


def box(name, coll, loc, size, mat=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = Vector(size)
    if mat:
        obj.data.materials.append(mat)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def shot_frames():
    """Returnerer [(id, start, end, ...)] i frames, utregnet fra varighetene."""
    out = []
    f = 1
    for (sid, dur, lens, c0, c1, t0, t1, note, parent) in SHOTS:
        n = int(round(dur * FPS))
        out.append(dict(id=sid, start=f, end=f + n - 1, lens=lens,
                        cam0=c0, cam1=c1, tgt0=t0, tgt1=t1, note=note,
                        parent=parent))
        f += n
    return out


def key_loc(obj, frame, loc):
    obj.location = Vector(loc)
    obj.keyframe_insert("location", frame=frame)


def iter_fcurves(obj):
    """
    F-curves for et objekt, uavhengig av Blender-versjon.

    Blender 4.4 innforte slotted actions: action.fcurves finnes ikke lenger,
    kurvene ligger i action.layers[].strips[].channelbag(slot). Eldre
    versjoner har den flate action.fcurves. Denne haandterer begge.
    """
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    act = ad.action
    if hasattr(act, "fcurves"):                      # Blender <= 4.3
        yield from act.fcurves
        return
    for layer in act.layers:                         # Blender >= 4.4
        for strip in layer.strips:
            if not hasattr(strip, "channelbag"):
                continue
            cb = strip.channelbag(ad.action_slot)
            if cb:
                yield from cb.fcurves


def linear(obj):
    """Previs skal lese jevnt — ingen ease-in/out som jukser timingen."""
    for fc in iter_fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# ---------------------------------------------------------------------------
# Bygg: havet og batene
# ---------------------------------------------------------------------------

def build_ocean(mat):
    coll = collection("OCEAN")
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, -1600, 0))
    obj = bpy.context.active_object
    obj.name = "OCEAN_plane"
    obj.data.materials.append(mat)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return coll


def build_boats(mat_hull, mat_crew):
    """Fire langskip. Hvert skip er skrog + mast + en rad mannskapskasser."""
    coll = collection("BOATS")
    frames = {s["id"]: s for s in shot_frames()}
    travel_start = frames["S01"]["start"]
    travel_end = frames["S10"]["end"]

    for i, x in enumerate(BOAT_XS, start=1):
        root = bpy.data.objects.new(f"BOAT_{i}", None)
        coll.objects.link(root)
        root.empty_display_size = 6

        hull = box(f"BOAT_{i}_hull", coll, (0, 0, 1.0), (7.0, 30.0, 2.4), mat_hull)
        prow = box(f"BOAT_{i}_prow", coll, (0, 16.5, 2.6), (1.4, 5.0, 5.0),
                   mat_hull, rot=(math.radians(-18), 0, 0))
        mast = box(f"BOAT_{i}_mast", coll, (0, -2.0, 7.0), (0.7, 0.7, 12.0), mat_hull)
        parts = [hull, prow, mast]

        # Mannskap: to rader kasser i menneskehoyde
        for row, side in ((0, -2.1), (1, 2.1)):
            for j in range(6):
                y = -11.0 + j * 4.4
                c = box(f"BOAT_{i}_crew_{row}{j}", coll,
                        (side, y, 3.1), (0.6, 0.45, 1.8), mat_crew)
                parts.append(c)

        # Lederen star fremst. S04 og S08 sikter pa ham.
        parts.append(box(f"BOAT_{i}_leader", coll, (0, 13.5, 3.2),
                         (0.65, 0.5, 1.9), mat_crew))

        for p in parts:
            p.parent = root

        # Batene seiler mot +Y gjennom hele Akt 1
        key_loc(root, travel_start, (x, BOAT_Y - i * 14.0, 0))
        key_loc(root, travel_end, (x, BOAT_Y - i * 14.0 + 120.0, 0))
        linear(root)

    return coll


# ---------------------------------------------------------------------------
# Bygg: fjellet, grotta, ilden
# ---------------------------------------------------------------------------

def build_cliff(mat_rock, mat_dark, mat_glow):
    coll = collection("LOCATION")
    rnd = random.Random(SEED)

    # Hovedmasse: veggen reiser seg fra havet og gar innover landet
    box("CLIFF_mass", coll,
        (0, CLIFF_FACE_Y + CLIFF_DEPTH / 2, CLIFF_TOP_Z / 2),
        (CLIFF_WIDTH, CLIFF_DEPTH, CLIFF_TOP_Z), mat_rock)

    # Basaltsoyler pa framsiden. Gir skalaen noe a lese mot.
    #
    # Soylene ma ga nesten helt til topps. Forste utkast varierte hoyden
    # 74-99% og resultatet lesesom et stakittgjerde foran en flat masse,
    # ikke som en vegg. Varier heller dybden — hvor langt de stikker ut.
    n = 64
    for i in range(n):
        x = -CLIFF_WIDTH / 2 + (i + 0.5) * (CLIFF_WIDTH / n)
        w = CLIFF_WIDTH / n * rnd.uniform(0.6, 0.95)
        # Hull i soylerekka der grotta er, ellers star soylene foran den
        if abs(x) < CAVE_W * 0.85:
            continue
        h = CLIFF_TOP_Z * rnd.uniform(0.94, 1.005)
        d = rnd.uniform(6.0, 26.0)
        box(f"CLIFF_col_{i:02d}", coll,
            (x, CLIFF_FACE_Y - d / 2, h / 2), (w, d, h), mat_rock,
            rot=(0, 0, math.radians(rnd.uniform(-2, 2))))

    # Grotteinngang. Mork bakvegg satt inn i fjellet, og et glodeplan i
    # selve munningen. Glodeplanet ma ligge FORAN bakveggen — ligger det
    # inni, er det fullstendig skjult og grotta lyser aldri opp.
    box("CAVE_back", coll,
        (0, CLIFF_FACE_Y + 20.0, CAVE_Z), (CAVE_W, 36.0, CAVE_H), mat_dark)
    glow = box("CAVE_glow", coll,
        (0, CLIFF_FACE_Y - 1.5, CAVE_Z), (CAVE_W * 0.82, 0.4, CAVE_H * 0.82),
        mat_glow)

    # Kanten mannen loper mot. Toppen av plata ligger pa GROUND_Z, flush
    # med fjellmassen — ikke oppa den.
    box("CLIFF_ledge", coll,
        (0, CLIFF_FACE_Y + 34.0, GROUND_Z - 0.6),
        (260.0, 70.0, 1.2), mat_rock)

    return coll, glow


def build_fire(mat_fire):
    """Ildveggen i S17/S18. Skalerer opp fra ingenting pa BAAM-framet."""
    coll = collection("FIRE")
    frames = {s["id"]: s for s in shot_frames()}
    f_baam = frames["S17"]["start"]
    f_end = frames["S18"]["end"]
    f_out = frames["S20"]["end"]

    blocks = []
    for i in range(13):
        x = -120.0 + i * 20.0
        b = box(f"FIRE_{i:02d}", coll, (x, CLIFF_FACE_Y - 3.0, CLIFF_TOP_Z + 14.0),
                (18.0, 16.0, 28.0), mat_fire)
        blocks.append(b)

    for i, b in enumerate(blocks):
        jitter = (i % 4) * 2          # ilden skal ikke sla opp som en enhet
        b.scale = (0.001, 0.001, 0.001)
        b.keyframe_insert("scale", frame=f_baam - 2 + jitter)
        b.scale = (18.0, 16.0, 34.0)
        b.keyframe_insert("scale", frame=f_baam + 6 + jitter)
        b.scale = (18.0, 16.0, 24.0)
        b.keyframe_insert("scale", frame=f_end)
        # Uten denne brenner ildveggen videre inn i hoppet og
        # drageshotene og skjuler alt bak seg.
        b.scale = (0.001, 0.001, 0.001)
        b.keyframe_insert("scale", frame=f_out + jitter)
    return coll


# ---------------------------------------------------------------------------
# Bygg: mannen, dragen, pilene
# ---------------------------------------------------------------------------

def build_man(mat):
    """Blockout-figur, 1.8 m. Gar mot kanten, sa loper, sa hopper."""
    coll = collection("CHAR_MAN")
    root = bpy.data.objects.new("MAN", None)
    coll.objects.link(root)
    root.empty_display_size = 1.0

    body = box("MAN_body", coll, (0, 0, 1.15), (0.5, 0.32, 1.3), mat)
    head = box("MAN_head", coll, (0, 0, 1.95), (0.25, 0.25, 0.3), mat)
    for p in (body, head):
        p.parent = root

    fr = {s["id"]: s for s in shot_frames()}
    z = GROUND_Z

    # Gar rolig mot kanten gjennom S13-S18
    key_loc(root, fr["S13"]["start"], (0, 74.0, z))
    key_loc(root, fr["S18"]["end"], (0, 20.0, z))
    # Loper i S19-S20
    key_loc(root, fr["S20"]["end"], (0, 7.0, z))
    # Hopper i S21
    key_loc(root, fr["S21"]["start"] + 18, (0, -6.0, z))
    key_loc(root, fr["S21"]["end"], (0, -26.0, z - 64.0))
    linear(root)
    return coll, root


def build_dragon(mat):
    """
    Blockout-drage. Vingespenn DRAGON_SPAN, ett vingeslag per WINGBEAT_SEC.

    Frekvensen er det viktigste tallet her — se docs/dragon.md. Den er satt
    bevisst lav fordi et stort dyr slar sakte, og for raskt vingeslag er den
    enkeltfeilen som odelegger skalaen mest.
    """
    coll = collection("DRAGON")
    root = bpy.data.objects.new("DRAGON", None)
    coll.objects.link(root)
    root.empty_display_size = 4.0

    body = box("DR_body", coll, (0, 0, 0), (3.4, 11.0, 2.8), mat)
    neck = box("DR_neck", coll, (0, 7.2, 1.4), (1.5, 5.0, 1.5), mat,
               rot=(math.radians(-22), 0, 0))
    head = box("DR_head", coll, (0, 10.4, 3.0), (1.5, 2.6, 1.2), mat)
    tail = box("DR_tail", coll, (0, -9.5, 0.2), (1.0, 9.0, 0.9), mat,
               rot=(math.radians(6), 0, 0))
    for p in (body, neck, head, tail):
        p.parent = root

    half = DRAGON_SPAN / 2.0
    wings = []
    for side, sx in (("L", -1.0), ("R", 1.0)):
        piv = bpy.data.objects.new(f"DR_wing_{side}_piv", None)
        coll.objects.link(piv)
        piv.location = (sx * 1.6, 1.0, 0.8)
        piv.parent = root
        piv.empty_display_size = 1.5
        memb = box(f"DR_wing_{side}", coll, (sx * half / 2, 0, 0),
                   (half, 7.0, 0.25), mat)
        memb.parent = piv
        wings.append((piv, sx))

    # Vingeslag: WINGBEAT_SEC per full syklus, hele veien gjennom S23/S24
    fr = {s["id"]: s for s in shot_frames()}
    f0, f1 = fr["S23"]["start"] - FPS, fr["S25"]["end"]
    period = int(round(WINGBEAT_SEC * FPS))
    for piv, sx in wings:
        f = f0
        while f <= f1 + period:
            for phase, ang in ((0.0, 34.0), (0.5, -26.0)):
                ff = f + int(phase * period)
                piv.rotation_euler = (0, math.radians(ang * sx * -1), 0)
                piv.keyframe_insert("rotation_euler", frame=ff)
            f += period

    path = build_dragon_path(coll, root, fr)
    return coll, root, path


# Flybanen. Punktene er kontrollpunkter pa en Bezier-kurve, ikke keyframes,
# nettopp sa du kan dra i dem. Rekkefolgen er flyretningen.
DRAGON_PATH_POINTS = [
    (0.0, -26.0, CLIFF_TOP_Z - 56.0),   # under kanten, ute av bildet
    (0.0, -40.0, CLIFF_TOP_Z - 2.0),    # bryter opp forbi kanten
    # AUTO-handtakene skyter over kontrollpunktet. Satt disse hoyere
    # klatrer buen ut av S23-kameraets ramme midt i shotet.
    (0.0, -56.0, CLIFF_TOP_Z + 18.0),   # over stupet, full vingespenn
    (-46.0, -190.0, CLIFF_TOP_Z + 26.0),  # legger seg over og svinger ut
    (-30.0, -620.0, 318.0),             # inn mot takebanken
    (24.0, -1250.0, 250.0),             # borte inne i taken
]


def build_dragon_path(coll, root, fr):
    """
    Legger dragen pa en redigerbar Bezier-kurve i stedet for keyframede
    posisjoner.

    Flytt et kontrollpunkt i viewporten og hele flyvningen folger med —
    med keyframes matte du treffe bade posisjon og tidspunkt pa nytt for
    hver justering. Follow Path styrer ogsa orienteringen, sa dragen
    peker dit den faktisk flyr uten at du roterer noe manuelt.
    """
    cu = bpy.data.curves.new("DRAGON_PATH", type="CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24

    spline = cu.splines.new("BEZIER")
    spline.bezier_points.add(len(DRAGON_PATH_POINTS) - 1)
    for bp, co in zip(spline.bezier_points, DRAGON_PATH_POINTS):
        bp.co = Vector(co)
        # AUTO gir myke tangenter som folger med nar du drar i punktet.
        # Da slipper du a stelle handtakene for hand.
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    path = bpy.data.objects.new("DRAGON_PATH", cu)
    coll.objects.link(path)
    path.show_in_front = True

    con = root.constraints.new("FOLLOW_PATH")
    con.target = path
    con.use_curve_follow = True
    con.forward_axis = "FORWARD_Y"   # dragens hode peker +Y i blockouten
    con.up_axis = "UP_Z"

    # eval_time ligger pa kurvedataen, ikke pa objektet, og er det som
    # styrer NAR dragen er hvor pa banen. Vil du endre tempoet uten a
    # rore formen pa banen, er det disse tre nokkelen du flytter.
    cu.use_path = True
    total = fr["S25"]["end"] - fr["S23"]["start"]
    cu.path_duration = total

    cu.eval_time = 0.0
    cu.keyframe_insert("eval_time", frame=fr["S23"]["start"])
    cu.eval_time = total * 0.30          # utbruddet tar det forste stykket
    cu.keyframe_insert("eval_time", frame=fr["S23"]["end"])
    cu.eval_time = total
    cu.keyframe_insert("eval_time", frame=fr["S25"]["end"])

    return path


def build_arrows(mat):
    """
    Pilsvermen som en enkelt gruppe. Filmen jukser med tiden (vi klipper vekk
    og tilbake), men i previs er det nyttig a se en sammenhengende bane — da
    ser du om retningene henger sammen fra shot til shot.
    """
    coll = collection("ARROWS")
    rnd = random.Random(SEED + 1)
    root = bpy.data.objects.new("ARROW_SWARM", None)
    coll.objects.link(root)
    root.empty_display_size = 12.0

    for i in range(90):
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.35, depth=2.6, vertices=5,
            location=(rnd.uniform(-95, 95), rnd.uniform(-45, 45),
                      rnd.uniform(-22, 22)),
            rotation=(math.radians(90), 0, 0))
        a = bpy.context.active_object
        a.name = f"ARROW_{i:03d}"
        a.data.materials.append(mat)
        for c in a.users_collection:
            c.objects.unlink(a)
        coll.objects.link(a)
        a.parent = root

    fr = {s["id"]: s for s in shot_frames()}
    key_loc(root, fr["S09"]["start"], (0, BOAT_Y + 110, 14))
    key_loc(root, fr["S10"]["end"], (0, -2320, 180))
    key_loc(root, fr["S11"]["start"], (0, -2240, 200))
    key_loc(root, fr["S11"]["end"], (0, -1240, 272))
    key_loc(root, fr["S12"]["end"], (0, -620, 320))
    key_loc(root, fr["S13"]["start"], (0, -520, 360))
    key_loc(root, fr["S16"]["start"], (0, -60, 420))
    key_loc(root, fr["S17"]["start"], (0, -10, 384))
    key_loc(root, fr["S18"]["start"], (0, 4, 356))
    key_loc(root, fr["S18"]["end"], (0, 16, 353))
    linear(root)
    return coll, root


# ---------------------------------------------------------------------------
# Bygg: take
# ---------------------------------------------------------------------------

def volume_mat(name, density, color=(0.62, 0.66, 0.70, 1.0)):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = color
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return mat


def build_fog():
    coll = collection("FOG")

    # Volumboksene ma vaere romslig storre enn noe kamera ser, ellers dukker
    # kanten av boksen opp som en rett strek tvers over framet.
    depth = abs(FOG_NEAR_Y - FOG_FAR_Y)
    mid = (FOG_NEAR_Y + FOG_FAR_Y) / 2.0
    box("FOG_bank", coll, (0, mid, 240.0), (9000.0, depth, 1400.0),
        volume_mat("FOG_volume", FOG_DENSITY))

    # Tynt lag over havet, sa batene star i noe
    box("FOG_sea", coll, (0, -2300.0, 10.0), (9000.0, 2600.0, 60.0),
        volume_mat("FOG_sea_volume", FOG_DENSITY * 0.8))

    # Global dis over hele settet. Uten denne leser ikke avstanden til
    # fjellveggen — den blir bare en flat kulisse.
    box("HAZE", coll, (0, -1200.0, 400.0), (12000.0, 8000.0, 2400.0),
        volume_mat("HAZE_volume", HAZE_DENSITY))
    return coll


# ---------------------------------------------------------------------------
# Bygg: kameraer + markorer
# ---------------------------------------------------------------------------

def build_cameras():
    coll = collection("CAMERAS")
    scene = bpy.context.scene
    shots = shot_frames()

    for s in shots:
        cam_data = bpy.data.cameras.new(f"CAM_{s['id']}")
        cam_data.lens = s["lens"]
        cam_data.clip_end = 12000.0
        cam = bpy.data.objects.new(f"CAM_{s['id']}", cam_data)
        coll.objects.link(cam)

        tgt = bpy.data.objects.new(f"TGT_{s['id']}", None)
        coll.objects.link(tgt)
        tgt.empty_display_size = 2.0

        con = cam.constraints.new("TRACK_TO")
        con.target = tgt
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"

        # Riggede shots seiler med baten. Uten dette blir de faste
        # kameraene liggende igjen bak en bat som er i fart.
        if s["parent"]:
            rig = bpy.data.objects.get(s["parent"])
            if rig is None:
                raise RuntimeError(f"{s['id']}: fant ikke parent {s['parent']}")
            cam.parent = rig
            tgt.parent = rig

        key_loc(cam, s["start"], s["cam0"])
        key_loc(cam, s["end"], s["cam1"])
        key_loc(tgt, s["start"], s["tgt0"])
        key_loc(tgt, s["end"], s["tgt1"])
        linear(cam)
        linear(tgt)

        # Marker binder kameraet til timelinen -> klippet kutter seg selv
        mk = scene.timeline_markers.new(f"{s['id']}_{s['note'][:28]}",
                                        frame=s["start"])
        mk.camera = cam

    return coll, shots


# ---------------------------------------------------------------------------
# Scene-oppsett
# ---------------------------------------------------------------------------

def setup_scene(total_frames):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    scene.frame_start = 1
    scene.frame_end = total_frames
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    ee = scene.eevee
    ee.taa_samples = 8
    ee.taa_render_samples = 24
    # Dette er Blender-ekvivalenten til UE sin Volumetric Fog Distance.
    # Standardverdien rekker ikke pa langt nok til a na fjellveggen.
    ee.use_volume_custom_range = True
    ee.volumetric_start = 0.5
    ee.volumetric_end = 4000.0
    ee.volumetric_samples = 96

    world = bpy.data.worlds.new("PREVIS_world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.30, 0.34, 0.38, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    sun_data = bpy.data.lights.new("SUN", type="SUN")
    sun_data.energy = 2.2
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new("SUN", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(66), 0, math.radians(-28))

    # Fill nedenfra. Shotene over kanten ser ut i tomt rom mot morkt hav og
    # blir ulesbare uten noe som loefter skyggesiden. Rent previs-lys —
    # ikke noe du tar med videre til ekte lyssetting.
    fill_data = bpy.data.lights.new("FILL", type="SUN")
    fill_data.energy = 0.9
    fill = bpy.data.objects.new("FILL", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-104), 0, math.radians(150))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv
    out = "helios_previs.blend"
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    use_landscape = "--landscape" in argv

    random.seed(SEED)
    clear_scene()

    m_rock = grey("M_rock", 0.17)
    m_dark = grey("M_dark", 0.03)
    m_sea = grey("M_sea", 0.16)
    m_hull = grey("M_hull", 0.22)
    m_crew = grey("M_crew", 0.40)
    m_man = grey("M_man", 0.58)
    m_drag = grey("M_dragon", 0.38)
    m_arrow = grey("M_arrow", 0.50)
    m_glow = grey("M_glow", 0.0, emission=14.0)
    m_fire = grey("M_fire", 0.0, emission=9.0)

    if use_landscape:
        # Den ekte lokasjonen i stedet for kassene. Samme koordinater, sa
        # alle 25 kameraene treffer det samme — bare med fjell foran seg.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import landscape_build
        _, cave_glow = landscape_build.build("LANDSCAPE")
    else:
        build_ocean(m_sea)
        _, cave_glow = build_cliff(m_rock, m_dark, m_glow)

    build_boats(m_hull, m_crew)

    # Grotta er mork til ropet i S14, sa tenner den.
    fr = {s["id"]: s for s in shot_frames()}
    full = tuple(cave_glow.scale)
    cave_glow.scale = (0.001, 0.001, 0.001)
    cave_glow.keyframe_insert("scale", frame=fr["S14"]["start"] - 3)
    cave_glow.scale = full
    cave_glow.keyframe_insert("scale", frame=fr["S14"]["start"] + 5)

    build_fire(m_fire)
    build_man(m_man)
    build_dragon(m_drag)
    build_arrows(m_arrow)
    build_fog()
    _, shots = build_cameras()

    total = shots[-1]["end"]
    setup_scene(total)

    kind = "ekte landskap" if use_landscape else "blockout"
    print(f"\n=== HELIOS previs bygget ({kind}) ===")
    print(f"  {len(shots)} shots, {total} frames, {total / FPS:.1f} sek @ {FPS}fps")
    for s in shots:
        print(f"  {s['id']}  {s['start']:>5}-{s['end']:<5} "
              f"{(s['end'] - s['start'] + 1) / FPS:>4.1f}s  {s['lens']:>3}mm  {s['note']}")

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print(f"\nLagret: {os.path.abspath(out)}")
    return total


if __name__ == "__main__":
    main()
