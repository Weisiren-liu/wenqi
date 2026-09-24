"""无头自检：验证 layout_b 的默认状态、预设列、覆盖值模型与折叠行为。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'prototype'))

from layout_b import (PrototypeLayoutB, STARTING_FORMATS, CUSTOM_FORMATS)
import docformat_gui as gui


def cell_text(app, element, field):
    _widget, var = app.table.cells[(element, field)]
    return var.get()


def visible_rows(app):
    """返回左列当前被布局管理的格式行 id。"""
    return [fid for fid, row in app.preset_column.rows.items()
            if row.winfo_manager() == 'pack']


app = PrototypeLayoutB()
app.withdraw()
app.update_idletasks()
app.update()

failures = []

print('1) 默认态：格式区展开、预设面板为滚动面板')
if app.format_collapsed:
    failures.append('格式区启动时应为展开状态')
if app.format_body.winfo_manager() != 'pack':
    failures.append('展开状态下 format_body 应处于 pack')
if app.collapse_toggle.cget('text') != '▾':
    failures.append('展开时箭头应为 ▾')
# 面板高度必须有上限，否则内容会把它撑高、滚动永远不会发生
canvas_height = app.preset_column.canvas.winfo_height()
if canvas_height > 500:
    failures.append('预设面板高度没有上限（%d），滚动会形同虚设' % canvas_height)
if app.preset_column.winfo_height() > 620:
    failures.append('预设列整体过高：%d' % app.preset_column.winfo_height())
print('   格式区展开=%s 面板 %dx%d 参数表高 %d'
      % (not app.format_collapsed, app.preset_column.canvas.winfo_width(),
         canvas_height, app.table.winfo_height()))

print('2) 预设面板：出厂只有 %d 个起始格式，用户格式从空开始'
      % len(STARTING_FORMATS))
rows = visible_rows(app)
expected = [f[0] for f in STARTING_FORMATS]
if rows != expected:
    failures.append('可见行不符：%s（期望 %s）' % (rows, expected))
if CUSTOM_FORMATS:
    failures.append('CUSTOM_FORMATS 应当是空的（不预置演示数据）')
if app.preset_column.custom_formats:
    failures.append('预设列不该自带用户格式')
if app.preset_column.empty_hint.winfo_manager() != 'pack':
    failures.append('没有用户格式时应显示空状态提示')
if hasattr(app.preset_column, 'more_btn'):
    failures.append('不该再有 more_btn 展开按钮')
if hasattr(app.preset_column, 'expanded'):
    failures.append('不该再有 expanded 折叠状态')
print('   可见行=%s 空状态提示=显示 无展开按钮=%s'
      % (rows, not hasattr(app.preset_column, 'more_btn')))

print('3) 面板有边框；内容装得下时滚动条隐藏')
if app.preset_column.panel.cget('bg') != gui.Theme.BORDER:
    failures.append('面板没有用主题边框色画边框')
if int(app.preset_column.panel.cget('padx')) < 1:
    failures.append('面板边框厚度不足')
if app.preset_column._content_overflows():
    failures.append('只有 4 行时不该溢出')
if app.preset_column.scrollbar.winfo_manager():
    failures.append('内容装得下时滚动条应隐藏')
print('   边框色=%s 内容h=%d 视口h=%d 滚动条=隐藏'
      % (app.preset_column.panel.cget('bg'),
         app.preset_column.list_area.winfo_height(),
         app.preset_column.canvas.winfo_height()))

print('4) 加满格式 → 面板宽度不变、滚动条出现、能滚')
panel_width = app.preset_column.panel.winfo_width()
for index in range(12):
    app.preset_column.add('probe_%d' % index, '格式 %d' % index)
app.update_idletasks()
app.update()
if app.preset_column.panel.winfo_width() != panel_width:
    failures.append('加格式后面板宽度变了：%d -> %d'
                    % (panel_width, app.preset_column.panel.winfo_width()))
if not app.preset_column._content_overflows():
    failures.append('内容变多后应溢出')
if app.preset_column.scrollbar.winfo_manager() != 'pack':
    failures.append('溢出时滚动条应显示')
app.preset_column.canvas.yview_moveto(1.0)
app.update_idletasks()
if app.preset_column.canvas.yview()[0] <= 0.0:
    failures.append('面板内滚动无效')

print('5) 长格式名会被截断，且不把面板撑宽')
long_name = '这是一个特别特别特别长的格式名称用来测试会不会把面板撑宽'
app.preset_column.custom_formats = (app.preset_column.custom_formats
                                    + (('probe_long', long_name),))
long_row = app.preset_column.add('probe_long', long_name)
app.update_idletasks()
app.update()
shown = long_row.title.cget('text')
if shown == long_name:
    failures.append('超长格式名未被截断')
if not shown.endswith('…'):
    failures.append('截断后应带省略号，实际：%r' % shown)
if app.preset_column.panel.winfo_width() != panel_width:
    failures.append('超长名把面板撑宽了：%d -> %d'
                    % (panel_width, app.preset_column.panel.winfo_width()))
print('   %r -> %r 面板宽 %d（未变）滚动条=pack' % (long_name[:12], shown, panel_width))

# 复位，后面的检查基于干净状态
app.preset_column.custom_formats = app.preset_column.custom_formats[:0]
for format_id in list(app.preset_column.rows):
    if format_id.startswith('probe_'):
        app.preset_column.rows.pop(format_id)
app.preset_column._layout()
app.preset_column.canvas.yview_moveto(0.0)
app.update_idletasks()
app.update()
if app.preset_column.canvas.winfo_height() != int(app.preset_column._viewport_height):
    failures.append('面板高度被内容改变了')

print('6) 起始格式默认选中「自定义格式」，装载公文参数')
if app.state.preset_id != 'custom':
    failures.append('默认起始格式应为 custom')
if cell_text(app, 'body', 'font_cn') != '仿宋_GB2312':
    failures.append('自定义格式的 body.font_cn 应为 仿宋_GB2312')
if cell_text(app, 'title', 'font_cn') != '方正小标宋简体':
    failures.append('自定义格式的 title.font_cn 应为 方正小标宋简体')
print('   起始=%s 正文中文=%s 标题中文=%s'
      % (app.state.preset_id, cell_text(app, 'body', 'font_cn'),
         cell_text(app, 'title', 'font_cn')))

print('7) 段前 / 段后 两列可读写')
if cell_text(app, 'body', 'space_before') != '0':
    failures.append('body.space_before 初始值应为 0')
app.select_format('academic')
app.update_idletasks()
if cell_text(app, 'heading1', 'space_before') != '6':
    failures.append('academic 的 heading1.space_before 应为 6')
app.cell_changed('heading1', 'space_after', 9)
app.update_idletasks()
if cell_text(app, 'heading1', 'space_after') != '9':
    failures.append('段后改 9 未生效')
app.state.restore_all()
app.refresh()
print('   academic heading1 段前=%s 段后=%s'
      % (cell_text(app, 'heading1', 'space_before'),
         cell_text(app, 'heading1', 'space_after')))

print('8) 存一个格式再点它 → 参数装载 + 其他行全部取消选中')
saved_id = 'probe_saved'
app.preset_column.add(saved_id, '我的格式')
app.select_format(saved_id)
app.update_idletasks()
if app.state.preset_id != saved_id:
    failures.append('未切换到我的格式')
selected = [fid for fid, row in app.preset_column.rows.items() if row.selected]
if selected != [saved_id]:
    failures.append('选中态不唯一：%s' % selected)
if app.state.override_count() != 0:
    failures.append('切换格式后覆盖值应清空')
print('   当前=%s 唯一选中=%s' % (app.state.preset_id, selected))

print('9) 改一格 → 覆盖值 + 行首色条 + 顶部汇总')
app.select_format('academic')
app.update_idletasks()
app.cell_changed('body', 'font_cn', '楷体_GB2312')
app.update_idletasks()
if app.state.override_count() != 1:
    failures.append('改一格后覆盖数应为 1')
if app.table.bars['body'].cget('bg') != gui.Theme.PRIMARY:
    failures.append('body 行首色条未亮起')
if app.table.bars['title'].cget('bg') == gui.Theme.PRIMARY:
    failures.append('未改动的 title 行色条不该亮起')
if '正文·中文字体' not in app.summary.cget('text'):
    failures.append('顶部汇总未列出改动字段')
print('   覆盖数=%d 色条=%s 摘要=%r'
      % (app.state.override_count(), app.table.bars['body'].cget('bg'),
         app.summary.cget('text')))

print('10) 格式区折叠 / 展开（摘要行必须始终可见）')
app.toggle_format_area()
app.update_idletasks()
if app.format_body.winfo_manager() != '':
    failures.append('折叠后 format_body 不该被布局管理')
if app.collapse_toggle.cget('text') != '▸':
    failures.append('折叠后箭头未变为 ▸')
if not app.summary.winfo_manager():
    failures.append('折叠后摘要行不应消失')
app.toggle_format_area()
app.update_idletasks()
if app.format_body.winfo_manager() != 'pack':
    failures.append('展开后 format_body 未恢复 pack')
print('   折叠→%r 展开→%s' % ('', app.format_body.winfo_manager()))

print('11) 存为新格式 → 追加进面板并滚到可见位置')
before = len(app.preset_column.custom_formats)
app.save_as_new_format()
app.update_idletasks()
if len(app.preset_column.custom_formats) != before + 1:
    failures.append('存为新格式后我的格式未增加')
if app.state.preset_id not in app.preset_column.rows:
    failures.append('新增的格式未出现在预设列中')
if app.preset_column.canvas.yview()[0] <= 0.0:
    failures.append('新增后未滚到可见位置')
print('   我的格式数量=%d 当前=%s yview=%s'
      % (len(app.preset_column.custom_formats), app.state.preset_id,
         tuple(round(v, 3) for v in app.preset_column.canvas.yview())))

print('12) 起始格式清单应为 4 项且含自定义格式')
ids = [p[0] for p in STARTING_FORMATS]
if ids != ['official', 'academic', 'legal', 'custom']:
    failures.append('起始格式清单不符：%s' % ids)
print('   起始格式: %s' % ids)

print('13) 恢复本行 / 恢复全部 / 反复切换')
app.select_format('academic')
app.update_idletasks()
app.cell_changed('body', 'font_cn', '楷体_GB2312')
app.restore_row('body')
app.update_idletasks()
if cell_text(app, 'body', 'font_cn') != '宋体':
    failures.append('恢复后 body.font_cn 应回到 宋体')
app.cell_changed('body', 'line_spacing', 30)
app.cell_changed('heading1', 'bold', True)
app.cell_changed('signature', 'align', 'center')
app.update_idletasks()
if app.state.override_count() != 3:
    failures.append('三处改动后覆盖数应为 3')
app.restore_all()
app.refresh()
app.update_idletasks()
if app.state.override_count() != 0:
    failures.append('恢复全部后覆盖数应为 0')
if cell_text(app, 'body', 'line_spacing') != '22':
    failures.append('恢复全部后 body.line_spacing 应回到 22')
for preset in ('official', 'legal', 'custom', 'academic', saved_id):
    app.select_format(preset)
    app.update_idletasks()
if app.state.override_count() != 0:
    failures.append('反复切换后覆盖值未清空')
print('   覆盖数=%d 行距=%s 最终=%s'
      % (app.state.override_count(), cell_text(app, 'body', 'line_spacing'),
         app.state.preset_id))

app.destroy()
print()
if failures:
    print('失败项:')
    for item in failures:
        print('  -', item)
    sys.exit(1)
print('全部自检通过')
