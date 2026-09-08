"""Local application launchers (Chrome, VS Code, Python, Windows built-ins)."""

import os
import shutil
import subprocess
import sys

from config import config


def _try_paths(exe_names, extra_paths):
    for name in exe_names:
        exe = shutil.which(name)
        if exe:
            subprocess.Popen([exe])
            return True
    for p in extra_paths:
        if os.path.exists(p):
            subprocess.Popen([p])
            return True
    return False


def open_chrome() -> bool:
    return _try_paths(["chrome", "google-chrome"], config.CHROME_PATHS)


def open_vscode() -> bool:
    return _try_paths(["code"], config.VSCODE_PATHS)


def open_python() -> bool:
    exe = sys.executable or shutil.which("python")
    if exe and os.path.exists(exe):
        subprocess.Popen([exe])
        return True
    return False


def open_python_idle() -> bool:
    exe = shutil.which("idle")
    if exe:
        subprocess.Popen([exe])
        return True
    try:
        subprocess.Popen([sys.executable, "-m", "idlelib"])
        return True
    except Exception:
        return False


def _open_via_start(win_name: str) -> bool:
    if os.name != "nt":
        return False
    try:
        subprocess.Popen(f"start {win_name}", shell=True)
        return True
    except Exception as e:
        print("LAUNCH ERROR:", e)
        return False


def open_application(app_name: str) -> str:
    name = app_name.lower().strip()

    callable_launchers = {
        "chrome": open_chrome,
        "vscode": open_vscode,
        "vs code": open_vscode,
        "python": open_python,
        "python-idle": open_python_idle,
        "idle": open_python_idle,
    }
    if name in callable_launchers:
        try:
            ok = callable_launchers[name]()
            return (f"{app_name} opened successfully."
                    if ok else f"Couldn't find {app_name} on this system.")
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    if name in config.WINDOWS_BUILTINS:
        if os.name != "nt":
            return f"'{app_name}' is Windows-only."
        ok = _open_via_start(config.WINDOWS_BUILTINS[name])
        return f"{app_name} opened successfully." if ok else f"Failed to open {app_name}."

    return f"'{app_name}' isn't a known application."
