"""
Groq API Generator - Fast & Free LLM Access

Groq provides ultra-fast inference (500+ tokens/sec) with generous free tier.
Perfect for RAG applications requiring fast response times.

Get free API key: https://console.groq.com/
"""

import os
from typing import List, Dict, Optional


class GroqGenerator:
    """Generate answers using Groq API (fast & free)"""
    
    def __init__(self,
             model_name: str = "llama-3.3-70b-versatile",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3):
        """
        Initialize Groq generator.
        
        Args:
            model_name: Groq model ID
                - "llama-3.3-70b-versatile" (recommended - best quality)
                - "llama-3.1-8b-instant" (fastest)
                - "gemma2-9b-it" (lightweight)
            api_key: Groq API key
            temperature: Generation temperature (0-1)
        """
        self.model_name = model_name
        self.temperature = temperature
        
        try:
            from groq import Groq
        except ImportError:
            print("❌ groq package not installed")
            print("Install with: pip install groq")
            raise
        
        # Get API key
        key = api_key or os.getenv("GROQ_API_KEY")
        
        if not key:
            raise ValueError(
                "Groq API key required. "
                "Set GROQ_API_KEY environment variable or pass api_key parameter.\n"
                "Get free key at: https://console.groq.com/"
            )
        
        self.client = Groq(api_key=key)
        
        print(f"✓ Initialized Groq API ({self.model_name})")
        print(f"  Speed: 500+ tokens/sec")
        print(f"  Free tier: Generous limits")
        
        self.stats = {
            "total_generations": 0,
            "total_tokens": 0,
            "by_language": {"mk": 0, "en": 0}
        }
    
    def generate(self,
                 query: str,
                 context: List[Dict],
                 language: str = "mk",
                 max_tokens: int = 512) -> Dict:
        """
        Generate answer given query and context.
        
        Args:
            query: User's question
            context: List of retrieved chunks
            language: Response language ("mk" or "en")
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with answer, sources, metadata
        """
        # Build prompt
        prompt = self._build_prompt(query, context, language)
        
        # Generate with Groq
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(language)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=max_tokens,
                top_p=0.9,
                stream=False
            )
            
            answer = response.choices[0].message.content
            
            # Track stats
            self.stats["total_generations"] += 1
            self.stats["by_language"][language] += 1
            
            if hasattr(response, 'usage'):
                self.stats["total_tokens"] += response.usage.total_tokens
            
        except Exception as e:
            answer = f"Error generating response: {str(e)}"
        
        return {
            "query": query,
            "answer": answer,
            "language": language,
            "sources": self._extract_sources(context),
            "num_sources": len(context),
            "model": self.model_name
        }
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt based on language"""
        if language == "mk":
            return """Ти си помошник за предметот Податочни Структури и Анализа на Алгоритми (ПСАА).

Твоја задача е да одговориш на прашањата на студентите користејќи ја информацијата од курсот.

ВАЖНИ ПРАВИЛА:
1. Одговори САМО врз основа на дадениот контекст
2. Ако одговорот не е во контекстот, кажи дека не знаеш
3. Биди прецизен, јасен и конкретен
4. Користи примери од контекстот кога е можно
5. Наведи го изворот кога даваш специфични информации
6. Одговори на македонски јазик
7. Не измислувај информации
8. Не го наведувај професорот/ асистентот по име само кажи професорот/асистентот
9. Доколку прашањето е на македонски,дополнително интерно преведи го промптот на англиски и пребарај дополнително во англиските документи покрај мекедонските"""
        else:
            return """You are an assistant for the Data Structures and Algorithms course.

Your task is to answer student questions using information from course materials.

IMPORTANT RULES:
1. Answer ONLY based on the provided context
2. If the answer is not in the context, say you don't know
3. Be precise, clear, and specific
4. Use examples from the context when possible
5. Cite sources when giving specific information
6. Respond in English
7. Do not make up information
8. Do not mention the professor/assistant by name, just say professor/assistant
9. If the question is in English,additionally internally translate the prompt into Macedonian and search through Macedonian documents in addition to the English ones."""
    
    def _build_prompt(self, query: str, context: List[Dict], language: str) -> str:
        """Build user prompt with context"""
        # Format context
        context_text = ""
        for i, chunk in enumerate(context, 1):
            source = chunk.get("metadata", {}).get("source", "Unknown")
            text = chunk.get("text", "")
            context_text += f"\n[Извор {i}: {source}]\n{text}\n"
        
        if language == "mk":
            user_prompt = f"""Контекст од курсот:
{context_text}

Прашање на студентот: {query}

Одговори на прашањето користејќи ја информацијата од контекстот. Ако одговорот не е во контекстот, кажи дека не можеш да одговориш врз основа на достапната информација."""
        else:
            user_prompt = f"""Context from course materials:
{context_text}

Student question: {query}

Answer the question using information from the context. If the answer is not in the context, say you cannot answer based on the available information."""
        
        return user_prompt
    
    def _extract_sources(self, context: List[Dict]) -> List[str]:
        """Extract unique sources"""
        sources = set()
        for chunk in context:
            source = chunk.get("metadata", {}).get("source", "Unknown")
            sources.add(source)
        return sorted(list(sources))
    
    def get_stats(self) -> Dict:
        """Get generation statistics"""
        return self.stats.copy()


# For backward compatibility
class MistralGenerator:
    """Wrapper for Mistral API (original)"""
    
    def __init__(self, mode: str = "api", **kwargs):
        if mode == "api":
            print("⚠️  For faster free inference, consider using GroqGenerator instead")
            print("   Groq is 10x faster and has generous free tier")
        
        # Import original if needed
        from .mistral_generator import MistralGenerator as Original
        self.generator = Original(mode=mode, **kwargs)
    
    def generate(self, *args, **kwargs):
        return self.generator.generate(*args, **kwargs)
    
    def get_stats(self):
        return self.generator.get_stats()


if __name__ == "__main__":
    print("Groq Generator - Fast & Free LLM Access")
    print("\nSetup:")
    print("1. Get free API key: https://console.groq.com/")
    print("2. Set environment variable:")
    print("   $env:GROQ_API_KEY='your-key-here'")
    print("\nUsage:")
    print("   generator = GroqGenerator()")
    print("   response = generator.generate(query, context)")
