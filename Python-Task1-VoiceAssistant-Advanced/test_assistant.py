"""Small offline tests for the voice assistant parser and integrations."""

import json
import os
import tempfile
import unittest

from assistant import CustomCommandStore, IntentParser, KnowledgeBase


class AssistantParserTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        commands_path = os.path.join(self.directory.name, "commands.json")
        with open(commands_path, "w", encoding="utf-8") as handle:
            json.dump({"commands": [{"trigger": "open notes", "response": "Notes ready."}]}, handle)
        self.store = CustomCommandStore(commands_path)
        self.parser = IntentParser(self.store)

    def tearDown(self):
        self.directory.cleanup()

    def test_free_form_time(self):
        self.assertEqual(self.parser.parse("Could you tell me what time it is")["name"], "time")

    def test_weather_entity(self):
        intent = self.parser.parse("Please give me the weather in Kolkata")
        self.assertEqual(intent["name"], "weather")
        self.assertEqual(intent["city"], "Kolkata")

    def test_reminder_duration(self):
        intent = self.parser.parse("remind me in 5 minutes to stretch")
        self.assertEqual(intent["name"], "reminder")
        self.assertEqual(intent["seconds"], 300)

    def test_custom_command(self):
        self.assertEqual(self.parser.parse("open notes")["name"], "custom")

    def test_knowledge_base(self):
        path = os.path.join(self.directory.name, "knowledge.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"python": "A programming language."}, handle)
        self.assertEqual(KnowledgeBase(path).answer("What is Python?"), "A programming language.")


if __name__ == "__main__":
    unittest.main()
