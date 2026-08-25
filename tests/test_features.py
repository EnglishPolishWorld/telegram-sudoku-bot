import tempfile
import unittest

from storage import Storage
from sudoku import make_cages, make_puzzle


class FeatureTests(unittest.TestCase):
    def test_cages_cover_board_once(self):
        _, solution = make_puzzle(9, seed=2)
        cages = make_cages(9, solution, seed=2)
        cells = [cell for cage in cages for cell in cage["cells"]]
        self.assertEqual(sorted(cells), list(range(81)))
        for cage in cages:
            self.assertEqual(cage["sum"], sum(solution[i] for i in cage["cells"]))

    def test_new_game_defaults_to_five_hearts(self):
        with tempfile.NamedTemporaryFile() as file:
            store = Storage(file.name)
            puzzle, solution = make_puzzle(4, seed=3)
            game = store.create(1, 1, 1, 4, puzzle, solution)
            self.assertEqual(store.get(game.id).hearts, 5)


if __name__ == "__main__":
    unittest.main()
