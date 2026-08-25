import unittest

from telegram_api import TelegramAPI


class FakeAPI(TelegramAPI):
    def __init__(self):
        self.calls = []

    def call(self, method, payload=None, timeout=45):
        self.calls.append((method, payload))
        return True


class TelegramApiTests(unittest.TestCase):
    def test_inline_result_contains_rich_message(self):
        api = FakeAPI()
        api.answer_inline("query", {"blocks": []})
        method, payload = api.calls[-1]
        self.assertEqual(method, "answerInlineQuery")
        self.assertIn("rich_message", payload["results"][0]["input_message_content"])

    def test_inline_edit_uses_inline_message_id(self):
        api = FakeAPI()
        api.edit_rich(0, 0, {"blocks": []}, "inline-id")
        _, payload = api.calls[-1]
        self.assertEqual(payload["inline_message_id"], "inline-id")
        self.assertNotIn("chat_id", payload)


if __name__ == "__main__":
    unittest.main()
