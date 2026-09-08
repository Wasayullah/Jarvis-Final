import os
import time
import sys
import tkinter as tk

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(PROJECT_ROOT, "screenshots")

def main():
    root = tk.Tk()
    root.withdraw()
    try:
        import jarvis.ui.app as appmod
    except Exception as e:
        print("import failed:", e, file=sys.stderr)
        sys.exit(1)
    w = 1440
    h = 860
    root.geometry(f"{w}x{h}")
    root.title("JARVIS")
    root.attributes("-alpha", 0.0)
    root.after(250, lambda: root.attributes("-alpha", 1.0))
    app = appmod.JarvisApp(root)
    root.update_idletasks()
    time.sleep(0.25)
    root.update_idletasks()
    root.attributes("-alpha", 1.0)
    time.sleep(0.5)
    root.update_idletasks()
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    except Exception:
        pass
    fn = os.path.join(SCREENSHOT_DIR, "jarvis_ui_review.png")
    app.desk.postscript(file=fn.replace(".png", ".ps"), colormode="color")
    print("saved postscript:", fn.replace(".png", ".ps"))

if __name__ == "__main__":
    main()
