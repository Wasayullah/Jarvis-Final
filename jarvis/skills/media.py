"""Media skills: YouTube playback, Spotify search, Google search."""

import webbrowser

try:
    import pywhatkit
except ImportError:
    pywhatkit = None


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
