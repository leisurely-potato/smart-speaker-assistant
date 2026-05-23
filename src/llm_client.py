from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterable


Message = dict[str, str]


def _clean_text(text: str) -> str:
    return "".join("\ufffd" if "\ud800" <= char <= "\udfff" else char for char in text)


def _clean_message(message: Message) -> Message:
    return {key: _clean_text(value) for key, value in message.items()}


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        enable_web_search: bool = False,
        force_web_search: bool = False,
        search_strategy: str = "turbo",
    ) -> None:
        if not api_key:
            raise RuntimeError("缺少 LLM_API_KEY 或对应供应商的 API key，请先在 .env 中填写。")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.enable_web_search = enable_web_search
        self.force_web_search = force_web_search
        self.search_strategy = search_strategy

    def chat(self, messages: Iterable[Message]) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [_clean_message(message) for message in messages],
            "temperature": 0.7,
            "stream": False,
        }
        if self.enable_web_search:
            payload["enable_search"] = True
            payload["search_options"] = {
                "forced_search": self.force_web_search,
                "search_strategy": self.search_strategy,
            }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"大模型 API 请求失败：HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接大模型 API：{exc.reason}") from exc

        result = json.loads(body)
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"大模型 API 返回格式异常：{body}") from exc


DeepSeekClient = LLMClient
