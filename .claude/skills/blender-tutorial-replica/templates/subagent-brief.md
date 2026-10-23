# Sub-agent brief: render-and-compare loop for one build stage

Use a cheaper/faster model for this loop. The main session keeps the plan; the sub-agent only iterates on one stage and reports back briefly.

```text
You are iterating on ONE build stage of a Blender scene to match a reference frame.

Stage: <e.g. "4 — mid plants (ferns, shrubs)">
Blend file: <path>   Camera: <CAM_name>   Frame: <n>
Reference image: <study/frames/t_0042.png>
Allowed changes: only objects/modifiers/materials with prefix <SCAT_ferns, SCAT_shrubs>; do not touch other stages.
Tools: Blender MCP (execute_blender_code) or `blender -b`; scripts in <skill>/scripts (scatter.py, render_presets.py, compare.py).

Loop (max <4> rounds):
1. render_presets.apply("preview"); render frame <n> from <CAM_name> at 50 % to <tmp/stage4_rN.png>
2. python3 compare.py <reference> <render> <tmp/stage4_rN_cmp.jpg> --label "stage 4 round N" --diff ; look at it
3. List concrete differences (density, scale, colour, clumping, placement, light) and fix the biggest 1–3.
Stop when it matches closely or after the round limit. Save the .blend.

Report back in at most 12 lines:
- MATCH: yes / partly / no
- Changes made (parameter: old → new)
- Remaining differences you could not fix
- Path of the last comparison image
```
