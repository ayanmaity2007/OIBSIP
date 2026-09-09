"""Offline tests for the secure password generator."""

import string
import unittest

from password_app import AMBIGUOUS_CHARACTERS, generate_password, password_strength


class PasswordTests(unittest.TestCase):
    def test_length_and_required_character_types(self):
        selected = ["uppercase", "lowercase", "numbers", "symbols"]
        password = generate_password(24, selected)
        self.assertEqual(len(password), 24)
        self.assertTrue(any(char in string.ascii_uppercase for char in password))
        self.assertTrue(any(char in string.ascii_lowercase for char in password))
        self.assertTrue(any(char in string.digits for char in password))
        self.assertTrue(any(char in "!@#$%^&*()-_=+[]{};:,.?/|~" for char in password))

    def test_ambiguous_characters_are_excluded(self):
        password = generate_password(32, ["uppercase", "lowercase", "numbers"], True)
        self.assertTrue(set(password).isdisjoint(AMBIGUOUS_CHARACTERS))

    def test_rules_are_validated(self):
        with self.assertRaises(ValueError):
            generate_password(7, ["uppercase", "lowercase"])
        with self.assertRaises(ValueError):
            generate_password(12, ["uppercase"])

    def test_strength_labels(self):
        self.assertEqual(password_strength("a" * 12, 2)[0], "Medium")
        self.assertEqual(password_strength("a" * 20, 4)[0], "Strong")


if __name__ == "__main__":
    unittest.main()
