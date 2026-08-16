"""Build Fusion tool JSON payloads from Centroid tool data."""

from __future__ import annotations

import copy
import math
import uuid
from typing import Any, Dict, Optional

from .centroid_parser import CentroidTool


def _new_guid() -> str:
    return str(uuid.uuid4())


def _coolant(centroid: CentroidTool) -> str:
    if centroid.coolant in ("OFF", "", "NONE"):
        return "disabled"
    return "flood"


def _is_empty_number(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return True


def _base_preset(centroid: CentroidTool, is_drill: bool = False) -> Dict[str, Any]:
    rpm = float(centroid.speed or 0.0)
    feed = max(rpm * 0.05 * max(centroid.flutes, 1), 50.0) if rpm else 200.0
    plunge = max(feed * 0.3, 50.0)
    vc = (math.pi * centroid.diameter * rpm) / 1000.0 if rpm else 0.0

    if is_drill:
        return {
            "expressions": {
                "tool_feedPlunge": "{:.3f} mmpm".format(plunge),
                "tool_spindleSpeed": "{:.0f} rpm".format(rpm),
            },
            "guid": _new_guid(),
            "material": {"category": "all", "query": "", "use-hardness": False},
            "n": rpm,
            "name": "Default preset",
            "tool-coolant": _coolant(centroid),
            "use-feed-per-revolution": False,
            "v_c": vc,
            "v_f_plunge": plunge,
            "v_f_retract": 1000.0,
        }

    fz = 0.05
    return {
        "expressions": {
            "tool_feedCutting": "{:.3f} mmpm".format(feed),
            "tool_feedPlunge": "{:.3f} mmpm".format(plunge),
            "tool_spindleSpeed": "{:.0f} rpm".format(rpm),
        },
        "f_n": fz,
        "f_z": fz,
        "guid": _new_guid(),
        "material": {"category": "all", "query": "", "use-hardness": False},
        "n": rpm,
        "n_ramp": rpm,
        "name": "Default preset",
        "ramp-angle": 2,
        "tool-coolant": _coolant(centroid),
        "use-stepdown": False,
        "use-stepover": False,
        "v_c": vc,
        "v_f": feed,
        "v_f_leadIn": feed,
        "v_f_leadOut": feed,
        "v_f_plunge": plunge,
        "v_f_ramp": feed / 3.0 if feed else 100.0,
        "v_f_transition": feed,
    }


def _apply_geometry_tokens(geometry: Dict[str, Any], centroid: CentroidTool) -> None:
    """Overwrite geometry keys when description tokens are present."""
    if centroid.lcf is not None:
        geometry["LCF"] = float(centroid.lcf)
    if centroid.lb is not None:
        geometry["LB"] = float(centroid.lb)
        geometry["assemblyGaugeLength"] = float(centroid.lb)
    if centroid.oal is not None:
        geometry["OAL"] = float(centroid.oal)
    if centroid.sfdm is not None:
        geometry["SFDM"] = float(centroid.sfdm)
    if centroid.point_angle is not None:
        geometry["SIG"] = float(centroid.point_angle)
    if centroid.taper_angle_explicit:
        geometry["TA"] = float(centroid.taper_angle)
    if centroid.corner_radius_explicit:
        geometry["RE"] = float(centroid.corner_radius)
    if centroid.flutes_explicit:
        geometry["NOF"] = int(centroid.flutes)


def _geometry_for(centroid: CentroidTool) -> Dict[str, Any]:
    dc = float(centroid.diameter)
    nof = int(centroid.flutes or 2)
    tool_type = centroid.tool_type

    if tool_type == "probe":
        geometry = {
            "CSP": False,
            "DC": dc,
            "HAND": True,
            "LB": dc * 4,
            "LCF": dc,
            "NOF": 1,
            "OAL": dc * 8,
            "SFDM": dc,
            "assemblyGaugeLength": dc * 4,
            "shoulder-diameter": dc,
            "shoulder-length": dc * 3,
        }
    elif tool_type == "drill":
        geometry = {
            "CSP": False,
            "DC": dc,
            "HAND": True,
            "LB": dc * 12,
            "LCF": dc * 10,
            "NOF": 2,
            "OAL": dc * 20,
            "SFDM": dc,
            "SIG": 118,
            "assemblyGaugeLength": dc * 12,
            "shoulder-length": dc * 12,
        }
    elif tool_type == "chamfer mill":
        geometry = {
            "CSP": False,
            "DC": dc,
            "HAND": True,
            "LB": dc * 5,
            "LCF": max(dc * 0.5, 1.0),
            "NOF": nof,
            "OAL": dc * 10,
            "SFDM": dc,
            "TA": float(centroid.taper_angle or 45.0),
            "assemblyGaugeLength": dc * 5,
            "shoulder-diameter": dc,
            "shoulder-length": dc * 4,
            "tip-diameter": 0,
        }
    elif tool_type == "ball end mill":
        geometry = {
            "CSP": False,
            "DC": dc,
            "HAND": True,
            "LB": dc * 6,
            "LCF": dc * 2,
            "NOF": nof,
            "OAL": dc * 10,
            "SFDM": max(dc, 6.0),
            "assemblyGaugeLength": dc * 6,
            "shoulder-diameter": dc,
            "shoulder-length": dc * 3,
            "RE": float(centroid.corner_radius or (dc / 2.0)),
        }
    elif tool_type == "face mill":
        geometry = {
            "CSP": False,
            "DC": dc,
            "DCX": dc * 1.2,
            "HAND": True,
            "LB": 70,
            "LCF": max(dc * 0.15, 5.0),
            "NOF": nof,
            "OAL": 73,
            "RE": 0,
            "SFDM": max(dc * 0.8, 1.0),
            "TA": 45,
            "assemblyGaugeLength": 70,
            "shoulder-diameter": dc * 1.2,
            "shoulder-length": 40,
            "upper-radius": 0,
        }
    else:
        # flat end mill (default)
        geometry = {
            "CSP": False,
            "DC": dc,
            "HAND": True,
            "LB": dc * 4,
            "LCF": dc * 3,
            "NOF": nof,
            "OAL": dc * 8,
            "SFDM": dc,
            "assemblyGaugeLength": dc * 4,
            "shoulder-diameter": dc,
            "shoulder-length": dc * 3.5,
        }

    _apply_geometry_tokens(geometry, centroid)
    return geometry


def _fusion_type(centroid: CentroidTool) -> str:
    if centroid.tool_type == "probe":
        # Fusion has dedicated probe tools; fall back to flat end mill geometry
        # tagged clearly so the tool remains usable in CAM.
        return "flat end mill"
    return centroid.tool_type


def _set_or_gap_fill(
    geometry: Dict[str, Any],
    key: str,
    token_value: Optional[float],
    default_value: Any,
) -> None:
    if token_value is not None:
        geometry[key] = float(token_value)
    elif _is_empty_number(geometry.get(key)) and default_value is not None:
        geometry[key] = default_value


def enrich_tool_json(tool: Dict[str, Any], centroid: CentroidTool) -> Dict[str, Any]:
    """Apply explicit description tokens; gap-fill empty/zero CAM fields only."""
    defaults = _geometry_for(centroid)
    geometry = tool.setdefault("geometry", {})

    _set_or_gap_fill(geometry, "LCF", centroid.lcf, defaults.get("LCF"))
    _set_or_gap_fill(geometry, "LB", centroid.lb, defaults.get("LB"))
    _set_or_gap_fill(geometry, "OAL", centroid.oal, defaults.get("OAL"))
    _set_or_gap_fill(geometry, "SFDM", centroid.sfdm, defaults.get("SFDM"))
    _set_or_gap_fill(geometry, "SIG", centroid.point_angle, defaults.get("SIG"))

    if centroid.lb is not None:
        geometry["assemblyGaugeLength"] = float(centroid.lb)
    elif _is_empty_number(geometry.get("assemblyGaugeLength")):
        if "assemblyGaugeLength" in defaults:
            geometry["assemblyGaugeLength"] = defaults["assemblyGaugeLength"]

    if centroid.taper_angle_explicit:
        geometry["TA"] = float(centroid.taper_angle)
    elif "TA" in defaults and _is_empty_number(geometry.get("TA")):
        geometry["TA"] = defaults["TA"]

    if centroid.corner_radius_explicit:
        geometry["RE"] = float(centroid.corner_radius)
    elif "RE" in defaults and _is_empty_number(geometry.get("RE")):
        geometry["RE"] = defaults["RE"]

    if centroid.flutes_explicit:
        geometry["NOF"] = int(centroid.flutes)
        expressions = tool.setdefault("expressions", {})
        expressions["tool_numberOfFlutes"] = str(int(centroid.flutes))
    elif _is_empty_number(geometry.get("NOF")):
        geometry["NOF"] = int(defaults.get("NOF") or centroid.flutes or 2)
        expressions = tool.setdefault("expressions", {})
        if not expressions.get("tool_numberOfFlutes"):
            expressions["tool_numberOfFlutes"] = str(int(geometry["NOF"]))

    if centroid.bmc:
        tool["BMC"] = centroid.bmc
    elif not tool.get("BMC"):
        tool["BMC"] = "hss"

    fusion_type = tool.get("type") or _fusion_type(centroid)
    is_drill = fusion_type == "drill"
    suggested = _base_preset(centroid, is_drill=is_drill)
    presets = (tool.get("start-values") or {}).get("presets") or []
    if presets:
        preset = presets[0]
        feed_keys = (
            "v_f",
            "v_f_leadIn",
            "v_f_leadOut",
            "v_f_plunge",
            "v_f_ramp",
            "v_f_transition",
            "v_f_retract",
            "f_z",
            "f_n",
        )
        for key in feed_keys:
            if key in suggested and _is_empty_number(preset.get(key)):
                preset[key] = suggested[key]

        exprs = preset.setdefault("expressions", {})
        for key, value in (suggested.get("expressions") or {}).items():
            if key == "tool_spindleSpeed":
                continue
            if key not in exprs or not str(exprs.get(key) or "").strip():
                exprs[key] = value

        if not preset.get("tool-coolant"):
            preset["tool-coolant"] = _coolant(centroid)

    return tool


def build_tool_json(centroid: CentroidTool) -> Dict[str, Any]:
    """Create a Fusion tool JSON object for a Centroid row."""
    fusion_type = _fusion_type(centroid)
    is_drill = fusion_type == "drill"
    geometry = _geometry_for(centroid)
    number = int(centroid.tool_number)
    length_offset = int(centroid.h_number or number)
    diameter_offset = int(centroid.d_number or number)

    tool: Dict[str, Any] = {
        "BMC": centroid.bmc or "hss",
        "description": centroid.description,
        "expressions": {
            "tool_description": "'{}'".format(centroid.description.replace("'", "")),
            "tool_numberOfFlutes": str(int(centroid.flutes or 2)),
        },
        "geometry": geometry,
        "guid": _new_guid(),
        "post-process": {
            "break-control": False,
            "comment": "",
            "diameter-offset": diameter_offset,
            "length-offset": length_offset,
            "live": True,
            "manual-tool-change": False,
            "number": number,
            "turret": 0,
        },
        "product-id": "",
        "product-link": "",
        "start-values": {
            "presets": [_base_preset(centroid, is_drill=is_drill)],
        },
        "type": fusion_type,
        "unit": "millimeters",
        "vendor": "Centroid",
    }
    return tool


def patch_tool_json(existing: Dict[str, Any], centroid: CentroidTool) -> Dict[str, Any]:
    """Patch machine fields, then enrich CAM gaps / explicit description tokens."""
    tool = copy.deepcopy(existing)
    tool["description"] = centroid.description
    tool["vendor"] = tool.get("vendor") or "Centroid"

    expressions = tool.setdefault("expressions", {})
    expressions["tool_description"] = "'{}'".format(
        centroid.description.replace("'", "")
    )

    post = tool.setdefault("post-process", {})
    post["number"] = int(centroid.tool_number)
    post["length-offset"] = int(centroid.h_number or centroid.tool_number)
    post["diameter-offset"] = int(centroid.d_number or centroid.tool_number)

    geometry = tool.setdefault("geometry", {})
    if centroid.diameter and centroid.diameter > 0:
        geometry["DC"] = float(centroid.diameter)
        if "SFDM" in geometry:
            # Keep shank if it was larger (common for reduced-shank tools)
            if float(geometry.get("SFDM") or 0) < float(centroid.diameter):
                geometry["SFDM"] = float(centroid.diameter)
        if "shoulder-diameter" in geometry:
            geometry["shoulder-diameter"] = float(centroid.diameter)

    presets = (tool.get("start-values") or {}).get("presets") or []
    if presets:
        preset = presets[0]
        rpm = float(centroid.speed or 0.0)
        preset["n"] = rpm
        if "n_ramp" in preset:
            preset["n_ramp"] = rpm
        exprs = preset.setdefault("expressions", {})
        exprs["tool_spindleSpeed"] = "{:.0f} rpm".format(rpm)
        if centroid.diameter and rpm:
            preset["v_c"] = (math.pi * float(centroid.diameter) * rpm) / 1000.0

    return enrich_tool_json(tool, centroid)
