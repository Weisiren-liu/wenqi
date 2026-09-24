"""
_split_heading_by_punct 相关测试。
v1.7.1: 默认关闭该拆分，避免破坏用户故意写成一行的合法段落
（如 "1. 第一阶段：完成xxx。"）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_split_heading_function_still_exists():
    """_split_heading_by_punct 函数本身不应被删除，只是默认不调用。"""
    from scripts.formatter import _split_heading_by_punct
    assert callable(_split_heading_by_punct)


def test_default_preset_does_not_split():
    """所有内置预设默认不应启用 split_heading_at_punct。"""
    from scripts.formatter import PRESETS
    for name, preset in PRESETS.items():
        # 字段不存在视为 False，存在则必须为 False
        assert not preset.get('split_heading_at_punct', False), \
            f'preset {name} should not enable split_heading_at_punct by default'
