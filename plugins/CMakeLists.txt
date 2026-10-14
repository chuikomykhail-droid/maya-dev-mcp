cmake_minimum_required(VERSION 3.25)
project(MayaPlugins LANGUAGES CXX)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(MayaPlugin)

# One subfolder per plugin; each calls maya_add_plugin(...).
add_subdirectory(waveDeformer)
