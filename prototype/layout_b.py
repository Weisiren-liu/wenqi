#!/usr/bin/env python3
"""布局原型：方案 B-2（格式编辑内联主页面 + 预设作为起点 + 覆盖值模型）。

与 layout_a.py 的区别：
- 格式编辑区**直接内联在主页面**，不再是弹窗
- 预设（内置 + 我的）缩成左侧一列小选项，点击即把参数**装载**进编辑区
- 采用**活链接 + 覆盖值**模型：
    显示值 = 预设值 ⊕ 覆盖值
  改过的格子会高亮，行尾有「↺ 恢复本行」，顶部有「恢复全部」。
  这样既能微调内置格式，又能随时退回原始预设值，不会误改坏。

纯视觉原型，不处理真实文档，不读写任何配置文件。
覆盖值只存在内存里，关掉窗口即丢弃。

运行：
    python prototype/layout_b.py
"""

import copy
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
from tkinter import messagebox, ttk
import docformat_gui as gui
from docformat_gui import (
    Theme, get_font, ui_px, Icons, FileInputField, InlineToggle,
    _configure_tk_high_dpi, _init_system_fonts,
    DEFAULT_CUSTOM_SETTINGS, FONT_SIZES, COMMON_FONTS_CN, COMMON_FONTS_EN,
)

# ---------------------------------------------------------------- 数据

# 起始格式：内置三个 + 一个自定义起点
STARTING_FORMATS = (
    ('official', 'GB/T 公文标准', '党政机关公文格式', True),
    ('academic', '学术论文', '论文投稿与学位论文', True),
    ('legal', '法律文书', '合同、起诉状等', True),
    ('custom', '自定义格式', '从公文格式起步，按需改', False),
)

# 用户保存的格式：出厂为空，靠「＋ 存为新格式」攒出来
CUSTOM_FORMATS = ()

# 用户格式名的显示上限：超出就截断，避免长名字把预设面板撑宽。
# 定 8 是因为面板宽度由最宽的行决定，而内置行的「内置」徽标 + 名称已占掉大部分宽度，
# 无徽标的自定义行能容纳的字符数也和它接近；改大就会把面板撑宽（实测 217 → 229）。
CUSTOM_NAME_MAX_CHARS = 8

# 公文参数表：元素 → (key, 中文名, 说明)
ELEMENTS = (
    ('title', '主标题', '文档大标题'),
    ('recipient', '主送机关', '顶格，如"XX单位："'),
    ('heading1', '一级标题', '一、二、三、'),
    ('heading2', '二级标题', '（一）（二）'),
    ('heading3', '三级标题', '1. 2. 3.'),
    ('heading4', '四级标题', '（1）（2）'),
    ('body', '正文', '段落正文'),
    ('signature', '落款', '发文单位署名'),
    ('date', '成文日期', '右对齐日期'),
    ('attachment', '附件说明', '附件标记'),
)

ALIGN_LABELS = (
    ('left', '左对齐'), ('center', '居中'),
    ('right', '右对齐'), ('justify', '两端对齐'),
)
ALIGN_SHORT = {'left': '左', 'center': '中', 'right': '右', 'justify': '两端'}

INDENT_LABELS = ((0, '0'), (32, '2 字符'), (16, '1 字符'), (48, '3 字符'))

SIZE_OPTIONS = ['%s(%spt)' % (name, pt) for name, pt in FONT_SIZES]


def size_display(pt):
    for name, value in FONT_SIZES:
        if abs(float(value) - float(pt)) < 0.01:
            return '%s(%spt)' % (name, value)
    return '%spt' % pt


def size_from_display(text):
    if '(' in text and text.endswith('pt)'):
        return float(text[text.rfind('(') + 1:-3])
    try:
        return float(text.replace('pt', ''))
    except ValueError:
        return 16.0


def build_preset_values(preset_id, difficulty=0):
    """返回某个预设的完整元素参数。

    原型里内置预设共用公文参数（真实实现会从 formatter.PRESETS 取不同值），
    只做少量偏移，好让"切换预设，编辑区参数跟着变"这件事看得出来。
    """
    values = {}
    for key, _label, _desc in ELEMENTS:
        base = copy.deepcopy(DEFAULT_CUSTOM_SETTINGS.get(key, {}))
        values[key] = {
            'font_cn': base.get('font_cn', '仿宋_GB2312'),
            'font_en': base.get('font_en', 'Times New Roman'),
            'size': base.get('size', 16),
            'bold': base.get('bold', False),
            'align': base.get('align', 'left'),
            'indent': base.get('indent', 32),
            'line_spacing': base.get('line_spacing', 28),
            'space_before': base.get('space_before', 0),
            'space_after': base.get('space_after', 0),
        }

    if preset_id == 'academic':
        values['body'].update(font_cn='宋体', size=12, line_spacing=22, indent=24)
        values['title'].update(font_cn='黑体', size=18)
        for key in ('heading1', 'heading2'):
            values[key].update(font_cn='黑体', size=14, space_before=6, space_after=6)
        values['heading3'].update(space_before=6, space_after=3)
        values['signature'].update(align='left')
        values['date'].update(align='left')
    elif preset_id == 'legal':
        values['body'].update(font_cn='宋体', size=14, line_spacing=26)
        values['title'].update(font_cn='黑体', size=20)
        values['heading1'].update(font_cn='黑体', size=15)
    elif preset_id == 'custom':
        # 自定义格式：出厂即公文参数，用户在上面改（本原型不需要额外偏移）
        values['signature'].update(align='right')
        values['date'].update(align='right')

    if difficulty:
        values['body']['line_spacing'] = 28 + difficulty
    return values


class FormatState:
    """活链接 + 覆盖值：显示值 = 预设值 ⊕ 覆盖值。"""

    def __init__(self, preset_id):
        self.preset_id = preset_id
        self.overrides = {}          # {element: {field: value}}

    def preset_values(self):
        return build_preset_values(self.preset_id)

    def effective(self):
        values = self.preset_values()
        for element, fields in self.overrides.items():
            values.setdefault(element, {}).update(fields)
        return values

    def set_field(self, element, field, value):
        self.overrides.setdefault(element, {})[field] = value

    def restore_row(self, element):
        self.overrides.pop(element, None)

    def restore_all(self):
        self.overrides.clear()

    def is_overridden(self, element, field):
        return field in self.overrides.get(element, {})

    def override_count(self):
        return sum(len(f) for f in self.overrides.values())

    def switch_preset(self, preset_id):
        self.preset_id = preset_id
        self.overrides.clear()


# ---------------------------------------------------------------- 组件

def _paint(widget, bg):
    """递归给纯 tk 控件换底色，跳过 ttk 控件（它们不吃 bg）。"""
    try:
        if not isinstance(widget, ttk.Widget):
            widget.configure(bg=bg)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _paint(child, bg)


class PresetColumn(tk.Frame):
    """左列：起始格式 + 我的格式，统一按行呈现，整列做成带边框的滚动面板。

    内置 3 个 + 自定义格式 1 个 + 用户格式若干，全部按同一行样式铺进滚动区。
    **没有展开/收起状态**：面板高度固定，内容多了就滚 —— 边框 + 滚动条本身
    就足以让用户看出"这里还有更多"。

    用户保存多个格式时，列宽列高都不变，只是面板内可滚。
    """

    ROW_GAP = Theme.SPACE_SM
    MIN_COLUMN_WIDTH = 150
    # 面板高度：定成常量而不是"单行高 × 行数"。
    # 内置行带描述有 66px 高，乘出来的值会比右侧参数表还高；直接定 400px
    # 既与参数表（约 350px）接近，又能让"格式多了就滚"真的发生 ——
    # 没有上限的话面板会一直长高去容纳内容，滚动就形同虚设。
    VIEWPORT_HEIGHT = 400
    SCROLLBAR_WIDTH = 12
    # 内容高度超过视口这么多像素才算"需要滚动"。
    # 定 6px 是因为 canvas 可视高度与 scrollregion 之间会有 1~4px 的边框误差。
    OVERFLOW_TOLERANCE = 6

    def __init__(self, parent, starting_formats, custom_formats, controller):
        super().__init__(parent, bg=Theme.BG)
        self.controller = controller
        self.starting_formats = tuple(starting_formats)
        self.custom_formats = tuple(custom_formats)
        self.rows = {}           # id -> PresetOption
        self.builtin_rows = {}   # 固定内置行的 id

        head = tk.Frame(self, bg=Theme.BG)
        head.pack(fill='x', pady=(0, Theme.SPACE_XS))
        self.head_label = tk.Label(head, text='起始格式', font=get_font(10), bg=Theme.BG,
                                   fg=Theme.TEXT_MUTED)
        self.head_label.pack(side='left')

        # 带边框的滚动面板：边框让"这里可以滚"一眼可见
        self.panel = tk.Frame(self, bg=Theme.BORDER, padx=1, pady=1)
        self.panel.pack(fill='x')
        self.canvas = tk.Canvas(self.panel, bg=Theme.BG, highlightthickness=0,
                                borderwidth=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar = tk.Scrollbar(self.panel, orient='vertical',
                                      command=self.canvas.yview,
                                      width=self.SCROLLBAR_WIDTH)
        self.canvas.configure(yscrollcommand=self._on_yscroll)

        self.list_area = tk.Frame(self.canvas, bg=Theme.BG)
        self._list_window = self.canvas.create_window((0, 0), window=self.list_area,
                                                     anchor='nw')
        self.canvas.bind('<Configure>', self._sync_viewport_width)

        # 所有行（起始格式 + 我的格式）都放进滚动区，顺序即显示顺序
        for format_id, label, description, is_builtin in self.starting_formats:
            row = PresetOption(self.list_area, format_id, label, description,
                               is_builtin, controller)
            self.builtin_rows[format_id] = row
            self.rows[format_id] = row
        for format_id, label in self.custom_formats:
            row = PresetOption(self.list_area, format_id, label, '', False, controller)
            self.rows[format_id] = row

        # 一个格式都还没保存时，给一行说明，免得面板看起来是空的
        self.empty_hint = tk.Label(
            self.list_area, text='还没有保存过格式\n改好参数后点上方「＋ 存为新格式」',
            font=get_font(9), bg=Theme.BG, fg=Theme.TEXT_MUTED, justify='left',
            anchor='w', padx=Theme.SPACE_SM, pady=Theme.SPACE_SM)

        self.column_width = self.MIN_COLUMN_WIDTH
        self._viewport_height = 0
        self._layout()
        self.column_width = self._measure_column_width()
        self._lock_viewport()
        # 宽度定下来之后，让用户格式行也在面板宽度内换行
        for format_id, _label in self.custom_formats:
            self.rows[format_id].fit_width(self.column_width)
        self._sync_scrollregion()
        self._bind_wheel_recursive(self.panel)

    # ---------- 滚动视口 ----------

    def _content_overflows(self):
        """内容是否真的超出视口。"""
        region = self.canvas.cget('scrollregion').split()
        if len(region) != 4:
            return False
        try:
            content_height = float(region[3]) - float(region[1])
        except ValueError:
            return True
        return content_height > self.canvas.winfo_height() + self.OVERFLOW_TOLERANCE

    def _canvas_width(self):
        """面板总宽恒定：滚动条占多少，canvas 就少多少。

        滚动条一旦 pack 进去，它的宽度就会加到面板上（pack 的布局自然会算进去），
        实测面板会从 217 涨到 229。所以这里按"面板宽 − 滚动条宽"给 canvas 定宽。
        """
        if self.scrollbar.winfo_manager():
            return max(60, self.column_width - self.SCROLLBAR_WIDTH)
        return self.column_width

    def _on_yscroll(self, first, last):
        """内容不超出视口时隐藏滚动条，避免视觉噪音。"""
        self.scrollbar.set(first, last)
        if self._content_overflows():
            if not self.scrollbar.winfo_manager():
                self.scrollbar.pack(side='right', fill='y')
                self._apply_canvas_geometry()
        elif self.scrollbar.winfo_manager():
            self.scrollbar.pack_forget()
            self._apply_canvas_geometry()

    def _apply_canvas_geometry(self):
        """把 canvas 与内容的宽度同步到当前（可能已含滚动条）的目标宽。"""
        width = self._canvas_width()
        self.canvas.configure(width=width)
        self.canvas.itemconfigure(self._list_window, width=width)

    def _sync_scrollregion(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self._on_yscroll(*self.canvas.yview())

    def _sync_viewport_width(self, event=None):
        """内容宽度跟随视口，保证行是"整行"而不是按内容宽。"""
        self._apply_canvas_geometry()
        if self._viewport_height:
            self.canvas.configure(height=self._viewport_height)

    def _bind_wheel_recursive(self, widget):
        """滚轮绑定到面板内所有控件上。

        只在 canvas 上绑 Enter/Leave 是不够的：行是 canvas 的子控件，鼠标移到行上时
        canvas 会收到 Leave，滚轮事件就漏给主页面了。
        """
        for target in [widget] + self._descendants(widget):
            target.bind('<MouseWheel>', self._on_wheel)

    @staticmethod
    def _descendants(widget):
        found = []
        for child in widget.winfo_children():
            found.append(child)
            found.extend(PresetColumn._descendants(child))
        return found

    def _on_wheel(self, event):
        """在面板内滚动，返回 break 阻止主页面跟着滚。"""
        if not self._content_overflows():
            return None
        self.canvas.yview_scroll(int(-event.delta / 120), 'units')
        return 'break'

    def _lock_viewport(self):
        """给面板定高，超出部分在面板内滚动。

        **必须有上限**：没有上限的话面板会一直长高去容纳内容，滚动就永远不会发生，
        等于白做。上限是常量 VIEWPORT_HEIGHT，与右侧参数表大致等高。

        宽高都要显式设置：canvas 默认宽约 378px 会把 162px 的内容拉宽，
        默认 highlightthickness=2 会让可视高度比内容矮几像素。
        """
        if not self._viewport_height:
            self._viewport_height = ui_px(self.VIEWPORT_HEIGHT)
        self.canvas.configure(height=self._viewport_height)
        self._apply_canvas_geometry()

    def _layout(self):
        """所有行按顺序铺进滚动区，没有折叠态之分。"""
        for row in self.rows.values():
            row.pack_forget()
        self.empty_hint.pack_forget()
        for format_id, _label, _desc, _flag in self.starting_formats:
            self.builtin_rows[format_id].pack(fill='x', pady=(0, self.ROW_GAP))
        if not self.custom_formats:
            self.empty_hint.pack(fill='x')
        for format_id, _label in self.custom_formats:
            self.rows[format_id].pack(fill='x', pady=(0, self.ROW_GAP))

    def _measure_column_width(self):
        """量取内容的自然宽度作为面板宽度。

        不能逐行比 reqwidth：内置行带「内置」徽标，比我的格式行宽，而内容宽度是
        由最宽的那一行决定的。直接问 list_area 的实际宽度最可靠。
        """
        self.update_idletasks()
        width = self.list_area.winfo_reqwidth()
        if width <= 1:
            width = max([row.winfo_reqwidth() for row in self.builtin_rows.values()]
                        + [self.MIN_COLUMN_WIDTH])
        return max(self.MIN_COLUMN_WIDTH, width)

    def add(self, format_id, label):
        """用户「存为新格式」后追加一项并滚到可见位置（原型内存操作）。"""
        self.custom_formats = self.custom_formats + ((format_id, label),)
        row = PresetOption(self.list_area, format_id, label, '', False, self.controller)
        row.fit_width(self.column_width)   # 长名字在面板宽度内换行
        self.rows[format_id] = row
        self._layout()
        self._bind_wheel_recursive(row)
        self.update_idletasks()
        self._sync_scrollregion()
        self.canvas.yview_moveto(1.0)      # 滚到底，让新增项可见
        return row

    def set_selected(self, format_id):
        for key, row in self.rows.items():
            row.set_selected(key == format_id)


class PresetOption(tk.Frame):
    """左侧起点格式小选项。"""

    def __init__(self, parent, preset_id, label, description, is_builtin, controller):
        super().__init__(parent, bg=Theme.CARD, highlightthickness=1,
                         highlightbackground=Theme.BORDER)
        self.preset_id = preset_id
        self.controller = controller
        self.selected = False

        inner = tk.Frame(self, bg=Theme.CARD)
        inner.pack(fill='x', padx=Theme.SPACE_SM + 2, pady=Theme.SPACE_SM - 1)

        head = tk.Frame(inner, bg=Theme.CARD)
        head.pack(fill='x')
        self.title = tk.Label(head, text=label, font=get_font(11), bg=Theme.CARD,
                              fg=Theme.TEXT, anchor='w')
        self.title.pack(side='left')
        if is_builtin:
            self.badge = tk.Label(head, text='内置', font=get_font(8), bg=Theme.BG,
                                  fg=Theme.TEXT_MUTED, padx=4)
            self.badge.pack(side='right')

        self.desc = tk.Label(inner, text=description, font=get_font(9), bg=Theme.CARD,
                             fg=Theme.TEXT_MUTED, anchor='w')
        self.desc.pack(fill='x', anchor='w')

        for w in (self, inner, head, self.title, self.desc):
            w.bind('<Button-1>', self._on_click)
            w.bind('<Enter>', self._on_enter)
            w.bind('<Leave>', self._on_leave)
            w.configure(cursor='hand2')

    def _on_click(self, _event=None):
        self.controller.select_format(self.preset_id)

    def _on_enter(self, _event=None):
        if not self.selected:
            self.configure(highlightbackground='#D0CCC6')

    def _on_leave(self, _event=None):
        self._apply()

    def set_selected(self, selected):
        self.selected = selected
        self._apply()

    def fit_width(self, width):
        """把用户格式名截断到面板装得下的长度。

        试过用 wraplength 换行，但 wraplength 只约束换行、不约束 Label 的最小请求宽度，
        长名字仍会把面板撑宽（实测 217 → 229）。所以这里直接截断显示。
        """
        text = self.title.cget('text')
        if len(text) > CUSTOM_NAME_MAX_CHARS:
            self.title.configure(text=text[:CUSTOM_NAME_MAX_CHARS - 1] + '…')

    def _apply(self):
        bg = Theme.PRIMARY_LIGHT if self.selected else Theme.CARD
        self.configure(bg=bg,
                       highlightbackground=Theme.PRIMARY if self.selected else Theme.BORDER,
                       highlightthickness=2 if self.selected else 1)
        _paint(self, bg)
        if getattr(self, 'badge', None) is not None:
            self.badge.configure(bg=Theme.BG)
        self.title.configure(font=get_font(11, 'bold' if self.selected else 'normal'))


class ElementTable(tk.Frame):
    """元素参数表：一行一个元素，列为各参数。

    用 grid 布局，列宽由表头统一决定，避免各行列宽对不齐。
    """

    COLUMNS = (
        ('font_cn', '中文字体', 17),
        ('font_en', '英数字体', 17),
        ('size', '字号', 11),
        ('bold', '加粗', 4),
        ('align', '对齐', 8),
        ('indent', '首行缩进', 8),
        ('line_spacing', '行距', 5),
        ('space_before', '段前', 4),
        ('space_after', '段后', 4),
    )

    def __init__(self, parent, controller):
        super().__init__(parent, bg=Theme.SURFACE, highlightthickness=1,
                         highlightbackground=Theme.BORDER)
        self.controller = controller
        self.cells = {}          # (element, field) -> (widget, var)
        self.bars = {}           # element -> 行首改动色条
        self.restore_buttons = {}

        # 表头：column 0 是改动色条，column 1 是元素名，之后是各参数列
        tk.Label(self, text='元素', font=get_font(10, 'bold'), bg=Theme.CARD_ALT,
                 fg=Theme.TEXT_SECONDARY, anchor='w', width=9
                 ).grid(row=0, column=1, sticky='w', padx=(Theme.SPACE_SM, 0), pady=6)
        for index, (field, label, width) in enumerate(self.COLUMNS, start=2):
            tk.Label(self, text=label, font=get_font(10, 'bold'), bg=Theme.CARD_ALT,
                     fg=Theme.TEXT_SECONDARY, anchor='w', width=width
                     ).grid(row=0, column=index, sticky='w', pady=6)
        tk.Label(self, text='', bg=Theme.CARD_ALT
                 ).grid(row=0, column=len(self.COLUMNS) + 2, sticky='ew', pady=6)

        for row_index, (element, label, _description) in enumerate(ELEMENTS, start=1):
            self._build_row(row_index, element, label)

    def _build_row(self, row_index, element, label):
        background = Theme.SURFACE if row_index % 2 else Theme.CARD
        self.row_backgrounds = getattr(self, 'row_backgrounds', {})
        self.row_backgrounds[element] = background

        # 行首改动色条：不依赖 ttk 主题着色，任何主题下都能看见
        bar = tk.Frame(self, bg=background, width=3)
        bar.grid(row=row_index, column=0, sticky='ns', padx=(0, 2))
        self.bars[element] = bar

        tk.Label(self, text=label, font=get_font(10), bg=background,
                 fg=Theme.TEXT, anchor='w', width=9
                 ).grid(row=row_index, column=1, sticky='w', padx=(Theme.SPACE_SM, 0), pady=3)

        for column, (field, _label, width) in enumerate(self.COLUMNS, start=2):
            widget, var = self._make_cell(element, field, width, background)
            widget.grid(row=row_index, column=column, sticky='w', padx=1, pady=2)
            self.cells[(element, field)] = (widget, var)

        restore = tk.Label(self, text='↺', font=get_font(12), bg=background,
                           fg=Theme.BORDER, cursor='arrow', width=3)
        restore.grid(row=row_index, column=len(self.COLUMNS) + 2, sticky='w')
        restore.bind('<Button-1>', lambda _e, el=element: self.controller.restore_row(el))
        self.restore_buttons[element] = restore

    def _make_cell(self, element, field, width, background):
        """按字段类型创建控件，返回 (widget, var)。"""
        # 字体下拉用更小的字，保证 "Times New Roman" 这类长名字不被截断
        font = get_font(9) if field in ('font_cn', 'font_en') else get_font(10)
        if field == 'bold':
            var = tk.BooleanVar()
            widget = tk.Checkbutton(
                self, variable=var, bg=background, activebackground=background,
                highlightthickness=0, bd=0, cursor='hand2',
                command=lambda el=element: self.controller.cell_changed(
                    el, 'bold', var.get()))
        elif field == 'align':
            var = tk.StringVar()
            widget = ttk.Combobox(self, textvariable=var, state='readonly', width=width,
                                  font=font,
                                  values=[label for _v, label in ALIGN_LABELS])
            widget.bind('<<ComboboxSelected>>',
                        lambda _e, el=element: self.controller.cell_changed(
                            el, 'align', dict((label, v) for v, label in ALIGN_LABELS)[var.get()]))
        elif field == 'indent':
            var = tk.StringVar()
            widget = ttk.Combobox(self, textvariable=var, state='readonly', width=width,
                                  font=font,
                                  values=[label for _v, label in INDENT_LABELS])
            widget.bind('<<ComboboxSelected>>',
                        lambda _e, el=element: self.controller.cell_changed(
                            el, 'indent', dict((label, v) for v, label in INDENT_LABELS)[var.get()]))
        elif field == 'size':
            var = tk.StringVar()
            widget = ttk.Combobox(self, textvariable=var, state='readonly', width=width,
                                  font=font, values=SIZE_OPTIONS)
            widget.bind('<<ComboboxSelected>>',
                        lambda _e, el=element: self.controller.cell_changed(
                            el, 'size', size_from_display(var.get())))
        elif field in ('line_spacing', 'space_before', 'space_after'):
            var = tk.StringVar()
            widget = tk.Entry(self, textvariable=var, font=font, width=width,
                              relief='solid', bd=1, justify='center')
            fallback = 28 if field == 'line_spacing' else 0
            commit = lambda _e, el=element, f=field: self.controller.cell_changed(
                el, f, self._as_number(var.get(), fallback))
            widget.bind('<FocusOut>', commit)
            widget.bind('<Return>', commit)
        else:
            var = tk.StringVar()
            values = COMMON_FONTS_CN if field == 'font_cn' else COMMON_FONTS_EN
            widget = ttk.Combobox(self, textvariable=var, width=width,
                                  font=font, values=list(values))
            commit = lambda _e, el=element, f=field: self.controller.cell_changed(
                el, f, var.get())
            widget.bind('<<ComboboxSelected>>', commit)
            widget.bind('<FocusOut>', commit)

        return widget, var

    @staticmethod
    def _as_number(text, fallback):
        """行距取整数更符合公文习惯，非整数输入保留小数。"""
        try:
            value = float(str(text).strip())
        except (TypeError, ValueError):
            return fallback
        return int(value) if value == int(value) else value

    def refresh(self, state):
        values = state.effective()
        changed = []             # [(元素名, 字段名)] 用于顶部汇总
        for element, label, _description in ELEMENTS:
            row_values = values.get(element, {})
            dirty = 0
            for field, field_label, _width in self.COLUMNS:
                widget, var = self.cells[(element, field)]
                value = row_values.get(field)
                if field == 'bold':
                    var.set(bool(value))
                elif field == 'align':
                    var.set(dict(ALIGN_LABELS).get(value, '左对齐'))
                elif field == 'indent':
                    var.set(dict(INDENT_LABELS).get(value, str(value)))
                elif field == 'size':
                    var.set(size_display(value))
                else:
                    var.set('' if value is None else str(value))

                overridden = state.is_overridden(element, field)
                if overridden:
                    dirty += 1
                    changed.append('%s·%s' % (label, field_label))
                self._tint(widget, overridden, self.row_backgrounds[element])

            # 行首色条：有改动则整行点亮，不依赖 ttk 着色
            self.bars[element].configure(
                bg=Theme.PRIMARY if dirty else self.row_backgrounds[element])
            button = self.restore_buttons[element]
            button.configure(fg=Theme.PRIMARY if dirty else Theme.BORDER,
                             cursor='hand2' if dirty else 'arrow')
        return changed

    @staticmethod
    def _tint(widget, overridden, background):
        """覆盖过的格子给出可见提示，未覆盖的恢复原样。"""
        try:
            if isinstance(widget, ttk.Combobox):
                widget.configure(style='Override.TCombobox' if overridden else 'TCombobox')
            elif isinstance(widget, tk.Entry):
                widget.configure(fg=Theme.PRIMARY if overridden else Theme.TEXT,
                                 bg=Theme.PRIMARY_LIGHT if overridden else Theme.CARD)
            else:
                widget.configure(activebackground=Theme.PRIMARY_LIGHT if overridden
                                 else background)
        except tk.TclError:
            pass


# ---------------------------------------------------------------- 主窗口

class PrototypeLayoutB(tk.Tk):
    """方案 B-2 的可运行原型。"""

    def __init__(self):
        super().__init__()
        self.title('【原型】自动文档格式处理工具 — 方案 B-2（内联格式编辑）')
        _configure_tk_high_dpi(self)
        _init_system_fonts()

        self.state = FormatState('custom')
        self.operation = tk.StringVar(value='smart')
        self.revision_var = tk.BooleanVar(value=False)
        self.auto_open_var = tk.BooleanVar(value=False)

        self._init_override_style()
        self._build_header()
        self._build_body()
        self.select_format('custom')
        # 格式区默认展开；「我的格式」默认只露 2 个（由 CustomFormatRow 自己控制）

        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(screen_w - 40, max(1240, int(screen_w * 0.78)))
        h = min(screen_h - 60, max(860, int(screen_h * 0.9)))
        self.geometry('%dx%d+%d+%d' % (w, h, max(0, (screen_w - w) // 2),
                                       max(0, (screen_h - h) // 2)))
        self.configure(bg=Theme.BG)

    def _init_override_style(self):
        """覆盖过的下拉框用淡橙底标出。

        注意：Win11 的 ttk 主题会忽略 combobox 的 foreground，
        所以用 fieldbackground 做提示，比改文字颜色可靠。
        """
        style = ttk.Style(self)
        try:
            style.configure('Override.TCombobox',
                            fieldbackground=Theme.PRIMARY_LIGHT,
                            foreground=Theme.PRIMARY,
                            arrowcolor=Theme.PRIMARY)
        except tk.TclError:
            pass

    # ---------- 头部 ----------

    def _build_header(self):
        bar = tk.Frame(self, bg=Theme.CARD_ALT)
        bar.pack(fill='x')
        tk.Label(bar, text='【界面原型】方案 B-2 — 格式编辑内联 + 预设作起点',
                 font=get_font(11, 'bold'), bg=Theme.CARD_ALT, fg=Theme.PRIMARY,
                 padx=Theme.SPACE_MD, pady=6).pack(side='left')
        tk.Label(bar, text='改动过的行左侧会亮起竖条，点行尾 ↺ 可恢复该行',
                 font=get_font(9), bg=Theme.CARD_ALT, fg=Theme.TEXT_MUTED,
                 padx=Theme.SPACE_MD).pack(side='right')

    # ---------- 主体 ----------

    def _build_body(self):
        wrap = tk.Frame(self, bg=Theme.BG)
        wrap.pack(fill='both', expand=True)
        canvas = tk.Canvas(wrap, bg=Theme.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(wrap, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        content = tk.Frame(canvas, bg=Theme.BG)
        window = canvas.create_window((0, 0), window=content, anchor='nw')
        content.bind('<Configure>',
                     lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        self.bind_all('<MouseWheel>',
                      lambda e: canvas.yview_scroll(int(-e.delta / 120), 'units'))

        inner = tk.Frame(content, bg=Theme.BG)
        inner.pack(fill='both', expand=True, padx=Theme.SPACE_XL, pady=Theme.SPACE_LG)

        self._build_title(inner)
        self._build_files(inner)
        self._build_format_area(inner)
        self._build_mode_block(inner)
        self._build_options(inner)
        self._build_run_button(inner)

    def _build_title(self, parent):
        row = tk.Frame(parent, bg=Theme.BG)
        row.pack(fill='x', pady=(0, Theme.SPACE_LG))
        tk.Label(row, text='自动文档格式处理工具', font=get_font(24, 'bold'),
                 bg=Theme.BG, fg=Theme.TEXT).pack(side='left')
        tk.Label(row, text='v1.8.8.2', font=get_font(11, 'bold'), bg=Theme.PRIMARY_LIGHT,
                 fg=Theme.PRIMARY, padx=9, pady=4).pack(side='left',
                                                        padx=(Theme.SPACE_SM, 0), pady=(5, 0))
        tk.Label(row, text='关于', font=get_font(11), bg=Theme.BG,
                 fg=Theme.TEXT_SECONDARY, padx=8, cursor='hand2').pack(side='right')

    def _build_files(self, parent):
        section = tk.Frame(parent, bg=Theme.BG)
        section.pack(fill='x', pady=(0, Theme.SPACE_LG))
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        FileInputField(section, label_text='输入',
                       placeholder='点击选择文件，或将文件拖到这里',
                       variable=self.input_var,
                       command=lambda: self.notice('这里会打开文件选择框')
                       ).pack(fill='x', pady=(0, Theme.SPACE_SM))
        FileInputField(section, label_text='输出',
                       placeholder='默认输出到原文件旁（_processed）',
                       variable=self.output_var,
                       command=lambda: self.notice('这里会打开保存位置选择框')
                       ).pack(fill='x', pady=(0, Theme.SPACE_SM))
        row = tk.Frame(section, bg=Theme.BG)
        row.pack(fill='x')
        tk.Frame(row, bg=Theme.BG, width=40).pack(side='left')
        paste = tk.Label(row, text='📋 没有文件？粘贴文本生成 docx', font=get_font(11),
                         bg=Theme.BG, fg=Theme.PRIMARY, cursor='hand2', padx=4)
        paste.pack(side='left')
        paste.bind('<Button-1>', lambda e: self.notice('这里会打开粘贴文本对话框'))

    # ---------- 核心：内联格式编辑区 ----------

    def _build_format_area(self, parent):
        section = tk.Frame(parent, bg=Theme.BG)
        section.pack(fill='x', pady=(0, Theme.SPACE_LG))

        head = tk.Frame(section, bg=Theme.BG)
        head.pack(fill='x', pady=(0, Theme.SPACE_SM))

        # 折叠开关：收起后只留标题条 + 摘要，主页面立刻变短
        self.format_collapsed = False
        self.collapse_toggle = tk.Label(
            head, text='▾', font=get_font(12), bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
            cursor='hand2', padx=4)
        self.collapse_toggle.pack(side='left')
        self.collapse_toggle.bind('<Button-1>', lambda e: self.toggle_format_area())

        self.format_title = tk.Label(head, text='文档格式', font=get_font(12, 'bold'),
                                     bg=Theme.BG, fg=Theme.TEXT, cursor='hand2')
        self.format_title.pack(side='left')
        self.format_title.bind('<Button-1>', lambda e: self.toggle_format_area())

        self.summary = tk.Label(head, text='', font=get_font(10), bg=Theme.BG,
                                fg=Theme.TEXT_MUTED)
        self.summary.pack(side='left', padx=(Theme.SPACE_MD, 0))

        restore_all = tk.Label(head, text='↺ 恢复全部', font=get_font(10), bg=Theme.BG,
                               fg=Theme.TEXT_MUTED, cursor='hand2', padx=6)
        restore_all.pack(side='right')
        restore_all.bind('<Button-1>', lambda e: self.restore_all())

        save_as = tk.Label(head, text='＋ 存为新格式', font=get_font(10, 'bold'),
                           bg=Theme.BG, fg=Theme.PRIMARY, cursor='hand2', padx=6)
        save_as.pack(side='right')
        save_as.bind('<Button-1>', lambda e: self.save_as_new_format())

        # 折叠时整块隐藏，只保留上面那行标题与摘要
        self.format_body = tk.Frame(section, bg=Theme.BG)
        self.format_body.pack(fill='x')

        two_col = tk.Frame(self.format_body, bg=Theme.BG)
        two_col.pack(fill='x')

        # 左：起始格式 + 我的格式，统一按行呈现
        left = tk.Frame(two_col, bg=Theme.BG)
        left.pack(side='left', fill='y', padx=(0, Theme.SPACE_MD))
        self.preset_column = PresetColumn(left, STARTING_FORMATS, CUSTOM_FORMATS, self)
        self.preset_column.pack(fill='x')

        # 右：元素参数表
        right = tk.Frame(two_col, bg=Theme.BG)
        right.pack(side='left', fill='both', expand=True)
        tk.Label(right, text='格式参数（可直接修改）', font=get_font(10), bg=Theme.BG,
                 fg=Theme.TEXT_MUTED).pack(anchor='w', pady=(0, Theme.SPACE_SM))
        self.table = ElementTable(right, self)
        self.table.pack(fill='x')

        note = tk.Label(right, text='页边距、页码、表格等其余参数仍在「高级设置」中调整',
                        font=get_font(9), bg=Theme.BG, fg=Theme.TEXT_MUTED)
        note.pack(anchor='w', pady=(Theme.SPACE_SM, 0))

    # ---------- 折叠 ----------

    def toggle_format_area(self):
        self.format_collapsed = not self.format_collapsed
        if self.format_collapsed:
            self.format_body.pack_forget()
        else:
            self.format_body.pack(fill='x')
        self.collapse_toggle.configure(text='▸' if self.format_collapsed else '▾')

    # ---------- 处理方式 / 选项 / 执行 ----------

    def _build_mode_block(self, parent):
        section = tk.Frame(parent, bg=Theme.BG)
        section.pack(fill='x', pady=(0, Theme.SPACE_LG))
        tk.Label(section, text='处理方式', font=get_font(12, 'bold'), bg=Theme.BG,
                 fg=Theme.TEXT).pack(anchor='w', pady=(0, Theme.SPACE_SM))

        gui.SelectableCard(section, title='智能一键处理',
                           description='修复中英文标点混用，并套用上表的格式参数，一步到位',
                           value='smart', variable=self.operation,
                           icon_draw_func=Icons.draw_magic, is_featured=True
                           ).pack(fill='x', pady=(0, Theme.SPACE_MD))

        row = tk.Frame(section, bg=Theme.BG)
        row.pack(fill='x')
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        gui.SelectableCard(row, title='格式诊断',
                           description='按上表参数体检，只出报告不改文件',
                           value='analyze', variable=self.operation,
                           icon_draw_func=Icons.draw_search
                           ).grid(row=0, column=0, sticky='nsew', padx=(0, Theme.SPACE_SM))
        gui.SelectableCard(row, title='仅修标点',
                           description='只统一标点，保留原有字体和段落',
                           value='punctuation', variable=self.operation,
                           icon_draw_func=Icons.draw_edit
                           ).grid(row=0, column=1, sticky='nsew')

    def _build_options(self, parent):
        section = tk.Frame(parent, bg=Theme.BG)
        section.pack(fill='x', pady=(0, Theme.SPACE_SM))
        row1 = tk.Frame(section, bg=Theme.BG)
        row1.pack(fill='x', pady=(0, Theme.SPACE_SM))
        InlineToggle(row1, text='输出修订标记（在 Word 中可逐条接受 / 拒绝格式更改）',
                     variable=self.revision_var).pack(side='left')
        info = tk.Label(row1, text='ⓘ 说明', font=get_font(11), bg=Theme.BG,
                        fg=Theme.TEXT_MUTED, cursor='hand2')
        info.pack(side='left', padx=(Theme.SPACE_SM, 0))
        info.bind('<Button-1>', lambda e: self.notice(
            '修订标记只记录字体、字号、缩进、对齐、行距等格式变更'))
        row2 = tk.Frame(section, bg=Theme.BG)
        row2.pack(fill='x')
        InlineToggle(row2, text='处理完成后自动打开输出文件',
                     variable=self.auto_open_var).pack(side='left')

    def _build_run_button(self, parent):
        btn = tk.Frame(parent, bg=Theme.PRIMARY, cursor='hand2')
        btn.pack(fill='x', pady=Theme.SPACE_LG)
        label = tk.Label(btn, text='开始处理', font=get_font(15, 'bold'), bg=Theme.PRIMARY,
                         fg='white', pady=Theme.SPACE_MD + 2, cursor='hand2')
        label.pack()
        for w in (btn, label):
            w.bind('<Button-1>', lambda e: self.notice('这里会开始处理文档'))
            w.bind('<Enter>', lambda e: (btn.configure(bg=Theme.PRIMARY_HOVER),
                                         label.configure(bg=Theme.PRIMARY_HOVER)))
            w.bind('<Leave>', lambda e: (btn.configure(bg=Theme.PRIMARY),
                                         label.configure(bg=Theme.PRIMARY)))

    # ---------- 交互 ----------

    def select_format(self, format_id):
        """选中一个起始格式或我的格式，把它的参数装载进编辑区。"""
        self.state.switch_preset(format_id)
        self.preset_column.set_selected(format_id)
        self.refresh()

    def save_as_new_format(self):
        """把当前生效值存成一份新的「我的格式」（原型只在内存里存）。"""
        count = len(self.preset_column.custom_formats) + 1
        label = '我的格式 %d' % count
        format_id = 'fmt_new_%d' % count
        self.preset_column.add(format_id, label)
        self.preset_column.set_selected(format_id)
        self.state.preset_id = format_id
        self.state.overrides.clear()
        self.refresh()
        # 用摘要行给出反馈，避免原型里弹模态框打断自检
        self.summary.configure(text='已存为「%s」（原型不落盘）' % label,
                               fg=Theme.PRIMARY)
        return label

    def cell_changed(self, element, field, value):
        current = self.state.effective().get(element, {}).get(field)
        if current == value:
            return
        self.state.set_field(element, field, value)
        self.refresh()

    def restore_row(self, element):
        if not self.state.overrides.get(element):
            self.notice('这一行没有改动，无需恢复')
            return
        self.state.restore_row(element)
        self.refresh()

    def restore_all(self):
        if not self.state.override_count():
            self.notice('当前没有改动')
            return
        self.state.restore_all()
        self.refresh()

    def refresh(self):
        changed = self.table.refresh(self.state)
        catalog = dict((p[0], p[1]) for p in STARTING_FORMATS)
        catalog.update(dict(self.preset_column.custom_formats))
        name = catalog.get(self.state.preset_id, self.state.preset_id)
        count = len(changed)
        if changed:
            shown = '、'.join(changed[:4])
            if count > 4:
                shown += ' 等 %d 处' % count
            self.summary.configure(
                text='当前格式：%s　·　已改动：%s' % (name, shown), fg=Theme.PRIMARY)
        else:
            self.summary.configure(text='当前格式：%s　·　未做修改' % name,
                                   fg=Theme.TEXT_MUTED)

    def notice(self, text):
        messagebox.showinfo('界面原型', '%s\n\n（原型不执行真实操作）' % text, parent=self)


# 演示用：改几处参数，方便截图核对覆盖值提示
DEMO_OVERRIDES = (
    ('body', 'font_cn', '楷体_GB2312'),
    ('body', 'line_spacing', 30),
    ('heading1', 'space_before', 12),
    ('heading1', 'bold', True),
)


def main():
    app = PrototypeLayoutB()
    # 起始格式：默认「自定义格式」，也可用 PROTOTYPE_PRESET 指定
    initial = os.environ.get('PROTOTYPE_PRESET', '').strip()
    if initial:
        app.select_format(initial)
    if os.environ.get('PROTOTYPE_DEMO') == '1':
        for element, field, value in DEMO_OVERRIDES:
            app.cell_changed(element, field, value)
    # 格式区默认展开；设 PROTOTYPE_COLLAPSE=1 可启动就折叠（便于截图核对）
    if os.environ.get('PROTOTYPE_COLLAPSE') == '1':
        app.toggle_format_area()
    # 设 PROTOTYPE_SCROLL_END=1 可把预设列滚到底，便于核对滚动效果
    if os.environ.get('PROTOTYPE_SCROLL_END') == '1':
        app.preset_column.canvas.yview_moveto(1.0)
    app.mainloop()


if __name__ == '__main__':
    main()
