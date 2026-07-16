"""Anthropic API wrapper: prompt loading, context assembly, streaming, structured output."""

import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from app.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

T = TypeVar("T", bound=BaseModel)


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMOutputError(RuntimeError):
    """The model failed to produce schema-valid JSON even after a retry."""


def load_prompt(name: str, **context: object) -> str:
    template = (PROMPTS_DIR / f"{name}.md").read_text()
    return template.format(**context)


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise LLMNotConfiguredError(
            "ANTHROPIC_API_KEY is not set — add it to backend/.env"
        )
    # bump SDK retries (default 2): rides out transient 429/529 overload spikes
    return AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=4)


def friendly_llm_error(e: Exception) -> str:
    text = str(e).lower()
    if "overloaded" in text or "rate_limit" in text or "429" in text:
        return "Claude 服务临时过载,稍等几秒再发一次(你的消息已保留)"
    return f"LLM 调用失败: {e}"


async def stream_completion(
    system: str,
    messages: list[dict],
    max_tokens: int = 1500,
) -> AsyncIterator[str]:
    """Yield text deltas from a streaming completion."""
    client = _client()
    async with client.messages.stream(
        model=settings.anthropic_model,
        system=system,
        messages=messages,
        max_tokens=max_tokens,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def completion(system: str, messages: list[dict], max_tokens: int = 3000) -> str:
    """Non-streaming completion returning the full text."""
    client = _client()
    resp = await client.messages.create(
        model=settings.anthropic_model,
        system=system,
        messages=messages,
        max_tokens=max_tokens,
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a completion (tolerates ``` fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{") : text.rfind("}") + 1]
    return json.loads(candidate)


async def structured_completion(
    system: str,
    messages: list[dict],
    schema: type[T],
    max_tokens: int = 3000,
) -> T:
    """Completion validated against a Pydantic schema; retries once on invalid output
    (PLAN 13.5.5), then raises LLMOutputError instead of degrading silently."""
    convo = list(messages)
    last_error = ""
    for _ in range(2):
        text = await completion(system, convo, max_tokens=max_tokens)
        try:
            return schema.model_validate(_extract_json(text))
        except (ValueError, ValidationError) as e:
            last_error = str(e)
            convo = [
                *convo,
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        "你的上一条输出不是合法的目标 JSON,错误:"
                        f"{last_error}\n请只输出符合要求的 JSON,不要任何其他文字。"
                    ),
                },
            ]
    raise LLMOutputError(f"LLM 未能产出合法 JSON(已重试一次):{last_error}")
