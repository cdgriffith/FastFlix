# -*- coding: utf-8 -*-


tool_window = None
tool_icon = None


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
        nid = (tool_window, 0, flags, WM_USER + 20, tool_icon, "FastFlix Notifications")
        Shell_NotifyIcon(NIM_ADD, nid)

    Shell_NotifyIcon(
        NIM_MODIFY, (tool_window, 0, NIF_INFO, WM_USER + 20, tool_icon, "Balloon Tooltip", msg, 200, title, 4)
    )


def cleanup_windows_notification():
    from win32gui import DestroyWindow, UnregisterClass

    if tool_window:
        DestroyWindow(tool_window)
        UnregisterClass("FastFlix", None)
