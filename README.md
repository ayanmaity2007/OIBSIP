# Oasis Infobyte – Advanced Python Programming Projects

This repository contains advanced implementations of all five projects listed
in `project.pdf` for the Oasis Infobyte Python Programming track.

## Projects

| Task | Folder | Main advanced features |
| --- | --- | --- |
| 1 | `Python-Task1-VoiceAssistant-Advanced` | Speech input/output, free-form intent parsing, SMTP email, reminders, live weather, local QA, custom commands |
| 2 | `Python-Task2-BMICalculator-Advanced` | Tkinter GUI, multi-user SQLite records, colour feedback, matplotlib trend chart |
| 3 | `Python-Task3-RandomPasswordGenerator-Advanced` | Tkinter GUI, `secrets`, strength indicator, clipboard, ambiguous-character exclusion, five-item session history |
| 4 | `Python-Task4-BasicWeatherApp-Advanced` | Tkinter GUI, current weather, icons, six forecast slots, five-day forecast, units, IP location |
| 5 | `Python-Task5-ChatApplication-Advanced` | Threaded sockets, GUI client, SQLite authentication/history, multiple rooms, notifications, emoji |

The earlier beginner BMI folder may also be present as
`Python-Task2-BMICalculator`; the advanced submission is in the explicitly
named `-Advanced` folder.

## General Setup

Each project is self-contained and has its own `README.md` and
`requirements.txt`. Use a separate virtual environment per project or install
only the dependencies needed by the project:

```bash
cd Python-Task2-BMICalculator-Advanced
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python bmi_app.py
```

Read each project README for API-key setup, operating-system dependencies,
privacy notes, and exact run commands. Never commit real API keys, SMTP
passwords, generated SQLite databases containing private data, or passwords
from screenshots.

## Verification

The projects include offline unit tests that do not require live API keys or a
microphone:

```bash
cd Python-Task1-VoiceAssistant-Advanced && python -m unittest
cd ../Python-Task2-BMICalculator-Advanced && python -m unittest
cd ../Python-Task3-RandomPasswordGenerator-Advanced && python -m unittest
cd ../Python-Task4-BasicWeatherApp-Advanced && python -m unittest
cd ../Python-Task5-ChatApplication-Advanced && python -m unittest
```

## Important Security/Privacy Notes

- Voice assistant speech recognition may send recorded speech to its provider;
  use text mode if that is not acceptable.
- Weather services receive requested locations, and IP-location detection sends
  the public IP to ipinfo.io.
- BMI records and chat history are local SQLite files and are not encrypted by
  default.
- The chat project explicitly does not provide end-to-end encryption or TLS.
- Use test accounts and demo data for an internship submission.
