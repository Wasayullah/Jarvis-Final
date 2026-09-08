# JARVIS-549 — Professional Desktop AI Assistant

**Version 3.0.0**

JARVIS-549 is a professional desktop AI assistant wrapped in a futuristic
**holographic HUD** — a borderless, animation-driven interface drawn entirely
in pure Tkinter. It combines a rich local rule-based brain, online skills
(Wikipedia, weather, Google, YouTube, Spotify), system-control utilities,
**voice input & speech output**, persistent user memory, and an optional
**Google Gemini** brain for free-form conversation.

> Built and engineered by **Mohammad Wasayullah**, **Muhammad Azhan Baig**, and **Muhammad Asad**.

---

## Table of Contents

1. [Highlights](#highlights)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Quick Start](#quick-start)
7. [Enable the Gemini AI Brain](#enable-the-gemini-ai-brain)
8. [Configuration](#configuration)
9. [Example Commands](#example-commands)
10. [Voice, Speech & the Ambient Mode](#voice-speech--the-ambient-mode)
11. [Memory & User Profiles](#memory--user-profiles)
12. [Architecture](#architecture)
13. [Developer Tooling](#developer-tooling)
14. [Packaging (PyInstaller)](#packaging-pyinstaller)
15. [Troubleshooting](#troubleshooting)
16. [License & Credits](#license--credits)

---

## Highlights

- 🪟 **Borderless holographic window** — no standard chrome; rounded corners,
  custom glass panels, drag-to-move, a transparent corner color and a real
  Windows taskbar button/icon.
- ⚙️ **Animated gear-core HUD** — a rotating gear train, orbital particles,
  breathing glow and a waveform ring driven by idle / thinking / speaking /
  listening states.
- 💬 **Bubble mission log** — rounded chat bubbles, typewriter AI replies,
  animated “typing” dots, fade-in entrances and a **🔊 read-aloud** button on
  every AI reply.
- 🧠 **Hybrid brain** — instant offline rule-based replies, online skills, and
  a Google Gemini fallback for anything else (with coding-intent detection so
  programming requests always reach the AI).
- 🗣 **Full voice pipeline** — microphone input (Windows `System.Speech`) plus
  background speech output (`pyttsx3` / SAPI5) that never blocks the UI.
- 🌐 **1,400+ websites** with fuzzy matching and a category browser.
- ⚙️ **Ambient gear mode** — a voice-only launcher that is *just* a colourful
  smoky gear on screen: click to open the mic, speak, get spoken answers,
  double-click / `Esc` to quit.

---

## Features

### Interface (Tkinter HUD, no external UI toolkit)

- Single-canvas holographic hub (`1100 × 640`), borderless and not resizable.
- **Light / Dark** theme palettes, switchable at runtime.
- 11 glassy **quick-action** buttons with hover-glow (Time, Date, Screenshot,
  Chrome, VS Code, Terminal, Joke, System Info, Google, Wikipedia, Notepad).
- Status bar with **Voice (`VOICE` pill)**, **TTS `ON/OFF`**, **`| STOP`**
  speech interrupt, and live assistant state.
- Custom window controls (close / minimize pills) bound to the canvas.
- First-run dialog asks the user’s name so the assistant can address them by
  name (persisted via user profile).

### Assistant skills (all local / online, offline-capable built-ins)

- **Time & date** — `what is the time`, `what is the date today`.
- **Wikipedia** — HTTPS REST + MediaWiki APIs (deliberately avoids the
  unmaintained `wikipedia` PyPI package), returns the first two sentences.
- **Weather** — OpenWeatherMap, metric units, feels-like, humidity, wind.
- **Media** — YouTube playback (pywhatkit), Spotify search, Google search.
- **Websites** — fuzzy open of **1,400+** sites, intent-aware shortcuts
  (`open github`, `go to youtube`) plus a `websites` category browser.
- **Local apps** — Chrome, VS Code, Python, Python IDLE, Notepad, Calculator,
  CMD / Command Prompt / Terminal.
- **System utilities** — screenshot, system info, battery, public + local IP,
  shutdown / restart (with cancel), countdown timer, clipboard, safe
  calculator.
- **Chat** — greetings, jokes, compliments, motivation quotes, help text,
  plus rule responses for “who are you” / “what can you do”, etc.

### AI brain

- **Rule-based layer** — instant offline answers with whole-word matching.
- **Gemini online fallback** — free-form conversation, thinking step-by-step,
  configurable model, conversation history (last 6 turns), and cached-answer
  fallback when the API/network fails.
- **Coding-intent detection** — if the message looks like a programming
  request, it is routed straight to the AI (never hijacked by website/app
  shortcuts).
- **Personalized prompts** — the system prompt always uses the **actual user
  name** you entered (creator vs. normal-user tone), and the model is
  instructed to never call you by a different name.
- **Markdown-safe speech** — AI replies are stripped of markdown symbols
  (`**`, `#`, `` ` ``, bullet points, links, etc.) before being spoken.

### Voice pipeline

- **STT** — `sounddevice` captures the mic; the built-in Windows
  `System.Speech` engine (via a PowerShell worker) transcribes spoken text,
  which then runs through the **same** command router as typed input.
- **TTS** — `pyttsx3` SAPI5 on a dedicated background thread; one fresh engine
  per utterance so speech never blocks the UI; toggleable and interruptible.
- **Ambient gear mode** — separate launcher (`python gear_run.py`) for a
  voice-only assistant with no chat UI.

### Persistence

- Per-user profiles stored in `data/memory.json` (bounded 20-turn history).
- Role detection (`creator` vs `user`) tunes the assistant’s tone.
- `.env` loading with zero dependencies; `.env` is git-ignored so keys are
  never committed.

---

## Project Structure

```
J-549-azhan-branch/
├── run.py                        # main GUI launcher (from anywhere)
├── main.py                       # thin compatibility launcher
├── gear_run.py                   # voice-only ambient gear launcher
├── requirements.txt
├── .env.example                  # template for API keys (.env is git-ignored)
├── .gitignore
├── README.md                     # original short readme
├── FinalREADME.md                # this document
│
├── config/
│   ├── __init__.py
│   └── config.py                 # paths, .env loader, theme, keys, app launchers, chat rules
│
├── jarvis/                       # main package
│   ├── __init__.py               # package metadata (v3.0.0, authors)
│   ├── __main__.py               # `python -m jarvis` entry
│   ├── ai_engine.py              # rule-based + Gemini brain, system-prompt builder
│   ├── command.py                # central command router + coding-intent detection
│   ├── memory.py                 # persistent user profiles (memory.json)
│   ├── stt.py                    # microphone input (Windows System.Speech)
│   ├── voice_listener.ps1        # SAPI worker for stt.py
│   ├── tts.py                    # background TTS worker (markdown-safe, wait-for-idle)
│   ├── ambient_gear.py           # voice-only smoky gear (no-UI mode)
│   ├── image.png                 # taskbar / window icon
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── time_date.py          # time, date, greeting
│   │   ├── wikipedia_search.py   # HTTPS Wikipedia summaries
│   │   ├── websites_skill.py     # fuzzy website opening + categories
│   │   ├── media.py              # YouTube, Spotify, Google
│   │   ├── weather.py            # OpenWeatherMap
│   │   ├── system_utils.py       # screenshot, info, battery, IP, timer, shutdown, … 
│   │   └── apps.py               # local app launchers
│   └── ui/
│       ├── __init__.py
│       ├── theme.py              # light/dark palettes + typography
│       ├── widgets.py            # Gear core renderer + ChatPanel bubbles
│       └── app.py                # borderless holographic main window (JarvisApp)
│
├── websites.py                   # 1,400+ website URLs + category dictionary
├── data/                         # runtime data (memory.json created here)
├── screenshots/                  # saved screenshots (git-ignored pngs)
│   ├── jarvis_ui_publish.ps      # Inkscape publishing helper
│   └── jarvis_ui_review.ps       # Inkscape review helper
│
├── archived/                     # original single-file versions (backup)
│   ├── main.py                   # CLI-only original
│   └── gui-gem.py                # earlier single-file GUI
│
├── Jarvis-549.spec               # PyInstaller spec (build Jarvis-549.exe)
├── test_flows.py                 # developer UI/flow checks
├── publish_check.py              # headless launch + screenshot verification helper
├── screenshot.py                 # automated UI screenshot helper
├── animate_check.py              # gear animation sanity checks
├── ps_to_png.py                  # Ghostscript preview -> PNG helper
├── gs_mock.py                    # Ghostscript env probe helper
├── tmp_launch.py                 # timed background launch helper
├── push.bat                      # git push loop helper (dev only)
└── tk_screenshot/
    └── notes.txt                 # Tkinter screenshot experiment notes
```

---

## Requirements

- **Python 3.8+** (Windows recommended — voice & shutdown features are
  Windows-only)
- **Windows** for: voice input (System.Speech), TTS (SAPI5), app launchers,
  shutdown/restart, `winsound` timer beeps.

### Python packages

| Package            | Purpose                                              | Optional? |
| ------------------ | ---------------------------------------------------- | --------- |
| `requests`         | Gemini, Wikipedia, weather, IP                       | required  |
| `pyttsx3`          | offline text-to-speech (SAPI5)                       | recommended |
| `pywhatkit`        | YouTube playback                                     | optional  |
| `PyAutoGUI`        | screenshots                                          | optional  |
| `psutil`           | system info / battery                                | optional  |
| `pyperclip`        | clipboard read                                       | optional  |
| `sounddevice`      | microphone recording for voice input                 | required for voice |
| `SpeechRecognition`| speech-to-text via Google API                        | required for voice |
| `numpy`            | audio data handling                                  | required for voice |

> Optional packages are imported lazily. If a library is missing the assistant
> simply reports that the feature is unavailable rather than crashing.

---

## Installation

```bash
# clone or enter the project directory, then:
pip install -r requirements.txt
```

If you only want the core chat + skills without voice, install at minimum:

```bash
pip install requests pyttsx3 PyAutoGUI psutil pyperclip
```

For the full voice experience on Windows add the audio stack:

```bash
pip install sounddevice SpeechRecognition numpy
```

---

## Quick Start

```bash
# Main holographic GUI (any of these are equivalent)
python run.py
python -m jarvis
python main.py

# Voice-only ambient gear mode
python gear_run.py
```

From the GUI you will be asked what to call you (once), and the assistant will
remember it for future sessions.

---

## Enable the Gemini AI Brain

The built-in commands (time, weather, Wikipedia, websites, apps, jokes, …) work
**without any key**. Only free-form AI conversation needs Gemini.

1. Get a free API key: <https://aistudio.google.com/apikey>
2. Store it in a `.env` file in the project root (there is a `.env.example`
   template; `.env` is git-ignored):

   ```env
   GEMINI_API_KEY=your-key-here
   ```

   Windows: `copy .env.example .env` — then edit the file.
   macOS/Linux: `cp .env.example .env`

3. Restart the assistant. The key is loaded automatically at startup.

> You can also set a real environment variable
> (`$env:GEMINI_API_KEY=...` in PowerShell, or `export GEMINI_API_KEY=...`
> on macOS/Linux), which takes priority over `.env`. The model is configurable
> via `GEMINI_MODEL` (default `gemini-3.5-flash-lite`).

---

## Configuration

Everything central lives in `config/config.py`:

| Setting               | What it controls                                    | How to override                     |
| --------------------- | --------------------------------------------------- | ----------------------------------- |
| `GEMINI_API_KEY`      | Enables the Gemini AI brain                         | `GEMINI_API_KEY` env or `.env`      |
| `GEMINI_MODEL`        | Model used (default `gemini-3.5-flash-lite`)        | `GEMINI_MODEL` env or `.env`        |
| `GEMINI_MAX_OUTPUT_TOKENS`| Max tokens per reply (4096)                     | edit config                         |
| `GEMINI_HISTORY_TURNS`| Conversation turns sent to Gemini (6)              | edit config                         |
| `WEATHER_API_KEY`     | OpenWeatherMap key (public sample is built-in)      | `WEATHER_API_KEY` env or config     |
| `MEMORY_FILE`         | User-profile store (`data/memory.json`)             | edit config                         |
| `SCREENSHOTS_DIR`     | Screenshot output folder (`screenshots/`)           | edit config                         |
| App launcher paths    | Chrome / VS Code executable paths                   | edit `CHROME_PATHS` / `VSCODE_PATHS`|
| `CHAT_RULES`          | Offline rule-based responses & jokes                | edit config                         |

---

## Example Commands

| Command                                   | Action                          |
| ----------------------------------------- | ------------------------------- |
| `hi` / `hello` / `good morning`           | Greetings                       |
| `what is the time` / `time`               | Current time                    |
| `what is the date today` / `date`         | Current date                    |
| `weather in Karachi`                      | Weather for a city              |
| `wikipedia Albert Einstein`               | Wikipedia summary               |
| `open github` / `open youtube`            | Open a website (fuzzy match)    |
| `go to google` / `take me to reddit`      | Explicit site navigation        |
| `open chrome` / `open vscode`             | Launch an installed app         |
| `open notepad` / `open cmd`               | Windows built-ins               |
| `play despacito`                          | Play a video on YouTube         |
| `play spotify imagine dragons`            | Open Spotify search             |
| `google python tutorial` / `search …`     | Google search                   |
| `take screenshot`                         | Save a screenshot               |
| `calculate 5*5-3` / `calc 2+2`            | Evaluate a math expression      |
| `tell me a joke`                          | A joke                          |
| `system info` / `battery` / `my ip`       | System diagnostics              |
| `timer 30` / `cancel timer`               | Countdown timer                 |
| `shutdown` / `restart` / `cancel shutdown`| Power actions (Windows)         |
| `clipboard` / `paste`                     | Read clipboard                  |
| `websites`                                | Show website categories         |
| `write a python function to …`            | Routed to AI as a coding request|
| `bye` / `exit` / `quit`                   | Say goodbye, then quit          |

> Typed commands and spoken (voice) commands are handled by the **same**
> router, so everything listed above also works via the microphone.

---

## Voice, Speech & the Ambient Mode

### Voice input (listen)

- Click the **VOICE** pill (top-right) or the mic button in the input bar.
- The mic must be set as the **default input device** in Windows.
- Speech is transcribed on Windows via the built-in `System.Speech` engine
  (no extra pip packages), then runs through the command router: typed and
  spoken commands behave identically.
- A 4-bar waveform visualizes the listening state.
- If the status bar reports `VOICE UNAVAILABLE`, check the microphone and the
  default input device in **Windows Sound settings**.

### Speech output (talk)

- TTS is toggled from the status-bar **`TTS : ON / OFF`** label.
- `| STOP` interrupts the current utterance without disabling TTS.
- The speaker runs on a **dedicated background thread** (fresh SAPI5 engine per
  utterance) so talking never freezes the UI.
- **Markdown is stripped before speaking** — the assistant will not read `#`,
  `**bold**`, backticks, bullet symbols, etc. aloud.
- On **exit/bye it waits for the goodbye sentence to finish** before closing,
  so goodbyes are never cut off mid-word.

### Ambient gear mode

`python gear_run.py` launches a second, minimal launcher: only a medium
colourful smoky gear on screen.

- **Click** the gear → open/close the microphone.
- **Speak** questions/commands; answers are spoken back (no chat UI).
- **Double-click** the gear or press **`Esc`** → speak “Deactivating.” then quit.
- **Drag** to move the gear anywhere.

---

## Memory & User Profiles

User profiles are stored in `data/memory.json`:

- Created per user (keyed by their lowercased name), with a bounded
  20-turn chat history shared with the app and the Gemini brain.
- `get_user_profile()` assigns a role:
  - `creator` — if the name contains `mohammad` → technical, direct,
    co-developer tone.
  - `user` — otherwise → polite, simple, helpful tone.
- The **system prompt always uses the actual name you enter** (never a
  hardcoded name) and instructs Gemini to address you only by your own name.

> The file is created automatically; it is git-ignored and can be deleted to
> reset all memory / saved conversations.

---

## Architecture

```
UI (Tkinter Canvas HUD)     jarvis/ui/{app,widgets,theme}.py
        │
        ▼
Command Router              jarvis/command.py   (coding-intent detection first)
        │
        ├──▶ Skills          jarvis/skills/*   (time, weather, wiki, media, …)
        ├──▶ Apps            config.APP_KEYWORDS → jarvis/skills/apps.py
        ├──▶ Websites        1,400+ site map → websites_skill fuzzy matcher
        ├──▶ Rule chat       config.CHAT_RULES → jarvis/ai_engine.get_rule_response
        └──▶ Gemini brain    jarvis/ai_engine.get_ai_response (history + prompt)

Voice output                jarvis/tts.Speaker (queue + daemon thread, SAPI5)
Voice input                 jarvis/stt.VoiceInput + voice_listener.ps1
Memory                      jarvis/memory → data/memory.json (profiles/history)
```

### Artificial-intelligence layering

1. `is_coding_request()` — programming intent is sent straight to the AI.
2. `get_rule_response()` — instant offline canned answers (greetings, jokes…).
3. Skill routing — time/date, Wikipedia, weather, media, system, apps, sites.
4. `get_ai_response()` — Gemini fallback for anything else, with:
   - `build_system_prompt(role, username)` — name + role aware system prompt;
   - last-6-turns history;
   - cached-answer fallback on API/network errors (rate-limit, timeout, etc.).

---

## Developer Tooling

The repo bundles several dev/QA helpers (not needed for end users):

| Script             | Purpose                                             |
| ------------------ | --------------------------------------------------- |
| `test_flows.py`    | Headless UI checks (geometry, resizability, title). |
| `publish_check.py` | Headless launch, then screenshot verification.      |
| `screenshot.py`    | Automated screenshot capture of the running UI.     |
| `animate_check.py` | Sanity-checks gear animation rendering.             |
| `ps_to_png.py`     | Converts Inkscape `.ps` previews to PNG.            |
| `gs_mock.py`       | Probes the Ghostscript environment.                 |
| `tmp_launch.py`    | Background-launch helper for scripts.               |
| `screenshots/*.ps` | Inkscape vector preview helpers.                    |
| `push.bat`         | Dev-only git commit/push loop (use with caution).   |

---

## Packaging (PyInstaller)

A PyInstaller spec is included:

```bash
python -m PyInstaller Jarvis-549.spec
```

This builds a `dist/Jarvis-549/` folder with the `Jarvis-549.exe` launcher.
Note: ensure the `.env` / API key needs are handled in the packaged
environment — keys are never baked into source.

---

## Troubleshooting

| Symptom                                   | Fix                                                        |
| ----------------------------------------- | ---------------------------------------------------------- |
| “Voice unavailable” / mic does not work   | Set your microphone as the **default input device** in Windows Sound settings; check the app isn’t muted. |
| TTS silent                                | pyttsx3 SAPI5 needs Windows audio output; toggle **TTS: ON**. The engine is created fresh per utterance on a dedicated thread. |
| Free-form chat says no Gemini key         | Add `GEMINI_API_KEY` to `.env` or environment (see above). |
| Weather/Wikipedia fail                    | They require internet; replace the sample weather key with your own OpenWeatherMap key if it is revoked. |
| “Goodbye” was cut off                     | Fixed — the app now waits for the goodbye sentence to finish speaking before exiting. |
| `shutdown`/`restart` not supported        | Power actions are Windows-only.                             |
| Everything stuck on “Processing…”         | Gemini thinking models can take 30–60 s for hard questions; wait for the reply. |
| Prompt address wrong name                 | The assistant always uses the name from your profile (ask on first run); names/users can be reset by deleting `data/memory.json`. |

---

## License & Credits

**Developers / creators:**

- **Mohammad Wasayullah**
- **Muhammad Azhan Baig**
- **Muhammad Asad**

**Powered by:** Google Gemini (optional), Wikipedia REST & MediaWiki APIs,
OpenWeatherMap, Google Cloud Speech, `pyttsx3` SAPI5, and the Python standard
library + the packages in `requirements.txt`.

This project is provided as-is. Example and sample API keys are included only
for local experimentation; replace them with your own keys before wider
distribution.
