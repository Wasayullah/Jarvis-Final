"""Reusable animated widgets and drawing primitives for the modern desktop assistant.

Renders an elegant minimal AI visualizer orb and a smooth chat panel.
"""

import math
import time
import tkinter as tk
from tkinter import font as tkfont

from jarvis.ui import theme


# ------------------------------------------------------------------ colour helpers
def mix(c1: str, c2: str, t: float) -> str:
    """Linearly blend two '#rrggbb' colours. t=0 -> c1, t=1 -> c2."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return "#%02x%02x%02x" % (
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def shade(color: str, factor: float) -> str:
    """Darken (factor<1) or lighten (factor>1) a colour toward black/white."""
    if factor < 1.0:
        return mix(color, "#000000", 1.0 - factor)
    return mix(color, "#ffffff", factor - 1.0)


def rounded_points(x1, y1, x2, y2, r, n=6):
    """Generate polygon vertices for a rounded rectangle (no smoothing)."""
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    if r <= 0:
        return [x1, y1, x2, y1, x2, y2, x1, y2]
    pts = []
    for cx, cy, start_a in [
        (x1 + r, y1 + r, math.pi),
        (x2 - r, y1 + r, math.pi / 2),
        (x2 - r, y2 - r, 0),
        (x1 + r, y2 - r, -math.pi / 2),
    ]:
        for i in range(n + 1):
            a = start_a - (math.pi / 2) * i / n
            pts.extend([cx + r * math.cos(a), cy - r * math.sin(a)])
    return pts


def rounded_rect(canvas, x1, y1, x2, y2, radius=12, **kwargs):
    return canvas.create_polygon(
        rounded_points(x1, y1, x2, y2, radius), **kwargs
    )


# ------------------------------------------------------------------- visualizer core
class Gear:
    """Minimal, elegant AI visualizer orb.

    Communicates state (idle, thinking, speaking, listening) through smooth
    motion, soft radiant aura rings, harmonic waveforms and glowing central core.
    """

    COLORS = {
        "idle": theme.ACCENT,
        "thinking": theme.ACCENT,
        "speaking": theme.ACCENT,
        "listening": theme.ACCENT,
    }
    SPEEDS = {
        "idle": 0.35,
        "thinking": 1.4,
        "speaking": 0.8,
        "listening": 0.6,
    }

    def __init__(self):
        self.state = "idle"
        self.a = 0.0      # rotation angle
        self.t = 0.0      # animation clock
        self._acc = theme.ACCENT
        self._acc_next = theme.ACCENT

    def set_state(self, state: str):
        if state in self.COLORS:
            self.state = state
            self._acc_next = self.COLORS[state]

    def step(self):
        self.a = (self.a + self.SPEEDS.get(self.state, 0.4)) % 360
        self.t += 0.05
        if self._acc != self._acc_next:
            self._acc = mix(self._acc, self._acc_next, 0.08)

    def draw(self, c: tk.Canvas, cx, cy, size):
        c.delete("gear")
        accent = self._acc
        bg = theme.BODY
        breath = math.sin(self.t * 1.6)
        state = self.state

        R = size * 0.38

        # 1. Soft atmospheric halo rings (restrained)
        h1 = mix(accent, bg, 0.955 + 0.02 * breath)
        c.create_oval(cx - R * 1.20, cy - R * 1.20, cx + R * 1.20, cy + R * 1.20,
                      outline=h1, width=1, tags="gear")

        h2 = mix(accent, bg, 0.90 + 0.03 * breath)
        c.create_oval(cx - R * 1.04, cy - R * 1.04, cx + R * 1.04, cy + R * 1.04,
                      outline=h2, width=1.5, tags="gear")

        # 2. Orbital rings with subtle rotating dashed arcs
        r_orb1 = R * 0.78
        c.create_oval(cx - r_orb1, cy - r_orb1, cx + r_orb1, cy + r_orb1,
                      outline=mix(accent, bg, 0.72), width=1, tags="gear")

        # Orbital arcs rotating smoothly
        for i in range(3):
            arc_start = self.a * 1.2 + i * 120
            c.create_arc(cx - r_orb1, cy - r_orb1, cx + r_orb1, cy + r_orb1,
                         start=arc_start, extent=38, style=tk.ARC,
                         outline=mix(accent, "#ffffff", 0.26), width=2, tags="gear")

        r_orb2 = R * 0.52
        c.create_oval(cx - r_orb2, cy - r_orb2, cx + r_orb2, cy + r_orb2,
                      outline=mix(accent, bg, 0.60), width=1, tags="gear")

        # 3. Dynamic State-Specific Visualizer Elements
        if state == "thinking":
            # Fast gyroscopic sweep beams
            r_think = R * 0.94
            c.create_arc(cx - r_think, cy - r_think, cx + r_think, cy + r_think,
                         start=self.a * 3.2, extent=70, style=tk.ARC,
                         outline=mix(accent, "#ffffff", 0.6), width=3, tags="gear")
            c.create_arc(cx - r_think, cy - r_think, cx + r_think, cy + r_think,
                         start=self.a * 3.2 + 180, extent=70, style=tk.ARC,
                         outline=mix(accent, "#ffffff", 0.4), width=2, tags="gear")

        elif state == "speaking":
            # Calm circular acoustic waveform petals
            bars = 26
            for i in range(bars):
                amp = (
                    0.42 * abs(math.sin(self.t * 3.6 + i * 0.45))
                    + 0.30 * abs(math.sin(self.t * 6.0 + i * 0.9))
                )
                bar_len = 3 + amp * (R * 0.26)
                angle = math.radians(i * (360.0 / bars) - 90)
                r_base = R * 0.76
                x1 = cx + r_base * math.cos(angle)
                y1 = cy + r_base * math.sin(angle)
                x2 = cx + (r_base + bar_len) * math.cos(angle)
                y2 = cy + (r_base + bar_len) * math.sin(angle)
                c.create_line(x1, y1, x2, y2,
                              fill=mix(accent, "#ffffff", 0.30),
                              width=2, tags="gear")

        elif state == "listening":
            # Quiet expanding acoustic radar waves
            for i in range(3):
                wave_phase = (self.t * 1.4 + i * 0.9) % 2.4
                r_wave = R * (0.34 + wave_phase * 0.34)
                fade = max(0.0, 1.0 - (wave_phase / 2.4))
                col = mix(accent, bg, 1.0 - (fade * 0.7))
                c.create_oval(cx - r_wave, cy - r_wave, cx + r_wave, cy + r_wave,
                              outline=col, width=1.4, tags="gear")

        # Orbiting satellite nodes
        for i in range(3):
            angle = math.radians(self.a + i * 120)
            px = cx + r_orb1 * math.cos(angle)
            py = cy + r_orb1 * math.sin(angle)
            c.create_oval(px - 3, py - 3, px + 3, py + 3,
                          fill=mix(accent, "#ffffff", 0.7), outline="", tags="gear")

        # 4. Central Luminous Core Orb
        core_scale = 1.0 + 0.07 * breath
        r_outer_core = R * 0.32 * core_scale
        c.create_oval(cx - r_outer_core, cy - r_outer_core,
                      cx + r_outer_core, cy + r_outer_core,
                      fill=mix(theme.GLASS_3, accent, 0.15),
                      outline=mix(accent, bg, 0.65), width=1, tags="gear")

        r_mid_core = R * 0.22 * core_scale
        c.create_oval(cx - r_mid_core, cy - r_mid_core,
                      cx + r_mid_core, cy + r_mid_core,
                      fill=mix(theme.GLASS_2, accent, 0.40),
                      outline=mix(accent, bg, 0.30), width=1.5, tags="gear")

        r_inner_core = R * 0.14 * core_scale
        c.create_oval(cx - r_inner_core, cy - r_inner_core,
                      cx + r_inner_core, cy + r_inner_core,
                      fill=mix(accent, "#ffffff", 0.75),
                      outline=accent, width=2, tags="gear")

        # Core highlight
        r_glint = R * 0.05
        c.create_oval(cx - r_glint, cy - r_glint,
                      cx + r_glint, cy + r_glint,
                      fill="#ffffff", outline="", tags="gear")


# -------------------------------------------------------------- chat panel
class ChatPanel(tk.Canvas):
    """Scrolling message conversation rendered as modern rounded bubbles."""

    def __init__(self, parent, width, height):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=theme.GLASS,
            highlightthickness=0,
            bd=0,
        )
        self._width = width
        self._height = height
        self._pad = 16
        self._y = 52
        self._maxw = width - 2 * self._pad

        self._font = theme.CHAT_BODY
        self._font_measure = tkfont.Font(family=theme.SEA, size=10)
        self._label_font = theme.CHAT_LABEL
        self._header_font = theme.HEADER
        self._status_font = theme.CHAT_SYSTEM

        self.configure(scrollregion=(0, 0, width, height))
        self._draw_chrome()

        self._bubbles = {}
        self._seq = 0
        self._typing_ids = ()
        self._typing_t = 0
        self._typewriter = None
        self._anim = []

        # Optional callback invoked when the user clicks the speak (🔊)
        # button on an AI bubble. Receives the bubble text to read aloud.
        self.on_speak = None

        self.bind("<Enter>", self._on_mouse_enter)
        self.bind("<Leave>", self._on_mouse_leave)
        self.after(90, self._tick_typing)

    # -- header chrome ---------------------------------------------------
    def _draw_chrome(self):
        # Clean section header
        self.create_text(
            self._pad,
            20,
            text="Conversation",
            anchor="w",
            font=self._header_font,
            fill=theme.TEXT,
            tags="chrome",
        )

        # Subtle online status pill
        status_x = self._width - self._pad
        self.create_oval(
            status_x - 64,
            16,
            status_x - 54,
            26,
            fill=theme.ACCENT_OK,
            outline="",
            tags="chrome",
        )
        self.create_text(
            status_x - 46,
            21,
            text="Connected",
            anchor="w",
            font=self._status_font,
            fill=mix(theme.TEXT, theme.MUTED, 0.4),
            tags="chrome",
        )

        # Clean separator line
        self.create_line(
            self._pad,
            38,
            self._width - self._pad,
            38,
            fill=theme.BORDER,
            width=1,
            tags="chrome",
        )

        self._radio = self.create_line(0, 0, 0, 0, fill=theme.ACCENT, width=1, tags="chrome", capstyle=tk.ROUND)
        self._hang = self.create_line(0, 0, 0, 0, fill=theme.ACCENT_SUB, width=1, tags="chrome")

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _sender_label(sender, now=None):
        ts = (now or time.strftime("%I:%M %p"))
        return f"You  •  {ts}" if sender == "user" else f"Jarvis  •  {ts}"

    # -- scrolling -------------------------------------------------------
    def _on_mouse_enter(self, _e=None):
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>", self._on_wheel)
        self.bind_all("<Button-5>", self._on_wheel)

    def _on_mouse_leave(self, _e=None):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        if getattr(event, "delta", None):
            delta = -1 * (event.delta // 120)
        else:
            delta = -1 if event.num == 4 else 1
        self.yview_scroll(int(delta), "units")

    def _update_scroll(self):
        bottom = max(self._height, self._y + 20)
        self.configure(scrollregion=(0, 0, self._width, bottom))

    def scroll_to_bottom(self):
        self.update_idletasks()
        self.yview_moveto(1.0)

    # -- layout ----------------------------------------------------------
    def _make_bubble(
        self, sender, text, reveal=None, fade=1.0, caret=False, y=None, bid=None
    ):
        if reveal is None:
            reveal = text

        tw = self._maxw - 48
        if tw < 60:
            tw = 60

        wrapped = self._font_measure.measure((text or " ").rstrip()) > tw
        eff_w = tw if wrapped else 0

        bubble_fill = theme.USER_BUBBLE if sender == "user" else theme.AI_BUBBLE
        bubble_edge = (
            theme.USER_BUBBLE_EDGE
            if sender == "user"
            else theme.AI_BUBBLE_EDGE
        )
        text_fill = "#ffffff" if sender == "user" else theme.TEXT

        # Fade recolours toward background
        bubble_fill = mix(bubble_fill, theme.GLASS, 1.0 - fade)
        bubble_edge = mix(bubble_edge, theme.GLASS, 1.0 - fade)
        text_fill = mix(text_fill, theme.GLASS, 1.0 - fade)

        # Measure text height
        tmp = self.create_text(
            0, 0, text=text or " ", font=self._font, anchor="nw", width=eff_w, fill=text_fill
        )
        bb = self.bbox(tmp)
        txt_h = (bb[3] - bb[1]) if bb else 20
        txt_w = (bb[2] - bb[0]) if bb else tw
        self.delete(tmp)

        bubble_w = (tw if wrapped else (txt_w if txt_w else tw)) + 32
        bubble_w = max(120, min(self._maxw, bubble_w))

        x = (
            self._pad
            if sender != "user"
            else self._width - self._pad - bubble_w
        )
        y = self._y if y is None else y
        bubble_h = txt_h + 38

        rect = rounded_rect(
            self,
            x,
            y,
            x + bubble_w,
            y + bubble_h,
            radius=16,
            width=1,
            fill=bubble_fill,
            outline=bubble_edge,
            tags=("bubble",),
        )

        label_color = (
            mix("#9aa8c2", theme.GLASS, 1.0 - fade)
            if sender == "user"
            else mix(theme.ACCENT, theme.GLASS, 1.0 - fade)
        )
        label = self.create_text(
            x + 14,
            y + 11,
            anchor="w",
            text=self._sender_label(sender),
            font=self._label_font,
            fill=label_color,
            tags=("bubble",),
        )
        body = self.create_text(
            x + 14,
            y + 30,
            anchor="nw",
            text=reveal or " ",
            font=self._font,
            width=eff_w,
            fill=text_fill,
            tags=("bubble",),
        )

        caret_id = None
        if caret:
            bb2 = self.bbox(body)
            cx1 = (bb2[2] + 2) if bb2 else x + 14
            caret_id = self.create_rectangle(
                cx1,
                y + 28,
                cx1 + 2,
                y + 42,
                fill=mix(text_fill, "#ffffff", 0.4),
                outline="",
                tags=("bubble",),
            )

        # Speak (🔊) button, shown on AI (assistant) bubbles only.
        speak_ids = ()
        if sender == "ai":
            sp_w, sp_h = 26, 20
            sx = x + bubble_w - sp_w - 12
            sy = y + 10
            sp_rect = rounded_rect(
                self,
                sx,
                sy,
                sx + sp_w,
                sy + sp_h,
                radius=8,
                fill=mix(theme.AI_BUBBLE, theme.ACCENT, 0.10),
                outline=mix(theme.AI_BUBBLE_EDGE, theme.ACCENT, 0.35),
                width=1,
                tags=("bubble", "speak"),
            )
            sp_txt = self.create_text(
                sx + sp_w / 2,
                sy + sp_h / 2,
                text="\U0001f50a",
                font=("Segoe UI Emoji", 9),
                fill=theme.ACCENT,
                tags=("bubble", "speak"),
            )
            self.tag_bind(
                sp_rect,
                "<Button-1>",
                lambda e, t=text: self._speak(t),
            )
            self.tag_bind(
                sp_txt,
                "<Button-1>",
                lambda e, t=text: self._speak(t),
            )
            speak_ids = (sp_rect, sp_txt)

        if bid is None:
            bid = self._seq
            self._seq += 1
        self._bubbles[bid] = {
            "id": bid,
            "x": x,
            "y": y,
            "w": bubble_w,
            "h": bubble_h,
            "y_end": y + bubble_h,
            "sender": sender,
            "text": text,
            "ids": (rect, label, body) + (caret_id,) * (caret_id is not None) + speak_ids,
        }
        return bid

    def _delete_bubble(self, bid, pop=True):
        b = self._bubbles.pop(bid, None) if pop else self._bubbles.get(bid)
        if b:
            for i in b["ids"]:
                self.delete(i)

    def _redraw(self, bid, text, reveal=None, fade=1.0, caret=False):
        b = self._bubbles[bid]
        self._delete_bubble(bid, pop=False)
        self._make_bubble(
            b["sender"],
            text,
            reveal=reveal,
            fade=fade,
            caret=caret,
            y=b["y"],
            bid=bid,
        )

    # -- public API ------------------------------------------------------
    def clear(self):
        self._remove_typing()
        self._anim.clear()
        self.delete("bubble")
        self._bubbles.clear()
        self._y = 52
        self._typewriter = None
        self._update_scroll()

    def add_system(self, text):
        clean_text = text.lstrip("/ ").capitalize() if text.startswith("//") else text
        self.create_text(
            self._width / 2,
            self._y + 16,
            text=clean_text,
            fill=theme.MUTED,
            font=(theme.FONT_FAMILY, 9),
            tags="bubble",
        )
        self._y += 30
        self._update_scroll()
        self.scroll_to_bottom()

    def add_message(self, sender, text, animate=True):
        bid = self._make_bubble(sender, text, fade=0.0)
        self._y = self._bubbles[bid]["y_end"] + 10
        self._update_scroll()
        if animate:
            self._anim.append({"kind": "bubble", "id": bid, "t": 0.0})
            self._pump_anim()
        else:
            self._redraw(bid, text, fade=1.0)
        self.scroll_to_bottom()
        return bid

    def _speak(self, text):
        """Forward a clicked 🔊 button to the app's TTS handler."""
        if getattr(self, "on_speak", None):
            self.on_speak(text)

    def stop_current_reveal(self):
        """Immediately finish the in-progress typewriter reveal (used when a
        new conversation starts and the previous reply must stop)."""
        j = self._typewriter
        if not j:
            return
        if self._bubbles:
            bid = list(self._bubbles)[-1]
            try:
                self._redraw(bid, j["text"], caret=False)
            except Exception:
                pass
        self._typewriter = None

    # -- entrance animation ---------------------------------------------
    def _pump_anim(self):
        alive = 0
        for anim in self._anim:
            if anim["t"] >= 1.0:
                continue
            anim["t"] += 0.25
            if anim["t"] < 1.0 and anim["id"] in self._bubbles:
                alive += 1
                self._redraw(
                    anim["id"],
                    self._bubbles[anim["id"]]["text"],
                    fade=anim["t"],
                )
        if alive:
            self.after(30, self._pump_anim)
            return
        for anim in list(self._anim):
            if anim["t"] >= 1.0 and anim["id"] in self._bubbles:
                self._redraw(
                    anim["id"],
                    self._bubbles[anim["id"]]["text"],
                    fade=1.0,
                )
                self._anim.remove(anim)
        self.scroll_to_bottom()

    # -- thinking indicator ---------------------------------------------
    def show_typing(self):
        self._remove_typing()
        x = self._pad
        y = self._y
        bw, bh = 80, 34
        ids = [
            rounded_rect(
                self,
                x,
                y,
                x + bw,
                y + bh,
                radius=20,
                fill=theme.AI_BUBBLE,
                outline=theme.AI_BUBBLE_EDGE,
                width=1,
            )
        ]
        for _ in range(3):
            ids.append(
                self.create_oval(0, 0, 0, 0, fill=theme.ACCENT, outline="")
            )
        self._typing_ids = tuple(ids)
        self._typing_ox, self._typing_oy = x + 18, y + bh / 2
        self._typing_t = 0
        self._y = y + bh + 10
        self._update_scroll()
        self.scroll_to_bottom()

    def _remove_typing(self):
        for i in self._typing_ids:
            self.delete(i)
        self._typing_ids = ()

    def remove_typing(self):
        self._remove_typing()

    def _tick_typing(self):
        if self._typing_ids:
            cx, cy = self._typing_ox, self._typing_oy
            t = self._typing_t
            for i in range(3):
                y_off = 3.6 * math.sin(t * 1.9 + i * 1.6)
                x = cx + i * 16
                r = 2.7 + 0.75 * abs(math.sin(t + i))
                self.coords(
                    self._typing_ids[1 + i], x - r, cy + y_off - r, x + r, cy + y_off + r
                )
            self._typing_t += 0.26
        if self._typewriter:
            self._typewriter_step()
        self.after(80, self._tick_typing)

    # -- typewriter reveal ----------------------------------------------
    def type_message(self, sender, text, done_cb=None):
        self._remove_typing()
        self._typewriter = {
            "sender": sender,
            "text": text,
            "n": 0,
            "done": done_cb,
        }
        bid = self._make_bubble(sender, text, reveal="", caret=True)
        self._y = self._bubbles[bid]["y_end"] + 10
        self._update_scroll()
        self.scroll_to_bottom()

    def _typewriter_step(self):
        j = self._typewriter
        if not j:
            return
        step = max(6, int(len(j["text"]) / 20))
        j["n"] += step
        done = j["n"] >= len(j["text"])
        chunk = j["text"] if done else j["text"][: j["n"]]
        bid = list(self._bubbles)[-1] if self._bubbles else None
        if bid is None:
            self._typewriter = None
            return
        if done:
            self._redraw(bid, j["text"], caret=False)
            self._typewriter = None
            cb = j["done"]
            if cb:
                self.after(30, cb)
        else:
            self._redraw(bid, j["text"], reveal=chunk, caret=True)
        self._update_scroll()
        self.scroll_to_bottom()