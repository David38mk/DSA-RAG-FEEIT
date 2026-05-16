"""
Google Gemini generator — free tier via Google AI Studio.

Free tier: 5 RPM, 250K TPM, 20 RPD (gemini-2.5-flash as of May 2026).
Get a free API key at: https://aistudio.google.com/app/apikey
Store it at: D:\\API_KEYS\\GEMINI_API_KEY.txt

Requires: pip install google-genai
"""

import os
from typing import Dict, List, Optional

from src.llm.base_generator import BaseGenerator
from src.llm.prompts import get_system_prompt, build_user_prompt


class GeminiGenerator(BaseGenerator):

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
    ):
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("Run: pip install google-genai")

        self.model_name = model_name
        self.temperature = temperature

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY not set. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )

        self._client = genai.Client(api_key=key)
        self._types = types
        print(f"Initialized Gemini ({self.model_name})")
        print(f"  Free tier: 5 RPM / 250K TPM / 20 RPD")

        self.stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "by_language": {"mk": 0, "en": 0},
        }

    def generate(
        self,
        query: str,
        context: List[Dict],
        language: str = "mk",
        max_tokens: int = 512,
        conversation_history: str = "",
    ) -> Dict:
        system_prompt = get_system_prompt(language)
        user_prompt = build_user_prompt(query, context, language, conversation_history)

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=self._types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=self.temperature,
                    max_output_tokens=max_tokens,
                    top_p=0.9,
                ),
            )
            answer = response.text
            self.stats["total_generations"] += 1
            self.stats["by_language"][language] = (
                self.stats["by_language"].get(language, 0) + 1
            )
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                self.stats["total_tokens"] += (
                    getattr(response.usage_metadata, "total_token_count", 0) or 0
                )

        except Exception as e:
            answer = f"Error generating response: {str(e)}"

        return {
            "query": query,
            "answer": answer,
            "language": language,
            "sources": self._extract_sources(context),
            "num_sources": len(context),
            "model": self.model_name,
            "provider": "google",
        }

    def _extract_sources(self, context: List[Dict]) -> List[str]:
        sources = {c.get("metadata", {}).get("source", "Unknown") for c in context}
        return sorted(sources)

    def get_stats(self) -> Dict:
        return self.stats.copy()
