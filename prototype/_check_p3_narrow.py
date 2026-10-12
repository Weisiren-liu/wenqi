#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 窄屏自检：参数表窄屏收窄后不允许再被窗口边缘裁掉。

背景缺陷（prototype/_p2_shots/08_small_screen.png）：1120px 窗口下
「段前/段后」列被挤扁、列头「段后」被切掉。修复 = ElementTable.COLUMN_STAGES
逐级收窄：先隐藏段后 → 再隐藏段前（编辑入口收进「高级设置」段落间距区），
还不够再压缩字体列宽。

覆盖验收项：
  1. 1120px —— 段前/段后列隐藏、提示可见、请求宽度 ≤ 可用宽度、无控件被裁
  2. 1000px / 960px —— 继续压缩列宽，同样无裁切
  3. 宽屏（1859px）—— 9 列全显
  4. 「高级设置」段落间距区可编辑段前/段后，写字段级覆盖值

用法：$env:PYTHONIOENCODING='utf-8'; python prototype/_check_p3_narrow.py
截图输出到 prototype/_p3_shots/。
"""
import os
import shutil
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import tkinter as tk                                    # noqa: E402

import docformat_gui as gui                             # noqa: E402

SHOTS = os.path.join(HERE, '_p3_shots')
CONFIG = os.path.join(SHOTS, 'custom_settings.json')
SHOTS_TAKEN = []


def shot(root, name, title='文齐 · WenQi'):
    try:
        import time
        from _screenshot import capture, find_window
        windows = find_window(title)
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
        time.sleep(0.6)
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


def visible_right_edges(table):
    """当前映射的列控件中，最右的一条右边缘（含被裁风险检测）。"""
    edges = []
    for field, _label, _width in table.COLUMNS:
        for widget in table._column_widgets(field):
            if widget.winfo_ismapped():
                edges.append(widget.winfo_x() + widget.winfo_width())
    for element, _label in gui.ELEMENTS:
        widget = table.restore_buttons[element]
        if widget.winfo_ismapped():
            edges.append(widget.winfo_x() + widget.winfo_width())
    return max(edges) if edges else 0


def main():
    if os.path.isdir(SHOTS):
        shutil.rmtree(SHOTS)
    os.makedirs(SHOTS)

    gui.CONFIG_FILE = gui.Path(CONFIG)
    gui.DocFormatApp._maybe_show_community_notice = lambda self: None
    gui.messagebox.showinfo = lambda *a, **k: print('  [弹窗]', a[1] if len(a) > 1 else '')
    gui.messagebox.showwarning = lambda *a, **k: print('  [警告]', a[1] if len(a) > 1 else '')

    failures = []

    def check(label, cond, detail=''):
        status = 'PASS' if cond else 'FAIL'
        print(f'[{status}] {label}' + (f' —— {detail}' if detail and not cond else ''))
        if not cond:
            failures.append(label)

    root = app = None
    try:
        root, app = build_app()
        table = app.format_table

        def resize(width, height=760):
            root.geometry(f'{width}x{height}+20+20')
            root.update_idletasks()
            root.update()
            root.update_idletasks()
            root.update()

        # ---------- 1. 1120px：隐藏段前/段后，且无裁切 ----------
        print('\n== 1. 1120px 窄屏 ==')
        resize(1120)
        check('1120px 请求宽度不超过可用宽度',
              table.winfo_reqwidth() <= table.winfo_width(),
              f'req={table.winfo_reqwidth()} avail={table.winfo_width()}')
        hidden = table._hidden_fields
        check('1120px 隐藏段前/段后两列',
              set(hidden) == {'space_before', 'space_after'}, str(hidden))
        check('1120px 无控件右边缘越界',
              visible_right_edges(table) <= table.winfo_width(),
              f'edge={visible_right_edges(table)} width={table.winfo_width()}')
        note = app.format_note.cget('text')
        check('窄屏提示可见（段落间距区入口）', '段落间距' in note, note)
        shot(root, '08_small_screen.png')

        # ---------- 2. 1000 / 960px：继续压缩列宽 ----------
        print('\n== 2. 1000 / 960px ==')
        for width in (1000, 960):
            resize(width)
            check(f'{width}px 请求宽度不超过可用宽度',
                  table.winfo_reqwidth() <= table.winfo_width(),
                  f'req={table.winfo_reqwidth()} avail={table.winfo_width()}')
            check(f'{width}px 无控件右边缘越界',
                  visible_right_edges(table) <= table.winfo_width(),
                  f'edge={visible_right_edges(table)} width={table.winfo_width()}')
            shot(root, f'09_small_{width}.png')

        # ---------- 3. 宽屏：9 列全显 ----------
        print('\n== 3. 宽屏全列 ==')
        resize(1859, 1000)
        check('宽屏不隐藏任何列', table._hidden_fields == (), str(table._hidden_fields))
        check('宽屏提示恢复单行', '段落间距' not in app.format_note.cget('text'),
              app.format_note.cget('text'))
        shot(root, '10_wide_full_columns.png')

        # ---------- 4. 高级设置 · 段落间距区 ----------
        print('\n== 4. 高级设置 · 段落间距 ==')
        dialog = gui.CustomSettingsDialog(root)
        dialog.canvas.yview_moveto(1.0)      # 滚到底部，露出段落间距区
        root.update()
        shot(root, '12_advanced_spacing.png', title='高级设置')
        check('段落间距区覆盖全部元素行',
              set(dialog._spacing_vars) == {key for key, _l in gui.ELEMENTS},
              str(sorted(dialog._spacing_vars)))
        loaded = dialog._spacing_vars['body']['space_before'].get()
        check('段前装载当前生效值', loaded == '0', loaded)
        dialog._spacing_vars['body']['space_before'].set('6')
        dialog._save_values()
        overrides = gui.get_preset_overrides(dialog._config, 'custom')
        check('段落间距写字段级覆盖值',
              overrides == {'body': {'space_before': 6}}, str(overrides))
        dialog._spacing_vars['body']['space_before'].set('')
        dialog._save_values()
        overrides = gui.get_preset_overrides(dialog._config, 'custom')
        check('清空输入 = 回到基准值，覆盖值自动清除', overrides == {}, str(overrides))
        dialog.destroy()

        # ---------- 5. 收窄后回到宽屏可恢复（可逆性） ----------
        print('\n== 5. 收窄可逆 ==')
        resize(960)
        check('960px 先收窄', 'space_before' in table._hidden_fields, str(table._hidden_fields))
        resize(1859, 1000)
        check('回到宽屏列全部恢复', table._hidden_fields == (), str(table._hidden_fields))
        shot(root, '11_back_to_wide.png')

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
