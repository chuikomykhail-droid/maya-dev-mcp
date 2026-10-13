# Loaded by Maya via PYTHONPATH set in Documents\maya\2024\Maya.env.
# 1) MEL command port for PatrickPalmer/MayaMCP (src/maya_mcp_server.py, DEFAULT_COMMAND_PORT).
# 2) Socket bridge for maya_dev_mcp (maya_dev_mcp/maya_side/maya_dev_bridge.py).
import sys

import maya.cmds as cmds
import maya.utils

MCP_PORT_NAME = "localhost:50007"
MAYA_DEV_MCP_SIDE = r"D:\Claude\Maya MCP test\maya_dev_mcp\maya_side"


def _open_mcp_port():
    if not cmds.commandPort(MCP_PORT_NAME, query=True):
        cmds.commandPort(name=MCP_PORT_NAME, sourceType="mel")
        print("MayaMCP: command port opened on " + MCP_PORT_NAME)


def _start_maya_dev_bridge():
    if MAYA_DEV_MCP_SIDE not in sys.path:
        sys.path.append(MAYA_DEV_MCP_SIDE)
    import maya_dev_bridge
    maya_dev_bridge.start()


maya.utils.executeDeferred(_open_mcp_port)
maya.utils.executeDeferred(_start_maya_dev_bridge)
