# 交接说明（下一步从这里开始）

> 面向**新对话**。读完这份就能接着干，不需要翻之前的聊天记录。
> 上位文档是 [`ARCHITECTURE.md`](./ARCHITECTURE.md)，UI 细节与坑在
> [`../prototype/README.md`](../prototype/README.md)。

---

## 1. 这个项目是什么

**文齐 · WenQi**（自动文档格式处理工具），基于 `docformat-gui` v1.8.8.2（**MIT 许可，可商用**）二次开发。

核心定位：用户描述自己的文档格式要求，工具把任意 Word 文档批量套用成该格式。
公文 / 学术论文 / 法律文书是**内置好的现成答案**，不是产品主体。

**许可边界（重要）**：
- 当前基线 v1.8.8.2 是 **MIT** —— 可闭源、可商用、可改名、可卖钱，只需保留
  `LICENSE` 里的 `Copyright (c) 2025 KaguraNanaga` 与许可声明（`AboutDialog` 里也有，别删）。
- **上游 v1.8.8.3 起改为 PolyForm Noncommercial（禁商用）**，不要从上游拉新代码。
- 当前分支只基于 MIT 版二次开发；GitHub 仓库为 `Weisiren-liu/wenqi`，不添加上游 remote。

---

## 2. 当前状态

| 项 | 状态 |
|---|---|
| 上游 Pro 推广内容 | ✅ 已剔除（`PRO.md`、闲鱼二维码、`ProInfoDialog`、打包引用等） |
| UI 设计 | ✅ 已定稿（`ARCHITECTURE.md` 3.3 节），有可运行原型 |
| P0 配置路径收敛 | ✅ 已完成（`a23c3f7`，唯一实现在 `scripts/formatter.py`） |
| P1 预设注册表统一 | ✅ 已完成（`e2f837d`，schema 2 → 3） |
| 覆盖值持久化定稿 | ✅ 已定稿并实现（文档 `979f8c9`，实现随 P2） |
| P2 主页面重排 | ✅ 已完成（`306e6b3`）；窄屏自适应修复（`aa39bf2`） |
| 真实文档端到端回归 | ✅ 已建立（`e742b42`，对照 P1 之前的排版结果逐项一致） |
| P3 文档更新 | ✅ 本轮完成（状态表 / README_DEV 配置路径说明已同步） |
| 产品更名 | ✅ 文齐 · WenQi v1.9.0：窗口、品牌元数据、三平台打包名称、README、图标统一 |
| 格式感知体检 | ⬜ 未开始，**放最后**（analyzer 需接入格式参数） |

**正式代码已经过三轮改造**（P0/P1/P2 + 窄屏修复），`git log` 里一阶段一提交。

---

## 3. 已锁定的设计决定

原型评审后确认，**不要再重新讨论**：

1. **格式编辑内联进主页面**，不走弹窗。原「方案 A：编辑走弹窗」已废弃删除。
2. **活链接 + 覆盖值模型**：`显示值 = 预设值 ⊕ 覆盖值`。改某一格 = 只记该格为覆盖值，
   **预设本身不变**（所以内置格式也能安全微调）。不做"选中即复制副本"。
3. **元素参数表**，一行一个元素，**9 列**：中文字体 / 英数字体 / 字号 / 加粗 / 对齐 /
   首行缩进 / 行距 / 段前 / 段后。
4. **预设栏是带边框的滚动面板**，固定 215×400，**没有展开按钮**（边框+滚动条已足够）。
5. **出厂只有 4 个起始格式**：GB/T 公文标准 / 学术论文 / 法律文书 / **自定义格式**（默认选中）。
   用户格式从空开始攒。
6. **格式区可折叠**（点标题），折叠后摘要行仍可见；折叠状态不记忆。
7. **保留现有公文语义模型**（title / recipient / heading1-4 / body / signature / date /
   attachment / closing），本轮不做通用样式映射。
8. **窄屏参数表按优先级隐藏次要列**（2026-02 定稿）：段后 → 段前 → 压缩字体列宽，
   逐级收窄直到不被窗口边缘裁掉；被隐藏列的编辑入口固定在「高级设置」的段落间距区。
   实现唯一落在 `docformat_gui.ElementTable.COLUMN_STAGES`。
9. **覆盖值清空语义**：编辑框清空 = **回到基准值**（`set_preset_override` 对 `None`
   自动清覆盖），不是「覆盖成空值」；与「显示值 = 预设值 ⊕ 覆盖值」一致。

---

## 4. 已完成阶段（存档）与当前验证

P0/P1/P2 已按序落地，一阶段一提交；设计细节见 `ARCHITECTURE.md` 第 7/9 节与提交信息。

### 各阶段实现落点

- **P0 `a23c3f7` 配置路径收敛**：唯一实现 `scripts/formatter.py::get_config_dir()` /
  `get_config_file()`；GUI 侧 `docformat_gui._get_config_dir()` 只是薄封装。
- **P1 `e2f837d` 预设注册表统一**：内置起始格式**加载时注入**（`_inject_builtin_presets`，
  带 `is_builtin: True`）、**持久化时过滤**（`save_custom_settings`）；用户格式 =
  `config['presets']` 完整快照（uuid）；`format_document()` 统一收 `preset=` 完整 dict，
  `preset_name='custom'` 旧路径仅为兼容；schema 2 → 3。
- **P2 `306e6b3` 主页面重排**：格式编辑内联（`ElementTable` 9 列 + 预设面板
  `PresetColumn`），活链接 + 覆盖值（`preset_overrides` 字段级，对内置与用户格式统一，
  key = 预设 id）；`CustomSettingsDialog` 降为「高级设置」（页边距/表格/页码/行为/
  段落间距/结束语），联动派生规则已删。
- **窄屏修复 `aa39bf2`**：`ElementTable.COLUMN_STAGES` 自适应收窄（见第 3 节第 8 条），
  段前/段后编辑入口在「高级设置」段落间距区。
- **端到端回归 `e742b42`**：真实公文样例双侧对照 P1 之前的排版结果，语义指纹逐项一致。

### 当前验证手段

```bash
# 全量测试（60 项，含注册表/覆盖值/窄屏阶梯）
python -m pytest -q

# P2 真实 GUI 自检（34 项：启动/切换/改格/存为新格式/重启/折叠/截断）
$env:PYTHONIOENCODING='utf-8'; python prototype/_check_p2_gui.py

# 窄屏自检（15 项：1120/1000/960 无裁切、宽屏全列、段落间距区、收窄可逆）
$env:PYTHONIOENCODING='utf-8'; python prototype/_check_p3_narrow.py

# 真实 .docx 端到端回归（对照基线 09d8aa5 的智能一键处理，排版指纹逐项一致）
# 首次运行会 git worktree 检出基线到 prototype/_e2e_wt/（gitignore，保留复用）
$env:PYTHONIOENCODING='utf-8'; python prototype/_check_p3_e2e.py

# 原型窗口 / 截图
python prototype/layout_b.py
python prototype/_screenshot.py out.png
```

> 控制台是 GBK，跑含 `▸▾` 等字符的脚本前必须设 `PYTHONIOENCODING=utf-8`，否则报
> `UnicodeEncodeError`。

### 后续排期（未开始，勿抢先）

1. **产品更名已完成**：品牌元数据在 `scripts/branding.py`；源码模块名、配置目录和预设导出类型保留兼容。
2. **格式感知体检** —— 放最后：`analyze_*` 目前不接格式参数，「格式诊断」卡片文案
   刻意写成「仅分析文档问题」而不是「按上表参数体检」（照抄定稿图是虚假承诺）。
   做格式感知体检时需给 analyzer 传入生效 preset 并改卡片文案。
3. **用户文档已更新**：中英文 README 与当前 UI 对齐，说明源码运行及尚未发布安装包。

---

## 5. 仓库状态

- **origin**：`https://github.com/Weisiren-liu/wenqi.git`（公开仓库）；未配置上游 remote。
- **历史**：保留重建后的 MIT 基线与本分支改造提交；未导入上游后续版本。
- **提交者身份**：`docformat-dev <dev@localhost>`（本地配置，未设置全局）。

提交记录：

| 提交 | 内容 |
|---|---|
| `5b6d176` | init：剔除上游 Pro 推广后的 v1.8.8.2 基线 |
| `d393e46` | docs：新增架构改造方案 |
| `09d8aa5` | UI 定稿 + 界面原型 + 交接文档 |
| `a23c3f7` | P0：配置路径收敛（唯一实现 `scripts/formatter.py`） |
| `e2f837d` | P1：预设注册表统一（内置项加载时注入、持久化时过滤） |
| `979f8c9` | docs：覆盖值持久化定稿（`preset_overrides` 字段级） |
| `306e6b3` | P2：主页面重排（格式编辑内联 + 活链接覆盖值） |
| `4d609f4` | prototype：截图工具支持指定窗口标题 |
| `aa39bf2` | fix：参数表窄屏自适应（次要列按优先级隐藏，收进高级设置） |
| `e742b42` | test：真实 .docx 端到端回归（对照 P1 之前） |
| 本提交 | docs（P3）：状态表与配置路径说明同步到实际代码 |

---

## 6. 踩过的坑（原型 + 正式改造累计）

`prototype/README.md` 有原型部分的详细记录，这里只列要点：

1. **`pack_propagate(False)` 会连带锁住高度** —— 内容会被整片裁掉。
2. **`wraplength` 不约束 Label 的最小请求宽度** —— 它只管换行，长文本照样把容器撑宽。
   要控制宽度得截断显示。
3. **canvas 有默认宽度（约 378px）和默认 `highlightthickness=2`** —— 不显式设置会把内容
   拉宽、并让可视高度比内容矮几像素导致误判"可滚动"。
4. **滚动条一出现，它的宽度会加到父容器上**（pack 的布局自然如此）—— 解法是
   "滚动条占多少，canvas 就少多少"，两者互补。
5. **Win11 的 `vista` ttk 主题忽略自定义的 `foreground`/`fieldbackground`** ——
   `style.lookup()` 读得回值但原生绘制不采用，所以覆盖值提示不能靠给 Combobox 上色，
   要用行首色条或自绘控件。
6. **鼠标滚轮绑定**：只在 canvas 上绑 `<Enter>/<Leave>` 不够（鼠标移到子行上时 canvas 收到
   `Leave`），要递归绑到面板内所有控件。
7. **PowerShell 5.1 的 `Get-Content`/`Set-Content` 会毁 UTF-8 源文件**（按 cp936 误读、
   写出 BOM，`docformat_gui.py` 被毁过一次）。改 UTF-8 文本用编辑工具或 Python；
   必须用 PS 时用 `[System.IO.File]::ReadAllText/WriteAllText` + `UTF8Encoding($false)`。
8. **驱动真实 GUI 跑批处理必须跑真 `mainloop`**：`run_operation` 的工作线程经 `after()`
   投递 Tk 调用，用 `update()` 轮询代替 mainloop 会炸
   `RuntimeError: main thread is not in main loop`（见 `prototype/_check_p3_e2e.py`）。
9. **grid 布局被挤时是"所有列同比压缩"而不是裁最后一列** —— 表现为末几列被窗口边缘
   切掉（列头半字）。要"永不裁列"得按实测 `winfo_reqwidth()` 逐级收窄（`COLUMN_STAGES`）。

---

## 7. 环境

| 项 | 值 |
|---|---|
| Python | 3.14.6（`C:\Users\weisi\AppData\Local\Python\bin\python.exe`） |
| 已装 | python-docx 1.2.0、pywin32 312、lxml、Pillow、PyInstaller 6.21.0、pytest 9.1.1 |
| 未装 | `tkinterdnd2` —— 拖拽会自动降级为禁用，程序可正常运行 |
| 平台 | Windows（Tk 8.6.15，主题 `vista`） |

> `requirements-win7.txt` 锁的是 Python 3.8 环境，与当前 3.14 无关，别混用。
