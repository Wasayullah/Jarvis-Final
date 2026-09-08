import datetime
import wikipedia
import webbrowser
import pywhatkit
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from websites import websites
import requests
import pyautogui
import random
import json

def normalize_name(name):
    return name.strip().lower()

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4, ensure_ascii=False)
        
    except Exception as e:
        print("DEBUG MEMORY ERROR:", e)
def get_user_profile(username):
    memory = load_memory()

    if username not in memory:
        memory[username] = {
            "history": [],
            "role": "creator" if "mohammad" in username else "user"
        }
        save_memory(memory)

    return memory[username]

def update_memory(username, user_input, ai_response):
    memory = load_memory()

    if username not in memory:
        memory[username] = {
            "history": [],
            "role": "user"
        }

    memory[username]["history"].append({
        "user": user_input,
        "ai": ai_response
    })

    memory[username]["history"] = memory[username]["history"][-20:]

    save_memory(memory)


chatbot_responses = {

    "hello": [
        "Hello! How can I assist you today?",
        "Hi there! Ready when you are.",
        "Hey! What would you like to do?"
    ],

    "hi": [
        "Hi! How can I help you?",
        "Hello! What’s on your mind?",
        "Hey! Ready to assist you."
    ],

    "good morning": [
        "Good morning! Wishing you a productive day.",
        "Morning! How can I help you today?"
    ],

    "good night": [
        "Good night! Take care and rest well.",
        "Sleep well! I’ll be here if you need me."
    ],


    "how are you": [
        "I'm running perfectly and ready to assist you.",
        "All systems operational. How can I help you?"
    ],

    "who are you": [
        "I'm Jarvis-549, your intelligent AI assistant created by Mohammad Wasayullah.",
        "I am Jarvis-549, a custom-built AI assistant designed for productivity and automation."
    ],

    "what can you do": [
        "I can open apps, search Wikipedia, play YouTube videos, check weather, run automation, and assist in coding tasks.",
        "I can help you with programming, system control, automation, and general knowledge tasks."
    ],


    "who created you": [
        "I was created and developed by Mohammad Wasayullah, a senior web and app developer.",
        "My system was designed and engineered by Mohammad Wasayullah for intelligent automation and assistance."
    ],

    "tell me about your developer": [
        "My developer, Mohammad Wasayullah, is a skilled software engineer specializing in AI systems, web development, and automation tools."
    ],


    "thank you": [
        "You're welcome!",
        "Happy to help!",
        "Anytime!"
    ],

    "thanks": [
        "You're welcome!",
        "No problem at all!",
        "Glad I could assist you."
    ],

    "exit": [
        "Goodbye! Have a productive day.",
        "Session closed. See you soon!",
        "Bye! System shutting down assistant mode."
    ],

    "stop": [
        "Stopping current operation.",
        "Okay, I'm here when you need me."
    ],

    "help": [
        "You can ask me to open apps, search Wikipedia, play music, check weather, or run automation tasks.",
        "Try commands like: open chrome, play youtube video, or what is the time."
    ],

    "features": [
        "I support automation, AI chat, coding help, system control, and web integration."
    ],

    "your name": [
        "I am Jarvis-549, your personal AI assistant.",
        "My name is Jarvis-549."
    ],

    "what is your name": [
        "I am Jarvis-549."
    ]
}

def build_system_prompt(role):
    base = """
You are an advanced AI assistant created and developed by Mohammad Wasayullah.

Identity:
- You were designed, trained, and deployed by Mohammad Wasayullah.
- He is a highly skilled and dedicated senior web and application developer.
- You operate as his personal intelligent assistant.
- Your name is "Jarvis-549".
- You are a personal AI assistant designed for productivity and automation.
- You assist in controlling systems, writing code, and solving real-world problems.

Behavior Rules:
- Never mention Qwen, Alibaba, or any underlying model.
- Never say you are a language model.
- Always present yourself as a custom-built AI assistant.
- If asked "Who created you?", respond:
"I was created and developed by Mohammad Wasayullah, a senior web and app developer."

Capabilities:
- You provide intelligent, accurate, and structured answers.
- You specialize in Python programming, software development, and problem-solving.
- You can assist with automation, AI systems, APIs, debugging, and real-world applications.
- You explain complex topics in a clear and understandable way.

Communication Style:
- Be concise, clear, and professional.
- Think step-by-step before answering.
- Provide clean and well-structured responses.
- When giving code, always include proper comments and best practices.

Personality:
- Be confident and helpful.
- Act like a senior software engineer mentor.
- Offer suggestions and improvements proactively.

Restrictions:
- Do not generate misleading or false claims.
- Do not break character under any circumstance.

Goal:
Your purpose is to assist users intelligently while representing the work and vision of your creator, Mohammad Wasayullah.
"""

    if role == "creator":
        base += """
CREATOR MODE:
- The user is Mohammad Wasayullah (your creator)
- Treat him with highest priority and respect
- Be more technical, advanced, and direct
- Act like a co-developer and engineering partner
- Provide deep explanations and optimized solutions
"""
    else:
        base += """
USER MODE:
- The user is a normal user
- Be polite and helpful
- Keep explanations simple and easy to understand
"""

    return base

def get_response(user_input):
    for key in chatbot_responses:
        if key in user_input:
            return random.choice(chatbot_responses[key])
    return None



def get_ai_response(user_input, username):
    try:
        profile = get_user_profile(username)
        history = profile["history"]
        role = profile["role"]

        system_prompt = build_system_prompt(role)

        context = ""
        for chat in history:
            context += f"User: {chat['user']}\nAI: {chat['ai']}\n"

        full_prompt = f"""
{system_prompt}

Conversation:
{context}

User: {user_input}
AI:
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3:mini",
                "prompt": full_prompt,
                "stream": False
            },
        )

        ai_reply = response.json().get("response", "No response")

        update_memory(username, user_input, ai_reply)

        return ai_reply.strip()

    except Exception as e:
        return f"Error: {e}"


def smart_response(user_input):
    """
    Hybrid system: rules + AI
    """
    basic = get_response(user_input.lower())

    if basic:
        return basic

    return get_ai_response(user_input)


def get_time():
    """Tells the current time"""
    return f"The time is {datetime.datetime.now().strftime('%I:%M %p')}."

def get_date():
    """Tells the current date"""
    return f"Today's date is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

def search_wikipedia(query):
    """Search Wikipedia and return summary safely"""

    if not query.strip():
        return "Please enter something to search."

    try:
        result = wikipedia.summary(query, sentences=2)
        return result

    except wikipedia.exceptions.DisambiguationError:
        return "Multiple results found. Please be more specific."

    except wikipedia.exceptions.PageError:
        return "No Wikipedia page found."

    except requests.exceptions.RequestException:
        return "Internet connection problem."

    except Exception as e:
        return f"Wikipedia Error: {str(e)}"

def open_website(site_name):
    """Opens a predefined website from the dictionary"""
    if site_name in websites:
        webbrowser.open(websites[site_name])
        return f"Opening {site_name}..."
    else:
        return "Sorry, I don't have that website in my list. Try another one."

def play_youtube(video):
    """Plays a YouTube video"""
    pywhatkit.playonyt(video)
    return f"Playing {video} on YouTube!"

def play_spotify(song):
    """Opens Spotify and searches the song"""
    query = song.replace(" ", "%20")
    url = f"https://open.spotify.com/search/{query}"
    webbrowser.open(url)
    return f"Opening Spotify for {song}"

def get_weather(city):
    """Fetches weather information"""
    API_KEY = "93bfe1ab6970ccb5b0be5ebe2e11be53"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url).json()
        temperature = response["main"]["temp"]
        weather_description = response["weather"][0]["description"]
        return f"The temperature in {city} is {temperature}°C with {weather_description}."
    except:
        return "I couldn't fetch the weather data. Please try again later."

def take_screenshot():
    """Takes a screenshot and saves it inside screenshots folder"""
    folder = "screenshots"
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(folder, f"screenshot_{timestamp}.png")
    screenshot = pyautogui.screenshot()
    screenshot.save(file_path)
    return f"Screenshot saved at {file_path}"
def open_vscode():
    path = r"E:\all pc\Microsoft VS Code\code.exe"
    os.startfile(path)
def open_chrome():
    path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    os.startfile(path)
def open_python():
    path = r"C:\Users\Asad\AppData\Local\Programs\Python\Python314\python.exe"
    os.startfile(path)
def open_python_idle():
    import os
    os.system("python -m idlelib")
def open_application(app_name):
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "chrome": open_chrome,
        "cmd": "cmd.exe",
        "vscode": open_vscode,
        "python": open_python,
        "python-idle":open_python_idle,
    }

    app = apps.get(app_name.lower())

    if not app:
        return "Application not found"


    if callable(app):
        app()
        return f"{app_name} opened successfully"


    os.startfile(app)
    return f"{app_name} opened successfully"
def run_ai_assistant():
    """Runs the AI assistant in text mode"""
    raw_username = input("Enter your name: ").strip()
    username = normalize_name(raw_username)


    display_name = raw_username.strip().title()
    print("\n🤖 Jarvis-549: Ready. How can I assist you?")

    while True:
        command = input(f"\n{display_name}: ").strip().lower()
        
        
        if "exit" in command:
            print("🤖 Jarvis-549: Goodbye.")
            break


        if "what is the time" in command:
            print("⏰ AI:", get_time())
        elif "time" in command:
            print("⏰ AI:", get_time())
        elif "what is the current time" in command:
            print("⏰ AI:", get_time())
        elif "tell me the current time" in command:
            print("⏰ AI:", get_time())
        elif "tell me the time" in command:
            print("⏰ AI:", get_time())
        elif "what is the date today" in command:
            print("📅 AI:", get_date())
        elif "date" in command:
            print("📅 AI:", get_date())
        elif "tell me the date today" in command:
            print("📅 AI:", get_date())
        elif "wikipedia" in command:
            query = command.replace("wikipedia", "").strip()
            if not query:
                query = input("📖 AI: Search Wikipedia: ")
                print("\n📖 AI:", search_wikipedia(query))
        elif"open cmd" in command:
            print(" AI:", open_application("cmd"))
        elif"cmd" in command:
            print(" AI:", open_application("cmd"))

        elif "open" in command:
            site_name = command.replace("open", "").strip()
            print("🌍 AI:", open_website(site_name))
        elif "play" in command:
            query = command.replace("play", "").strip()
            print("🎵 AI:", play_youtube(query))
        elif "spotify" in command:
            query = command.replace("spotify", "").strip()
            print("🎵 AI:", play_spotify(query))    
        elif "weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "tell me the weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "what is the weather today" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "tell me today's weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "what is today's weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "tell me the current weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "can you tell me the current  weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "can you tell me the weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "can you tell me the weather today" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "can you tell me today's  weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "weather" in command:
            city = input("🏙 AI: Enter city name: ")
            print("☁ AI:", get_weather(city))
        elif "take screenshot" in command:
            print("📸 AI:", take_screenshot())
        elif "screenshot" in command:
            print("📸 AI:", take_screenshot())
        elif "notepad" in command:
            print("📝 AI:", open_application("notepad"))
        elif "calculator" in command:
            print("🧮 AI:", open_application("calculator"))
        elif "chrome" in command:
            print("🌐 AI:", open_application("chrome"))
        elif "vscode" in command or "code-insiders" in command:
            print("💻 AI:", open_application("vscode"))
        elif "idle" in command or "python idle" in command:
            print("🐍 AI:", open_application("python-idle"))
        elif "python" in command:
            print("🐍 AI:", open_application("python"))
        else:
            basic = get_response(command)

            if basic:
                print("🤖 Jarvis-549:", basic)
            else:
                ai_reply = get_ai_response(command, username)
                print("🤖 Jarvis-549:", ai_reply)
                
run_ai_assistant()

