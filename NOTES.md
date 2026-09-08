# JARVIS Notes

## App Architecture

- **Single Canvas architecture**: All UI elements drawn on one Tkinter Canvas (`self.desk`). No multi-page view system. Views are not swapped; instead, navigation buttons open popup dialogs.
- **Window**: `Tk()` with title "JARVIS-549". Geometry constrained; resizing disabled.
- **Theme**: Primary colors are `theme.GLASS` (background), `theme.ACCENT` (cyan, used for active buttons/text), `theme.MUTED` (grayish text), `theme.GLASS_3` (semi-transparent panels). `ACCENT_WARN` has been removed; all active states unified to cyan ACCENT.
- **Voice pipeline**: Top-right toggle button (`tag: voice`) and input-bar button (`tag: voice_input`) control `self.voice_input_enabled`. When active, a `VoiceInput()` STT engine runs in a daemon thread (`_voice_thread`). A 4-bar waveform visualizes listening state.
- **TTS**: Controlled by `tag: ttsbtn` button. `speaker` object has `stop()` method with `_stop` flag and queue clearing. `stop_speaking()` method stops current speech without disabling TTS. `_current_command` tracker enables interrupt/barge-in feature.
- **Quick actions**: 11 buttons at left panel for common commands (open chrome, vscode, etc.).
- **Navigation buttons**: Home/Skills/Memory/Settings buttons at left panel open popup dialogs via `_open_nav_view()`. Full in-canvas view switching not implemented due to single-Canvas architecture.
- **TTS stop button**: "| STOP" button in status bar stops current speech without disabling TTS entirely.

## Methods of Note

- `_build_hub()`: Builds the left panel with quick actions + nav buttons + separator
- `_toggle_voice_input()`: Toggles voice listening state; starts/stops `_voice_thread`
- `_ui_call(fn)`: Schedules `fn` to run on main thread via `root.after(0, fn)`
- `_open_nav_view(view_idx)`: Opens a popup dialog for the requested view (0=Home, 1=Skills, 2=Memory, 3=Settings)
- `_open_popup(title, text)`: Helper to create a popup Toplevel dialog
- `_voice_worker()`: Background thread loop that checks `voice_input_enabled` and `_thinking`/`_speaking_now` flags
- `_stop_tts_speaking()`: Stops current TTS speech without disabling TTS entirely
- `speaker.stop_speaking()`: Sets `_stop_speaking=True` and clears queue
- `speaker.stop()`: Sets `_stop=True` and clears audio queue for clean TTS shutdown
- `_stop_current()`: Sets `_thinking=False` and clears `_current_command`
- `_command_counter`: Increments with each command; old responses are ignored when counter doesn't match

## Known Issues

- **Close button**: Fades window via `after()` animation but does NOT terminate the Python process. Process remains in Task Manager.
- **No multi-page view**: Single Canvas means no true page navigation; nav buttons open info popups instead.
- **TTS literal audio**: Button toggles state but has not been verified by playing actual audio output.
- **Voice STT**: Availability depends on microphone and Windows audio configuration; may report "VOICE ENGINE UNAVAILABLE".
- **Input/mic spacing**: Entry field repositioned right of capsule button with 8px gap; no longer collapses with mic button.

## Files Modified Since Init

- `jarvis/ui/app.py`: Nav buttons, `_open_nav_view()`, `_open_popup()`, TTS stop method, _current_command, waveform, interrupt feature (command counter), input field width fix, TTS stop button in status bar
- `jarvis/tts.py`: `stop()` method with `_stop` flag and queue clearing; `stop_speaking()` method for current speech only
- `jarvis/stt.py`: Fixed "READY" line consumption in `_spawn()`
- `jarvis/ui/widgets.py`: Gear COLORS unified to `theme.ACCENT` for all states (hover/press/idle)
- `PROGRESS.md`: Rewritten with accurate current status (no fake "14/14 PASS")
- `NOTES.md`: Rewritten from scratch with accurate current status