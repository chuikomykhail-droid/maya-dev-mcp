# Shared setup for Maya 2024 C++ plugins (Windows, MSVC).
#
#   include(MayaPlugin)
#   maya_add_plugin(myPlugin SOURCES pluginMain.cpp myNode.cpp [LIBS OpenMayaUI OpenMayaRender])
#
# Builds <build>/plug-ins/myPlugin.mll (+ .pdb), linked to Foundation, OpenMaya and OpenMayaAnim
# plus any extra LIBS (devkit library names or CMake targets).
include_guard(GLOBAL)

if(NOT MSVC)
    message(FATAL_ERROR
        "Maya plugins must be built with MSVC: MinGW/GCC binaries are not ABI compatible with Maya.\n"
        "Configure with a preset from plugins/CMakePresets.json, e.g. tools\\build.cmd relwithdebinfo")
endif()

set(MAYA_LOCATION "D:/Soft/Autodesk/MayaDevKit/devkitBase" CACHE PATH "Maya devkit root (devkitBase)")
set(EIGEN_DIR "D:/Soft/Autodesk/CppMods/eigen" CACHE PATH "Eigen root (the folder that contains Eigen/)")

find_package(Maya)
if(NOT MAYA_FOUND)
    message(FATAL_ERROR "Maya devkit not found: MAYA_LOCATION='${MAYA_LOCATION}' must contain include/maya/MFn.h and lib/Foundation.lib")
endif()

set(_MAYA_PLUGIN_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(MAYA_PLUGIN_DEFAULT_LIBS Foundation OpenMaya OpenMayaAnim)

function(maya_add_plugin name)
    cmake_parse_arguments(ARG "" "" "SOURCES;LIBS" ${ARGN})
    if(NOT ARG_SOURCES)
        message(FATAL_ERROR "maya_add_plugin(${name}): SOURCES is required")
    endif()

    add_library(${name} SHARED ${ARG_SOURCES})

    # Maya ships release-runtime binaries only, so even Debug builds use /MD (no _DEBUG, no debug CRT);
    # Debug differs by /Od and full debug info.
    set_target_properties(${name} PROPERTIES
        PREFIX ""
        SUFFIX ".mll"
        CXX_STANDARD 17
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
        MSVC_RUNTIME_LIBRARY "MultiThreadedDLL"
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/plug-ins"
        PDB_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/plug-ins")

    target_compile_definitions(${name} PRIVATE
        NT_PLUGIN REQUIRE_IOSTREAM _BOOL NOMINMAX _USE_MATH_DEFINES
        # Keeps the plugin working if an older msvcp140.dll than the toolset's gets loaded.
        _DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR)
    target_compile_options(${name} PRIVATE /utf-8 /Zc:__cplusplus)

    target_include_directories(${name} SYSTEM PRIVATE "${MAYA_INCLUDE_DIR}")
    if(EXISTS "${EIGEN_DIR}/Eigen")
        target_include_directories(${name} SYSTEM PRIVATE "${EIGEN_DIR}")
    endif()

    foreach(lib IN LISTS MAYA_PLUGIN_DEFAULT_LIBS ARG_LIBS)
        if(TARGET ${lib})
            target_link_libraries(${name} PRIVATE ${lib})
        elseif(EXISTS "${MAYA_LIBRARY_DIR}/${lib}.lib")
            target_link_libraries(${name} PRIVATE "${MAYA_LIBRARY_DIR}/${lib}.lib")
        else()
            target_link_libraries(${name} PRIVATE ${lib})
        endif()
    endforeach()

    # Windows keeps a loaded .mll (and a .pdb held by a debugger) locked; fail early with a clear message.
    add_custom_command(TARGET ${name} PRE_LINK
        COMMAND "${CMAKE_COMMAND}"
            "-DMLL=$<TARGET_FILE:${name}>"
            "-DPDB=$<TARGET_PDB_FILE:${name}>"
            "-DPLUGIN=${name}"
            -P "${_MAYA_PLUGIN_CMAKE_DIR}/CheckUnlocked.cmake"
        VERBATIM)
endfunction()
