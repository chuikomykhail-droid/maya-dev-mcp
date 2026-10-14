# Loaded by Maya via PYTHONPATH set in Documents\maya\2024\Maya.env.
# Starts the socket bridge for maya_dev_mcp (maya_dev_mcp/maya_side/maya_dev_bridge.py).
import sys

import maya.utils

MAYA_DEV_MCP_SIDE = r"D:\Claude\Maya MCP test\maya_dev_mcp\maya_side"


def _start_maya_dev_bridge():
    if MAYA_DEV_MCP_SIDE not in sys.path:
        sys.path.append(MAYA_DEV_MCP_SIDE)
    import maya_dev_bridge
    maya_dev_bridge.start()


maya.utils.executeDeferred(_start_maya_dev_bridge)
