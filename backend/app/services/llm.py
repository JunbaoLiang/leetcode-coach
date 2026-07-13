"""Anthropic API wrapper: prompt loading, context assembly, streaming."""

from collections.abc import AsyncIterator
from pathlib import Path

from anthropic import AsyncAnthropic

from app.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class LLMNotConfiguredError(RuntimeError):
    pass


def load_prompt(name: str, **context: object) -> str:
    template = (PROMPTS_DIR / f"{name}.md").read_text()
    return template.format(**context)


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise LLMNotConfiguredError(
            "ANTHROPIC_API_KEY is not set — add it to backend/.env"
        )
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


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
