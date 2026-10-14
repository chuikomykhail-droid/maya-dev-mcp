@echo off
rem Configure and/or build the Maya plugins with a CMake preset (MSVC x64 + Ninja).
rem No Developer Prompt needed: the MSVC environment comes from cmake\msvc-env.json.
rem
rem   tools\build.cmd [preset] [action]
rem     preset: relwithdebinfo (default) | debug
rem     action: all (default: configure + build) | configure | build | clean | env (regenerate msvc-env.json)
setlocal
set "PLUGINS_DIR=%~dp0.."
if not defined MAYA_PLUGINS_CMAKE set "MAYA_PLUGINS_CMAKE=D:\Soft\Visual Studio\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"

set "PRESET=%~1"
if "%PRESET%"=="" set "PRESET=relwithdebinfo"
set "ACTION=%~2"
if "%ACTION%"=="" set "ACTION=all"

if /i "%ACTION%"=="env" goto :gen_env
if not exist "%PLUGINS_DIR%\cmake\msvc-env.json" call :gen_env || exit /b 1

set "CMAKE_ARGS="
if /i "%ACTION%"=="all"       set "CMAKE_ARGS=--workflow --preset %PRESET%"
if /i "%ACTION%"=="configure" set "CMAKE_ARGS=--preset %PRESET%"
if /i "%ACTION%"=="build"     set "CMAKE_ARGS=--build --preset %PRESET%"
if /i "%ACTION%"=="clean"     set "CMAKE_ARGS=--build --preset %PRESET% --target clean"
if not defined CMAKE_ARGS (
    echo Unknown action "%ACTION%". Use: all ^| configure ^| build ^| clean ^| env
    exit /b 2
)

pushd "%PLUGINS_DIR%" || exit /b 1
"%MAYA_PLUGINS_CMAKE%" %CMAKE_ARGS%
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" echo [build.cmd] %ACTION% (%PRESET%) FAILED with exit code %RC%
exit /b %RC%

:gen_env
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0gen-msvc-env.ps1"
exit /b %ERRORLEVEL%
