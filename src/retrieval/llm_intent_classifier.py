"""
LLM Intent Classifier - Phase 6 Enhancement

Uses Groq LLM to classify query intent with semantic understanding.
Provides reasoning and confidence scores for better routing decisions.

For DSA-RAG-FEEIT thesis project - Phase 6: LLM-Enhanced Routing
"""

import os
import json
from typing import Dict, Tuple
from groq import Groq


class LLMIntentClassifier:
    """
    LLM-based query intent classifier using semantic understanding.
    
    Advantages over rule-based:
    - Semantic understanding (not just keyword matching)
    - Handles ambiguous queries better
    - Provides reasoning for decisions
    - Adapts to new query patterns
    
    Disadvantages:
    - Slower (~300-500ms vs ~1ms)
    - Requires API access
    - Non-deterministic (small variations)
    """
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant", api_key: str = None):
        """
        Initialize LLM classifier.

        Args:
            model_name: Groq model to use. Intentionally the 8B model —
                binary TECHNICAL/SUPPORT classification doesn't need 70B,
                and using 70B here doubles the heavyweight call count per query,
                burning the free-tier 100K daily token cap twice as fast.
            api_key: Groq API key (or from GROQ_API_KEY env)
        """
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Set environment variable or pass api_key parameter.")
        
        self.client = Groq(api_key=self.api_key)
        
        # Statistics
        self.stats = {
            "total_classifications": 0,
            "by_intent": {"TECHNICAL": 0, "SUPPORT": 0, "AMBIGUOUS": 0},
            "avg_confidence": 0.0,
            "avg_latency_ms": 0.0
        }
    
    def classify(self, query: str, language: str = "mk") -> Dict:
        """
        Classify query intent using LLM.
        
        Args:
            query: User query
            language: Query language ('mk' or 'en')
            
        Returns:
            {
                "intent": "TECHNICAL" | "SUPPORT" | "AMBIGUOUS",
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "alternative_intent": str | None,
                "latency_ms": int
            }
        """
        import time
        start_time = time.perf_counter()
        
        # Build classification prompt
        system_prompt = self._get_system_prompt(language)
        user_prompt = self._build_classification_prompt(query, language)
        
        try:
            # Call Groq LLM
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=300
            )
            
            # Parse response
            result_text = response.choices[0].message.content.strip()
            result = self._parse_llm_response(result_text)
            
            # Calculate latency
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            result["latency_ms"] = latency_ms
            
            # Update statistics
            self._update_stats(result, latency_ms)
            
            return result
            
        except Exception as e:
            # Fallback to AMBIGUOUS if LLM fails
            return {
                "intent": "AMBIGUOUS",
                "confidence": 0.0,
                "reasoning": f"LLM classification failed: {str(e)}",
                "alternative_intent": None,
                "latency_ms": int((time.perf_counter() - start_time) * 1000),
                "error": str(e)
            }
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt based on language"""
        
        if language == "mk":
            return """Ти си експерт за класификација на прашања за курсот "Податочни Структури и Анализа на Алгоритми" (ПСАА).

Твоја задача е да ги класификуваш прашањата во 2 категории:

**TECHNICAL** - Прашања за:
- Податочни структури (низи, листи, дрва, графови, hash табели)
- Алгоритми (сортирање, пребарување, динамичко програмирање)
- Комплексност (Big O, анализа на алгоритми)
- Имплементација и код
- Теоретски концепти од предметот

**SUPPORT** - Прашања за:
- Организација на испити и лабораториски вежби
- Бодување и услови за полагање
- Рокови и датуми
- Административни процедури
- Општи прашања за курсот
- Консултации и термини

Одговори САМО во JSON формат без никакви дополнителни текстови."""

        else:  # English
            return """You are an expert at classifying questions for a "Data Structures and Analysis of Algorithms" course.

Your task is to classify questions into 2 categories:

**TECHNICAL** - Questions about:
- Data structures (arrays, lists, trees, graphs, hash tables)
- Algorithms (sorting, searching, dynamic programming)
- Complexity (Big O, algorithm analysis)
- Implementation and code
- Theoretical concepts from the course

**SUPPORT** - Questions about:
- Exam and lab organization
- Grading and passing requirements
- Deadlines and dates
- Administrative procedures
- General course questions
- Office hours and appointments

Respond ONLY in JSON format without any additional text."""
    
    def _build_classification_prompt(self, query: str, language: str) -> str:
        """Build classification prompt"""
        
        if language == "mk":
            template = f"""Прашање: "{query}"

Класифицирај го ова прашање и одговори во следниот JSON формат:

{{
    "intent": "TECHNICAL" или "SUPPORT",
    "confidence": 0.0 до 1.0,
    "reasoning": "Кратко објаснување зошто е ова категорија",
    "alternative_intent": "Друга можна категорија ако не си сигурен" или null
}}

Примери:

Прашање: "Објасни AVL дрва"
{{
    "intent": "TECHNICAL",
    "confidence": 0.95,
    "reasoning": "Прашање за податочна структура (AVL дрва)",
    "alternative_intent": null
}}

Прашање: "Колку поени треба за полагање?"
{{
    "intent": "SUPPORT",
    "confidence": 0.98,
    "reasoning": "Прашање за услови за полагање и бодување",
    "alternative_intent": null
}}

Прашање: "Објасни како да положам испит"
{{
    "intent": "SUPPORT",
    "confidence": 0.75,
    "reasoning": "Прашање за процедура на полагање испит",
    "alternative_intent": "TECHNICAL"
}}

Сега класифицирај го горното прашање:"""

        else:  # English
            template = f"""Question: "{query}"

Classify this question and respond in the following JSON format:

{{
    "intent": "TECHNICAL" or "SUPPORT",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation why this category",
    "alternative_intent": "Other possible category if uncertain" or null
}}

Examples:

Question: "Explain AVL trees"
{{
    "intent": "TECHNICAL",
    "confidence": 0.95,
    "reasoning": "Question about data structure (AVL trees)",
    "alternative_intent": null
}}

Question: "How many points do I need to pass?"
{{
    "intent": "SUPPORT",
    "confidence": 0.98,
    "reasoning": "Question about passing requirements and grading",
    "alternative_intent": null
}}

Question: "Explain how to pass the exam"
{{
    "intent": "SUPPORT",
    "confidence": 0.75,
    "reasoning": "Question about exam procedure",
    "alternative_intent": "TECHNICAL"
}}

Now classify the above question:"""
        
        return template
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse LLM JSON response"""
        
        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Validate required fields
            if "intent" not in result:
                raise ValueError("Missing 'intent' field")
            
            # Ensure confidence is float
            result["confidence"] = float(result.get("confidence", 0.5))
            
            # Ensure reasoning exists
            if "reasoning" not in result:
                result["reasoning"] = "No reasoning provided"
            
            # Validate intent value
            if result["intent"] not in ["TECHNICAL", "SUPPORT"]:
                result["intent"] = "AMBIGUOUS"
                result["confidence"] = 0.5
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Fallback parsing if JSON fails
            response_lower = response_text.lower()
            
            if "technical" in response_lower:
                intent = "TECHNICAL"
                confidence = 0.6
            elif "support" in response_lower:
                intent = "SUPPORT"
                confidence = 0.6
            else:
                intent = "AMBIGUOUS"
                confidence = 0.3
            
            return {
                "intent": intent,
                "confidence": confidence,
                "reasoning": f"Fallback parsing: {response_text[:100]}",
                "alternative_intent": None,
                "parse_error": str(e)
            }
    
    def _update_stats(self, result: Dict, latency_ms: int):
        """Update classification statistics"""
        
        self.stats["total_classifications"] += 1
        
        intent = result.get("intent", "AMBIGUOUS")
        self.stats["by_intent"][intent] = self.stats["by_intent"].get(intent, 0) + 1
        
        # Running average of confidence
        n = self.stats["total_classifications"]
        old_avg = self.stats["avg_confidence"]
        self.stats["avg_confidence"] = (old_avg * (n - 1) + result["confidence"]) / n
        
        # Running average of latency
        old_latency = self.stats["avg_latency_ms"]
        self.stats["avg_latency_ms"] = (old_latency * (n - 1) + latency_ms) / n
    
    def get_stats(self) -> Dict:
        """Get classification statistics"""
        return self.stats.copy()
    
    def print_stats(self):
        """Pretty print statistics"""
        stats = self.get_stats()
        
        print("\n" + "="*50)
        print("LLM INTENT CLASSIFIER STATISTICS")
        print("="*50)
        print(f"Total classifications: {stats['total_classifications']}")
        print(f"Average confidence: {stats['avg_confidence']:.2f}")
        print(f"Average latency: {stats['avg_latency_ms']:.0f}ms")
        print(f"\nBy intent:")
        for intent, count in stats['by_intent'].items():
            pct = (count / stats['total_classifications'] * 100) if stats['total_classifications'] > 0 else 0
            print(f"  {intent}: {count} ({pct:.1f}%)")
        print("="*50)


def test_classifier():
    """Test the LLM classifier with sample queries"""
    
    print("Testing LLM Intent Classifier...")
    
    classifier = LLMIntentClassifier()
    
    test_queries = [
        # Technical (Macedonian)
        ("Објасни AVL дрва", "mk"),
        ("Како работи quicksort?", "mk"),
        ("Што е Big O нотација?", "mk"),
        
        # Support (Macedonian)
        ("Колку поени треба за полагање?", "mk"),
        ("Дали ќе имаме лаб утре?", "mk"),
        ("Кога е испитот?", "mk"),
        
        # Ambiguous (Macedonian)
        ("Објасни како да положам", "mk"),
        ("Што треба да знам за испитот?", "mk"),
        
        # English
        ("Explain binary search trees", "en"),
        ("How many points do I need to pass?", "en"),
    ]
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    
    for query, lang in test_queries:
        result = classifier.classify(query, lang)
        
        print(f"\nQuery: \"{query}\"")
        print(f"  Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"  Reasoning: {result['reasoning']}")
        print(f"  Latency: {result['latency_ms']}ms")
        
        if result.get('alternative_intent'):
            print(f"  Alternative: {result['alternative_intent']}")
    
    classifier.print_stats()


if __name__ == "__main__":
    test_classifier()
