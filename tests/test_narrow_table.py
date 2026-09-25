"""窄屏参数表自适应：次要列（段前/段后）按优先级隐藏，编辑入口收进「高级设置」。

背景：1120px 窗口下参数表请求宽度 884px > 可用 840px，末两列曾被窗口
边缘裁掉（列头「段后」直接切没）。修法是 COLUMN_STAGES 逐级收窄：
先隐藏次要列，还不够再压缩字体列宽；隐藏列的字段在「高级设置」的
段落间距区始终可编辑。
"""

from pathlib import Path

import docformat_gui as gui


PROJECT_ROOT = Path(__file__).parent.parent


def _stage_fields():
    return [field for field, _label, _width in gui.ElementTable.COLUMNS]


def test_stage_ladder_hides_secondary_columns_by_priority():
    """收窄阶梯：段后先于段前隐藏，字体类主列永不隐藏。"""
    stages = gui.ElementTable.COLUMN_STAGES
    fields = _stage_fields()

    # 第 0 级 = 全列展示
    assert stages[0]['hide'] == ()
    assert stages[0]['widths'] == {}

    for stage in stages:
        for field in stage['hide']:
            assert field in fields, f'隐藏列 {field} 不在 COLUMNS 里'
        assert set(stage['hide']) <= {'space_before', 'space_after'}, \
            '次要列只允许是段前/段后（其余列另有编辑入口，不许静默隐藏）'

    # 段后（最次要）先于段前被隐藏
    for stage in stages:
        if 'space_before' in stage['hide']:
            assert 'space_after' in stage['hide']

    # 阶梯单调：越往下隐藏越多、列宽只减不增
    prev_hidden, prev_widths = set(), {}
    for stage in stages:
        hidden = set(stage['hide'])
        assert prev_hidden <= hidden, '收窄阶梯的隐藏集必须单调扩大'
        for field, width in prev_widths.items():
            assert stage['widths'].get(field, _base_width(field)) <= width, \
                f'{field} 列宽在阶梯里必须单调不增'
        prev_hidden = hidden
        prev_widths = {
            field: stage['widths'].get(field, _base_width(field))
            for field in fields if field not in hidden
        }


def _base_width(field):
    return dict((f, w) for f, _l, w in gui.ElementTable.COLUMNS)[field]


def test_hidden_spacing_columns_keep_edit_home_in_advanced_dialog():
    """被隐藏列的字段必须有固定编辑入口（高级设置 · 段落间距区）。"""
    source = (PROJECT_ROOT / "docformat_gui.py").read_text(encoding="utf-8")
    assert "段落间距" in source
    assert "_build_spacing_grid" in source
    assert "_spacing_vars" in source

    dialog = gui.CustomSettingsDialog
    assert hasattr(dialog, "_parse_spacing")

    # 段落间距区逐行覆盖参数表全部元素
    grid_source = source.split("def _build_spacing_grid", 1)[1].split("def ", 1)[0]
    assert "enumerate(ELEMENTS)" in grid_source


def test_spacing_inputs_treat_blank_as_clear():
    """空输入 = 清空该格（None = 回到基准值），整数化整、小数保留、垃圾输入不落覆盖。"""
    parse = gui.CustomSettingsDialog._parse_spacing
    assert parse('') is None
    assert parse('   ') is None
    assert parse(None) is None
    assert parse('abc') is None
    assert parse('0') == 0
    assert parse('3') == 3
    assert parse('2.5') == 2.5

    # 参数表单元格同一语义
    assert gui.ElementTable._as_number('') is None
    assert gui.ElementTable._as_number('30') == 30
    assert gui.ElementTable._as_number('x', 28) == 28


def test_spacing_override_roundtrip_uses_field_level_model():
    """段落间距区写的是字段级覆盖值，与基准一致时自动不记。"""
    config = {
        'schema_version': gui.CONFIG_SCHEMA_VERSION,
        'active_preset_id': 'custom',
        'presets': [],
    }
    gui._inject_builtin_presets(config)   # 与 load_custom_settings 同路径
    gui.set_preset_override(config, 'custom', 'body', 'space_before', 6)
    assert gui.get_preset_overrides(config, 'custom') == {'body': {'space_before': 6}}

    # 写回基准值自动清除
    base = gui.get_preset_by_id(config, 'custom')
    gui.set_preset_override(config, 'custom', 'body', 'space_before',
                            base.get('body', {}).get('space_before'))
    assert gui.get_preset_overrides(config, 'custom') == {}

    # 编辑框清空（None）= 回到基准值，同样只清不记
    gui.set_preset_override(config, 'custom', 'body', 'space_after', 12)
    gui.set_preset_override(config, 'custom', 'body', 'space_after', None)
    assert gui.get_preset_overrides(config, 'custom') == {}
