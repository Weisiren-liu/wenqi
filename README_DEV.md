# 文齐 · WenQi 开发者说明

名称、版本与地址集中于 `scripts/branding.py`，GUI 和打包工具共享。源码入口保留 `docformat_gui.py`，打包产物以 `wenqi_` 开头。图标使用 `assets/icon.*`。为兼容已有设置，仍使用历史 `DocFormatter` 配置目录。

## 液态玻璃界面

Python 3.9+ 的默认入口会启动 `scripts/desktop_ui.py` 中的 pywebview 桌面壳，加载仓库内的 `ui/index.html`、`styles.css`、`app.js`。文件和参数通过本地 Python 桥接读写，文档不会发送到远程服务。Windows 使用 WebView2；Mac 使用 WKWebView；Linux 使用 WebKitGTK。Python 3.8 的 Win7 兼容构建保留原 Tk 界面；调试旧界面也可设置 `WENQI_LEGACY_UI=1`。

配置模型仍使用 `docformat_gui.py` 的预设注册表及覆盖值方法，新界面修改与原有配置兼容。不要让新界面直接修改 `PRESETS` 或往磁盘写入内置格式。

真实界面验证：`python prototype/_check_glass_ui.py`。它隔离配置、验证浏览器桥接、内联参数编辑、文件拖拽的 DOM/桥接路径、真实 `.docx` 处理与结果展示，并抓取桌面及窄窗口截图到 `prototype/_glass_shots/`。合成拖拽使用预置的本地路径缓存，操作系统提供文件句柄的部分需要手动拖入文件检查。

打包后验证：先安装开发辅助依赖 `python -m pip install websockets`，再运行 `python prototype/_check_glass_exe.py`。它在独立临时配置目录中启动真实 EXE，仅给该测试进程设置 WebView2 调试端口，检查界面、玻璃材质、全部设置页及实际文档输出，并抓取打包版截图。日常启动不会开启调试端口。

Windows 窗口验证：`python prototype/_check_window_controls.py`。检查最大化与任务栏工作区、反复还原尺寸、最小化后恢复，以及真实鼠标拖动四边/四角、点击窗口按钮和双击标题栏。测试会短暂移动鼠标，仅点击自己的窗口，结束后恢复原位置。

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
