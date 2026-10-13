"""End-to-end check of maya_dev_mcp: spawn server.py over stdio like an MCP client and call every tool."""
import asyncio
import base64
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(r"D:\Claude\Maya MCP test\maya_dev_mcp")
PARAMS = StdioServerParameters(command=str(ROOT / ".venv/Scripts/python.exe"), args=[str(ROOT / "server.py")])
OUT = Path(r"D:\Claude\Maya MCP test\tests\out")


async def call(session, tool, **args):
    res = await session.call_tool(tool, args)
    print(f"--> {tool}({ {k: (v if len(str(v)) < 80 else str(v)[:80] + '...') for k, v in args.items()} })"
          f"{'  [isError]' if res.is_error else ''}")
    for c in res.content:
        if c.type == "text":
            print("    " + c.text[:1500].replace("\n", "\n    "))
        elif c.type == "image":
            OUT.mkdir(exist_ok=True)
            path = OUT / f"{tool}_{len(list(OUT.iterdir()))}.png"
            path.write_bytes(base64.b64decode(c.data))
            print(f"    image {c.mime_type} -> {path}")
    return res


async def main():
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            await call(session, "scene_info")
            await call(session, "execute_python", code="x = 21\nprint('hello from', cmds.about(version=True))\nx * 2")
            await call(session, "execute_python", code="x + 1")  # namespace persists
            await call(session, "execute_python", code='s = "quotes \\" and \\n newlines \' ok"\nlen(s)')
            await call(session, "execute_python", code="1/0")
            await call(session, "execute_python", code=(
                "cmds.file(new=True, force=True)\n"
                "c = cmds.polyCube(name='box', w=2, h=1, d=1)[0]\n"
                "cmds.move(0, 0.5, 0, c)\n"
                "s = cmds.polySphere(name='ball', r=0.6)[0]\n"
                "cmds.move(2.5, 0.6, 0, s)\n"
                "cmds.warning('test warning from mcp')\n"
                "cmds.exactWorldBoundingBox(c)"))
            await call(session, "maya_log", last=5, levels=["warning", "error"])
            await call(session, "viewport_capture")
            await call(session, "viewport_capture", views=["persp"], objects=["ball"],
                       display="wireOnShaded", width=640, height=480)
            await call(session, "load_plugin", path=r"D:\Soft\Autodesk\Maya2024\bin\plug-ins\nearestPointOnMesh.mll")
            await call(session, "execute_python", code="cmds.createNode('nearestPointOnMesh')")
            await call(session, "unload_plugin", name="nearestPointOnMesh")
            await call(session, "unload_plugin", name="nearestPointOnMesh", delete_nodes=True)


asyncio.run(main())

