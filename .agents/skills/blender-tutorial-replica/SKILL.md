---
name: blender-tutorial-replica
description: Build ultra-realistic Blender environments and shots by replicating a real Blender tutorial instead of prompting from scratch. Claude studies the tutorial (full transcript + frame-by-frame reference), writes a shot plan, security-checks the creator's free assets, builds the scene in stages with a test render compared side-by-side against the reference after every stage, writes its own scatter system and rigs instead of running third-party add-ons, delegates render/compare loops to sub-agents, and renders efficiently (preview pass, test stills, GPU + persistent data, resumable image sequence, overnight keep-awake). Use when the user gives a Blender tutorial/video link, says "make it like this tutorial/video", wants a realistic forest/landscape/environment/car shot in Blender, or wants to avoid AI-slop-looking Blender renders.
---

# blender-tutorial-replica — a tutorial, not a prompt

Workflow from Mr omi, "How to Make an Ultra-Realistic 3D Environment Using Claude (Full Workflow)", which recreated row.num77's Blender forest tutorial. Credit for any scene built this way belongs to the tutorial's creator; say so when sharing.

**Core idea:** don't ask Claude to invent a scene. Give it a good (long) tutorial and copy it one-to-one, the way people learn Blender. The tutorial supplies the art direction, technique and assets; Claude supplies **code and cameras**, which it is good at. Claude is weak at hero 3D models and character/organic animation, so use the creator's free assets and open-source community resources for those, never Claude-modelled ones.

Scripts (in `scripts/`, tested on Blender 5.0):
| Script | Does |
|---|---|
| `study_tutorial.sh` | transcript + every frame of the first N s + timestamped contact sheets + per-step reference stills |
| `scan_assets.py` | security check of an asset pack before anything is opened (scripts, disguised executables, add-ons, archive path traversal, and inside `.blend`: auto-run text blocks, scripted drivers, OSL nodes, linked libraries) |
| `scatter.py` | own geometry-nodes scatter (replaces paid scatter add-ons): instances, masks, Poisson spacing, light viewport |
| `vehicle_rig.py` | own car rig (replaces third-party rig add-ons): path follow, wheel spin from distance, steering from curvature, gravel bounce, baked keyframes |
| `compare.py` | reference frame vs test render side by side (+ difference view) |
| `render_presets.py` | `preview` / `still` / `final` presets: GPU, persistent data, adaptive sampling, light-path caps, resumable image sequence |
| `keep_awake.sh` / `keep_awake.ps1` | keep macOS / Linux / Windows awake during an overnight render |

Run Blender-side scripts through the Blender MCP (`execute_blender_code`: `import sys; sys.path.insert(0, "<skill>/scripts"); import scatter`) or `blender -b file.blend -P script.py`.

## Workflow

### 0. Plan the target (with the user)
What scene, which shots, how long, what format (16:9 / 9:16), deadline, render hardware. Then find **one long, high-quality tutorial** that builds something close (forest, interior, city street, product shot…). Prefer tutorials that share their assets for free. If the user only has an idea, help them pick a tutorial first; that choice drives the result more than any prompt.

### 1. Study the tutorial
```bash
bash scripts/study_tutorial.sh "<youtube-url or file>" study/ 30 20
```
- Read the **entire** transcript; list every technique, add-on, asset and setting the creator uses.
- If YouTube blocks the download (CAPTCHA/bot check), run it on the user's machine with `--cookies-from-browser chrome` (or have them download the file). Never try to bypass a block from a server.
- Read the contact sheets; open the dense frames of the final shots to measure **camera height, lens, speed and cut points**.
- No captions? Transcribe with the `video-cut` skill's `transcribe.py`.

### 2. Write the shot plan (`shot-plan.md`, template in `templates/shot-plan.md`)
Every shot: duration (frames), camera type and lens, height, movement and speed, what's in frame, matching reference frames, and the tutorial chapter that builds it. Plus the **build stages** (terrain → sky/light → large plants → small plants/ground cover → paths/rocks → hero assets → animation → camera) with a reference frame for each. Confirm the plan with the user before building.

### 3. Assets: download, then security-check before opening anything
```bash
python3 scripts/scan_assets.py downloads/asset_pack.zip --blender /path/to/blender --json scan.json
```
- Review every finding with the user. Never enable add-ons from packs and never run embedded text blocks; open `.blend` files with **Python auto-execution off** (Blender's default; don't enable "Auto Run Python Scripts").
- If the tutorial depends on a paid or third-party add-on (scatter, car rig, …), **write your own** with this skill's scripts rather than installing someone else's code.

### 4. Build in stages, comparing after every stage
For each build stage:
1. Implement it with code (small, named, rerunnable steps; prefixes `ENV_`, `SCAT_`, `CAM_`, `RIG_`, `MAT_`).
2. Render a **small test image** from the matching camera (`render_presets.apply("preview")`, 25–50 % resolution).
3. `python3 scripts/compare.py study/frames/<ref>.png test.png cmp.jpg --label "<stage>" --diff`, read it, list concrete differences (framing, lens, light direction/colour, density, plant scale, contrast, haze).
4. Fix, re-render, compare again. **Only move on when the stage matches.** Slow, but it's why the result looks real.

Stage notes:
- **Terrain**: use the tutorial's terrain/heightmap and ground textures when shared; otherwise displace + their texture approach.
- **Sky / lighting**: use their HDRI / sky texture and sun angle; light direction is the first thing to match.
- **Plants**: `scatter.scatter(...)` one layer per plant type (trees, ferns, shrubs, grass, branches, leaves, pebbles), each with its own density, mask, seed and scale range. 500k+ instances are fine as instances; keep `viewport_ratio` low.
- **Paths / roads**: cut into the ground (boolean or displacement mask), then mask the scatter layers off the path.
- **Hero models** (cabins, vehicles, characters): use downloaded assets. If Claude-built models look flat (plain walls, no detail), **drop them** rather than ship them.

### 5. Save tokens: delegate render-compare loops to sub-agents
The render → compare → report loop is token-heavy. Hand each stage's loop to a cheaper sub-agent (e.g. a Sonnet-class model) with the brief in `templates/subagent-brief.md`. The sub-agent renders, compares and returns **a short list of differences and the fixes it applied**. The main session keeps the plan, decisions and the user conversation.

### 6. Pivot when it isn't converging
If after several rounds a shot still doesn't look like the reference, say so and propose a different shot from the same tutorial that plays to the strengths (e.g. the car-on-gravel clip instead of the cabin scene). Better one convincing shot than three average ones.

### 7. Animation and cameras (Claude's strength)
- Break the reference clip down frame by frame (e.g. 390 frames → 4 shots): camera height, lens, speed, cut points.
- Vehicles: `vehicle_rig.bake(...)`. It keys path follow, wheel spin = distance / radius, steering = atan(wheelbase × curvature) and gravel bounce, all baked so motion blur and other machines see the same motion.
- Cameras: parent to the rig or path; match lens and type (e.g. fisheye on the car: Cycles panoramic `FISHEYE_EQUISOLID`).
- Check motion blur on a test frame: **wheels and fast parts must blur**. If they don't, the animation is probably not keyed (drivers or constraints evaluated differently); bake it.

### 8. Render efficiently
1. `render_presets.apply("preview")`: render a quick low-quality pass of the animation and **find problems** (popping, flicker, missing blur, wrong timing). Fix all of them.
2. `render_presets.apply("still")`: render 2–4 representative full-size frames and tune samples, adaptive threshold, light paths and denoising until the look stays the same at a lower time per frame (a ~45 % speed-up without visible change is realistic).
3. `render_presets.apply("final")`: GPU on, **persistent data on** (keeps a 700k-plant scene loaded on the GPU instead of rebuilding it on the CPU for every frame), image sequence with overwrite off + placeholders so it resumes after a crash.
4. Run overnight with `scripts/keep_awake.sh blender -b scene.blend -a` (or `keep_awake.ps1` on Windows) and turn off notifications so nothing wakes or sleeps the machine.
5. Encode the sequence: `ffmpeg -framerate 30 -i frames/frame_%04d.png -c:v libx264 -crf 16 -pix_fmt yuv420p out.mp4`.
Budget honestly: heavy foliage can take hours per few seconds (≈3 h for 13–30 s on a home GPU).

### 9. Sound
Renders are silent. Add sound in an editor (CapCut, DaVinci Resolve, Premiere): listen to the tutorial's final video, infer which effects it uses (birds, wind, gravel, engine) and match them with properly licensed sounds (CC0 / Pixabay / freesound with attribution). Credit them.

## Rules
- Copy one tutorial faithfully before improvising; credit the creator.
- Claude does code, cameras, rigs, scatter, render settings. Assets come from the tutorial or open-source libraries.
- Never run third-party code from asset packs or add-ons; write equivalents.
- Compare against the reference after every stage; don't stack stages on an unverified one.
- Delegate the noisy loops; keep the main context for plan and decisions.
- When the user wants their own variation after the faithful copy, combine with the `blender-ctlt` skill (Camera/Tone/Lighting/Texture brief) if it is installed.
