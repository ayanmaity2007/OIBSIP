# Advanced Voice Assistant

Advanced implementation of **Task 1 – Voice Assistant** for the Oasis
Infobyte Python Programming track.

The assistant accepts natural spoken requests through a microphone, responds
with text-to-speech, and falls back to typed commands when microphone or audio
support is unavailable. Integrations are optional and configured through
environment variables so API keys and email passwords are not committed to
GitHub.

## Features

### Beginner requirements included

- Microphone input through `SpeechRecognition`.
- Text-to-speech responses through `pyttsx3`.
- Greeting responses.
- Current time and date.
- Google web search opened in the default browser.
- A repeat prompt when speech is not understood.

### Advanced requirements included

- Free-form intent parsing with phrase scoring, tokenization, and entity
  extraction. For example, “Could you tell me what time it is?” and “Please
  look up renewable energy” are both understood.
- Voice-driven SMTP email composition and sending.
- Non-blocking timed reminders with a terminal bell and spoken alert.
- Live OpenWeatherMap current-weather lookup.
- General-knowledge answers from a local `knowledge.json` file.
- Custom commands loaded from and saved to `commands.json`, including a voice
  command such as `add command open notes that says your notes are ready`.
- Privacy and configuration documentation.

## Installation

Python 3.8 or later is recommended. The program can still start in text mode
without optional packages, but install the dependencies for the full feature
set:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

`PyAudio` may need an operating-system audio package. If microphone setup is
not available, use `--text`; all other features remain demonstrable.

## Configuration

Copy `.env.example` values into your shell environment. Do not commit a real
`.env` file or password.

```bash
# macOS/Linux example
export OPENWEATHER_API_KEY="your_key"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USERNAME="test@example.com"
export SMTP_PASSWORD="app_password"
export SMTP_FROM="test@example.com"
```

For Windows PowerShell, use `$env:NAME = "value"` instead. A free
OpenWeatherMap API key is required for live weather. SMTP must point to a test
account or app-password-enabled account; the assistant refuses to send when
SMTP configuration is incomplete.

## Run

Voice mode:

```bash
python assistant.py
```

Typed demonstration mode (recommended for testing in a terminal):

```bash
python assistant.py --text --no-speech
```

Example commands:

```text
hello
could you tell me what time it is
what is Python
what is the weather in Kolkata
remind me in 10 seconds to check my submission
please search for Python socket programming
send an email to test@example.com subject demo body This is a test message
add command open notes that says your notes are ready
open notes
exit
```

## Privacy and Security

- Speech is sent to the speech-recognition provider used by the installed
  recognizer (the default Google recognizer in this demo) for transcription.
  Use `--text` if audio must not leave the device.
- The OpenWeatherMap request contains the requested city, API key, and the
  machine's IP address as part of normal HTTPS network metadata. No location
  history is stored by this application.
- Email content is sent to the SMTP provider and recipient when the email
  feature is explicitly requested. Credentials are read only from environment
  variables and are never written to the JSON files.
- Custom commands are stored locally in `commands.json`. Knowledge data is
  local in `knowledge.json`.
- Reminders live in memory and disappear when the process exits.
- Use HTTPS services and test accounts. This educational project does not
  provide end-to-end encryption for email or speech transcription.

## Project Structure

```text
Python-Task1-VoiceAssistant-Advanced/
├── assistant.py       # Application, NLU, integrations, and event loop
├── commands.json      # User-editable custom commands
├── knowledge.json     # Offline general-knowledge answers
├── .env.example       # Safe configuration template
├── requirements.txt   # Optional dependencies
└── README.md
```

## Error Handling

Unknown speech, microphone failures, network timeouts, invalid weather keys,
missing SMTP settings, invalid addresses, malformed JSON, and missing local
packages are reported without crashing the assistant. A text mode is available
for computers without a microphone.
