"""AI engine: rule-based quick replies + Google Gemini online fallback.

The rule-based layer answers common phrases instantly and offline. Anything
not covered falls through to the Gemini API (requires GEMINI_API_KEY env var).
"""

import random
import re
import requests

from config import config
from jarvis import memory


# ---------------------------------------------------------------------
# Rule-based quick replies
# ---------------------------------------------------------------------
def get_rule_response(user_input: str, rules: dict = None):
    """Return a canned reply for a matching phrase.

    Uses whole-phrase matching (word boundaries) so that, e.g., "hi" does
    not accidentally match the word "this" and "war" does not match "who
    are you". Only simple ASCII-phrase rules are eligible.
    """
    rules = rules if rules is not None else config.CHAT_RULES
    for key, options in rules.items():
        if not key.strip():
            continue
        words = key.split()
        # All words of the key must appear as whole words in the input.
        if all(re.search(r"\b" + re.escape(w) + r"\b", user_input) for w in words):
            return random.choice(options)
    return None


# ---------------------------------------------------------------------
# Gemini online brain
# ---------------------------------------------------------------------
SYSTEM_PROMPT_BASE = """
You are an advanced AI assistant created and developed by Mohammad Wasayullah, Muhammad Azhan Baig, and Muhammad Asad.
Your name is "JARVIS". Never mention any underlying model provider.
Be concise, clear, and professional. Think step by step. When giving code,
include comments and best practices.
Always address the user by their own name. Never call the user by a different name.
"""


def build_system_prompt(role: str, username: str = "") -> str:
    prompt = SYSTEM_PROMPT_BASE
    name = username.strip().title() if username and username.strip() else ""
    if role == "creator":
        prompt += (f"\nThe user is your creator, named {name or 'the user'}. "
                   "Be technical and direct, like a co-developer.\n")
    else:
        if name:
            prompt += f"\nThe user's name is {name}. Be polite, simple, and helpful.\n"
        else:
            prompt += "\nThe user is a normal user. Be polite, simple, and helpful.\n"
    return prompt


def is_available() -> bool:
    return bool(config.GEMINI_API_KEY)


def _cached_answer(user_input: str, username: str) -> str:
    """Look up a previously stored Q&A from memory that matches the input,
    so we can answer instantly without hitting the network."""
    try:
        profile = memory.get_user_profile(username)
    except Exception:
        return ""
    q = " ".join(user_input.lower().split())
    for turn in profile.get("history", []):
        stored_q = " ".join(str(turn.get("user", "")).lower().split())
        if stored_q and (stored_q == q or q in stored_q or stored_q in q):
            return str(turn.get("ai", ""))
    return ""


def get_ai_response(user_input: str, username: str) -> str:
    if not config.GEMINI_API_KEY:
        return ("I don't have a Gemini API key configured. Set the GEMINI_API_KEY "
                "environment variable and restart me, or ask a built-in command like "
                "time, date, weather, or wikipedia.")

    cached = _cached_answer(user_input, username)
    try:
        profile = memory.get_user_profile(username)
        history = profile["history"][-config.GEMINI_HISTORY_TURNS:]
        role = profile["role"]
        system_prompt = build_system_prompt(role, username)

        contents = []
        for turn in history:
            contents.append({"role": "user", "parts": [{"text": turn["user"]}]})
            contents.append({"role": "model", "parts": [{"text": turn["ai"]}]})
        contents.append({"role": "user", "parts": [{"text": user_input}]})

        response = requests.post(
            config.GEMINI_URL,
            params={"key": config.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {"maxOutputTokens": config.GEMINI_MAX_OUTPUT_TOKENS},
            },
            # Timeout intentionally commented out -- the gemini-3.6-flash
            # thinking model can take 30-60s. We wait for the full reply.
            # timeout=config.GEMINI_TIMEOUT,
        )

        if response.status_code != 200:
            detail = (response.text or "no details").strip()[:300]
            if response.status_code in (401, 403, 400):
                if cached:
                    return cached + ("\n\n(Note: Gemini rejected the request (HTTP "
                                     f"{response.status_code}), so I answered from "
                                     "our earlier conversation instead.)")
                return ("Gemini couldn't accept my request (HTTP "
                        f"{response.status_code}): {detail} "
                        "Check that GEMINI_API_KEY is a complete, valid key.")
            if response.status_code == 429:
                return "I'm being rate-limited by Gemini right now -- try again in a moment."
            return f"Gemini error (HTTP {response.status_code}): {detail}"

        try:
            data = response.json()
        except ValueError:
            return cached or "Gemini sent back a malformed response. Please try again."

        candidates = data.get("candidates") or []
        if not candidates:
            feedback = data.get("promptFeedback", {})
            reason = feedback.get("blockReason", "no candidates returned")
            return (cached or f"Gemini didn't return a reply ({reason}). Try rephrasing.")

        parts = candidates[0].get("content", {}).get("parts", [])
        ai_reply = "".join(p.get("text", "") for p in parts).strip()
        if not ai_reply:
            return cached or "I don't have a response for that."

        memory.update_memory(username, user_input, ai_reply)
        return ai_reply

    except requests.exceptions.Timeout:
        if cached:
            return cached + ("\n\n(Note: Gemini timed out, so I answered from "
                             "our earlier conversation instead.)")
        return ("I couldn't reach Gemini in time (it took too long). Please "
                "try again in a moment, or ask a built-in command like time, "
                "date, weather, or wikipedia.")
    except requests.exceptions.ConnectionError:
        if cached:
            return cached + ("\n\n(Note: Gemini was unreachable, so I answered "
                             "from our earlier conversation instead.)")
        return "Can't reach Gemini -- check your internet, or ask a built-in command."
    except Exception as e:
        if cached:
            return cached + ("\n\n(Note: I couldn't reach Gemini, so I answered "
                             "from our earlier conversation instead.)")
        return f"Something went wrong: {e}"
