import unittest

from sudoku import SPECS, can_place, count_solutions, is_complete, make_puzzle


class SudokuTests(unittest.TestCase):
    def test_every_supported_size_has_unique_solution(self):
        for size, spec in SPECS.items():
            with self.subTest(size=size):
                puzzle, solution = make_puzzle(size, seed=42)
                self.assertEqual(len(puzzle), size * size)
                self.assertTrue(is_complete(solution, size))
                self.assertEqual(count_solutions(puzzle.copy(), spec), 1)
                self.assertGreater(puzzle.count(0), 0)

    def test_rejects_duplicate_in_row(self):
        puzzle, _ = make_puzzle(4, seed=7)
        puzzle = [0] * 16
        puzzle[0] = 1
        self.assertFalse(can_place(puzzle, 4, 1, 1))
        self.assertTrue(can_place(puzzle, 4, 1, 2))


if __name__ == "__main__":
    unittest.main()

