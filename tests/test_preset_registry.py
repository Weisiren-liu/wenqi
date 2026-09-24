"""P0 行为测试：配置路径收敛。

对应 docs/HANDOFF.md 第 4 节 P0 的验收标准：
GUI 与 formatter 两侧解析出同一个配置文件路径，写入/读取命中同一文件。
"""

from copy import deepcopy

import docformat_gui
from scripts import formatter


def _make_user_preset(preset_id, name):
    preset = deepcopy(docformat_gui.DEFAULT_CUSTOM_SETTINGS)
    preset.update({"id": preset_id, "name": name})
    return preset


def test_gui_and_formatter_read_the_same_config_file(tmp_path, monkeypatch):
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(formatter.sys, "platform", "win32")

    gui_dir = docformat_gui._get_config_dir()
    assert gui_dir == formatter.get_config_dir()
    assert gui_dir == appdata / "DocFormatter"
    assert formatter.get_config_file() == gui_dir / "custom_settings.json"

    # GUI 写、formatter 读 —— 必须命中同一个文件
    monkeypatch.setattr(docformat_gui, "CONFIG_FILE", formatter.get_config_file())
    preset = _make_user_preset("shared-1", "两侧共享")
    preset["page"] = {"top": 1.1, "bottom": 1.2, "left": 1.3, "right": 1.4}
    docformat_gui.save_custom_settings({
        "schema_version": docformat_gui.CONFIG_SCHEMA_VERSION,
        "active_preset_id": "shared-1",
        "presets": [preset],
    })

    loaded_by_formatter = formatter.load_custom_preset()
    assert loaded_by_formatter is not None
    assert loaded_by_formatter["id"] == "shared-1"
    assert loaded_by_formatter["page"]["left"] == 1.3
