import tkinter as tk
from tkinter import font as tkfont

import jarvis.ui.app as appmod
import jarvis.ui.theme as theme


def geometry_ok() -> dict:
    root = tk.Tk()
    root.withdraw()
    app = appmod.JarvisApp(root)

    expected = appmod.W, appmod.H
    actual = (app.root.winfo_width(), app.root.winfo_height())
    resizable = app.root.resizable()
    title = app.root.title()

    check = {
        "title": title,
        "size_expected": expected,
        "size_actual": actual,
        "resizable": resizable,
    }

    root.destroy()
    return check


def panel_checks() -> dict:
    root = tk.Tk()
    root.withdraw()
    app = appmod.JarvisApp(root)

    d = app.desk
    stats = {}
    for tag in ("bg", "min", "close", "voice", "send", "capsule",
                "chip", "status_tts_text", "tts_stop_btn", "legend",
                "legend_name", "status_item"):
        ids = d.find_withtag(tag)
        stats[tag] = [d.coords(it) for it in ids]

    chat = app.chat
    panel_info = {
        "chat_width": app.chat._width,
        "chat_height": app.chat._height,
        "chat_pad": app.chat._pad,
    }

    root.destroy()
    return {"statics": stats, "chat": panel_info}


def font_hierarchy_checks() -> dict:
    fonts = {
        "APP_TITLE": theme.APP_TITLE,
        "APP_SUB": theme.APP_SUB,
        "CHIP_STATE": theme.CHIP_STATE,
        "HEADER": theme.HEADER,
        "HEADER_HINT": theme.HEADER_HINT,
        "ACTION_LABEL": theme.ACTION_LABEL,
        "ACTION_ICON": theme.ACTION_ICON,
        "CHAT_LABEL": theme.CHAT_LABEL,
        "CHAT_BODY": theme.CHAT_BODY,
        "CHAT_SYSTEM": theme.CHAT_SYSTEM,
        "TIME": theme.TIME,
        "STATUS": theme.STATUS,
    }
    root = tk.Tk()
    root.withdraw()
    probe = tkfont.Font(family=theme.SEA, size=10)
    family = probe.actual("family")
    root.destroy()
    return {"fonts_defined": fonts, "probe_family": family}


if __name__ == "__main__":
    print("GEOMETRY", geometry_ok())
    print("PANELS", panel_checks())
    print("FONTS", font_hierarchy_checks())
