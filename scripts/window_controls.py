"""Native Windows frame behavior around the custom desktop title bar."""

import ctypes
from ctypes import wintypes


class MINMAXINFO(ctypes.Structure):
    _fields_ = [(name, wintypes.POINT) for name in (
        "ptReserved", "ptMaxSize", "ptMaxPosition", "ptMinTrackSize", "ptMaxTrackSize",
    )]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


def monitor_maximum(monitor, work):
    """Window coordinates are relative to the selected monitor, including negative origins."""
    return (work.left - monitor.left, work.top - monitor.top,
            work.right - work.left, work.bottom - work.top)


class WindowsWindowControls:
    def __init__(self, window):
        self._window = window
        self._hwnd = int(window.native.Handle.ToInt64())
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
        self._callback = None
        self._configure_functions()

    def _configure_functions(self):
        pointer = ctypes.c_ssize_t
        self._subclass_type = ctypes.WINFUNCTYPE(pointer, wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM, ctypes.c_size_t, ctypes.c_size_t)
        signatures = {
            "IsZoomed": ([wintypes.HWND], wintypes.BOOL),
            "IsIconic": ([wintypes.HWND], wintypes.BOOL),
            "GetDpiForWindow": ([wintypes.HWND], wintypes.UINT),
            "GetWindowLongW": ([wintypes.HWND, ctypes.c_int], wintypes.LONG),
            "SetWindowLongW": ([wintypes.HWND, ctypes.c_int, wintypes.LONG], wintypes.LONG),
            "GetWindowRect": ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            "GetClientRect": ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            "ClientToScreen": ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            "MonitorFromWindow": ([wintypes.HWND, wintypes.DWORD], wintypes.HANDLE),
            "GetMonitorInfoW": ([wintypes.HANDLE, ctypes.POINTER(MONITORINFO)], wintypes.BOOL),
            "GetSystemMetricsForDpi": ([ctypes.c_int, wintypes.UINT], ctypes.c_int),
            "ReleaseCapture": ([], wintypes.BOOL),
            "GetCursorPos": ([ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            "GetDoubleClickTime": ([], wintypes.UINT),
            "PostMessageW": ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
            "SetWindowPos": ([wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.BOOL),
            "ShowWindow": ([wintypes.HWND, ctypes.c_int], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self._user32, name)
            function.argtypes = arguments
            function.restype = result
        self._comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, self._subclass_type,
                                                     ctypes.c_size_t, ctypes.c_size_t]
        self._comctl32.SetWindowSubclass.restype = wintypes.BOOL
        self._comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT,
                                                   wintypes.WPARAM, wintypes.LPARAM]
        self._comctl32.DefSubclassProc.restype = pointer
        self._comctl32.RemoveWindowSubclass.argtypes = [wintypes.HWND, self._subclass_type, ctypes.c_size_t]
        self._comctl32.RemoveWindowSubclass.restype = wintypes.BOOL

    def state(self):
        return {"maximized": bool(self._user32.IsZoomed(self._hwnd)),
                "minimized": bool(self._user32.IsIconic(self._hwnd)), "nativeDrag": True,
                "doubleClickTime": self._user32.GetDoubleClickTime()}

    def begin_drag(self):
        # Let Windows own the move loop, snapping and restore-from-maximized behavior.
        self._begin_nonclient_operation(2)  # HTCAPTION

    def _begin_nonclient_operation(self, hit):
        from System import Action
        def begin_on_gui_thread():
            self._user32.ReleaseCapture()
            point = wintypes.POINT()
            self._user32.GetCursorPos(ctypes.byref(point))
            position = (point.x & 0xffff) | ((point.y & 0xffff) << 16)
            self._user32.PostMessageW(self._hwnd, 0x00A1, hit, position)
        self._window.native.Invoke(Action(begin_on_gui_thread))

    def begin_resize(self, edge):
        edges = {"left": 10, "right": 11, "top": 12, "top-left": 13,
                 "top-right": 14, "bottom": 15, "bottom-left": 16, "bottom-right": 17}
        if edge not in edges:
            raise ValueError("未知缩放边缘。")
        if self._user32.IsZoomed(self._hwnd) or self._user32.IsIconic(self._hwnd):
            return
        self._begin_nonclient_operation(edges[edge])

    def action(self, action):
        from System import Action
        commands = {"minimize": 6, "maximize": 3, "restore": 9}
        command = commands[action]
        # WinForms assumes its managed border style when calculating restore bounds.
        # Use Windows' saved placement so our custom sizing border cannot shrink it.
        self._window.native.Invoke(Action(lambda: self._user32.ShowWindow(self._hwnd, command)))

    def install(self):
        from System import Action

        def install_on_gui_thread():
            def sync_browser_bounds():
                if self._user32.IsIconic(self._hwnd):
                    return
                view = self._window.native.webview
                if view.IsDisposed or not view.IsHandleCreated:
                    return
                client = wintypes.RECT()
                origin = wintypes.POINT()
                if not self._user32.GetClientRect(self._hwnd, ctypes.byref(client)):
                    return
                self._user32.ClientToScreen(self._hwnd, ctypes.byref(origin))
                child = int(view.Handle.ToInt64())
                actual = wintypes.RECT()
                self._user32.GetWindowRect(child, ctypes.byref(actual))
                if (actual.left, actual.top, actual.right, actual.bottom) != (
                    origin.x, origin.y, origin.x+client.right, origin.y+client.bottom
                ):
                    # A frameless WinForms restore can leave the WebView at the
                    # minimized (-32000,-32000) coordinate offset. Correct the
                    # native child, even when managed Bounds still reports (0,0).
                    self._user32.SetWindowPos(child, None, 0, 0, client.right, client.bottom,
                                             0x0004 | 0x0010)

            def procedure(hwnd, message, wparam, lparam, subclass_id, reference):
                if message == 0x0084:  # WM_NCHITTEST
                    # The invisible native caption must not intercept browser
                    # buttons. Browser edge/title handlers enter native loops.
                    return 1  # HTCLIENT
                if message == 0x0083:  # WM_NCCALCSIZE
                    if self._user32.IsIconic(hwnd):
                        return self._comctl32.DefSubclassProc(hwnd, message, wparam, lparam)
                    # Match WinForms' borderless restore bookkeeping: the browser
                    # fills the outer rectangle. Edge handles start native sizing.
                    if self._user32.IsZoomed(hwnd):
                        monitor = self._user32.MonitorFromWindow(hwnd, 2)
                        info = MONITORINFO()
                        info.cbSize = ctypes.sizeof(info)
                        if self._user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                            # Windows places the invisible maximized resize border
                            # outside the work area; keep our visible client inside.
                            rect = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                            rect.left, rect.top = info.rcWork.left, info.rcWork.top
                            rect.right, rect.bottom = info.rcWork.right, info.rcWork.bottom
                    return 0
                if message == 0x0024:  # WM_GETMINMAXINFO
                    result = self._comctl32.DefSubclassProc(hwnd, message, wparam, lparam)
                    monitor = self._user32.MonitorFromWindow(hwnd, 2)
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(info)
                    if self._user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                        x, y, width, height = monitor_maximum(info.rcMonitor, info.rcWork)
                        limits = ctypes.cast(lparam, ctypes.POINTER(MINMAXINFO)).contents
                        limits.ptMaxPosition.x, limits.ptMaxPosition.y = x, y
                        limits.ptMaxSize.x, limits.ptMaxSize.y = width, height
                        limits.ptMinTrackSize.x = min(limits.ptMinTrackSize.x, width)
                        limits.ptMinTrackSize.y = min(limits.ptMinTrackSize.y, height)
                    return result
                if message == 0x0082:  # WM_NCDESTROY
                    self._comctl32.RemoveWindowSubclass(hwnd, self._callback, 1)
                result = self._comctl32.DefSubclassProc(hwnd, message, wparam, lparam)
                if message == 0x0047:  # WM_WINDOWPOSCHANGED, after managed layout
                    sync_browser_bounds()
                return result

            self._callback = self._subclass_type(procedure)
            if not self._comctl32.SetWindowSubclass(self._hwnd, self._callback, 1, 0):
                raise ctypes.WinError(ctypes.get_last_error())
            style = self._user32.GetWindowLongW(self._hwnd, -16) & 0xffffffff
            # Keep standard overlapped-window semantics for sizing, snapping and
            # system commands; WM_NCCALCSIZE hides the native caption visually.
            style = (style & ~0x80000000) | 0x00CF0000
            self._user32.SetWindowLongW(self._hwnd, -16, style)
            dpi = self._user32.GetDpiForWindow(self._hwnd) or 96
            self._user32.SetWindowPos(self._hwnd, None, 0, 0,
                round(self._window.initial_width * dpi / 96),
                round(self._window.initial_height * dpi / 96),
                0x0002 | 0x0004 | 0x0020)

        # comctl32 requires installing a subclass on the window's own GUI thread.
        self._window.native.Invoke(Action(install_on_gui_thread))
