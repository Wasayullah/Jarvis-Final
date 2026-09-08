"""Time and date skills."""

import datetime


def get_time() -> str:
    return f"The time is {datetime.datetime.now().strftime('%I:%M %p')}."


def get_date() -> str:
    return f"Today's date is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."


def get_greeting() -> str:
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"
