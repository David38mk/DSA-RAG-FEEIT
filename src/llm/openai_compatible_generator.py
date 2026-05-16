"""
OpenAI-compatible generator — works with any OpenAI-format API endpoint.

Preconfigured for:
  - OpenRouter (free models): https://openrouter.ai
      Free API key at: https://openrouter.ai/keys
      Store at: D:\\API_KEYS\\OPENROUTER_API_KEY.txt
      Free models listed in FREE_OPENROUTER_MODELS below.

  - Ollama (local, unlimited, no key needed):
      Install Ollama from https://ollama.com, then: ollama pull llama3.1

Requires: pip install openai
"""

import os
import time
from typing import Dict, List, Optional

from src.llm.base_generator import BaseGenerator
from src.llm.prompts import get_system_prompt, build_user_prompt

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Run evaluation/scripts/list_openrouter_free_models.py to refresh this list
FREE_OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
]


class OpenAICompatibleGenerator(BaseGenerator):

    def __init__(
        self,
        model_name: str = "meta-llama/llama-3.3-70b-instruct:free",
        base_url: str = OPENROUTER_BASE_URL,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        provider_name: str = "openrouter",
        max_retries: int = 1,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Run: pip install openai")

        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.provider_name = provider_name
        self.max_retries = max_retries

        key = api_key or os.getenv("OPENROUTER_API_KEY") or "ollama"
        self.client = OpenAI(base_url=base_url, api_key=key)

        print(f"Initialized {provider_name} ({self.model_name})")
        if "openrouter" in base_url:
            print(f"  Free tier: rate-limited upstream (Venice), no daily hard cap")
        else:
            print(f"  Local endpoint: {base_url}")

        self.stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "by_language": {"mk": 0, "en": 0},
        }

    @classmethod
    def for_openrouter(
        cls,
        model_name: str = "meta-llama/llama-3.3-70b-instruct:free",
        api_key: Optional[str] = None,
        max_retries: int = 1,
    ) -> "OpenAICompatibleGenerator":
        return cls(
            model_name=model_name,
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            provider_name="openrouter",
            max_retries=max_retries,
        )

    @classmethod
    def for_ollama(
        cls,
        model_name: str = "llama3.1",
        base_url: str = OLLAMA_BASE_URL,
    ) -> "OpenAICompatibleGenerator":
        return cls(
            model_name=model_name,
            base_url=base_url,
            api_key="ollama",
            provider_name="ollama",
            max_retries=1,
        )

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

        answer = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    top_p=0.9,
                )
                answer = response.choices[0].message.content
                self.stats["total_generations"] += 1
                self.stats["by_language"][language] = (
                    self.stats["by_language"].get(language, 0) + 1
                )
                if hasattr(response, "usage") and response.usage:
                    self.stats["total_tokens"] += response.usage.total_tokens or 0
                break

            except Exception as e:
                err = str(e)
                retry_after = 30
                if "retry_after_seconds" in err:
                    try:
                        import re
                        m = re.search(r"'retry_after_seconds':\s*([\d.]+)", err)
                        if m:
                            retry_after = int(float(m.group(1))) + 1
                    except Exception:
                        pass

                if "429" in err and attempt < self.max_retries - 1:
                    print(f"  Rate limited — waiting {retry_after}s (retry {attempt + 2}/{self.max_retries})")
                    time.sleep(retry_after)
                else:
                    answer = f"Error generating response: {err}"
                    break

        if answer is None:
            answer = "Error: max retries exceeded"

        return {
            "query": query,
            "answer": answer,
            "language": language,
            "sources": self._extract_sources(context),
            "num_sources": len(context),
            "model": self.model_name,
            "provider": self.provider_name,
        }

    def _extract_sources(self, context: List[Dict]) -> List[str]:
        sources = {c.get("metadata", {}).get("source", "Unknown") for c in context}
        return sorted(sources)

    def get_stats(self) -> Dict:
        return self.stats.copy()
