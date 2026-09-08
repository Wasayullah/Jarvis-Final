import os
import sys
import subprocess
import time

import tkinter as tk
from PIL import Image

import jarvis.ui.app as appmod


def main():
    root = tk.Tk()
    root.withdraw()
    app = appmod.JarvisApp(root)

    canvas = app.desk
    ps_path = os.path.join("screenshots", "jarvis_ui_publish.ps")
    png_path = os.path.join("screenshots", "jarvis_ui_publish.png")

    canvas.postscript(file=ps_path, colormode="color")
    print("wrote ps", ps_path, os.path.getsize(ps_path))

    img = Image.open(ps_path)
    img.load()
    img = img.resize((appmod.W, appmod.H), Image.LANCZOS)
    img.save(png_path)
    print("wrote png", png_path, os.path.getsize(png_path))
    root.destroy()


if __name__ == "__main__":
    main()
