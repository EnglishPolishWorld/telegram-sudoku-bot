from __future__ import annotations

import json
import urllib.error
import urllib.request


class TelegramError(RuntimeError):
    pass


class TelegramAPI:
    def __init__(self, token: str) -> None:
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def call(self, method: str, payload: dict | None = None, timeout: int = 45) -> dict:
        body = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + method,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise TelegramError(f"Telegram HTTP {exc.code}: {details}") from exc
        if not result.get("ok"):
            raise TelegramError(result.get("description", "Unknown Telegram API error"))
        return result["result"]

    def send_rich(self, chat_id: int, rich_message: dict) -> dict:
        return self.call("sendRichMessage", {"chat_id": chat_id, "rich_message": rich_message})

    def edit_rich(self, chat_id: int, message_id: int, rich_message: dict) -> dict:
        return self.call(
            "editMessageText",
            {"chat_id": chat_id, "message_id": message_id, "rich_message": rich_message},
        )

    def answer_callback(self, callback_id: str, text: str = "", alert: bool = False) -> None:
        payload = {"callback_query_id": callback_id, "show_alert": alert}
        if text:
            payload["text"] = text
        self.call("answerCallbackQuery", payload)

