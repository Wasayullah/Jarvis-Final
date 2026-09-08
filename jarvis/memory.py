"""Memory / user-profile persistence backed by a JSON store.

Each user gets a profile keyed by their lowercased name, containing a
bounded chat history and a role ("creator" vs "user") that tunes the
assistant's tone.
"""

import json
import os

from config import config


def normalize_name(name: str) -> str:
    return name.strip().lower()


def load_memory() -> dict:
    if os.path.exists(config.MEMORY_FILE):
        try:
            with open(config.MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_memory(memory: dict):
    try:
        with open(config.MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("MEMORY SAVE ERROR:", e)


def get_user_profile(username: str) -> dict:
    memory = load_memory()
    if username not in memory:
        memory[username] = {
            "history": [],
            "role": "creator" if "mohammad" in username else "user",
        }
        save_memory(memory)
    return memory[username]


def update_memory(username: str, user_input: str, ai_response: str):
    memory = load_memory()
    if username not in memory:
        memory[username] = {"history": [], "role": "user"}
    memory[username]["history"].append({"user": user_input, "ai": ai_response})
    memory[username]["history"] = memory[username]["history"][-20:]
    save_memory(memory)
