"""Advanced voice assistant for the Oasis Infobyte Python track.

The assistant has a speech-recognition mode and a text fallback mode.  It uses
small, dependency-light intent parsing instead of requiring a cloud NLP model,
so it can be demonstrated offline.  Optional integrations are enabled by
configuration (OpenWeatherMap and SMTP) and never contain hard-coded secrets.
"""

import argparse
import datetime as dt
import json
import math
import os
import re
import smtplib
import threading
import urllib.parse
import webbrowser
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - handled gracefully at runtime
    requests = None

try:
    import speech_recognition as speech_recognition
except ImportError:  # pragma: no cover - optional in text mode
    speech_recognition = None

try:
    import pyttsx3
except ImportError:  # pragma: no cover - handled gracefully at runtime
    pyttsx3 = None

try:
    from nltk.tokenize import wordpunct_tokenize
except ImportError:  # NLTK is optional; the fallback is enough for this app.
    wordpunct_tokenize = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")
DEFAULT_KNOWLEDGE_FILE = os.path.join(BASE_DIR, "knowledge.json")


class Speaker:
    """Print and, when available, speak every assistant response."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and pyttsx3 is not None
        self._lock = threading.RLock()
        self.engine = None
        if self.enabled:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 170)
            except Exception as error:  # audio drivers differ by operating system
                print("[Audio unavailable: {}]".format(error))
                self.engine = None

    def say(self, message: str) -> None:
        """Display a response and send it to the text-to-speech engine."""
        print("Assistant: {}".format(message))
        if self.engine is None:
            return
        with self._lock:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception as error:
                print("[Text-to-speech error: {}]".format(error))

    def alert(self, message: str) -> None:
        """Play an audible reminder alert and read the reminder aloud."""
        print("\a", end="")
        self.say(message)


class InputProvider:
    """Obtain text using a microphone, or use typed input as a fallback."""

    def __init__(self, voice_mode: bool = True) -> None:
        self.voice_mode = voice_mode and speech_recognition is not None
        self.recognizer = speech_recognition.Recognizer() if self.voice_mode else None
        self._microphone_warning_shown = False

    def listen(self) -> str:
        """Return a recognized sentence or a typed sentence.

        Speech recognition failures do not terminate the program.  A user can
        repeat the command, and microphone setup failures switch to text mode.
        """
        if not self.voice_mode:
            return input("You: ").strip()

        try:
            with speech_recognition.Microphone() as microphone:
                if not self._microphone_warning_shown:
                    self.recognizer.adjust_for_ambient_noise(microphone, duration=0.4)
                    self._microphone_warning_shown = True
                print("Listening...")
                audio = self.recognizer.listen(microphone, timeout=6, phrase_time_limit=12)
            try:
                text = self.recognizer.recognize_google(audio)
                print("You: {}".format(text))
                return text.strip()
            except speech_recognition.UnknownValueError:
                print("I could not understand that audio.")
                return ""
            except speech_recognition.RequestError as error:
                print("Speech service unavailable: {}".format(error))
                return input("Type your command instead: ").strip()
        except (speech_recognition.WaitTimeoutError, speech_recognition.UnknownValueError):
            return ""
        except Exception as error:
            print("[Microphone unavailable: {}]".format(error))
            self.voice_mode = False
            return input("Type your command instead: ").strip()


class IntentParser:
    """Parse free-form sentences into intents and extracted entities.

    The parser scores phrase patterns and token overlap rather than requiring a
    command to match one exact keyword.  Examples such as "could you tell me
    what time it is" and "please look up renewable energy" are both accepted.
    """

    def __init__(self, custom_store: "CustomCommandStore") -> None:
        self.custom_store = custom_store

    @staticmethod
    def _tokens(text: str) -> List[str]:
        if wordpunct_tokenize is not None:
            return [token.lower() for token in wordpunct_tokenize(text) if token.strip()]
        return re.findall(r"[a-z0-9@._'-]+", text.lower())

    @staticmethod
    def _duration(text: str) -> Optional[Tuple[float, str]]:
        match = re.search(
            r"(?:in|after|for)\s+(\d+(?:\.\d+)?)\s*(second|seconds|minute|minutes|hour|hours)",
            text.lower(),
        )
        if not match:
            return None
        number = float(match.group(1))
        unit = match.group(2)
        multiplier = 3600 if unit.startswith("hour") else 60 if unit.startswith("minute") else 1
        return number * multiplier, unit

    def parse(self, text: str) -> Dict[str, Any]:
        """Return an intent dictionary with a confidence score and entities."""
        original = text.strip()
        normalized = re.sub(r"\s+", " ", original.lower())
        tokens = set(self._tokens(normalized))

        custom = self.custom_store.match(normalized)
        if custom is not None:
            return {"name": "custom", "score": 1.0, "text": original, "custom": custom}

        if any(phrase in normalized for phrase in ("goodbye", "good bye", "see you", "shut down", "exit")):
            return {"name": "exit", "score": 0.98, "text": original}

        if "add command" in normalized or "custom command" in normalized or "teach you" in normalized:
            return {"name": "add_command", "score": 0.96, "text": original}

        duration = self._duration(normalized)
        if duration and any(word in tokens for word in ("remind", "reminder", "remember")):
            message = re.sub(
                r"^(.*?)(?:in|after|for)\s+\d+(?:\.\d+)?\s*(?:second|seconds|minute|minutes|hour|hours)\s*",
                "",
                original,
                flags=re.IGNORECASE,
            ).strip(" .")
            message = re.sub(r"^(?:me to|that)\s+", "", message, flags=re.IGNORECASE)
            return {
                "name": "reminder",
                "score": 0.95,
                "text": original,
                "seconds": duration[0],
                "message": message or "Your reminder is due.",
            }

        if any(phrase in normalized for phrase in ("send an email", "send email", "email to", "compose an email")):
            return {"name": "email", "score": 0.94, "text": original}

        if any(word in tokens for word in ("weather", "temperature", "forecast")):
            city_match = re.search(r"\b(?:in|for|at)\s+(.+?)(?:\s+today|\s+right now)?$", original, re.IGNORECASE)
            return {
                "name": "weather",
                "score": 0.91,
                "text": original,
                "city": city_match.group(1).strip(" ?.") if city_match else "",
            }

        if any(phrase in normalized for phrase in ("search for", "look up", "google", "web search", "find information")):
            query = re.sub(
                r"^(?:please\s+)?(?:search for|look up|google|web search|find information about)\s*",
                "",
                original,
                flags=re.IGNORECASE,
            ).strip(" ?.")
            return {"name": "search", "score": 0.90, "text": original, "query": query or original}

        if any(word in tokens for word in ("time", "clock")) and any(
            word in tokens for word in ("what", "tell", "current", "now", "time")
        ):
            return {"name": "time", "score": 0.88, "text": original}

        if any(word in tokens for word in ("date", "day", "today")) and any(
            word in tokens for word in ("what", "tell", "today", "date", "day")
        ):
            return {"name": "date", "score": 0.87, "text": original}

        if any(phrase in normalized for phrase in ("what is", "who is", "tell me about", "how does", "define")):
            question = re.sub(
                r"^(?:please\s+)?(?:what is|who is|tell me about|how does|define)\s*",
                "",
                original,
                flags=re.IGNORECASE,
            ).strip(" ?.")
            return {"name": "knowledge", "score": 0.84, "text": original, "query": question}

        if any(word in tokens for word in ("hello", "hi", "hey", "greetings")):
            return {"name": "greeting", "score": 0.82, "text": original}

        return {"name": "unknown", "score": 0.20, "text": original}


class CustomCommandStore:
    """Load, match, and persist user-defined spoken commands."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.commands: List[Dict[str, str]] = []
        self.load()

    def load(self) -> None:
        """Load commands from JSON, creating a valid empty file if needed."""
        try:
            if not os.path.exists(self.path):
                self._write()
                return
            with open(self.path, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
            self.commands = [
                item for item in data.get("commands", [])
                if item.get("trigger") and item.get("response")
            ]
        except (OSError, ValueError, AttributeError) as error:
            print("[Custom command file could not be loaded: {}]".format(error))
            self.commands = []

    def _write(self) -> None:
        with open(self.path, "w", encoding="utf-8") as file_handle:
            json.dump({"commands": self.commands}, file_handle, indent=2)

    def add(self, trigger: str, response: str) -> None:
        """Add or replace a command and save it to disk."""
        trigger = re.sub(r"\s+", " ", trigger.lower().strip())
        with self._lock:
            self.commands = [item for item in self.commands if item["trigger"] != trigger]
            self.commands.append({"trigger": trigger, "response": response.strip()})
            try:
                self._write()
            except OSError as error:
                print("[Custom command could not be saved: {}]".format(error))

    def match(self, text: str) -> Optional[Dict[str, str]]:
        """Return the longest matching custom command, if one exists."""
        with self._lock:
            matches = [item for item in self.commands if item["trigger"] == text or item["trigger"] in text]
        return max(matches, key=lambda item: len(item["trigger"])) if matches else None


class KnowledgeBase:
    """Answer general questions from a small local JSON knowledge base."""

    def __init__(self, path: str) -> None:
        self.entries: Dict[str, str] = {}
        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                self.entries = json.load(file_handle)
        except (OSError, ValueError) as error:
            print("[Knowledge base unavailable: {}]".format(error))

    def answer(self, query: str) -> Optional[str]:
        """Find an exact or topic-based answer for a question."""
        normalized = query.lower().strip()
        if normalized in self.entries:
            return self.entries[normalized]
        for topic, answer in self.entries.items():
            if topic.lower() in normalized or normalized in topic.lower():
                return answer
        return None


class WeatherService:
    """Read current weather from OpenWeatherMap when an API key is configured."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")

    def current(self, city: str) -> str:
        """Fetch and format current weather for a city."""
        if not city:
            return "Please tell me the city for the weather report."
        if requests is None:
            return "The requests package is not installed, so weather is unavailable."
        if not self.api_key:
            return "Weather is not configured. Set OPENWEATHER_API_KEY in the environment first."
        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": self.api_key, "units": "metric"},
                timeout=8,
            )
            if response.status_code == 401:
                return "The weather API key was rejected. Please check your configuration."
            if response.status_code == 404:
                return "I could not find that city. Please try another location."
            response.raise_for_status()
            data = response.json()
            condition = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind = data.get("wind", {}).get("speed", 0)
            return (
                "In {}, it is {:.1f} degrees Celsius with {}. Humidity is {} percent "
                "and wind speed is {:.1f} metres per second."
            ).format(data.get("name", city), temperature, condition, humidity, wind)
        except (requests.Timeout, requests.ConnectionError):
            return "The weather service timed out. Please try again later."
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            return "I could not read the weather response: {}".format(error)


class EmailService:
    """Send email through SMTP using environment-based configuration."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST")
        try:
            self.port = int(os.getenv("SMTP_PORT", "587"))
        except ValueError:
            self.port = 587
        self.username = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.sender = os.getenv("SMTP_FROM") or self.username

    def send(self, recipient: str, subject: str, body: str) -> str:
        """Send a message, or explain how to configure a safe test account."""
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient):
            return "That recipient email address does not look valid."
        if not all((self.host, self.username, self.password, self.sender)):
            return "Email is not configured; no message was sent. Set the SMTP variables in .env.example."
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject or "Message from Voice Assistant"
        message.set_content(body or "This message was sent by the voice assistant.")
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.send_message(message)
            return "The email was sent successfully."
        except (OSError, smtplib.SMTPException) as error:
            return "I could not send the email: {}".format(error)


class ReminderManager:
    """Schedule reminders without blocking the assistant loop."""

    def __init__(self, speaker: Speaker) -> None:
        self.speaker = speaker
        self._timers: List[threading.Timer] = []
        self._lock = threading.Lock()

    def schedule(self, seconds: float, message: str) -> None:
        """Schedule an audible reminder after a positive number of seconds."""
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("Reminder duration must be greater than zero.")

        def notify() -> None:
            self.speaker.alert("Reminder: {}".format(message))

        timer = threading.Timer(seconds, notify)
        timer.daemon = True
        with self._lock:
            self._timers.append(timer)
        timer.start()


class VoiceAssistant:
    """Coordinate input, NLU, integrations, and spoken responses."""

    def __init__(
        self,
        voice_mode: bool = True,
        speech_enabled: bool = True,
        commands_path: str = DEFAULT_COMMANDS_FILE,
        knowledge_path: str = DEFAULT_KNOWLEDGE_FILE,
    ) -> None:
        self.speaker = Speaker(enabled=speech_enabled)
        self.input_provider = InputProvider(voice_mode=voice_mode)
        self.custom_commands = CustomCommandStore(commands_path)
        self.parser = IntentParser(self.custom_commands)
        self.knowledge = KnowledgeBase(knowledge_path)
        self.weather = WeatherService()
        self.email = EmailService()
        self.reminders = ReminderManager(self.speaker)

    def ask(self, question: str) -> str:
        """Speak a question and collect the next voice or text response."""
        self.speaker.say(question)
        return self.input_provider.listen()

    def handle(self, intent: Dict[str, Any]) -> bool:
        """Execute an intent; return False when the main loop should stop."""
        name = intent["name"]
        if name == "exit":
            self.speaker.say("Goodbye. Have a great day!")
            return False
        if name == "greeting":
            self.speaker.say("Hello! I am ready to help with time, weather, reminders, email, and searches.")
        elif name == "time":
            self.speaker.say("The current time is {}.".format(dt.datetime.now().strftime("%I:%M %p")))
        elif name == "date":
            self.speaker.say("Today is {}.".format(dt.datetime.now().strftime("%A, %B %d, %Y")))
        elif name == "search":
            query = intent.get("query", "").strip()
            if not query:
                query = self.ask("What should I search for?")
            if query:
                webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
                self.speaker.say("I opened a web search for {}.".format(query))
            else:
                self.speaker.say("I did not receive a search topic.")
        elif name == "weather":
            city = intent.get("city", "").strip()
            if not city:
                city = self.ask("Which city should I check?")
            self.speaker.say(self.weather.current(city))
        elif name == "knowledge":
            query = intent.get("query", "").strip()
            answer = self.knowledge.answer(query)
            if answer:
                self.speaker.say(answer)
            else:
                self.speaker.say("I do not have that answer in my local knowledge base. I can search the web if you ask me to.")
        elif name == "reminder":
            try:
                self.reminders.schedule(float(intent["seconds"]), intent["message"])
                self.speaker.say("Reminder set for {}.".format(intent["message"]))
            except (KeyError, ValueError) as error:
                self.speaker.say("I could not set that reminder: {}".format(error))
        elif name == "email":
            self.handle_email(intent.get("text", ""))
        elif name == "add_command":
            self.handle_add_command(intent.get("text", ""))
        elif name == "custom":
            self.speaker.say(intent["custom"]["response"])
        else:
            self.speaker.say("I did not understand that. Try asking for the time, weather, a reminder, an email, or a web search.")
        return True

    def handle_email(self, text: str) -> None:
        """Collect missing email fields conversationally and send the email."""
        recipient_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        recipient = recipient_match.group(0) if recipient_match else self.ask("What email address should receive the message?")
        subject_match = re.search(r"subject\s+(.*?)(?:\s+body\s+|\s+message\s+|$)", text, re.IGNORECASE)
        subject = subject_match.group(1).strip(" .") if subject_match else self.ask("What is the email subject?")
        body_match = re.search(r"(?:body|message|saying)\s+(.+)$", text, re.IGNORECASE)
        body = body_match.group(1).strip(" .") if body_match else self.ask("What should the email say?")
        self.speaker.say(self.email.send(recipient, subject, body))

    def handle_add_command(self, text: str) -> None:
        """Add a command from phrases such as 'add command X that says Y'."""
        match = re.search(
            r"add\s+(?:a\s+)?(?:custom\s+)?command\s+(.+?)\s+(?:that\s+)?(?:says|responds with)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if not match:
            match = re.search(r"when I say\s+(.+?)\s+you say\s+(.+)$", text, re.IGNORECASE)
        if match:
            self.custom_commands.add(match.group(1).strip(" '\"."), match.group(2).strip(" '\"."))
            self.speaker.say("I saved that custom command.")
        else:
            self.speaker.say("Try saying: add command open my notes that says your notes are ready.")

    def run(self) -> None:
        """Run the assistant until the user says goodbye or exits."""
        self.speaker.say("Hello! I am your advanced voice assistant. How can I help?")
        while True:
            try:
                text = self.input_provider.listen()
            except (EOFError, KeyboardInterrupt):
                self.speaker.say("Goodbye.")
                break
            if not text:
                self.speaker.say("I did not understand that. Please repeat your request.")
                continue
            if not self.handle(self.parser.parse(text)):
                break


def main() -> None:
    """Parse command-line options and start the assistant."""
    parser = argparse.ArgumentParser(description="Advanced voice assistant")
    parser.add_argument("--text", action="store_true", help="Use typed commands instead of a microphone")
    parser.add_argument("--no-speech", action="store_true", help="Disable pyttsx3 audio while testing")
    parser.add_argument("--commands", default=DEFAULT_COMMANDS_FILE, help="Path to custom commands JSON")
    parser.add_argument("--knowledge", default=DEFAULT_KNOWLEDGE_FILE, help="Path to local knowledge JSON")
    args = parser.parse_args()
    VoiceAssistant(
        voice_mode=not args.text,
        speech_enabled=not args.no_speech,
        commands_path=args.commands,
        knowledge_path=args.knowledge,
    ).run()


if __name__ == "__main__":
    main()
