"""Weather forecast via OpenWeatherMap."""

import requests

from config import config


def get_weather(city: str) -> str:
    if not city.strip():
        return "Please tell me which city."
    url = (f"http://api.openweathermap.org/data/2.5/weather"
           f"?q={city}&appid={config.WEATHER_API_KEY}&units=metric")
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
