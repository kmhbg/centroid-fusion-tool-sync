"""Unit tests for Centroid description namnstandard + gap-fill enrich (v1)."""

from __future__ import annotations

import unittest

from lib.centroid_parser import parse_description, parse_row
from lib.tool_templates import build_tool_json, enrich_tool_json, patch_tool_json


def _tool(description: str, **kwargs):
    row = {
        "Tool": "T{:03d}".format(kwargs.get("tool_number", 2)),
        "H": "H{:03d}".format(kwargs.get("h_number", 2)),
        "D": "D{:03d}".format(kwargs.get("d_number", 4)),
        "Offset": "0",
        "Diameter": str(kwargs.get("diameter", 0)),
        "Coolant": "OFF",
        "Spindle": "CW",
        "Speed": str(kwargs.get("speed", 3500)),
        "Description": description,
    }
    return parse_row(row)


class NamingStandardParseTests(unittest.TestCase):
    def test_full_token_string(self):
        meta = parse_description("EM 6mm 4f LCF20 LB40 OAL75 CARB")
        self.assertEqual(meta["tool_type"], "flat end mill")
        self.assertEqual(meta["diameter"], 6.0)
        self.assertEqual(meta["flutes"], 4)
        self.assertTrue(meta["flutes_explicit"])
        self.assertEqual(meta["lcf"], 20.0)
        self.assertEqual(meta["lb"], 40.0)
        self.assertEqual(meta["oal"], 75.0)
        self.assertEqual(meta["bmc"], "carbide")

    def test_drill_sig(self):
        meta = parse_description("DR 5mm SIG118 LCF50 OAL80 HSS")
        self.assertEqual(meta["tool_type"], "drill")
        self.assertEqual(meta["point_angle"], 118.0)
        self.assertEqual(meta["bmc"], "hss")
        self.assertEqual(meta["lcf"], 50.0)

    def test_ball_radius(self):
        meta = parse_description("BL 6mm 2f R3 LCF12 OAL60")
        self.assertEqual(meta["tool_type"], "ball end mill")
        self.assertEqual(meta["corner_radius"], 3.0)
        self.assertTrue(meta["corner_radius_explicit"])

    def test_legacy_short_description(self):
        meta = parse_description("6mm 2f end mill")
        self.assertEqual(meta["tool_type"], "flat end mill")
        self.assertEqual(meta["diameter"], 6.0)
        self.assertEqual(meta["flutes"], 2)
        self.assertIsNone(meta["lcf"])
        self.assertIsNone(meta["bmc"])


class CreateAndEnrichTests(unittest.TestCase):
    def test_create_applies_tokens(self):
        centroid = _tool("EM 6mm 4f LCF20 LB40 OAL75 CARB")
        payload = build_tool_json(centroid)
        self.assertEqual(payload["geometry"]["LCF"], 20.0)
        self.assertEqual(payload["geometry"]["LB"], 40.0)
        self.assertEqual(payload["geometry"]["OAL"], 75.0)
        self.assertEqual(payload["geometry"]["NOF"], 4)
        self.assertEqual(payload["BMC"], "carbide")

    def test_update_token_overwrites_lengths(self):
        centroid = _tool("EM 6mm 4f LCF20 LB40 OAL75 CARB")
        existing = build_tool_json(_tool("6mm 2f end mill"))
        existing["geometry"]["LCF"] = 18.0
        existing["geometry"]["LB"] = 24.0
        existing["geometry"]["OAL"] = 48.0
        existing["BMC"] = "hss"

        patched = patch_tool_json(existing, centroid)
        self.assertEqual(patched["geometry"]["LCF"], 20.0)
        self.assertEqual(patched["geometry"]["LB"], 40.0)
        self.assertEqual(patched["geometry"]["OAL"], 75.0)
        self.assertEqual(patched["BMC"], "carbide")

    def test_update_without_tokens_keeps_nonzero_lengths(self):
        centroid = _tool("6mm 2f end mill")
        existing = build_tool_json(centroid)
        existing["geometry"]["LCF"] = 99.0
        existing["geometry"]["LB"] = 88.0
        existing["geometry"]["OAL"] = 77.0

        patched = patch_tool_json(existing, centroid)
        self.assertEqual(patched["geometry"]["LCF"], 99.0)
        self.assertEqual(patched["geometry"]["LB"], 88.0)
        self.assertEqual(patched["geometry"]["OAL"], 77.0)

    def test_gap_fill_zero_lengths(self):
        centroid = _tool("6mm 2f end mill")
        existing = build_tool_json(centroid)
        existing["geometry"]["LCF"] = 0
        existing["geometry"]["LB"] = 0
        existing["geometry"]["OAL"] = 0

        enrich_tool_json(existing, centroid)
        self.assertGreater(existing["geometry"]["LCF"], 0)
        self.assertGreater(existing["geometry"]["LB"], 0)
        self.assertGreater(existing["geometry"]["OAL"], 0)


if __name__ == "__main__":
    unittest.main()
