#!/usr/bin/env python3
"""Security-check a downloaded asset pack BEFORE opening anything in Blender.

Usage:
  python3 scan_assets.py ASSET_DIR_OR_ARCHIVE [--blender /path/to/blender] [--json report.json]

What it does (read-only, never executes asset content):
  1. Archives (.zip): lists members, flags path traversal / absolute paths / nested archives,
     extracts safely into <archive>_extracted/ (no overwrite outside that folder).
  2. Walks every file and flags executables and scripts by extension AND by magic bytes
     (PE "MZ", ELF, Mach-O, shebang), plus Blender add-ons (__init__.py with bl_info).
  3. With --blender: opens every .blend with Python auto-execution DISABLED and lists embedded
     risks: text blocks (especially ones marked to run on load), scripted driver expressions,
     OSL script nodes, linked external libraries.
Exit code 0 = nothing flagged, 1 = review the findings before opening the files.
"""
import argparse
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

RISKY_EXT = {
    ".py": "python script", ".pyc": "compiled python", ".pyw": "python script",
    ".sh": "shell script", ".bash": "shell script", ".zsh": "shell script",
    ".bat": "windows batch", ".cmd": "windows batch", ".ps1": "powershell", ".vbs": "vbscript",
    ".js": "javascript", ".jse": "javascript", ".wsf": "windows script", ".hta": "html application",
    ".exe": "executable", ".msi": "installer", ".dll": "library", ".scr": "screensaver exe",
    ".com": "dos executable", ".lnk": "windows shortcut", ".jar": "java archive",
    ".so": "shared library", ".dylib": "shared library", ".app": "mac app", ".pkg": "mac installer",
    ".dmg": "disk image", ".deb": "linux package", ".rpm": "linux package", ".osl": "OSL shader source",
    ".oso": "compiled OSL shader", ".command": "mac script",
}
ARCHIVES = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"}
MAGIC = [(b"MZ", "windows executable (PE)"), (b"\x7fELF", "linux executable (ELF)"),
         (b"\xcf\xfa\xed\xfe", "mac executable (Mach-O)"), (b"\xfe\xed\xfa\xcf", "mac executable (Mach-O)"),
         (b"\xca\xfe\xba\xbe", "mac universal binary / java class"), (b"#!", "script with shebang")]
SAFE_MAGIC_EXT = {".png", ".jpg", ".jpeg", ".exr", ".hdr", ".tif", ".tiff", ".blend", ".fbx", ".obj",
                  ".glb", ".gltf", ".abc", ".usd", ".usdc", ".usdz", ".mtl", ".txt", ".md", ".pdf"}

BLEND_PROBE = r'''
import bpy, json, sys
path = sys.argv[sys.argv.index("--") + 1]
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
props = {p.identifier for p in bpy.ops.wm.open_mainfile.get_rna_type().properties}
kw = {"use_scripts": False} if "use_scripts" in props else {"use_scripts_auto_execute": False}
bpy.ops.wm.open_mainfile(filepath=path, load_ui=False, **kw)
d = bpy.data
out = {"file": path,
       "texts": [{"name": t.name, "runs_on_load": bool(getattr(t, "use_module", False)), "lines": len(t.lines)} for t in d.texts],
       "scripted_drivers": [], "osl_script_nodes": [], "libraries": [l.filepath for l in d.libraries]}
def scan_anim(owner, label):
    ad = getattr(owner, "animation_data", None)
    if ad:
        for fc in ad.drivers:
            if fc.driver.type == "SCRIPTED":
                out["scripted_drivers"].append(f"{label}: {fc.data_path} = {fc.driver.expression}")
for coll in (d.objects, d.meshes, d.materials, d.node_groups, d.scenes, d.shape_keys, d.cameras, d.lights):
    for idb in coll:
        scan_anim(idb, idb.name)
for nt_owner in list(d.materials) + list(d.node_groups) + list(d.worlds):
    nt = getattr(nt_owner, "node_tree", None) if not isinstance(nt_owner, bpy.types.NodeTree) else nt_owner
    if nt:
        for n in nt.nodes:
            if n.bl_idname == "ShaderNodeScript":
                out["osl_script_nodes"].append(f"{nt_owner.name}: {n.name}")
print("BLENDPROBE" + json.dumps(out))
'''


def safe_extract(zpath: Path, findings):
    dest = zpath.with_name(zpath.stem + "_extracted")
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            name = m.filename
            target = (dest / name).resolve()
            if name.startswith(("/", "\\")) or ".." in Path(name).parts or not str(target).startswith(str(dest.resolve())):
                findings.append({"file": f"{zpath}!{name}", "issue": "path traversal / absolute path in archive (NOT extracted)"})
                continue
            if Path(name).suffix.lower() in ARCHIVES:
                findings.append({"file": f"{zpath}!{name}", "issue": "nested archive (scan it too)"})
            z.extract(m, dest)
    return dest


def scan_tree(root: Path, findings, blends):
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            findings.append({"file": str(p), "issue": f"symlink -> {os.readlink(p)}"})
            continue
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in RISKY_EXT:
            issue = RISKY_EXT[ext]
            if p.name == "__init__.py" and "bl_info" in p.read_text(errors="ignore"):
                issue = "Blender add-on (runs code when installed/enabled)"
            findings.append({"file": str(p), "issue": issue})
        elif ext in ARCHIVES:
            findings.append({"file": str(p), "issue": "archive inside the pack (unpack and scan separately)"})
        try:
            head = p.open("rb").read(4)
        except OSError:
            continue
        for magic, what in MAGIC:
            if head.startswith(magic) and ext not in RISKY_EXT and (ext not in SAFE_MAGIC_EXT or magic != b"#!"):
                findings.append({"file": str(p), "issue": f"{what} disguised as '{ext or 'no extension'}'"})
                break
        if ext == ".blend" or head.startswith(b"BLEND"):
            blends.append(p)


def probe_blends(blender, blends, findings, reports):
    for b in blends:
        if "python" in Path(blender).name:      # a Python with the bpy module installed
            cmd = [blender, "-I", "-c", BLEND_PROBE, "--", str(b)]
        else:
            cmd = [blender, "-b", "--factory-startup", "--disable-autoexec", "--python-expr", BLEND_PROBE, "--", str(b)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        line = next((l for l in res.stdout.splitlines() if l.startswith("BLENDPROBE")), None)
        if not line:
            findings.append({"file": str(b), "issue": "could not inspect .blend (open it only after manual review)"})
            continue
        r = json.loads(line[len("BLENDPROBE"):])
        reports.append(r)
        for t in r["texts"]:
            findings.append({"file": str(b), "issue": f"embedded text block '{t['name']}' ({t['lines']} lines)"
                             + (" MARKED TO RUN ON LOAD" if t["runs_on_load"] else "")})
        for dr in r["scripted_drivers"]:
            findings.append({"file": str(b), "issue": f"scripted driver expression: {dr}"})
        for n in r["osl_script_nodes"]:
            findings.append({"file": str(b), "issue": f"OSL script node: {n}"})
        for lib in r["libraries"]:
            findings.append({"file": str(b), "issue": f"links external library: {lib}"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--blender", help="Blender executable (or a Python with bpy), to inspect .blend contents safely")
    ap.add_argument("--json", help="write the full report here")
    args = ap.parse_args()

    findings, blends, reports = [], [], []
    root = Path(args.path)
    if root.is_file() and root.suffix.lower() == ".zip":
        root = safe_extract(root, findings)
        print(f"extracted to {root}")
    scan_tree(root, findings, blends)
    if args.blender and blends:
        probe_blends(args.blender, blends, findings, reports)
    elif blends:
        findings.append({"file": str(root), "issue": f"{len(blends)} .blend file(s) not inspected (pass --blender)"})

    files = sum(1 for p in root.rglob("*") if p.is_file())
    print(f"scanned {files} files, {len(blends)} .blend")
    for f in findings:
        print(f"  ! {f['issue']}: {f['file']}")
    if args.json:
        Path(args.json).write_text(json.dumps({"findings": findings, "blends": reports}, indent=1))
    if not findings:
        print("no findings: nothing executable or scripted detected")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
