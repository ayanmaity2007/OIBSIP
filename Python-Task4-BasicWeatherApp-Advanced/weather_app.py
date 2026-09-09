"""Advanced OpenWeatherMap GUI with hourly and daily forecast panels."""

import datetime as dt
import io
import os
import re
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

try:
    import requests
except ImportError:  # pragma: no cover - shown inside the GUI
    requests = None

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - shown inside the GUI
    Image = None
    ImageTk = None


class WeatherError(Exception):
    """User-facing weather integration error."""


class WeatherClient:
    """OpenWeatherMap and optional IP-location API client."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    ICON_URL = "https://openweathermap.org/img/wn/{}@2x.png"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")

    @staticmethod
    def _location_params(location: str) -> Dict[str, str]:
        """Treat a numeric location as a ZIP/postal code, otherwise as a city."""
        if re.match(r"^\d{4,10}(?:,[A-Za-z]{2})?$", location.strip()):
            return {"zip": location.strip()}
        return {"q": location.strip()}

    def _get_json(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a timed API request and translate common errors."""
        if requests is None:
            raise WeatherError("The requests package is not installed.")
        try:
            response = requests.get(endpoint, params=params, timeout=10)
        except requests.Timeout:
            raise WeatherError("The weather request timed out. Please try again.")
        except requests.ConnectionError:
            raise WeatherError("The network is unavailable. Check your connection.")
        except requests.RequestException:
            raise WeatherError("The weather service could not be reached.")

        if response.status_code == 401:
            raise WeatherError("The OpenWeatherMap API key is invalid or missing.")
        if response.status_code == 404:
            raise WeatherError("Location not found. Enter a city name or ZIP/postal code.")
        if response.status_code == 429:
            raise WeatherError("The weather API rate limit was reached. Try again later.")
        try:
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            raise WeatherError("The weather service returned an unreadable response.")
        if str(data.get("cod", "200")) not in ("200", "0"):
            raise WeatherError(data.get("message", "The weather service returned an error."))
        return data

    @staticmethod
    def _local_time(timestamp: int, timezone_offset: int) -> dt.datetime:
        """Convert a UTC epoch value to the location's local time."""
        return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc) + dt.timedelta(seconds=timezone_offset)

    @staticmethod
    def _metric_current(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract stable metric fields from the current-weather response."""
        weather = data["weather"][0]
        return {
            "name": data.get("name", "Unknown location"),
            "description": weather.get("description", "Unknown").title(),
            "icon": weather.get("icon", "01d"),
            "temp_c": float(data["main"]["temp"]),
            "feels_like_c": float(data["main"].get("feels_like", data["main"]["temp"])),
            "humidity": int(data["main"].get("humidity", 0)),
            "wind_mps": float(data.get("wind", {}).get("speed", 0)),
            "timestamp": int(data.get("dt", 0)),
        }

    def fetch(self, location: str) -> Dict[str, Any]:
        """Fetch current conditions and forecast data in metric units."""
        location = location.strip()
        if not location:
            raise WeatherError("Enter a city name or ZIP/postal code first.")
        if not self.api_key:
            raise WeatherError("No API key configured. Set OPENWEATHER_API_KEY and try again.")

        params = dict(self._location_params(location), appid=self.api_key, units="metric")
        current_response = self._get_json(self.BASE_URL + "/weather", params)
        forecast_response = self._get_json(self.BASE_URL + "/forecast", params)
        current = self._metric_current(current_response)
        forecast = self._parse_forecast(forecast_response, current)
        return {"current": current, **forecast}

    def _parse_forecast(self, data: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise 3-hour forecast slots into six hourly cards and five days."""
        timezone_offset = int(data.get("city", {}).get("timezone", 0))
        slots = data.get("list", [])
        if not slots:
            raise WeatherError("The weather service returned no forecast entries.")

        hourly: List[Dict[str, Any]] = []
        groups: Dict[dt.date, List[Dict[str, Any]]] = defaultdict(list)
        for item in slots:
            local = self._local_time(int(item["dt"]), timezone_offset)
            weather = item["weather"][0]
            normalized = {
                "timestamp": int(item["dt"]),
                "local": local,
                "temp_c": float(item["main"]["temp"]),
                "min_c": float(item["main"].get("temp_min", item["main"]["temp"])),
                "max_c": float(item["main"].get("temp_max", item["main"]["temp"])),
                "description": weather.get("description", "Unknown").title(),
                "icon": weather.get("icon", "01d"),
                "humidity": int(item["main"].get("humidity", 0)),
                "wind_mps": float(item.get("wind", {}).get("speed", 0)),
            }
            groups[local.date()].append(normalized)
            if len(hourly) < 6:
                hourly.append(normalized)

        daily: List[Dict[str, Any]] = []
        for date_value in sorted(groups.keys())[:5]:
            entries = groups[date_value]
            representative = min(entries, key=lambda entry: abs(entry["local"].hour - 12))
            daily.append(
                {
                    "date": date_value,
                    "min_c": min(entry["min_c"] for entry in entries),
                    "max_c": max(entry["max_c"] for entry in entries),
                    "description": representative["description"],
                    "icon": representative["icon"],
                }
            )
        return {"hourly": hourly, "daily": daily, "timezone_offset": timezone_offset}

    def locate_by_ip(self) -> str:
        """Return a city from ipinfo.io for the optional auto-location feature."""
        if requests is None:
            raise WeatherError("The requests package is not installed.")
        try:
            response = requests.get("https://ipinfo.io/json", timeout=6)
            if response.status_code != 200:
                raise WeatherError("Automatic location detection failed.")
            city = response.json().get("city")
            if not city:
                raise WeatherError("Your IP provider did not return a city.")
            return str(city)
        except WeatherError:
            raise
        except (requests.Timeout, requests.ConnectionError):
            raise WeatherError("Automatic location detection timed out.")
        except (requests.RequestException, ValueError):
            raise WeatherError("Automatic location detection failed.")


class WeatherApp:
    """Responsive Tkinter weather application."""

    def __init__(self, root: tk.Tk, client: WeatherClient) -> None:
        self.root = root
        self.client = client
        self.root.title("Advanced Weather App")
        self.root.geometry("1120x780")
        self.root.minsize(900, 650)

        self.location_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="C")
        self.status_var = tk.StringVar(value="Enter a city or ZIP/postal code to begin.")
        self.current_location_var = tk.StringVar(value="—")
        self.current_temperature_var = tk.StringVar(value="—")
        self.current_condition_var = tk.StringVar(value="—")
        self.current_details_var = tk.StringVar(value="Humidity: —    Wind: —")
        self.current_icon_label: Optional[tk.Label] = None
        self.data: Optional[Dict[str, Any]] = None
        self.hourly_container: Optional[tk.Frame] = None
        self.daily_container: Optional[tk.Frame] = None
        self._request_in_progress = False

        self._build_widgets()

    def _build_widgets(self) -> None:
        """Create the search bar, current panel, and forecast card panels."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Arial", 20, "bold"))
        style.configure("Section.TLabel", font=("Arial", 13, "bold"))
        style.configure("Search.TButton", font=("Arial", 10, "bold"))

        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)
        outer.rowconfigure(5, weight=1)

        ttk.Label(outer, text="Advanced Weather App", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Live conditions, six forecast periods, five-day outlook, icons, and unit switching",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        search = ttk.Frame(outer)
        search.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        search.columnconfigure(0, weight=1)
        entry = ttk.Entry(search, textvariable=self.location_var, font=("Arial", 12))
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        entry.bind("<Return>", lambda _event: self.get_weather())
        ttk.Button(search, text="Get Weather", style="Search.TButton", command=self.get_weather).grid(
            row=0, column=1, padx=4
        )
        ttk.Button(search, text="Use My Location", command=self.use_my_location).grid(row=0, column=2, padx=4)
        self.unit_button = ttk.Button(search, text="Switch to °F", command=self.toggle_units)
        self.unit_button.grid(row=0, column=3, padx=(4, 0))

        current_frame = tk.LabelFrame(outer, text="Current conditions", font=("Arial", 12, "bold"), padx=14, pady=12)
        current_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 14))
        current_frame.columnconfigure(1, weight=1)
        self.current_icon_label = tk.Label(current_frame, text="☁", font=("Arial", 42), width=5)
        self.current_icon_label.grid(row=0, column=0, rowspan=3, padx=(4, 18))
        tk.Label(
            current_frame,
            textvariable=self.current_location_var,
            font=("Arial", 16, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        tk.Label(
            current_frame,
            textvariable=self.current_temperature_var,
            font=("Arial", 27, "bold"),
            fg="#1d4ed8",
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=3)
        tk.Label(current_frame, textvariable=self.current_condition_var, font=("Arial", 12), anchor="w").grid(
            row=2, column=1, sticky="w"
        )
        tk.Label(current_frame, textvariable=self.current_details_var, font=("Arial", 11), anchor="w").grid(
            row=1, column=2, rowspan=2, sticky="w", padx=35
        )

        hourly_label = ttk.Label(outer, text="Next 6 forecast periods", style="Section.TLabel")
        hourly_label.grid(row=4, column=0, sticky="w", pady=(0, 6))
        self.hourly_container = tk.Frame(outer, bg="#f8fafc")
        self.hourly_container.grid(row=5, column=0, sticky="nsew", pady=(0, 14))
        for column in range(6):
            self.hourly_container.grid_columnconfigure(column, weight=1)

        daily_label = ttk.Label(outer, text="Five-day forecast", style="Section.TLabel")
        daily_label.grid(row=6, column=0, sticky="w", pady=(0, 6))
        self.daily_container = tk.Frame(outer, bg="#f8fafc")
        self.daily_container.grid(row=7, column=0, sticky="ew")
        for column in range(5):
            self.daily_container.grid_columnconfigure(column, weight=1)

        ttk.Label(outer, textvariable=self.status_var, foreground="#475569").grid(
            row=8, column=0, sticky="w", pady=(14, 0)
        )

    def _set_error(self, message: str) -> None:
        """Show errors in the GUI without writing them to the terminal."""
        self.status_var.set("Error: {}".format(message))
        self.current_location_var.set("Weather unavailable")
        self.current_temperature_var.set("—")
        self.current_condition_var.set(message)
        self.current_details_var.set("Try another location or check your API key.")

    def get_weather(self) -> None:
        """Start a background weather request so the GUI remains responsive."""
        if self._request_in_progress:
            self.status_var.set("A weather request is already in progress…")
            return
        location = self.location_var.get().strip()
        if not location:
            self._set_error("Enter a city name or ZIP/postal code.")
            return
        self._request_in_progress = True
        self.status_var.set("Loading weather for {}…".format(location))
        threading.Thread(target=self._fetch_worker, args=(location,), daemon=True).start()

    def _fetch_worker(self, location: str) -> None:
        try:
            data = self.client.fetch(location)
        except WeatherError as error:
            self.root.after(0, lambda: self._finish_error(str(error)))
            return
        self.root.after(0, lambda: self._finish_success(data, location))

    def _finish_error(self, message: str) -> None:
        self._request_in_progress = False
        self._set_error(message)

    def _finish_success(self, data: Dict[str, Any], location: str) -> None:
        self._request_in_progress = False
        self.data = data
        self.location_var.set(location)
        self.render()
        self.status_var.set("Updated weather for {}.".format(data["current"]["name"]))

    def use_my_location(self) -> None:
        """Look up the approximate IP city and then fetch its weather."""
        if self._request_in_progress:
            self.status_var.set("Please wait for the current request to finish.")
            return
        self._request_in_progress = True
        self.status_var.set("Detecting your approximate city…")
        threading.Thread(target=self._location_worker, daemon=True).start()

    def _location_worker(self) -> None:
        try:
            city = self.client.locate_by_ip()
        except WeatherError as error:
            self.root.after(0, lambda: self._finish_error(str(error)))
            return
        self.root.after(0, lambda: self._location_found(city))

    def _location_found(self, city: str) -> None:
        self._request_in_progress = False
        self.location_var.set(city)
        self.get_weather()

    def toggle_units(self) -> None:
        """Switch displayed temperature and wind units without another API call."""
        self.unit_var.set("F" if self.unit_var.get() == "C" else "C")
        self.unit_button.configure(text="Switch to °F" if self.unit_var.get() == "C" else "Switch to °C")
        if self.data:
            self.render()

    def _temperature(self, celsius: float) -> str:
        """Format a Celsius value in the currently selected unit."""
        if self.unit_var.get() == "F":
            return "{:.1f} °F".format(celsius * 9 / 5 + 32)
        return "{:.1f} °C".format(celsius)

    def _wind(self, metres_per_second: float) -> str:
        """Format wind speed in metres/second or miles/hour."""
        if self.unit_var.get() == "F":
            return "{:.1f} mph".format(metres_per_second * 2.236936)
        return "{:.1f} m/s".format(metres_per_second)

    def render(self) -> None:
        """Render current conditions and rebuild both forecast panels."""
        if not self.data:
            return
        current = self.data["current"]
        self.current_location_var.set(current["name"])
        self.current_temperature_var.set(self._temperature(current["temp_c"]))
        self.current_condition_var.set(
            "{}  •  Feels like {}".format(current["description"], self._temperature(current["feels_like_c"]))
        )
        self.current_details_var.set(
            "Humidity: {}%    Wind: {}".format(current["humidity"], self._wind(current["wind_mps"]))
        )
        self._load_icon(current["icon"], self.current_icon_label, 76)
        self._render_hourly()
        self._render_daily()

    def _clear(self, parent: tk.Misc) -> None:
        for child in parent.winfo_children():
            child.destroy()

    def _render_hourly(self) -> None:
        """Render six forecast cards from the OpenWeatherMap 3-hour feed."""
        assert self.hourly_container is not None
        self._clear(self.hourly_container)
        for index, item in enumerate(self.data["hourly"] if self.data else []):
            card = tk.Frame(self.hourly_container, bg="#ffffff", relief="groove", borderwidth=1, padx=6, pady=7)
            card.grid(row=0, column=index, sticky="nsew", padx=3)
            local = item["local"]
            tk.Label(card, text=local.strftime("%a %H:%M"), bg="#ffffff", font=("Arial", 9, "bold")).pack()
            icon = tk.Label(card, text="☁", bg="#ffffff", font=("Arial", 24), width=4)
            icon.pack(pady=2)
            tk.Label(card, text=self._temperature(item["temp_c"]), bg="#ffffff", font=("Arial", 12, "bold")).pack()
            tk.Label(
                card,
                text=item["description"],
                bg="#ffffff",
                wraplength=125,
                font=("Arial", 9),
            ).pack(pady=(3, 0))
            self._load_icon(item["icon"], icon, 52)

    def _render_daily(self) -> None:
        """Render up to five daily forecast cards."""
        assert self.daily_container is not None
        self._clear(self.daily_container)
        for index, item in enumerate(self.data["daily"] if self.data else []):
            card = tk.Frame(self.daily_container, bg="#ffffff", relief="groove", borderwidth=1, padx=8, pady=7)
            card.grid(row=0, column=index, sticky="ew", padx=3)
            date_value = item["date"]
            tk.Label(card, text=date_value.strftime("%a, %b %d"), bg="#ffffff", font=("Arial", 10, "bold")).pack()
            icon = tk.Label(card, text="☁", bg="#ffffff", font=("Arial", 25), width=4)
            icon.pack(pady=2)
            tk.Label(
                card,
                text="{} / {}".format(self._temperature(item["max_c"]), self._temperature(item["min_c"])),
                bg="#ffffff",
                font=("Arial", 10, "bold"),
            ).pack()
            tk.Label(card, text=item["description"], bg="#ffffff", wraplength=140).pack(pady=(3, 0))
            self._load_icon(item["icon"], icon, 54)

    def _load_icon(self, icon_code: str, label: Optional[tk.Label], size: int) -> None:
        """Download an OpenWeatherMap icon in a worker and install it in Tk."""
        if label is None:
            return
        if Image is None or ImageTk is None or requests is None:
            label.configure(text="☁")
            return
        url = WeatherClient.ICON_URL.format(icon_code)

        def worker() -> None:
            try:
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                content = response.content
            except requests.RequestException:
                return
            self.root.after(0, lambda: self._install_icon(label, content, size))

        threading.Thread(target=worker, daemon=True).start()

    def _install_icon(self, label: tk.Label, content: bytes, size: int) -> None:
        """Convert icon bytes to a Tk image while retaining a strong reference."""
        if Image is None or ImageTk is None:
            return
        try:
            image = Image.open(io.BytesIO(content)).convert("RGBA")
            image.thumbnail((size, size))
            photo = ImageTk.PhotoImage(image)
            label.configure(image=photo, text="")
            label.image = photo
        except (OSError, ValueError, tk.TclError):
            # A user may have refreshed the forecast while an old icon was downloading.
            try:
                label.configure(text="☁")
            except tk.TclError:
                pass


def main() -> None:
    """Start the weather GUI."""
    root = tk.Tk()
    WeatherApp(root, WeatherClient())
    root.mainloop()


if __name__ == "__main__":
    main()
