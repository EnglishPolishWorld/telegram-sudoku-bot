from __future__ import annotations

import sqlite3
import uuid
import json
import time
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
    mode: str = "classic"
    difficulty: str = "normal"
    hearts: int = 5
    mistakes: int = 0
    hints: int = 3
    started_at: int = 0
    history: list[tuple[int, int]] | None = None
    cages: list[dict] | None = None
    daily: bool = False


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
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(games)")}
        additions = {
            "mode": "TEXT NOT NULL DEFAULT 'classic'", "difficulty": "TEXT NOT NULL DEFAULT 'normal'",
            "hearts": "INTEGER NOT NULL DEFAULT 5", "mistakes": "INTEGER NOT NULL DEFAULT 0",
            "hints": "INTEGER NOT NULL DEFAULT 3", "started_at": "INTEGER NOT NULL DEFAULT 0",
            "history": "TEXT NOT NULL DEFAULT '[]'", "cages": "TEXT NOT NULL DEFAULT '[]'",
            "daily": "INTEGER NOT NULL DEFAULT 0"
        }
        for name, definition in additions.items():
            if name not in columns:
                self.db.execute(f"ALTER TABLE games ADD COLUMN {name} {definition}")
        self.db.execute("CREATE TABLE IF NOT EXISTS stats (user_id INTEGER PRIMARY KEY, wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0, best_time INTEGER)")
        self.db.commit()

    def create(
        self,
        owner_id: int,
        chat_id: int,
        message_id: int,
        size: int,
        puzzle: list[int],
        solution: list[int], mode: str = "classic", difficulty: str = "normal",
        cages: list[dict] | None = None, daily: bool = False,
    ) -> Game:
        game = Game(uuid.uuid4().hex[:10], owner_id, chat_id, message_id, size, puzzle, puzzle.copy(), solution, None, False,
                    mode, difficulty, 5, 0, 3, int(time.time()), [], cages or [], daily)
        self.db.execute(
            "INSERT INTO games (id, owner_id, chat_id, message_id, size, puzzle, board, solution, mode, difficulty, hearts, mistakes, hints, started_at, history, cages, daily) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (game.id, owner_id, chat_id, message_id, size, _pack(puzzle), _pack(puzzle), _pack(solution), mode, difficulty, 5, 0, 3, game.started_at, "[]", json.dumps(cages or []), int(daily)),
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
            row["selected"], bool(row["finished"]), row["mode"], row["difficulty"], row["hearts"], row["mistakes"], row["hints"],
            row["started_at"], [tuple(x) for x in json.loads(row["history"])], json.loads(row["cages"]), bool(row["daily"]),
        )

    def save(self, game: Game) -> None:
        self.db.execute(
            "UPDATE games SET board = ?, selected = ?, finished = ?, hearts = ?, mistakes = ?, hints = ?, history = ? WHERE id = ?",
            (_pack(game.board), game.selected, int(game.finished), game.hearts, game.mistakes, game.hints, json.dumps(game.history or []), game.id),
        )
        self.db.commit()

    def finish(self, game: Game, won: bool) -> None:
        elapsed = max(1, int(time.time()) - game.started_at)
        self.db.execute("INSERT OR IGNORE INTO stats(user_id) VALUES (?)", (game.owner_id,))
        if won:
            self.db.execute("UPDATE stats SET wins=wins+1, best_time=CASE WHEN best_time IS NULL OR best_time>? THEN ? ELSE best_time END WHERE user_id=?", (elapsed, elapsed, game.owner_id))
        else:
            self.db.execute("UPDATE stats SET losses=losses+1 WHERE user_id=?", (game.owner_id,))
        self.db.commit()

    def stats(self, user_id: int) -> tuple[int, int, int | None]:
        row = self.db.execute("SELECT wins, losses, best_time FROM stats WHERE user_id=?", (user_id,)).fetchone()
        return (row[0], row[1], row[2]) if row else (0, 0, None)

    def leaderboard(self) -> list[tuple[int, int, int | None]]:
        return [tuple(row) for row in self.db.execute("SELECT user_id, wins, best_time FROM stats ORDER BY wins DESC, best_time ASC LIMIT 10")]
