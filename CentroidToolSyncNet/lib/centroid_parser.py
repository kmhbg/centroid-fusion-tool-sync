"""Parse Centroid Acorn tools.csv exports into normalized tool dicts."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, TextIO, Union


TYPE_RULES = [
    (re.compile(r"probe", re.I), "probe"),
    (re.compile(r"chamfer|90\s*d", re.I), "chamfer mill"),
    (re.compile(r"facing|face", re.I), "face mill"),
    (re.compile(r"\bball\b|round", re.I), "ball end mill"),
    (re.compile(r"drill", re.I), "drill"),
    (re.compile(r"end\s*mill|\bem\b|rough", re.I), "flat end mill"),
]


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


def digits_from(value: str) -> int:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else 0


def parse_description(description: str) -> dict:
    text = description.strip()
    lower = text.lower()

    diam_match = re.search(r"(\d+(?:\.\d+)?)\s*mm", lower)
    flute_match = re.search(r"(\d)\s*f\b", lower)
    radius_match = re.search(r"r\s*(\d+(?:\.\d+)?)", lower)
    angle_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:d|deg|°)", lower)

    tool_type = "flat end mill"
    for pattern, mapped in TYPE_RULES:
        if pattern.search(lower):
            tool_type = mapped
            break

    taper_angle = 45.0 if tool_type == "chamfer mill" else 0.0
    if tool_type == "chamfer mill" and angle_match:
        taper_angle = float(angle_match.group(1))

    return {
        "tool_type": tool_type,
        "diameter": float(diam_match.group(1)) if diam_match else None,
        "flutes": int(flute_match.group(1)) if flute_match else 2,
        "corner_radius": float(radius_match.group(1)) if radius_match else 0.0,
        "taper_angle": taper_angle,
    }


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float((value or "").strip() or default)
    except ValueError:
        return default


def parse_row(row: dict) -> Optional[CentroidTool]:
    description = (row.get("Description") or "").strip()
    if not description:
        return None

    meta = parse_description(description)
    csv_diameter = _safe_float(row.get("Diameter", ""), 0.0)
    diameter = meta["diameter"] if meta["diameter"] is not None else csv_diameter
    if not diameter or diameter <= 0:
        diameter = 1.0

    return CentroidTool(
        tool_number=digits_from(row.get("Tool", "")),
        h_number=digits_from(row.get("H", "")),
        d_number=digits_from(row.get("D", "")),
        offset=_safe_float(row.get("Offset", ""), 0.0),
        diameter=float(diameter),
        coolant=(row.get("Coolant") or "OFF").strip().upper(),
        spindle=(row.get("Spindle") or "OFF").strip().upper(),
        speed=_safe_float(row.get("Speed", ""), 0.0),
        description=description,
        tool_type=meta["tool_type"],
        flutes=meta["flutes"],
        corner_radius=meta["corner_radius"],
        taper_angle=meta["taper_angle"],
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

    return CentroidTool(
        tool_number=tool_number,
        h_number=h_number,
        d_number=d_number,
        offset=_safe_float(str(row.get("offset", 0)), 0.0),
        diameter=float(diameter),
        coolant=str(row.get("coolant") or "OFF").strip().upper(),
        spindle=str(row.get("spindle") or "OFF").strip().upper(),
        speed=_safe_float(str(row.get("speed", 0)), 0.0),
        description=description,
        tool_type=meta["tool_type"],
        flutes=meta["flutes"],
        corner_radius=meta["corner_radius"],
        taper_angle=meta["taper_angle"],
    )


def from_bridge_payload(payload: dict) -> List[CentroidTool]:
    tools: List[CentroidTool] = []
    for row in payload.get("tools") or []:
        parsed = from_bridge_dict(row)
        if parsed is not None:
            tools.append(parsed)
    return tools
