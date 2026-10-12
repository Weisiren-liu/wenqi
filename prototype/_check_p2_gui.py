#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 真实 GUI 自检：直接驱动正式版主窗口（docformat_gui.DocFormatApp）。

覆盖验收项（docs/HANDOFF.md P2 + 本次约束）：
  1. 启动 —— 默认选中「自定义格式」，预设面板出厂 4 个起始格式 + 空状态提示
  2. 切换三种起始格式（official / academic / legal），参数表跟随装载
  3. 改一格 —— 覆盖值记录、行首色条亮起、摘要列出改动
  4. 「＋ 存为新格式」—— 新格式进面板并自动选中，源格式覆盖值清空
  5. 重启（销毁根窗口后重建）—— 新格式与参数都不丢
  6. 格式区折叠 / 展开
  7. 原型不变量：预设面板视口 400px、用户格式名截断

用法：$env:PYTHONIOENCODING='utf-8'; python prototype/_check_p2_gui.py
截图输出到 prototype/_p2_shots/。
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import tkinter as tk                                    # noqa: E402
from tkinter import simpledialog, messagebox            # noqa: E402

import docformat_gui as gui                             # noqa: E402

SHOTS = os.path.join(HERE, '_p2_shots')
CONFIG = os.path.join(SHOTS, 'custom_settings.json')
SHOTS_TAKEN = []


def shot(root, name):
    """抓一张真实窗口截图（PrintWindow，高 DPI 也取全窗口）。"""
    try:
        import time
        from _screenshot import capture, find_window
        windows = find_window('文齐 · WenQi')
        if not windows:
            print('  [跳过截图] 未找到窗口:', name)
            return
        hwnd, _title = windows[0]
        try:
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        root.update_idletasks()
        root.update()
        time.sleep(0.6)          # 等重绘稳定再取图
        root.update()
        path = os.path.join(SHOTS, name)
        capture(hwnd, path)
        SHOTS_TAKEN.append(path)
        print('  [截图]', path)
    except Exception as e:
        print('  [跳过截图]', name, '->', e)


def build_app():
    root = tk.Tk()
    gui._configure_tk_high_dpi(root)
    app = gui.DocFormatApp(root)
    root.update()
    return root, app


def main():
    if os.path.isdir(SHOTS):
        import shutil
        shutil.rmtree(SHOTS)
    os.makedirs(SHOTS)

    # 隔离配置 + 静音弹窗（驱动里所有交互走真实处理函数）
    gui.CONFIG_FILE = gui.Path(CONFIG)
    gui.DocFormatApp._maybe_show_community_notice = lambda self: None
    saved_names = iter(['我的格式 1'])
    simpledialog.askstring = lambda *a, **k: next(saved_names, None)
    messagebox.showinfo = lambda *a, **k: print('  [弹窗]', a[1] if len(a) > 1 else '')
    messagebox.showwarning = lambda *a, **k: print('  [警告]', a[1] if len(a) > 1 else '')

    failures = []

    def check(label, cond, detail=''):
        status = 'PASS' if cond else 'FAIL'
        print(f'[{status}] {label}' + (f' —— {detail}' if detail and not cond else ''))
        if not cond:
            failures.append(label)

    root = app = None
    try:
        # ---------- 1. 启动 ----------
        print('\n== 1. 启动 ==')
        root, app = build_app()
        check('默认选中「自定义格式」', app.preset.get() == 'custom', app.preset.get())
        summary = app.format_summary.cget('text')
        check('摘要行显示当前格式', '自定义格式' in summary and '未做修改' in summary, summary)
        rows = app.preset_column.rows
        check('出厂 4 个起始格式', list(rows) == ['official', 'academic', 'legal', 'custom'],
              str(list(rows)))
        check('空状态提示可见', bool(app.preset_column.empty_hint.winfo_manager()))
        check('预设面板视口 400px',
              int(app.preset_column.canvas.cget('height')) == int(gui.ui_px(400)),
              str(app.preset_column.canvas.cget('height')))
        shot(root, '01_startup.png')

        # ---------- 2. 切换三种起始格式 ----------
        print('\n== 2. 切换三种起始格式 ==')
        table = app.format_table
        expect = {
            'official': ('仿宋_GB2312', '三号(16pt)'),
            'academic': ('宋体', '小四(12pt)'),
            'legal': ('宋体', '四号(14pt)'),
        }
        for fmt_id, (font_cn, size) in expect.items():
            app.select_format(fmt_id)
            got_font = table.cells[('body', 'font_cn')][1].get()
            got_size = table.cells[('body', 'size')][1].get()
            check(f'切换 {fmt_id} 参数表跟随（正文中文字体）',
                  got_font == font_cn, got_font)
            check(f'切换 {fmt_id} 参数表跟随（正文字号）',
                  got_size == size, got_size)
            shot(root, f'02_select_{fmt_id}.png')
        app.select_format('official')
        title_font = table.cells[('title', 'font_cn')][1].get()
        check('official 主标题为方正小标宋简体', title_font == '方正小标宋简体', title_font)

        # ---------- 3. 改一格：覆盖值 + 色条 + 摘要 ----------
        print('\n== 3. 改一格 ==')
        app.cell_changed('body', 'font_cn', '楷体_GB2312')
        overrides = gui.get_preset_overrides(app._config, 'official')
        check('覆盖值按字段级记录', overrides == {'body': {'font_cn': '楷体_GB2312'}},
              str(overrides))
        bar_color = table.bars['body'].cget('bg')
        check('改动行色条亮起（朱砂红）', bar_color == gui.Theme.PRIMARY, str(bar_color))
        summary = app.format_summary.cget('text')
        check('摘要列出改动字段', '已改动' in summary and '正文·中文字体' in summary, summary)
        check('未改的行色条不亮',
              table.bars['title'].cget('bg') != gui.Theme.PRIMARY,
              str(table.bars['title'].cget('bg')))
        shot(root, '03_override_cell.png')

        # ---------- 3b. 存为新格式 ----------
        print('\n== 3b. ＋ 存为新格式 ==')
        app.save_as_new_format()
        new_id = app.preset.get()
        check('自动选中新格式', new_id not in gui.STARTING_FORMAT_IDS, new_id)
        check('新格式出现在面板', len(app.preset_column.rows) == 5,
              str(list(app.preset_column.rows)))
        check('源格式覆盖值已清空',
              gui.get_preset_overrides(app._config, 'official') == {},
              str(gui.get_preset_overrides(app._config, 'official')))
        effective = app._current_effective()
        check('新格式 = 当前生效值快照',
              effective['body']['font_cn'] == '楷体_GB2312', str(effective['body']))
        check('新格式自身无覆盖值',
              gui.get_preset_overrides(app._config, new_id) == {})
        shot(root, '04_saved_new_format.png')

        # ---------- 4. 重启不丢 ----------
        print('\n== 4. 重启 ==')
        root.destroy()
        root, app = build_app()
        check('重启后选中仍是新格式', app.preset.get() == new_id, app.preset.get())
        rows = app.preset_column.rows
        check('重启后新格式仍在面板', len(rows) == 5 and new_id in rows, str(list(rows)))
        effective = app._current_effective()
        check('重启后参数不丢（正文·中文字体）',
              effective['body']['font_cn'] == '楷体_GB2312', str(effective['body']))
        check('重启后主标题参数不丢',
              effective['title']['font_cn'] == '方正小标宋简体',
              str(effective['title']['font_cn']))
        shot(root, '05_after_restart.png')

        # ---------- 5. 折叠 ----------
        print('\n== 5. 折叠 / 展开 ==')
        app.toggle_format_area()
        check('折叠后正文隐藏', not app.format_body.winfo_manager())
        check('折叠后摘要仍在', '我的格式 1' in app.format_summary.cget('text'),
              app.format_summary.cget('text'))
        shot(root, '06_collapsed.png')
        app.toggle_format_area()
        check('展开恢复', bool(app.format_body.winfo_manager()))

        # ---------- 6. 恢复本行 / 恢复全部 ----------
        print('\n== 6. 恢复 ==')
        app.select_format('custom')
        app.cell_changed('body', 'line_spacing', 30)
        app.cell_changed('title', 'font_cn', '黑体')
        app.restore_row('body')
        check('恢复本行只删该行覆盖值',
              gui.get_preset_overrides(app._config, 'custom') == {'title': {'font_cn': '黑体'}},
              str(gui.get_preset_overrides(app._config, 'custom')))
        app.restore_all()
        check('恢复全部清空覆盖值',
              gui.get_preset_overrides(app._config, 'custom') == {})

        # ---------- 7. 原型不变量：长名字截断 ----------
        print('\n== 7. 原型不变量 ==')
        long_name = '这是一个特别长的用户格式名称'
        gui.save_as_new_preset(app._config, 'custom', long_name)
        app._persist_config()
        app.preset_column.rebuild(app._custom_format_entries())
        row = [r for r in app.preset_column.rows.values()
               if r.preset_id == app._config['active_preset_id']][0]
        shown = row.title.cget('text')
        check('用户格式名超长截断显示', len(shown) <= gui.CUSTOM_NAME_MAX_CHARS and shown.endswith('…'),
              shown)
        shot(root, '07_long_name.png')

    except Exception:
        traceback.print_exc()
        failures.append('异常中断')
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass

    print('\n========== 结果 ==========')
    if failures:
        print('失败 %d 项: %s' % (len(failures), '、'.join(failures)))
        return 1
    print('全部通过 ✓  截图目录:', SHOTS)
    return 0


if __name__ == '__main__':
    sys.exit(main())
