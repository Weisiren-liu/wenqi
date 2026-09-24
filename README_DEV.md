## 关于 custom_settings.json

仓库里这个文件是**源码运行模式（`python docformat_gui.py` / `bash install.sh`）的默认配置**，
内容与代码里的 DEFAULT_CUSTOM_SETTINGS 保持一致。

### 给开发者的提示

该文件已加入 .gitignore。**如果你在调试时通过 GUI 保存了自定义设置，会写到本地这个文件，
但 git 不会再追踪它**——这是故意的，避免脏配置被误提交。

如果你确实要修改这份"默认配置"（比如调整 DEFAULT_CUSTOM_SETTINGS 后想同步到这里），
请用 `git add -f custom_settings.json` 强制添加。

### 用户配置文件的实际位置

- Windows/Linux 打包发布版：exe 同目录
- macOS 打包发布版：~/Library/Application Support/DocFormatter/
- 开发模式（python 直接运行）：项目根目录（即这个文件本身）
