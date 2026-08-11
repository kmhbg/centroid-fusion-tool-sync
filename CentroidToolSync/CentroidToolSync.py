"""Centroid Tool Sync – Fusion 360 Add-In entry point."""

import adsk.core
import traceback
import os
import sys

_ADDIN_PATH = os.path.dirname(os.path.realpath(__file__))
if _ADDIN_PATH not in sys.path:
    sys.path.insert(0, _ADDIN_PATH)

from commands import sync_command


_handlers = []


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        sync_command.start(ui, _handlers)
    except Exception:
        if ui:
            ui.messageBox(
                "Centroid Tool Sync misslyckades vid start:\n{}".format(
                    traceback.format_exc()
                )
            )


def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        sync_command.stop(ui, _handlers)
    except Exception:
        if ui:
            ui.messageBox(
                "Centroid Tool Sync misslyckades vid stopp:\n{}".format(
                    traceback.format_exc()
                )
            )
