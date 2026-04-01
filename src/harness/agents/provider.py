from __future__ import annotations

import os

from openai import OpenAI


class ProviderUnavailableError(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(self, model: str) -> None:
        self.model = model

    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.available():
            raise ProviderUnavailableError("OPENAI_API_KEY is not set")
        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )
        return response.output_text.strip()
