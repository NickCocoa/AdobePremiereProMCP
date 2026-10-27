"""Refresh the selected procedural actors: flush the PCG cache, then regenerate.

  py "C:/path/regenerate_selected.py"
  py "C:/path/regenerate_selected.py" --random-preset City.Buildings.NeoRenaissance City.Buildings.Industrial --seed 4

With --random-preset each selected actor first gets a random tag from the list through its
`ApplyPresetByName(Name)` Blueprint function (rename with --preset-function). The preset
data already on the actor is kept; only the PCG output is rebuilt.
"""
import argparse
import random
import sys

import unreal

sys.path.append(__import__("os").path.dirname(__file__))
from _ue_common import call_if_present, flush_pcg_cache, generate_pcg, log, selected_actors  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--random-preset", nargs="*", default=None, metavar="TAG")
    ap.add_argument("--preset-function", default="ApplyPresetByName")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args(argv)

    actors = selected_actors()
    if not actors:
        unreal.EditorDialog.show_message("City tools", "Select one or more buildings or blocks first.",
                                         unreal.AppMsgType.OK)
        return

    rng = random.Random(args.seed)
    flush_pcg_cache()
    regenerated = 0
    for actor in actors:
        if args.random_preset:
            call_if_present(actor, args.preset_function, rng.choice(args.random_preset))
        if generate_pcg(actor):
            regenerated += 1
    log(f"regenerated {regenerated} of {len(actors)} selected actors")


main(sys.argv[1:])
