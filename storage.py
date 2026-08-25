from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass


def _pack(values: list[int]) -> str:
    return ",".join(map(str, values))


def _unpack(values: str) -> list[int]:
    return [int(value) for value in values.split(",")]


@dataclass
class Game:
    id: str
    owner_id: int
    chat_id: int
    message_id: int
    size: int
    puzzle: list[int]
    board: list[int]
    solution: list[int]
    selected: int | None
    finished: bool


class Storage:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                size INTEGER NOT NULL,
                puzzle TEXT NOT NULL,
                board TEXT NOT NULL,
                solution TEXT NOT NULL,
                selected INTEGER,
                finished INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.commit()

    def create(
        self,
        owner_id: int,
        chat_id: int,
        message_id: int,
        size: int,
        puzzle: list[int],
        solution: list[int],
    ) -> Game:
        game = Game(uuid.uuid4().hex[:10], owner_id, chat_id, message_id, size, puzzle, puzzle.copy(), solution, None, False)
        self.db.execute(
            "INSERT INTO games (id, owner_id, chat_id, message_id, size, puzzle, board, solution) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (game.id, owner_id, chat_id, message_id, size, _pack(puzzle), _pack(puzzle), _pack(solution)),
        )
        self.db.commit()
        return game

    def get(self, game_id: str) -> Game | None:
        row = self.db.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if row is None:
            return None
        return Game(
            row["id"], row["owner_id"], row["chat_id"], row["message_id"], row["size"],
            _unpack(row["puzzle"]), _unpack(row["board"]), _unpack(row["solution"]),
            row["selected"], bool(row["finished"]),
        )

    def save(self, game: Game) -> None:
        self.db.execute(
            "UPDATE games SET board = ?, selected = ?, finished = ? WHERE id = ?",
            (_pack(game.board), game.selected, int(game.finished), game.id),
        )
        self.db.commit()

