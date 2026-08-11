"""Fusion command UI for Centroid Tool Sync Net (CSV or Bridge)."""

from __future__ import annotations

import traceback
from typing import Dict, List, Optional

import adsk.core

from lib import bridge_client, centroid_parser, fusion_library, merge


CMD_ID = "CentroidToolSyncNetCmd"
CMD_NAME = "Centroid Sync Net"
CMD_DESC = "Synka Centroid via CSV eller bridge (IP) till lokalt Fusion Tool Library"

SOURCE_CSV = "CSV-fil"
SOURCE_BRIDGE = "Centroid Bridge"

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
_source_mode: str = SOURCE_CSV
_bridge_meta: str = ""
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
            global _csv_path, _centroid_tools, _skipped_empty, _source_mode, _bridge_meta
            _csv_path = ""
            _centroid_tools = []
            _skipped_empty = 0
            _source_mode = SOURCE_CSV
            _bridge_meta = ""
            _local_handlers.clear()

            cmd = args.command
            cmd.isRepeatable = False
            cmd.setDialogInitialSize(560, 520)

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
                "Välj källa (CSV eller Bridge), hämta verktyg, välj lokalt bibliotek, "
                "kontrollera preview och tryck OK (update + add, ingen radering).",
                3,
                True,
            )

            source = inputs.addDropDownCommandInput(
                "source",
                "Källa",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            source.listItems.add(SOURCE_CSV, True)
            source.listItems.add(SOURCE_BRIDGE, False)

            inputs.addBoolValueInput("browse_csv", "Välj CSV…", False, "", False)
            path_input = inputs.addStringValueInput(
                "csv_path", "CSV-fil", "(ingen fil vald)"
            )
            path_input.isReadOnly = True

            inputs.addStringValueInput("bridge_ip", "Bridge IP", "192.168.1.100")
            inputs.addStringValueInput(
                "bridge_port", "Bridge-port", str(bridge_client.DEFAULT_PORT)
            )
            inputs.addBoolValueInput(
                "bridge_fetch", "Anslut / Hämta från bridge", False, "", False
            )

            dropdown = inputs.addDropDownCommandInput(
                "library",
                "Målbibliotek",
                adsk.core.DropDownStyles.TextListDropDownStyle,
            )
            _populate_libraries(dropdown)

            inputs.addTextBoxCommandInput(
                "preview",
                "Preview",
                "Välj källa och hämta verktyg för preview.",
                10,
                True,
            )

            _apply_source_visibility(inputs, SOURCE_CSV)
        except Exception:
            _message("Kunde inte skapa dialog:\n{}".format(traceback.format_exc()))


class CommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args: adsk.core.InputChangedEventArgs):
        global _csv_path, _centroid_tools, _skipped_empty, _source_mode, _bridge_meta
        try:
            changed = args.input
            inputs = args.firingEvent.sender.commandInputs

            if changed.id == "source":
                dropdown = adsk.core.DropDownCommandInput.cast(changed)
                if dropdown.selectedItem:
                    _source_mode = dropdown.selectedItem.name
                _centroid_tools = []
                _skipped_empty = 0
                _bridge_meta = ""
                _apply_source_visibility(inputs, _source_mode)
                _refresh_preview(inputs)
                return

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
                _bridge_meta = ""
                _refresh_preview(inputs)
                return

            if changed.id == "bridge_fetch":
                changed.value = False
                ip_input = adsk.core.StringValueCommandInput.cast(
                    inputs.itemById("bridge_ip")
                )
                port_input = adsk.core.StringValueCommandInput.cast(
                    inputs.itemById("bridge_port")
                )
                host = ip_input.value.strip()
                try:
                    port = int(port_input.value.strip() or bridge_client.DEFAULT_PORT)
                except ValueError:
                    _message("Ogiltig port.")
                    return
                try:
                    tools, skipped, health = bridge_client.fetch_tools(host, port)
                    _centroid_tools = tools
                    _skipped_empty = skipped
                    _bridge_meta = "source={} toolCount={}".format(
                        health.get("source", "?"), health.get("toolCount", len(tools))
                    )
                    _refresh_preview(inputs)
                except bridge_client.BridgeError as exc:
                    _centroid_tools = []
                    _skipped_empty = 0
                    _bridge_meta = ""
                    _message("Bridge-fel:\n{}".format(exc))
                    _refresh_preview(inputs)
                return

            if changed.id == "library":
                _refresh_preview(inputs)
        except Exception:
            _message("Fel vid inmatning:\n{}".format(traceback.format_exc()))


class CommandValidateHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args: adsk.core.ValidateInputsEventArgs):
        has_lib = bool(_library_urls)
        args.areInputsValid = has_lib and bool(_centroid_tools)


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
                ui.messageBox("Inga verktyg att synka.")
                return

            library = fusion_library.load_library(url)
            stats = merge.merge_into_library(
                library, _centroid_tools, skipped_empty=_skipped_empty
            )
            fusion_library.save_library(url, library)

            ui.messageBox(
                "Sync klar mot '{}' (källa: {}).\n\n{}".format(
                    lib_name, _source_mode, stats.preview_text()
                )
            )
        except Exception:
            ui.messageBox("Sync misslyckades:\n{}".format(traceback.format_exc()))


def _apply_source_visibility(inputs: adsk.core.CommandInputs, mode: str) -> None:
    is_csv = mode == SOURCE_CSV
    for input_id, visible in (
        ("browse_csv", is_csv),
        ("csv_path", is_csv),
        ("bridge_ip", not is_csv),
        ("bridge_port", not is_csv),
        ("bridge_fetch", not is_csv),
    ):
        item = inputs.itemById(input_id)
        if item:
            item.isVisible = visible


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
    if not _centroid_tools:
        if _source_mode == SOURCE_BRIDGE:
            preview.formattedText = (
                "Bridge-läge: fyll i IP/port och tryck Anslut / Hämta."
            )
        else:
            preview.formattedText = "CSV-läge: välj en CSV-fil."
        return

    header = "Källa: {} — {} verktyg".format(_source_mode, len(_centroid_tools))
    if _skipped_empty:
        header += " ({} tomma hoppade över)".format(_skipped_empty)
    if _bridge_meta:
        header += "\nBridge: {}".format(_bridge_meta)

    url = _selected_library_url(inputs)
    if url is None:
        preview.formattedText = header + "\nVälj målbibliotek."
        return

    try:
        library = fusion_library.load_library(url)
        existing = set(merge.index_library_by_number(library).keys())
        stats = merge.preview_merge(_centroid_tools, existing, _skipped_empty)
        preview.formattedText = "{}\nBibliotek: {}\n\n{}".format(
            header, url.leafName, stats.preview_text()
        )
    except Exception:
        preview.formattedText = "{}\nKunde inte läsa bibliotek:\n{}".format(
            header, traceback.format_exc()
        )


def _message(text: str) -> None:
    ui = adsk.core.Application.get().userInterface
    if ui:
        ui.messageBox(text)
