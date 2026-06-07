from __future__ import annotations

from collections.abc import Iterable

from openai import OpenAI

from app.config import Settings


class QwenClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.qwen_api_key)

    def chat(self, messages: list[dict], stream: bool = False) -> str | Iterable[str]:
        if not self.enabled:
            answer = local_answer(messages[-1]["content"])
            return stream_text(answer) if stream else answer

        client = OpenAI(
            api_key=self.settings.qwen_api_key,
            base_url=self.settings.qwen_base_url,
            timeout=self.settings.request_timeout,
        )
        response = client.chat.completions.create(
            model=self.settings.qwen_model,
            messages=messages,
            temperature=0.2,
            stream=stream,
        )
        if not stream:
            return response.choices[0].message.content or ""

        def _iter() -> Iterable[str]:
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        return _iter()


def local_answer(prompt: str) -> str:
    if "【检索上下文】" in prompt:
        context = prompt.split("【检索上下文】", 1)[-1].split("【用户问题】", 1)[0].strip()
        lines = [line.strip() for line in context.splitlines() if line.strip() and not line.startswith("[来源")]
        preview = "\n".join(lines[:6])
        return (
            "当前未配置通义千问 API Key，系统已使用本地检索摘要模式回答。\n\n"
            f"根据已选知识库中召回的内容，核心信息如下：\n{preview}"
        )
    return "当前未配置通义千问 API Key，普通对话模式将以本地兜底方式回复。你可以在 .env 中配置 DASHSCOPE_API_KEY 启用 qwen-plus。"


def stream_text(text: str) -> Iterable[str]:
    for char in text:
        yield char
