"""maya-dev-mcp: MCP server that gives an LLM full Python access to a running Maya session.

Talks to maya_side/maya_dev_bridge.py over a length-prefixed JSON socket on 127.0.0.1.
"""
import json
import os
import socket
import struct
import time
from pathlib import Path
from typing import Literal

from PIL import Image as PILImage, ImageDraw
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

HOST = "127.0.0.1"
PORT = int(os.environ.get("MAYA_DEV_MCP_PORT", "50010"))
CAPTURE_DIR = Path(os.environ.get("MAYA_DEV_MCP_CAPTURE_DIR", Path(__file__).parent / "captures"))
KEEP_CAPTURES = 40
MAX_TEXT_CHARS = 40_000

ViewName = Literal["persp", "front", "back", "side", "left", "top", "bottom", "current"]
DisplayMode = Literal["shaded", "textured", "wireframe", "wireOnShaded"]

INSTRUCTIONS = """\
Controls a live Autodesk Maya session through Python.
- Use execute_python for anything (maya.cmds as `cmds`, maya.api.OpenMaya as `om`, maya.mel as `mel`
  are pre-imported). Prefer exact numeric checks (xform, exactWorldBoundingBox, polyEvaluate,
  getAttr, listConnections) to decide whether something is correct.
- Use viewport_capture as a visual sanity check after a batch of changes, not after every step.
- C++ plugin loop: unload_plugin -> build the .mll -> load_plugin -> exercise it with
  execute_python -> read maya_log for errors/warnings. Windows keeps a loaded .mll locked,
  so always unload before rebuilding.
"""

mcp = MCPServer("maya-dev-mcp", instructions=INSTRUCTIONS)


class MayaBridgeError(ToolError):
    """Raised for anything that went wrong on the Maya side; ToolError text reaches the model."""


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(min(size - len(buf), 1024 * 1024))
        if not chunk:
            raise MayaBridgeError("Maya closed the connection")
        buf += chunk
    return bytes(buf)


def _request(cmd: str, timeout: float = 120.0, **args):
    """Send one command to the bridge and return its result, raising on bridge-side errors."""
    try:
        sock = socket.create_connection((HOST, PORT), timeout=5)
    except OSError as e:
        raise MayaBridgeError(
            f"Cannot reach the Maya bridge on {HOST}:{PORT} ({e}). Is Maya running and was "
            "maya_dev_bridge.start() executed (see userSetup.py)?"
        ) from None
    with sock:
        sock.settimeout(timeout)
        body = json.dumps({"cmd": cmd, "args": args}).encode("utf-8")
        sock.sendall(struct.pack(">I", len(body)) + body)
        (size,) = struct.unpack(">I", _recv_exact(sock, 4))
        reply = json.loads(_recv_exact(sock, size).decode("utf-8"))
    if not reply.get("ok"):
        raise MayaBridgeError(reply.get("error", "unknown bridge error"))
    return reply.get("result")


def _clip(text: str) -> str:
    if len(text) <= MAX_TEXT_CHARS:
        return text
    return text[:MAX_TEXT_CHARS] + f"\n... [truncated {len(text) - MAX_TEXT_CHARS} chars]"


def _prune_captures() -> None:
    files = sorted(CAPTURE_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)
    for old in files[:-KEEP_CAPTURES]:
        old.unlink(missing_ok=True)


def _compose(images: list[dict]) -> Path:
    # Playblast PNGs mark the background as transparent but keep its real colour in RGB,
    # so dropping alpha gives exactly what the viewport shows.
    tiles = [(img["view"], PILImage.open(img["path"]).convert("RGB")) for img in images]
    w, h = tiles[0][1].size
    cols = 1 if len(tiles) == 1 else 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = PILImage.new("RGB", (w * cols, h * rows), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, (view, tile) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(tile, (x, y))
        draw.rectangle([x, y, x + 8 * len(view) + 10, y + 16], fill=(0, 0, 0))
        draw.text((x + 5, y + 2), view, fill=(255, 220, 0))
    for img in images:
        Path(img["path"]).unlink(missing_ok=True)
    out = CAPTURE_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_sheet.png"
    sheet.save(out)
    _prune_captures()
    return out


@mcp.tool()
def execute_python(code: str, undoable: bool = True, reset_namespace: bool = False,
                   timeout_seconds: float = 120.0) -> str:
    """Execute Python code inside the running Maya session (on Maya's main thread).

    `cmds` (maya.cmds), `om` (maya.api.OpenMaya) and `mel` (maya.mel) are pre-imported. The
    namespace persists between calls, so functions and variables defined earlier stay available
    (reset_namespace=True starts fresh). If the last statement is an expression its value is
    returned (like a REPL); print() output is captured. With undoable=True the whole call is a
    single undo chunk, so one Ctrl+Z in Maya reverts it.
    """
    r = _request("exec", timeout=timeout_seconds, code=code, undoable=undoable,
                 reset_namespace=reset_namespace)
    parts = []
    if r["result"] is not None:
        value = r["result"] if isinstance(r["result"], str) else json.dumps(r["result"])
        parts.append(f"result: {value}")
    if r["stdout"]:
        parts.append(f"stdout:\n{r['stdout'].rstrip()}")
    if r["stderr"]:
        parts.append(f"stderr:\n{r['stderr'].rstrip()}")
    if r["error"]:
        parts.append(f"error:\n{r['error'].rstrip()}")
        raise MayaBridgeError(_clip("\n".join(parts)))
    parts.append(f"({r['seconds']}s)")
    return _clip("\n".join(parts))


@mcp.tool()
def viewport_capture(views: list[ViewName] = ["persp", "front", "side", "top"],
                     objects: list[str] | None = None, display: DisplayMode = "shaded",
                     width: int = 512, height: int = 384, isolate: bool = False) -> Image:
    """Render the viewport (Viewport 2.0 playblast of the current frame) and return one image.

    Several views are tiled into a labelled contact sheet (2 columns). Each named view uses a
    temporary camera framed on `objects` (default: all visible geometry); 'current' uses the
    panel's own camera as-is. The user's cameras, selection and panel settings are restored and
    nothing is added to the undo queue. Y-up scenes only. Image size is width x height per view.
    The ground grid is not drawn (Viewport 2.0 playblasts omit it); isolate=True hides everything
    except `objects`.
    """
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    r = _request("capture", out_dir=str(CAPTURE_DIR), views=list(views), objects=objects,
                 width=width, height=height, display=display, isolate=isolate)
    return Image(path=_compose(r["images"]))


@mcp.tool()
def load_plugin(path: str, new_scene: bool = False, delete_nodes: bool = False) -> str:
    """Load a Maya plugin (.mll/.py) by file path; reloads it if a plugin with that name is loaded.

    Reloading follows unload_plugin rules (new_scene / delete_nodes). Returns the registered
    node types and commands plus any errors/warnings Maya printed while loading.
    """
    return json.dumps(_request("load_plugin", path=path, new_scene=new_scene,
                               delete_nodes=delete_nodes), indent=1)


@mcp.tool()
def unload_plugin(name: str, new_scene: bool = False, delete_nodes: bool = False) -> str:
    """Unload a plugin by name (or file path) so its .mll is unlocked for rebuilding.

    Fails if nodes of the plugin's types exist, unless delete_nodes=True (deletes just those
    nodes) or new_scene=True (DISCARDS the whole current scene without saving). The undo queue is
    flushed because it holds references that block unloading.
    """
    return json.dumps(_request("unload_plugin", name=name, new_scene=new_scene,
                               delete_nodes=delete_nodes), indent=1)


@mcp.tool()
def maya_log(last: int = 50, levels: list[Literal["info", "warning", "error", "result", "display",
                                                   "history", "stacktrace"]] | None = None,
             since_id: int | None = None, clear: bool = False) -> str:
    """Read recent Script Editor output captured by the bridge (MGlobal::displayError/Warning/Info,
    cmds.warning, results...). Command echoes ('history') are left out unless asked for in `levels`.
    Use since_id from a previous call to get only new lines.

    Output of execute_python's own print() is returned by that tool instead, and C++ std::cout goes
    to Maya's Output Window, not here; use MGlobal::displayInfo in plugins.
    """
    r = _request("log", last=last, levels=levels, since_id=since_id, clear=clear)
    lines = [f"[{e['id']}] {e['level']}: {e['msg']}" for e in r["entries"]]
    lines.append(f"(last_id={r['last_id']})")
    return _clip("\n".join(lines))


@mcp.tool()
def scene_info() -> str:
    """Compact summary of the open scene: file, up axis, units, time, selection, top-level nodes,
    node counts by type and user (non-Autodesk) plugins currently loaded."""
    info = _request("scene_info")
    info["bridge"] = _request("ping")
    return json.dumps(info, indent=1)


@mcp.tool()
def reload_bridge() -> str:
    """Reload maya_dev_bridge.py inside Maya after its source was edited (no Maya restart)."""
    return json.dumps(_request("reload_bridge"))


if __name__ == "__main__":
    mcp.run()
