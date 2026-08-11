"""Access and persist local Fusion Tool Libraries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import adsk.cam
import adsk.core


@dataclass
class LibraryRef:
    name: str
    url: adsk.core.URL


def _tool_libraries() -> adsk.cam.ToolLibraries:
    cam_manager = adsk.cam.CAMManager.get()
    return cam_manager.libraryManager.toolLibraries


def list_local_library_urls(
    folder_url: Optional[adsk.core.URL] = None,
) -> List[LibraryRef]:
    """Recursively list local tool library assets."""
    tool_libs = _tool_libraries()
    if folder_url is None:
        folder_url = tool_libs.urlByLocation(
            adsk.cam.LibraryLocations.LocalLibraryLocation
        )

    results: List[LibraryRef] = []
    for asset_url in tool_libs.childAssetURLs(folder_url):
        results.append(LibraryRef(name=asset_url.leafName, url=asset_url))

    for child_folder in tool_libs.childFolderURLs(folder_url):
        results.extend(list_local_library_urls(child_folder))

    return results


def load_library(url: adsk.core.URL) -> adsk.cam.ToolLibrary:
    tool_libs = _tool_libraries()
    library = tool_libs.toolLibraryAtURL(url)
    if library is None:
        raise RuntimeError("Kunde inte ladda verktygsbiblioteket: {}".format(url.leafName))
    return library


def save_library(url: adsk.core.URL, library: adsk.cam.ToolLibrary) -> None:
    tool_libs = _tool_libraries()
    tool_libs.updateToolLibrary(url, library)


def find_library_by_name(name: str) -> Optional[LibraryRef]:
    for ref in list_local_library_urls():
        if ref.name == name:
            return ref
    return None


def library_choices() -> List[Tuple[str, adsk.core.URL]]:
    return [(ref.name, ref.url) for ref in list_local_library_urls()]
