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

### Полная очистка
1. Удалить строку `PYTHONPATH=...` из `Maya.env`.
2. Удалить папку `D:\Claude\Maya MCP test\`.
3. (опц.) `pip cache purge`.
