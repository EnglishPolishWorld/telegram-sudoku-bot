import unittest

from rich_ui import creator_view, game_view, size_picker
from storage import Game


class RichUiTests(unittest.TestCase):
    def test_size_picker_has_three_sizes(self):
        picker = size_picker()
        callbacks = [button["callback_data"] for button in picker["blocks"][1]["buttons"]]
        self.assertEqual(callbacks, ["new:classic:normal:4", "new:classic:normal:6", "new:classic:normal:9"])

    def test_board_is_square_and_callbacks_are_short(self):
        game = Game("abc123", 1, 1, 1, 9, [0] * 81, [0] * 81, [1] * 81, None, False)
        view = game_view(game)
        table = next(block for block in view["blocks"] if block["type"] == "table")
        self.assertEqual(len(table["cells"]), 9)
        self.assertTrue(all(len(row) == 9 for row in table["cells"]))
        for row in table["cells"]:
            for cell in row:
                data = cell["text"]["button"]["callback_data"]
                self.assertLessEqual(len(data.encode()), 64)

    def test_creator_has_start_button(self):
        view = creator_view()
        self.assertEqual(view["blocks"][-1]["buttons"][0]["callback_data"], "menu:0")
        self.assertIn("@etetnall_dog", view["blocks"][1]["text"])


if __name__ == "__main__":
    unittest.main()
