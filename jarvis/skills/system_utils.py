"""System utility skills: screenshots, system/battery info, IP, shutdown,
restart, timer, clipboard and a small safe calculator."""

import datetime
import os
import platform
import socket
import subprocess
import threading
import time

from config import config

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


# ---------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------
def take_screenshot() -> str:
    if pyautogui is None:
        return "pyautogui isn't installed, so I can't take screenshots."
    config.ensure_dirs()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(config.SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
    try:
        pyautogui.screenshot().save(file_path)
        return f"Screenshot saved at {file_path}"
    except Exception as e:
        return f"Couldn't take a screenshot: {e}"


# ---------------------------------------------------------------------
# System info & battery
# ---------------------------------------------------------------------
def get_system_info() -> str:
    info = []
    info.append(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    info.append(f"Python: {platform.python_version()}")
    info.append(f"Processor: {platform.processor() or 'N/A'}")
    try:
        info.append(f"Hostname: {socket.gethostname()}")
    except Exception:
        pass
    if psutil:
        info.append(f"CPU Cores: {psutil.cpu_count(logical=False)} physical, "
                    f"{psutil.cpu_count()} logical")
        info.append(f"RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB total, "
                    f"{psutil.virtual_memory().percent}% used")
        disk = psutil.disk_usage("/")
        info.append(f"Disk: {disk.total / (1024**3):.1f} GB total, {disk.percent}% used")
        info.append(f"Boot Time: {datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(info)


def get_battery_info() -> str:
    if not psutil:
        return "Install 'psutil' for battery info: pip install psutil"
    bat = psutil.sensors_battery()
    if bat is None:
        return "No battery detected (desktop system?)."
    status = "Charging" if bat.power_plugged else "Discharging"
    return f"Battery: {bat.percent}% ({status}), time left: {bat.secsleft // 60} min"


# ---------------------------------------------------------------------
# IP address
# ---------------------------------------------------------------------
def get_ip_address() -> str:
    import requests
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"Public IP: {ip}\nLocal IP: {local_ip}\nHostname: {hostname}"
    except Exception:
        return "Couldn't fetch IP address."


# ---------------------------------------------------------------------
# Shutdown / restart
# ---------------------------------------------------------------------
def shutdown_pc() -> str:
    if os.name != "nt":
        return "Shutdown is only supported on Windows."
    try:
        os.system("shutdown /s /t 30")
        return "Shutting down in 30 seconds. Run 'shutdown /a' in cmd to cancel."
    except Exception as e:
        return f"Shutdown failed: {e}"


def restart_pc() -> str:
    if os.name != "nt":
        return "Restart is only supported on Windows."
    try:
        os.system("shutdown /r /t 30")
        return "Restarting in 30 seconds. Run 'shutdown /a' in cmd to cancel."
    except Exception as e:
        return f"Restart failed: {e}"


def cancel_shutdown() -> str:
    if os.name != "nt":
        return "Cancel only works on Windows."
    try:
        os.system("shutdown /a")
        return "Shutdown/restart cancelled."
    except Exception as e:
        return f"Cancel failed: {e}"


# ---------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------
_timer_state = {"cancelled": False}


def set_timer(seconds: int) -> str:
    if seconds <= 0 or seconds > 3600:
        return "Timer must be between 1 and 3600 seconds."

    _timer_state["cancelled"] = False

    def _countdown():
        for _ in range(seconds, 0, -1):
            if _timer_state["cancelled"]:
                return
            time.sleep(1)
        if not _timer_state["cancelled"]:
            try:
                import winsound
                for _ in range(5):
                    winsound.Beep(1000, 300)
                    time.sleep(0.1)
            except Exception:
                print("\a", end="", flush=True)

    threading.Thread(target=_countdown, daemon=True).start()
    mins, secs = divmod(seconds, 60)
    return f"Timer set for {mins}m {secs}s."


def cancel_timer() -> str:
    _timer_state["cancelled"] = True
    return "Timer cancelled."


# ---------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------
def get_clipboard() -> str:
    if pyperclip is None:
        return "Install 'pyperclip' for clipboard: pip install pyperclip"
    try:
        text = pyperclip.paste()
        return f"Clipboard: {text[:500]}" if text else "Clipboard is empty."
    except Exception as e:
        return f"Couldn't read clipboard: {e}"


# ---------------------------------------------------------------------
# Calculator (safe, no builtins)
# ---------------------------------------------------------------------
def calculate(expr: str) -> str:
    expr = expr.strip()
    if not expr:
        return "Tell me a math expression, e.g. 'calculate 2+2*3'."
    safe_chars = set("0123456789+-*/().% ")
    if not all(c in safe_chars for c in expr):
        return "I can only evaluate basic math (numbers, +, -, *, /, %, parentheses)."
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return f"{expr} = {result}"
    except ZeroDivisionError:
        return "Cannot divide by zero."
    except Exception:
        return f"I couldn't evaluate '{expr}'."
