from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class SudokuSpec:
    size: int
    box_rows: int
    box_cols: int
    clues: int


SPECS = {
    4: SudokuSpec(4, 2, 2, 8),
    6: SudokuSpec(6, 2, 3, 18),
    9: SudokuSpec(9, 3, 3, 36),
}


def _shuffled(values: range | list[int], rng: random.Random) -> list[int]:
    result = list(values)
    rng.shuffle(result)
    return result


def make_solution(spec: SudokuSpec, rng: random.Random) -> list[int]:
    def pattern(row: int, col: int) -> int:
        return (spec.box_cols * (row % spec.box_rows) + row // spec.box_rows + col) % spec.size

    rows = [
        band * spec.box_rows + row
        for band in _shuffled(range(spec.box_cols), rng)
        for row in _shuffled(range(spec.box_rows), rng)
    ]
    cols = [
        stack * spec.box_cols + col
        for stack in _shuffled(range(spec.box_rows), rng)
        for col in _shuffled(range(spec.box_cols), rng)
    ]
    numbers = _shuffled(range(1, spec.size + 1), rng)
    return [numbers[pattern(row, col)] for row in rows for col in cols]


def candidates(board: list[int], spec: SudokuSpec, index: int) -> set[int]:
    row, col = divmod(index, spec.size)
    used = set(board[row * spec.size : (row + 1) * spec.size])
    used.update(board[col :: spec.size])
    box_row = (row // spec.box_rows) * spec.box_rows
    box_col = (col // spec.box_cols) * spec.box_cols
    for r in range(box_row, box_row + spec.box_rows):
        for c in range(box_col, box_col + spec.box_cols):
            used.add(board[r * spec.size + c])
    return set(range(1, spec.size + 1)) - used


def count_solutions(board: list[int], spec: SudokuSpec, limit: int = 2) -> int:
    empty = [i for i, value in enumerate(board) if value == 0]
    if not empty:
        return 1
    index = min(empty, key=lambda i: len(candidates(board, spec, i)))
    options = candidates(board, spec, index)
    if not options:
        return 0
    total = 0
    for value in options:
        board[index] = value
        total += count_solutions(board, spec, limit)
        board[index] = 0
        if total >= limit:
            return total
    return total


def make_puzzle(size: int, seed: int | None = None) -> tuple[list[int], list[int]]:
    spec = SPECS[size]
    rng = random.Random(seed)
    solution = make_solution(spec, rng)
    puzzle = solution.copy()
    positions = list(range(size * size))
    rng.shuffle(positions)

    for index in positions:
        if sum(value != 0 for value in puzzle) <= spec.clues:
            break
        previous = puzzle[index]
        puzzle[index] = 0
        if count_solutions(puzzle.copy(), spec) != 1:
            puzzle[index] = previous
    return puzzle, solution


def can_place(board: list[int], size: int, index: int, value: int) -> bool:
    if value == 0:
        return True
    spec = SPECS[size]
    copy = board.copy()
    copy[index] = 0
    return value in candidates(copy, spec, index)


def is_complete(board: list[int], size: int) -> bool:
    spec = SPECS[size]
    expected = set(range(1, size + 1))
    if any(value == 0 for value in board):
        return False
    for row in range(size):
        if set(board[row * size : (row + 1) * size]) != expected:
            return False
    for col in range(size):
        if set(board[col :: size]) != expected:
            return False
    for box_row in range(0, size, spec.box_rows):
        for box_col in range(0, size, spec.box_cols):
            values = {
                board[row * size + col]
                for row in range(box_row, box_row + spec.box_rows)
                for col in range(box_col, box_col + spec.box_cols)
            }
            if values != expected:
                return False
    return True

