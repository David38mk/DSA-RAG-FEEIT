"""
Groq API Generator - Fast & Free LLM Access

Groq provides ultra-fast inference (500+ tokens/sec) with generous free tier.
Get free API key: https://console.groq.com/
"""

import os
from typing import List, Dict, Optional

from src.llm.base_generator import BaseGenerator
from src.llm.prompts import get_system_prompt, build_user_prompt


class GroqGenerator(BaseGenerator):
    """Generate answers using Groq API (fast & free)"""

    def __init__(self,
                 model_name: str = "llama-3.3-70b-versatile",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3):
        self.model_name = model_name
        self.temperature = temperature

        try:
            from groq import Groq
        except ImportError:
            print("groq package not installed. Install with: pip install groq")
            raise

        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError(
                "Groq API key required. "
                "Set GROQ_API_KEY env var or pass api_key. "
                "Free key at: https://console.groq.com/"
            )

        self.client = Groq(api_key=key)
        print(f"Initialized Groq ({self.model_name})")

        self.stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "by_language": {"mk": 0, "en": 0},
        }

    def generate(self,
                 query: str,
                 context: List[Dict],
                 language: str = "mk",
                 max_tokens: int = 512,
                 conversation_history: str = "") -> Dict:

        prompt = build_user_prompt(query, context, language, conversation_history)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": get_system_prompt(language)},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=max_tokens,
                top_p=0.9,
                stream=False,
            )
            answer = response.choices[0].message.content
            self.stats["total_generations"] += 1
            self.stats["by_language"][language] += 1
            if hasattr(response, "usage"):
                self.stats["total_tokens"] += response.usage.total_tokens

        except Exception as e:
            answer = f"Error generating response: {str(e)}"

        return {
            "query": query,
            "answer": answer,
            "language": language,
            "sources": self._extract_sources(context),
            "num_sources": len(context),
            "model": self.model_name,
            "provider": "groq",
        }

    def _extract_sources(self, context: List[Dict]) -> List[str]:
        sources = {c.get("metadata", {}).get("source", "Unknown") for c in context}
        return sorted(sources)

    def get_stats(self) -> Dict:
        return self.stats.copy()


# Backward-compatibility shim
class MistralGenerator:
    def __init__(self, mode: str = "api", **kwargs):
        from .mistral_generator import MistralGenerator as Original
        self.generator = Original(mode=mode, **kwargs)

    def generate(self, *args, **kwargs):
        return self.generator.generate(*args, **kwargs)

    def get_stats(self):
        return self.generator.get_stats()
