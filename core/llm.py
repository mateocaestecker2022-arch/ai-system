import anthropic
from typing import AsyncIterator


def call_llm(prompt: str, config) -> str:
    client = anthropic.Anthropic(api_key=config.API_KEY)
    message = client.messages.create(
        model=config.MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def call_llm_async(prompt: str, config) -> str:
    client = anthropic.AsyncAnthropic(api_key=config.API_KEY)
    message = await client.messages.create(
        model=config.MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def stream_llm_async(prompt: str, config) -> AsyncIterator[str]:
    client = anthropic.AsyncAnthropic(api_key=config.API_KEY)
    async with client.messages.stream(
        model=config.MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
