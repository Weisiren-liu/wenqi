from ctypes import wintypes
from types import SimpleNamespace

import pytest

from scripts.window_controls import monitor_maximum
from scripts.desktop_ui import DesktopApi


@pytest.mark.parametrize("monitor,work,expected", [
    ((0, 0, 2560, 1440), (0, 0, 2560, 1392), (0, 0, 2560, 1392)),
    ((-1920, 0, 0, 1080), (-1920, 30, 0, 1080), (0, 30, 1920, 1050)),
    ((2560, -200, 4480, 880), (2608, -200, 4480, 880), (48, 0, 1872, 1080)),
])
def test_maximum_respects_taskbar_and_monitor_origin(monitor, work, expected):
    assert monitor_maximum(wintypes.RECT(*monitor), wintypes.RECT(*work)) == expected


def test_maximize_uses_actual_system_state_after_external_changes():
    actual = {"maximized": True, "minimized": False, "nativeDrag": True}
    commands = []

    def apply(command):
        commands.append(command)
        actual["maximized"] = command == "maximize"

    api = object.__new__(DesktopApi)
    api._window_controls = SimpleNamespace(state=lambda: dict(actual), action=apply)
    api.window_action("maximize")
    assert commands == ["restore"]
    actual["maximized"] = False  # Windows restored it outside our button handler.
    api.window_action("maximize")
    assert commands == ["restore", "maximize"]
