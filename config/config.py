"""Centralized configuration: paths, theme colors, constants and categories.

Import these from anywhere via::

    from config import config
    print(config.ACCENT)
"""

import os

# ---------------------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------------------
# Project root = two directories above this file's package dir:
#   <root>/jarvis/../config/ -> root is <root>
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "screenshots")
ARCHIVED_DIR = os.path.join(PROJECT_ROOT, "archived")

# Memory / user profile store
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")


# ---------------------------------------------------------------------
# .ENV LOADER (zero dependencies)
# ---------------------------------------------------------------------
# Loads <root>/.env into os.environ if it exists. Simple KEY=VALUE parser
# that supports comments (#) and quoted values. Real os.environ values
# always win over the .env file.
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")


def load_dotenv(path: str = ENV_FILE) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Never override a value already set in the real environment.
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print("WARNING: failed to read .env file:", e)


load_dotenv()


def ensure_dirs():
    """Create runtime folders (data, screenshots) if they don't exist."""
    for d in (DATA_DIR, SCREENSHOTS_DIR):
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------
# THEME COLORS  (primary blue + white)
# ---------------------------------------------------------------------
BG = "#ffffff"
PANEL = "#f4f7fc"
PANEL_2 = "#eef3fa"
INPUT_BG = "#f2f6fb"
ACCENT = "#1e6fff"
ACCENT_WARN = "#f59e0b"
ACCENT_OK = "#22c55e"
ACCENT_ERR = "#ef4444"
TEXT = "#0f2550"
MUTED = "#5b6b87"
BORDER = "#d7e2f2"
HOVER_BG = "#e6eefb"

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

# ---------------------------------------------------------------------
# ONLINE AI (GEMINI) CONFIGURATION
# ---------------------------------------------------------------------
# Read from environment / .env. NEVER hardcode secrets in source.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
GEMINI_MAX_OUTPUT_TOKENS = 4096
GEMINI_HISTORY_TURNS = 6
# Request timeout commented out -- the gemini-3.6-flash thinking model can
# take 30-60s to answer, so we wait as long as needed for the full reply.
# GEMINI_TIMEOUT = 20

# Third-party service keys (apply for your own if these are revoked)
WEATHER_API_KEY = "93bfe1ab6970ccb5b0be5ebe2e11be53"


# ---------------------------------------------------------------------
# APP LAUNCHER PATHS / RESERVED NAMES
# ---------------------------------------------------------------------
# Names that map to installed applications rather than websites.
RESERVED_APP_NAMES = {"chrome", "vscode", "vs code", "code", "python",
                      "idle", "notepad", "calculator", "cmd",
                      "command prompt", "code-insiders", "calc", "terminal"}

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
VSCODE_PATHS = [
    r"C:\Program Files\Microsoft VS Code\Code.exe",
    r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
    os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
]

WINDOWS_BUILTINS = {"cmd": "cmd", "notepad": "notepad", "calculator": "calc"}

# Keyword -> canonical app name used by open_application()
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

# ---------------------------------------------------------------------
# RULE-BASED CHAT RESPONSES
# ---------------------------------------------------------------------
CHAT_RULES = {
    "hello": ["Hello! How can I assist you today?", "Hi there! Ready when you are."],
    "hi": ["Hi! How can I help you?", "Hello! What's on your mind?"],
    "good morning": ["Good morning! Wishing you a productive day.", "Morning! Ready to help."],
    "good night": ["Good night! Take care and rest well."],
    "good afternoon": ["Good afternoon! How can I help?"],
    "good evening": ["Good evening! What can I do for you?"],
    "how are you": ["I'm running perfectly and ready to assist you."],
    "who are you": ["I'm JARVIS, your intelligent AI assistant created by Mohammad Wasayullah, Muhammad Azhan Baig, and Muhammad Asad."],
    "what can you do": ["I can open apps/websites, search Wikipedia, play YouTube/Spotify, check weather, "
                        "take screenshots, calculate math, tell jokes, search Google, check system info, "
                        "and chat using AI."],
    "who created you": ["I was created and developed by Mohammad Wasayullah, Muhammad Azhan Baig, and Muhammad Asad."],
    "tell me about your developer": ["My developers, Mohammad Wasayullah, Muhammad Azhan Baig, and Muhammad Asad, are software engineers specializing "
                                     "in AI systems, web development, and automation."],
    "thank you": ["You're welcome!", "Happy to help!"],
    "thanks": ["You're welcome!", "Anytime!"],
    "your name": ["I am JARVIS, your personal AI assistant."],
    "what is your name": ["I am JARVIS."],
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
