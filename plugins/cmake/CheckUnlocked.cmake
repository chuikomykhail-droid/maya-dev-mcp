# PRE_LINK step of maya_add_plugin: stop the build with a readable message when the output .mll
# is loaded in Maya (or the .pdb is held by a debugger) instead of a bare LNK1104/LNK1201.
#   cmake -DMLL=<file.mll> -DPDB=<file.pdb> -DPLUGIN=<name> -P CheckUnlocked.cmake
#
# file(LOCK) raises a hard error when it cannot open the file, so the probe runs in a child
# cmake (-DPROBE=<file>) and only its exit code is used here.

if(DEFINED PROBE)
    file(LOCK "${PROBE}" GUARD PROCESS TIMEOUT 0)
    return()
endif()

function(_check_unlocked file hint)
    if(NOT file OR NOT EXISTS "${file}")
        return()
    endif()
    execute_process(
        COMMAND "${CMAKE_COMMAND}" "-DPROBE=${file}" -P "${CMAKE_CURRENT_LIST_FILE}"
        RESULT_VARIABLE result
        OUTPUT_QUIET ERROR_QUIET)
    if(NOT result EQUAL 0)
        get_filename_component(file_name "${file}" NAME)
        message(FATAL_ERROR "\n"
            "  ${file_name} is locked and cannot be overwritten.\n"
            "  ${hint}\n"
            "  File: ${file}\n")
    endif()
endfunction()

_check_unlocked("${MLL}"
    "It is probably loaded in Maya. Unload it first: MCP unload_plugin(\"${PLUGIN}\") or cmds.unloadPlugin(\"${PLUGIN}\") in Maya.")
_check_unlocked("${PDB}"
    "It is probably held by a debugger attached to Maya. Stop/detach the debugger, then rebuild.")
