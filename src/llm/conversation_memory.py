"""
Conversation memory - sliding window of recent turns.

Held in-memory per Streamlit session. Provides the LLM with prior turns
so it can resolve anaphora ("how do they work?", "и таа?") without needing
heuristic query rewriting.

Scope decision (thesis defense note): we deliberately do NOT modify the
retrieval query with prior-turn topics. The risk that a wrong topic guess
shifts the embedding off-target outweighs the gain, given that a 70B LLM
can resolve references natively when given the prior turns in its prompt.
"""

import time
from typing import List, Optional


class ConversationMemory:
    """Sliding-window memory of recent (query, answer) turns."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.turns: List[dict] = []

    def add_turn(
        self,
        query: str,
        answer: str,
        language: str = "mk",
    ) -> None:
        self.turns.append({
            "query": query,
            "answer": answer,
            "language": language,
            "timestamp": time.time(),
        })
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def get_history(self, n: Optional[int] = None) -> List[dict]:
        if n is None:
            return list(self.turns)
        return self.turns[-n:]

    def format_for_prompt(self, n: int = 3, language: str = "mk") -> str:
        """
        Format the last n turns as a transcript block for the LLM system prompt.
        Returns an empty string if there is no history yet.
        """
        recent = self.turns[-n:]
        if not recent:
            return ""
        if language == "mk":
            student_label, assistant_label = "Студент", "Асистент"
        else:
            student_label, assistant_label = "Student", "Assistant"
        parts = [
            f"{student_label}: {t['query']}\n{assistant_label}: {t['answer']}"
            for t in recent
        ]
        return "\n\n".join(parts)

    def clear(self) -> None:
        self.turns = []

    def __len__(self) -> int:
        return len(self.turns)
