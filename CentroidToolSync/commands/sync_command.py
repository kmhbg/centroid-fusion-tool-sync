"""Fusion command UI for Centroid → Tool Library sync."""

from __future__ import annotations

import traceback
from typing import Dict, List, Optional

import adsk.core

from lib import centroid_parser, fusion_library, merge


CMD_ID = "CentroidToolSyncCmd"
CMD_NAME = "Centroid Sync"
CMD_DESC = "Synka Centroid Acorn tools.csv till ett lokalt Fusion Tool Library"

_WORKSPACE_CANDIDATES = (
    "CAMEnvironment",
    "MfgWorkingModelEnvironment",
    "FusionSolidEnvironment",
)
_PANEL_CANDIDATES = (
    "SolidScriptsAddinsPanel",
    "CAMScriptsAddinsPanel",
    "UtilityPanel",
)

_csv_path: str = ""
_library_urls: Dict[str, adsk.core.URL] = {}
_centroid_tools: List[centroid_parser.CentroidTool] = []
_skipped_empty: int = 0
_local_handlers: list = []


def start(ui: adsk.core.UserInterface, handlers: list) -> None:
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESC, ""
        )

    on_created = CommandCreatedHandler(handlers)
    cmd_def.commandCreated.add(on_created)
    handlers.append(on_created)

    _add_button_to_ui(ui, cmd_def)


def stop(ui: adsk.core.UserInterface, handlers: list) -> None:
    for workspace_id in _WORKSPACE_CANDIDATES:
        workspace = ui.workspaces.itemById(workspace_id)
        if not workspace:
            continue
        for panel_id in _PANEL_CANDIDATES:
            panel = workspace.toolbarPanels.itemById(panel_id)
            if not panel:
                continue
            control = panel.controls.itemById(CMD_ID)
            if control:
                control.deleteMe()

    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()

    handlers.clear()
    _local_handlers.clear()


def _add_button_to_ui(
    ui: adsk.core.UserInterface, cmd_def: adsk.core.CommandDefinition
) -> None:
    for workspace_id in _WORKSPACE_CANDIDATES:
        workspace = ui.workspaces.itemById(workspace_id)
        if not workspace:
            continue
        for panel_id in _PANEL_CANDIDATES:
            panel = workspace.toolbarPanels.itemById(panel_id)
            if not panel:
                continue
            if panel.controls.itemById(CMD_ID):
                return
            panel.controls.addCommand(cmd_def)
            return

    design = ui.workspaces.itemById("FusionSolidEnvironment")
    if design:
        panel = design.toolbarPanels.itemById("SolidScriptsAddinsPanel")
        if panel and not panel.controls.itemById(CMD_ID):
            panel.controls.addCommand(cmd_def)


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, handlers: list):
        super().__init__()
        self._handlers = handlers

    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        try:
            global _csv_path, _centroid_tools, _skipped_empty
            _csv_path = ""
            _centroid_tools = []
            _skipped_empty = 0
            _local_handlers.clear()

            cmd = args.command
            cmd.isRepeatable = False
            cmd.setDialogInitialSize(520, 420)

            on_execute = CommandExecuteHandler()
            cmd.execute.add(on_execute)
            _local_handlers.append(on_execute)

            on_input = CommandInputChangedHandler()
            cmd.inputChanged.add(on_input)
            _local_handlers.append(on_input)

            on_validate = CommandValidateHandler()
            cmd.validateInputs.add(on_validate)
            _local_handlers.append(on_validate)

            inputs = cmd.commandInputs

            inputs.addTextBoxCommandInput(
                "info",
                "Info",
                "1) Välj Centroid tools.csv\n"
                "2) Välj lokalt bibliotek\n"
                "3) Kontrollera preview\n"
                "4) OK för att synka (update + add, ingen radering)",
                5,
                True,
            )

            inputs.addBoolValueInput("browse_csv", "Välj CSV…", False, "", False)
            path_input = inputs.addStringValueInput(
                "csv_path", "CSV-fil", "(ingen fil vald)"
            )
            path_input.isReadOnly = True

            dropdown = inputs.addDropDownCommandInput(
                "library",
                "Målbibliotek",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            _populate_libraries(dropdown)

            inputs.addTextBoxCommandInput(
                "preview",
                "Preview",
                "Välj CSV och bibliotek för preview.",
                10,
                True,
            )
        except Exception:
            _message("Kunde inte skapa dialog:\n{}".format(traceback.format_exc()))


class CommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args: adsk.core.InputChangedEventArgs):
        global _csv_path, _centroid_tools, _skipped_empty
        try:
            changed = args.input
            inputs = args.firingEvent.sender.commandInputs

            if changed.id == "browse_csv":
                changed.value = False
                path = _pick_csv()
                if not path:
                    return
                _csv_path = path
                path_input = inputs.itemById("csv_path")
                path_input.value = path
                _centroid_tools = centroid_parser.parse_centroid_csv(path)
                _skipped_empty = centroid_parser.count_empty_rows(path)
                _refresh_preview(inputs)
            elif changed.id == "library":
                _refresh_preview(inputs)
        except Exception:
            _message("Fel vid inmatning:\n{}".format(traceback.format_exc()))


class CommandValidateHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args: adsk.core.ValidateInputsEventArgs):
        has_lib = bool(_library_urls)
        args.areInputsValid = bool(_csv_path) and has_lib and bool(_centroid_tools)


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args: adsk.core.CommandEventArgs):
        ui = adsk.core.Application.get().userInterface
        try:
            inputs = args.command.commandInputs
            dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById("library"))
            selected = dropdown.selectedItem
            if not selected:
                ui.messageBox("Välj ett målbibliotek.")
                return

            lib_name = selected.name
            url = _library_urls.get(lib_name)
            if url is None:
                ui.messageBox("Kunde inte hitta biblioteket: {}".format(lib_name))
                return

            if not _centroid_tools:
                ui.messageBox("Inga verktyg att synka i CSV-filen.")
                return

            library = fusion_library.load_library(url)
            stats = merge.merge_into_library(
                library, _centroid_tools, skipped_empty=_skipped_empty
            )
            fusion_library.save_library(url, library)

            ui.messageBox(
                "Sync klar mot '{}'.\n\n{}".format(lib_name, stats.preview_text())
            )
        except Exception:
            ui.messageBox("Sync misslyckades:\n{}".format(traceback.format_exc()))


def _populate_libraries(dropdown: adsk.core.DropDownCommandInput) -> None:
    global _library_urls
    _library_urls = {}
    dropdown.listItems.clear()

    try:
        refs = fusion_library.list_local_library_urls()
    except Exception:
        dropdown.listItems.add("(inga lokala bibliotek)", True)
        return

    if not refs:
        dropdown.listItems.add("(inga lokala bibliotek)", True)
        return

    for i, ref in enumerate(refs):
        _library_urls[ref.name] = ref.url
        dropdown.listItems.add(ref.name, i == 0)


def _pick_csv() -> Optional[str]:
    ui = adsk.core.Application.get().userInterface
    dlg = ui.createFileDialog()
    dlg.isMultiSelectEnabled = False
    dlg.title = "Välj Centroid tools.csv"
    dlg.filter = "CSV-filer (*.csv);;Alla filer (*.*)"
    if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
        return None
    return dlg.filename


def _selected_library_url(inputs: adsk.core.CommandInputs) -> Optional[adsk.core.URL]:
    dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById("library"))
    if not dropdown or not dropdown.selectedItem:
        return None
    return _library_urls.get(dropdown.selectedItem.name)


def _refresh_preview(inputs: adsk.core.CommandInputs) -> None:
    preview = adsk.core.TextBoxCommandInput.cast(inputs.itemById("preview"))
    if not _csv_path:
        preview.formattedText = "Välj en CSV-fil."
        return

    url = _selected_library_url(inputs)
    if url is None:
        preview.formattedText = (
            "CSV: {} verktyg ({} tomma hoppade över).\nVälj målbibliotek.".format(
                len(_centroid_tools), _skipped_empty
            )
        )
        return

    try:
        library = fusion_library.load_library(url)
        existing = set(merge.index_library_by_number(library).keys())
        stats = merge.preview_merge(_centroid_tools, existing, _skipped_empty)
        preview.formattedText = "Bibliotek: {}\n\n{}".format(
            url.leafName, stats.preview_text()
        )
    except Exception:
        preview.formattedText = "Kunde inte läsa bibliotek:\n{}".format(
            traceback.format_exc()
        )


def _message(text: str) -> None:
    ui = adsk.core.Application.get().userInterface
    if ui:
        ui.messageBox(text)
