# 文齐 · WenQi

<p align="center"><img src="assets/icon.png" alt="文齐图标" width="128"></p>
<p align="center"><strong>让文档格式整齐一致。</strong></p>
<p align="center">自定义 Word 格式 · 批量排版 · 标点修复 · 本地处理</p>
<p align="center"><a href="README_EN.md">English</a> · <a href="README_DEV.md">开发说明</a> · <a href="https://github.com/Weisiren-liu/wenqi/issues">问题反馈</a></p>

文齐是一个基于 Python / Tkinter 的 Word 文档格式处理工具。以自定义格式或内置预设为起点，直接在主界面调整字体、字号、加粗、对齐、缩进、行距与段落间距，再批量应用到文档。

本项目基于 KaguraNanaga 的 `docformat-gui` **MIT 版 v1.8.8.2** 二次开发，保留原始版权与许可声明。本分支完成了配置路径统一、预设注册表整合、主界面重排、窄屏适配，以及 WenQi 更名与图标重绘。

## 界面

![文齐主界面](assets/screenshot.png)

## 能力与边界

- **格式直接编辑**：主标题、主送机关、一级至四级标题、正文、落款、日期和附件可分别设置中英文字体等参数。
- **格式预设**：自定义格式默认选中，另有公文、学术论文、法律文书起始预设。修改值与预设分开保存，可恢复单行或全部参数，也可存为新格式。
- **高级设置**：页边距、页码样式与位置、表格、段落间距，以及样式清洗等行为。
- **批量处理**：多选文件或选择文件夹，统一输出；也可粘贴文本生成 `.docx`。
- **三种处理方式**：智能处理（修标点并应用格式）、格式诊断（只出报告）、仅修标点（保留原有排版）。
- **中文排版**：标点规范化、中文禁则、标题识别、页码和表格调整，保留内嵌图片及附件媒体节点。
- **处理修订**：可输出修订标记，供 Word 中复核格式变化。
- **离线运行**：文档处理在本地完成，无文档上传、遥测或后台网络请求。

当前段落识别仍以中文公文元素为基础，论文和法律预设提供的是排版起点。**格式诊断尚未按当前自定义参数逐项校验**。处理结果需要人工复核，字体缺失、复杂表格和特殊结构可能影响最终效果。

## 运行

当前仓库提供源码，预编译安装包尚未发布。后续安装包将在 [Releases](https://github.com/Weisiren-liu/wenqi/releases) 提供。

推荐 Python 3.11 或更高版本：

```bash
git clone https://github.com/Weisiren-liu/wenqi.git
cd wenqi
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python docformat_gui.py
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python docformat_gui.py
```

Linux 需要系统 Tk 支持，例如 Debian / Ubuntu 的 `python3-tk`。也可在项目目录执行 `bash install.sh`，由安装助手创建环境并启动。

| 平台 | 文档支持 |
|---|---|
| Windows | `.docx`；`.doc` / `.wps` 转换需本机 Microsoft Office 或 WPS Office |
| macOS / Linux | `.docx`；其他格式请先转换 |

`.docx` 处理无需安装 Microsoft Word。请安装所选中文字体；字体回退可能改变外观。拖拽依赖 `tkinterdnd2`，未安装时仍可用按钮选择文件；macOS 打包版当前关闭拖拽。

## 使用

1. 选择输入文件（支持多选）和输出位置。
2. 在“文档格式”中选择起始格式，直接修改参数；更多选项在“高级设置”。
3. 选择处理方式，点击“开始处理”。
4. 复核输出文件，默认在原文件旁生成带 `_processed` 后缀的新文件。

格式和修改值重启后继续保留。为兼容已有设置，更名后仍使用 `DocFormatter` 用户配置目录，详见 [开发说明](README_DEV.md)。

## 开发与打包

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip install pyinstaller
python build.py windows   # 在对应系统运行 windows / linux / macos
```

产物以 `wenqi_` 开头，如 `wenqi_windows.exe`。GitHub Actions 支持手动构建；推送 `v*` 标签会构建并发布多平台包。Windows 7 兼容构建使用 Python 3.8 和 `requirements-win7.txt`，macOS 签名与公证需自行配置仓库密钥。

GUI 在 `docformat_gui.py`，排版核心在 `scripts/formatter.py`，诊断在 `scripts/analyzer.py`，Windows 转换在 `scripts/converter.py`。品牌信息集中于 `scripts/branding.py`。详细设计见 [架构说明](docs/ARCHITECTURE.md)。

## 许可与来源

[MIT License](LICENSE) 允许使用、修改和分发，包括商业用途；分发时须保留原始版权与许可声明。原作者：**KaguraNanaga**。二次开发与维护：**Weisiren-liu**。本项目基线为上游 MIT 版 v1.8.8.2。

参见 [第三方依赖](THIRD_PARTY_LICENSES.md)、[隐私与免责声明](DISCLAIMER.md)、[品牌资源](docs/BRANDING.md)。反馈请提交 [Issue](https://github.com/Weisiren-liu/wenqi/issues)。
