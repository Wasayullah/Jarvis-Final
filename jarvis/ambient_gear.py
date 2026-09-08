"""Ambient voice-only assistant: a single colourful, smoky gear on screen.

No text input, no chat panel, no menus -- just a medium-sized animated gear
floating over the desktop. Commands arrive exclusively by voice (Windows
System.Speech via `jarvis.stt`) and answers are spoken back through TTS.

Launcher:  python gear_run.py

Controls:
    click/drag the gear  -> move the window
    single click         -> toggle the microphone on/off
    double-click / Esc   -> quit
    "exit" / "bye"       -> quit (voice, while listening)

States are shown by the gear itself:
    idle      rainbow smoke, slow spin, breathing core
    listening shimmering red swirl + sonar ping rings
    thinking  cyan smoke, fast spin, radar scan
    speaking  green smoke, gentle sway + waveform arcs
    muted     grey smoke (no microphone)
"""

import colorsys
import math
import queue
import random
import threading
import time
import tkinter as tk
from config import config
from jarvis import command
from jarvis.stt import VoiceInput
from jarvis.tts import Speaker
from jarvis.ui import theme

WW, WH = 620, 620                 # window / canvas size
CX, CY = WW // 2, WH // 2
R_GEAR = 104                      # main gear radius
R_HUB = 42                        # inner energy-core gear radius
WISP_RINGS = (50, 76, 104, 132, 160)
WISP_PER_RING = 24
ORBITS = (174, 202, 230)           # satellite orbit radii

# per-state parameters:
#   (spin rad/s, base hue, saturation, value, hue drift/s, sonar on, scan on)
#   base hue None => rainbow drift (idle)
STATE = {
    "idle":      (0.42, None, 0.85, 0.75, 0.060, False, False),
    "listening": (0.95, 0.02, 0.95, 0.82, 0.015, True, True),
    "thinking":  (2.50, 0.55, 0.90, 0.82, 0.045, False, True),
    "speaking":  (0.30, 0.38, 0.90, 0.82, 0.030, False, False),
    "muted":     (0.14, None, 0.00, 0.55, 0.010, False, False),
}


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)),
                                  max(0.0, min(1.0, v)))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


class SmokeGear(tk.Canvas):
    """The whole visual. Every item is created once and only moved/retinted
    per frame (positions every frame, colours every other frame) so it stays
    buttery at 30 fps with ~200 canvas items."""

    def __init__(self, master):
        super().__init__(master, width=WW, height=WH, bg=theme.CORNER,
                         highlightthickness=0, bd=0)
        self.state = "idle"
        self.t = 0.0
        self._ft = 0

        # ------------------------------------------------------ nebula blobs
        self._blobs = []
        for i, (br, phase) in enumerate((
                (270, 0.0), (238, 2.1), (208, 4.2), (176, 1.0), (144, 3.3))):
            self._blobs.append({
                "id": self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                       stipple="gray12"),
                "r": br, "ph": phase, "ax": 26 + i * 5, "ay": 20 + i * 4,
                "dh": (i - 2) * 0.13,
            })

        # -------------------------------------------------- aura / halo shells
        # Tkinter has no alpha compositing, so several stippled shells create
        # a surprisingly soft volumetric glow without adding dependencies.
        self._aura_shells = [
            self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                             stipple=stipple, tags="fx")
            for stipple in ("gray12", "gray12", "gray25", "gray25", "gray50")
        ]
        self.halo = self.create_oval(0, 0, 0, 0, outline="#ffffff", width=18,
                                     outlinestipple="gray25", tags="fx")
        self.ring = self.create_oval(0, 0, 0, 0, outline="#ffffff", width=2,
                                     outlinestipple="gray12", tags="fx")
        self.ring2 = self.create_oval(0, 0, 0, 0, outline="#ffffff", width=1,
                                      outlinestipple="gray12", tags="fx")
        self.breathe = self.create_oval(0, 0, 0, 0, outline="#ffffff", width=1,
                                        outlinestipple="gray12", tags="fx")
        self.sonar = self.create_oval(0, 0, 0, 0, outline=theme.ACCENT_ERR,
                                      width=2, tags="fx")
        self._auroras = [
            self.create_arc(0, 0, 0, 0, start=0, extent=110, style=tk.ARC,
                            outline="#ffffff", width=4, outlinestipple="gray25")
            for _ in range(2)
        ]
        self.scan = self.create_arc(0, 0, 0, 0, start=0, extent=45, style=tk.ARC,
                                    outline="#ffffff", width=3, outlinestipple="gray25")
        self._constellation = [
            self.create_arc(0, 0, 0, 0, start=0, extent=26, style=tk.ARC,
                            outline="#ffffff", width=2, outlinestipple="gray25",
                            tags="fx")
            for _ in range(6)
        ]

        # ------------------------------------------------------ smoke wisps
        self._wisps = []
        a_sizes = (12, 15, 18, 21, 24)
        b_sizes = (5, 6, 7, 8, 10)
        for ring in range(len(WISP_RINGS)):
            for k in range(WISP_PER_RING):
                self._wisps.append({
                    "id": self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                           stipple=("gray25" if ring % 2 else "gray12"),
                                           tags="wisp"),
                    "ring": ring, "k": k,
                    "base_r": WISP_RINGS[ring] + ring * 2 + (k % 4),
                    "a": a_sizes[ring], "b": b_sizes[ring],
                     "spin": 1.0 if ring % 2 else -1.0,
                     "seed": random.random() * math.tau,
                })

        # ------------------------------------------------- orbital satellites
        self._sats = []       # (dot, trail)
        dot_r = 3.5
        for i, orad in enumerate(ORBITS):
            for k in range(4):
                dot = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                       stipple="gray12", tags="fx")
                trail = self.create_line(0, 0, 0, 0, fill="#ffffff", width=3,
                                         capstyle=tk.ROUND, tags="fx")
                self._sats.append({"dot": dot, "trail": trail, "r": orad,
                                   "phase": k * (math.tau / 4.0) + i * 0.7,
                                   "spd": 0.9 - i * 0.14})

        # --------------------------------------------------------- sparkles
        self._sparks = []
        for _ in range(16):
            self._sparks.append({
                "id": self.create_oval(0, 0, 0, 0, fill="#ffffff", outline=""),
                "ph": 6.283 * random.random(), "rr": 96 + 46 * random.random(),
                "b": 0.5 + 0.5 * random.random(),
            })

        # ----------------------------------------------------- main gear set
        self._gear_glows = [
            self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                             stipple=stipple, tags="gear")
            for stipple in ("gray12", "gray25", "gray25", "gray50")
        ]
        self.glow = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                     stipple="gray25", tags="gear")
        self.glass = self.create_oval(0, 0, 0, 0, fill="#091326", outline="",
                                      tags="gear")
        self.rim = self.create_oval(0, 0, 0, 0, fill="#050914", outline="#ffffff",
                                    width=8, tags="gear")
        self.rim_hl = self.create_arc(0, 0, 0, 0, start=0, extent=60, style=tk.ARC,
                                      outline="#ffffff", width=3, tags="gear")
        self.rim_shadow = self.create_arc(0, 0, 0, 0, start=180, extent=150,
                                          style=tk.ARC, outline="#ffffff", width=2,
                                          tags="gear")
        self._tooth_glows = [
            self.create_line(0, 0, 0, 0, width=18, capstyle=tk.ROUND,
                             fill="#ffffff", stipple="gray25", tags="gear")
            for _ in range(18)
        ]
        self._teeth = [
            self.create_line(0, 0, 0, 0, width=8, capstyle=tk.ROUND,
                             fill="#ffffff", tags="gear")
            for _ in range(18)
        ]
        self._teeth_i = [
            self.create_line(0, 0, 0, 0, width=6, capstyle=tk.ROUND,
                             fill="#ffffff", tags="gear")
            for _ in range(8)
        ]
        self._spokes = [
            self.create_line(0, 0, 0, 0, width=2, fill="#ffffff", tags="gear")
            for _ in range(6)
        ]
        self.hub_rim = self.create_oval(0, 0, 0, 0, fill="#06090f",
                                        outline="#ffffff", width=4, tags="gear")
        self.hub_glass = self.create_oval(0, 0, 0, 0, fill="#081a2b",
                                          outline="#ffffff", width=2, tags="gear")
        self._inner_arcs = [
            self.create_arc(0, 0, 0, 0, start=0, extent=70, style=tk.ARC,
                            outline="#ffffff", width=2, tags="gear")
            for _ in range(4)
        ]

        # energy core (stacked ovals => fake radial glow)
        self.core_o = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                       stipple="gray25", tags="core")
        self.core_m = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                       stipple="gray25", tags="core")
        self.core_i = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                       stipple="gray12", tags="core")
        self.light = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="",
                                      tags="core")
        self.core_glint = self.create_oval(0, 0, 0, 0, fill="#ffffff",
                                           outline="", tags="core")
        self._core_rays = [
            self.create_line(0, 0, 0, 0, fill="#ffffff", width=2,
                             capstyle=tk.ROUND, tags="core")
            for _ in range(8)
        ]

        # --------------------------------------------------- speaking arcs
        self._rings = [
            self.create_arc(0, 0, 0, 0, start=15, extent=150, style=tk.ARC,
                            outline="#ffffff", width=4, outlinestipple="gray25")
            for _ in range(3)
        ]

    # -------------------------------------------------------------- helpers
    def _spin(self, sway=0.0):
        spin = STATE[self.state][0]
        if sway:
            spin *= (0.4 + 0.6 * abs(math.sin(self.t * sway)))
        return spin

    def _palette(self):
        _, hue, sat, val, drift, _, _ = STATE[self.state]
        if self.state == "muted":
            h = 0.0
        elif hue is None:
            h = self.t * drift
        else:
            h = hue + self.t * drift
        comp = h + 0.5
        return {
            "h": h,
            "hi": _hsv(h, sat, min(1.0, val + 0.2)),
            "mid": _hsv(h, sat, val),
            "deep": _hsv(h, max(0.25, sat - 0.25), max(0.22, val - 0.4)),
            "comp": _hsv(comp, min(1.0, sat + 0.1), min(1.0, val + 0.15)),
            "violet": _hsv(h + 0.18, min(1.0, sat + 0.05), min(1.0, val + 0.08)),
            "warm": _hsv(h - 0.12, min(1.0, sat + 0.05), min(1.0, val + 0.08)),
            "white": "#ffffff",
        }

    # -------------------------------------------------------------- drawing
    def draw(self):
        self.t += 0.033
        self._ft += 1
        p = self._palette()
        spin = self._spin(sway=2.4 if self.state == "speaking" else 0.0)
        angle = self.t * spin
        inner = self.t * -spin * 1.6
        active = self.state in ("listening", "thinking")
        pulse = (1.0 + 0.14 * abs(math.sin(self.t * (1.6 if active else 0.55))))

        # ---- nebula blobs (slow basement light, hue tied to state)
        for b in self._blobs:
            xx = CX + b["ax"] * math.sin(self.t * 0.21 + b["ph"])
            yy = CY + b["ay"] * math.cos(self.t * 0.17 + b["ph"])
            r = b["r"] * (1.0 + 0.06 * math.sin(self.t * 0.3 + b["ph"]))
            self.coords(b["id"], xx - r, yy - r, xx + r, yy + r)
            if self._ft % 2 == 0:
                bh = p["h"] + b["dh"] + 0.05 * math.sin(self.t * 0.4 + b["ph"])
                self.itemconfig(b["id"], fill=_hsv(bh, 0.65, 0.20))

        # ---- layered aura + breathing rings
        shell_sizes = (242, 210, 178, 148, 122)
        for i, oid in enumerate(self._aura_shells):
            rr = shell_sizes[i] * pulse
            self.coords(oid, CX - rr, CY - rr, CX + rr, CY + rr)
            if self._ft % 2 == 0:
                shell_h = p["h"] + (i - 2) * 0.12 + self.t * 0.012
                self.itemconfig(oid, fill=_hsv(shell_h, 0.75, 0.12 + i * 0.035))
        hr = 190 * pulse
        self.coords(self.halo, CX - hr, CY - hr, CX + hr, CY + hr)
        self.coords(self.ring, CX - 164, CY - 164, CX + 164, CY + 164)
        self.coords(self.ring2, CX - 142, CY - 142, CX + 142, CY + 142)
        br = 76 + 42 * abs(math.sin(self.t * (0.8 if self.state == "idle" else 1.8)))
        self.coords(self.breathe, CX - br, CY - br, CX + br, CY + br)
        if self._ft % 2 == 0:
            self.itemconfig(self.halo, outline=p["comp"])
            self.itemconfig(self.ring, outline=p["mid"])
            self.itemconfig(self.ring2, outline=p["comp"])
            self.itemconfig(self.breathe, outline=p["hi"])

        # ---- segmented constellation ring, like a holographic interface
        for i, oid in enumerate(self._constellation):
            rr = 184 + 9 * math.sin(self.t * 0.8 + i)
            self.coords(oid, CX - rr, CY - rr, CX + rr, CY + rr)
            self.itemconfig(oid, start=(self.t * (-26 if i % 2 else 34) +
                                        i * 61) % 360,
                            extent=18 + 10 * abs(math.sin(self.t + i)),
                            outline=p["violet"] if i % 2 else p["warm"])

        # ---- aurora arcs (rotating, ghostly)
        for i, oid in enumerate(self._auroras):
            start = (self.t * 42 + i * 180) % 360
            self.itemconfig(oid, start=start, outline=p["comp"])
        self.coords(self._auroras[0], CX - 124, CY - 124, CX + 124, CY + 124)
        self.coords(self._auroras[1], CX - 148, CY - 148, CX + 148, CY + 148)

        # ---- sonar ping (listening)
        if self.state == "listening":
            phase = (self.t * 1.5) % 1.0
            sr = 46 + phase * 150
            self.coords(self.sonar, CX - sr, CY - sr, CX + sr, CY + sr)
            self.itemconfig(self.sonar, outline=_hsv(0.02, 0.95, 0.45 + 0.55 * (1 - phase)),
                            width=3 if phase > 0.5 else 1)
        else:
            self.coords(self.sonar, 0, 0, 0, 0)

        # ---- radar scan (thinking / listening)
        if active:
            self.coords(self.scan, CX - 62, CY - 62, CX + 62, CY + 62)
            self.itemconfig(self.scan, start=(self.t * 200) % 360, outline=p["hi"])
        else:
            self.coords(self.scan, 0, 0, 0, 0)

        # ---- smoke wisps (layered, counter-rotating rings)
        for w in self._wisps:
            a = self.t * 0.55 * w["spin"] + w["k"] * (math.tau / WISP_PER_RING) \
                + w["ring"] * 0.35
            r = w["base_r"] + 8 * math.sin(self.t * 0.7 + w["k"] * 1.1)
            ca = math.cos(a)
            sa = math.sin(a)
            cx = CX + r * ca
            cy = CY + r * sa
            ex = w["a"] * abs(sa) + w["b"] * abs(ca)
            ey = w["a"] * abs(ca) + w["b"] * abs(sa)
            self.coords(w["id"], cx - ex, cy - ey, cx + ex, cy + ey)
            if self._ft % 2 == 0:
                _, hue, sat, val, drift, _, _ = STATE[self.state]
                h = (hue if hue is not None else (a + self.t * drift))
                h += 0.14 * math.sin(self.t * 0.9 + w["seed"]) + w["ring"] * 0.045
                smoke_val = max(0.16, val - w["ring"] * 0.027)
                self.itemconfig(w["id"], fill=_hsv(h, sat, smoke_val))

        # ---- orbital satellites with comet trails
        for s in self._sats:
            a = self.t * s["spd"] + s["phase"]
            ca = math.cos(a)
            sa = math.sin(a)
            r = s["r"] * (1.0 + 0.05 * math.sin(self.t * 1.3 + s["phase"]))
            x = CX + r * ca
            y = CY + r * sa
            tx = x - 16 * ca
            ty = y - 16 * sa
            self.coords(s["dot"], x - 3.5, y - 3.5, x + 3.5, y + 3.5)
            self.coords(s["trail"], tx, ty, x, y)
            if self._ft % 2 == 0:
                self.itemconfig(s["dot"], fill=p["hi"])
                self.itemconfig(s["trail"], fill=_hsv(p["h"] + 0.06, 0.7, 0.95))

        # ---- sparkles (twinkling)
        for sp in self._sparks:
            a = self.t * 0.25 + sp["ph"]
            x = CX + sp["rr"] * math.cos(a)
            y = CY + sp["rr"] * math.sin(a)
            if self._ft % 2 == 0:
                tw = sp["b"] * (0.5 + 0.5 * math.sin(self.t * 2.1 + sp["ph"] * 3))
                self.itemconfig(sp["id"], fill=_hsv(p["h"] + 0.15, 0.35, 0.5 + 0.5 * tw))
            r = 1.5 + 1.6 * abs(math.sin(self.t * 2.4 + sp["ph"] * 3))
            self.coords(sp["id"], x - r, y - r, x + r, y + r)

        # ---- main gear (outer teeth + rim + highlight + inner hub gear)
        grp = R_GEAR * pulse
        gx0, gy0 = CX - grp, CY - grp
        gx1, gy1 = CX + grp, CY + grp
        for i, oid in enumerate(self._gear_glows):
            rr = grp * (1.68 - i * 0.16)
            self.coords(oid, CX - rr, CY - rr, CX + rr, CY + rr)
            if self._ft % 2 == 0:
                self.itemconfig(oid, fill=(
                    p["violet"], p["comp"], p["mid"], p["hi"])[i])
        self.coords(self.glow, CX - grp * 1.3, CY - grp * 1.3,
                    CX + grp * 1.3, CY + grp * 1.3)
        self.coords(self.glass, CX - grp * 0.90, CY - grp * 0.90,
                    CX + grp * 0.90, CY + grp * 0.90)
        self.coords(self.rim, gx0, gy0, gx1, gy1)
        self.coords(self.rim_hl, gx0, gy0, gx1, gy1)
        self.coords(self.rim_shadow, gx0 + 3, gy0 + 3, gx1 - 3, gy1 - 3)
        self.itemconfig(self.rim_hl, start=(math.degrees(angle)) % 360)
        self.itemconfig(self.rim_shadow, start=(math.degrees(angle) + 170) % 360)
        n = len(self._teeth)
        for i, oid in enumerate(self._teeth):
            a = angle + i * (math.tau / n)
            self.coords(self._tooth_glows[i],
                        CX + (grp - 1) * math.cos(a), CY + (grp - 1) * math.sin(a),
                        CX + (grp + 19) * math.cos(a), CY + (grp + 19) * math.sin(a))
            self.coords(oid,
                        CX + (grp - 1) * math.cos(a), CY + (grp - 1) * math.sin(a),
                        CX + (grp + 19) * math.cos(a), CY + (grp + 19) * math.sin(a))
        m = len(self._teeth_i)
        hr2 = R_HUB * pulse
        for i, oid in enumerate(self._teeth_i):
            a = inner + i * (math.tau / m)
            self.coords(oid,
                        CX + (hr2 - 1) * math.cos(a), CY + (hr2 - 1) * math.sin(a),
                        CX + (hr2 + 11) * math.cos(a), CY + (hr2 + 11) * math.sin(a))
        k = len(self._spokes)
        for i, oid in enumerate(self._spokes):
            a = inner + i * (math.tau / k)
            self.coords(oid,
                        CX + 12 * math.cos(a), CY + 12 * math.sin(a),
                        CX + (hr2 - 5) * math.cos(a), CY + (hr2 - 5) * math.sin(a))
        self.coords(self.hub_rim, CX - hr2, CY - hr2, CX + hr2, CY + hr2)
        self.coords(self.hub_glass, CX - hr2 * 0.83, CY - hr2 * 0.83,
                    CX + hr2 * 0.83, CY + hr2 * 0.83)
        for i, oid in enumerate(self._inner_arcs):
            rr = hr2 + 7 + i * 4
            self.coords(oid, CX - rr, CY - rr, CX + rr, CY + rr)
            self.itemconfig(oid, start=(math.degrees(inner) + i * 90 +
                                        self.t * (18 if i % 2 else -12)) % 360,
                            outline=p["comp"] if i % 2 else p["violet"])

        # ---- energy core (breathing stacked orbs)
        bristle = 1.0 + 0.12 * abs(math.sin(self.t * (3.0 if self.state == "speaking" else 1.3)))
        for oid, kk in ((self.core_o, 34), (self.core_m, 24), (self.core_i, 15)):
            rr = kk * bristle
            self.coords(oid, CX - rr, CY - rr, CX + rr, CY + rr)
        lr = (8 + 3.5 * abs(math.sin(self.t * (3.6 if self.state == "listening" else 1.5))))
        self.coords(self.light, CX - lr, CY - lr, CX + lr, CY + lr)
        glint = 4 + 3 * abs(math.sin(self.t * 2.8))
        self.coords(self.core_glint, CX - glint, CY - glint,
                    CX + glint, CY + glint)
        for i, oid in enumerate(self._core_rays):
            ra = self.t * 0.9 + i * math.tau / len(self._core_rays)
            r0 = 15 + 3 * math.sin(self.t * 2 + i)
            r1 = 27 + 6 * abs(math.sin(self.t * 1.4 + i))
            self.coords(oid, CX + r0 * math.cos(ra), CY + r0 * math.sin(ra),
                        CX + r1 * math.cos(ra), CY + r1 * math.sin(ra))
        if self._ft % 2 == 0:
            self.itemconfig(self.glow, fill=p["hi"])
            self.itemconfig(self.rim, outline=p["mid"])
            self.itemconfig(self.rim_hl, outline=p["white"])
            for oid in self._teeth:
                self.itemconfig(oid, fill=p["mid"])
            for oid in self._tooth_glows:
                self.itemconfig(oid, fill=p["comp"])
            for oid in self._teeth_i:
                self.itemconfig(oid, fill=p["hi"])
            for oid in self._spokes:
                self.itemconfig(oid, fill=p["hi"])
            self.itemconfig(self.hub_rim, outline=p["comp"])
            self.itemconfig(self.hub_glass, outline=p["hi"])
            self.itemconfig(self.rim_shadow, outline=p["deep"])
            self.itemconfig(self.core_o, fill=_hsv(p["h"], 0.5, 0.30))
            self.itemconfig(self.core_m, fill=_hsv(p["h"], 0.65, 0.55))
            self.itemconfig(self.core_i, fill=_hsv(p["h"], 0.8, 0.9))
            self.itemconfig(self.light, fill=str(_hsv(p["h"], 0.15, 1.0)))
            self.itemconfig(self.core_glint, fill="#ffffff")
            for oid in self._core_rays:
                self.itemconfig(oid, fill=p["hi"])

        # ---- speaking waveform arcs
        if self.state == "speaking":
            for i, oid in enumerate(self._rings):
                rr = 46 + i * 20
                wob = 7 * math.sin(self.t * 5.2 + i * 2.1)
                self.coords(oid, CX - rr - wob, CY - rr - wob,
                            CX + rr + wob, CY + rr + wob)
                if self._ft % 2 == 0:
                    self.itemconfig(oid, outline=_hsv(0.38, 0.95,
                                                      0.5 + 0.5 * abs(math.sin(self.t * 4.0 + i))))
        else:
            for oid in self._rings:
                self.coords(oid, 0, 0, 0, 0)


class AmbientGear:
    """Boots the borderless gear window and drives the voice pipeline."""

    def __init__(self):
        config.ensure_dirs()
        self.root = tk.Tk()
        self.root.title("JARVIS AMBIENT")
        self.root.geometry(f"{WW}x{WH}")
        self.root.resizable(False, False)
        self.root.configure(bg=theme.CORNER)
        self.root.overrideredirect(True)
        try:
            self.root.attributes("-transparentcolor", theme.CORNER)
        except Exception:
            pass
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass
        self._center()

        self.gear = SmokeGear(self.root)
        self.gear.pack()

        self.username = "user"
        self.state = "idle"
        self._listening = False
        self._thinking = False
        self._speaking_now = False
        self._voice_thread = None
        self._closed = False
        self._bus = queue.Queue()      # thread-safe main-thread dispatch

        self.speaker = Speaker(on_state_change=self._on_speaker_state)
        self.stt = VoiceInput()

        self._press = None
        self._ignore_release = False
        self.gear.bind("<ButtonPress-1>", self._on_press)
        self.gear.bind("<ButtonRelease-1>", self._on_release)
        self.gear.bind("<B1-Motion>", self._on_drag)
        self.gear.bind("<Double-Button-1>", self._on_double)
        self.root.bind("<Escape>", lambda e: self._bye())
        self.root.bind("<space>", lambda e: self._toggle_listening())

        self.root.after(33, self._tick)
        self.root.after(500, self._boot)

    def _center(self):
        try:
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry(f"{WW}x{WH}+{(sw - WW)//2}+{(sh - WH)//2}")
        except Exception:
            pass

    # -------------------------------------------------------------- mouse
    def _on_press(self, e):
        self._press = (e.x_root, e.y_root)
        self._ignore_release = False

    def _on_drag(self, e):
        if self._press:
            dx, dy = self._press
            self.root.geometry(f"+{e.x_root - dx + self.root.winfo_x()}"
                               f"+{e.y_root - dy + self.root.winfo_y()}")
            self._press = (e.x_root, e.y_root)

    def _on_release(self, e):
        if self._ignore_release:
            return
        if self._press:
            dx = abs(e.x_root - self._press[0])
            dy = abs(e.y_root - self._press[1])
            if dx < 6 and dy < 6:                  # it was a click, not a drag
                self._toggle_listening()

    def _on_double(self, _e):
        self._ignore_release = True
        self._bye()

    # ------------------------------------------------------------- states
    def _set_state(self, state):
        self.state = state
        self.gear.state = state

    def _on_speaker_state(self, state):
        def apply():
            if state == "speaking":
                self._speaking_now = True
                self._set_state("speaking")
            else:
                self._speaking_now = False
                if not self._thinking:
                    self._set_state("listening" if self._listening else "idle")
        self._bus.put(apply)

    def _speak(self, text):
        if self.speaker.enabled and text:
            self.speaker.say(text)

    def _boot(self):
        if not self.speaker.enabled:
            self._set_state("muted")
            return
        if self.stt.available():
            self._speak("Jarvis ambient core online. Click me to open the microphone.")
        else:
            self._set_state("muted")
            self._speak("Microphone unavailable. Check your mic and default input device.")

    # -------------------------------------------------------------- voice
    def _toggle_listening(self):
        if self._thinking:
            return
        if self._listening:
            self._listening = False
            self._set_state("idle")
            return
        if not self.stt.available():
            self._set_state("muted")
            self._speak("Microphone unavailable.")
            return
        self._listening = True
        self._set_state("listening")
        if self._voice_thread is None or not self._voice_thread.is_alive():
            self._voice_thread = threading.Thread(target=self._voice_worker,
                                                  daemon=True)
            self._voice_thread.start()

    def _ui(self, fn):
        self._bus.put(fn)

    def _drain(self):
        while True:
            try:
                fn = self._bus.get_nowait()
            except queue.Empty:
                return
            fn()

    def _voice_worker(self):
        while self._listening and not self._closed:
            if self._thinking or self._speaking_now:
                time.sleep(0.25)
                continue
            try:
                text = self.stt.listen(timeout=15)
            except RuntimeError as e:
                msg = str(e)
                if any(k in msg for k in ("NO_MIC", "NO_SPEECH_ENGINE", "RESTART_FAIL")):
                    self._ui(self._voice_died)
                    return
                time.sleep(1.0)
                continue
            except Exception:
                time.sleep(1.0)
                continue
            if not text or not self._listening or self._closed:
                continue
            if len(text.strip()) < 3:              # ignore debris / half words
                continue
            if self._thinking:
                continue
            self._ui(lambda t=text: self._run_voice_command(t))

    def _voice_died(self):
        self._listening = False
        self._set_state("muted")
        self._speak("Microphone lost.")

    def _run_voice_command(self, text):
        low = text.lower().strip()
        if low in ("exit", "quit", "bye", "goodbye", "close"):
            self._bye()
            return
        self._thinking = True
        self._set_state("thinking")

        def worker():
            try:
                reply = command.process_command(text, self.username)
            except Exception as e:
                reply = f"I hit an error handling that: {e}"
            self._ui(lambda r=reply: self._on_reply(r))

        threading.Thread(target=worker, daemon=True).start()

    def _on_reply(self, reply):
        self._thinking = False
        self._set_state("listening" if self._listening else "idle")
        self._speak(reply)

    # ------------------------------------------------------------- loop
    def _tick(self):
        if self._closed:
            return
        self._drain()
        self.gear.draw()
        self.root.after(33, self._tick)

    def _bye(self):
        if self._closed:
            return
        self._closed = True
        self._listening = False
        self.stt.close()
        self._speak("Deactivating.")

        def finish():
            # Let "Deactivating." finish speaking before we quit.
            if self.speaker and self.speaker.enabled:
                self.speaker.wait_until_idle(timeout=8)
            self.root.destroy()

        def fade(step=0):
            if step >= 10:
                finish()
                return
            try:
                self.root.attributes("-alpha", 1.0 - step * 0.1)
            except Exception:
                pass
            self.root.after(18, lambda: fade(step + 1))
        fade()


def run():
    AmbientGear().root.mainloop()


if __name__ == "__main__":
    run()