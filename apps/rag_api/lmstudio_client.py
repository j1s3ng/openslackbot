from openai import OpenAI

from packages.common.config import get_settings


class LMStudioClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.lmstudio_model
        self.client = OpenAI(
            base_url=settings.lmstudio_base_url,
            api_key=settings.lmstudio_api_key,
            timeout=settings.lmstudio_timeout_seconds,
        )

    def complete(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
