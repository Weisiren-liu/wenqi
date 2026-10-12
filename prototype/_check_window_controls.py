"""Exercise real Windows placement, minimize/restore, dragging and edge resizing."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.desktop_ui import create_window
import docformat_gui as model
import webview
import win32api
import win32con
import win32gui


def main():
    failure = []
    original_cursor = win32api.GetCursorPos()
    with TemporaryDirectory(prefix="wenqi-window-check-") as work:
        model.CONFIG_FILE = Path(work) / "settings.json"
        window, api = create_window()

        def check():
            try:
                assert window.events.loaded.wait(20)
                deadline = time.monotonic() + 10
                while not api._window_controls and time.monotonic() < deadline:
                    time.sleep(.1)
                assert api._window_controls
                time.sleep(.3)
                hwnd = int(window.native.Handle.ToInt64())
                original = win32gui.GetWindowRect(hwnd)
                workarea = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd, 2))["Work"]
                def client_bounds():
                    bounds = win32gui.GetClientRect(hwnd)
                    return (*win32gui.ClientToScreen(hwnd, bounds[:2]),
                            *win32gui.ClientToScreen(hwnd, bounds[2:]))
                for _ in range(3):
                    api.window_action("maximize")
                    time.sleep(.15)
                    assert api.window_state()["maximized"]
                    assert client_bounds() == workarea, (client_bounds(), workarea)
                    api.window_action("maximize")
                    time.sleep(.15)
                    assert not api.window_state()["maximized"]
                    assert win32gui.GetWindowRect(hwnd) == original
                api.window_action("minimize")
                assert api.window_state()["minimized"]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(.2)
                assert win32gui.GetWindowRect(hwnd) == original
                # Simulate a system maximize, bypassing the browser button.
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                api.window_action("maximize")
                time.sleep(.2)
                assert win32gui.GetWindowRect(hwnd) == original
                api.window_action("maximize")
                api.window_action("minimize")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(.2)
                assert api.window_state()["maximized"]
                api.window_action("maximize")
                assert win32gui.GetWindowRect(hwnd) == original
                print("MAXIMUM WORK AREA / REPEATED RESTORE / NORMAL AND MAXIMIZED TASKBAR RESTORE: OK", flush=True)

                window.move(100, 100)
                time.sleep(.2)
                win32gui.SetForegroundWindow(hwnd)
                edges = {
                    "left": (2, .5), "right": (-2, .5), "top": (.5, 2), "bottom": (.5, -2),
                    "top-left": (3, 3), "top-right": (-3, 3),
                    "bottom-left": (3, -3), "bottom-right": (-3, -3),
                }
                for edge, (x, y) in edges.items():
                    window.resize(1000, 740)
                    window.move(100, 100)
                    time.sleep(.5)
                    rect = win32gui.GetWindowRect(hwnd)
                    width, height = rect[2] - rect[0], rect[3] - rect[1]
                    local_x = round(width*x) if 0<x<1 else width+x if x<0 else x
                    local_y = round(height*y) if 0<y<1 else height+y if y<0 else y
                    start = (rect[0]+local_x, rect[1]+local_y)
                    # Never inject a click into another application's window.
                    target = win32gui.WindowFromPoint(start)
                    assert win32gui.GetAncestor(target, win32con.GA_ROOT) == hwnd
                    win32api.SetCursorPos(start)
                    time.sleep(.12)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                    time.sleep(.2)
                    dx = -30 if "left" in edge else 30 if "right" in edge else 0
                    dy = -20 if "top" in edge else 20 if "bottom" in edge else 0
                    win32api.SetCursorPos((start[0]+dx, start[1]+dy))
                    time.sleep(.2)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                    time.sleep(.15)
                    resized = win32gui.GetWindowRect(hwnd)
                    assert resized != rect, (edge, rect, resized)
                    if dx:
                        assert resized[2]-resized[0] > width, (edge, resized)
                    if dy:
                        assert resized[3]-resized[1] > height, (edge, resized)
                    print("NATIVE EDGE DRAG", edge, "OK", flush=True)
                # Drag the title bar using the real native move loop.
                window.move(100, 100)
                time.sleep(.2)
                before = win32gui.GetWindowRect(hwnd)
                point = win32gui.ClientToScreen(hwnd, (220, 35))
                assert win32gui.GetAncestor(win32gui.WindowFromPoint(point), win32con.GA_ROOT) == hwnd
                win32api.SetCursorPos(point)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                time.sleep(.2)
                win32api.SetCursorPos((point[0]+50, point[1]+25))
                time.sleep(.2)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                time.sleep(.2)
                after = win32gui.GetWindowRect(hwnd)
                assert after[0] != before[0] and after[1] != before[1]
                assert after[2]-after[0] == before[2]-before[0]
                assert after[3]-after[1] == before[3]-before[1]
                print("NATIVE TITLE DRAG: OK", flush=True)

                def click_button(action):
                    selector = "[data-window=" + action + "]"
                    point = window.evaluate_js("(function(){const r=document.querySelector('" + selector + "').getBoundingClientRect();return [Math.round(r.x+r.width/2),Math.round(r.y+r.height/2)]})()")
                    point = win32gui.ClientToScreen(hwnd, tuple(point))
                    assert win32gui.GetAncestor(win32gui.WindowFromPoint(point), win32con.GA_ROOT) == hwnd
                    win32api.SetCursorPos(point)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                    time.sleep(.04)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                    time.sleep(.35)

                placement = win32gui.GetWindowRect(hwnd)
                click_button("maximize")
                assert api.window_state()["maximized"]
                assert client_bounds() == workarea
                click_button("maximize")
                assert win32gui.GetWindowRect(hwnd) == placement
                click_button("minimize")
                assert api.window_state()["minimized"]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(.2)
                assert win32gui.GetWindowRect(hwnd) == placement
                print("PHYSICAL MAXIMIZE / RESTORE / MINIMIZE BUTTON CLICKS: OK", flush=True)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(.2)
                point = win32gui.ClientToScreen(hwnd, (220, 35))
                assert win32gui.GetAncestor(win32gui.WindowFromPoint(point), win32con.GA_ROOT) == hwnd
                win32api.SetCursorPos(point)
                for _ in range(2):
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                    time.sleep(.04)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                    time.sleep(.07)
                deadline = time.monotonic()+2
                while not api.window_state()["maximized"] and time.monotonic()<deadline:
                    time.sleep(.1)
                assert api.window_state()["maximized"], "Title bar double click did not maximize"
                api.window_action("maximize")
                print("PHYSICAL TITLE DOUBLE CLICK: OK", flush=True)
                time.sleep(.3)
            except Exception:
                failure.append(traceback.format_exc())
                print(failure[-1], flush=True)
            finally:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
                win32api.SetCursorPos(original_cursor)
                window.destroy()

        webview.start(check, gui="edgechromium")
    if failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
