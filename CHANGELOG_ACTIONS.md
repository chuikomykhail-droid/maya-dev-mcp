# Журнал действий (для последующей очистки)

## 2026-10-13 — установка MayaMCP и подключение к Maya 2024

### Создано внутри проекта `D:\Claude\Maya MCP test\`
| Путь | Что это |
|---|---|
| `SESSION_RULES.md` | правила сессии |
| `CHANGELOG_ACTIONS.md` | этот журнал |
| `MayaMCP\` | `git clone https://github.com/PatrickPalmer/MayaMCP` |
| `MayaMCP\.venv\` | виртуальное окружение Python 3.12 (из `D:\Soft\miniconda`), пакет `mcp==1.30.0` (~60 МБ) |
| `MayaMCP\requirements.txt` | **изменён**: `mcp` → `mcp<2` (проект несовместим с mcp 2.x, где удалён `mcp.server.fastmcp`) |
| `MayaMCP\src\maya_mcp_server.log` | лог MCP-сервера (создаётся сервером при запуске) |
| `maya_startup\userSetup.py` | при старте Maya открывает MEL commandPort `localhost:50007` |
| `.mcp.json` | регистрация MCP-сервера `MayaMCP` для Claude Code (project scope) |
| `tests\e2e_mcp_test.py` | сквозной тест: MCP-клиент → сервер → Maya |
| `backup_Maya.env.orig` | резервная копия исходного Maya.env (был пустой, 0 байт) |

### Изменено ВНЕ проекта
| Путь | Изменение | Как откатить |
|---|---|---|
| `C:\Users\chyck\OneDrive\Documents\maya\2024\Maya.env` | добавлена строка `PYTHONPATH=D:\Claude\Maya MCP test\maya_startup` | удалить эту строку (или скопировать `backup_Maya.env.orig` обратно) |

Побочный эффект: **pip-кэш** при установке пишется в `C:\Users\chyck\AppData\Local\pip\cache` (стандартное поведение pip; можно очистить `pip cache purge`).

### Изменения в сцене Maya (тест, не сохранялись)
Созданы `mcp_test_cube`, `mcp_test_cube2`, `mcp_chair_*`, материалы `chrome_mat_*` — в несохранённой сцене.

## 2026-10-13 — собственный сервер maya-dev-mcp

### Создано внутри проекта
| Путь | Что это |
|---|---|
| `maya_dev_mcp\server.py` | MCP-сервер (mcp 2.x): execute_python, viewport_capture, load/unload_plugin, maya_log, scene_info, reload_bridge |
| `maya_dev_mcp\maya_side\maya_dev_bridge.py` | мост внутри Maya: TCP `127.0.0.1:50010`, выполнение в главном потоке |
| `maya_dev_mcp\README.md`, `requirements.txt`, `.gitignore` | документация и зависимости |
| `maya_dev_mcp\.venv\` | окружение Python 3.12: `mcp==2.3.0`, `pillow==12.3.0` (~89 МБ) |
| `maya_dev_mcp\captures\` | снимки вьюпорта (хранятся последние 40, удаляются автоматически) |
| `tests\e2e_dev_mcp.py` | сквозной тест maya-dev-mcp |

### Изменено
| Путь | Изменение |
|---|---|
| `maya_startup\userSetup.py` | теперь ещё и запускает `maya_dev_bridge` (порт 50010) |
| `.mcp.json` | добавлен сервер `maya-dev` |

Вне проекта ничего нового не менялось (pip-кэш — см. выше).

### Сцена Maya (тест, не сохранялась)
Тест делает `file -new -force` и создаёт `box`, `ball`; загружал/выгружал штатный плагин `nearestPointOnMesh.mll`.

## 2026-10-13 — промпт для VS Code
| Путь | Что это |
|---|---|
| `VSCODE_AGENT_PROMPT.md` | промпт для Claude-агента в VS Code: разработка C++ плагинов в этом проекте (`plugins\`), MCP maya-dev; FirstPlugin — только образец |

`D:\Soft\Autodesk\OpenMayaProjects\FirstPlugin` только прочитан, ничего не менялось.

## 2026-10-13 — git-репозиторий
| Путь | Что это | Как откатить |
|---|---|---|
| `.git\` | `git init -b main`, remote `origin` = https://github.com/chuikomykhail-droid/maya-dev-mcp | удалить папку `.git\` |
| `.gitignore` | исключены `MayaMCP\` (чужой клон со своим `.git`), `.venv\`, `__pycache__\`, `captures\`, `*.log`, `plugins\build\`, `*.orig` | удалить файл |

Вне проекта: первый коммит запушен в ветку `main` на GitHub (откат — удалить ветку/репозиторий на GitHub). Глобальный git-конфиг не менялся.

## 2026-10-13 — C++ плагины в VS Code (`plugins\`)

### Создано внутри проекта
| Путь | Что это | Как откатить |
|---|---|---|
| `plugins\CMakeLists.txt`, `plugins\CMakePresets.json` | общий проект, presets `debug` / `relwithdebinfo` (MSVC + Ninja, `build\<preset>`) | удалить |
| `plugins\cmake\FindMaya.cmake` | **копия** `D:\Soft\Autodesk\OpenMayaProjects\FirstPlugin\cmake\FindMaya.cmake` (оригинал не тронут) | удалить |
| `plugins\cmake\MayaPlugin.cmake` | `maya_add_plugin()` — devkit, флаги, `.mll`, проверка блокировки | удалить |
| `plugins\cmake\CheckUnlocked.cmake` | PRE_LINK: понятная ошибка, если `.mll`/`.pdb` заняты | удалить |
| `plugins\cmake\msvc-env.json` | **генерируется** `tools\gen-msvc-env.ps1` из `vcvars64.bat`; не в git | удалить (пересоздаётся `tools\build.cmd`) |
| `plugins\tools\build.cmd`, `plugins\tools\gen-msvc-env.ps1` | сборка одной командой, генерация окружения MSVC | удалить |
| `plugins\waveDeformer\` | тестовый деформер (синусоида по X → смещение Y) + `tests\test_waveDeformer.py` | удалить |
| `plugins\README.md` | документация | удалить |
| `plugins\build\` | артефакты сборки (`.mll`, `.pdb`, `.obj`), ~10 МБ; не в git | удалить папку |
| `.vscode\settings.json`, `c_cpp_properties.json`, `tasks.json`, `launch.json`, `extensions.json` | настройки VS Code **только для этой папки** (workspace) | удалить `.vscode\` |
| `.gitattributes` | CRLF для `*.cmd`/`*.bat` | удалить |
| `.gitignore` | + `plugins/cmake/msvc-env.json` | убрать строку |

Вне проекта ничего не менялось: глобальные настройки VS Code (включая `C_Cpp.default.compilerPath` = gcc и MinGW-kit CMake Tools) не тронуты — workspace-настройки их перекрывают. Расширения не ставились (CMake Tools, C/C++, Python уже были установлены).

### Сцена Maya
`load_plugin` для `waveDeformer.mll` из `plugins\build\` вызвал модальный диалог Maya «Untrusted Plugin Loading - Security Warning» (плагин вне доверенных путей) — до ответа на него Maya и MCP-мост ждут. В 23:29 Windows зафиксировал зависание (AppHangB1) и закрыл maya.exe; несохранённая тестовая сцена (`box`, `ball` от прошлых тестов) потеряна. Код плагина при этом не выполнялся.

2026-10-14: пользователь перезапустил Maya. Мост `userSetup.py` не стартовал сам: машинная переменная `PYTHONPATH=D:\Sumo\SUMO\tools\` имеет приоритет над `Maya.env`, и `maya_startup` в путь не попадает. Мост запущен вручную из Script Editor. **Не исправлено**, нужно решение пользователя (см. отчёт).
Пользователь добавил в доверенные пути Maya (optionVar `SafeModeAllowedlistPaths`, вне проекта) папку `D:/Claude/Maya MCP test/plugins/build/relwithdebinfo/plug-ins`. Откат: Preferences → Security → удалить путь.
Исправлен `waveDeformer`: короткое имя `wl` конфликтовало с `weightList`, заменено на `wvl`. Цикл unload → build → load → тест пройден дважды. Объекты `test_*` удалены, плагин выгружен, сцена пользователя (`pSphere1`) не тронута. Побочный эффект `unload_plugin`: очищена история undo.

## 2026-10-14 — репозиторий только про maya-dev-mcp, удалён сторонний MayaMCP
| Что | Изменение | Как откатить |
|---|---|---|
| `MayaMCP\` (клон PatrickPalmer/MayaMCP + `.venv` ~75 МБ + лог) | **удалён** по просьбе пользователя; перед этим остановлены его процессы MCP-сервера (PID 11112, 19820) | `git clone https://github.com/PatrickPalmer/MayaMCP`, venv заново, в `requirements.txt` `mcp<2` |
| `.mcp.json` | убран сервер `MayaMCP`, остался `maya-dev` | вернуть блок из git-истории (`69b91da`) |
| `maya_startup\userSetup.py` | убран MEL commandPort `localhost:50007` (нужен был только MayaMCP), остался запуск моста | из git-истории |
| `tests\e2e_mcp_test.py` | удалён (тест MayaMCP) | из git-истории |
| `maya_dev_mcp\README.md` → `README.md` | README сервера перенесён в корень репозитория, добавлены структура репо и раздел про `plugins\` (тестовые плагины) | `git mv` обратно |
| `.gitignore` | убрана строка `MayaMCP/` | — |

`VSCODE_AGENT_PROMPT.md` не менялся (исторический промпт, в нём ещё упоминается MayaMCP).

### Полная очистка
1. Удалить строку `PYTHONPATH=...` из `Maya.env`.
2. Удалить папку `D:\Claude\Maya MCP test\`.
3. (опц.) `pip cache purge`.
