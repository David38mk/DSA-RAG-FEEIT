"""
Mistral LLM Generator - Answer Generation

Supports:
- Mistral API (cloud)
- Local Mistral models (Ollama)
- Prompt engineering for DSA domain
- Macedonian + English responses

For DSA-RAG-FEEIT thesis project
"""

from typing import List, Dict, Optional
import os


class MistralGenerator:
    """Generate answers using Mistral LLM"""
    
    def __init__(self, 
                 mode: str = "api",
                 api_key: Optional[str] = None,
                 model_name: str = "mistral:latest",
                 temperature: float = 0.3,
                 max_tokens: int = 1000):
        """
        Initialize Mistral generator.
        
        Args:
            mode: "api" for Mistral API, "local" for Ollama
            api_key: Mistral API key (required for API mode)
            model_name: Model to use
            temperature: Generation temperature (0-1)
            max_tokens: Max tokens in response
        """
        self.mode = mode
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if mode == "api":
            self._init_api(api_key)
        elif mode == "local":
            self._init_local()
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'api' or 'local'")
        
        self.stats = {"queries_processed": 0, "tokens_used": 0, "errors": 0}
    
    def _init_api(self, api_key: Optional[str]):
        """Initialize Mistral API client"""
        try:
            from mistralai import Mistral
            
            self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
            
            if not self.api_key:
                print("⚠️  No Mistral API key provided!")
                print("   Set MISTRAL_API_KEY environment variable")
                print("   Or pass api_key parameter")
                print("   Get key at: https://console.mistral.ai/")
                raise ValueError("Mistral API key required")
            
            self.client = Mistral(api_key=self.api_key)
            print(f"✓ Mistral API initialized (model: {self.model_name})")
            
        except ImportError:
            print("❌ mistralai package not installed")
            print("   Install: pip install mistralai")
            raise
    
    def _init_local(self):
        """Initialize local Ollama client"""
        try:
            import ollama
            self.client = ollama
            print(f"✓ Ollama connected (model: {self.model_name})")
                
        except ImportError:
            print("❌ ollama package not installed")
            print("   Install: pip install ollama")
            raise
    
    def generate(self, query: str, context: List[Dict]) -> Dict:
        """
        Generate answer from query and context.
        
        Args:
            query: User query
            context: Retrieved chunks
            
        Returns:
            Dict with answer, sources, metadata
        """
        context_text = self._format_context(context)
        prompt = self._build_prompt(query, context_text)
        
        try:
            if self.mode == "api":
                response = self._generate_api(prompt)
            else:
                response = self._generate_local(prompt)
            
            self.stats["queries_processed"] += 1
            
            return {
                "query": query,
                "answer": response["text"],
                "model": self.model_name,
                "sources": self._extract_sources(context),
                "metadata": {
                    "tokens_used": response.get("tokens", 0),
                    "context_chunks": len(context)
                }
            }
            
        except Exception as e:
            self.stats["errors"] += 1
            return {
                "query": query,
                "answer": f"Error: {str(e)}",
                "error": str(e),
                "sources": []
            }
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format retrieved chunks"""
        if not context:
            return "No context found."
        
        formatted = []
        for i, chunk in enumerate(context, 1):
            text = chunk.get('text', chunk.get('document', ''))
            source = chunk.get('metadata', {}).get('source', 'Unknown')
            formatted.append(f"[{i}. {source}]\n{text}\n")
        
        return "\n".join(formatted)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build complete prompt"""
        is_mk = any(c in query for c in 'абвгдежзијклмнопрстуфхцчџш')
        lang = "Одговори на македонски." if is_mk else "Answer in English."
        
        return f"""You are a DSA teaching assistant.

{lang}

Context:
{context}

Question: {query}

Answer (be concise, cite sources):"""
    
    def _generate_api(self, prompt: str) -> Dict:
        """Generate using Mistral API"""
        response = self.client.chat.complete(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return {
            "text": response.choices[0].message.content,
            "tokens": getattr(response.usage, 'total_tokens', 0)
        }
    
    def _generate_local(self, prompt: str) -> Dict:
        """Generate using Ollama"""
        response = self.client.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": self.temperature}
        )
        
        return {"text": response['message']['content'], "tokens": 0}
    
    def _extract_sources(self, context: List[Dict]) -> List[str]:
        """Extract unique sources"""
        sources = []
        seen = set()
        
        for chunk in context:
            source = chunk.get('metadata', {}).get('source', 'Unknown')
            if source not in seen:
                sources.append(source)
                seen.add(source)
        
        return sources


if __name__ == "__main__":
    print("Mistral Generator - Phase 4")
