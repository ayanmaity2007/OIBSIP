"""Offline tests for chat framing, emoji rendering, hashing, and SQLite."""

import os
import socket
import tempfile
import threading
import unittest

from common import hash_password, receive_json, render_shortcodes, send_json, verify_password
from server import ChatDatabase


class ProtocolTests(unittest.TestCase):
    def test_length_prefixed_json(self):
        left, right = socket.socketpair()
        try:
            payload = {"message": "hello :smile:", "number": 7}
            thread = threading.Thread(target=lambda: send_json(left, payload))
            thread.start()
            self.assertEqual(receive_json(right), payload)
            thread.join()
        finally:
            left.close()
            right.close()

    def test_emoji_and_password_hash(self):
        self.assertIn("😄", render_shortcodes("hello :smile:"))
        credentials = hash_password("correct horse battery staple")
        self.assertTrue(verify_password("correct horse battery staple", credentials["salt"], credentials["digest"]))
        self.assertFalse(verify_password("wrong password", credentials["salt"], credentials["digest"]))


class DatabaseTests(unittest.TestCase):
    def test_register_rooms_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "chat.db")
            database = ChatDatabase(path)
            database.register("Alice_1", "password123")
            self.assertTrue(database.authenticate("Alice_1", "password123"))
            database.create_room("Project Room")
            stamp = database.save_message("Project Room", "Alice_1", "Hello :smile:")
            history = database.history("Project Room")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["timestamp"], stamp)
            self.assertIn("😄", history[0]["message"])
            self.assertIn("Lobby", database.list_rooms())


if __name__ == "__main__":
    unittest.main()
