from __future__ import annotations

import time
from storage import Game

MARKS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _button(text: str, callback_data: str, style: str | None = None) -> dict:
    result: dict = {"text": text, "callback_data": callback_data}
    if style:
        result["style"] = style
    return result


def main_menu(note: str = "") -> dict:
    blocks = [{"type": "heading", "size": 2, "text": "Sudoku"}]
    if note:
        blocks.append({"type": "paragraph", "text": note})
    blocks += [
        {"type": "paragraph", "text": "Выберите режим."},
        {"type": "buttons", "align": "center", "buttons": [
            _button("Классика", "mode:classic", "primary"), _button("Killer Σ", "mode:killer", "success"),
            _button("Ежедневная", "daily:0"),
        ]},
        {"type": "buttons", "align": "center", "buttons": [
            _button("Статистика", "stats:0"), _button("Рейтинг", "leaders:0")
        ]},
    ]
    return {"blocks": blocks}


def creator_view() -> dict:
    return {"blocks": [
        {"type": "heading", "size": 3, "text": "Создатель бота"},
        {"type": "paragraph", "text": "Создатель бота — @eternall_dog\nПо всем вопросам и предложениям пишите ему."},
    ]}


def difficulty_picker(mode: str) -> dict:
    return {"blocks": [
        {"type": "heading", "size": 3, "text": "Killer Sudoku" if mode == "killer" else "Классическое Sudoku"},
        {"type": "paragraph", "text": "Выберите сложность."},
        {"type": "buttons", "align": "center", "buttons": [
            _button("Лёгкая", f"diff:{mode}:easy"), _button("Средняя", f"diff:{mode}:normal", "primary"),
            _button("Сложная", f"diff:{mode}:hard")
        ]},
        {"type": "buttons", "align": "center", "buttons": [_button("← Меню", "menu:0")]},
    ]}


def size_picker(mode: str = "classic", difficulty: str = "normal") -> dict:
    return {"blocks": [
        {"type": "heading", "size": 3, "text": "Выберите размер"},
        {"type": "buttons", "align": "center", "buttons": [
            _button("4 × 4", f"new:{mode}:{difficulty}:4"), _button("6 × 6", f"new:{mode}:{difficulty}:6"),
            _button("9 × 9", f"new:{mode}:{difficulty}:9", "primary"),
        ]},
        {"type": "buttons", "align": "center", "buttons": [_button("← Меню", "menu:0")]},
    ]}


def stats_view(wins: int, losses: int, best: int | None) -> dict:
    best_text = f"{best // 60}:{best % 60:02d}" if best else "—"
    return {"blocks": [
        {"type": "heading", "size": 3, "text": "Ваша статистика"},
        {"type": "paragraph", "text": f"Победы: {wins}\nПоражения: {losses}\nЛучшее время: {best_text}"},
        {"type": "buttons", "buttons": [_button("← Меню", "menu:0", "primary")]},
    ]}


def leaderboard_view(rows: list[tuple[int, int, int | None]]) -> dict:
    text = "Пока результатов нет." if not rows else "\n".join(
        f"{i}. Игрок {uid}: {wins} побед" for i, (uid, wins, _) in enumerate(rows, 1)
    )
    return {"blocks": [
        {"type": "heading", "size": 3, "text": "Рейтинг"}, {"type": "paragraph", "text": text},
        {"type": "buttons", "buttons": [_button("← Меню", "menu:0", "primary")]},
    ]}


def game_view(game: Game) -> dict:
    cage_for: dict[int, tuple[int, dict]] = {}
    for cage_index, cage in enumerate(game.cages or []):
        for index in cage["cells"]:
            cage_for[index] = (cage_index, cage)
    cells: list[list[dict]] = []
    for row in range(game.size):
        table_row = []
        for col in range(game.size):
            index = row * game.size + col
            value = game.board[index]
            label = str(value) if value else "·"
            if game.mode == "killer" and index in cage_for:
                cage_index, cage = cage_for[index]
                mark = MARKS[cage_index % len(MARKS)]
                label = f"{mark}{cage['sum']}" if index == cage["cells"][0] and not value else f"{mark}{label}"
            style = "link" if game.puzzle[index] else None
            if index == game.selected:
                style = "primary"
            table_row.append({"text": {"type": "button", "button": _button(label, f"cell:{game.id}:{index}", style)}, "align": "center", "valign": "middle"})
        cells.append(table_row)
    elapsed = max(0, int(time.time()) - game.started_at)
    status = f"{'❤️' * game.hearts}{'🖤' * (5-game.hearts)}  ⏱ {elapsed // 60}:{elapsed % 60:02d}  💡 {game.hints}"
    blocks: list[dict] = [
        {"type": "heading", "size": 3, "text": f"{'Killer ' if game.mode == 'killer' else ''}Sudoku {game.size}×{game.size}"},
        {"type": "paragraph", "text": "Готово! Победа 🎉" if game.finished else status},
        {"type": "table", "cells": cells, "is_bordered": True, "is_compact": True},
    ]
    if not game.finished:
        buttons = [_button(str(n), f"num:{game.id}:{n}") for n in range(1, game.size + 1)]
        for offset in range(0, len(buttons), 8):
            blocks.append({"type": "buttons", "align": "center", "buttons": buttons[offset:offset + 8]})
        blocks.append({"type": "buttons", "align": "center", "buttons": [
            _button("Стереть", f"num:{game.id}:0"), _button("↶ Отмена", f"undo:{game.id}:0"),
            _button("💡 Подсказка", f"hint:{game.id}:0"), _button("Меню", "menu:0")
        ]})
    else:
        blocks.append({"type": "buttons", "buttons": [_button("Ещё игру", "menu:0", "success")]})
    return {"blocks": blocks}
