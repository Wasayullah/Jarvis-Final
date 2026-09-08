"""Central command router: parses raw user input and dispatches to skills."""

import re

import webbrowser
from websites import websites

from config import config
from jarvis import ai_engine
from jarvis.skills import (
    apps, media, system_utils, time_date, weather, websites_skill, wikipedia_search,
)

# Re-export popular website categories for the UI
WEBSITE_CATEGORIES = websites_skill.categories()


def _fuzzy_ok(query: str, site: str) -> bool:
    """Return True only if `site` is a strong, unambiguous match for the
    bare command `query`. Guards against opening a random site because a
    short fragment (e.g. 'ea') happens to appear inside a word."""
    url, matched = websites_skill._fuzzy_find_site(query)  # noqa: SLF001
    if url is None:
        return False
    if isinstance(matched, list):
        return False
    # Require the matched site to actually be this site and reasonably close.
    if matched != site:
        return False
    return site in query or _is_close(query, site)


def _is_close(a: str, b: str) -> bool:
    """Cheap similarity check for short site names (exact / substring /
    small edit distance)."""
    if a == b:
        return True
    if a in b or b in a:
        return True
    if abs(len(a) - len(b)) > 3:
        return False
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.7


# Phrases/patterns that indicate the user wants coding / programming help.
# When these appear, we route straight to the AI rather than letting
# website/app/command shortcuts hijack the message (e.g. "write a python
# program" must not open the Python app, "fix this javascript code" must
# not open a site matching "this" -> the veil etc.).
CODING_INDICATORS = [
    r"write\s+(a|the|some|me)?\s*(py|python|code|script|program|function|class|app|application|api)",
    r"code\s*(for|to|that|in|with|using)",
    r"(?:fix|debug|solve|explain|review|improve)\s+(?:this|the|my)?\s*(?:code|bug|error|script|program|function)",
    r"\b(python|javascript|typescript|java|c\+\+|go|rust|react|next\.?js|vue|angular|django|flask|fastapi|node(?:\.js)?|express|dart|swift|kotlin|ruby|php|html|css|sql|bash|powershell)\b",
    r"how (?:do|to|can|would) i (?:write|code|build|create|make|implement|fix|debug|install)",
    r"(?:tell me|show me|give me).*(?:code|snippet|example|program)",
    r"(?:error|exception|traceback|stack ?trace|debug)",
    r"\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(|\bconst\s+\w+\s*=|^[a-zA-Z_]+\(.*\)\s*[:{=]",
]
CODING_RE = re.compile("|".join(CODING_INDICATORS))


def is_coding_request(cmd: str) -> bool:
    # Explicit navigation commands are never "coding requests" -- they must
    # still open the app/site. (e.g. "open python", "play x", "go to y").
    if re.match(r"^(open|play|launch|run|start|go to|take me to|open up|visit|navigate to|search)\b", cmd):
        return False
    return bool(CODING_RE.search(cmd))


def process_command(raw_command: str, username: str) -> str:
    cmd = raw_command.lower().strip()

    if not cmd:
        return "I didn't catch that."

    # --- coding / programming intent: bypass shortcuts, go to AI ---
    # Do this early so website/app/command matching never hijacks a coding
    # request. Rule-based greetings still get a quick answer first.
    if is_coding_request(cmd):
        basic = ai_engine.get_rule_response(cmd)
        if basic:
            return basic
        return ai_engine.get_ai_response(raw_command, username)

    # --- time / date ---
    if ("what" in cmd and "time" in cmd) or cmd == "time":
        return time_date.get_time()
    if ("what" in cmd and "date" in cmd) or cmd == "date":
        return time_date.get_date()

    # --- wikipedia ---
    if "wikipedia" in cmd:
        query = re.sub(r"wikipedia", "", raw_command, flags=re.IGNORECASE).strip()
        return wikipedia_search.search_wikipedia(query)

    # --- spotify ---
    if "spotify" in cmd:
        query = raw_command.lower().replace("spotify", "").replace("play", "").strip()
        return media.play_spotify(query)

    # --- youtube ---
    if "play" in cmd and ("youtube" in cmd or "video" in cmd):
        query = (raw_command.lower()
                 .replace("play", "").replace("on youtube", "")
                 .replace("youtube", "").replace("video", "").strip())
        return media.play_youtube(query)
    if "play" in cmd:
        query = (raw_command.lower()
                 .replace("play", "").replace("on youtube", "")
                 .replace("youtube", "").strip())
        return media.play_youtube(query)

    # --- weather ---
    if "weather" in cmd:
        if " in " in cmd:
            city = cmd.split(" in ", 1)[1].strip()
        else:
            city = (cmd.replace("weather", "")
                    .replace("what's the", "").replace("what is the", "").strip())
        if not city:
            return "Please specify a city, e.g. 'weather in Karachi'."
        return weather.get_weather(city)

    # --- screenshot ---
    if "screenshot" in cmd:
        return system_utils.take_screenshot()

    # --- calculator ---
    if cmd.startswith(("calc ", "calculate ", "evaluate ")):
        expr = re.sub(r"^(calc|calculate|evaluate)\s+", "", cmd, flags=re.IGNORECASE)
        return system_utils.calculate(expr)

    # --- timer ---
    if "timer" in cmd:
        if "cancel" in cmd:
            return system_utils.cancel_timer()
        nums = re.findall(r"\d+", cmd)
        if nums:
            return system_utils.set_timer(int(nums[0]))
        return "Say 'timer 30' to set a 30-second timer, or 'cancel timer'."

    # --- joke ---
    if "joke" in cmd:
        return ai_engine.get_rule_response("joke")

    # --- google search ---
    if cmd.startswith(("google ", "search ")):
        query = re.sub(r"^(google|search)\s+", "", raw_command, flags=re.IGNORECASE).strip()
        return media.search_google(query)

    # --- system info ---
    if "system info" in cmd or "systeminfo" in cmd or "my pc" in cmd:
        return system_utils.get_system_info()

    # --- battery ---
    if "battery" in cmd:
        return system_utils.get_battery_info()

    # --- ip address ---
    if "ip address" in cmd or "my ip" in cmd or "what's my ip" in cmd:
        return system_utils.get_ip_address()

    # --- shutdown / restart ---
    if "shutdown" in cmd or "shut down" in cmd:
        if "cancel" in cmd:
            return system_utils.cancel_shutdown()
        return system_utils.shutdown_pc()
    if "restart" in cmd or "reboot" in cmd:
        return system_utils.restart_pc()

    # --- clipboard ---
    if "clipboard" in cmd or "paste" in cmd:
        return system_utils.get_clipboard()

    # --- open <app> FIRST (before website matching to avoid conflicts) ---
    for keyword, app in config.APP_KEYWORDS.items():
        if keyword in cmd:
            result = apps.open_application(app)
            if result and "isn't a known" not in result:
                return result

    # --- open <website> (fuzzy match, AFTER apps) ---
    if cmd.startswith("open "):
        target = cmd[5:].strip()
        result = websites_skill.open_website(target)
        if result:
            return result
        url, matched = websites_skill._fuzzy_find_site(target)  # noqa: SLF001
        suggestions = matched if isinstance(matched, list) else []
        if suggestions:
            return f"I don't have '{target}'. Did you mean: {', '.join(suggestions[:4])}?"
        return f"I don't have '{target}'. Type 'websites' to browse categories."

    # --- website shortcuts (intent-aware, no "open" prefix needed) ---
    # Only open a site when the user clearly wants to go there. We must NOT
    # open something just because a site name appears inside a normal
    # sentence/question (e.g. "what is next.js" -> nextjs, or "who created
    # you" -> ea). So we restrict this to:
    #   1) bare site-name messages ("youtube", "github"), or
    #   2) explicit navigation phrases ("go to X", "take me to X", ...).
    _nav_phrase = re.match(
        r"^(?:go to|take me to|open up|launch|visit|navigate to|search on)\s+(.+)$",
        cmd,
    )
    if _nav_phrase:
        target = _nav_phrase.group(1).strip()
        result = websites_skill.open_website(target)
        if result:
            return result

    # Bare site name (single concept, no extra words that indicate chat).
    _words = cmd.split()
    if len(_words) <= 2 and not any(q in cmd for q in ("what", "who", "how", "why", "when", "which", "?")):
        for site in websites:
            if site in cmd and site not in config.RESERVED_APP_NAMES and _fuzzy_ok(cmd, site):
                webbrowser.open(websites[site])
                return f"Opening {site}..."

    # --- browse website categories ---
    if "websites" in cmd or "browse sites" in cmd or "website list" in cmd:
        return (f"Available categories:\n{websites_skill.categories_text()}\n\n"
                f"Type 'open <name>' to open any site.")

    # --- rule-based chat ---
    basic = ai_engine.get_rule_response(cmd)
    if basic:
        return basic

    # --- AI fallback ---
    return ai_engine.get_ai_response(raw_command, username)
