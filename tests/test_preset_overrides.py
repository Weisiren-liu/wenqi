"""P2 行为测试：活链接 + 覆盖值（preset_overrides）。

对应 docs/ARCHITECTURE.md 第 9 节定稿：
显示值 = 预设值 ⊕ 覆盖值，字段级记录，对固定起始格式与用户格式统一生效；
切换 / 重启不清空；「＋ 存为新格式」= 快照生效值并清空源格式覆盖值。
"""

import json
from copy import deepcopy

import docformat_gui
from scripts.formatter import CUSTOM_PRESET_BASE


def _fresh_config(tmp_path, monkeypatch):
    monkeypatch.setattr(docformat_gui, "CONFIG_FILE", tmp_path / "custom_settings.json")
    return docformat_gui.load_custom_settings()


def test_effective_preset_is_base_plus_overrides(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)

    base = docformat_gui.get_preset_by_id(config, "official")
    base_spacing = base["body"]["line_spacing"]

    docformat_gui.set_preset_override(config, "official", "body", "line_spacing", 30)

    # 基准不变，生效值 = 基准 ⊕ 覆盖
    assert base["body"]["line_spacing"] == base_spacing
    effective = docformat_gui.get_effective_preset(config, "official")
    assert effective["body"]["line_spacing"] == 30
    assert effective["body"]["font_cn"] == base["body"]["font_cn"]

    # 覆盖值只记被改的格子
    overrides = docformat_gui.get_preset_overrides(config, "official")
    assert overrides == {"body": {"line_spacing": 30}}


def test_override_equal_to_base_is_dropped(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    base_spacing = docformat_gui.get_preset_by_id(config, "official")["body"]["line_spacing"]

    docformat_gui.set_preset_override(config, "official", "body", "line_spacing", 30)
    docformat_gui.set_preset_override(config, "official", "body", "line_spacing", base_spacing)
    # 改回基准值 = 不再偏离，覆盖自动清除（「已改动」标记只反映真实偏离）
    assert docformat_gui.get_preset_overrides(config, "official") == {}


def test_restore_row_and_restore_all(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    docformat_gui.set_preset_override(config, "official", "body", "line_spacing", 30)
    docformat_gui.set_preset_override(config, "official", "body", "font_cn", "楷体_GB2312")
    docformat_gui.set_preset_override(config, "official", "title", "size", 18)

    docformat_gui.clear_preset_override_row(config, "official", "body")
    assert docformat_gui.get_preset_overrides(config, "official") == {"title": {"size": 18}}

    docformat_gui.clear_preset_overrides(config, "official")
    assert docformat_gui.get_preset_overrides(config, "official") == {}


def test_overrides_survive_reload(tmp_path, monkeypatch):
    """重启不丢：覆盖值、选中格式都持久化。"""
    config = _fresh_config(tmp_path, monkeypatch)
    docformat_gui.set_preset_override(config, "official", "body", "line_spacing", 30)
    config["active_preset_id"] = "official"
    docformat_gui.save_custom_settings(config)

    reloaded = docformat_gui.load_custom_settings()
    assert reloaded["active_preset_id"] == "official"
    assert docformat_gui.get_preset_overrides(reloaded, "official") == {
        "body": {"line_spacing": 30}}
    assert docformat_gui.get_effective_preset(reloaded, "official")["body"]["line_spacing"] == 30


def test_overrides_on_user_format_work_the_same(tmp_path, monkeypatch):
    """用户格式 = 不可变快照 + 覆盖值，语义与固定起始格式一致。"""
    config = _fresh_config(tmp_path, monkeypatch)
    preset = docformat_gui.save_as_new_preset(config, "custom", "我的格式 1")
    preset_id = preset["id"]

    docformat_gui.set_preset_override(config, preset_id, "title", "font_cn", "楷体_GB2312")
    docformat_gui.save_custom_settings(config)

    reloaded = docformat_gui.load_custom_settings()
    saved = docformat_gui.get_preset_by_id(reloaded, preset_id)
    # 快照本身不变
    assert saved["title"]["font_cn"] == CUSTOM_PRESET_BASE["title"]["font_cn"]
    # 生效值带覆盖
    assert docformat_gui.get_effective_preset(reloaded, preset_id)["title"]["font_cn"] == "楷体_GB2312"

    docformat_gui.clear_preset_overrides(reloaded, preset_id)
    assert (docformat_gui.get_effective_preset(reloaded, preset_id)["title"]["font_cn"]
            == CUSTOM_PRESET_BASE["title"]["font_cn"])


def test_save_as_new_preset_snapshots_effective_and_clears_source(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    docformat_gui.set_preset_override(config, "custom", "body", "line_spacing", 30)
    docformat_gui.set_preset_override(config, "custom", "title", "font_cn", "楷体_GB2312")

    new_preset = docformat_gui.save_as_new_preset(config, "custom", "我的格式 1")

    # 新格式 = 当前生效值的完整快照
    assert new_preset["body"]["line_spacing"] == 30
    assert new_preset["title"]["font_cn"] == "楷体_GB2312"
    assert new_preset["is_builtin"] is False
    # 自动选中新格式
    assert config["active_preset_id"] == new_preset["id"]
    # 源格式的覆盖值已清空（改动折进新格式）
    assert docformat_gui.get_preset_overrides(config, "custom") == {}
    # 新格式自己没有覆盖值：它的基准就是快照
    assert docformat_gui.get_preset_overrides(config, new_preset["id"]) == {}

    docformat_gui.save_custom_settings(config)
    reloaded = docformat_gui.load_custom_settings()
    saved = docformat_gui.get_preset_by_id(reloaded, new_preset["id"])
    assert saved["body"]["line_spacing"] == 30
    assert reloaded["active_preset_id"] == new_preset["id"]


def test_overrides_use_field_level_paths(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    docformat_gui.set_preset_override(config, "custom", "page", "left", 3.0)
    docformat_gui.set_preset_override(config, "custom", "deep_clean", None, True)
    docformat_gui.set_preset_override(config, "custom", "body", "font_cn", "楷体_GB2312")

    assert docformat_gui.get_preset_overrides(config, "custom") == {
        "page": {"left": 3.0},
        "deep_clean": True,
        "body": {"font_cn": "楷体_GB2312"},
    }
    effective = docformat_gui.get_effective_preset(config, "custom")
    assert effective["page"]["left"] == 3.0
    assert effective["page"]["top"] == CUSTOM_PRESET_BASE["page"]["top"]
    assert effective["deep_clean"] is True
