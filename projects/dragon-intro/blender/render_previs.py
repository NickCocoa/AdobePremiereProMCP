#!/usr/bin/env python3
"""
render_previs.py — rendrer previs-scenen.

To modi:

    # Ett bilde per shot (midtframet), til a se gjennom blockingen raskt
    python3 render_previs.py --blend helios_previs.blend --contact out/

    # Hele animaticen som frames, klar for Premiere
    python3 render_previs.py --blend helios_previs.blend --all out/ --pct 50

I Blender:
    blender -b helios_previs.blend --python render_previs.py -- --contact out/

Uten GPU faller EEVEE tilbake pa software-GL (llvmpipe). Det virker, men
regn ~20 sek per frame — bruk --pct lavt nar du bare skal sjekke blocking.
"""

import os
import subprocess
import sys

import bpy


def args_after_dashdash():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else argv[1:]


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def shot_markers(scene):
    """[(id, start_frame, end_frame)] lest ut av timeline-markorene."""
    mks = sorted(scene.timeline_markers, key=lambda m: m.frame)
    out = []
    for i, m in enumerate(mks):
        end = mks[i + 1].frame - 1 if i + 1 < len(mks) else scene.frame_end
        out.append((m.name, m.frame, end))
    return out


def setup(scene, pct, samples):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = int(pct)
    scene.eevee.taa_render_samples = int(samples)


def render_contact(scene, outdir, pct, samples):
    """Ett bilde per shot, tatt pa midtframet."""
    os.makedirs(outdir, exist_ok=True)
    setup(scene, pct, samples)
    shots = shot_markers(scene)
    made = []
    for name, start, end in shots:
        sid = name.split("_")[0]
        mid = (start + end) // 2
        scene.frame_set(mid)
        path = os.path.join(outdir, f"{sid}_f{mid:05d}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        made.append(path)
        print(f"  {sid}  frame {mid}  -> {os.path.basename(path)}", flush=True)
    return made


def render_all(scene, outdir, pct, samples):
    os.makedirs(outdir, exist_ok=True)
    setup(scene, pct, samples)
    scene.render.filepath = os.path.join(outdir, "f_")
    bpy.ops.render.render(animation=True)
    return [outdir]


def montage(paths, outfile, cols=5):
    """Limer kontaktarket sammen hvis ImageMagick finnes. Ellers hopper vi over."""
    try:
        subprocess.run(["montage", "-geometry", "+3+3", "-tile", f"{cols}x",
                        "-background", "#1a1a1a", *paths, outfile],
                       check=True, capture_output=True)
        return outfile
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def main():
    args = args_after_dashdash()
    blend = opt(args, "--blend")
    pct = opt(args, "--pct", "40")
    samples = opt(args, "--samples", "16")

    if blend:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    scene = bpy.context.scene

    if "--contact" in args:
        outdir = os.path.abspath(opt(args, "--contact"))
        print(f"Kontaktark -> {outdir}")
        made = render_contact(scene, outdir, pct, samples)
        sheet = montage(made, os.path.join(outdir, "_contact_sheet.png"))
        if sheet:
            print(f"Kontaktark limt sammen: {sheet}")
    elif "--all" in args:
        outdir = os.path.abspath(opt(args, "--all"))
        print(f"Full animatic -> {outdir}  ({scene.frame_end} frames)")
        render_all(scene, outdir, pct, samples)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
