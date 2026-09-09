"""Offline tests for forecast parsing and unit helpers."""

import unittest

from weather_app import WeatherClient


class WeatherParsingTests(unittest.TestCase):
    def test_forecast_is_grouped_into_hourly_and_daily_data(self):
        slots = []
        base = 1_700_000_000
        for index in range(10):
            slots.append(
                {
                    "dt": base + index * 3 * 3600,
                    "main": {
                        "temp": 20 + index,
                        "temp_min": 18 + index,
                        "temp_max": 22 + index,
                        "humidity": 60,
                    },
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 2.0},
                }
            )
        parsed = WeatherClient()._parse_forecast(
            {"city": {"timezone": 0}, "list": slots},
            {"timestamp": base},
        )
        self.assertEqual(len(parsed["hourly"]), 6)
        self.assertLessEqual(len(parsed["daily"]), 5)
        self.assertGreaterEqual(len(parsed["daily"]), 1)
        self.assertEqual(parsed["hourly"][0]["description"], "Clear Sky")

    def test_zip_location_is_detected(self):
        self.assertEqual(WeatherClient._location_params("700001"), {"zip": "700001"})
        self.assertEqual(WeatherClient._location_params("Kolkata"), {"q": "Kolkata"})


if __name__ == "__main__":
    unittest.main()
