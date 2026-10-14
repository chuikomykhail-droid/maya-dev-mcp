# Maya 2024 C++ plugins

Plugins for Maya 2024 (Windows, MSVC x64 + Ninja), developed in VS Code and checked in a live Maya
through the `maya-dev` MCP server (`../maya_dev_mcp`).

```
plugins/
  CMakeLists.txt            # project; one add_subdirectory() per plugin
  CMakePresets.json         # presets debug / relwithdebinfo -> build/<preset>/
  cmake/MayaPlugin.cmake    # maya_add_plugin(): devkit, flags, .mll, lock check
  cmake/FindMaya.cmake      # devkit lookup (copied from FirstPlugin)
  cmake/CheckUnlocked.cmake # PRE_LINK: clear error if Maya holds the .mll
  cmake/msvc-env.json       # GENERATED, not in git: MSVC environment from vcvars64.bat
  tools/build.cmd           # one-command configure/build/clean
  tools/gen-msvc-env.ps1    # regenerates cmake/msvc-env.json
  waveDeformer/             # sample deformer + tests/test_waveDeformer.py
```

Build output: `build/<preset>/plug-ins/<name>.mll` with its `.pdb` next to it.

## Toolchain

| What | Where |
|---|---|
| MSVC 14.51 (VS 2026) | `D:\Soft\Visual Studio`, environment from `VC\Auxiliary\Build\vcvars64.bat` |
| CMake 4.3 / Ninja 1.13 | bundled with Visual Studio (not in PATH; the scripts and presets use full paths) |
| Maya devkit | `D:\Soft\Autodesk\MayaDevKit\devkitBase` (cache var `MAYA_LOCATION`) |
| Eigen | `D:\Soft\Autodesk\CppMods\eigen` (cache var `EIGEN_DIR`, added as include if present) |

Only MSVC works: MinGW/GCC binaries are not ABI compatible with Maya (the CMake module refuses them).

**Why `msvc-env.json`.** `vswhere` reports this Visual Studio only with `-prerelease`, so CMake Tools'
auto-detection is unreliable, and CMake Tools ignores kits (`environmentSetupScript`) when presets are used.
`tools/gen-msvc-env.ps1` runs `vcvars64.bat` once and stores what it changes (`INCLUDE`, `LIB`, `LIBPATH`,
PATH additions, ...) as a hidden preset `msvc-env` that `CMakePresets.json` includes. The terminal and
CMake Tools therefore get the same environment without a Developer Prompt. `tools/build.cmd` generates
the file when it is missing; regenerate it after updating Visual Studio / the Windows SDK:

```
plugins\tools\build.cmd relwithdebinfo env
```

**Debug preset** = `/Od /Ob0 /RTC1` + full PDB, but with the release CRT (`/MD`, no `_DEBUG`): Maya
ships release binaries only, and mixing in the debug CRT breaks across the API boundary.

## Build

From any terminal (no Developer Prompt):

```
plugins\tools\build.cmd                    # relwithdebinfo: configure + build
plugins\tools\build.cmd debug              # debug preset
plugins\tools\build.cmd debug build        # build only;  actions: all | configure | build | clean | env
```

Equivalent raw CMake, run in `plugins\` (cmake.exe from Visual Studio):
`cmake --workflow --preset relwithdebinfo`.

In VS Code:

- **Tasks** (`Ctrl+Shift+B` = `plugins: build (relwithdebinfo)`), plus `plugins: build (debug)`,
  `plugins: configure`, `plugins: clean`, `plugins: regenerate MSVC environment`.
- **CMake Tools** works on `plugins/` (`cmake.sourceDirectory`): pick the configure preset in the status
  bar, then Build. `.vscode/settings.json` points it at Visual Studio's cmake.exe and disables its own VS
  environment detection.

IntelliSense takes the flags from CMake Tools (fallback: `build/relwithdebinfo/compile_commands.json`);
`.vscode/c_cpp_properties.json` forces `cl.exe` / `windows-msvc-x64` over the user-level MinGW gcc.

### "<name>.mll is locked"

Windows keeps a loaded `.mll` open. Before linking, `CheckUnlocked.cmake` fails the build with:

```
waveDeformer.mll is locked and cannot be overwritten.
It is probably loaded in Maya. Unload it first: MCP unload_plugin("waveDeformer") or cmds.unloadPlugin("waveDeformer") in Maya.
```

The same check reports a `.pdb` held by an attached debugger.

## Add a plugin

1. Create `plugins/myPlugin/` with the sources and a `CMakeLists.txt`:
   ```cmake
   maya_add_plugin(myPlugin SOURCES pluginMain.cpp myNode.cpp myNode.h)
   # extra devkit libs or CMake targets:  LIBS OpenMayaUI OpenMayaRender
   ```
   Foundation, OpenMaya and OpenMayaAnim are linked by default.
2. Add `add_subdirectory(myPlugin)` to `plugins/CMakeLists.txt`.
3. Build. The result is `build/<preset>/plug-ins/myPlugin.mll`.

Notes for plugin code:
- Node IDs `0x00000000-0x0007FFFF` are Autodesk's range for local/test plugins; get a registered block
  from Autodesk before distributing. `waveDeformer` uses `0x0007F001`.
- Report with `MGlobal::displayInfo/displayWarning/displayError`, which the MCP `maya_log` tool sees.
  `std::cout` and `CHECK_MSTATUS*` go to Maya's Output Window instead, so on a failed `registerNode`
  print `status.errorString()` with `displayError` (see `waveDeformer/pluginMain.cpp`).
- Attribute short names must not clash with inherited ones. For deformers, `wl` (weightList), `en`
  (envelope), `ip` (input) and `og` (outputGeometry) are taken. A clash makes `initializePlugin` fail.
  To list them: `om.MNodeClass("weightGeometryFilter")` → `MFnAttribute(...).shortName`.

## Check in Maya (MCP `maya-dev`)

Maya must be running with the bridge (`maya_startup/userSetup.py`, port 50010).

1. `unload_plugin("waveDeformer")`. If its nodes are in the scene, use `delete_nodes=True`.
   `new_scene=True` discards the whole scene without saving.
2. Build: `plugins\tools\build.cmd`.
3. `load_plugin("D:/Claude/Maya MCP test/plugins/build/relwithdebinfo/plug-ins/waveDeformer.mll")`.
   The returned log contains `waveDeformer 0.1.0 loaded (built <date time>)`.
4. Numeric test with `execute_python`:
   ```python
   import runpy
   t = runpy.run_path(r"D:/Claude/Maya MCP test/plugins/waveDeformer/tests/test_waveDeformer.py")
   t["run"]()            # creates test_wavePlane + test_waveDeformer, checks, deletes them
   ```
   It compares every vertex with `y = envelope * A * sin(2*pi*x/wavelength + phase)` for several
   attribute sets, checks crest/trough/node vertices and the bounding box, and raises `AssertionError`
   on any mismatch.
5. `maya_log` should show no errors.
6. Visual check: `t["run"](keep=True)`, then `viewport_capture(objects=["test_wavePlane"])`, then `t["cleanup"]()`.

Maya 2024 asks **"Untrusted Plugin Loading - Security Warning"** for a plugin outside its trusted
locations (optionVar `SafeModeAllowedlistPaths`). The dialog is modal: until it is answered, Maya's main
thread and every MCP call wait. On 2026-10-13 Maya hung on it and Windows closed it. Trust is per exact
folder: `build/relwithdebinfo/plug-ins` is trusted, while `build/debug/plug-ins` is not yet, so add it via
Preferences → Security or the dialog's trust option before loading a debug build through MCP.

## Debug

`.vscode/launch.json` (`cppvsdbg`; symbols are loaded only for `*.mll` to keep it fast):

- **Attach to maya.exe**: pick `maya.exe` from the process list, load or reload the plugin, and
  breakpoints bind. Works with either preset; use `debug` for reliable stepping.
- **Launch Maya under debugger (debug build)**: builds the `debug` preset, then starts Maya.
  Close the running Maya first because the bridge port is per process. Then load
  `build/debug/plug-ins/<name>.mll`.

While a debugger is attached, it holds the `.pdb`: detach before rebuilding.
