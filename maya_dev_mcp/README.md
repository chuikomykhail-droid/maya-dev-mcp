# maya-dev-mcp

An MCP server that gives an LLM full Python access to a running Autodesk Maya session, plus
viewport capture and a plugin load/unload loop for C++ plugin development.

Not affiliated with Autodesk. Tested with Maya 2024 on Windows.

## Tools

| Tool | What it does |
|---|---|
| `execute_python` | Runs Python in Maya on the main thread. `cmds`, `om` (maya.api.OpenMaya) and `mel` are pre-imported, the namespace persists between calls, the value of a trailing expression is returned, `print()` output is captured, and the whole call is one undo chunk. |
| `viewport_capture` | Viewport 2.0 playblast of the current frame from `persp/front/back/side/left/top/bottom/current`, framed on given objects (or all visible geometry), tiled into one labelled image. Uses a temporary window and cameras, so the user's viewports, cameras and selection are untouched and nothing goes to the undo queue. |
| `load_plugin` | Loads a `.mll`/`.py` plugin by path (reloads it if loaded) and reports node types, commands and what Maya printed while loading. |
| `unload_plugin` | Unloads a plugin so Windows releases the `.mll` for rebuilding. Refuses while plugin nodes exist unless `delete_nodes` or `new_scene` is passed; flushes the undo queue. |
| `maya_log` | Recent Script Editor output (errors, warnings, info, results) captured via `MCommandMessage`. |
| `scene_info` | Scene file, up axis, units, time, selection, top-level nodes, node counts, non-Autodesk plugins. |
| `reload_bridge` | Reloads the Maya-side bridge after editing it, without restarting Maya. |

## How it works

```
MCP client (Claude Code, ...) --stdio--> server.py --TCP 127.0.0.1:50010--> maya_side/maya_dev_bridge.py (inside Maya)
```

The bridge is a small socket server running in a background thread inside Maya. Messages are
length-prefixed JSON; every command is executed on Maya's main thread through
`maya.utils.executeInMainThreadWithResult`. Unlike Maya's `commandPort` there is no MEL
escaping, no 4 KB buffer limit and no security prompt.

## Setup

1. Create a virtual environment and install the dependencies (Python 3.10+):
   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
2. Start the bridge in Maya, e.g. from `userSetup.py`:
   ```python
   import sys
   import maya.utils
   sys.path.append(r"<path to>\maya_dev_mcp\maya_side")

   def _start_maya_dev_bridge():
       import maya_dev_bridge
       maya_dev_bridge.start()

   maya.utils.executeDeferred(_start_maya_dev_bridge)
   ```
3. Register the server with your MCP client, e.g. Claude Code:
   ```
   claude mcp add --scope project maya-dev -- "<path>\.venv\Scripts\python.exe" "<path>\server.py"
   ```

Environment variables: `MAYA_DEV_MCP_PORT` (default `50010`, used by both sides) and
`MAYA_DEV_MCP_CAPTURE_DIR` (default `./captures`, the last 40 contact sheets are kept).

## Security

`execute_python` runs arbitrary code with the permissions of the Maya process. The bridge only
listens on 127.0.0.1 and has no authentication, so any local process can use it, as with a
Maya `commandPort`. Only connect MCP clients you trust.

## Limitations

- `viewport_capture` supports Y-up scenes only; Viewport 2.0 playblasts do not draw the grid.
- Long-running code blocks Maya's UI for its duration (default timeout 120 s).
- C++ `std::cout` goes to Maya's Output Window, not to `maya_log`; use `MGlobal::displayInfo`.
