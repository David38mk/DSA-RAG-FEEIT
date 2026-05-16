"""
BaseGenerator — abstract interface all LLM generator implementations must satisfy.

Keeping RAGPipeline provider-agnostic: it only calls generate() and get_stats().
Any class implementing these two methods works as a drop-in generator.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseGenerator(ABC):

    @abstractmethod
    def generate(
        self,
        query: str,
        context: List[Dict],
        language: str = "mk",
        max_tokens: int = 512,
        conversation_history: str = "",
    ) -> Dict:
        """
        Generate an answer given the user query and retrieved context chunks.

        Returns a dict with at minimum:
            answer      (str)  — the generated response
            sources     (list) — unique source filenames from context
            model       (str)  — model identifier used
        """
        ...

    def get_stats(self) -> Dict:
        """Return usage statistics. Optional — default is empty."""
        return {}
