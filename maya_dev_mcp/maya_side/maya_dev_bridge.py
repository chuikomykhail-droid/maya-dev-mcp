"""Maya-side bridge for maya-dev-mcp.

Runs a small TCP server on 127.0.0.1 inside Maya. Every request is one length-prefixed
JSON message {"cmd": str, "args": dict}; the handler runs on Maya's main thread and the
reply {"ok": bool, "result": ..., "error": str} is sent back the same way.

Start from userSetup.py:
    import maya_dev_bridge; maya_dev_bridge.start()
"""
import ast
import collections
import contextlib
import io
import json
import os
import socket
import struct
import threading
import time
import traceback

import maya.cmds as cmds
import maya.mel as mel
import maya.utils
import maya.api.OpenMaya as om

BRIDGE_VERSION = "0.1.0"
HOST = "127.0.0.1"
DEFAULT_PORT = 50010
MAX_MESSAGE_BYTES = 256 * 1024 * 1024
UNDO_CHUNK_NAME = "maya_dev_mcp"

_server = None
_log = collections.deque(maxlen=2000)
_log_next_id = 1
_log_callback_id = None
_namespace = None
# Emitted asynchronously by viewFit on the capture cameras; not useful to the model.
_IGNORED_LOG_MESSAGES = ("Selection is outside of view frustrum",)


# --------------------------------------------------------------------------- protocol

def _recv_exact(conn, size):
    buf = bytearray()
    while len(buf) < size:
        chunk = conn.recv(min(size - len(buf), 1024 * 1024))
        if not chunk:
            return None
        buf += chunk
    return bytes(buf)


def _recv_message(conn):
    header = _recv_exact(conn, 4)
    if header is None:
        return None
    (size,) = struct.unpack(">I", header)
    if size > MAX_MESSAGE_BYTES:
        raise ValueError("message too large: %d bytes" % size)
    body = _recv_exact(conn, size)
    if body is None:
        return None
    return json.loads(body.decode("utf-8"))


def _send_message(conn, obj):
    body = json.dumps(obj, default=repr).encode("utf-8")
    conn.sendall(struct.pack(">I", len(body)) + body)


class _BridgeServer(threading.Thread):
    def __init__(self, port):
        super().__init__(name="maya_dev_mcp_bridge", daemon=True)
        self.port = port
        self._stopping = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind((HOST, port))
        self._sock.listen(4)

    def run(self):
        while not self._stopping.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            with conn:
                try:
                    self._serve(conn)
                except Exception:
                    traceback.print_exc()

    def _serve(self, conn):
        while True:
            request = _recv_message(conn)
            if request is None:
                return
            _send_message(conn, _dispatch(request))

    def stop(self):
        self._stopping.set()
        try:
            self._sock.close()
        except OSError:
            pass


def _dispatch(request):
    cmd = request.get("cmd")
    args = request.get("args") or {}
    handler = _HANDLERS.get(cmd)
    if handler is None:
        return {"ok": False, "error": "unknown command: %r" % cmd}

    def call():
        try:
            return {"ok": True, "result": handler(**args)}
        except Exception as e:
            return {"ok": False, "error": "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc())}

    return maya.utils.executeInMainThreadWithResult(call)


# --------------------------------------------------------------------------- script editor log

_MESSAGE_KINDS = {
    om.MCommandMessage.kHistory: "history",
    om.MCommandMessage.kDisplay: "display",
    om.MCommandMessage.kInfo: "info",
    om.MCommandMessage.kWarning: "warning",
    om.MCommandMessage.kError: "error",
    om.MCommandMessage.kResult: "result",
    om.MCommandMessage.kStackTrace: "stacktrace",
}


def _on_command_output(message, message_type, *_):
    # Never print from here: it would re-enter this callback.
    global _log_next_id
    text = message.rstrip("\n")
    if not text or text.startswith(_IGNORED_LOG_MESSAGES):
        return
    _log.append({"id": _log_next_id, "t": time.time(),
                 "level": _MESSAGE_KINDS.get(message_type, str(message_type)), "msg": text})
    _log_next_id += 1


def _install_log_callback():
    global _log_callback_id
    if _log_callback_id is None:
        _log_callback_id = om.MCommandMessage.addCommandOutputCallback(_on_command_output)


def _remove_log_callback():
    global _log_callback_id
    if _log_callback_id is not None:
        om.MMessage.removeCallback(_log_callback_id)
        _log_callback_id = None


# --------------------------------------------------------------------------- helpers

def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _get_namespace(reset=False):
    global _namespace
    if _namespace is None or reset:
        _namespace = {"__name__": "__maya_dev_mcp__", "cmds": cmds, "mel": mel, "om": om}
    return _namespace


@contextlib.contextmanager
def _undo_chunk(enabled):
    if enabled:
        cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK_NAME)
    try:
        yield
    finally:
        if enabled:
            cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def _undo_suspended():
    was_on = cmds.undoInfo(q=True, state=True)
    if was_on:
        cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        if was_on:
            cmds.undoInfo(stateWithoutFlush=True)


def _user_plugins():
    """Loaded plugins that are not Autodesk's own (by install location and vendor)."""
    install_dir = os.path.normcase(os.path.normpath(os.environ.get("MAYA_LOCATION", "")))
    result = []
    for name in cmds.pluginInfo(q=True, listPlugins=True) or []:
        path = cmds.pluginInfo(name, q=True, path=True) or ""
        vendor = cmds.pluginInfo(name, q=True, vendor=True) or ""
        if install_dir and os.path.normcase(os.path.normpath(path)).startswith(install_dir):
            continue
        if "autodesk" in vendor.lower():
            continue
        result.append({"name": name, "path": path, "vendor": vendor})
    return result


# --------------------------------------------------------------------------- commands

def cmd_ping():
    return {"bridge_version": BRIDGE_VERSION, "maya_version": cmds.about(version=True),
            "api_version": cmds.about(apiVersion=True), "pid": os.getpid()}


def cmd_exec(code, undoable=True, reset_namespace=False):
    ns = _get_namespace(reset_namespace)
    out, err = io.StringIO(), io.StringIO()
    result, error = None, None
    started = time.perf_counter()
    with _undo_chunk(undoable):
        try:
            tree = ast.parse(code, "<mcp>", "exec")
            last_expr = None
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last_expr = ast.Expression(tree.body.pop().value)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                exec(compile(tree, "<mcp>", "exec"), ns)
                if last_expr is not None:
                    value = eval(compile(last_expr, "<mcp>", "eval"), ns)
                    ns["_"] = value
                    result = _jsonable(value)
        except Exception:
            error = traceback.format_exc()
    return {"result": result, "stdout": out.getvalue(), "stderr": err.getvalue(),
            "error": error, "seconds": round(time.perf_counter() - started, 3)}


_VIEWS = {
    # name: (orthographic, rotation) for a Y-up scene
    "persp": (False, (-25.0, 45.0, 0.0)),
    "front": (True, (0.0, 0.0, 0.0)),
    "back": (True, (0.0, 180.0, 0.0)),
    "side": (True, (0.0, 90.0, 0.0)),
    "left": (True, (0.0, -90.0, 0.0)),
    "top": (True, (-90.0, 0.0, 0.0)),
    "bottom": (True, (90.0, 0.0, 0.0)),
}

_DISPLAY_MODES = {
    "shaded": dict(displayAppearance="smoothShaded", wireframeOnShaded=False, displayTextures=False),
    "textured": dict(displayAppearance="smoothShaded", wireframeOnShaded=False, displayTextures=True),
    "wireframe": dict(displayAppearance="wireframe", wireframeOnShaded=False, displayTextures=False),
    "wireOnShaded": dict(displayAppearance="smoothShaded", wireframeOnShaded=True, displayTextures=False),
}

CAPTURE_WINDOW = "mayaDevMcpCaptureWindow"
CAPTURE_PANEL = "mayaDevMcpCapturePanel"


def _user_camera():
    """Camera of the panel the user is looking through (focused, else first visible), or persp."""
    candidates = [cmds.getPanel(withFocus=True)] + (cmds.getPanel(visiblePanels=True) or [])
    for panel in candidates:
        if panel and panel != CAPTURE_PANEL and cmds.getPanel(typeOf=panel) == "modelPanel":
            return cmds.modelPanel(panel, q=True, camera=True)
    return "persp"


def _default_fit_targets():
    shapes = cmds.ls(geometry=True, visible=True, long=True, noIntermediate=True) or []
    return sorted(set(cmds.listRelatives(shapes, parent=True, fullPath=True) or []))


def _pull_back_outside(cam, targets):
    """viewFit can leave an orthographic camera inside the framed geometry; move it backwards along
    its view axis until it is clear of the targets' bounding box (distance does not affect ortho)."""
    xmin, ymin, zmin, xmax, ymax, zmax = cmds.exactWorldBoundingBox(targets)
    diagonal = ((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2) ** 0.5
    center = ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0)
    matrix = cmds.xform(cam, q=True, matrix=True, worldSpace=True)
    back = matrix[8:11]  # camera looks down its local -Z, so +Z points backwards
    position = cmds.xform(cam, q=True, translation=True, worldSpace=True)
    # Keep the framing (offset across the view axis) and only reset the depth.
    depth = sum((position[i] - center[i]) * back[i] for i in range(3))
    shift = diagonal + 10.0 - depth
    cmds.xform(cam, translation=[position[i] + back[i] * shift for i in range(3)], worldSpace=True)


def _delete_capture_ui():
    if cmds.modelPanel(CAPTURE_PANEL, exists=True):
        cmds.deleteUI(CAPTURE_PANEL, panel=True)
    if cmds.window(CAPTURE_WINDOW, exists=True):
        cmds.deleteUI(CAPTURE_WINDOW)


def _create_capture_panel(width, height, display):
    """A throwaway window with its own modelPanel: capture never depends on (or changes) the user's
    viewports, and works even when the main window's panels are hidden (e.g. Maya minimized)."""
    _delete_capture_ui()
    window = cmds.window(CAPTURE_WINDOW, title="maya_dev_mcp capture", sizeable=False,
                         widthHeight=(width + 20, height + 20))
    cmds.paneLayout()
    panel = cmds.modelPanel(CAPTURE_PANEL, menuBarVisible=False, camera="persp")
    cmds.modelEditor(panel, e=True, headsUpDisplay=False, cameras=False, lights=False,
                     manipulators=False, locators=False, **_DISPLAY_MODES[display])
    cmds.showWindow(window)
    return panel


def cmd_capture(out_dir, views=("persp", "front", "side", "top"), objects=None,
                width=512, height=384, display="shaded", isolate=False):
    unknown = [v for v in views if v not in _VIEWS and v != "current"]
    if unknown:
        raise ValueError("unknown views %s, expected some of %s or 'current'" % (unknown, sorted(_VIEWS)))
    if display not in _DISPLAY_MODES:
        raise ValueError("unknown display %r, expected one of %s" % (display, sorted(_DISPLAY_MODES)))
    if cmds.upAxis(q=True, axis=True) != "y":
        raise RuntimeError("viewport_capture currently supports Y-up scenes only")
    if objects:
        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            raise ValueError("objects not found: %s" % missing)
    os.makedirs(out_dir, exist_ok=True)

    user_camera = _user_camera()
    original_selection = cmds.ls(selection=True, long=True) or []
    fit_targets = list(objects) if objects else _default_fit_targets()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    frame = cmds.currentTime(q=True)
    temp_nodes = []
    images = []

    with _undo_suspended():
        try:
            panel = _create_capture_panel(width, height, display)
            if isolate and fit_targets:
                cmds.select(fit_targets, replace=True)
                cmds.isolateSelect(panel, state=True)

            for view in views:
                if view == "current":
                    cmds.lookThru(panel, user_camera)
                else:
                    ortho, rotation = _VIEWS[view]
                    cam, shape = cmds.camera(orthographic=ortho, name="mcp_capture_%s" % view)
                    temp_nodes.append(cam)
                    cmds.xform(cam, rotation=rotation, worldSpace=True)
                    cmds.setAttr(shape + ".nearClipPlane", 0.01)
                    cmds.setAttr(shape + ".farClipPlane", 1.0e6)
                    cmds.lookThru(panel, cam)
                    if fit_targets:
                        cmds.select(fit_targets, replace=True)
                        cmds.viewFit(cam, fitFactor=0.85)
                    else:
                        cmds.viewFit(cam, allObjects=True, fitFactor=0.85)
                    if ortho and fit_targets:
                        _pull_back_outside(cam, fit_targets)
                # No selection highlight in the image.
                cmds.select(clear=True)
                path = os.path.join(out_dir, "%s_%s.png" % (stamp, view)).replace("\\", "/")
                cmds.playblast(frame=[frame], format="image", compression="png", completeFilename=path,
                               widthHeight=(width, height), percent=100, viewer=False,
                               showOrnaments=False, offScreen=True, forceOverwrite=True,
                               editorPanelName=panel, clearCache=True)
                if not os.path.isfile(path):
                    raise RuntimeError("playblast did not write %s" % path)
                images.append({"view": view, "path": path,
                               "camera": user_camera if view == "current" else None})
        finally:
            _delete_capture_ui()
            if temp_nodes:
                cmds.delete([n for n in temp_nodes if cmds.objExists(n)])
            if original_selection:
                cmds.select([n for n in original_selection if cmds.objExists(n)], replace=True)
            else:
                cmds.select(clear=True)
    return {"images": images}


def _plugin_nodes(name):
    types = cmds.pluginInfo(name, q=True, dependNode=True) or []
    return cmds.ls(type=types, long=True) if types else []


def cmd_unload_plugin(name, new_scene=False, delete_nodes=False):
    name = os.path.splitext(os.path.basename(name))[0]
    if not cmds.pluginInfo(name, q=True, loaded=True):
        return {"unloaded": False, "message": "plugin %r is not loaded" % name}
    nodes = _plugin_nodes(name)
    if nodes:
        if new_scene:
            cmds.file(new=True, force=True)
        elif delete_nodes:
            cmds.delete(nodes)
        else:
            raise RuntimeError("plugin %r has %d node(s) in the scene, pass new_scene or delete_nodes: %s"
                               % (name, len(nodes), nodes[:20]))
    # The undo queue keeps references to plugin nodes/commands and blocks the unload.
    cmds.flushUndo()
    cmds.unloadPlugin(name)
    if cmds.pluginInfo(name, q=True, loaded=True):
        raise RuntimeError("plugin %r is still loaded" % name)
    return {"unloaded": True, "name": name, "deleted_nodes": len(nodes) if delete_nodes else 0,
            "new_scene": bool(nodes and new_scene)}


def cmd_load_plugin(path, new_scene=False, delete_nodes=False):
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    name = os.path.splitext(os.path.basename(path))[0]
    unloaded = None
    if cmds.pluginInfo(name, q=True, loaded=True):
        unloaded = cmd_unload_plugin(name, new_scene=new_scene, delete_nodes=delete_nodes)
    log_mark = _log_next_id
    cmds.loadPlugin(path)
    return {
        "name": name,
        "path": cmds.pluginInfo(name, q=True, path=True),
        "version": cmds.pluginInfo(name, q=True, version=True),
        "vendor": cmds.pluginInfo(name, q=True, vendor=True),
        "node_types": cmds.pluginInfo(name, q=True, dependNode=True) or [],
        "commands": cmds.pluginInfo(name, q=True, command=True) or [],
        "previous_unload": unloaded,
        "log": [e for e in _log if e["id"] >= log_mark and e["level"] in ("error", "warning", "info")],
    }


def cmd_log(last=50, levels=None, since_id=None, clear=False):
    entries = list(_log)
    if since_id is not None:
        entries = [e for e in entries if e["id"] > since_id]
    if levels:
        entries = [e for e in entries if e["level"] in levels]
    else:
        entries = [e for e in entries if e["level"] != "history"]
    entries = entries[-last:] if last else entries
    if clear:
        _log.clear()
    return {"entries": entries, "last_id": _log_next_id - 1}


def cmd_scene_info():
    counts = {t: len(cmds.ls(type=t) or []) for t in
              ("transform", "mesh", "nurbsCurve", "nurbsSurface", "joint", "camera", "light",
               "shadingEngine", "deformableShape")}
    start = cmds.playbackOptions(q=True, minTime=True)
    end = cmds.playbackOptions(q=True, maxTime=True)
    return {
        "scene": cmds.file(q=True, sceneName=True) or "untitled",
        "modified": cmds.file(q=True, modified=True),
        "maya_version": cmds.about(version=True),
        "up_axis": cmds.upAxis(q=True, axis=True),
        "linear_unit": cmds.currentUnit(q=True, linear=True),
        "current_time": cmds.currentTime(q=True),
        "playback_range": [start, end],
        "selection": (cmds.ls(selection=True, long=True) or [])[:100],
        "top_level_nodes": (cmds.ls(assemblies=True, long=True) or [])[:200],
        "counts": counts,
        "user_plugins": _user_plugins(),
    }


def cmd_reload_bridge():
    port = _server.port if _server else DEFAULT_PORT

    def reload_later():
        import importlib
        import maya_dev_bridge
        maya_dev_bridge.stop()
        importlib.reload(maya_dev_bridge)
        maya_dev_bridge.start(port)

    maya.utils.executeDeferred(reload_later)
    return {"scheduled": True, "port": port}


_HANDLERS = {
    "ping": cmd_ping,
    "exec": cmd_exec,
    "capture": cmd_capture,
    "load_plugin": cmd_load_plugin,
    "unload_plugin": cmd_unload_plugin,
    "log": cmd_log,
    "scene_info": cmd_scene_info,
    "reload_bridge": cmd_reload_bridge,
}


# --------------------------------------------------------------------------- lifecycle

def start(port=None):
    global _server
    port = int(port or os.environ.get("MAYA_DEV_MCP_PORT", DEFAULT_PORT))
    if _server is not None and _server.is_alive():
        return _server.port
    _install_log_callback()
    _server = _BridgeServer(port)
    _server.start()
    print("maya_dev_mcp: bridge %s listening on %s:%d" % (BRIDGE_VERSION, HOST, port))
    return port


def stop():
    global _server
    if _server is not None:
        _server.stop()
        _server = None
    _remove_log_callback()


def is_running():
    return _server is not None and _server.is_alive()
