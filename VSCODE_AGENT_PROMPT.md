# Промпт для Claude-агента в VS Code

Открой в VS Code папку `D:\Claude\Maya MCP test` (File → Open Folder) и скопируй в чат Claude всё, что ниже линии.

---

Это мой проект для разработки под Autodesk Maya 2024 с помощью LLM. В нём уже есть MCP-сервер для связи с Maya, а теперь я хочу писать здесь C++ плагины в VS Code. Сначала изучи проект и окружение, потом покажи план и только после моего «ок» вноси изменения.

## Правила работы
1. Прочитай `SESSION_RULES.md` и `CHANGELOG_ACTIONS.md` в корне и соблюдай их. Если коротко:
   - всё, что скачиваешь или создаёшь, клади внутрь этого проекта, а не во временные папки на диске C;
   - каждое изменение записывай в `CHANGELOG_ACTIONS.md`: что сделано, где лежит и как откатить; изменения вне проекта — отдельно, с шагом отката.
2. Перед установкой расширений и программ или изменением глобальных настроек спроси меня.
3. Папка `D:\Soft\Autodesk\OpenMayaProjects\FirstPlugin` — это другой мой плагин. Используй её только как образец рабочих настроек сборки, ничего в ней не меняй. Если что-то оттуда нужно (например `cmake/FindMaya.cmake`), скопируй в этот проект и запиши в журнал.

## Что уже есть в проекте
- `maya_dev_mcp\` — мой MCP-сервер для Maya (подробности в его `README.md`). Инструменты: `execute_python` (любой Python в Maya, `cmds`/`om`/`mel` уже импортированы), `viewport_capture` (снимок вьюпорта, несколько ракурсов), `load_plugin` / `unload_plugin`, `maya_log` (ошибки и предупреждения Script Editor), `scene_info`, `reload_bridge`. Мост в Maya стартует из `maya_startup\userSetup.py` и слушает 127.0.0.1:50010.
- `MayaMCP\` — сторонний MCP (PatrickPalmer/MayaMCP), оставлен для сравнения, в работе не нужен.
- `.mcp.json` — оба сервера (`maya-dev` и `MayaMCP`) уже прописаны. Пользуйся `maya-dev`.
- `tests\` — сквозные тесты MCP.

## Проверенное окружение
- Maya 2024: `D:\Soft\Autodesk\Maya2024\bin\maya.exe`, `mayapy.exe` (Python 3.10).
- Maya devkit: `D:\Soft\Autodesk\MayaDevKit\devkitBase` (`include\`, `lib\`, `cmake\`). Eigen: `D:\Soft\Autodesk\CppMods\eigen`.
- Компилятор: Visual Studio в `D:\Soft\Visual Studio`, MSVC `14.51.36231`, `cl.exe` в `D:/Soft/Visual Studio/VC/Tools/MSVC/14.51.36231/bin/Hostx64/x64/`. Окружение задаёт `D:\Soft\Visual Studio\VC\Auxiliary\Build\vcvars64.bat`.
- CMake и Ninja встроены в студию: `D:/Soft/Visual Studio/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe` и `.../CMake/Ninja/ninja.exe`. В PATH их нет.
- `vswhere.exe` эту установку VS не находит, поэтому автопоиск компилятора в CMake Tools может не сработать. Задай окружение явно: пользовательским kit с `environmentSetupScript` на `vcvars64.bat` или через `cmd /c "call vcvars64.bat && ..."` в tasks. Выбери надёжный вариант и проверь его.
- Для Maya нужен только MSVC: MinGW-сборки с Maya не совместимы по ABI.
- Рабочий образец сборки: `D:\Soft\Autodesk\OpenMayaProjects\FirstPlugin\CMakeLists.txt` и `cmake\FindMaya.cmake` (Ninja, RelWithDebInfo, `NT_PLUGIN`, `REQUIRE_IOSTREAM`, линковка Foundation / OpenMaya / OpenMayaAnim, суффикс `.mll`).

## Что нужно сделать
1. **Структура для C++ плагинов.** Создай `plugins\` с общим `CMakeLists.txt`, где каждый плагин — своя подпапка через `add_subdirectory`. Общие вещи (поиск devkit, флаги, суффикс `.mll`) вынеси в один cmake-модуль, чтобы новый плагин добавлялся парой строк.
2. **CMakePresets.json** для MSVC + Ninja: Debug и RelWithDebInfo, сборка в `plugins\build\<preset>`, `CMAKE_EXPORT_COMPILE_COMMANDS=ON`. Сборка должна работать и из VS Code (CMake Tools, `cmake.sourceDirectory` → `plugins`), и из терминала одной командой.
3. **IntelliSense.** Настрой `.vscode/settings.json` (и `c_cpp_properties.json`, если нужен), чтобы заголовки Maya и Eigen находились и не было ошибок-призраков. Python-интерпретатор для `maya_dev_mcp` — его `.venv`. Предложи `.vscode/extensions.json` (CMake Tools, C/C++, Python), но ставить расширения без моего согласия не надо.
4. **Задачи (`.vscode/tasks.json`):** configure, build, clean. Сборка должна падать с понятной ошибкой, если `.mll` заблокирован загруженной Maya.
5. **Отладка (`.vscode/launch.json`):** `cppvsdbg` с «attach to maya.exe» и вариант «запустить Maya под отладчиком». Нужна сборка с pdb.
6. **Первый тестовый плагин для проверки цикла:** простой деформер (например, синусоидальная волна вдоль оси с атрибутами amplitude / wavelength) в `plugins\waveDeformer\`. Используй `MGlobal::displayInfo` при загрузке, чтобы это было видно в `maya_log`.
7. **Проверка всего цикла через MCP `maya-dev`:**
   `unload_plugin` → сборка → `load_plugin(<путь к .mll>)` → через `execute_python` создать тестовый меш `test_*`, навесить деформер, проверить результат числами (смещение конкретных вершин против формулы, bounding box) → `maya_log` без ошибок → `viewport_capture` для визуальной проверки → убрать тестовые объекты.
   Windows блокирует загруженный `.mll`, поэтому перед пересборкой всегда выгружай плагин. Если в сцене есть ноды плагина, используй `delete_nodes=True`, а `new_scene=True` — только с моего согласия: он сбрасывает сцену без сохранения.
   Если Maya не отвечает, попроси меня её запустить, сам не запускай.
8. **Документация.** `plugins\README.md`: как добавить новый плагин, собрать, отладить и прогнать проверку в Maya.

## Как работать дальше
- Изменения в плагинах проверяй числами через `execute_python`. `viewport_capture` используй как контрольную визуальную проверку, а не после каждого шага.
- Вывод плагина смотри через `maya_log`: `std::cout` уходит в Output Window Maya, а не в лог.
- Не трогай мою открытую сцену без спроса: работай со своими объектами `test_*` и убирай их за собой.

В конце дай краткий отчёт: что настроено, какие файлы появились, что проверено и с каким результатом, что не получилось.
