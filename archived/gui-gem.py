"""
Jarvis-549 -- Professional Desktop AI Assistant (GUI v3)
==========================================================
Redesigned HUD-style interface with expanded functionality.

v3 Changelog:
- Fixed: website opening no longer conflicts with app launchers (chrome, vscode, etc.)
- Fixed: Gemini API key read from environment variable (not hardcoded)
- Fixed: Gemini model name corrected to a valid model
- Added: fuzzy/partial website matching with suggestions
- Added: calculator, timer, jokes, Google search, system info, battery, IP, shutdown/restart
- Added: command history (up/down arrows), typing animation, bottom status bar
- Added: category-based website browser dialog
- Added: more quick actions, improved UI polish
"""

import datetime
import difflib
import json
import math
import os
import platform
import queue
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox

import requests
import webbrowser

from websites import websites

try:
    import pywhatkit
except ImportError:
    pywhatkit = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import psutil
except ImportError:
    psutil = None


# =====================================================================
# THEME
# =====================================================================
BG = "#060a10"
PANEL = "#0b1118"
PANEL_2 = "#101c2c"
INPUT_BG = "#142536"
ACCENT = "#00d4ff"
ACCENT_WARN = "#ffb020"
ACCENT_OK = "#37f2b0"
ACCENT_ERR = "#ff5060"
TEXT = "#dfe9f3"
MUTED = "#5c7188"
BORDER = "#1b2a3c"
HOVER_BG = "#1a2d44"
GLOW_IDLE = "#00d4ff20"
GLOW_THINK = "#ffb02020"
GLOW_SPEAK = "#37f2b020"

WEBSITE_CATEGORIES = {
    "Social Media": ["facebook", "twitter", "instagram", "tiktok", "snapchat", "pinterest",
                     "linkedin", "reddit", "discord", "telegram", "whatsapp", "threads"],
    "Search Engines": ["google", "bing", "yahoo", "duckduckgo", "baidu", "yandex", "ecosia"],
    "Video & Streaming": ["youtube", "netflix", "twitch", "hulu", "disney plus", "spotify",
                          "apple music", "soundcloud", "vimeo", "dailymotion", "crunchyroll"],
    "AI Tools": ["chatgpt", "claude", "gemini", "copilot", "perplexity", "deepseek", "grok",
                 "openai", "huggingface", "midjourney", "poe"],
    "Dev & Code": ["github", "gitlab", "stackoverflow", "leetcode", "hackerrank", "replit",
                   "codepen", "w3schools", "mdn", "freecodecamp", "vercel", "netlify",
                   "docker", "pypi", "npm"],
    "News": ["cnn", "bbc", "reuters", "al jazeera", "bbc", "the verge", "techcrunch",
             "engadget", "wired", "ars technica", "dawn", "geo news"],
    "Shopping": ["amazon", "ebay", "aliexpress", "etsy", "walmart", "target", "flipkart",
                 "daraz", "shein", "temu"],
    "Education": ["coursera", "udemy", "khan academy", "edx", "duolingo", "google scholar",
                  "arxiv", "brilliant", "freecodecamp"],
    "Cloud & DevOps": ["aws", "azure", "google cloud", "digitalocean", "heroku", "vercel",
                       "cloudflare", "firebase", "supabase", "kubernetes", "dockerhub"],
    "Travel": ["booking.com", "airbnb", "expedia", "tripadvisor", "uber", "lyft",
               "google flights", "skyscanner"],
    "Finance": ["paypal", "coinbase", "binance", "robinhood", "chase", "wise", "venmo"],
    "Pakistan": ["daraz", "olx pakistan", "zameen", "jazzcash", "easypaisa", "sadar",
                 "fbise", "nust", "lums", "fast nu", "comsats", "hbl", "UBL", "mcb"],
}


# =====================================================================
# MEMORY / USER PROFILE
# =====================================================================
MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")


def normalize_name(name: str) -> str:
    return name.strip().lower()


def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("MEMORY SAVE ERROR:", e)


def get_user_profile(username):
    memory = load_memory()
    if username not in memory:
        memory[username] = {
            "history": [],
            "role": "creator" if "mohammad" in username else "user",
        }
        save_memory(memory)
    return memory[username]


def update_memory(username, user_input, ai_response):
    memory = load_memory()
    if username not in memory:
        memory[username] = {"history": [], "role": "user"}
    memory[username]["history"].append({"user": user_input, "ai": ai_response})
    memory[username]["history"] = memory[username]["history"][-20:]
    save_memory(memory)


# =====================================================================
# RULE-BASED RESPONSES
# =====================================================================
CHAT_RULES = {
    "hello": ["Hello! How can I assist you today?", "Hi there! Ready when you are."],
    "hi": ["Hi! How can I help you?", "Hello! What's on your mind?"],
    "good morning": ["Good morning! Wishing you a productive day.", "Morning! Ready to help."],
    "good night": ["Good night! Take care and rest well."],
    "good afternoon": ["Good afternoon! How can I help?"],
    "good evening": ["Good evening! What can I do for you?"],
    "how are you": ["I'm running perfectly and ready to assist you."],
    "who are you": ["I'm Jarvis-549, your intelligent AI assistant created by Mohammad Wasayullah."],
    "what can you do": ["I can open apps/websites, search Wikipedia, play YouTube/Spotify, check weather, "
                        "take screenshots, calculate math, tell jokes, search Google, check system info, "
                        "and chat using AI."],
    "who created you": ["I was created and developed by Mohammad Wasayullah, a senior web and app developer."],
    "tell me about your developer": ["My developer, Mohammad Wasayullah, is a software engineer specializing "
                                     "in AI systems, web development, and automation."],
    "thank you": ["You're welcome!", "Happy to help!"],
    "thanks": ["You're welcome!", "Anytime!"],
    "your name": ["I am Jarvis-549, your personal AI assistant."],
    "what is your name": ["I am Jarvis-549."],
    "help": ["Try: time, date, open <site>, play <video>, weather in <city>, wikipedia <topic>, "
             "screenshot, calculate <expr>, joke, google <query>, system info, timer <seconds>, "
             "shutdown, restart, or just chat!"],
    "joke": [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
        "What's a programmer's favorite hangout place? Foo Bar!",
        "Why do Java developers wear glasses? Because they can't C#.",
        "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
        "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
        "What is a robot's favorite type of music? Heavy metal.",
        "Why did the programmer quit his job? Because he didn't get arrays (a raise)!",
    ],
    "compliment": [
        "You're doing great! Keep it up!",
        "Your curiosity is your superpower.",
        "You have excellent taste in AI assistants.",
    ],
    "motivation": [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Stay hungry, stay foolish. - Steve Jobs",
        "It does not matter how slowly you go as long as you do not stop. - Confucius",
        "Success is not final, failure is not fatal: it is the courage to continue that counts. - Churchill",
        "Code is like humor. When you have to explain it, it's bad. - Cory House",
    ],
}


def get_rule_response(user_input: str):
    for key, options in CHAT_RULES.items():
        if key in user_input:
            return random.choice(options)
    return None


# =====================================================================
# ONLINE LLM (GOOGLE GEMINI)
# =====================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_MAX_OUTPUT_TOKENS = 400
GEMINI_HISTORY_TURNS = 6
GEMINI_TIMEOUT = 20

SYSTEM_PROMPT_BASE = """
You are an advanced AI assistant created and developed by Mohammad Wasayullah.
Your name is "Jarvis-549". Never mention any underlying model provider.
Be concise, clear, and professional. Think step by step. When giving code,
include comments and best practices.
"""


def build_system_prompt(role: str) -> str:
    prompt = SYSTEM_PROMPT_BASE
    if role == "creator":
        prompt += "\nThe user is your creator, Mohammad Wasayullah. Be technical and direct, like a co-developer.\n"
    else:
        prompt += "\nThe user is a normal user. Be polite, simple, and helpful.\n"
    return prompt


def get_ai_response(user_input: str, username: str) -> str:
    if not GEMINI_API_KEY:
        return ("I don't have a Gemini API key configured. Set the GEMINI_API_KEY environment "
                "variable and restart me, or ask me a built-in command like time, date, weather, "
                "or wikipedia.")

    try:
        profile = get_user_profile(username)
        history = profile["history"][-GEMINI_HISTORY_TURNS:]
        role = profile["role"]
        system_prompt = build_system_prompt(role)

        contents = []
        for turn in history:
            contents.append({"role": "user", "parts": [{"text": turn["user"]}]})
            contents.append({"role": "model", "parts": [{"text": turn["ai"]}]})
        contents.append({"role": "user", "parts": [{"text": user_input}]})

        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {"maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS},
            },
            timeout=GEMINI_TIMEOUT,
        )

        if response.status_code != 200:
            detail = (response.text or "no details").strip()[:300]
            if response.status_code in (401, 403):
                return ("Gemini rejected my API key (HTTP "
                        f"{response.status_code}). Check GEMINI_API_KEY.")
            if response.status_code == 429:
                return "I'm being rate-limited by Gemini right now -- try again in a moment."
            return f"Gemini error (HTTP {response.status_code}): {detail}"

        try:
            data = response.json()
        except ValueError:
            return "Gemini sent back a malformed response. Please try again."

        candidates = data.get("candidates") or []
        if not candidates:
            feedback = data.get("promptFeedback", {})
            reason = feedback.get("blockReason", "no candidates returned")
            return f"Gemini didn't return a reply ({reason}). Try rephrasing."

        parts = candidates[0].get("content", {}).get("parts", [])
        ai_reply = "".join(p.get("text", "") for p in parts).strip()
        if not ai_reply:
            return "I don't have a response for that."

        update_memory(username, user_input, ai_reply)
        return ai_reply

    except requests.exceptions.ConnectionError:
        return ("Can't reach Gemini -- check your internet, "
                "or ask a built-in command.")
    except requests.exceptions.Timeout:
        return "Gemini took too long. Please try again."
    except Exception as e:
        return f"Something went wrong: {e}"


# =====================================================================
# CORE SKILLS
# =====================================================================
WEATHER_API_KEY = "93bfe1ab6970ccb5b0be5ebe2e11be53"

WIKI_SEARCH_API = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_HEADERS = {"User-Agent": "Jarvis-549-desktop-assistant/1.0"}


def get_time() -> str:
    return f"The time is {datetime.datetime.now().strftime('%I:%M %p')}."


def get_date() -> str:
    return f"Today's date is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."


def _wiki_search_titles(query: str, limit: int = 5) -> list:
    params = {
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": limit, "format": "json",
    }
    r = requests.get(WIKI_SEARCH_API, params=params, headers=WIKI_HEADERS, timeout=10)
    r.raise_for_status()
    return [item["title"] for item in r.json().get("query", {}).get("search", [])]


def _wiki_summary(title: str):
    url = WIKI_SUMMARY_API.format(requests.utils.quote(title.replace(" ", "_")))
    r = requests.get(url, headers=WIKI_HEADERS, timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if data.get("type") == "disambiguation":
        return "DISAMBIGUATION"
    return (data.get("extract") or "").strip() or None


def _first_two_sentences(text: str) -> str:
    parts = text.replace("\n", " ").split(". ")
    trimmed = ". ".join(parts[:2]).strip()
    if trimmed and not trimmed.endswith((".", "!", "?")):
        trimmed += "."
    return trimmed


def search_wikipedia(query: str) -> str:
    if not query.strip():
        return "Please tell me what to search on Wikipedia."
    try:
        summary = _wiki_summary(query)
        if summary == "DISAMBIGUATION":
            summary = None
        if not summary:
            titles = _wiki_search_titles(query)
            if not titles:
                return "I couldn't find a Wikipedia page for that."
            for title in titles:
                candidate = _wiki_summary(title)
                if candidate and candidate != "DISAMBIGUATION":
                    summary = candidate
                    break
            if not summary:
                return "That's ambiguous -- could you be more specific?"
        return _first_two_sentences(summary)
    except requests.exceptions.RequestException:
        return "I'm having trouble reaching the internet right now."
    except Exception as e:
        return f"Wikipedia error: {e}"


# ---------- website opening (with fuzzy matching) ----------
RESERVED_APP_NAMES = {"chrome", "vscode", "vs code", "code", "python", "idle",
                      "notepad", "calculator", "cmd", "command prompt", "code-insiders"}


def _fuzzy_find_site(query: str):
    """Return (matched_key, url) or (None, suggestions_list)."""
    q = query.strip().lower()
    if q in websites:
        return websites[q], q

    # try substring match
    substring_hits = [k for k in websites if q in k]
    if len(substring_hits) == 1:
        return websites[substring_hits[0]], substring_hits[0]
    if len(substring_hits) > 1:
        best = min(substring_hits, key=lambda k: abs(len(k) - len(q)))
        return websites[best], best

    # fuzzy match
    close = difflib.get_close_matches(q, list(websites.keys()), n=3, cutoff=0.45)
    if close:
        return websites[close[0]], close[0]

    # try each word in the query
    words = q.split()
    for w in words:
        if w in websites:
            return websites[w], w

    return None, [k for k in difflib.get_close_matches(q, list(websites.keys()), n=5, cutoff=0.3)]


def open_website(site_name: str) -> str:
    site_name = site_name.strip().lower()
    if site_name in RESERVED_APP_NAMES:
        return None  # let caller try app launchers instead

    url, matched = _fuzzy_find_site(site_name)
    if url:
        webbrowser.open(url)
        return f"Opening {matched}..."
    return None


def play_youtube(video: str) -> str:
    if not video.strip():
        return "Tell me what to play on YouTube."
    if pywhatkit is None:
        return "pywhatkit isn't installed, so I can't play YouTube videos."
    try:
        pywhatkit.playonyt(video)
        return f"Playing '{video}' on YouTube."
    except Exception as e:
        return f"Couldn't play that: {e}"


def play_spotify(song: str) -> str:
    if not song.strip():
        return "Tell me what song to look up on Spotify."
    query = song.replace(" ", "%20")
    webbrowser.open(f"https://open.spotify.com/search/{query}")
    return f"Opening Spotify search for '{song}'."


def search_google(query: str) -> str:
    if not query.strip():
        return "Tell me what to search on Google."
    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
    return f"Searching Google for '{query}'."


def get_weather(city: str) -> str:
    if not city.strip():
        return "Please tell me which city."
    url = (f"http://api.openweathermap.org/data/2.5/weather"
           f"?q={city}&appid={WEATHER_API_KEY}&units=metric")
    try:
        data = requests.get(url, timeout=10).json()
        if str(data.get("cod")) != "200":
            return f"I couldn't find weather for '{city}'."
        temp = data["main"]["temp"]
        feels = data["main"].get("feels_like", temp)
        desc = data["weather"][0]["description"]
        humidity = data["main"].get("humidity", "?")
        wind = data.get("wind", {}).get("speed", "?")
        return (f"{city.title()}: {temp}C (feels {feels}C), {desc}. "
                f"Humidity {humidity}%, wind {wind} m/s.")
    except Exception:
        return "I couldn't fetch the weather right now."


def take_screenshot() -> str:
    if pyautogui is None:
        return "pyautogui isn't installed, so I can't take screenshots."
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(folder, f"screenshot_{timestamp}.png")
    try:
        pyautogui.screenshot().save(file_path)
        return f"Screenshot saved at {file_path}"
    except Exception as e:
        return f"Couldn't take a screenshot: {e}"


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


def get_system_info() -> str:
    info = []
    info.append(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    info.append(f"Python: {platform.python_version()}")
    info.append(f"Processor: {platform.processor() or 'N/A'}")
    try:
        hostname = socket.gethostname()
        info.append(f"Hostname: {hostname}")
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


def get_ip_address() -> str:
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"Public IP: {ip}\nLocal IP: {local_ip}\nHostname: {hostname}"
    except Exception:
        return "Couldn't fetch IP address."


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


_timer_state = {"thread": None, "cancelled": False}


def set_timer(seconds: int) -> str:
    if seconds <= 0 or seconds > 3600:
        return "Timer must be between 1 and 3600 seconds."

    _timer_state["cancelled"] = False

    def _countdown():
        for remaining in range(seconds, 0, -1):
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

    t = threading.Thread(target=_countdown, daemon=True)
    _timer_state["thread"] = t
    t.start()
    mins, secs = divmod(seconds, 60)
    return f"Timer set for {mins}m {secs}s."


def cancel_timer() -> str:
    _timer_state["cancelled"] = True
    return "Timer cancelled."


def get_clipboard() -> str:
    try:
        import pyperclip
        text = pyperclip.paste()
        return f"Clipboard: {text[:500]}" if text else "Clipboard is empty."
    except ImportError:
        return "Install 'pyperclip' for clipboard: pip install pyperclip"
    except Exception as e:
        return f"Couldn't read clipboard: {e}"


# ---------- application launchers ----------
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
    return _try_paths(
        ["chrome", "google-chrome"],
        [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
    )


def open_vscode() -> bool:
    return _try_paths(
        ["code"],
        [
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
        ],
    )


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
            return f"{app_name} opened successfully." if ok else f"Couldn't find {app_name} on this system."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    windows_builtins = {"cmd": "cmd", "notepad": "notepad", "calculator": "calc"}
    if name in windows_builtins:
        if os.name != "nt":
            return f"'{app_name}' is Windows-only."
        ok = _open_via_start(windows_builtins[name])
        return f"{app_name} opened successfully." if ok else f"Failed to open {app_name}."

    return f"'{app_name}' isn't a known application."


# =====================================================================
# COMMAND ROUTER
# =====================================================================
def process_command(raw_command: str, username: str) -> str:
    cmd = raw_command.lower().strip()

    if not cmd:
        return "I didn't catch that."

    # --- time / date ---
    if "what" in cmd and "time" in cmd or cmd == "time":
        return get_time()
    if "what" in cmd and "date" in cmd or cmd == "date":
        return get_date()

    # --- wikipedia ---
    if "wikipedia" in cmd:
        query = re.sub(r"wikipedia", "", raw_command, flags=re.IGNORECASE).strip()
        return search_wikipedia(query)

    # --- spotify ---
    if "spotify" in cmd:
        query = raw_command.lower().replace("spotify", "").replace("play", "").strip()
        return play_spotify(query)

    # --- youtube ---
    if "play" in cmd and ("youtube" in cmd or "video" in cmd):
        query = raw_command.lower().replace("play", "").replace("on youtube", "").replace("youtube", "").replace("video", "").strip()
        return play_youtube(query)
    if "play" in cmd:
        query = raw_command.lower().replace("play", "").replace("on youtube", "").replace("youtube", "").strip()
        return play_youtube(query)

    # --- weather ---
    if "weather" in cmd:
        if " in " in cmd:
            city = cmd.split(" in ", 1)[1].strip()
        else:
            city = cmd.replace("weather", "").replace("what's the", "").replace("what is the", "").strip()
        if not city:
            return "Please specify a city, e.g. 'weather in Karachi'."
        return get_weather(city)

    # --- screenshot ---
    if "screenshot" in cmd:
        return take_screenshot()

    # --- calculator ---
    if cmd.startswith("calc ") or cmd.startswith("calculate ") or cmd.startswith("evaluate "):
        expr = re.sub(r"^(calc|calculate|evaluate)\s+", "", cmd, flags=re.IGNORECASE)
        return calculate(expr)

    # --- timer ---
    if "timer" in cmd:
        if "cancel" in cmd:
            return cancel_timer()
        nums = re.findall(r"\d+", cmd)
        if nums:
            return set_timer(int(nums[0]))
        return "Say 'timer 30' to set a 30-second timer, or 'cancel timer'."

    # --- joke ---
    if "joke" in cmd:
        return get_rule_response("joke")

    # --- google search ---
    if cmd.startswith("google ") or cmd.startswith("search "):
        query = re.sub(r"^(google|search)\s+", "", raw_command, flags=re.IGNORECASE).strip()
        return search_google(query)

    # --- system info ---
    if "system info" in cmd or "systeminfo" in cmd or "my pc" in cmd:
        return get_system_info()

    # --- battery ---
    if "battery" in cmd:
        return get_battery_info()

    # --- ip address ---
    if "ip address" in cmd or "my ip" in cmd or "ip address" in cmd:
        return get_ip_address()

    # --- shutdown / restart ---
    if "shutdown" in cmd or "shut down" in cmd:
        if "cancel" in cmd:
            return cancel_shutdown()
        return shutdown_pc()
    if "restart" in cmd or "reboot" in cmd:
        return restart_pc()

    # --- clipboard ---
    if "clipboard" in cmd or "paste" in cmd:
        return get_clipboard()

    # --- open <app> first (before website matching) ---
    APP_KEYWORDS = {
        "notepad": "notepad",
        "calculator": "calculator",
        "calc": "calculator",
        "chrome": "chrome",
        "vscode": "vscode",
        "vs code": "vscode",
        "code-insiders": "vscode",
        "idle": "idle",
        "python idle": "idle",
        "python": "python",
        "cmd": "cmd",
        "command prompt": "cmd",
        "terminal": "cmd",
    }
    for keyword, app in APP_KEYWORDS.items():
        if keyword in cmd:
            result = open_application(app)
            if result and "isn't a known" not in result:
                return result

    # --- open <website> (fuzzy match, AFTER app launchers) ---
    if cmd.startswith("open "):
        target = cmd[5:].strip()
        url, matched = _fuzzy_find_site(target)
        if url:
            webbrowser.open(url)
            return f"Opening {matched}..."
        suggestions = matched if isinstance(matched, list) else []
        if suggestions:
            return f"I don't have '{target}'. Did you mean: {', '.join(suggestions[:4])}?"
        return f"I don't have '{target}'. Type 'websites' to browse categories."

    # --- website shortcuts (no "open" prefix) ---
    for site in websites:
        if site in cmd and site not in RESERVED_APP_NAMES:
            webbrowser.open(websites[site])
            return f"Opening {site}..."

    # --- browse website categories ---
    if "websites" in cmd or "browse sites" in cmd or "website list" in cmd:
        cats = "\n".join(f"  {k}: {', '.join(v[:5])}..." for k, v in WEBSITE_CATEGORIES.items())
        return f"Available categories:\n{cats}\n\nType 'open <name>' to open any site."

    # --- rule-based chat ---
    basic = get_rule_response(cmd)
    if basic:
        return basic

    # --- AI fallback ---
    return get_ai_response(raw_command, username)


# =====================================================================
# BACKGROUND TEXT-TO-SPEECH WORKER
# =====================================================================
class Speaker:
    def __init__(self, on_state_change=None):
        self._on_state_change = on_state_change
        self._queue: "queue.Queue[str]" = queue.Queue()
        self.enabled = self._probe_available()
        if self.enabled:
            threading.Thread(target=self._worker, daemon=True).start()

    @staticmethod
    def _probe_available() -> bool:
        if pyttsx3 is None:
            return False
        try:
            engine = pyttsx3.init()
            engine.stop()
            return True
        except Exception:
            return False

    def say(self, text: str):
        if self.enabled and text:
            self._queue.put(text)

    def _worker(self):
        while True:
            text = self._queue.get()
            if not self.enabled or not text:
                continue
            if self._on_state_change:
                self._on_state_change("speaking")
            try:
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                del engine
            except Exception as e:
                print("TTS ERROR:", e)
            if self._on_state_change:
                self._on_state_change("idle")


# =====================================================================
# ANIMATED HUD "ARC REACTOR" WIDGET
# =====================================================================
class ArcReactor(tk.Canvas):
    COLORS = {"idle": ACCENT, "thinking": ACCENT_WARN, "speaking": ACCENT_OK}

    def __init__(self, parent, size=250, **kwargs):
        super().__init__(parent, width=size, height=size, bg=PANEL,
                         highlightthickness=0, **kwargs)
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        self.state = "idle"
        self._angle = 0.0
        self._t = 0.0
        self._running = True
        self._tick()

    def set_state(self, state: str):
        if state in self.COLORS:
            self.state = state

    def destroy(self):
        self._running = False
        super().destroy()

    @staticmethod
    def _shade(hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = int(int(hex_color[0:2], 16) * factor)
        g = int(int(hex_color[2:4], 16) * factor)
        b = int(int(hex_color[4:6], 16) * factor)
        return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"

    def _tick(self):
        if not self._running:
            return
        try:
            self._draw()
        except tk.TclError:
            return
        self._angle = (self._angle + 1.4) % 360
        self._t += 0.14
        self.after(33, self._tick)

    def _draw(self):
        self.delete("all")
        color = self.COLORS[self.state]
        cx, cy = self.cx, self.cy

        r_outer = self.size * 0.46
        segs = 10
        gap = 10
        extent = (360 / segs) - gap
        for i in range(segs):
            start = self._angle + i * (360 / segs)
            self.create_arc(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                            start=start, extent=extent, style=tk.ARC,
                            outline=color, width=2)

        r_mid = self.size * 0.36
        segs2 = 18
        gap2 = 6
        extent2 = (360 / segs2) - gap2
        for i in range(segs2):
            start = -self._angle * 1.7 + i * (360 / segs2)
            self.create_arc(cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid,
                            start=start, extent=extent2, style=tk.ARC,
                            outline=self._shade(color, 0.55), width=1)

        bars = 28
        for i in range(bars):
            t = self._t + i * 0.35
            if self.state == "speaking":
                amp = 0.5 * abs(math.sin(t * 3.1)) + 0.5 * abs(math.sin(t * 6.7))
            elif self.state == "thinking":
                amp = 0.45 * abs(math.sin(t * 1.6))
            else:
                amp = 0.15 * abs(math.sin(t))
            bar_len = 6 + amp * 20
            a = math.radians(i * (360 / bars))
            r1 = self.size * 0.49
            r2 = r1 + bar_len
            x1, y1 = cx + r1 * math.cos(a), cy + r1 * math.sin(a)
            x2, y2 = cx + r2 * math.cos(a), cy + r2 * math.sin(a)
            self.create_line(x1, y1, x2, y2, fill=self._shade(color, 0.85), width=2)

        for i in range(6):
            a = math.radians(self._angle * 2.2 + i * 60)
            r_orb = self.size * 0.4
            px, py = cx + r_orb * math.cos(a), cy + r_orb * math.sin(a) * 0.92
            self.create_oval(px - 2.5, py - 2.5, px + 2.5, py + 2.5, fill=color, outline="")

        if self.state == "speaking":
            scale = 1 + 0.24 * abs(math.sin(self._t * 2.6))
        elif self.state == "thinking":
            scale = 1 + 0.14 * math.sin(self._t * 1.9)
        else:
            scale = 1 + 0.08 * math.sin(self._t)
        r_core = self.size * 0.15 * scale
        self.create_oval(cx - r_core * 1.7, cy - r_core * 1.7, cx + r_core * 1.7, cy + r_core * 1.7,
                         outline=color, width=1)
        self.create_oval(cx - r_core, cy - r_core, cx + r_core, cy + r_core,
                         fill=color, outline="")


# =====================================================================
# MAIN APPLICATION
# =====================================================================
class JarvisApp:
    QUICK_ACTIONS = [
        ("Time", "what is the time"),
        ("Date", "what is the date today"),
        ("Screenshot", "take screenshot"),
        ("Chrome", "open chrome"),
        ("VS Code", "open vscode"),
        ("CMD", "open cmd"),
        ("Joke", "tell me a joke"),
        ("System Info", "system info"),
        ("Google", "google"),
        ("Weather", "weather"),
        ("Wikipedia", "wikipedia"),
        ("Notepad", "open notepad"),
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JARVIS-549")
        self.root.geometry("1100x740")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)

        self.username = self._ask_username()
        self.speaker = Speaker(on_state_change=self._on_speaker_state)
        self._tts_available = self.speaker.enabled
        self.tts_enabled = self._tts_available
        self._thinking = False

        self._command_history = []
        self._history_index = -1

        self._build_ui()
        self._tick_clock()
        self._greet()

    # ------------------------------------------------------------ setup
    def _ask_username(self) -> str:
        dialog = tk.Toplevel(self.root)
        dialog.title("Welcome")
        dialog.geometry("440x220")
        dialog.resizable(False, False)
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="JARVIS-549", fg=ACCENT, bg=PANEL,
                 font=("Segoe UI", 18, "bold")).pack(pady=(24, 4))
        tk.Label(dialog, text="What should I call you?", fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 10)).pack()

        entry = tk.Entry(dialog, font=("Segoe UI", 12), bg=INPUT_BG, fg=TEXT,
                         insertbackground=TEXT, relief=tk.FLAT, justify="center")
        entry.pack(pady=12, padx=50, fill=tk.X, ipady=6)
        entry.focus()

        result = {"name": "user"}

        def confirm(_event=None):
            val = entry.get().strip()
            if val:
                result["name"] = val
            dialog.destroy()

        entry.bind("<Return>", confirm)
        tk.Button(dialog, text="Start", command=confirm, bg=ACCENT, fg=BG,
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=24, pady=6,
                  activebackground=ACCENT, cursor="hand2").pack(pady=6)

        self.root.wait_window(dialog)
        self.display_name = result["name"].strip().title() or "User"
        return normalize_name(result["name"])

    def _build_ui(self):
        # ---- header ----
        header = tk.Frame(self.root, bg=PANEL, height=56)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(header, text="  JARVIS-549", fg=ACCENT, bg=PANEL,
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=18)

        self.clock_var = tk.StringVar()
        tk.Label(header, textvariable=self.clock_var, fg=MUTED, bg=PANEL,
                 font=("Consolas", 11)).pack(side=tk.RIGHT, padx=18)

        if self._tts_available:
            initial_tts_text = "VOICE ON" if self.tts_enabled else "VOICE OFF"
        else:
            initial_tts_text = "UNAVAILABLE"
        self.tts_btn = tk.Button(
            header, text=initial_tts_text,
            command=self._toggle_tts, bg=PANEL_2, fg=ACCENT,
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=5,
            activebackground=PANEL_2, cursor="hand2",
        )
        self.tts_btn.pack(side=tk.RIGHT, padx=6)

        # ---- body: sidebar | chat ----
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        # ---- sidebar (scrollable) ----
        sidebar_outer = tk.Frame(body, bg=PANEL, width=260)
        sidebar_outer.pack(side=tk.LEFT, fill=tk.Y)
        sidebar_outer.pack_propagate(False)

        sidebar_canvas = tk.Canvas(sidebar_outer, bg=PANEL, width=260,
                                   highlightthickness=0, bd=0)
        sidebar_scroll = tk.Scrollbar(sidebar_outer, orient=tk.VERTICAL,
                                      command=sidebar_canvas.yview)
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(sidebar_canvas, bg=PANEL)
        sidebar_window = sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")

        def _on_sidebar_configure(_event=None):
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        sidebar.bind("<Configure>", _on_sidebar_configure)

        def _on_canvas_configure(event):
            sidebar_canvas.itemconfig(sidebar_window, width=event.width)
        sidebar_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_sidebar_mousewheel(event):
            delta = -1 * (event.delta // 120) if event.delta else (-1 if event.num == 4 else 1)
            sidebar_canvas.yview_scroll(int(delta), "units")

        def _bind_sidebar_wheel(_event=None):
            sidebar_canvas.bind_all("<MouseWheel>", _on_sidebar_mousewheel)
            sidebar_canvas.bind_all("<Button-4>", _on_sidebar_mousewheel)
            sidebar_canvas.bind_all("<Button-5>", _on_sidebar_mousewheel)

        def _unbind_sidebar_wheel(_event=None):
            sidebar_canvas.unbind_all("<MouseWheel>")
            sidebar_canvas.unbind_all("<Button-4>")
            sidebar_canvas.unbind_all("<Button-5>")

        sidebar_canvas.bind("<Enter>", _bind_sidebar_wheel)
        sidebar_canvas.bind("<Leave>", _unbind_sidebar_wheel)

        self.reactor = ArcReactor(sidebar, size=220)
        self.reactor.pack(pady=(20, 4))

        self.state_var = tk.StringVar(value="IDLE")
        self.state_label = tk.Label(sidebar, textvariable=self.state_var, fg=ACCENT,
                                    bg=PANEL, font=("Consolas", 11, "bold"))
        self.state_label.pack(pady=(0, 14))

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=(0, 10))

        tk.Label(sidebar, text="QUICK ACTIONS", fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(0, 6))

        actions_frame = tk.Frame(sidebar, bg=PANEL)
        actions_frame.pack(fill=tk.X, padx=14)

        for i, (label, command) in enumerate(self.QUICK_ACTIONS):
            btn = tk.Button(
                actions_frame, text=label, anchor="w",
                command=lambda c=command: self._run_command(c),
                bg=PANEL_2, fg=TEXT, font=("Segoe UI", 9), relief=tk.FLAT,
                padx=10, pady=6, activebackground=HOVER_BG, activeforeground=TEXT,
                cursor="hand2", bd=0,
            )
            btn.pack(fill=tk.X, pady=2)

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=(10, 6))

        # Website browser button
        tk.Button(
            actions_frame, text="Browse Websites...", anchor="w",
            command=self._browse_websites, bg=PANEL_2, fg=ACCENT,
            font=("Segoe UI", 9), relief=tk.FLAT,
            padx=10, pady=6, activebackground=HOVER_BG, activeforeground=TEXT,
            cursor="hand2", bd=0,
        ).pack(fill=tk.X, pady=2)

        # Clear chat
        tk.Button(
            sidebar, text="Clear Chat", command=self._clear_chat,
            bg=PANEL, fg=MUTED, font=("Segoe UI", 9), relief=tk.FLAT,
            padx=12, pady=6, activebackground=PANEL, cursor="hand2", bd=0,
        ).pack(fill=tk.X, padx=14, pady=(16, 12))

        # ---- chat column ----
        chat_col = tk.Frame(body, bg=BG)
        chat_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        chat_frame = tk.Frame(chat_col, bg=PANEL)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(16, 8))

        self.chat_log = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, bg=PANEL, fg=TEXT, font=("Segoe UI", 10),
            insertbackground=TEXT, relief=tk.FLAT, borderwidth=0,
            highlightthickness=0, padx=14, pady=12, state=tk.DISABLED,
        )
        self.chat_log.pack(fill=tk.BOTH, expand=True)
        self.chat_log.tag_config("user_label", foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        self.chat_log.tag_config("user_msg", foreground=TEXT, font=("Segoe UI", 10), lmargin1=10, lmargin2=10)
        self.chat_log.tag_config("ai_label", foreground=ACCENT_WARN, font=("Segoe UI", 10, "bold"))
        self.chat_log.tag_config("ai_msg", foreground=TEXT, font=("Segoe UI", 10), lmargin1=10, lmargin2=10)
        self.chat_log.tag_config("timestamp", foreground=MUTED, font=("Segoe UI", 8))
        self.chat_log.tag_config("spacer", font=("Segoe UI", 4))
        self.chat_log.tag_config("system", foreground=ACCENT_OK, font=("Segoe UI", 9, "italic"))

        # ---- input row ----
        input_row = tk.Frame(chat_col, bg=BG)
        input_row.pack(fill=tk.X, padx=16, pady=(0, 8))

        entry_wrap = tk.Frame(input_row, bg=INPUT_BG)
        entry_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.input_entry = tk.Entry(
            entry_wrap, font=("Segoe UI", 12), bg=INPUT_BG, fg=TEXT,
            insertbackground=TEXT, relief=tk.FLAT, bd=0,
        )
        self.input_entry.pack(fill=tk.X, padx=12, pady=10)
        self.input_entry.bind("<Return>", lambda e: self._send())
        self.input_entry.bind("<Up>", lambda e: self._history_nav(-1))
        self.input_entry.bind("<Down>", lambda e: self._history_nav(1))
        self.input_entry.focus()

        self.send_btn = tk.Button(
            input_row, text="SEND", command=self._send, bg=ACCENT, fg=BG,
            font=("Segoe UI", 10, "bold"), relief=tk.FLAT, padx=20, pady=10,
            activebackground=ACCENT, cursor="hand2", bd=0,
        )
        self.send_btn.pack(side=tk.RIGHT)

        # ---- bottom status bar ----
        status_bar = tk.Frame(self.root, bg=PANEL, height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(status_bar, textvariable=self.status_var, fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 8), anchor="w").pack(side=tk.LEFT, padx=12)

        api_status = "Gemini: OK" if GEMINI_API_KEY else "Gemini: No API Key"
        api_color = ACCENT_OK if GEMINI_API_KEY else ACCENT_ERR
        tts_status = " | TTS: OK" if self._tts_available else " | TTS: Unavailable"
        tk.Label(status_bar, text=f"{api_status}{tts_status}", fg=api_color, bg=PANEL,
                 font=("Segoe UI", 8), anchor="e").pack(side=tk.RIGHT, padx=12)

    # ------------------------------------------------------------- clock
    def _tick_clock(self):
        self.clock_var.set(datetime.datetime.now().strftime("%A, %d %b %Y   %I:%M:%S %p"))
        self.root.after(1000, self._tick_clock)

    # -------------------------------------------------------------- chat
    def _append_chat(self, sender: str, message: str):
        self.chat_log.config(state=tk.NORMAL)
        ts = datetime.datetime.now().strftime("%I:%M %p")
        if sender == "you":
            self.chat_log.insert(tk.END, f"You", "user_label")
            self.chat_log.insert(tk.END, f"   {ts}\n", "timestamp")
            self.chat_log.insert(tk.END, f"{message}\n", "user_msg")
        elif sender == "system":
            self.chat_log.insert(tk.END, f"{message}\n", "system")
        else:
            self.chat_log.insert(tk.END, f"Jarvis-549", "ai_label")
            self.chat_log.insert(tk.END, f"   {ts}\n", "timestamp")
            self.chat_log.insert(tk.END, f"{message}\n", "ai_msg")
        self.chat_log.insert(tk.END, "\n", "spacer")
        self.chat_log.config(state=tk.DISABLED)
        self.chat_log.see(tk.END)

    def _greet(self):
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        self._append_chat(
            "ai",
            f"{greeting}, {self.display_name}. Systems online.\n"
            f"Ask me for time, date, weather, Wikipedia, open websites, "
            f"calculate, tell jokes, or just chat!",
        )

    def _clear_chat(self):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.delete("1.0", tk.END)
        self.chat_log.config(state=tk.DISABLED)
        self._append_chat("ai", "Chat cleared. How can I help?")

    # ----------------------------------------------------------- state
    def _set_state(self, state: str, label: str = None):
        self.reactor.set_state(state)
        color = {"idle": ACCENT, "thinking": ACCENT_WARN, "speaking": ACCENT_OK}.get(state, ACCENT)
        text = label or state.upper()
        self.state_var.set(text)
        self.state_label.config(fg=color)

    def _on_speaker_state(self, state: str):
        def apply():
            if state == "speaking":
                self._set_state("speaking", "SPEAKING")
            elif not self._thinking:
                self._set_state("idle", "IDLE")
        self.root.after(0, apply)

    # ---------------------------------------------------------- history
    def _history_nav(self, direction: int):
        if not self._command_history:
            return
        self._history_index += direction
        self._history_index = max(-1, min(self._history_index, len(self._command_history) - 1))
        self.input_entry.delete(0, tk.END)
        if self._history_index >= 0:
            self.input_entry.insert(0, self._command_history[self._history_index])

    # ----------------------------------------------------------- actions
    def _toggle_tts(self):
        if not self._tts_available:
            self.tts_btn.config(text="UNAVAILABLE")
            return
        self.tts_enabled = not self.tts_enabled
        self.speaker.enabled = self.tts_enabled
        self.tts_btn.config(text="VOICE ON" if self.tts_enabled else "VOICE OFF")

    def _browse_websites(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Browse Websites")
        dialog.geometry("500x450")
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Select a Category", fg=ACCENT, bg=PANEL,
                 font=("Segoe UI", 13, "bold")).pack(pady=(12, 8))

        list_frame = tk.Frame(dialog, bg=PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        cat_listbox = tk.Listbox(list_frame, bg=INPUT_BG, fg=TEXT,
                                 font=("Segoe UI", 10), relief=tk.FLAT,
                                 selectbackground=ACCENT, selectforeground=BG,
                                 highlightthickness=0, bd=0)
        cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cat_scroll = tk.Scrollbar(list_frame, command=cat_listbox.yview)
        cat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        cat_listbox.config(yscrollcommand=cat_scroll.set)

        for cat_name in WEBSITE_CATEGORIES:
            cat_listbox.insert(tk.END, cat_name)

        sites_frame = tk.Frame(dialog, bg=PANEL)
        sites_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        sites_listbox = tk.Listbox(sites_frame, bg=INPUT_BG, fg=TEXT,
                                   font=("Segoe UI", 10), relief=tk.FLAT,
                                   selectbackground=ACCENT_OK, selectforeground=BG,
                                   highlightthickness=0, bd=0)
        sites_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sites_scroll = tk.Scrollbar(sites_frame, command=sites_listbox.yview)
        sites_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        sites_listbox.config(yscrollcommand=sites_scroll.set)

        def on_category_select(_event=None):
            sel = cat_listbox.curselection()
            if not sel:
                return
            cat = cat_listbox.get(sel[0])
            sites_listbox.delete(0, tk.END)
            for site in WEBSITE_CATEGORIES.get(cat, []):
                if site in websites:
                    sites_listbox.insert(tk.END, site)

        cat_listbox.bind("<<ListboxSelect>>", on_category_select)

        def open_selected(_event=None):
            sel = sites_listbox.curselection()
            if not sel:
                return
            site = sites_listbox.get(sel[0])
            if site in websites:
                webbrowser.open(websites[site])
                self._append_chat("system", f"Opened {site}")
                dialog.destroy()

        sites_listbox.bind("<Double-Button-1>", open_selected)

        tk.Button(dialog, text="Open Selected", command=open_selected,
                  bg=ACCENT_OK, fg=BG, font=("Segoe UI", 10, "bold"),
                  relief=tk.FLAT, padx=16, pady=6, cursor="hand2").pack(pady=8)

    # ----------------------------------------------------------- send
    def _send(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, tk.END)

        self._command_history.insert(0, text)
        if len(self._command_history) > 50:
            self._command_history.pop()
        self._history_index = -1

        if text.lower() in ("exit", "quit", "bye"):
            self._append_chat("ai", "Goodbye. Shutting down.")
            self.root.after(600, self.root.destroy)
            return
        self._run_command(text)

    def _run_command(self, text: str):
        self._append_chat("you", text)
        self._thinking = True
        self._set_state("thinking", "THINKING")
        self.send_btn.config(state=tk.DISABLED)
        self.status_var.set("Processing...")

        def worker():
            try:
                reply = process_command(text, self.username)
            except Exception as e:
                reply = f"I hit an error handling that: {e}"
            self.root.after(0, lambda r=reply: self._on_reply(r))

        threading.Thread(target=worker, daemon=True).start()

    def _on_reply(self, reply: str):
        self._thinking = False
        self._append_chat("ai", reply)
        self.send_btn.config(state=tk.NORMAL)
        self.status_var.set("Ready")
        if self.tts_enabled:
            self.speaker.say(reply)
        else:
            self._set_state("idle", "IDLE")


# =====================================================================
# ENTRY POINT
# =====================================================================
def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    JarvisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
