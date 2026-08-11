"""Merge Centroid tools into a Fusion ToolLibrary (update + add)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING

from .centroid_parser import CentroidTool
from .tool_templates import build_tool_json, patch_tool_json

if TYPE_CHECKING:
    import adsk.cam


@dataclass
class MergeStats:
    updated: int = 0
    added: int = 0
    skipped_empty: int = 0
    unmatched_in_fusion: List[int] = field(default_factory=list)
    updated_numbers: List[int] = field(default_factory=list)
    added_numbers: List[int] = field(default_factory=list)

    def preview_text(self) -> str:
        lines = [
            "Uppdateras: {}".format(self.updated),
            "Läggs till: {}".format(self.added),
            "Tomma CSV-rader hoppade över: {}".format(self.skipped_empty),
        ]
        if self.updated_numbers:
            lines.append(
                "T-nummer som uppdateras: {}".format(
                    ", ".join("T{:03d}".format(n) for n in self.updated_numbers[:30])
                )
            )
        if self.added_numbers:
            lines.append(
                "T-nummer som läggs till: {}".format(
                    ", ".join("T{:03d}".format(n) for n in self.added_numbers[:30])
                )
            )
        if self.unmatched_in_fusion:
            lines.append(
                "Finns bara i Fusion (rörs ej): {}".format(
                    ", ".join(
                        "T{:03d}".format(n) for n in self.unmatched_in_fusion[:30]
                    )
                )
            )
        return "\n".join(lines)


def _tool_number_from_json(tool_obj: dict) -> Optional[int]:
    try:
        return int(tool_obj.get("post-process", {}).get("number"))
    except (TypeError, ValueError):
        return None


def _tool_number_from_tool(tool) -> Optional[int]:
    try:
        raw = tool.toJson()
        data = json.loads(raw)
        if isinstance(data, dict) and "data" in data and data["data"]:
            return _tool_number_from_json(data["data"][0])
        if isinstance(data, dict):
            return _tool_number_from_json(data)
    except Exception:
        pass

    try:
        param = tool.parameters.itemByName("tool_number")
        if param and param.value:
            return int(param.value.value)
    except Exception:
        return None
    return None


def index_library_by_number(library) -> Dict[int, int]:
    """Map tool number -> library index."""
    index: Dict[int, int] = {}
    for i in range(library.count):
        tool = library.item(i)
        number = _tool_number_from_tool(tool)
        if number is not None:
            index[number] = i
    return index


def preview_merge(
    centroid_tools: List[CentroidTool],
    existing_numbers: Set[int],
    skipped_empty: int = 0,
) -> MergeStats:
    stats = MergeStats(skipped_empty=skipped_empty)
    centroid_numbers = set()
    for tool in centroid_tools:
        centroid_numbers.add(tool.tool_number)
        if tool.tool_number in existing_numbers:
            stats.updated += 1
            stats.updated_numbers.append(tool.tool_number)
        else:
            stats.added += 1
            stats.added_numbers.append(tool.tool_number)

    stats.unmatched_in_fusion = sorted(existing_numbers - centroid_numbers)
    stats.updated_numbers.sort()
    stats.added_numbers.sort()
    return stats


def _replace_tool_at_index(library, index: int, tool_json: dict) -> None:
    import adsk.cam

    new_tool = adsk.cam.Tool.createFromJson(json.dumps(tool_json))
    library.remove(index)
    library.add(new_tool)


def merge_into_library(
    library,
    centroid_tools: List[CentroidTool],
    skipped_empty: int = 0,
) -> MergeStats:
    """Apply update+add merge. Does not persist; caller must save the library."""
    import adsk.cam

    by_number = index_library_by_number(library)
    stats = preview_merge(centroid_tools, set(by_number.keys()), skipped_empty)

    for centroid in centroid_tools:
        by_number = index_library_by_number(library)
        if centroid.tool_number in by_number:
            idx = by_number[centroid.tool_number]
            existing_tool = library.item(idx)
            existing_json = json.loads(existing_tool.toJson())
            if isinstance(existing_json, dict) and "data" in existing_json:
                existing_json = existing_json["data"][0]
            patched = patch_tool_json(existing_json, centroid)
            try:
                _apply_parameter_patch(existing_tool, centroid)
                if hasattr(library, "updateTool"):
                    library.updateTool(existing_tool)
                else:
                    _replace_tool_at_index(library, idx, patched)
            except Exception:
                _replace_tool_at_index(library, idx, patched)
        else:
            payload = build_tool_json(centroid)
            library.add(adsk.cam.Tool.createFromJson(json.dumps(payload)))

    return stats


def _apply_parameter_patch(tool, centroid: CentroidTool) -> None:
    """Best-effort parameter patch for machine fields."""
    desc = centroid.description.replace("'", "")
    _set_expression(tool, "tool_description", "'{}'".format(desc))
    _set_expression(
        tool,
        "tool_lengthOffset",
        str(int(centroid.h_number or centroid.tool_number)),
    )
    _set_expression(
        tool,
        "tool_diameterOffset",
        str(int(centroid.d_number or centroid.tool_number)),
    )
    if centroid.diameter and centroid.diameter > 0:
        _set_expression(tool, "tool_diameter", "{} mm".format(centroid.diameter))
    if centroid.speed is not None:
        _set_expression(tool, "tool_spindleSpeed", "{:.0f} rpm".format(centroid.speed))


def _set_expression(tool, name: str, expression: str) -> None:
    param = tool.parameters.itemByName(name)
    if param is None:
        return
    param.expression = expression
