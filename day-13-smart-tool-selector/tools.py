"""The 8-tool personal-assistant catalog. All real work, no mocks (see docs/adr/0002).

Four tools read/write local JSON stores under `data/` (email outbox, calendar,
contacts, reminders); three call free, no-auth APIs (Open-Meteo, Frankfurter,
DuckDuckGo). No live SMTP send — `send_email` appends to a local outbox.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

from agents import FunctionTool, function_tool

DATA = Path(__file__).resolve().parent / "data"

SEEDS = {
    "contacts.json": [
        {"name": "Priya Raman", "email": "priya@example.com", "phone": "+1-555-0142"},
        {"name": "Marcus Webb", "email": "marcus@example.com", "phone": "+1-555-0177"},
        {"name": "the team", "email": "team@example.com", "phone": ""},
        {"name": "Dr. Alvarez (dentist)", "email": "front-desk@example.com", "phone": "+1-555-0190"},
    ],
    "calendar.json": [
        {"title": "Sprint planning", "start": "2026-07-23T09:00", "attendees": ["team@example.com"]},
        {"title": "Design review", "start": "2026-07-23T14:00", "attendees": ["marcus@example.com"]},
        {"title": "Roadmap sync", "start": "2026-07-24T11:00", "attendees": ["priya@example.com"]},
    ],
    "outbox.json": [],
    "reminders.json": [],
}


def _load(name: str) -> list[dict]:
    path = DATA / name
    if not path.exists():
        DATA.mkdir(exist_ok=True)
        path.write_text(json.dumps(SEEDS[name], indent=2))
    return json.loads(path.read_text())


def _append(name: str, record: dict) -> None:
    rows = _load(name)
    rows.append(record)
    (DATA / name).write_text(json.dumps(rows, indent=2))


def _get_json(url: str, params: dict) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=20) as resp:
        return json.loads(resp.read())


@function_tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient. Use for notifying people, sharing updates, or messaging a group."""
    _append("outbox.json", {"to": to, "subject": subject, "body": body})
    return f"Email queued to {to}: {subject!r}"


@function_tool
def search_calendar(query: str) -> str:
    """Look up existing calendar events. Use to check what is already scheduled or when someone is busy."""
    hits = [e for e in _load("calendar.json") if query.lower() in json.dumps(e).lower()]
    return json.dumps(hits or _load("calendar.json"))


@function_tool
def create_calendar_event(title: str, start: str, attendees: str = "") -> str:
    """Create a new calendar event. Use to schedule a meeting, block time, or add an appointment."""
    event = {"title": title, "start": start, "attendees": [a for a in attendees.split(",") if a]}
    _append("calendar.json", event)
    return f"Created event {title!r} at {start}"


@function_tool
def search_contacts(query: str) -> str:
    """Look up a person's contact details — email address or phone number — from the address book."""
    hits = [c for c in _load("contacts.json") if query.lower() in json.dumps(c).lower()]
    return json.dumps(hits) if hits else f"No contact matching {query!r}"


@function_tool
def set_reminder(text: str, when: str) -> str:
    """Set a personal reminder or to-do nudge for a given time. Use for 'remind me to ...' requests."""
    _append("reminders.json", {"text": text, "when": when})
    return f"Reminder set: {text!r} at {when}"


@function_tool
def search_web(query: str) -> str:
    """Search the public web for facts, news, or anything not in the user's personal data."""
    from ddgs import DDGS

    results = DDGS().text(query, max_results=3)
    return json.dumps([{"title": r["title"], "body": r["body"]} for r in results])


@function_tool
def get_weather(location: str) -> str:
    """Get the current weather forecast for a city or place."""
    geo = _get_json("https://geocoding-api.open-meteo.com/v1/search", {"name": location, "count": 1})
    if not geo.get("results"):
        return f"Unknown location {location!r}"
    place = geo["results"][0]
    fc = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "forecast_days": 3,
        },
    )
    return json.dumps({"place": place["name"], "current": fc["current"], "daily": fc["daily"]})


@function_tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount of money from one currency to another at the current exchange rate."""
    data = _get_json(
        "https://api.frankfurter.app/latest",
        {"amount": amount, "from": from_currency.upper(), "to": to_currency.upper()},
    )
    return json.dumps(data)


CATALOG: list[FunctionTool] = [
    send_email,
    search_calendar,
    create_calendar_event,
    search_contacts,
    set_reminder,
    search_web,
    get_weather,
    convert_currency,
]

BY_NAME = {t.name: t for t in CATALOG}
