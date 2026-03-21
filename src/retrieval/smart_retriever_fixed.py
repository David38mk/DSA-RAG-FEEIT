"""
Smart Retriever - FIXED VERSION

Critical Fix: Proper filter handling to prevent intent confusion
- Each query gets fresh filter dict
- No state persistence between queries
- Proper metadata reset

For DSA-RAG-FEEIT thesis project
"""

import re
from typing import List, Dict, Optional, Tuple
from enum import Enum


class QueryIntent(Enum):
    """Query intent categories"""
    TECHNICAL = "technical"
    SUPPORT = "support"      # Combined FAQ + Administrative
    MIXED = "mixed"


class SmartRetriever:
    """Intelligent retrieval with query routing - FIXED"""
    
    def __init__(self, vector_store_manager):
        """
        Initialize retriever.
        
        Args:
            vector_store_manager: Instance of VectorStoreManager
        """
        self.vsm = vector_store_manager
        
        # Intent detection patterns
        self.intent_patterns = {
            QueryIntent.SUPPORT: [
                # FAQ patterns
                r'\b(дали|можам|можеме|треба|потребно|need)\b',
                r'\b(can i|should i|do i need|how many)\b',
                r'\b(лаб|laboratory|лабораториски)\b',
                r'\b(испит|exam|test)\b',
                # Administrative patterns
                r'\b(поени|points|grade|оценка)\b',
                r'\b(услов|requirement|prerequisite)\b',
                r'\b(рок|deadline|датум|date)\b',
                r'\b(проект|project|homework)\b',
                r'\b(консултации|office hours|consults)\b',
                r'\b(полагање|passing|failing)\b',
                r'\b(материјал|material)\b',
            ],
            QueryIntent.TECHNICAL: [
                r'\b(алгоритам|algorithm)\b',
                r'\b(complexity|комплексност|O\()\b',
                r'\b(дрво|tree|граф|graph)\b',
                r'\b(сортирање|sorting|search|пребарување)\b',
                r'\b(stack|queue|list|листа|низа|array)\b',
                r'\b(hash|хеш)\b',
                r'\b(recursion|рекурзија)\b',
                r'\b(divide and conquer|greedy|dynamic)\b',
            ]
        }
        
        self.stats = {
            "total_queries": 0,
            "by_intent": {intent: 0 for intent in QueryIntent},
            "by_language": {"mk": 0, "en": 0, "mixed": 0}
        }
    
    def detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Detect query intent.
        
        Returns:
            (intent, confidence)
        """
        query_lower = query.lower()
        
        scores = {intent: 0 for intent in QueryIntent}
        
        # Score each intent
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    scores[intent] += 1
        
        # Determine primary intent
        max_score = max(scores.values())
        
        if max_score == 0:
            return QueryIntent.TECHNICAL, 0.5  # Default to technical
        
        # Get intent with highest score
        primary_intent = max(scores, key=scores.get)
        
        # Calculate confidence
        total_matches = sum(scores.values())
        confidence = scores[primary_intent] / total_matches if total_matches > 0 else 0.5
        
        # If multiple intents, mark as MIXED
        if sum(1 for s in scores.values() if s > 0) > 1 and confidence < 0.7:
            return QueryIntent.MIXED, 0.5
        
        return primary_intent, confidence
    
    def detect_language(self, query: str) -> str:
        """
        Detect query language.
        
        Returns:
            'mk', 'en', or 'mixed'
        """
        # Count Cyrillic vs Latin
        cyrillic = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', query))
        latin = len(re.findall(r'[a-zA-Z]', query))
        
        total = cyrillic + latin
        
        if total == 0:
            return "en"
        
        cyrillic_ratio = cyrillic / total
        
        if cyrillic_ratio > 0.7:
            return "mk"
        elif cyrillic_ratio < 0.3:
            return "en"
        else:
            return "mixed"
    
    def route_query(self, query: str, n_results: int = 5) -> Dict:
        """
        Route query to appropriate search strategy.
        
        CRITICAL FIX: Creates fresh filter dict for each query
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            Search results with routing info
        """
        # Detect intent and language
        intent, confidence = self.detect_intent(query)
        language = self.detect_language(query)
        
        # Update stats
        self.stats["total_queries"] += 1
        self.stats["by_intent"][intent] += 1
        self.stats["by_language"][language] += 1
        
        # CRITICAL FIX: Create fresh filter dict for EACH query
        # This prevents filter persistence bugs
        
        if intent == QueryIntent.SUPPORT:
            # Search ONLY support docs (FAQ + admin)
            # Create NEW dict every time
            filter_dict = {
                "$or": [
                    {"is_faq": "True"},
                    {"is_admin": "True"}
                ]
            }
            results = self.vsm.search(query, n_results, filter_metadata=filter_dict)
            strategy = "Support search (FAQ + Admin)"
            
        elif intent == QueryIntent.TECHNICAL:
            # Search technical content ONLY
            # Create NEW dict every time
            filter_dict = {
                "doc_type": {
                    "$in": ["lecture_slides", "supplementary_slides", "textbook"]
                }
            }
            results = self.vsm.search(query, n_results, filter_metadata=filter_dict)
            strategy = "Technical content search"
            
        else:  # MIXED
            # Search all documents - NO filter
            # Pass None explicitly
            results = self.vsm.search(query, n_results, filter_metadata=None)
            strategy = "General search"
        
        # Add routing metadata
        results["routing"] = {
            "intent": intent.value,
            "intent_confidence": confidence,
            "language": language,
            "strategy": strategy
        }
        
        return results
    
    def search_technical(self, 
                        query: str, 
                        require_code: bool = False,
                        n_results: int = 5) -> Dict:
        """Search for technical content."""
        if require_code:
            # Create fresh filter
            filter_dict = {"has_code": "True"}
            return self.vsm.search(query, n_results, filter_metadata=filter_dict)
        else:
            # Create fresh filter
            filter_dict = {
                "doc_type": {
                    "$in": ["lecture_slides", "supplementary_slides", "textbook"]
                }
            }
            return self.vsm.search(query, n_results, filter_metadata=filter_dict)
    
    def search_support(self, query: str, n_results: int = 3) -> Dict:
        """Search support documents (FAQ + admin)"""
        # Create fresh filter
        filter_dict = {
            "$or": [
                {"is_faq": "True"},
                {"is_admin": "True"}
            ]
        }
        return self.vsm.search(query, n_results, filter_metadata=filter_dict)
    
    def search_with_code(self, query: str, n_results: int = 5) -> Dict:
        """Search only documents containing code"""
        # Create fresh filter
        filter_dict = {"has_code": "True"}
        return self.vsm.search(query, n_results, filter_metadata=filter_dict)
    
    def hybrid_search(self, 
                     query: str,
                     semantic_weight: float = 0.7,
                     n_results: int = 5) -> Dict:
        """
        Hybrid search combining semantic + metadata.
        
        Args:
            query: Search query
            semantic_weight: Weight for semantic similarity (0-1)
            n_results: Number of results
        """
        # Get semantic results
        semantic_results = self.route_query(query, n_results * 2)
        
        # Re-rank based on metadata relevance
        intent, _ = self.detect_intent(query)
        language = self.detect_language(query)
        
        for result in semantic_results["results"]:
            metadata = result["metadata"]
            
            # Boost score based on intent match
            metadata_score = 0.0
            
            if intent == QueryIntent.SUPPORT:
                if metadata.get("is_faq") == "True" or metadata.get("is_admin") == "True":
                    metadata_score += 0.3
            elif intent == QueryIntent.TECHNICAL:
                if metadata.get("doc_type") in ["lecture_slides", "supplementary_slides", "textbook"]:
                    metadata_score += 0.2
            
            # Language match boost
            if metadata.get("language") == language:
                metadata_score += 0.1
            
            # Code presence boost for technical queries
            if intent == QueryIntent.TECHNICAL and metadata.get("has_code") == "True":
                metadata_score += 0.15
            
            # Combine scores
            original_similarity = result["similarity"]
            result["hybrid_score"] = (semantic_weight * original_similarity) + ((1 - semantic_weight) * metadata_score)
            result["metadata_boost"] = metadata_score
        
        # Re-sort by hybrid score
        semantic_results["results"].sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        # Take top n
        semantic_results["results"] = semantic_results["results"][:n_results]
        semantic_results["search_type"] = "hybrid"
        semantic_results["semantic_weight"] = semantic_weight
        
        return semantic_results
    
    def get_stats(self) -> Dict:
        """Get retrieval statistics"""
        return self.stats.copy()
    
    def print_results(self, results: Dict, max_chars: int = 200):
        """Pretty print search results"""
        print(f"\n🔍 Query: {results['query']}")
        
        if "routing" in results:
            routing = results["routing"]
            print(f"   Intent: {routing['intent']} (confidence: {routing['intent_confidence']:.2f})")
            print(f"   Language: {routing['language']}")
            print(f"   Strategy: {routing['strategy']}")
        
        print(f"\n📊 Found {results['n_results']} results:\n")
        
        for i, result in enumerate(results["results"], 1):
            metadata = result["metadata"]
            
            print(f"--- Result {i} ---")
            print(f"Source: {metadata['source']}")
            print(f"Type: {metadata['doc_type']}")
            print(f"Language: {metadata['language']}")
            print(f"Similarity: {result['similarity']:.3f}")
            
            if "hybrid_score" in result:
                print(f"Hybrid Score: {result['hybrid_score']:.3f}")
            
            print(f"\nText preview:")
            text = result["text"][:max_chars]
            print(f"{text}...")
            print()


if __name__ == "__main__":
    print("Smart Retriever - FIXED VERSION")
    print("Critical fix: Proper filter handling to prevent intent confusion")
