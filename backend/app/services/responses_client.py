import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class ResponsesClient:
    def __init__(self) -> None:
        if settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            self.client = AsyncOpenAI()

    async def create(
        self,
        instructions: str,
        user_input: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        logger.info(
            (
                "Calling OpenAI chat completion model=%s input_chars=%s "
                "instruction_chars=%s max_tokens=%s temperature=%s."
            ),
            settings.openai_model,
            len(user_input),
            len(instructions),
            max_tokens,
            temperature,
        )
        request_payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_input},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        response = await self.client.chat.completions.create(**request_payload)

        content = response.choices[0].message.content or ""
        logger.info("OpenAI chat completion returned response_chars=%s.", len(content))
        return content
