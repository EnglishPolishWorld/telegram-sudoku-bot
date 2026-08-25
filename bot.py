from __future__ import annotations

import logging
import os
import time
from datetime import date

from rich_ui import creator_view, difficulty_picker, game_view, leaderboard_view, main_menu, size_picker, stats_view
from storage import Game, Storage
from sudoku import SPECS, is_complete, make_cages, make_puzzle
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
        elif "inline_query" in update:
            self.api.answer_inline(update["inline_query"]["id"], main_menu())

    def handle_message(self, message: dict) -> None:
        text = message.get("text", "").split("@", 1)[0].strip().lower()
        if text in {"/start", "/sudoku", "/new"}:
            self.api.send_rich(message["chat"]["id"], main_menu())
        elif text == "/creator":
            self.api.send_rich(message["chat"]["id"], creator_view())
        elif text == "/stats":
            self.api.send_rich(message["chat"]["id"], stats_view(*self.storage.stats(message["from"]["id"])))
        elif text in {"/top", "/rating"}:
            self.api.send_rich(message["chat"]["id"], leaderboard_view(self.storage.leaderboard()))
        elif text == "/group":
            if message["chat"].get("type") == "private":
                self.api.send_rich(message["chat"]["id"], main_menu("Команда /group предназначена для групп."))
                return
            puzzle, solution = make_puzzle(9, difficulty="normal")
            cages: list[dict] = []
            sent = self.api.send_rich(message["chat"]["id"], main_menu("Создаю общую игру…"))
            game = self.storage.create(0, message["chat"]["id"], sent["message_id"], 9, puzzle, solution, "classic", "normal", cages)
            self.api.edit_rich(message["chat"]["id"], sent["message_id"], game_view(game))

    def handle_callback(self, callback: dict) -> None:
        callback_id = callback["id"]
        data = callback.get("data", "")
        message = callback.get("message")
        inline_message_id = callback.get("inline_message_id")
        user_id = callback["from"]["id"]
        if not message and not inline_message_id:
            self.api.answer_callback(callback_id, "Сообщение игры недоступно.", True)
            return
        chat_id = message["chat"]["id"] if message else 0
        message_id = message["message_id"] if message else 0

        def edit(view: dict) -> None:
            self.api.edit_rich(chat_id, message_id, view, inline_message_id)

        try:
            if data.startswith("menu:"):
                self.api.answer_callback(callback_id)
                edit(main_menu())
                return
            if data.startswith("mode:"):
                self.api.answer_callback(callback_id)
                edit(difficulty_picker(data.split(":", 1)[1]))
                return
            if data.startswith("diff:"):
                _, mode, difficulty = data.split(":")
                self.api.answer_callback(callback_id)
                edit(size_picker(mode, difficulty))
                return
            if data.startswith("stats:"):
                self.api.answer_callback(callback_id)
                edit(stats_view(*self.storage.stats(user_id)))
                return
            if data.startswith("leaders:"):
                self.api.answer_callback(callback_id)
                edit(leaderboard_view(self.storage.leaderboard()))
                return
            if data.startswith("daily:"):
                seed = int(date.today().strftime("%Y%m%d"))
                puzzle, solution = make_puzzle(9, seed=seed, difficulty="normal")
                game = self.storage.create(user_id, chat_id, message_id, 9, puzzle, solution, "classic", "normal", [], True)
                self.api.answer_callback(callback_id)
                edit(game_view(game))
                return
            if data.startswith("new:"):
                _, mode, difficulty, raw_size = data.split(":")
                size = int(raw_size)
                if size not in SPECS:
                    raise ValueError("unsupported size")
                puzzle, solution = make_puzzle(size, difficulty=difficulty)
                cages = make_cages(size, solution) if mode == "killer" else []
                # Killer mode keeps fewer normal clues and adds cage sums.
                if mode == "killer":
                    keep = max(0, len([x for x in puzzle if x]) // 3)
                    shown = [i for i, x in enumerate(puzzle) if x]
                    puzzle = [x if i in set(shown[:keep]) else 0 for i, x in enumerate(puzzle)]
                game = self.storage.create(user_id, chat_id, message_id, size, puzzle, solution, mode, difficulty, cages)
                self.api.answer_callback(callback_id)
                edit(game_view(game))
                return

            action, game_id, raw_value = data.split(":", 2)
            game = self.storage.get(game_id)
            if game is None:
                self.api.answer_callback(callback_id, "Эта партия уже недоступна.", True)
                return
            if game.owner_id not in {0, user_id}:
                self.api.answer_callback(callback_id, "Эту головоломку начал другой игрок.", True)
                return

            if action == "cell":
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
                if number and number != game.solution[game.selected]:
                    game.hearts -= 1
                    game.mistakes += 1
                    self.storage.save(game)
                    if game.hearts <= 0:
                        self.storage.finish(game, False)
                        self.api.answer_callback(callback_id, "Сердца закончились.", True)
                        edit(main_menu("💔 Вы проиграли. Попробуйте ещё раз!"))
                    else:
                        self.api.answer_callback(callback_id, f"Ошибка. Осталось сердец: {game.hearts}", True)
                        edit(game_view(game))
                    return
                game.history = (game.history or []) + [(game.selected, game.board[game.selected])]
                game.board[game.selected] = number
                game.finished = is_complete(game.board, game.size)
                if not game.finished:
                    game.selected = self._next_empty(game)
                self.storage.save(game)
                if game.finished:
                    self.storage.finish(game, True)
                self.api.answer_callback(callback_id, "Готово!" if game.finished else "")
            elif action == "undo":
                if not game.history:
                    self.api.answer_callback(callback_id, "Отменять пока нечего.")
                    return
                index, previous = game.history.pop()
                game.board[index] = previous
                game.selected = index
                self.storage.save(game)
                self.api.answer_callback(callback_id)
            elif action == "hint":
                if game.hints <= 0:
                    self.api.answer_callback(callback_id, "Подсказки закончились.")
                    return
                empty = next((i for i, value in enumerate(game.board) if value == 0), None)
                if empty is None:
                    self.api.answer_callback(callback_id)
                    return
                game.history = (game.history or []) + [(empty, 0)]
                game.board[empty] = game.solution[empty]
                game.hints -= 1
                game.selected = self._next_empty(game)
                game.finished = is_complete(game.board, game.size)
                self.storage.save(game)
                if game.finished:
                    self.storage.finish(game, True)
                self.api.answer_callback(callback_id, "Открыта одна клетка.")
            else:
                self.api.answer_callback(callback_id, "Неизвестное действие.")
                return

            edit(game_view(game))
        except (ValueError, IndexError):
            self.api.answer_callback(callback_id, "Некорректное действие.", True)

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
    commands = [
        {"command": "start", "description": "Запустить Sudoku"},
        {"command": "creator", "description": "Создатель бота и обратная связь"},
        {"command": "group", "description": "Общая игра в группе"},
        {"command": "stats", "description": "Моя статистика"},
        {"command": "top", "description": "Рейтинг игроков"},
    ]
    api.call("setMyCommands", {"commands": commands})
    api.call("setMyCommands", {"commands": commands, "scope": {"type": "all_group_chats"}})
    bot = SudokuBot(api, Storage(os.getenv("DATABASE_PATH", "sudoku.sqlite3")))
    offset = 0
    log.info("Sudoku bot started")
    while True:
        try:
            updates = api.call("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query", "inline_query"]}, timeout=40)
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
