"""Tests for the offline scripts: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import grammar_check as g  # noqa: E402
import osm_to_footprints as osm  # noqa: E402


class GrammarParse(unittest.TestCase):
    def test_docs_examples_parse(self):
        for s in ["A", "A, B", "A*", "A+", "[A, B]", "[A, B]*", "[A, B]+", "[A, B]2", "<A, B, C>",
                  "{[A,P]:2,[BL,P]:1,[BS,P]:1}*,[G,P], {[A,P]:2,[BL,P]:1,[BS,P]:1}*"]:
            g.parse(s)

    def test_errors(self):
        for bad in ["A,[B", "A,,B", "{A:x}", "[A]0", "A#"]:
            with self.assertRaises(g.GrammarError, msg=bad):
                g.parse(bad)


class GrammarFill(unittest.TestCase):
    SIZES = {"A": 50, "B": 150, "C": 200, "D": 60}

    def test_facade_repeat(self):
        r = g.simulate("A,[B,B,C,B,B,A]*,D", self.SIZES, 2400)
        self.assertEqual(r["placed"][0], "A")
        self.assertEqual(r["placed"][-1], "D")
        self.assertEqual(r["counts"]["C"], 2)          # 110 fixed + 2 x 850 = 1810 <= 2400 < 2660
        self.assertEqual(r["remainder"], 590)
        self.assertTrue(r["fits"])

    def test_exact_count_and_plus(self):
        r = g.simulate("[A,B]2,C+", self.SIZES, 600)
        self.assertEqual(r["placed"], ["A", "B", "A", "B", "C"])

    def test_priority_picks_first_that_fits(self):
        sizes = {"W2": 300, "W1": 150, "P": 20}
        self.assertEqual(g.simulate("P,<W2,W1>,P", sizes, 400)["placed"], ["P", "W2", "P"])
        self.assertEqual(g.simulate("P,<W2,W1>,P", sizes, 250)["placed"], ["P", "W1", "P"])

    def test_two_fills_share_space(self):
        sizes = {"A": 100, "G": 300}
        r = g.simulate("A*,G,A*", sizes, 1300)
        i = r["placed"].index("G")
        self.assertEqual(i, 5)                          # gate lands in the middle
        self.assertEqual(r["remainder"], 0)

    def test_weighted_random_is_seeded(self):
        sizes = {"A": 100, "B": 100}
        a = g.simulate("{A:3,B:1}*", sizes, 2000, seed=3)["placed"]
        b = g.simulate("{A:3,B:1}*", sizes, 2000, seed=3)["placed"]
        self.assertEqual(a, b)
        self.assertEqual(len(a), 20)

    def test_too_narrow(self):
        r = g.simulate("A,B,C,D", self.SIZES, 100)
        self.assertFalse(r["fits"])

    def test_missing_size(self):
        with self.assertRaises(g.GrammarError):
            g.simulate("A,X", self.SIZES, 100)

    def test_cli_exit_codes(self):
        script = os.path.join(HERE, "..", "scripts", "grammar_check.py")
        ok = subprocess.run([sys.executable, "-I", script, "A*", "--modules", "A=10", "--width", "100"])
        bad = subprocess.run([sys.executable, "-I", script, "A,["], capture_output=True)
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(bad.returncode, 2)


LAT0, LON0, D = 53.4048, -2.9916, 1e-4


def way(i, tags, coords):
    return {"type": "way", "id": i, "tags": tags, "geometry": [{"lat": a, "lon": b} for a, b in coords]}


SQUARE = [(LAT0, LON0), (LAT0, LON0 + D), (LAT0 + D, LON0 + D), (LAT0 + D, LON0), (LAT0, LON0)]


class Osm(unittest.TestCase):
    def test_square_building(self):
        out = osm.convert({"elements": [way(1, {"building": "retail", "building:levels": "4"}, SQUARE)]},
                          origin=(LAT0, LON0))
        b = out["buildings"][0]
        self.assertEqual(b["style"], "commercial")
        self.assertEqual(b["levels"], 4)
        self.assertEqual(b["height_cm"], 1280)
        self.assertEqual(len(b["points"]), 4)            # closing point dropped
        self.assertAlmostEqual(b["area_m2"], 73.9, delta=0.2)
        self.assertIn([0.0, 0.0, 0.0], b["points"])     # the origin corner, wherever the loop starts

    def test_north_is_negative_y_and_east_positive_x(self):
        out = osm.convert({"elements": [way(1, {"building": "yes"}, SQUARE)]}, origin=(LAT0, LON0))
        xs = [p[0] for p in out["buildings"][0]["points"]]
        ys = [p[1] for p in out["buildings"][0]["points"]]
        self.assertGreater(max(xs), 600)                 # east of origin
        self.assertLess(min(ys), -1100)                  # north of origin

    def test_winding_is_consistent(self):
        a = osm.convert({"elements": [way(1, {"building": "yes"}, SQUARE)]}, origin=(LAT0, LON0))
        b = osm.convert({"elements": [way(1, {"building": "yes"}, list(reversed(SQUARE)))]}, origin=(LAT0, LON0))
        area = lambda bld: osm.signed_area([tuple(p[:2]) for p in bld["points"]])  # noqa: E731
        self.assertGreater(area(a["buildings"][0]), 0)
        self.assertGreater(area(b["buildings"][0]), 0)

    def test_height_units_and_tiny_and_roads(self):
        tiny = [(LAT0, LON0), (LAT0, LON0 + 1e-5), (LAT0 + 1e-5, LON0), (LAT0, LON0)]
        out = osm.convert({"elements": [
            way(1, {"building": "apartments", "height": "40ft"}, SQUARE),
            way(2, {"building": "shed"}, tiny),
            way(3, {"highway": "primary", "lanes": "2"}, [(LAT0 - 2e-4, LON0), (LAT0 - 2e-4, LON0 + 5e-4)]),
            way(4, {"amenity": "bench"}, [(LAT0, LON0)]),
        ]}, origin=(LAT0, LON0))
        self.assertEqual(out["buildings"][0]["height_cm"], 1219)
        self.assertEqual(out["buildings"][0]["levels"], 4)
        self.assertEqual(out["skipped"], 1)
        self.assertEqual(len(out["roads"]), 1)
        self.assertGreater(out["roads"][0]["points"][0][1], 0)   # south of origin

    def test_geojson(self):
        gj = {"type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {"building": "industrial"},
            "geometry": {"type": "Polygon", "coordinates": [[[b, a] for a, b in SQUARE]]}}]}
        out = osm.convert(gj, origin=(LAT0, LON0))
        self.assertEqual(out["buildings"][0]["style"], "industrial")
        self.assertFalse(any(str(v) == "-0.0" for p in out["buildings"][0]["points"] for v in p))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, "in.json"), os.path.join(d, "out.json")
            with open(src, "w") as fh:
                json.dump({"elements": [way(1, {"building": "yes"}, SQUARE)]}, fh)
            script = os.path.join(HERE, "..", "scripts", "osm_to_footprints.py")
            subprocess.run([sys.executable, "-I", script, src, "-o", dst], check=True, capture_output=True)
            with open(dst) as fh:
                self.assertEqual(len(json.load(fh)["buildings"]), 1)


if __name__ == "__main__":
    unittest.main()
