# Advanced Weather App

Advanced implementation of **Task 4 – Basic Weather App** for the Oasis
Infobyte Python Programming track.

This project is a responsive Tkinter GUI that reads current conditions and
forecasts from OpenWeatherMap. It includes icons, a six-period forecast panel,
a five-day panel, a Celsius/Fahrenheit toggle, and optional approximate
location detection through ipinfo.io.

## Features

### Beginner features included

- City name or ZIP/postal-code input.
- OpenWeatherMap API request and JSON parsing.
- Current temperature in Celsius or Fahrenheit, humidity, condition, and wind.
- GUI error messages for empty input, unknown locations, network timeouts,
  rate limits, and invalid API keys.

### Advanced features included

- Tkinter window with location input, **Get Weather**, and results panel.
- OpenWeatherMap condition icons loaded from icon URLs using Pillow.
- Next six forecast periods from the free 3-hour forecast feed.
- Five-day forecast panel aggregated from forecast data.
- Celsius/Fahrenheit unit switch without another network request.
- **Use My Location** button using ipinfo.io's approximate IP city.
- Background threads keep the GUI responsive while requests are running.
- All user-facing API errors appear inside the GUI rather than terminal print
  statements.

## API Key Setup

Create a free OpenWeatherMap API key, then export it without putting it in
GitHub:

```bash
export OPENWEATHER_API_KEY="your_key_here"      # macOS/Linux
```

Windows PowerShell:

```powershell
$env:OPENWEATHER_API_KEY = "your_key_here"
```

`.env.example` is only a template; this project deliberately does not load or
commit a real `.env` file. The OpenWeatherMap free forecast endpoint provides
three-hour slots, so the “hourly” panel displays the next six available
forecast periods (about the next 18 hours).

## Install

Python 3.8 or later is recommended. Tkinter is included with most Python
installations:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Ubuntu/Debian, install Tkinter if necessary:

```bash
sudo apt install python3-tk
```

## Run

```bash
python weather_app.py
```

1. Enter a city such as `Kolkata` or a supported postal code.
2. Select **Get Weather**.
3. Use **Switch to °F** or **Switch to °C** to change displayed units.
4. Select **Use My Location** for approximate IP-based city detection.

## Error Handling

The GUI handles empty input, missing dependencies, missing API key, invalid
API key, unknown city, API rate limits, timeout, connection failures, malformed
JSON, and missing forecast data. The program does not log API keys or location
history to a file.

## Privacy and Security

- OpenWeatherMap receives the requested location and normal HTTPS request
  metadata. Review its privacy policy before using the service.
- ipinfo.io receives the public IP address when **Use My Location** is pressed.
  This is approximate and optional; the feature can be avoided by entering a
  city manually.
- The app does not store location searches or weather history.
- API keys are read from an environment variable and are never embedded in
  source code.
- Weather data is informational and is not a safety or medical service.

## Project Structure

```text
Python-Task4-BasicWeatherApp-Advanced/
├── weather_app.py   # GUI, API client, forecast aggregation, and icons
├── requirements.txt # requests and Pillow
├── .env.example     # safe API-key template
└── README.md
```
