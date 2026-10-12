"""Do not ship desktop builds whose drag-and-drop runtime is missing."""

import sys
from types import SimpleNamespace

import pytest

import build
import docformat_gui as gui


@pytest.fixture
def packaging_hooks(monkeypatch):
    hooks = SimpleNamespace(collect_data_files=None, collect_dynamic_libs=None)
    monkeypatch.setitem(sys.modules, "PyInstaller.utils.hooks", hooks)
    monkeypatch.setitem(sys.modules, "tkinterdnd2", SimpleNamespace(
        TkinterDnD=object, DND_FILES="DND_Files", COPY="copy",
    ))
    return hooks


@pytest.mark.parametrize("build_function", [build.build_windows, build.build_linux])
def test_missing_drag_drop_dependency_stops_packaging(monkeypatch, capsys, build_function):
    monkeypatch.setitem(sys.modules, "tkinterdnd2", None)
    monkeypatch.setattr(build, "_get_docx_templates_path", lambda: None)
    commands = []
    monkeypatch.setattr(build.subprocess, "run", lambda *args, **kwargs: commands.append(args))

    assert build_function() is False
    assert commands == []
    assert "已停止打包" in capsys.readouterr().out


@pytest.mark.parametrize(
    "data_files,dynamic_libs",
    [
        ([], []),
        ([("tkdnd/pkgIndex.tcl", "tkinterdnd2/tkdnd/win-x64")], []),
        ([], [("tkdnd/libtkdnd.dll", "tkinterdnd2/tkdnd/win-x64")]),
    ],
)
def test_incomplete_drag_drop_resources_stop_packaging(monkeypatch, packaging_hooks, data_files, dynamic_libs):
    monkeypatch.setattr(packaging_hooks, "collect_data_files", lambda package: data_files)
    monkeypatch.setattr(packaging_hooks, "collect_dynamic_libs", lambda package: dynamic_libs)

    assert build._get_tkinterdnd_pyinstaller_args("windows") is None


@pytest.mark.parametrize("platform_name,separator,library", [
    ("windows", ";", "libtkdnd.dll"),
    ("linux", ":", "libtkdnd.so"),
])
def test_complete_drag_drop_resources_are_bundled(monkeypatch, packaging_hooks, platform_name, separator, library):
    monkeypatch.setattr(packaging_hooks, "collect_data_files", lambda package: [
        ("tkdnd/pkgIndex.tcl", "tkinterdnd2/tkdnd"),
    ])
    monkeypatch.setattr(packaging_hooks, "collect_dynamic_libs", lambda package: [
        (f"tkdnd/{library}", "tkinterdnd2/tkdnd"),
    ])

    args = build._get_tkinterdnd_pyinstaller_args(platform_name)

    assert "--hidden-import=tkinterdnd2" in args
    assert f"--add-data=tkdnd/pkgIndex.tcl{separator}tkinterdnd2/tkdnd" in args
    assert f"--add-binary=tkdnd/{library}{separator}tkinterdnd2/tkdnd" in args


def test_runtime_load_failure_is_reported_to_the_gui(monkeypatch):
    def fail_to_load():
        raise RuntimeError("Unable to load tkdnd library.")

    monkeypatch.setattr(gui, "_DND_AVAILABLE", True)
    monkeypatch.setattr(gui, "_DND_DISABLED_REASON", "")
    monkeypatch.setattr(gui, "_enable_windows_high_dpi", lambda: None)
    monkeypatch.setattr(gui, "TkinterDnD", SimpleNamespace(Tk=fail_to_load), raising=False)
    monkeypatch.setattr(gui.tk, "Tk", lambda: SimpleNamespace(mainloop=lambda: None))
    monkeypatch.setattr(gui, "_configure_tk_high_dpi", lambda root: None)
    reasons = []
    monkeypatch.setattr(gui, "DocFormatApp", lambda root: reasons.append(gui._DND_DISABLED_REASON))

    gui._legacy_main()

    assert gui._DND_AVAILABLE is False
    assert reasons == ["拖拽运行库加载失败：Unable to load tkdnd library."]
