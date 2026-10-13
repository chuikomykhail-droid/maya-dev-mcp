"""End-to-end check: start MayaMCP over stdio like an MCP client would, list tools, call a few in Maya."""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = r"D:\Claude\Maya MCP test\MayaMCP"
PARAMS = StdioServerParameters(
    command=ROOT + r"\.venv\Scripts\python.exe",
    args=[ROOT + r"\src\maya_mcp_server.py"],
)


async def call(session, tool, **args):
    res = await session.call_tool(tool, args)
    text = " ".join(c.text for c in res.content if hasattr(c, "text"))
    print(f"--> {tool}({args})\n    {text[:400]}")


async def main():
    async with stdio_client(PARAMS) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            for step in sys.argv[1:] or ["list"]:
                if step == "list":
                    await call(session, "list_objects_by_type", filter_by="cameras")
                elif step == "build":
                    await call(session, "create_object", object_type="cube", name="mcp_test_cube2")
                    await call(session, "set_object_transform_attributes", object_name="mcp_test_cube2",
                               translate=[0.0, 2.0, 0.0])
                    await call(session, "create_advanced_model", model_type="chair", name="mcp_chair",
                               translate=[4.0, 0.0, 0.0])
                    await call(session, "create_material", material_type="chrome", assign_to="mcp_test_cube2")
                    await call(session, "viewport_focus", object_name="")
                    await call(session, "list_objects_by_type", filter_by="shapes")


asyncio.run(main())


