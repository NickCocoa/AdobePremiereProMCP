"""Render presets for the preview → test-stills → final workflow. Run inside Blender.

    import render_presets
    render_presets.apply("preview")      # fast, low-res animation check: find problems early
    render_presets.apply("still")        # full-res single frames: tune quality vs time
    render_presets.apply("final", out_dir="//frames/")   # overnight image-sequence render

Key speed settings (the ones that mattered in practice):
  - GPU compute enabled and the GPU devices ticked (OptiX > CUDA > HIP > Metal > oneAPI)
  - render.use_persistent_data = True: keeps the scene (e.g. 700k scattered plants) loaded on the
    GPU between frames instead of rebuilding it on the CPU every frame. Biggest win for animations.
  - adaptive sampling + denoising instead of brute-force samples
  - sensible light-path caps (heavy foliage needs few bounces)
  - image sequence output with overwrite off + placeholders: a crash or reboot resumes where it stopped
"""
import bpy

PRESETS = {
    "preview": dict(pct=50, samples=32, threshold=0.1, max_bounces=4, motion_blur=False, fmt="PNG"),
    "still": dict(pct=100, samples=512, threshold=0.02, max_bounces=8, motion_blur=True, fmt="PNG"),
    "final": dict(pct=100, samples=512, threshold=0.02, max_bounces=8, motion_blur=True, fmt="PNG"),
}


def enable_gpu():
    """Turn on the best available GPU backend. Returns the backend name or 'CPU'."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU"
    available = [e.identifier for e in prefs.bl_rna.properties["compute_device_type"].enum_items]
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        if backend not in available:
            continue
        try:
            prefs.compute_device_type = backend
            prefs.refresh_devices() if hasattr(prefs, "refresh_devices") else prefs.get_devices()
        except Exception:
            continue
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend          # GPU only; mixing in the CPU is often slower
            bpy.context.scene.cycles.device = "GPU"
            return backend
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def apply(name, out_dir="//frames/", file_prefix="frame_"):
    p = PRESETS[name]
    s = bpy.context.scene
    r, c = s.render, s.cycles
    s.render.engine = "CYCLES"
    backend = enable_gpu()

    r.resolution_percentage = p["pct"]
    c.samples = p["samples"]
    c.use_adaptive_sampling = True
    c.adaptive_threshold = p["threshold"]
    c.use_denoising = True
    c.max_bounces = p["max_bounces"]
    c.diffuse_bounces = min(4, p["max_bounces"])
    c.glossy_bounces = min(4, p["max_bounces"])
    c.transmission_bounces = p["max_bounces"]
    c.volume_bounces = 0 if name == "preview" else 1
    c.transparent_max_bounces = 16        # leaf alpha cards need enough transparent bounces
    c.sample_clamp_indirect = 10.0
    c.caustics_reflective = False
    c.caustics_refractive = False
    r.use_persistent_data = True
    r.use_motion_blur = p["motion_blur"]

    r.image_settings.file_format = p["fmt"]
    if p["fmt"] == "PNG":
        r.image_settings.color_depth = "16" if name == "final" else "8"
    r.filepath = out_dir.rstrip("/") + "/" + file_prefix
    r.use_overwrite = name != "final"     # final: skip frames that already exist (resume)
    r.use_placeholder = name == "final"   # final: claim frames so several machines can share the job
    return {"preset": name, "device": backend, "samples": c.samples, "resolution_pct": r.resolution_percentage,
            "persistent_data": r.use_persistent_data, "output": r.filepath}
