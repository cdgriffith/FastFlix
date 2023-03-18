# -*- coding: utf-8 -*-
import logging

import reusables

logger = logging.getLogger("fastflix")

tool_window = None
tool_icon = None
CONTINUOUS = 0x80000000
SYSTEM_REQUIRED = 0x00000001


def show_windows_notification(title, msg, icon_path):
    global tool_window, tool_icon
    from win32api import GetModuleHandle
    from win32con import (
        CW_USEDEFAULT,
        IMAGE_ICON,
        LR_DEFAULTSIZE,
        LR_LOADFROMFILE,
        WM_USER,
        WS_OVERLAPPED,
        WS_SYSMENU,
    )
    from win32gui import (
        NIF_ICON,
        NIF_INFO,
        NIF_MESSAGE,
        NIF_TIP,
        NIM_ADD,
        NIM_MODIFY,
        WNDCLASS,
        CreateWindow,
        LoadImage,
        RegisterClass,
        Shell_NotifyIcon,
        UpdateWindow,
    )

    wc = WNDCLASS()
    hinst = wc.hInstance = GetModuleHandle(None)
    wc.lpszClassName = "FastFlix"
    if not tool_window:
        tool_window = CreateWindow(
            RegisterClass(wc),
            "Taskbar",
            WS_OVERLAPPED | WS_SYSMENU,
            0,
            0,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            0,
            0,
            hinst,
            None,
        )
        UpdateWindow(tool_window)

        icon_flags = LR_LOADFROMFILE | LR_DEFAULTSIZE
        tool_icon = LoadImage(hinst, icon_path, IMAGE_ICON, 0, 0, icon_flags)

        flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid = (tool_window, 0, flags, WM_USER + 20, tool_icon, "FastFlix")
        Shell_NotifyIcon(NIM_ADD, nid)

    Shell_NotifyIcon(
        NIM_MODIFY, (tool_window, 0, NIF_INFO, WM_USER + 20, tool_icon, "Balloon Tooltip", msg, 200, title, 4)
    )


def cleanup_windows_notification():
    try:
        from win32gui import DestroyWindow, UnregisterClass
    except ImportError:
        return
    else:
        if tool_window:
            DestroyWindow(tool_window)
            UnregisterClass("FastFlix", None)


def prevent_sleep_mode():
    """https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx"""
    if reusables.win_based:
        import ctypes

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(CONTINUOUS | SYSTEM_REQUIRED)
        except Exception:
            logger.exception("Could not prevent system from possibly going to sleep during conversion")
        else:
            logger.debug("System has been asked to not sleep")


def allow_sleep_mode():
    if reusables.win_based:
        import ctypes

        try:
            ctypes.windll.kernel32.SetThreadExecutionState(CONTINUOUS)
        except Exception:
            logger.exception("Could not allow system to resume sleep mode")
        else:
            logger.debug("System has been allowed to enter sleep mode again")
