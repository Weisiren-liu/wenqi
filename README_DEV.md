# 开发者说明

## 配置文件 custom_settings.json 在哪

路径由**唯一实现** `scripts/formatter.py::get_config_dir()` 决定（P0 收敛后，
GUI 侧 `docformat_gui._get_config_dir()` 只是薄封装，不再各自做平台判断）：

| 平台 | 位置 |
|---|---|
| Windows（打包版与源码运行一致） | `%APPDATA%\DocFormatter\custom_settings.json` |
| macOS | `~/Library/Application Support/DocFormatter/custom_settings.json` |
| Linux | `$XDG_CONFIG_HOME/DocFormatter/custom_settings.json`（缺省 `~/.config/...`） |
| 极端情况（用户目录不可写） | 回退到可执行文件同目录 |

> 历史说明：旧版 Windows 打包版写 exe 同目录、源码运行写项目根目录。P0 起统一写
> 用户配置目录——放 exe 同目录时，装进 Program Files 会逼用户用管理员运行，
> 而管理员模式下资源管理器拖文件会被系统拦截，拖拽功能直接失效。
> `formatter.load_custom_preset()` 仍保留一轮兼容回退（新位置没配置时读项目根目录的
> 旧 `custom_settings.json`）；GUI 主路径不走该回退，确认无人再用旧布局后可删。

## schema 与内容（当前 schema = 3）

- **内置起始格式不落盘**：`official / academic / legal / custom` 在加载时注入
  （`docformat_gui._inject_builtin_presets`，定义只来自 `scripts/formatter.py`），
  `save_custom_settings` 持久化时过滤 `is_builtin`。
- **用户格式**：`config['presets']` 里的完整快照（uuid）。
- **覆盖值**：`config['preset_overrides']`，字段级，key = 预设 id
  （`显示值 = 预设值 ⊕ 覆盖值`，见 `docs/ARCHITECTURE.md` 第 9 节）。

## 给开发者的提示

- 项目根目录的 `custom_settings.json`（如果有）是本地调试产物，已在 `.gitignore` 里，
  不要提交。
- 调试 GUI 时想隔离配置：启动前改 `docformat_gui.CONFIG_FILE` 指到临时路径
  （`prototype/_check_p2_gui.py` 等自检脚本就是这么做的）。
- 改 UTF-8 源文件**不要用 PowerShell 5.1 的 `Get-Content`/`Set-Content`**（按 cp936
  误读、写出 BOM，会毁中文注释）；用编辑工具或 Python。
