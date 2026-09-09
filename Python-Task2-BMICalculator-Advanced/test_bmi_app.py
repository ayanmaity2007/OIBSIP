"""Headless tests for the advanced BMI calculator's calculation and database."""

import os
import tempfile
import unittest

from bmi_app import BMIRepository, calculate_bmi, classify_bmi


class BMICalculationTests(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(calculate_bmi(70, 1.75), 22.86)
        self.assertEqual(classify_bmi(22.86)[0], "Normal weight")
        self.assertEqual(classify_bmi(17.0)[0], "Underweight")
        self.assertEqual(classify_bmi(27.0)[0], "Overweight")
        self.assertEqual(classify_bmi(31.0)[0], "Obese")

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            calculate_bmi(0, 1.75)
        with self.assertRaises(ValueError):
            calculate_bmi(70, -1.75)
        with self.assertRaises(ValueError):
            calculate_bmi(float("nan"), 1.75)


class RepositoryTests(unittest.TestCase):
    def test_multi_user_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "records.db")
            repository = BMIRepository(path)
            repository.add_record("Alice", 70, 1.75, 22.86, "Normal weight")
            repository.add_record("Bob", 100, 1.65, 36.73, "Obese")
            self.assertEqual(repository.list_users(), ["Alice", "Bob"])
            self.assertEqual(len(repository.history("Alice")), 1)
            self.assertEqual(repository.history("Bob")[0]["category"], "Obese")
            repository.close()


if __name__ == "__main__":
    unittest.main()
