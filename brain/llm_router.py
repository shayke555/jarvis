import logging

import groq as groq_module
from groq import AsyncGroq
from google import genai
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self) -> None:
        self._groq = AsyncGroq(api_key=settings.groq_api_key)
        self._gemini = genai.Client(api_key=settings.gemini_api_key)

    def route(self, messages: list[dict], context_tokens: int = 0) -> str:
        if context_tokens > 50_000:
            return "gemini"
        last_content = messages[-1]["content"].lower() if messages else ""
        if any(kw in last_content for kw in ["pdf", "document", "summarize this", "analyze this file", "ocr"]):
            return "gemini"
        return "groq"

    async def chat(self, messages: list[dict], context_tokens: int = 0) -> str:
        backend = self.route(messages, context_tokens)
        if backend == "groq":
            try:
                return await self._chat_groq(messages)
            except groq_module.RateLimitError:
                return await self._chat_gemini(messages)
        return await self._chat_gemini(messages)

    async def _chat_groq(self, messages: list[dict]) -> str:
        response = await self._groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        context_tokens: int = 0,
    ) -> dict | str:
        """Send messages + tool schemas to Groq function-calling.

        Returns:
        - str: final answer (LLM answered directly)
        - dict {"tool_calls": [...]}: LLM wants to use a tool
        """
        backend = self.route(messages, context_tokens)
        if backend != "groq":
            return await self._chat_gemini(messages)

        try:
            response = await self._groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=2048,
            )
        except Exception as e:
            logger.warning("Groq tool_use failed, falling back to plain chat: %s", e)
            return await self._chat_groq(messages)

        msg = response.choices[0].message
        if msg.tool_calls:
            return {
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            }
        return msg.content or ""

    async def _chat_gemini(self, messages: list[dict]) -> str:
        # Gemini uses "user"/"model" roles; map system+user → "user", assistant → "model"
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        response = await self._gemini.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
        )
        return response.text
