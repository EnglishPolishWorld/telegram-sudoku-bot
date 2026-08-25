from __future__ import annotations

from storage import Game


def _button(text: str, callback_data: str, style: str | None = None) -> dict:
    result: dict = {"text": text, "callback_data": callback_data}
    if style:
        result["style"] = style
    return result


def size_picker() -> dict:
    return {
        "blocks": [
            {"type": "heading", "size": 2, "text": "Sudoku"},
            {"type": "paragraph", "text": "Выберите размер доски."},
            {
                "type": "buttons",
                "align": "center",
                "buttons": [
                    _button("4 × 4", "new:4"),
                    _button("6 × 6", "new:6"),
                    _button("9 × 9", "new:9", "primary"),
                ],
            },
        ]
    }


def game_view(game: Game) -> dict:
    cells: list[list[dict]] = []
    for row in range(game.size):
        table_row = []
        for col in range(game.size):
            index = row * game.size + col
            value = game.board[index]
            style = "link" if game.puzzle[index] else None
            if index == game.selected:
                style = "primary"
            cell_button = _button(str(value) if value else "·", f"cell:{game.id}:{index}", style)
            table_row.append(
                {
                    "text": {"type": "button", "button": cell_button},
                    "align": "center",
                    "valign": "middle",
                }
            )
        cells.append(table_row)

    blocks: list[dict] = [
        {"type": "heading", "size": 3, "text": f"Sudoku {game.size} × {game.size}"},
        {
            "type": "paragraph",
            "text": "Готово! Все клетки заполнены правильно. 🎉"
            if game.finished
            else "Правило: заполните клетки без повторов в строках, столбцах и блоках.",
        },
        {"type": "table", "cells": cells, "is_bordered": True, "is_compact": True},
    ]

    if not game.finished:
        number_buttons = [_button(str(number), f"num:{game.id}:{number}") for number in range(1, game.size + 1)]
        for offset in range(0, len(number_buttons), 8):
            blocks.append({"type": "buttons", "align": "center", "buttons": number_buttons[offset : offset + 8]})
        blocks.append(
            {
                "type": "buttons",
                "align": "center",
                "buttons": [
                    _button("Стереть", f"num:{game.id}:0"),
                    _button("Новая", f"again:{game.id}:0", "success"),
                    _button("Размер", "sizes", "primary"),
                ],
            }
        )
    else:
        blocks.append(
            {
                "type": "buttons",
                "align": "center",
                "buttons": [
                    _button("Ещё одну", f"again:{game.id}:0", "success"),
                    _button("Другой размер", "sizes", "primary"),
                ],
            }
        )
    return {"blocks": blocks}
