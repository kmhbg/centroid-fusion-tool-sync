"""Parse Centroid Acorn tools.csv exports into normalized tool dicts."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, TextIO, Union


TYPE_RULES = [
    (re.compile(r"(?:^|\s)pr(?:\s|$)|probe", re.I), "probe"),
    (re.compile(r"(?:^|\s)ch(?:\s|$)|chamfer|90\s*d", re.I), "chamfer mill"),
    (re.compile(r"(?:^|\s)fm(?:\s|$)|facing|\bface\b", re.I), "face mill"),
    (re.compile(r"(?:^|\s)bl(?:\s|$)|\bball\b|round", re.I), "ball end mill"),
    (re.compile(r"(?:^|\s)dr(?:\s|$)|drill", re.I), "drill"),
    (re.compile(r"(?:^|\s)em(?:\s|$)|end\s*mill|\bem\b|rough", re.I), "flat end mill"),
]

_TOKEN_FLOAT = re.compile(
    r"\b(lcf|lb|oal|sfdm|sig|ta)\s*(\d+(?:\.\d+)?)\b",
    re.I,
)


@dataclass
class CentroidTool:
    tool_number: int
    h_number: int
    d_number: int
    offset: float
    diameter: float
    coolant: str
    spindle: str
    speed: float
    description: str
    tool_type: str
    flutes: int
    corner_radius: float
    taper_angle: float
    # Optional CAM tokens from description (None = not declared)
    lcf: Optional[float] = None
    lb: Optional[float] = None
    oal: Optional[float] = None
    sfdm: Optional[float] = None
    bmc: Optional[str] = None
    point_angle: Optional[float] = None
    flutes_explicit: bool = False
    corner_radius_explicit: bool = False
    taper_angle_explicit: bool = False


def digits_from(value: str) -> int:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else 0


def parse_description(description: str) -> dict:
    text = description.strip()
    lower = text.lower()

    diam_match = re.search(r"(\d+(?:\.\d+)?)\s*mm", lower)
    flute_match = re.search(r"(\d)\s*f\b", lower)
    radius_match = re.search(r"\br\s*(\d+(?:\.\d+)?)\b", lower)

    tool_type = "flat end mill"
    for pattern, mapped in TYPE_RULES:
        if pattern.search(lower):
            tool_type = mapped
            break

    tokens = {
        "lcf": None,
        "lb": None,
        "oal": None,
        "sfdm": None,
        "sig": None,
        "ta": None,
    }
    for match in _TOKEN_FLOAT.finditer(lower):
        key = match.group(1).lower()
        tokens[key] = float(match.group(2))

    bmc = None
    if re.search(r"\b(carbide|carb)\b", lower):
        bmc = "carbide"
    elif re.search(r"\bhss\b", lower):
        bmc = "hss"

    taper_angle = 45.0 if tool_type == "chamfer mill" else 0.0
    taper_explicit = False
    # Prefer explicit TA token; fall back to "90d" / "deg" style for chamfer
    if tokens["ta"] is not None:
        taper_angle = float(tokens["ta"])
        taper_explicit = True
    else:
        angle_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:d|deg|°)\b", lower)
        # Ignore bare "d" that is part of typed tokens already consumed; keep legacy 90d
        if tool_type == "chamfer mill" and angle_match:
            taper_angle = float(angle_match.group(1))
            taper_explicit = True

    flutes_explicit = flute_match is not None
    flutes = int(flute_match.group(1)) if flute_match else 2

    corner_explicit = radius_match is not None
    corner_radius = float(radius_match.group(1)) if radius_match else 0.0

    return {
        "tool_type": tool_type,
        "diameter": float(diam_match.group(1)) if diam_match else None,
        "flutes": flutes,
        "flutes_explicit": flutes_explicit,
        "corner_radius": corner_radius,
        "corner_radius_explicit": corner_explicit,
        "taper_angle": taper_angle,
        "taper_angle_explicit": taper_explicit,
        "lcf": tokens["lcf"],
        "lb": tokens["lb"],
        "oal": tokens["oal"],
        "sfdm": tokens["sfdm"],
        "bmc": bmc,
        "point_angle": tokens["sig"],
    }


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float((value or "").strip() or default)
    except ValueError:
        return default


def _tool_from_meta(
    *,
    tool_number: int,
    h_number: int,
    d_number: int,
    offset: float,
    diameter: float,
    coolant: str,
    spindle: str,
    speed: float,
    description: str,
    meta: dict,
) -> CentroidTool:
    return CentroidTool(
        tool_number=tool_number,
        h_number=h_number,
        d_number=d_number,
        offset=offset,
        diameter=float(diameter),
        coolant=coolant,
        spindle=spindle,
        speed=speed,
        description=description,
        tool_type=meta["tool_type"],
        flutes=meta["flutes"],
        corner_radius=meta["corner_radius"],
        taper_angle=meta["taper_angle"],
        lcf=meta["lcf"],
        lb=meta["lb"],
        oal=meta["oal"],
        sfdm=meta["sfdm"],
        bmc=meta["bmc"],
        point_angle=meta["point_angle"],
        flutes_explicit=meta["flutes_explicit"],
        corner_radius_explicit=meta["corner_radius_explicit"],
        taper_angle_explicit=meta["taper_angle_explicit"],
    )


def parse_row(row: dict) -> Optional[CentroidTool]:
    description = (row.get("Description") or "").strip()
    if not description:
        return None

    meta = parse_description(description)
    csv_diameter = _safe_float(row.get("Diameter", ""), 0.0)
    diameter = meta["diameter"] if meta["diameter"] is not None else csv_diameter
    if not diameter or diameter <= 0:
        diameter = 1.0

    return _tool_from_meta(
        tool_number=digits_from(row.get("Tool", "")),
        h_number=digits_from(row.get("H", "")),
        d_number=digits_from(row.get("D", "")),
        offset=_safe_float(row.get("Offset", ""), 0.0),
        diameter=float(diameter),
        coolant=(row.get("Coolant") or "OFF").strip().upper(),
        spindle=(row.get("Spindle") or "OFF").strip().upper(),
        speed=_safe_float(row.get("Speed", ""), 0.0),
        description=description,
        meta=meta,
    )


def parse_centroid_csv(
    source: Union[str, Path, TextIO, Iterable[str]],
) -> List[CentroidTool]:
    """Parse a Centroid tools.csv path or file-like object."""
    close_after = False
    if isinstance(source, (str, Path)):
        handle = open(source, newline="", encoding="utf-8-sig")
        close_after = True
    else:
        handle = source

    try:
        reader = csv.DictReader(handle)
        tools: List[CentroidTool] = []
        for row in reader:
            parsed = parse_row(row)
            if parsed is not None and parsed.tool_number > 0:
                tools.append(parsed)
        return tools
    finally:
        if close_after:
            handle.close()


def count_empty_rows(source: Union[str, Path]) -> int:
    with open(source, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return sum(1 for row in reader if not (row.get("Description") or "").strip())


def from_bridge_dict(row: dict) -> Optional[CentroidTool]:
    """Map a bridge JSON tool object to CentroidTool (same heuristics as CSV)."""
    description = str(row.get("description") or "").strip()
    if not description:
        return None

    meta = parse_description(description)
    raw_diameter = row.get("diameter", 0)
    try:
        csv_diameter = float(raw_diameter or 0)
    except (TypeError, ValueError):
        csv_diameter = 0.0
    diameter = meta["diameter"] if meta["diameter"] is not None else csv_diameter
    if not diameter or diameter <= 0:
        diameter = 1.0

    try:
        tool_number = int(row.get("tool_number") or 0)
    except (TypeError, ValueError):
        tool_number = 0
    if tool_number <= 0:
        return None

    try:
        h_number = int(row.get("h_number") or tool_number)
    except (TypeError, ValueError):
        h_number = tool_number
    try:
        d_number = int(row.get("d_number") or tool_number)
    except (TypeError, ValueError):
        d_number = tool_number

    return _tool_from_meta(
        tool_number=tool_number,
        h_number=h_number,
        d_number=d_number,
        offset=_safe_float(str(row.get("offset", 0)), 0.0),
        diameter=float(diameter),
        coolant=str(row.get("coolant") or "OFF").strip().upper(),
        spindle=str(row.get("spindle") or "OFF").strip().upper(),
        speed=_safe_float(str(row.get("speed", 0)), 0.0),
        description=description,
        meta=meta,
    )


def from_bridge_payload(payload: dict) -> List[CentroidTool]:
    tools: List[CentroidTool] = []
    for row in payload.get("tools") or []:
        parsed = from_bridge_dict(row)
        if parsed is not None:
            tools.append(parsed)
    return tools
