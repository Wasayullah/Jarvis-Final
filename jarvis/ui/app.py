"""JARVIS: modern elegant desktop AI assistant.

A borderless dark-mode application with minimal AI visualizer orb,
curated quick actions, smooth conversation panel and unified input controls.
"""

import datetime
import math
import os
import random
import threading
import time
import tkinter as tk
import webbrowser

from config import config
from jarvis import ai_engine, command, memory
from jarvis.skills import websites_skill
from jarvis.stt import VoiceInput
from jarvis.tts import Speaker
from jarvis.ui import theme
from jarvis.ui.widgets import ChatPanel, Gear, mix, rounded_rect

W, H = 1100, 640
XM = 18

X_LEFT, W_LEFT = 18, 250
GX, CY = 480, 310
GEAR_SIZE = 300
CX, CW = 700, 382
PANEL_TOP, PANEL_BOT = 62, 596

STATES = {
    "idle": theme.VIS_IDLE,
    "thinking": theme.VIS_THINK,
    "speaking": theme.VIS_SPEAK,
    "listening": theme.VIS_LISTEN,
}


class JarvisApp:
    QUICK_ACTIONS = [
        ("Time", "what is the time", "\u23f1"),
        ("Date", "what is the date today", "\U0001f4c5"),
        ("Screenshot", "take screenshot", "\U0001f4f8"),
        ("Chrome", "open chrome", "\U0001f310"),
        ("VS Code", "open vscode", "\U0001f4bb"),
        ("Terminal", "open cmd", ">_"),
        ("Joke", "tell me a joke", "\u2728"),
        ("System Info", "system info", "\u2699"),
        ("Google", "google", "\U0001f50d"),
        ("Wikipedia", "wikipedia", "\U0001f4d6"),
        ("Notepad", "open notepad", "\U0001f4dd"),
    ]

    def __init__(self, root: tk.Tk):
        config.ensure_dirs()
        self.root = root
        self._drag = None
        self._closed = False
        self._frame = 0
        self._locked = False
        self._thinking = False
        self._command_counter = 0
        self._current_command = None
        self._speaking_now = False
        self.voice_input_enabled = False
        self._stt = None
        self._voice_thread = None
        self._username = "user"
        self.display_name = "User"
        self._command_history = []
        self._history_index = -1
        self._gen = 0

        root.title("JARVIS")
        root.geometry(f"{W}x{H}")
        root.resizable(False, False)
        root.configure(bg=theme.CORNER)
        root.overrideredirect(True)
        try:
            root.attributes("-transparentcolor", theme.CORNER)
        except Exception:
            pass

        self._len = None
        self._setup_taskbar()

        self.speaker = Speaker(on_state_change=self._on_speaker_state)
        self._tts_available = self.speaker.enabled
        self.tts_enabled = self._tts_available
        root.bind("<Map>", self._restore_decoration)

        self.desk = tk.Canvas(
            root, width=W, height=H, bg=theme.CORNER, highlightthickness=0, bd=0
        )
        self.desk.pack()

        self.gear = Gear()
        self._particles = []

        self._build_hub()
        self.root.after(200, self._ask_username)

        self._spawn_particles()
        self._start_loops()
        self.root.after(400, lambda: self.entry.focus_force())

    # ------------------------------------------------------------ window mgmt
    def _setup_taskbar(self):
        """Force this borderless window to show a taskbar button with an icon,
        and set the app's taskbar icon. Works via the Windows API."""
        # 1) Window icon (from bundled PNG; falls back silently).
        try:
            from PIL import Image, ImageTk

            img_path = os.path.join(os.path.dirname(__file__), "..", "image.png")
            if os.path.isfile(img_path):
                img = Image.open(img_path).resize((32, 32), Image.LANCZOS)
                self._tray_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self._tray_icon)
        except Exception:
            pass

        # 2) Force the borderless window into the Windows taskbar via
        #    WS_EX_APPWINDOW. tkinter's overrideredirect strips the owner so,
        #    without this, no button appears.
        try:
            import ctypes
            from ctypes import wintypes

            HWND = wintypes.HWND
            GetParent = ctypes.windll.user32.GetParent
            GetWindowLong = ctypes.windll.user32.GetWindowLongW
            SetWindowLong = ctypes.windll.user32.SetWindowLongW
            ShowWindow = ctypes.windll.user32.ShowWindow
            FindWindowW = ctypes.windll.user32.FindWindowW
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            SW_SHOW = 5

            hwnd = self.root.winfo_id()
            parent = GetParent(hwnd)
            if parent:
                hwnd = parent
            style = GetWindowLong(hwnd, GWL_EXSTYLE)
            style |= WS_EX_APPWINDOW
            SetWindowLong(hwnd, GWL_EXSTYLE, style)
            ShowWindow(hwnd, SW_SHOW)
            self._hwnd = hwnd
        except Exception:
            pass

    def _maybe_drag_start(self, e):
        items = self.desk.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        for item in items:
            tags = self.desk.gettags(item)
            if any(
                t in tags
                for t in (
                    "voice",
                    "min",
                    "close",
                    "send",
                    "stopbtn",
                    "ttsbtn",
                    "capsule",
                    "browse",
                    "clear",
                    "themetoggle",
                )
            ):
                self._drag = None
                return
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _maybe_drag(self, e):
        if self._drag:
            x = e.x_root - self._drag[0]
            y = e.y_root - self._drag[1]
            self.root.geometry(f"+{x}+{y}")
            self._drag = (e.x_root - x, e.y_root - y)

    def _drag_end(self, _e=None):
        self._drag = None

    def _minimize(self):
        """Minimize to the taskbar (even though the window is borderless)."""
        hwnd = getattr(self, "_hwnd", None)
        if hwnd:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                return
            except Exception:
                pass
        self.root.overrideredirect(False)
        self.root.iconify()

    def _restore_decoration(self, _e=None):
        # Re-assert the borderless style, and make sure the taskbar button
        # (WS_EX_APPWINDOW) is present again after map/restore.
        self._setup_taskbar()
        self.root.after(120, lambda: self.root.overrideredirect(True))
        self.root.overrideredirect(True)

    def _on_canvas_click(self, e):
        items = self.desk.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        for item in items:
            tags = self.desk.gettags(item)
            if any(
                t in tags
                for t in (
                    "voice",
                    "min",
                    "close",
                    "send",
                    "ttsbtn",
                    "capsule",
                    "browse",
                    "clear",
                    "themetoggle",
                )
            ):
                return
        self.entry.focus_force()

    def _close(self):
        def finish():
            # Let the goodbye sentence finish speaking before we quit.
            if self.speaker and self.speaker.enabled:
                self.speaker.wait_until_idle(timeout=12)
            self.root.destroy()

        def fade(step=0):
            if step >= 12:
                finish()
                return
            self.root.attributes("-alpha", 1.0 - step * 0.09)
            self.root.after(18, lambda: fade(step + 1))

        self._closed = True
        self.voice_input_enabled = False
        if getattr(self, "_stt", None):
            self._stt.close()
        fade()

    # ------------------------------------------------------------ background
    def _spawn_particles(self):
        self._particles = []
        for _ in range(24):
            self._particles.append({
                "x": random.uniform(GX - 220, GX + 220),
                "y": random.uniform(PANEL_TOP + 40, PANEL_BOT - 60),
                "vx": random.uniform(-0.14, 0.14),
                "vy": random.uniform(-0.08, 0.08),
                "r": random.uniform(0.6, 1.4),
                "ph": random.uniform(0, 6.28),
            })

    def _draw_ambient(self):
        d = self.desk
        d.delete("part")
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < GX - 240 or p["x"] > GX + 240:
                p["vx"] *= -1
            if p["y"] < PANEL_TOP + 20 or p["y"] > PANEL_BOT - 40:
                p["vy"] *= -1
            tw = 0.5 + 0.5 * math.sin(self._frame * 0.03 + p["ph"])
            col = mix(theme.ACCENT, theme.BODY, 0.92 + 0.05 * tw)
            d.create_oval(
                p["x"] - p["r"],
                p["y"] - p["r"],
                p["x"] + p["r"],
                p["y"] + p["r"],
                fill=col,
                outline="",
                tags="part",
            )

    def _draw_core_glow(self):
        d = self.desk
        d.delete("glow")
        accent = STATES.get(self.gear.state, theme.ACCENT)
        pulse = 0.5 + 0.5 * math.sin(self._frame * 0.04)
        for i, w in enumerate((18, 10, 5)):
            r = (GEAR_SIZE * 0.46 + pulse * GEAR_SIZE * 0.03) * (i / 3.0 + 0.6)
            d.create_oval(
                GX - r,
                CY - r,
                GX + r,
                CY + r,
                outline=mix(accent, theme.BODY, 0.95 + i * 0.02),
                width=w,
                tags="glow",
            )

    def _tick_loop(self, _gen=None):
        if self._closed or (_gen is not None and _gen != self._gen):
            return
        self._frame += 1
        self.gear.step()
        self._draw_ambient()
        self._draw_core_glow()
        self.gear.draw(self.desk, GX, CY, GEAR_SIZE)
        self._pulse_logo()
        self._pulse_chip()
        self._pulse_voice()
        g = _gen if _gen is not None else self._gen
        self.root.after(33, lambda: self._tick_loop(g))

    def _tick_clock(self, _gen=None):
        if self._closed or (_gen is not None and _gen != self._gen):
            return
        now = datetime.datetime.now()
        date_str = now.strftime("%d %b %Y")
        time_str = now.strftime("%I:%M %p")
        try:
            self.desk.itemconfig(self.clock_item, text=f"{date_str}   {time_str}")
        except Exception:
            pass
        g = _gen if _gen is not None else self._gen
        self.root.after(1000, lambda: self._tick_clock(g))

    def _start_loops(self):
        g = self._gen
        self.root.after(33, lambda: self._tick_loop(g))
        self.root.after(1000, lambda: self._tick_clock(g))

    def _pulse_voice(self):
        if not self.voice_input_enabled:
            return
        r = 2.6 + 1.1 * abs(math.sin(self._frame * 0.16))
        vcx = CX + CW - 78
        vcy = PANEL_BOT - 34
        self.desk.coords(
            self.voice_dot,
            vcx + 8 - r,
            vcy - 10 - r,
            vcx + 8 + r,
            vcy - 10 + r,
        )
        # Keep chip "active" only while voice is on
        self._chip_bar_active = True
        # Live countdown for the fixed listening window
        started = getattr(self, "_voice_started", None)
        if started is not None:
            remaining = 5 - (time.time() - started)
            secs = max(0, int(math.ceil(remaining)))
            label = f"Listening… {secs}s"
            self.desk.itemconfig(self.chip_state_text, text=label)
            self.desk.itemconfig(self.legend, text=label)

    # ------------------------------------------------------------ chrome items
    def _pulse_logo(self):
        d = self.desk
        r = 3.5 + 1.2 * abs(math.sin(self._frame * 0.06))
        d.coords(self._logo_hot, 42 - r, 42 - r, 42 + r, 42 + r)
        d.coords(
            self._logo_ring,
            42 - r * 1.8,
            42 - r * 1.8,
            42 + r * 1.8,
            42 + r * 1.8,
        )

    def _pulse_chip(self):
        d = self.desk
        # Subtle bottom-edge pulse bar + dot glide on the status chip when active
        if self._chip_bar_active:
            phase = (self._frame * 0.05) % 1.0
            x0 = GX - 124
            x1 = GX - 124 + 11 * phase
            d.coords(self._chip_bar, x0, 55, x1, 55)
            d.itemconfig(self._chip_bar, fill=theme.ACCENT)
            gx = GX - 118 + 16 * phase
            d.coords(self._chip_glide, gx - 2, 40 - 2, gx + 2, 40 + 2)
        else:
            d.coords(self._chip_bar, 0, 0, 0, 0)
            d.coords(self._chip_glide, 0, 0, 0, 0)

    def _draw_control_pill(
        self, x1, y1, x2, y2, tag, fill=None, outline=None, radius=12
    ):
        d = self.desk
        fill = fill or theme.GLASS_3
        outline = outline or theme.GLASS_BORDER
        return rounded_rect(
            d,
            x1,
            y1,
            x2,
            y2,
            radius,
            fill=fill,
            outline=outline,
            width=1,
            tags=(tag,),
        )

    # ------------------------------------------------------------ UI build
    def _build_hub(self):
        d = self.desk

        # Window body
        rounded_rect(
            d,
            2,
            2,
            W - 2,
            H - 2,
            20,
            fill=theme.BODY,
            outline=theme.GLASS_BORDER,
            width=1,
            tags=("bg", "dzone"),
        )
        d.tag_bind("dzone", "<ButtonPress-1>", self._maybe_drag_start)
        d.tag_bind("dzone", "<B1-Motion>", self._maybe_drag)
        d.tag_bind("dzone", "<ButtonRelease-1>", self._drag_end)
        d.bind(
            "<ButtonPress-1>",
            lambda e: self._on_canvas_click(e),
            add="+",
        )

        self._build_header()
        self._build_side_panel()
        self._build_chat_panel()
        self._build_status_bar()

        # Visualizer state & credits
        self.legend = d.create_text(
            GX,
            PANEL_BOT - 68,
            text="",
            fill=theme.ACCENT,
            font=theme.CHIP_STATE,
            anchor="n",
            tags="statics",
        )
        self._set_state("idle", "Ready")

    def _build_header(self):
        d = self.desk

        # Logo
        d.create_oval(
            42 - 6, 42 - 6, 42 + 6, 42 + 6, outline=theme.BORDER, width=1, tags="statics"
        )
        self._logo_hot = d.create_oval(
            0, 0, 0, 0, fill=theme.ACCENT, outline="", tags="statics"
        )
        self._logo_ring = d.create_oval(
            0, 0, 0, 0, outline=theme.ACCENT, width=1.5, tags="statics"
        )
        d.create_text(
            64,
            33,
            text="JARVIS",
            anchor="w",
            fill=theme.ACCENT,
            font=theme.APP_TITLE,
            tags=("statics",),
        )
        d.create_text(
            65,
            50,
            text="Personal AI Assistant",
            anchor="w",
            fill=theme.MUTED,
            font=theme.APP_SUB,
            tags=("statics",),
        )

        # Header Status Chip (Center)
        chip = self._draw_control_pill(
            GX - 132, 24, GX + 132, 58, "chip", fill=theme.CHIP, outline=theme.BORDER, radius=18
        )
        d.tag_bind(
            "chip", "<Enter>", lambda e: d.itemconfig(chip, outline=theme.ACCENT)
        )
        d.tag_bind(
            "chip", "<Leave>", lambda e: d.itemconfig(chip, outline=theme.BORDER)
        )
        self.chip_state_dot = d.create_oval(
            GX - 103, 36, GX - 95, 44, fill=theme.ACCENT, outline="", tags="statics"
        )
        self.chip_state_text = d.create_text(
            GX - 86,
            40,
            anchor="w",
            text="Ready",
            font=theme.CHIP_STATE,
            fill=theme.ACCENT,
            tags="statics",
        )
        self._chip_bar = d.create_line(0, 0, 0, 0, fill=theme.ACCENT_SUB, width=1, tags="statics")
        self._chip_glide = d.create_oval(0, 0, 0, 0, fill=theme.ACCENT, outline="", tags="statics")

        # Right Controls: Clock / Theme Toggle / Minimize / Close
        self.clock_item = d.create_text(
            W - 200,
            41,
            anchor="e",
            text="",
            fill=theme.MUTED,
            font=theme.TIME,
            tags="statics",
        )

        # Theme toggle (light / dark) button
        theme_fill = theme.GLASS_3
        theme_outline = theme.GLASS_BORDER
        self.theme_btn = self._draw_control_pill(
            W - 190, 26, W - 160, 56, "themetoggle",
            fill=theme_fill, outline=theme_outline, radius=10,
        )
        self.theme_icon = d.create_text(
            W - 175,
            41,
            text="\u263e" if theme.is_dark() else "\u2600",
            fill=theme.TEXT,
            font=(theme.FONT_FAMILY, 12),
            tags="themetoggle",
        )
        d.tag_bind(
            "themetoggle", "<ButtonPress-1>",
            lambda e: (self._toggle_theme(), "break")[1],
        )
        d.tag_bind(
            "themetoggle", "<Enter>",
            lambda e: d.itemconfig(self.theme_btn, outline=theme.ACCENT),
        )
        d.tag_bind(
            "themetoggle", "<Leave>",
            lambda e: d.itemconfig(self.theme_btn, outline=theme.GLASS_BORDER),
        )

        self.min_btn = self._draw_control_pill(
            W - 96, 26, W - 66, 56, "min", fill=theme.GLASS_3, outline=theme.GLASS_BORDER, radius=10
        )
        d.create_text(
            W - 81,
            41,
            text="\u2500",
            fill=theme.TEXT,
            font=theme.STATUS,
            tags=(),
        )
        d.tag_bind("min", "<ButtonPress-1>", lambda e: (self._minimize(), "break")[1])
        d.tag_bind(
            "min", "<Enter>", lambda e: d.itemconfig(self.min_btn, outline=theme.ACCENT)
        )
        d.tag_bind(
            "min", "<Leave>", lambda e: d.itemconfig(self.min_btn, outline=theme.GLASS_BORDER)
        )

        self.close_btn = self._draw_control_pill(
            W - 58, 26, W - 28, 56, "close", fill=theme.GLASS_3, outline=theme.GLASS_BORDER, radius=10
        )
        d.create_text(
            W - 43,
            41,
            text="\u2715",
            fill=theme.ACCENT_ERR,
            font=(theme.FONT_FAMILY, 11, "bold"),
            tags=(),
        )
        d.tag_bind("close", "<ButtonPress-1>", lambda e: (self._close(), "break")[1])
        d.tag_bind(
            "close", "<Enter>", lambda e: d.itemconfig(self.close_btn, outline=theme.ACCENT_ERR)
        )
        d.tag_bind(
            "close", "<Leave>", lambda e: d.itemconfig(self.close_btn, outline=theme.GLASS_BORDER)
        )

    def _build_side_panel(self):
        d = self.desk
        rounded_rect(
            d,
            X_LEFT,
            PANEL_TOP,
            X_LEFT + W_LEFT,
            PANEL_BOT,
            18,
            fill=theme.GLASS,
            outline=theme.GLASS_BORDER,
            width=1,
            tags="statics",
        )

        # ---- Tab bar ----------------------------------------------------
        tab_w = (W_LEFT - 34) / 3
        tab_y1 = PANEL_TOP + 12
        tab_y2 = PANEL_TOP + 40
        self._tabs = {}
        for i, (name, tag) in enumerate(
            [("Home", "tab_home"), ("History", "tab_history"), ("Skills", "tab_skills")]
        ):
            x1 = X_LEFT + 14 + i * tab_w
            x2 = x1 + tab_w - 4
            r = rounded_rect(
                d,
                x1,
                tab_y1,
                x2,
                tab_y2,
                radius=10,
                fill=theme.GLASS_2 if i == 0 else theme.GLASS_3,
                outline=theme.ACCENT if i == 0 else theme.GLASS_BORDER,
                width=1,
                tags=("statics", tag),
            )
            lbl = d.create_text(
                (x1 + x2) / 2,
                (tab_y1 + tab_y2) / 2,
                text=name,
                fill=theme.ACCENT if i == 0 else theme.MUTED,
                font=theme.ACTION_LABEL,
                tags=("statics", tag),
            )
            self._tabs[tag] = {"rect": r, "idx": i, "lbl": lbl}
            d.tag_bind(
                tag,
                "<ButtonPress-1>",
                lambda e, t=tag: self._show_sidebar_tab(t),
            )

        # ---- Home content: quick actions --------------------------------
        self._build_sidebar_home()
        # ---- History + Skills panels (hidden by default) ----------------
        self._build_sidebar_history()
        self._build_sidebar_skills()
        self._show_sidebar_tab("tab_home")

    def _build_sidebar_home(self):
        d = self.desk
        group = "sbtab_home"

        # Section title & hint
        d.create_text(
            X_LEFT + 20,
            PANEL_TOP + 48,
            anchor="w",
            text="Quick actions",
            fill=theme.TEXT,
            font=theme.HEADER,
            tags=("statics", group),
        )
        d.create_line(
            X_LEFT + 16,
            PANEL_TOP + 60,
            X_LEFT + W_LEFT - 16,
            PANEL_TOP + 60,
            fill=theme.BORDER,
            width=1,
            tags=("statics", group),
        )

        y = PANEL_TOP + 68
        bh = 28
        for i, (label, cmd, icon) in enumerate(self.QUICK_ACTIONS):
            tag = f"act{i}"
            r = self._draw_control_pill(
                X_LEFT + 14,
                y,
                X_LEFT + W_LEFT - 14,
                y + bh,
                tag,
                fill=theme.GLASS_3,
                outline=theme.GLASS_BORDER,
                radius=10,
            )
            d.addtag_withtag(group, r)

            rounded_rect(
                d,
                X_LEFT + 18,
                y + 4,
                X_LEFT + 46,
                y + bh - 4,
                radius=6,
                fill=theme.GLASS_2,
                outline=theme.BORDER,
                tags=(tag, group),
            )
            d.create_text(
                X_LEFT + 32,
                y + bh / 2,
                text=icon,
                fill=theme.ACCENT,
                font=("Segoe UI Emoji", 13),
                tags=(tag, group),
            )
            d.create_text(
                X_LEFT + 58,
                y + bh / 2,
                anchor="w",
                text=label,
                fill=theme.TEXT,
                font=theme.ACTION_LABEL,
                tags=(tag, group),
            )
            d.create_text(
                X_LEFT + W_LEFT - 24,
                y + bh / 2,
                anchor="e",
                text="\u25B8",
                fill=theme.MUTED,
                font=(theme.FONT_FAMILY, 11),
                tags=(tag, group),
            )

            def hot(e, _r=r):
                d.itemconfig(_r, fill=theme.HOVER_BG, outline=theme.GLASS_BORDER_HOT)

            def cold(e, _r=r):
                d.itemconfig(_r, fill=theme.GLASS_3, outline=theme.GLASS_BORDER)

            def act(_e, _cmd=cmd, _r=r):
                d.itemconfig(_r, fill=mix(theme.HOVER_BG, theme.ACCENT, 0.30))
                self.root.after(90, lambda: self._run_command(_cmd))
                self.root.after(
                    130, lambda: d.itemconfig(_r, fill=theme.HOVER_BG, outline=theme.GLASS_BORDER)
                )

            d.tag_bind(tag, "<Enter>", hot)
            d.tag_bind(tag, "<Leave>", cold)
            d.tag_bind(tag, "<ButtonPress-1>", act)
            y += bh + 3

        y += 4
        d.create_line(
            X_LEFT + 16,
            y,
            X_LEFT + W_LEFT - 16,
            y,
            fill=theme.BORDER,
            width=1,
            tags=("statics", group),
        )
        y += 8

        browse = self._draw_control_pill(
            X_LEFT + 14, y, X_LEFT + W_LEFT - 14, y + bh, "browse",
            fill=theme.GLASS_3, radius=10,
        )
        d.addtag_withtag(group, browse)
        rounded_rect(
            d, X_LEFT + 18, y + 4, X_LEFT + 46, y + bh - 4, radius=6,
            fill=theme.GLASS_2, outline=theme.BORDER, tags=("browse", group),
        )
        d.create_text(
            X_LEFT + 32, y + bh / 2, text="\U0001f9ed", fill=theme.ACCENT,
            font=("Segoe UI Emoji", 13), tags=("browse", group),
        )
        d.create_text(
            X_LEFT + 58, y + bh / 2, anchor="w", text="Browse Websites",
            fill=theme.ACCENT, font=theme.ACTION_LABEL, tags=("browse", group),
        )
        d.tag_bind("browse", "<Enter>", lambda e: d.itemconfig(browse, fill=theme.HOVER_BG, outline=theme.GLASS_BORDER_HOT))
        d.tag_bind("browse", "<Leave>", lambda e: d.itemconfig(browse, fill=theme.GLASS_3, outline=theme.GLASS_BORDER))
        d.tag_bind("browse", "<ButtonPress-1>", lambda e: self._browse_websites())
        y += bh + 3

        clr = self._draw_control_pill(
            X_LEFT + 14, y, X_LEFT + W_LEFT - 14, y + bh, "clear",
            fill=theme.GLASS_3, radius=10,
        )
        d.addtag_withtag(group, clr)
        rounded_rect(
            d, X_LEFT + 18, y + 4, X_LEFT + 46, y + bh - 4, radius=6,
            fill=theme.GLASS_2, outline=theme.BORDER, tags=("clear", group),
        )
        d.create_text(
            X_LEFT + 32, y + bh / 2, text="\U0001f5d1", fill=theme.MUTED,
            font=("Segoe UI Emoji", 13), tags=("clear", group),
        )
        d.create_text(
            X_LEFT + 58, y + bh / 2, anchor="w", text="Clear chat",
            fill=theme.MUTED, font=theme.ACTION_LABEL, tags=("clear", group),
        )
        d.tag_bind("clear", "<Enter>", lambda e: d.itemconfig(clr, fill=theme.INPUT_BG, outline=theme.GLASS_BORDER_HOT))
        d.tag_bind("clear", "<Leave>", lambda e: d.itemconfig(clr, fill=theme.GLASS_3, outline=theme.GLASS_BORDER))
        d.tag_bind("clear", "<ButtonPress-1>", lambda e: self._clear_chat())

        # Stop Generating button (hidden unless a command is processing)
        y += bh + 3
        st = self._draw_control_pill(
            X_LEFT + 14, y, X_LEFT + W_LEFT - 14, y + bh, "stopgen",
            fill=theme.ACCENT_ERR, radius=10,
        )
        d.addtag_withtag(group, st)
        rounded_rect(
            d, X_LEFT + 18, y + 4, X_LEFT + 46, y + bh - 4, radius=6,
            fill=mix(theme.ACCENT_ERR, "#ffffff", 0.2), outline=theme.ACCENT_ERR,
            tags=("stopgen", group),
        )
        d.create_text(
            X_LEFT + 32, y + bh / 2, text="\u23f9", fill="#ffffff",
            font=(theme.FONT_FAMILY, 13), tags=("stopgen", group),
        )
        d.create_text(
            X_LEFT + 58, y + bh / 2, anchor="w", text="Stop Generating",
            fill="#ffffff", font=theme.ACTION_LABEL, tags=("stopgen", group),
        )
        d.tag_bind("stopgen", "<ButtonPress-1>", lambda e: self._cancel_generation())
        d.tag_bind("stopgen", "<Enter>", lambda e: d.itemconfig(st, fill=mix(theme.ACCENT_ERR, "#ffffff", 0.2)))
        d.tag_bind("stopgen", "<Leave>", lambda e: d.itemconfig(st, fill=theme.ACCENT_ERR))

    def _build_sidebar_history(self):
        d = self.desk
        group = "sbtab_history"
        x1 = X_LEFT + 14
        x2 = X_LEFT + W_LEFT - 14
        y_top = PANEL_TOP + 52

        d.create_text(
            x1, y_top, anchor="w", text="Chat History",
            fill=theme.TEXT, font=theme.HEADER, tags=("statics", group),
        )
        d.create_text(
            x1, y_top + 20, anchor="w", text="Click an entry to re-run it",
            fill=theme.MUTED, font=theme.HEADER_HINT, tags=("statics", group),
        )
        d.create_line(
            x1 - 2, y_top + 32, x2 + 2, y_top + 32,
            fill=theme.BORDER, width=1, tags=("statics", group),
        )

    def _refresh_history(self):
        d = self.desk
        group = "sbtab_history"
        # Remove any previously drawn rows (keep the static header above).
        for htag, _ in getattr(self, "_history_list", []):
            try:
                d.delete(htag)
            except Exception:
                pass
        self._history_list = []
        d.delete("hist_none")

        x1 = X_LEFT + 14
        x2 = X_LEFT + W_LEFT - 14
        y_top = PANEL_TOP + 52

        from jarvis import memory as mem
        profile = mem.get_user_profile(getattr(self, "username", "user"))
        history = profile.get("history", []) or []
        y = y_top + 42
        bh = 30
        max_y = PANEL_BOT - 10
        for turn in reversed(history[-14:]):
            if y + bh > max_y:
                break
            q = str(turn.get("user", "")).strip()
            if not q:
                continue
            htag = f"histrow{len(self._history_list)}"
            r = rounded_rect(
                d, x1, y, x2, y + bh, radius=8,
                fill=theme.GLASS_3, outline=theme.GLASS_BORDER, width=1,
                tags=(htag, group),
            )
            snippet = q if len(q) <= 22 else q[:20] + "\u2026"
            d.create_text(
                x1 + 10, y + bh / 2, anchor="w", text=snippet,
                fill=theme.TEXT, font=theme.ACTION_LABEL,
                tags=(htag, group),
            )
            self._history_list.append((htag, q))
            d.tag_bind(
                htag, "<ButtonPress-1>",
                lambda e, _q=q, _r=r: self._rerun_history(_q, _r),
            )
            d.tag_bind(htag, "<Enter>", lambda e, _r=r: d.itemconfig(_r, outline=theme.ACCENT))
            d.tag_bind(htag, "<Leave>", lambda e, _r=r: d.itemconfig(_r, outline=theme.GLASS_BORDER))
            y += bh + 4

        if not self._history_list:
            d.create_text(
                (x1 + x2) / 2, y_top + 60, text="No history yet",
                fill=theme.MUTED, font=theme.HEADER_HINT,
                tags=(group, "hist_none"),
            )

    def _build_sidebar_skills(self):
        d = self.desk
        group = "sbtab_skills"
        x1 = X_LEFT + 14
        x2 = X_LEFT + W_LEFT - 14
        y_top = PANEL_TOP + 52

        d.create_text(
            x1, y_top, anchor="w", text="Skills & Commands",
            fill=theme.TEXT, font=theme.HEADER, tags=("statics", group),
        )
        d.create_text(
            x1, y_top + 20, anchor="w", text="What I can do",
            fill=theme.MUTED, font=theme.HEADER_HINT, tags=("statics", group),
        )
        d.create_line(
            x1 - 2, y_top + 32, x2 + 2, y_top + 32,
            fill=theme.BORDER, width=1, tags=("statics", group),
        )

        skills = [
            ("\u23f1", "Time & Date"),
            ("\U0001f4d6", "Wikipedia search"),
            ("\u2601\ufe0f", "Weather by city"),
            ("\U0001f4f8", "Take screenshot"),
            ("\U0001f5a5\ufe0f", "System information"),
            ("\U0001f50d", "Google search"),
            ("\U0001f3b5", "YouTube / Spotify"),
            ("\u270f\ufe0f", "Calculator"),
            ("\u23f2\ufe0f", "Timer"),
            ("\U0001f4d5", "Open websites"),
            ("\U0001f4bb", "Open apps"),
            ("\U0001f4a1", "Jokes & chat"),
            ("\U0001f5d1\ufe0f", "Clear chat"),
        ]
        y = y_top + 42
        bh = 26
        for icon, name in skills:
            if y + bh > PANEL_BOT - 6:
                break
            d.create_text(
                x1 + 2, y + bh / 2, text=icon, fill=theme.ACCENT,
                font=("Segoe UI Emoji", 11), tags=group,
            )
            d.create_text(
                x1 + 22, y + bh / 2, anchor="w", text=name,
                fill=theme.TEXT, font=theme.ACTION_LABEL, tags=group,
            )
            y += bh + 4

    def _show_sidebar_tab(self, active: str):
        tabs = {
            "tab_home": "sbtab_home",
            "tab_history": "sbtab_history",
            "tab_skills": "sbtab_skills",
        }
        d = self.desk
        for tag, group in tabs.items():
            try:
                d.itemconfig(group, state="normal" if tag == active else "hidden")
            except Exception:
                pass
        if active == "tab_history":
            self._refresh_history()
        if active == "tab_home":
            try:
                self.desk.itemconfig(
                    "stopgen",
                    state=("normal" if getattr(self, "_thinking", False) else "hidden"),
                )
            except Exception:
                pass
        # Highlight active tab, dim others.
        tab_w = (W_LEFT - 34) / 3
        for name, tag in [("Home", "tab_home"), ("History", "tab_history"), ("Skills", "tab_skills")]:
            info = self._tabs[tag]
            x1 = X_LEFT + 14 + info["idx"] * tab_w
            x2 = x1 + tab_w - 4
            if tag == active:
                fill, outline, tcol = theme.GLASS_2, theme.ACCENT, theme.ACCENT
            else:
                fill, outline, tcol = theme.GLASS_3, theme.GLASS_BORDER, theme.MUTED
            d.itemconfig(info["rect"], fill=fill, outline=outline)
            d.itemconfig(info["lbl"], fill=tcol)

    def _rerun_history(self, question: str, rect):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, question)
        self._send()

    def _build_chat_panel(self):
        d = self.desk
        rounded_rect(
            d,
            CX,
            PANEL_TOP,
            CX + CW,
            PANEL_BOT,
            18,
            fill=theme.GLASS,
            outline=theme.BORDER,
            width=1,
            tags="statics",
        )

        chat_h = PANEL_BOT - PANEL_TOP - 20 - 64
        self.chat = ChatPanel(d, CW - 24, chat_h)
        self.chat.on_speak = self._speak_bubble
        d.create_window(CX + 12, PANEL_TOP + 10, anchor="nw", window=self.chat)
        self.chat.bind("<Button-1>", lambda e: self.entry.focus_force())

        # Polished Input Capsule Container
        inp_y1 = PANEL_BOT - 56
        inp_y2 = PANEL_BOT - 12
        self._capsule = self._draw_control_pill(
            CX + 14,
            inp_y1,
            CX + CW - 14,
            inp_y2,
            "capsule",
            fill=theme.INPUT_BG,
            outline=theme.BORDER,
            radius=22,
        )
        d.tag_bind("capsule", "<ButtonPress-1>", lambda e: self.entry.focus_force())

        self.entry = tk.Entry(
            d,
            font=theme.CHAT_BODY,
            fg=theme.TEXT,
            bg=theme.INPUT_BG,
            insertbackground=theme.ACCENT,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.ACCENT,
            width=26,
        )
        d.create_window(
            CX + 30,
            PANEL_BOT - 44,
            anchor="nw",
            window=self.entry,
            width=CW - 150,
        )
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.bind("<Up>", lambda e: self._history_nav(-1))
        self.entry.bind("<Down>", lambda e: self._history_nav(1))

        # Voice Button (Mic)
        vcx, vcy = CX + CW - 78, PANEL_BOT - 34
        self.voice_circle = d.create_oval(
            vcx - 16,
            vcy - 16,
            vcx + 16,
            vcy + 16,
            fill=theme.GLASS_3,
            outline=theme.BORDER,
            width=1,
            tags="voice",
        )
        self.voice_icon = d.create_text(
            vcx,
            vcy,
            text="\U0001f3a4",
            font=("Segoe UI Emoji", 12),
            fill=theme.MUTED,
            tags="voice",
        )
        self.voice_dot = d.create_oval(
            vcx + 5,
            vcy - 11,
            vcx + 10,
            vcy - 6,
            fill=theme.MUTED,
            outline="",
            tags="voice",
        )
        d.tag_bind(
            "voice",
            "<ButtonPress-1>",
            lambda e: (self._toggle_voice_input(), "break")[1],
        )
        d.tag_bind(
            "voice",
            "<Enter>",
            lambda e: d.itemconfig(self.voice_circle, outline=theme.ACCENT),
        )
        d.tag_bind(
            "voice",
            "<Leave>",
            lambda e: d.itemconfig(self.voice_circle, outline=theme.BORDER),
        )

        # Send Button (Cyan Accent Circle + Chevron)
        scx, scy = CX + CW - 42, PANEL_BOT - 34
        self.send_circle = d.create_oval(
            scx - 16,
            scy - 16,
            scx + 16,
            scy + 16,
            fill=theme.ACCENT,
            outline=theme.ACCENT,
            width=1,
            tags="send",
        )
        self.send_glyph = d.create_polygon(
            scx - 4,
            scy - 6,
            scx + 5,
            scy,
            scx - 4,
            scy + 6,
            fill=theme.BODY,
            outline="",
            tags="send",
        )
        d.tag_bind(
            "send",
            "<ButtonPress-1>",
            lambda e: (
                self._send(),
                d.itemconfig(self.send_circle, fill=mix(theme.ACCENT, "#ffffff", 0.3)),
                "break",
            )[2],
        )
        d.tag_bind(
            "send",
            "<Enter>",
            lambda e: d.itemconfig(
                self.send_circle, fill=mix(theme.ACCENT, "#ffffff", 0.2)
            ),
        )
        d.tag_bind(
            "send",
            "<Leave>",
            lambda e: d.itemconfig(self.send_circle, fill=theme.ACCENT),
        )

        # Stop-Generating Button (red square, replaces Send while thinking)
        self.stop_circle = d.create_oval(
            scx - 16,
            scy - 16,
            scx + 16,
            scy + 16,
            fill=theme.ACCENT_ERR,
            outline=theme.ACCENT_ERR,
            width=1,
            tags="stopbtn",
            state="hidden",
        )
        self.stop_glyph = d.create_rectangle(
            scx - 6,
            scy - 6,
            scx + 6,
            scy + 6,
            fill=theme.BODY,
            outline="",
            tags="stopbtn",
            state="hidden",
        )
        d.tag_bind("stopbtn", "<ButtonPress-1>", lambda e: self._cancel_generation())
        d.tag_bind(
            "stopbtn",
            "<Enter>",
            lambda e: d.itemconfig(
                self.stop_circle, fill=mix(theme.ACCENT_ERR, "#ffffff", 0.2)
            ),
        )
        d.tag_bind(
            "stopbtn",
            "<Leave>",
            lambda e: d.itemconfig(self.stop_circle, fill=theme.ACCENT_ERR),
        )

    def _build_status_bar(self):
        d = self.desk
        rounded_rect(
            d,
            XM,
            610,
            W - XM,
            633,
            10,
            fill=theme.GLASS,
            outline=theme.GLASS_BORDER,
            width=1,
            tags="statics",
        )

        # Status text on the left
        self.status_item = d.create_text(
            42,
            621,
            anchor="w",
            text="Ready",
            fill=theme.MUTED,
            font=theme.STATUS,
            tags="statics",
        )

        # Gemini status indicator
        gem_ok = ai_engine.is_available()
        gx = W - 322
        d.create_oval(
            gx,
            616,
            gx + 9,
            625,
            fill=theme.ACCENT_OK if gem_ok else theme.ACCENT_ERR,
            outline="",
            tags="statics",
        )
        d.create_text(
            gx + 16,
            621,
            anchor="w",
            text="Gemini" + (" Online" if gem_ok else " Offline"),
            fill=theme.MUTED,
            font=theme.STATUS,
            tags="statics",
        )

        # TTS toggle button
        tts_ok = self._tts_available
        tx = W - 182
        self.status_tts_dot = d.create_oval(
            tx,
            616,
            tx + 9,
            625,
            fill=theme.ACCENT_OK if tts_ok else theme.ACCENT_ERR,
            outline="",
            tags="statics",
        )
        self.status_tts_text = d.create_text(
            tx + 16,
            621,
            anchor="w",
            text="Voice" + (" On" if tts_ok else " Off"),
            fill=theme.MUTED,
            font=theme.STATUS,
            tags="ttsbtn",
        )
        d.tag_bind(
            "ttsbtn", "<ButtonPress-1>", lambda e: (self._toggle_tts(), "break")[1]
        )
        d.tag_bind(
            "ttsbtn",
            "<Enter>",
            lambda e: d.itemconfig(self.status_tts_text, fill=theme.TEXT),
        )
        d.tag_bind(
            "ttsbtn",
            "<Leave>",
            lambda e: d.itemconfig(self.status_tts_text, fill=theme.MUTED),
        )

    # ------------------------------------------------------------ clock
    def _set_status(self, msg: str):
        self.desk.itemconfig(self.status_item, text=msg)

    # ------------------------------------------------------------ state
    def _set_state(self, state: str, label: str = None):
        self.gear.set_state(state)
        color = STATES.get(state, theme.ACCENT)
        self.state_label = label or (
            "Ready"
            if state == "idle"
            else "Processing..."
            if state == "thinking"
            else "Speaking..."
            if state == "speaking"
            else "Listening..."
        )

        self.desk.itemconfig(self.chip_state_dot, fill=color)
        self.desk.itemconfig(self.chip_state_text, text=self.state_label, fill=color)
        self.desk.itemconfig(
            self.legend,
            text=self.state_label,
            fill=color,
        )
        self._chip_bar_active = (state != "idle")
        thinking = state == "thinking"
        for tag in ("send", "stopbtn"):
            try:
                self.desk.itemconfig(
                    tag,
                    state=("hidden" if (tag == "send") == thinking else "normal"),
                )
            except Exception:
                pass
        try:
            self.desk.itemconfig(
                "stopgen",
                state=("normal" if thinking else "hidden"),
            )
        except Exception:
            pass

    def _on_speaker_state(self, state: str):
        def apply():
            if state == "speaking":
                self._speaking_now = True
                self._set_state("speaking", "Speaking...")
            else:
                self._speaking_now = False
                if not self._thinking:
                    if self.voice_input_enabled:
                        self._set_state("listening", "Listening...")
                    else:
                        self._set_state("idle", "Ready")
                    self._set_status("Ready")
                self._chip_bar_active = False

        try:
            self.root.after(0, apply)
        except Exception:
            pass

    # ------------------------------------------------------------ voice input
    def _set_voice_ui(self, on: bool):
        d = self.desk
        if on:
            d.itemconfig(self.voice_circle, fill=theme.ACCENT, outline=theme.ACCENT)
            d.itemconfig(self.voice_icon, fill=theme.BODY)
            d.itemconfig(self.voice_dot, fill=theme.ACCENT_ERR)
            d.itemconfig(self._capsule, outline=theme.ACCENT)
            self._set_state("listening", "Listening...")
        else:
            d.itemconfig(
                self.voice_circle, fill=theme.GLASS_3, outline=theme.BORDER
            )
            d.itemconfig(self.voice_icon, fill=theme.MUTED)
            d.itemconfig(self.voice_dot, fill=theme.MUTED)
            d.itemconfig(self._capsule, outline=theme.BORDER)
            if not self._thinking:
                self._set_state("idle", "Ready")

    def _toggle_voice_input(self):
        # --- Second click: stop listening immediately ---
        if self.voice_input_enabled:
            self.voice_input_enabled = False
            # Abort the blocking sd.rec/sd.wait() call right now
            if self._stt is not None:
                self._stt.stop()
            self._set_voice_ui(False)
            self._set_status("Ready")
            return

        # --- First click: start a single-shot listen ---
        if self._locked:
            self._set_status("Please wait — previous command still running")
            return
        if self._stt is None:
            self._stt = VoiceInput()
        if not self._stt.available():
            self._set_status("Voice engine unavailable — check microphone")
            self.chat.add_system("Voice engine unavailable (microphone or Windows Speech)")
            return

        self.voice_input_enabled = True
        self._voice_started = time.time()
        self._set_voice_ui(True)
        self._set_status("Listening… 5s, then auto-submit")
        self.chat.add_system("Voice input active — I'll listen for 5 seconds, then auto-submit")
        if self._voice_thread is None or not self._voice_thread.is_alive():
            self._voice_thread = threading.Thread(
                target=self._voice_worker, daemon=True
            )
            self._voice_thread.start()

    def _ui_call(self, fn):
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def _voice_worker(self):
        """Single-shot: listen for ~5s, put result in entry box, then turn off."""
        try:
            text = self._stt.listen(timeout=5)
        except RuntimeError as e:
            msg = str(e)
            if (
                "NO_MIC" in msg
                or "NO_SPEECH_ENGINE" in msg
                or "RESTART_FAIL" in msg
            ):
                self._ui_call(self._voice_died)
                return
            self._ui_call(
                lambda err=str(e): self._set_status(f"Voice error: {err}")
            )
            self._ui_call(self._voice_done)
            return
        except Exception as e:
            self._ui_call(
                lambda err=str(e): self._set_status(f"Voice error: {err}")
            )
            self._ui_call(self._voice_done)
            return

        # Deliver result to UI (even if user stopped early — partial audio is fine)
        self._ui_call(lambda t=text: self._voice_result(t))

    def _voice_result(self, text: str):
        """Called on the UI thread after a listen() completes. Auto-sends the result."""
        self.voice_input_enabled = False
        self._set_voice_ui(False)
        if text:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, text)
            self._set_status("Voice captured — processing…")
            self.root.after(120, self._send)
        else:
            self._set_status("No speech detected — try again")

    def _voice_done(self):
        """Reset voice UI without inserting text (e.g. on error)."""
        self.voice_input_enabled = False
        self._set_voice_ui(False)

    def _voice_died(self):
        self.voice_input_enabled = False
        self._set_voice_ui(False)
        self._set_status("Voice unavailable — check microphone")
        self.chat.add_system("Voice input lost — microphone unavailable")

    # ---------------------------------------------------------- history
    def _history_nav(self, direction: int):
        if not self._command_history:
            return
        self._history_index += direction
        n = len(self._command_history)
        self._history_index = max(-1, min(self._history_index, n - 1))
        self.entry.delete(0, tk.END)
        if self._history_index >= 0:
            self.entry.insert(0, self._command_history[self._history_index])

    # ------------------------------------------------------------ chat ui
    def _clear_chat(self):
        self.chat.clear()
        self.chat.add_system("Conversation cleared")

    def _append_user(self, text):
        self.chat.add_message("user", text, animate=True)

    def _greet(self):
        from jarvis.skills.time_date import get_greeting

        msg = (
            f"{get_greeting()}, {self.display_name}.\n"
            f"I can open apps and websites, check the weather, play media, "
            f"take screenshots, calculate, or answer any questions."
        )
        self.chat.add_system("Jarvis initialized")
        self._reply_ai(msg)

    def _reply_ai(self, text, speak=True):
        """Render an assistant reply with a typewriter reveal."""
        cmd_id = self._command_counter

        def done():
            # A newer command supersedes this reply: don't finish speaking it.
            if cmd_id != self._command_counter:
                return
            self._set_status("Ready")
            if speak and self.tts_enabled:
                self.speaker.say(text)
            elif self.voice_input_enabled:
                self._set_state("listening", "Listening...")
            else:
                self._set_state("idle", "Ready")

        self.chat.type_message("ai", text, done_cb=done)

    # ----------------------------------------------------------- actions
    def _toggle_theme(self):
        """Switch light/dark palette and rebuild the UI in the new theme."""
        theme.toggle()
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Re-render the whole window using the currently active theme,
        preserving the on-screen conversation."""
        # Snapshot existing conversation (user + AI bubbles).
        snap = []
        chat = getattr(self, "chat", None)
        bubbles = getattr(chat, "_bubbles", None) or {}
        for b in bubbles.values():
            if b.get("sender") in ("user", "ai") and b.get("text"):
                snap.append((b["sender"], b["text"]))

        # Stop background loops for the old canvas by invalidating the gen.
        self._gen += 1
        self._voice_input_enabled_saved = self.voice_input_enabled
        self.voice_input_enabled = False

        old_desk = self.desk
        try:
            old_desk.destroy()
        except Exception:
            pass

        self.desk = tk.Canvas(
            self.root, width=W, height=H, bg=theme.CORNER,
            highlightthickness=0, bd=0,
        )
        self.desk.pack()
        self._spawn_particles()
        self._build_hub()
        self._setup_taskbar()

        # Replay the conversation with the new colours.
        if snap:
            self.chat.add_system("Theme changed — conversation preserved")
            for sender, text in snap:
                try:
                    self.chat.add_message(sender, text, animate=False)
                except Exception:
                    pass
        self._set_state("idle", "Ready")
        self._set_status("Ready")

        self._start_loops()
        self.root.after(100, lambda: self.entry.focus_force())

    def _speak_bubble(self, text):
        """Speak a chat message aloud when its 🔊 button is clicked."""
        if not text:
            return
        if not self._tts_available:
            self._set_status("Voice (TTS) not available")
            return
        self.speaker.say(text)

    def _toggle_tts(self):
        if not self._tts_available:
            return
        self.tts_enabled = not self.tts_enabled
        self.speaker.enabled = self.tts_enabled
        if not self.tts_enabled:
            # Turning voice off should interrupt any current speech too.
            self.speaker.stop_speaking()
        color = theme.ACCENT_OK if self.tts_enabled else theme.ACCENT_ERR
        if hasattr(self, "status_tts_dot"):
            self.desk.itemconfig(self.status_tts_dot, fill=color)
        self.desk.itemconfig(
            self.status_tts_text,
            text="Voice is On" if self.tts_enabled else "Voice is Off",
            fill=theme.MUTED,
        )

    def _stop_tts_speaking(self):
        if self.speaker:
            self.speaker.stop_speaking()
        self._speaking_now = False
        self._set_status("Ready")

    def _send(self):
        if self.voice_input_enabled:
            self.entry.delete(0, tk.END)
            self.chat.add_system("Voice mode active \u2014 speak, or tap mic icon to return to text")
            return
        text = self.entry.get().strip()
        if not text or self._locked:
            return
        self.entry.delete(0, tk.END)
        self._command_history.insert(0, text)
        if len(self._command_history) > 50:
            self._command_history.pop()
        self._history_index = -1
        self._run_command(text)

    def _run_command(self, text: str):
        self._append_user(text)
        self._command_counter += 1
        self._current_command = text
        self._stop_current()
        low = text.lower().strip()
        if low in ("exit", "quit", "bye"):
            self._reply_ai("Goodbye. Have a great day!")
            self.root.after(1400, self._close)
            return

        self._set_state("thinking", "Processing...")
        self._set_status("Processing request...")
        self.chat.show_typing()
        self._thinking = True
        self._lock(True)
        cmd_id = self._command_counter

        def worker():
            try:
                reply = command.process_command(text, self.username)
            except Exception as e:
                reply = f"I encountered an error processing that: {e}"
            try:
                self.root.after(
                    0, lambda r=reply, cid=cmd_id: self._on_reply(r, cid)
                )
            except RuntimeError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_reply(self, reply: str, cmd_id: int = 0):
        if cmd_id != self._command_counter:
            return
        self._thinking = False
        self.chat.remove_typing()
        self._lock(False)
        self._reply_ai(reply)

    def _stop_current(self):
        """Stop the in-flight AI task. Also pauses/suppresses any previous
        reply that is still being spoken, so the new conversation starts fresh."""
        self._thinking = False
        self._current_command = None
        if self.speaker:
            self.speaker.stop_speaking()
        self._speaking_now = False
        chat = getattr(self, "chat", None)
        if chat is not None:
            try:
                chat.stop_current_reveal()
            except Exception:
                pass

    def _cancel_generation(self):
        """Stop waiting for the current AI reply. Discards the in-flight
        worker result and unlocks the UI right away."""
        self._command_counter += 1          # invalidate pending reply
        self._thinking = False
        self._current_command = None
        if self.speaker:
            self.speaker.stop_speaking()
        self._speaking_now = False
        self._lock(False)
        self.chat.remove_typing()
        self._set_state("idle", "Ready")
        self._set_status("Generation stopped")

    def _lock(self, locked: bool):
        self._locked = locked
        # Physically disable the text input and voice button while a
        # command is still being processed.
        try:
            self.entry.config(state=tk.DISABLED if locked else tk.NORMAL)
        except Exception:
            pass
        self.desk.itemconfig(
            self.send_circle,
            fill=mix(theme.ACCENT, theme.INPUT_BG, 0.55)
            if locked
            else theme.ACCENT,
        )
        self.desk.itemconfig(
            self.send_glyph, fill=theme.INPUT_BG if locked else theme.BODY
        )

    # ------------------------------------------------------------ dialogs
    def _ask_username(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Welcome to Jarvis")
        dialog.geometry("440x230")
        dialog.resizable(False, False)
        dialog.configure(bg=theme.GLASS)
        dialog.transient(self.root)
        try:
            dialog.attributes("-topmost", True)
        except Exception:
            pass

        x = self.root.winfo_x() + W // 2 - 220
        y = self.root.winfo_y() + H // 2 - 115
        dialog.geometry(f"440x230+{x}+{y}")

        tk.Label(
            dialog,
            text="Welcome to JARVIS",
            fg=theme.TEXT,
            bg=theme.GLASS,
            font=(theme.FONT_FAMILY, 15, "bold"),
        ).pack(pady=(22, 4))
        tk.Label(
            dialog,
            text="How would you like me to address you?",
            fg=theme.MUTED,
            bg=theme.GLASS,
            font=(theme.FONT_FAMILY, 10),
        ).pack()

        entry = tk.Entry(
            dialog,
            font=(theme.FONT_FAMILY, 11),
            bg=theme.INPUT_BG,
            fg=theme.TEXT,
            insertbackground=theme.ACCENT,
            relief=tk.FLAT,
            bd=0,
            justify="center",
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.ACCENT,
        )
        entry.pack(pady=16, padx=50, fill=tk.X, ipady=6)
        entry.focus()

        result = {"name": "user"}

        def confirm(_event=None):
            val = entry.get().strip()
            if val:
                result["name"] = val
            dialog.destroy()
            self.username = memory.normalize_name(result["name"])
            self.display_name = result["name"].strip().title() or "User"
            self._greet()

        entry.bind("<Return>", confirm)
        tk.Button(
            dialog,
            text="Get Started",
            command=confirm,
            bg=theme.ACCENT,
            fg=theme.BODY,
            font=(theme.FONT_FAMILY, 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=6,
            activebackground=mix(theme.ACCENT, "#ffffff", 0.2),
            activeforeground=theme.BODY,
            cursor="hand2",
            bd=0,
        ).pack(pady=4)

        dialog.grab_set()

    def _browse_websites(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Browse Websites & Services")
        dialog.geometry("540x480")
        dialog.configure(bg=theme.GLASS)
        dialog.transient(self.root)
        dialog.grab_set()
        x = self.root.winfo_x() + W // 2 - 270
        y = self.root.winfo_y() + H // 2 - 240
        dialog.geometry(f"540x480+{x}+{y}")

        tk.Label(
            dialog,
            text="Websites & Services Library",
            fg=theme.TEXT,
            bg=theme.GLASS,
            font=(theme.FONT_FAMILY, 13, "bold"),
        ).pack(pady=(16, 4))
        tk.Label(
            dialog,
            text="Select a category, then choose a website to launch",
            fg=theme.MUTED,
            bg=theme.GLASS,
            font=(theme.FONT_FAMILY, 9),
        ).pack(pady=(0, 10))

        content_frame = tk.Frame(dialog, bg=theme.GLASS)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        # Categories list
        cat_box_frame = tk.Frame(content_frame, bg=theme.GLASS)
        cat_box_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        tk.Label(
            cat_box_frame,
            text="Categories",
            fg=theme.ACCENT,
            bg=theme.GLASS,
            font=(theme.FONT_FAMILY, 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 4))

        cat_listbox = tk.Listbox(
            cat_box_frame,
            bg=theme.INPUT_BG,
            fg=theme.TEXT,
            font=(theme.FONT_FAMILY, 9),
            relief=tk.FLAT,
            selectbackground=theme.ACCENT,
            selectforeground=theme.BODY,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            bd=0,
        )
        cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cat_scroll = tk.Scrollbar(
            cat_box_frame, command=cat_listbox.yview, bg=theme.GLASS
        )
        cat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        cat_listbox.config(yscrollcommand=cat_scroll.set)
        for cat_name in command.WEBSITE_CATEGORIES:
            cat_listbox.insert(tk.END, cat_name)

        # Sites list
        sites_box_frame = tk.Frame(content_frame, bg=theme.GLASS)
        sites_box_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(
            sites_box_frame,
            text="Websites",
            fg=theme.ACCENT,
            bg=theme.GLASS,
            font=(theme.FONT_FAMILY, 9, "bold"),
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 4))

        sites_listbox = tk.Listbox(
            sites_box_frame,
            bg=theme.INPUT_BG,
            fg=theme.TEXT,
            font=(theme.FONT_FAMILY, 9),
            relief=tk.FLAT,
            selectbackground=theme.ACCENT_OK,
            selectforeground=theme.BODY,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            bd=0,
        )
        sites_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sites_scroll = tk.Scrollbar(
            sites_box_frame, command=sites_listbox.yview, bg=theme.GLASS
        )
        sites_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        sites_listbox.config(yscrollcommand=sites_scroll.set)

        from websites import websites as all_websites

        def on_category_select(_event=None):
            sel = cat_listbox.curselection()
            if not sel:
                return
            cat = cat_listbox.get(sel[0])
            sites_listbox.delete(0, tk.END)
            for site in websites_skill.categories().get(cat, []):
                if site in all_websites:
                    sites_listbox.insert(tk.END, site)

        cat_listbox.bind("<<ListboxSelect>>", on_category_select)

        def open_selected(_event=None):
            sel = sites_listbox.curselection()
            if not sel:
                return
            site = sites_listbox.get(sel[0])
            if site in all_websites:
                webbrowser.open(all_websites[site])
                self.chat.add_system(f"Opened {site}")
                dialog.destroy()

        sites_listbox.bind("<Double-Button-1>", open_selected)
        tk.Button(
            dialog,
            text="Open Selected Website",
            command=open_selected,
            bg=theme.ACCENT,
            fg=theme.BODY,
            font=(theme.FONT_FAMILY, 10, "bold"),
            relief=tk.FLAT,
            padx=18,
            pady=6,
            activebackground=mix(theme.ACCENT, "#ffffff", 0.2),
            activeforeground=theme.BODY,
            cursor="hand2",
            bd=0,
        ).pack(pady=12)


def run():
    root = tk.Tk()
    app = JarvisApp(root)
    root.mainloop()
