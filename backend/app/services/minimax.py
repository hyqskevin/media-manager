import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from app.core.config import Settings


class MiniMaxError(RuntimeError):
    pass


class MiniMaxClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    def extract(self, text: str) -> dict[str, Any]:
        return self._request(text, "Extract event fields and return one JSON object.", 1024)

    def extract_many(self, text: str, reference: datetime | None = None) -> dict[str, Any]:
        reference = reference or datetime.now()
        instruction = (
            "Extract every distinct concrete event from the note and OCR text. Return one JSON object with an activities array. "
            "Each activity must contain name, start_time, end_time, location, price, type, summary, confidence, and source_image_indexes. "
            f"The reference date is {reference.date().isoformat()} in {self.settings.celery_timezone}. "
            f"Only extract events intersecting the next {self.settings.activity_future_window_days} days. "
            "Use ISO 8601 date-time strings for start_time and end_time. Never invent a year that is absent from the source. "
            "Do not create one summary event for the whole note. IMAGE markers identify source image indexes. Use null for unknown values."
        )
        tools=[{"type":"function","function":{"name":"emit_activities","description":"Return every distinct concrete activity found in the note and OCR images.","parameters":{"type":"object","properties":{"activities":{"type":"array","items":{"type":"object","properties":{"name":{"type":"string"},"start_time":{"type":["string","null"]},"end_time":{"type":["string","null"]},"location":{"type":["string","null"]},"price":{"type":["string","null"]},"type":{"type":["string","null"]},"summary":{"type":["string","null"]},"confidence":{"type":["number","string"]},"source_image_indexes":{"type":"array","items":{"type":"integer"}}},"required":["name","start_time","location","source_image_indexes"]}}},"required":["activities"]}}}]
        return self._request(text, instruction+" You must call emit_activities exactly once.", 16384, tools)

    def extract_many_parallel(
        self, texts: list[str], reference: datetime | None = None
    ) -> list[dict[str, Any]]:
        """批量并行调用 extract_many，按输入顺序返回结果。

        并发数由 settings.minimax_concurrency 控制（默认 1=串行，最高 4）。
        小范围并行避免 529 限流雪崩；每个线程独立 httpx.Client。
        """
        concurrency = getattr(self.settings, "minimax_concurrency", 1)
        if concurrency <= 1 or len(texts) <= 1:
            return [self.extract_many(text, reference) for text in texts]

        results: list[dict[str, Any] | None] = [None] * len(texts)
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_index = {
                executor.submit(self.extract_many, text, reference): idx
                for idx, text in enumerate(texts)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                results[idx] = future.result()
        return [r if r is not None else {"activities": []} for r in results]

    def _request(self, text: str, instruction: str, max_tokens: int, tools: list[dict[str,Any]] | None = None) -> dict[str, Any]:
        if not self.settings.minimax_api_key:
            raise MiniMaxError("MINIMAX_API_KEY is not configured")
        url = f"{self.settings.minimax_base_url.rstrip('/')}/{self.settings.minimax_chat_path.lstrip('/')}"
        payload = {
            "model": self.settings.minimax_model,
            "messages": [
                {"role": "system", "name": "extractor", "content": instruction},
                {"role": "user", "name": "user", "content": text},
            ],
            "max_completion_tokens": max_tokens,
        }
        if tools:
            payload["tools"]=tools; payload["tool_choice"]="auto"
        with httpx.Client(transport=self.transport, timeout=self.settings.minimax_timeout_seconds) as client:
            response = client.post(url, headers={"Authorization": f"Bearer {self.settings.minimax_api_key}", "Content-Type": "application/json"}, json=payload)
        if response.status_code != 200:
            raise MiniMaxError(f"MiniMax HTTP {response.status_code}")
        body = response.json()
        base_resp = body.get("base_resp") or {}
        if base_resp.get("status_code") not in (None, 0):
            raise MiniMaxError(str(base_resp.get("status_msg") or base_resp.get("status_code")))
        try:
            message=body["choices"][0]["message"]
            tool_calls=message.get("tool_calls") or []
            content=tool_calls[0]["function"]["arguments"] if tool_calls else message["content"]
            if isinstance(content,dict): return content
            if content.startswith("```json"):
                content = content.removeprefix("```json").removesuffix("```").strip()
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise MiniMaxError("MiniMax returned invalid structured output") from exc
        if not isinstance(result, dict):
            raise MiniMaxError("MiniMax returned non-object output")
        return result

    def vision_chat(
        self,
        image_b64: str,
        mime_type: str,
        instruction: str,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        extra_user_text: str = "",
    ) -> dict[str, Any]:
        """调用 MiniMax vision 能力（要求 LLM 支持 image_url）。

        image_b64: 已 base64 编码的图片字节；
        mime_type: 'image/jpeg' / 'image/png';
        extra_user_text: 可补充文本上下文；
        返回 dict（JSON 解析成功时），否则抛 MiniMaxError。
        """
        if not self.settings.minimax_api_key:
            raise MiniMaxError("MINIMAX_API_KEY is not configured")
        url = f"{self.settings.minimax_base_url.rstrip('/')}/{self.settings.minimax_chat_path.lstrip('/')}"
        content_blocks: list[dict[str, Any]] = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
            }
        ]
        if extra_user_text:
            content_blocks.append({"type": "text", "text": extra_user_text})
        payload: dict[str, Any] = {
            "model": getattr(self.settings, "minimax_vision_model", "MiniMax-vision-01"),
            "messages": [
                {"role": "system", "name": "vision_parser", "content": instruction},
                {"role": "user", "name": "user", "content": content_blocks},
            ],
            "max_completion_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        with httpx.Client(transport=self.transport, timeout=self.settings.minimax_timeout_seconds) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.settings.minimax_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if response.status_code != 200:
            raise MiniMaxError(f"MiniMax vision HTTP {response.status_code}")
        body = response.json()
        base_resp = body.get("base_resp") or {}
        if base_resp.get("status_code") not in (None, 0):
            raise MiniMaxError(str(base_resp.get("status_msg") or base_resp.get("status_code")))
        try:
            message = body["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                content = tool_calls[0]["function"]["arguments"]
            else:
                content = message["content"]
            if isinstance(content, dict):
                return content
            if isinstance(content, str) and content.startswith("```json"):
                content = content.removeprefix("```json").removesuffix("```").strip()
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise MiniMaxError("MiniMax vision returned invalid structured output") from exc
