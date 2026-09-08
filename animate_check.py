import math
import sys
import tkinter as tk

from jarvis.ui import theme
from jarvis.ui.app import JarvisApp, W, H, GX, CY, PANEL_TOP, PANEL_BOT, STATES

def main():
    root = tk.Tk()
    root.withdraw()
    from jarvis.ui.widgets import Gear

    gear = Gear()
    checks = []
    def step_and_sample():
        gear.step()
        accent = STATES.get(gear.state, theme.ACCENT)
        breath = math.sin(gear.t * 1.6)
        R = 400 * 0.38
        checks.append((
            gear.state,
            f"R={R:.1f}",
            [
                "h1", "h2", "h3",
                f"r_orb1={R * 0.78:.1f}",
                f"r_orb2={R * 0.58:.1f}",
                f"core_outer={R * 0.32 * (1.0 + 0.07 * breath):.1f}",
                f"r_glint={R * 0.05:.1f}",
            ],
        ))
        return gear.state != "idle"
    gear.set_state("thinking")
    for _ in range(5):
        if step_and_sample():
            break
    gear.set_state("speaking")
    for _ in range(5):
        if step_and_sample():
            break
    gear.set_state("listening")
    for _ in range(5):
        if step_and_sample():
            break
    gear.set_state("idle")
    step_and_sample()
    print("GEAR_STATE_CHECKS", checks)

    app = JarvisApp(root)

    def report_app():
        d = app.desk
        items = d.find_withtag("statics")
        stats = {}
        for it in items:
            tags = d.gettags(it)
            if not tags:
                continue
            key = tags[0]
            coords = d.coords(it)
            stats[key] = coords
        print("APP_STATICS_COORDS", stats)
        root.destroy()
    root.after(250, report_app)
    root.mainloop()

if __name__ == "__main__":
    main()
