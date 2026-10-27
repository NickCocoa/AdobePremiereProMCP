#!/usr/bin/env python3
"""Check a PCG shape-grammar string before building it in Unreal.

Parses the grammar (syntax as in the UE 5.8 docs) and simulates filling a facade of a
given width with the module sizes you pass, so you see what would be placed and how
much is left over. The fill is an approximation of PCG's solver: fixed parts first,
then repeats (`*`, `+`) share the remaining width one unit at a time, left to right.
The editor and the Print Grammar node are the final word.

  python3 grammar_check.py "A,[B,B,C,B,B,A]*,D" --modules A=50 B=150 C=200 D=60 --width 2400
  python3 grammar_check.py "{[A,P]:2,[BL,P]:1}*,[G,P],{[A,P]:2,[BL,P]:1}*" \
      --modules A=200 P=20 BL=200 G=300 --width 3000 --seed 7 --print-tree
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------- syntax tree


@dataclass
class Sym:
    name: str


@dataclass
class Seq:
    items: list


@dataclass
class Repeat:
    node: object
    kind: str          # '*', '+', or 'n'
    count: int = 0     # for kind 'n'


@dataclass
class Priority:        # <A, B, C>: first option that fits
    options: list


@dataclass
class Random:          # {A:2, B:1}: weighted choice
    options: list
    weights: list = field(default_factory=list)


class GrammarError(ValueError):
    pass


TOKEN = re.compile(r"\s*(?:(?P<sym>[A-Za-z_][A-Za-z0-9_]*)|(?P<num>\d+(?:\.\d+)?)|(?P<op>[\[\]<>{},:*+]))")


def tokenize(text: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise GrammarError(f"unexpected character {text[pos]!r} at {pos}")
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
    return out


class Parser:
    def __init__(self, text: str):
        self.toks = tokenize(text)
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self, value=None):
        tok = self.peek()
        if tok[0] is None:
            raise GrammarError("unexpected end of grammar")
        if value is not None and tok[1] != value:
            raise GrammarError(f"expected {value!r}, got {tok[1]!r}")
        self.i += 1
        return tok

    def parse(self):
        seq = self.sequence(end=None)
        if self.peek()[0] is not None:
            raise GrammarError(f"unexpected {self.peek()[1]!r}")
        return seq

    def sequence(self, end):
        items = [self.item()]
        while self.peek()[1] == ",":
            self.take(",")
            items.append(self.item())
        if end is not None:
            self.take(end)
        return Seq(items)

    def item(self):
        kind, val = self.peek()
        if kind == "sym":
            self.take()
            node = Sym(val)
        elif val == "[":
            self.take("[")
            node = self.sequence("]")
        elif val == "<":
            self.take("<")
            node = Priority(self.sequence(">").items)
        elif val == "{":
            self.take("{")
            node = self.weighted()
        else:
            raise GrammarError(f"expected a module, '[', '<' or '{{', got {val!r}")
        kind, val = self.peek()
        if val in ("*", "+"):
            self.take()
            return Repeat(node, val)
        if kind == "num":
            self.take()
            if "." in val or int(val) < 1:
                raise GrammarError(f"repeat count must be a whole number >= 1, got {val}")
            return Repeat(node, "n", int(val))
        return node

    def weighted(self):
        options, weights = [], []
        while True:
            options.append(self.item())
            w = 1.0
            if self.peek()[1] == ":":
                self.take(":")
                kind, val = self.take()
                if kind != "num":
                    raise GrammarError(f"weight must be a number, got {val!r}")
                w = float(val)
            weights.append(w)
            if self.peek()[1] == ",":
                self.take(",")
                continue
            self.take("}")
            return Random(options, weights)


def parse(text: str) -> Seq:
    return Parser(text).parse()


# ---------------------------------------------------------------- simulation


def symbols(node) -> set[str]:
    if isinstance(node, Sym):
        return {node.name}
    if isinstance(node, Seq):
        return set().union(*(symbols(n) for n in node.items))
    if isinstance(node, Repeat):
        return symbols(node.node)
    return set().union(*(symbols(n) for n in node.options))


def min_len(node, sizes) -> float:
    if isinstance(node, Sym):
        return sizes[node.name]
    if isinstance(node, Seq):
        return sum(min_len(n, sizes) for n in node.items)
    if isinstance(node, Repeat):
        unit = min_len(node.node, sizes)
        return {"*": 0.0, "+": unit, "n": unit * node.count}[node.kind]
    return min(min_len(n, sizes) for n in node.options)


def expand(node, budget, sizes, rng) -> list[str]:
    """Place `node` within `budget`; returns the module names in order."""
    if isinstance(node, Sym):
        return [node.name]
    if isinstance(node, Priority):
        for opt in node.options:
            if min_len(opt, sizes) <= budget + 1e-6:
                return expand(opt, budget, sizes, rng)
        return expand(node.options[-1], budget, sizes, rng)
    if isinstance(node, Random):
        fitting = [(o, w) for o, w in zip(node.options, node.weights) if min_len(o, sizes) <= budget + 1e-6]
        pool = fitting or list(zip(node.options, node.weights))
        opt = rng.choices([o for o, _ in pool], weights=[w for _, w in pool])[0]
        return expand(opt, budget, sizes, rng)
    if isinstance(node, Repeat) and node.kind == "n":
        out = []
        for _ in range(node.count):
            out += expand(node.node, min_len(node.node, sizes), sizes, rng)
        return out
    if isinstance(node, Repeat):
        return expand(Seq([node]), budget, sizes, rng)

    # Seq: fixed items get their minimum; repeats share what is left, one unit at a time.
    items = node.items
    placed: list[list[str]] = [[] for _ in items]
    used = 0.0
    for i, it in enumerate(items):
        if isinstance(it, Repeat) and it.kind in "*+":
            if it.kind == "+":
                unit = expand(it.node, budget - used, sizes, rng)
                placed[i] += unit
                used += sum(sizes[s] for s in unit)
            continue
        rest = sum(min_len(x, sizes) for x in items[i + 1:])
        unit = expand(it, max(budget - used - rest, min_len(it, sizes)), sizes, rng)
        placed[i] = unit
        used += sum(sizes[s] for s in unit)
    repeats = [i for i, it in enumerate(items) if isinstance(it, Repeat) and it.kind in "*+"]
    full = set()
    while len(full) < len(repeats):
        for i in repeats:
            if i in full:
                continue
            trial = expand(items[i].node, budget - used, sizes, rng)
            width = sum(sizes[s] for s in trial)
            if width <= 0 or used + width > budget + 1e-6:
                full.add(i)
                continue
            placed[i] += trial
            used += width
    return [s for part in placed for s in part]


def simulate(grammar: str, sizes: dict[str, float], width: float, seed: int = 0) -> dict:
    tree = parse(grammar)
    missing = sorted(symbols(tree) - sizes.keys())
    if missing:
        raise GrammarError(f"no size given for module(s): {', '.join(missing)}")
    need = min_len(tree, sizes)
    placed = expand(tree, width, sizes, random.Random(seed))
    used = sum(sizes[s] for s in placed)
    return {
        "grammar": grammar,
        "width": width,
        "minimum_width": need,
        "fits": need <= width + 1e-6,
        "placed": placed,
        "used": used,
        "remainder": round(width - used, 3),
        "counts": {s: placed.count(s) for s in sorted(set(placed))},
    }


def tree_lines(node, depth=0) -> list[str]:
    pad = "  " * depth
    if isinstance(node, Sym):
        return [f"{pad}module {node.name}"]
    if isinstance(node, Seq):
        out = [f"{pad}sequence"]
        for n in node.items:
            out += tree_lines(n, depth + 1)
        return out
    if isinstance(node, Repeat):
        label = {"*": "repeat as many as fit", "+": "repeat at least once", "n": f"repeat {node.count} times"}[node.kind]
        return [f"{pad}{label}"] + tree_lines(node.node, depth + 1)
    if isinstance(node, Priority):
        out = [f"{pad}priority (first that fits)"]
        for n in node.options:
            out += tree_lines(n, depth + 1)
        return out
    out = [f"{pad}weighted random"]
    total = sum(node.weights)
    for n, w in zip(node.options, node.weights):
        out.append(f"{pad}  weight {w:g} ({w / total:.0%})")
        out += tree_lines(n, depth + 2)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("grammar")
    ap.add_argument("--modules", nargs="+", default=[], metavar="SYM=SIZE", help="module sizes in cm")
    ap.add_argument("--width", type=float, help="facade/segment length in cm")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--print-tree", action="store_true", help="show how the grammar is read")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        tree = parse(args.grammar)
        if args.print_tree:
            print("\n".join(tree_lines(tree)))
        if args.width is None:
            return 0
        sizes = {}
        for m in args.modules:
            name, _, size = m.partition("=")
            sizes[name] = float(size)
        res = simulate(args.grammar, sizes, args.width, args.seed)
    except (GrammarError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"width {res['width']:g} cm, minimum needed {res['minimum_width']:g} cm")
        if not res["fits"]:
            print("DOES NOT FIT: the fixed parts are wider than the segment")
        print("placed: " + " ".join(res["placed"]))
        print("counts: " + ", ".join(f"{k}×{v}" for k, v in res["counts"].items()))
        print(f"used {res['used']:g} cm, left over {res['remainder']:g} cm")
        if res["remainder"] > 0:
            print("tip: a narrow filler or trim module in the grammar absorbs the remainder")
    return 0 if res["fits"] else 1


if __name__ == "__main__":
    sys.exit(main())
