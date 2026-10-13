#!/usr/bin/env python3
"""
landscape_build.py — bygger den faktiske HELIOS-lokasjonen.

Erstatter blockout-kassene med ekte geometri: islandske basaltsoyler i
sekskantpakking, en forvitret fjellvegg med reell grotteapning, erodert
platatopp, urfot mot havet, sjostabler og et bolgesatt hav.

Koordinatene er de samme som previs_build.py bruker, sa alle 25 kameraene
treffer det samme som for.

Kjor frittstaende:
    blender --background --python landscape_build.py -- --out helios_land.blend
    python3 landscape_build.py --out helios_land.blend

Eller bruk den fra previs:
    blender --background --python previs_build.py -- --landscape

Geometrien bygges med from_pydata i stedet for bpy.ops per objekt. Rundt
900 soyler som enkeltobjekter tar minutter; som ett mesh tar det sekunder.
"""

import math
import os
import sys

import bpy
from mathutils import Vector, noise

# ---------------------------------------------------------------------------
# CONFIG — ma holdes i takt med previs_build.py
# ---------------------------------------------------------------------------

SEED = 7

CLIFF_FACE_Y = 0.0
CLIFF_TOP_Z = 352.0
CLIFF_WIDTH = 1400.0
CLIFF_DEPTH = 500.0
GROUND_Z = CLIFF_TOP_Z

CAVE_X, CAVE_Z = 0.0, 205.0
CAVE_W, CAVE_H = 46.0, 58.0
CAVE_DEPTH = 120.0         # hvor langt inn i fjellet grotta gar

COL_RADIUS = 4.2           # soylenes omkretsradius. Ekte basalt er ~1 m,
                           # men pa en 352 m vegg leser 8 m bredde riktig
                           # og holder antallet handterbart
COL_ROWS = 5               # hvor mange soyler i dybden
COL_BASE_Z = 18.0          # soylene starter over urfoten

TALUS_H = 26.0             # urfotens hoyde
SEA_Z = 0.0

BOAT_Y = -2400.0
FOG_NEAR_Y = -700.0


# ---------------------------------------------------------------------------
# Hjelpere
# ---------------------------------------------------------------------------

def collection(name):
    old = bpy.data.collections.get(name)
    if old:
        for ob in list(old.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def mesh_object(name, verts, faces, coll, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def rock_material(name, base, rough=0.92, spec=0.25):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = spec
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return mat


def emission_material(name, color, strength):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def fbm(x, y, z, octaves=4, scale=1.0):
    return noise.fractal(Vector((x * scale, y * scale, z * scale)),
                         1.0, 2.0, octaves)


def ridged(x, y, z, octaves=5, scale=1.0):
    return noise.ridged_multi_fractal(
        Vector((x * scale, y * scale, z * scale)), 1.0, 2.0, octaves, 1.0, 2.0)


def cave_falloff(x, z):
    """
    1.0 midt i grotteapningen, 0.0 utenfor, mykt imellom.

    Styrer bade hvor soylene utelates og hvor dypt veggflaten trekkes
    innover, sa apningen blir ekte geometri og ikke en pamalt flekk.
    """
    dx = (x - CAVE_X) / (CAVE_W * 0.5)
    dz = (z - CAVE_Z) / (CAVE_H * 0.5)
    d = math.sqrt(dx * dx + dz * dz)
    if d >= 1.45:
        return 0.0
    if d <= 0.82:
        return 1.0
    t = (1.45 - d) / (1.45 - 0.82)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Basaltsoyler
# ---------------------------------------------------------------------------

def build_columns(coll, mat):
    """
    Sekskantpakkede soyler over hele veggen. Flat-top heksagoner, pakket i
    XY, ekstrudert i Z. Hoydene korrelerer via stoy, fordi ekte basalt
    brekker i klynger og ikke tilfeldig soyle for soyle.
    """
    noise.seed_set(SEED)
    r = COL_RADIUS
    dx = 1.5 * r
    dy = math.sqrt(3.0) * r

    verts, faces = [], []
    half = CLIFF_WIDTH * 0.5
    n_cols = int(CLIFF_WIDTH / dx)

    for i in range(n_cols + 1):
        cx = -half + i * dx
        for j in range(COL_ROWS):
            cy = CLIFF_FACE_Y - j * dy - (dy * 0.5 if i % 2 else 0.0)

            # Klyngevis hoydevariasjon + enkeltsoylens eget avvik
            cluster = fbm(cx, cy, 0.0, octaves=3, scale=0.004)
            jitter = noise.noise(Vector((cx * 0.35, cy * 0.35, 11.0)))
            gully = ridged(cx, cy, 0.0, octaves=3, scale=0.0021)
            top = CLIFF_TOP_Z + cluster * 34.0 + jitter * 6.0 - gully * 22.0

            # Soylene lengst inne star litt hoyere enn de ytterste
            top += j * 1.6

            # Ingen soyler foran grotta — der skal veggen vaere apen
            if cave_falloff(cx, (COL_BASE_Z + top) * 0.5) > 0.05:
                continue
            if cave_falloff(cx, CAVE_Z) > 0.05 and top > CAVE_Z - CAVE_H * 0.6:
                continue

            # Hver soyle stikker ulikt langt ut. Uten dette danner en rad
            # et plan, og veggen leser flatt nar kameraet star rett forfra.
            cy += noise.noise(Vector((cx * 0.55, cy * 0.55, 21.0))) * 3.1
            rr = r * (0.82 + 0.3 * abs(noise.noise(Vector((cx * .2, cy * .2, 3.)))))
            base = COL_BASE_Z + jitter * 3.0
            tilt = noise.noise(Vector((cx * 0.05, cy * 0.05, 7.0))) * 1.8

            k0 = len(verts)
            for k in range(6):
                a = math.radians(60 * k)
                vx = cx + rr * math.cos(a)
                vy = cy + rr * math.sin(a)
                verts.append((vx, vy, base))
            for k in range(6):
                a = math.radians(60 * k)
                vx = cx + rr * math.cos(a) + tilt
                vy = cy + rr * math.sin(a)
                verts.append((vx, vy, top))
            for k in range(6):
                kn = (k + 1) % 6
                faces.append((k0 + k, k0 + kn, k0 + 6 + kn, k0 + 6 + k))
            faces.append(tuple(k0 + 6 + k for k in range(6)))

    return mesh_object("CLIFF_columns", verts, faces, coll, mat)


# ---------------------------------------------------------------------------
# Fjellvegg med grotteapning
# ---------------------------------------------------------------------------

def build_cliff_face(coll, mat):
    """
    Veggflaten som et forskjovet rutenett i XZ. Grotta lages ved a trekke
    vertekser innover der falloffen er hoy — en ekte apning i geometrien,
    ikke en boolsk operasjon som kan feile.
    """
    nx, nz = 270, 110
    half = CLIFF_WIDTH * 0.5
    verts = []
    for iz in range(nz + 1):
        z = CLIFF_TOP_Z * iz / nz
        for ix in range(nx + 1):
            x = -half + CLIFF_WIDTH * ix / nx
            rough = ridged(x, 0.0, z, octaves=5, scale=0.0055) * 14.0
            broad = fbm(x, 0.0, z, octaves=3, scale=0.0016) * 20.0
            # Soylebandet ligger mellom y=0 og y=-COL_ROWS*dy. Flaten ma
            # holde seg bak det, ellers buler den fram foran soylene og
            # klipper dem bort i store felt.
            y = CLIFF_FACE_Y + 16.0 + rough + broad
            y = max(y, CLIFF_FACE_Y + 3.0)
            y += CAVE_DEPTH * cave_falloff(x, z)
            verts.append((x, y, z))

    faces = []
    for iz in range(nz):
        for ix in range(nx):
            a = iz * (nx + 1) + ix
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_object("CLIFF_face", verts, faces, coll, mat, smooth=True)


def build_cliff_body(coll, mat):
    """Massen bak veggflaten. Lukker fjellet sa vi ikke ser gjennom det."""
    half = CLIFF_WIDTH * 0.5
    # Ma ligge bak veggflatens dypeste punkt (grotteresessen, ~160 m).
    # Startet den pa +4 forseglet den bade grotta og hele veggen, og det
    # var kassens flate forside som rendret, ikke geometrien foran.
    y0, y1 = CLIFF_FACE_Y + 178.0, CLIFF_FACE_Y + CLIFF_DEPTH
    v = [(-half, y0, 0), (half, y0, 0), (half, y1, 0), (-half, y1, 0),
         (-half, y0, CLIFF_TOP_Z), (half, y0, CLIFF_TOP_Z),
         (half, y1, CLIFF_TOP_Z), (-half, y1, CLIFF_TOP_Z)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
         (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_object("CLIFF_body", v, f, coll, mat)


def build_cave(coll, mat_dark, mat_glow):
    """
    Grottegangen innover i fjellet, pluss glodeflaten innerst. Gangen
    smalner og boyer litt, sa vi ikke ser rett inn i en blindvegg.
    """
    segs, ring = 16, 14
    verts, faces = [], []
    for s in range(segs + 1):
        t = s / segs
        depth = CLIFF_FACE_Y + 10.0 + t * CAVE_DEPTH
        w = CAVE_W * 0.5 * (1.0 - 0.45 * t)
        h = CAVE_H * 0.5 * (1.0 - 0.40 * t)
        cz = CAVE_Z + t * 14.0                 # gangen stiger innover
        cx = CAVE_X + math.sin(t * 2.1) * 3.0  # og boyer svakt av
        for k in range(ring):
            a = 2 * math.pi * k / ring
            # Litt kantet tverrsnitt — en grotte i basalt er ikke et ror
            rr = 1.0 + 0.12 * math.cos(a * 3.0)
            verts.append((cx + w * math.cos(a) * rr,
                          depth,
                          cz + h * math.sin(a) * rr))
    for s in range(segs):
        for k in range(ring):
            kn = (k + 1) % ring
            a = s * ring + k
            b = s * ring + kn
            faces.append((a, b, b + ring, a + ring))
    tube = mesh_object("CAVE_tunnel", verts, faces, coll, mat_dark, smooth=True)

    # Glodeflaten ma ligge grunt nok til a sees fra utsiden. Lagt for
    # dypt, eller bak en skarp sving, tenner grotta aldri i bildet.
    t = 0.34
    w = CAVE_W * 0.5 * (1.0 - 0.45 * t)
    h = CAVE_H * 0.5 * (1.0 - 0.40 * t)
    cz = CAVE_Z + t * 14.0
    cx = CAVE_X + math.sin(t * 2.1) * 3.0
    gy = CLIFF_FACE_Y + 10.0 + t * CAVE_DEPTH
    gv = [(cx - w, gy, cz - h), (cx + w, gy, cz - h),
          (cx + w, gy, cz + h), (cx - w, gy, cz + h)]
    glow = mesh_object("CAVE_glow", gv, [(0, 1, 2, 3)], coll, mat_glow)
    return tube, glow


# ---------------------------------------------------------------------------
# Platatopp, urfot, sjostabler, hav
# ---------------------------------------------------------------------------

def build_plateau(coll, mat):
    """
    Toppen mannen gar og loper pa. Erodert, svakt stigende innover, med
    en frynsete kant mot stupet.
    """
    nx, ny = 120, 70
    half = CLIFF_WIDTH * 0.5
    y0, y1 = CLIFF_FACE_Y - 6.0, CLIFF_FACE_Y + 420.0
    verts = []
    for iy in range(ny + 1):
        y = y0 + (y1 - y0) * iy / ny
        for ix in range(nx + 1):
            x = -half + CLIFF_WIDTH * ix / nx
            z = GROUND_Z
            z += fbm(x, y, 50.0, octaves=5, scale=0.0032) * 15.0
            z += ridged(x, y, 90.0, octaves=5, scale=0.011) * 6.5
            z += ridged(x, y, 140.0, octaves=4, scale=0.045) * 1.6
            z += (y - CLIFF_FACE_Y) * 0.045        # stiger innover landet

            # Flatt dekke i spillflaten. Previs plasserer mannen pa
            # GROUND_Z; et bolgende plata ville begravd ham eller latt
            # ham sveve over bakken.
            # Kjernen ma vaere HELT flat, ikke bare delvis. En myk blanding
            # hele veien inn gir ~354,5 m der previs forventer 352, og da
            # havner hvert kamera pa toppen under terrengoverflaten og
            # rendrer svart.
            ax = abs(x) / 140.0
            ay = max(0.0, (y - CLIFF_FACE_Y)) / 150.0
            d = math.sqrt(ax * ax + ay * ay)
            if d <= 0.62:
                z = GROUND_Z
            elif d < 1.0:
                m = (1.0 - d) / 0.38
                m = m * m * (3.0 - 2.0 * m)
                z = GROUND_Z * m + z * (1.0 - m)

            # Kanten smuldrer bort de siste meterne mot stupet
            edge = y - CLIFF_FACE_Y
            if edge < 24.0:
                fray = noise.noise(Vector((x * 0.09, 4.0, 2.0))) * 9.0
                if edge < fray:
                    z -= (fray - edge) * 3.2
            verts.append((x, y, z))

    faces = []
    for iy in range(ny):
        for ix in range(nx):
            a = iy * (nx + 1) + ix
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_object("PLATEAU", verts, faces, coll, mat, smooth=True)


def build_talus(coll, mat):
    """Ur og rasmasse der veggen moter sjoen."""
    nx = 160
    half = CLIFF_WIDTH * 0.5
    verts, faces = [], []
    for ix in range(nx + 1):
        x = -half + CLIFF_WIDTH * ix / nx
        depth = 34.0 + noise.noise(Vector((x * 0.012, 9.0, 1.0))) * 22.0
        h = TALUS_H + noise.noise(Vector((x * 0.02, 3.0, 5.0))) * 11.0
        verts.append((x, CLIFF_FACE_Y - depth, SEA_Z - 3.0))
        verts.append((x, CLIFF_FACE_Y + 3.0, h))
    for ix in range(nx):
        a = ix * 2
        faces.append((a, a + 2, a + 3, a + 1))
    return mesh_object("TALUS", verts, faces, coll, mat, smooth=True)


def build_sea_stacks(coll, mat):
    """
    Reynisdrangar-aktige stabler ute i sjoen. De gir batshotene noe a
    passere og skalaen noe a males mot pa vei inn mot land.
    """
    stacks = [(-330, -520, 86), (-250, -610, 58), (265, -470, 104),
              (360, -700, 72), (-60, -880, 44), (430, -1180, 63)]
    verts, faces = [], []
    rings, segs = 11, 12
    for (sx, sy, sh) in stacks:
        k0 = len(verts)
        # Tverrsnittet laases EN gang per stabel. Varierte det per ring,
        # fikk stablene midje og lignet vaser i stedet for bratte skjaer.
        profile = [1.0 + 0.40 * noise.noise(Vector((sx * .03 + math.cos(a) * 3,
                                                    sy * .03 + math.sin(a) * 3,
                                                    5.0)))
                   for a in (2 * math.pi * k / segs for k in range(segs))]
        for ri in range(rings):
            t = ri / (rings - 1)
            z = SEA_Z - 6.0 + t * (sh + 6.0)
            # Avsmalningen ma vaere monoton. Varierer bredden opp og ned
            # langs hoyden far stabelen midje og ser ut som en vase.
            w = (sh * 0.30) * (1.0 - t * 0.58)
            jag = 1.0 + (0.26 * noise.noise(Vector((sx * .05, sy * .05, t * 9)))
                         if t > 0.78 else 0.0)
            # Svak helling gir dem karakter uten a bryte silhuetten
            lean_x = math.sin(sx * 0.013) * sh * 0.09 * t
            lean_y = math.cos(sy * 0.011) * sh * 0.07 * t
            for k in range(segs):
                a = 2 * math.pi * k / segs
                rr = profile[k] * jag
                verts.append((sx + lean_x + w * math.cos(a) * rr,
                              sy + lean_y + w * math.sin(a) * rr, z))
        for ri in range(rings - 1):
            for k in range(segs):
                kn = (k + 1) % segs
                a = k0 + ri * segs + k
                b = k0 + ri * segs + kn
                faces.append((a, b, b + segs, a + segs))
        faces.append(tuple(k0 + (rings - 1) * segs + k for k in range(segs)))
    return mesh_object("SEA_STACKS", verts, faces, coll, mat, smooth=True)


def build_ocean(coll, mat):
    """Havflate med bolger. Grovt rutenett — det skal leses, ikke simuleres."""
    nx, ny = 200, 200
    x0, x1 = -3000.0, 3000.0
    y0, y1 = -3400.0, 200.0
    verts = []
    for iy in range(ny + 1):
        y = y0 + (y1 - y0) * iy / ny
        for ix in range(nx + 1):
            x = x0 + (x1 - x0) * ix / nx
            z = SEA_Z
            z += math.sin(y * 0.021 + math.cos(x * 0.004) * 1.7) * 1.5
            z += math.sin(y * 0.052 + x * 0.011) * 0.6
            z += fbm(x, y, 20.0, octaves=3, scale=0.009) * 1.1
            verts.append((x, y, z))
    faces = []
    for iy in range(ny):
        for ix in range(nx):
            a = iy * (nx + 1) + ix
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_object("OCEAN", verts, faces, coll, mat, smooth=True)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def build(coll_name="LANDSCAPE"):
    """Bygger hele lokasjonen. Returnerer (collection, cave_glow_object)."""
    noise.seed_set(SEED)
    coll = collection(coll_name)

    m_basalt = rock_material("M_basalt", (0.045, 0.048, 0.055), rough=0.90)
    m_face = rock_material("M_cliff_face", (0.055, 0.056, 0.062), rough=0.94)
    m_dark = rock_material("M_cave_dark", (0.012, 0.011, 0.012), rough=0.97)
    m_scree = rock_material("M_scree", (0.050, 0.049, 0.051), rough=0.96)
    m_top = rock_material("M_plateau", (0.052, 0.052, 0.050), rough=0.96)
    m_sea = rock_material("M_sea", (0.022, 0.030, 0.036), rough=0.14, spec=0.6)
    m_glow = emission_material("M_cave_glow", (1.0, 0.33, 0.07), 11.0)

    build_cliff_body(coll, m_basalt)
    build_cliff_face(coll, m_face)
    build_columns(coll, m_basalt)
    _, glow = build_cave(coll, m_dark, m_glow)
    build_plateau(coll, m_top)
    build_talus(coll, m_scree)
    build_sea_stacks(coll, m_basalt)
    build_ocean(coll, m_sea)

    tris = sum(len(o.data.polygons) for o in coll.objects if o.type == "MESH")
    print(f"  LANDSCAPE: {len(coll.objects)} objekter, {tris} flater")
    return coll, glow


# ---------------------------------------------------------------------------
# Frittstaende
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    out = argv[argv.index("--out") + 1] if "--out" in argv else "helios_land.blend"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 2048, 858
    scene.unit_settings.system = "METRIC"

    build()

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.26, 0.30, 0.35, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    sun_data = bpy.data.lights.new("SUN", type="SUN")
    sun_data.energy = 2.4
    sun_data.angle = math.radians(7)
    sun = bpy.data.objects.new("SUN", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(64), 0, math.radians(-30))

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print(f"Lagret: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
