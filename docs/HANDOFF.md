# 交接说明（下一步从这里开始）

> 面向**新对话**。读完这份就能接着干，不需要翻之前的聊天记录。
> 上位文档是 [`ARCHITECTURE.md`](./ARCHITECTURE.md)，UI 细节与坑在
> [`../prototype/README.md`](../prototype/README.md)。

---

## 1. 这个项目是什么

**自动文档格式处理工具**，基于 `docformat-gui` v1.8.8.2（**MIT 许可，可商用**）二次开发。

核心定位：用户描述自己的文档格式要求，工具把任意 Word 文档批量套用成该格式。
公文 / 学术论文 / 法律文书是**内置好的现成答案**，不是产品主体。

**许可边界（重要）**：
- 当前基线 v1.8.8.2 是 **MIT** —— 可闭源、可商用、可改名、可卖钱，只需保留
  `LICENSE` 里的 `Copyright (c) 2025 KaguraNanaga` 与许可声明（`AboutDialog` 里也有，别删）。
- **上游 v1.8.8.3 起改为 PolyForm Noncommercial（禁商用）**，不要从上游拉新代码。
- 仓库已 `git init` 重建，无 remote，历史干净（见第 5 节）。

---

## 2. 当前状态

| 项 | 状态 |
|---|---|
| 上游 Pro 推广内容 | ✅ 已剔除（`PRO.md`、闲鱼二维码、`ProInfoDialog`、打包引用等） |
| UI 设计 | ✅ 已定稿（`ARCHITECTURE.md` 3.3 节），有可运行原型 |
| 正式代码 | ⬜ **一个字都没改**，仍是上游 v1.8.8.2 原样 |
| 配置层统一（P0/P1） | ⬜ 未开始 |
| 主页面重排（P2） | ⬜ 未开始 |
| 文档更新（P3） | ⬜ 未开始 |

`git status` 应显示只有 `prototype/` 未跟踪（或已提交，见第 5 节）。

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

---

## 4. 下一步做什么

按 `ARCHITECTURE.md` 第 7 节，**建议先做 P0 + P1**（不碰 UI，可测试，且是 P2 的前提）。

### P0 — 配置路径收敛

**问题**：配置文件的目录解析有两份独立实现，纯属重复：
- `docformat_gui.py` 的 `_get_config_dir()`（约 389 行）
- `scripts/formatter.py` 的 `load_custom_preset()`（约 272 行）—— 自己又写了一遍平台判断

当前两边结果恰好一致，但任一侧单独改动就会分叉。

**做法**：把 `get_config_dir()` 迁入 `formatter.py` 作为唯一实现，GUI 反过来 import 它
（现有依赖方向是 GUI → formatter，不新增反向依赖）。

**验收**：两侧读到同一文件；39 个原有测试全通过。

### P1 — 预设注册表统一

**问题**：现在有**三套互不相干的预设体系**（`ARCHITECTURE.md` 2.1 节详述）：
- `formatter.PRESETS`（硬编码 official/academic/legal，不在用户配置里）
- `config['presets']`（用户自建格式，带 uuid）
- 主页面硬编码的卡片元组

后果很具体：**用户在设置里新建的格式，在主页面根本看不到**。
`format_document()` 内部还用 `preset_name == 'custom'` 这个字符串魔法值分流两条代码路径。

另有死代码：`BUILTIN_PRESET_IDS`（`docformat_gui.py` 约 554 行）**定义后全项目从未引用**；
`is_builtin` 被写入 8 处、只被读 1 次。**原作者已在往统一注册表方向走但没走完**，
顺着补完即可，不用推倒重来。

**做法**（`ARCHITECTURE.md` 3.1 / 3.2 节）：
- 内置预设**加载时注入**注册表（带 `is_builtin: True`，id 沿用 `'official'` 等字符串），
  **持久化时过滤掉** —— 避免内置定义随代码演进时污染用户配置
- `active_preset_id` 允许指向内置 id（当前 `load_custom_settings()` 会校验并重置）
- `format_document()` 统一接收完整 preset dict，保留 `preset_name` 仅为兼容旧调用
  （现有测试大量使用 `format_document(..., 'official')`）
- schema `2 → 3`

**验收**：新增注册表测试 + 迁移测试通过；**原 39 个测试全通过**；升级后用户原有预设不丢、
默认选中格式不变。

### P2 — 主页面重排

按 `ARCHITECTURE.md` 3.3 节定稿图实现，对照 `prototype/layout_b.py` 逐项复核。

**核心工作**：把 `CustomSettingsDialog`（一个 1600×1100 的弹窗，约 1500 行）里的编辑控件
改造成内联面板。注意该弹窗的**快速设置是按控件意图分组 + 联动派生**的（正文字体同时写入
recipient/signature/date，heading3/4 跟正文联动，英文/数字字体是全局的），
而新设计是**按元素逐行独立编辑** —— 这个取舍已在原型阶段确认，联动规则不再保留。

**必须回答的遗留问题**：覆盖值要不要**持久化**？原型里只在内存。建议存到配置文件的
独立字段 `builtin_overrides`，理由与结构见 `ARCHITECTURE.md` 第 9 节末尾。

### 可用的验证手段

```bash
# 原有测试（pytest 已装）
python -m pytest -q                    # 应 39 passed

# 原型的无头自检（13 项，覆盖预设面板/覆盖值/折叠）
$env:PYTHONIOENCODING='utf-8'; python prototype/_check_b.py

# 原型窗口
python prototype/layout_b.py

# 截图（高 DPI 下也能正确取全窗口）
python prototype/_screenshot.py out.png
```

> 控制台是 GBK，跑含 `▸▾` 等字符的脚本前必须设 `PYTHONIOENCODING=utf-8`，否则报
> `UnicodeEncodeError`。

---

## 5. 仓库状态

- **无 remote**：上游 remote 已删，避免误拉 PolyForm 代码（v1.8.8.3+）。
- **历史干净**：`.git` 已删除重建，1 个初始提交，0 个 tag，无 PolyForm 历史残留。
- **提交者身份**：`docformat-dev <dev@localhost>`（本地配置，未设置全局）。

提交记录（本对话产出）：

| 提交 | 内容 |
|---|---|
| `5b6d176` | init：剔除上游 Pro 推广后的 v1.8.8.2 基线 |
| `d393e46` | docs：新增架构改造方案 |
| 见 `git log` | prototype：界面原型与自检脚本（若已提交） |

---

## 6. 原型里踩过的坑（P2 会再踩一次）

`prototype/README.md` 有详细记录，这里只列要点：

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

---

## 7. 环境

| 项 | 值 |
|---|---|
| Python | 3.14.6（`C:\Users\weisi\AppData\Local\Python\bin\python.exe`） |
| 已装 | python-docx 1.2.0、pywin32 312、lxml、Pillow、PyInstaller 6.21.0、pytest 9.1.1 |
| 未装 | `tkinterdnd2` —— 拖拽会自动降级为禁用，程序可正常运行 |
| 平台 | Windows（Tk 8.6.15，主题 `vista`） |

> `requirements-win7.txt` 锁的是 Python 3.8 环境，与当前 3.14 无关，别混用。
