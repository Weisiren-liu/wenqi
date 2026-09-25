#!/usr/bin/env python3
"""Run the BASELINE GUI "smart one-click" pipeline on one docx.

This script is executed against an OLD checkout (git worktree of 09d8aa5,
before the P0/P1/P2 work): it imports THAT checkout's docformat_gui and
scripts.formatter, drives the real baseline GUI object end to end in smart
mode (punctuation fix + formatting), and writes the processed docx.

Usage:
  python _e2e_baseline_run.py <baseline_root> <input_docx> <output_docx> \
      <artifacts_json> [settings_json]

settings_json is optional: when given, it is a settings dict (same shape as
DEFAULT_CUSTOM_SETTINGS) written into the baseline config as the active user
preset, so both sides process with byte-identical format parameters.

ASCII-only by design (must run under any console codepage).
"""
import json
import os
import sys
import time


def main():
    if len(sys.argv) < 5:
        print('usage: _e2e_baseline_run.py <baseline_root> <input> <output> <artifacts> [settings]')
        return 2
    root_dir, input_path, output_path, artifacts = sys.argv[1:5]
    settings_json = sys.argv[5] if len(sys.argv) > 5 else None

    sys.path.insert(0, root_dir)

    import tkinter as tk
    from tkinter import messagebox
    import docformat_gui as gui

    for name in ('showinfo', 'showwarning', 'showerror', 'askyesno',
                 'askyesnocancel', 'askretrycancel'):
        setattr(messagebox, name, lambda *a, **k: None)

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(output_path)),
                            'baseline_custom_settings.json')
    gui.CONFIG_FILE = gui.Path(cfg_path)
    try:
        gui.DocFormatApp._maybe_show_community_notice = lambda self: None
    except Exception:
        pass

    if settings_json:
        with open(settings_json, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        preset_id = '0e2e-baseline-active'
        gui.save_custom_settings({
            'schema_version': gui.CONFIG_SCHEMA_VERSION,
            'active_preset_id': preset_id,
            'presets': [dict(settings, id=preset_id, name='E2E baseline',
                             is_builtin=False)],
        })

    root = tk.Tk()
    if hasattr(gui, '_configure_tk_high_dpi'):
        gui._configure_tk_high_dpi(root)
    app = gui.DocFormatApp(root)
    root.update()

    # Record the exact settings the baseline pipeline will use.
    try:
        active = gui.get_active_user_preset(gui.load_custom_settings())
    except Exception as exc:
        active = {'_error': str(exc)}
    with open(artifacts, 'w', encoding='utf-8') as f:
        json.dump({'active_settings': active,
                   'default_custom_settings': gui.DEFAULT_CUSTOM_SETTINGS},
                  f, ensure_ascii=False, indent=2)

    app.preset.set('custom')
    if hasattr(app, 'auto_open_var'):
        app.auto_open_var.set(False)
    app.input_files = [input_path]
    app.output_file.set(output_path)
    app.operation.set('smart')
    app.run_operation()

    # Drive a real mainloop: the worker thread posts Tk calls via after(),
    # which only works while the main thread sits in mainloop().
    state = {'deadline': time.time() + 300}

    def poll():
        if os.path.exists(output_path) and not app._processing_active:
            root.quit()
            return
        if time.time() > state['deadline']:
            root.quit()
            return
        root.after(100, poll)

    root.after(100, poll)
    root.mainloop()
    for _ in range(20):
        root.update()
        time.sleep(0.05)
    root.destroy()

    if not os.path.exists(output_path):
        print('BASELINE OUTPUT MISSING')
        return 2
    print('BASELINE OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
