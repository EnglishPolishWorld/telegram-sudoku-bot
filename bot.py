from __future__ import annotations

import logging
import os
import time

from rich_ui import game_view, size_picker
from storage import Game, Storage
from sudoku import SPECS, can_place, is_complete, make_puzzle
from telegram_api import TelegramAPI, TelegramError


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sudoku-bot")


class SudokuBot:
    def __init__(self, api: TelegramAPI, storage: Storage) -> None:
        self.api = api
        self.storage = storage

    def handle_update(self, update: dict) -> None:
        if "message" in update:
            self.handle_message(update["message"])
        elif "callback_query" in update:
            self.handle_callback(update["callback_query"])

    def handle_message(self, message: dict) -> None:
        text = message.get("text", "").split("@", 1)[0].strip().lower()
        if text in {"/start", "/sudoku", "/new"}:
            self.api.send_rich(message["chat"]["id"], size_picker())

    def handle_callback(self, callback: dict) -> None:
        callback_id = callback["id"]
        data = callback.get("data", "")
        message = callback.get("message")
        user_id = callback["from"]["id"]
        if not message:
            self.api.answer_callback(callback_id, "Сообщение игры недоступно.", True)
            return
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]

        try:
            if data == "sizes":
                self.api.answer_callback(callback_id)
                self.api.edit_rich(chat_id, message_id, size_picker())
                return
            if data.startswith("new:"):
                size = int(data.split(":", 1)[1])
                if size not in SPECS:
                    raise ValueError("unsupported size")
                puzzle, solution = make_puzzle(size)
                game = self.storage.create(user_id, chat_id, message_id, size, puzzle, solution)
                self.api.answer_callback(callback_id)
                self.api.edit_rich(chat_id, message_id, game_view(game))
                return

            action, game_id, raw_value = data.split(":", 2)
            game = self.storage.get(game_id)
            if game is None:
                self.api.answer_callback(callback_id, "Эта партия уже недоступна.", True)
                return
            if game.owner_id != user_id:
                self.api.answer_callback(callback_id, "Эту головоломку начал другой игрок.", True)
                return

            if action == "again":
                self._restart(game)
                self.api.answer_callback(callback_id)
            elif action == "cell":
                index = int(raw_value)
                if game.puzzle[index]:
                    self.api.answer_callback(callback_id, "Это исходная цифра — её менять нельзя.")
                    return
                game.selected = index
                self.storage.save(game)
                self.api.answer_callback(callback_id)
            elif action == "num":
                if game.selected is None:
                    self.api.answer_callback(callback_id, "Сначала выберите пустую клетку.")
                    return
                number = int(raw_value)
                if not 0 <= number <= game.size:
                    raise ValueError("invalid number")
                if not can_place(game.board, game.size, game.selected, number):
                    self.api.answer_callback(callback_id, "Здесь получится повтор.")
                    return
                game.board[game.selected] = number
                game.finished = is_complete(game.board, game.size)
                if not game.finished:
                    game.selected = self._next_empty(game)
                self.storage.save(game)
                self.api.answer_callback(callback_id, "Готово!" if game.finished else "")
            else:
                self.api.answer_callback(callback_id, "Неизвестное действие.")
                return

            self.api.edit_rich(chat_id, message_id, game_view(game))
        except (ValueError, IndexError):
            self.api.answer_callback(callback_id, "Некорректное действие.", True)

    def _restart(self, game: Game) -> None:
        puzzle, solution = make_puzzle(game.size)
        game.puzzle = puzzle
        game.board = puzzle.copy()
        game.solution = solution
        game.selected = None
        game.finished = False
        # Restart keeps the same compact game id; persist every changed field.
        self.storage.db.execute(
            "UPDATE games SET puzzle = ?, board = ?, solution = ?, selected = NULL, finished = 0 WHERE id = ?",
            (",".join(map(str, puzzle)), ",".join(map(str, puzzle)), ",".join(map(str, solution)), game.id),
        )
        self.storage.db.commit()

    @staticmethod
    def _next_empty(game: Game) -> int | None:
        start = (game.selected if game.selected is not None else -1) + 1
        for offset in range(len(game.board)):
            index = (start + offset) % len(game.board)
            if game.puzzle[index] == 0 and game.board[index] == 0:
                return index
        return game.selected


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Вставьте токен от @BotFather. Он используется только в памяти и не записывается в проект.")
        token = input("BOT_TOKEN: ").strip()
    if not token:
        raise SystemExit("Токен не указан")
    api = TelegramAPI(token)
    bot = SudokuBot(api, Storage(os.getenv("DATABASE_PATH", "sudoku.sqlite3")))
    offset = 0
    log.info("Sudoku bot started")
    while True:
        try:
            updates = api.call("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query"]}, timeout=40)
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    bot.handle_update(update)
                except TelegramError:
                    log.exception("Telegram request failed while processing update %s", update["update_id"])
        except TelegramError:
            log.exception("Polling failed; retrying")
            time.sleep(3)
        except KeyboardInterrupt:
            log.info("Stopped")
            break


if __name__ == "__main__":
    main()
