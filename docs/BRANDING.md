# 文齐 · WenQi 品牌资源

名称取“文档整齐、格式统一”的意思。产品名称、版本与地址由 `scripts/branding.py` 统一提供。

## 图标

图标使用内置 image_gen 工具生成，设计为朱砂色圆角底、暖白折角纸张，以及左侧对齐的标题与正文线条。完整生成提示词如下：

```text
Use case: logo-brand. Asset type: Windows/macOS/Linux desktop application icon for 文齐 (WenQi), an offline Word document formatting utility. Create one polished square app icon, front-facing flat vector-like illustration with crisp geometric edges. A terracotta red rounded-square tile carries a warm ivory sheet of paper with a folded upper-right corner. On the paper show three clear dark-teal horizontal typesetting lines with a common left edge and deliberate equal spacing; one short red heading line above them. The form should evoke neat aligned documents, restrained editorial stationery and warm paper. Strong simple silhouette, generous margins, recognizable at 32px. No lettering, no words, no initials, no watermark, no pencil, no sparkles, no additional objects, no perspective mockup. Transparent background outside the rounded square tile. Centered single icon, square image.
```

生成原图保存在 `assets/wenqi-icon-source.png`；应用使用 `assets/icon.png` 和 `assets/icon_square.png`（1024 × 1024）。`assets/icon.ico` 提供 16、24、32、48、64、128、256 像素版本，`assets/icon.icns` 用于 macOS 打包。转换保留透明通道。

新图标用于主窗口、主界面标题、Windows 可执行文件、macOS 应用和 Linux AppImage。README 使用新图标和当前主界面的真实截图。

生成日期：2026-10-12。视觉检查 MCP 服务因认证错误未能完成图像内容复核；尺寸、透明通道和容器格式已通过程序检查。

## 兼容标识

源码入口 `docformat_gui.py`、用户配置目录 `DocFormatter`、导出类型 `docformat-preset` 与内部类名保留兼容。用户可见名称与打包产物改为 WenQi；历史架构说明中的旧名称作为设计记录保留。旧版宣传横幅不再用于 README。
