#!/usr/bin/env python3
"""Turn OpenStreetMap data into building footprints and roads in Unreal units.

Input: Overpass JSON (`out geom;`) or GeoJSON. Output: JSON with closed footprint
loops in centimetres around a local origin, ready for `unreal/spawn_footprints.py`.

Unreal axes: X = east, Y = south (Unreal is left-handed with Y to the right of X when
seen from above, so north is -Y), Z = up. Coordinates use a local equirectangular
projection around the data's centre, which is accurate to well under a centimetre per
metre over a few kilometres; tile larger areas.

  python3 osm_to_footprints.py city.json -o footprints.json
  python3 osm_to_footprints.py city.geojson -o footprints.json --origin 53.4048,-2.9916
"""
from __future__ import annotations

import argparse
import json
import math
import sys

EARTH_R = 6378137.0
LEVEL_HEIGHT_M = 3.2

# OSM building=* value -> style key used to pick a preset in Unreal.
STYLE_BY_TYPE = {
    "commercial": "commercial", "retail": "commercial", "office": "commercial", "supermarket": "commercial",
    "industrial": "industrial", "warehouse": "industrial", "factory": "industrial", "garage": "industrial",
    "residential": "residential", "apartments": "residential", "house": "residential", "terrace": "residential",
    "detached": "residential", "semidetached_house": "residential", "dormitory": "residential",
}
ROAD_KEYS = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified",
             "service", "living_street", "pedestrian", "motorway_link", "trunk_link", "primary_link"}


def parse_number(value) -> float | None:
    if value is None:
        return None
    s = str(value).strip().lower().replace(",", ".")
    num = ""
    for ch in s:
        if ch.isdigit() or ch in ".-":
            num += ch
        elif num:
            break
    try:
        n = float(num)
    except ValueError:
        return None
    if s.endswith("ft") or "'" in s:
        n *= 0.3048
    return n


def read_features(data: dict) -> list[dict]:
    """Normalise Overpass JSON or GeoJSON to [{'tags', 'kind', 'coords': [(lat, lon)]}]."""
    feats = []
    if data.get("type") == "FeatureCollection":
        for f in data.get("features", []):
            geom = f.get("geometry") or {}
            tags = f.get("properties") or {}
            gtype = geom.get("type")
            if gtype == "Polygon":
                rings = [geom["coordinates"][0]]
            elif gtype == "MultiPolygon":
                rings = [poly[0] for poly in geom["coordinates"]]
            elif gtype == "LineString":
                rings = [geom["coordinates"]]
            else:
                continue
            for ring in rings:
                feats.append({"tags": tags, "coords": [(p[1], p[0]) for p in ring]})
    elif "elements" in data:
        for el in data["elements"]:
            if el.get("type") == "way" and el.get("geometry"):
                feats.append({"tags": el.get("tags", {}), "id": el.get("id"),
                              "coords": [(g["lat"], g["lon"]) for g in el["geometry"]]})
            elif el.get("type") == "relation" and el.get("members"):
                for m in el["members"]:
                    if m.get("role") == "outer" and m.get("geometry"):
                        feats.append({"tags": el.get("tags", {}), "id": el.get("id"),
                                      "coords": [(g["lat"], g["lon"]) for g in m["geometry"]]})
    else:
        raise ValueError("input is neither GeoJSON nor Overpass JSON")
    return feats


def project(lat, lon, lat0, lon0) -> tuple[float, float]:
    """Return Unreal (X, Y) in centimetres."""
    x = math.radians(lon - lon0) * EARTH_R * math.cos(math.radians(lat0))
    north = math.radians(lat - lat0) * EARTH_R
    return round(x * 100, 1) + 0.0, round(-north * 100, 1) + 0.0


def signed_area(pts) -> float:
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))


def clean_loop(pts, min_dist_cm=5.0):
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-6:
        pts = pts[:-1]
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) >= min_dist_cm:
            out.append(p)
    if len(out) > 2 and math.dist(out[0], out[-1]) < min_dist_cm:
        out.pop()
    return out


def convert(data: dict, origin: tuple[float, float] | None = None, min_area_m2: float = 8.0) -> dict:
    feats = read_features(data)
    pts = [c for f in feats for c in f["coords"]]
    if not pts:
        raise ValueError("no geometry found")
    if origin is None:
        origin = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    lat0, lon0 = origin

    buildings, roads, skipped = [], [], 0
    for f in feats:
        tags = f["tags"]
        local = [project(lat, lon, lat0, lon0) for lat, lon in f["coords"]]
        if "building" in tags or "building:part" in tags:
            loop = clean_loop(local)
            if len(loop) < 3:
                skipped += 1
                continue
            area = signed_area(loop)
            if abs(area) / 1e4 < min_area_m2:
                skipped += 1
                continue
            # Clockwise as seen from above in Unreal (X east, Y south) has positive signed area here.
            if area < 0:
                loop.reverse()
            btype = str(tags.get("building", "yes")).lower()
            levels = parse_number(tags.get("building:levels"))
            height = parse_number(tags.get("height"))
            if height is None and levels is not None:
                height = levels * LEVEL_HEIGHT_M
            if levels is None and height is not None:
                levels = max(1, round(height / LEVEL_HEIGHT_M))
            buildings.append({
                "id": f.get("id"),
                "type": btype,
                "style": STYLE_BY_TYPE.get(btype, "generic"),
                "levels": int(levels) if levels else None,
                "height_cm": round(height * 100) if height else None,
                "area_m2": round(abs(area) / 1e4, 1),
                "name": tags.get("name"),
                "points": [[x, y, 0.0] for x, y in loop],
            })
        elif tags.get("highway") in ROAD_KEYS:
            line = clean_loop(local) if len(local) > 2 and local[0] == local[-1] else local
            if len(line) < 2:
                continue
            lanes = parse_number(tags.get("lanes"))
            roads.append({
                "id": f.get("id"),
                "highway": tags["highway"],
                "name": tags.get("name"),
                "lanes": int(lanes) if lanes else None,
                "oneway": tags.get("oneway") == "yes",
                "points": [[x, y, 0.0] for x, y in line],
            })

    return {
        "origin": {"lat": lat0, "lon": lon0},
        "units": "cm",
        "axes": "X east, Y south, Z up",
        "attribution": "© OpenStreetMap contributors (ODbL)",
        "buildings": buildings,
        "roads": roads,
        "skipped": skipped,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="-")
    ap.add_argument("--origin", help="lat,lon to use as (0,0); default is the data's centre")
    ap.add_argument("--min-area", type=float, default=8.0, help="drop footprints smaller than this (m²)")
    args = ap.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        data = json.load(fh)
    origin = tuple(float(v) for v in args.origin.split(",")) if args.origin else None
    try:
        out = convert(data, origin, args.min_area)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text = json.dumps(out, indent=1)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"{len(out['buildings'])} buildings, {len(out['roads'])} roads, {out['skipped']} skipped -> {args.output}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
