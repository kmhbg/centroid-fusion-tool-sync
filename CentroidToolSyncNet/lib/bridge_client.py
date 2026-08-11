"""HTTP client for CentroidBridge (/health, /tools)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import List, Tuple

from .centroid_parser import CentroidTool, from_bridge_payload


DEFAULT_PORT = 8765
DEFAULT_TIMEOUT_S = 8.0


class BridgeError(Exception):
    """Raised when the Centroid bridge cannot be reached or returns bad data."""


def _base_url(host: str, port: int) -> str:
    host = (host or "").strip()
    if host.startswith("http://") or host.startswith("https://"):
        # Allow pasting full URL host part; strip trailing slash
        return host.rstrip("/")
    return "http://{}:{}".format(host, int(port))


def _get_json(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "CentroidToolSyncNet/2.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        raise BridgeError("HTTP {}: {}".format(exc.code, exc.reason)) from exc
    except urllib.error.URLError as exc:
        raise BridgeError("Kunde inte ansluta: {}".format(exc.reason)) from exc
    except json.JSONDecodeError as exc:
        raise BridgeError("Ogiltigt JSON-svar från bridge") from exc
    except Exception as exc:
        raise BridgeError(str(exc)) from exc


def check_health(host: str, port: int = DEFAULT_PORT) -> dict:
    url = "{}/health".format(_base_url(host, port))
    data = _get_json(url)
    if not data.get("ok", False):
        raise BridgeError("Bridge svarade men ok=false")
    return data


def fetch_tools(
    host: str, port: int = DEFAULT_PORT
) -> Tuple[List[CentroidTool], int, dict]:
    """
    Fetch tools from bridge.

    Returns (tools, skipped_empty_estimate, health_or_meta).
    """
    health = check_health(host, port)
    url = "{}/tools".format(_base_url(host, port))
    payload = _get_json(url)
    raw_count = len(payload.get("tools") or [])
    tools = from_bridge_payload(payload)
    skipped = max(raw_count - len(tools), 0)
    # Prefer bridge-reported empty skip if present
    if "skipped_empty" in payload:
        try:
            skipped = int(payload["skipped_empty"])
        except (TypeError, ValueError):
            pass
    return tools, skipped, health
