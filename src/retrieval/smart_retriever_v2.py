"""
Smart Retriever - UPDATED WITH LATIN-MACEDONIAN FIX

CHANGES FROM PREVIOUS VERSION:
1. Integrated EnhancedLanguageDetector (fixes Latin-script Macedonian)
2. Added debug logging for language detection
3. Maintains all existing functionality (intent routing, filters, hybrid search)

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


class EnhancedLanguageDetector:
    """Enhanced language detection with Latin-script Macedonian support"""
    
    def __init__(self):
        # Macedonian word patterns (both Cyrillic and Latin)
        self.macedonian_patterns = {
            # Question words
            'dali': r'\b(дали|dali)\b',
            'kolku': r'\b(колку|kolku|kolko)\b',
            'shto': r'\b(што|shto|sto)\b',
            'koga': r'\b(кога|koga)\b',
            'kade': r'\b(каде|kade)\b',
            'zoshto': r'\b(зошто|zoshto|zosto)\b',
            'koj': r'\b(кој|koj)\b',
            'koja': r'\b(која|koja)\b',
            
            # Common verbs
            'ke': r'\b(ќе|ke|kje)\b',
            'ima': r'\b(има|ima)\b',
            'imame': r'\b(имаме|imame)\b',
            'treba': r'\b(треба|treba)\b',
            'moze': r'\b(може|moze|mozhe)\b',
            'mozam': r'\b(можам|mozam|mozham)\b',
            
            # Course-specific
            'lab': r'\b(лаб|lab)\b',
            'ispit': r'\b(испит|ispit)\b',
            'vezhba': r'\b(вежба|vezhba|vezhbi|вежби)\b',
            'poeni': r'\b(поени|poeni)\b',
            'polaganje': r'\b(полагање|polaganje)\b',
            'predmet': r'\b(предмет|predmet)\b',
            'proekt': r'\b(проект|proekt)\b',
            
            # Politeness
            'profesorke': r'\b(професорке|profesorke)\b',
            'blagodaram': r'\b(благодарам|blagodaram)\b',
            'izvinete': r'\b(извинете|izvinete)\b',
            
            # Particles
            'li': r'\b(ли|li)\b',
            'na': r'\b(на|na)\b',
            'od': r'\b(од|od)\b',
            'vo': r'\b(во|vo)\b',
            'za': r'\b(за|za)\b',
        }
        
        self.compiled_patterns = {
            word: re.compile(pattern, re.IGNORECASE) 
            for word, pattern in self.macedonian_patterns.items()
        }
    
    def detect_language(self, text: str) -> Tuple[str, float, dict]:
        """
        Detect language with confidence score.
        
        Returns:
            (language, confidence, debug_info)
        """
        text_lower = text.lower()
        
        # Cyrillic ratio
        cyrillic = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
        latin = len(re.findall(r'[a-zA-Z]', text))
        total_letters = cyrillic + latin
        
        cyrillic_ratio = cyrillic / total_letters if total_letters > 0 else 0.0
        
        # Macedonian word matching
        macedonian_word_count = 0
        matched_words = []
        
        for word, pattern in self.compiled_patterns.items():
            if pattern.search(text_lower):
                macedonian_word_count += 1
                matched_words.append(word)
        
        debug_info = {
            'cyrillic_ratio': cyrillic_ratio,
            'macedonian_words': macedonian_word_count,
            'matched_words': matched_words[:5]
        }
        
        # Decision logic
        if cyrillic_ratio > 0.7:
            return 'mk', 0.95, debug_info
        
        if cyrillic_ratio < 0.1 and macedonian_word_count == 0:
            return 'en', 0.90, debug_info
        
        # KEY FIX: Latin-script Macedonian
        if cyrillic_ratio < 0.3 and macedonian_word_count >= 2:
            confidence = min(0.70 + (macedonian_word_count * 0.05), 0.95)
            return 'mk', confidence, debug_info
        
        if 0.3 <= cyrillic_ratio <= 0.7:
            return 'mixed', 0.60, debug_info
        
        if macedonian_word_count == 1:
            return 'mk', 0.55, debug_info
        
        return 'mk', 0.50, debug_info
    
    def detect_language_simple(self, text: str) -> str:
        """Simple version returning only language code"""
        language, _, _ = self.detect_language(text)
        return language


class SmartRetriever:
    """
    Intelligent retrieval with query routing - UPDATED VERSION
    
    CHANGES:
    - Uses EnhancedLanguageDetector (fixes Latin-script Macedonian bug)
    - Proper filter handling (fixed intent confusion bug)
    - Added language detection debugging
    """
    
    def __init__(self, vector_store_manager):
        """
        Initialize retriever.
        
        Args:
            vector_store_manager: Instance of VectorStoreManager
        """
        self.vsm = vector_store_manager
        self.language_detector = EnhancedLanguageDetector()  # NEW!
        
        # Intent detection patterns
        self.intent_patterns = {
            QueryIntent.SUPPORT: [
                # FAQ patterns
                r'\b(дали|можам|можеме|треба|потребно)\b',
                r'\b(can i|should i|do i need)\b',
                r'\b(лаб|laboratory|лабораториски)\b',
                r'\b(испит|exam|test)\b',
                # Administrative patterns
                r'\b(поени|points|grade|оценка)\b',
                r'\b(услов|requirement|prerequisite)\b',
                r'\b(рок|deadline|датум|date)\b',
                r'\b(проект|project|homework)\b',
                r'\b(консултации|office hours)\b',
                r'\b(полагање|passing|failing)\b',
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
            "by_language": {"mk": 0, "en": 0, "mixed": 0},
            "latin_macedonian_detected": 0  # NEW STAT!
        }
    
    def detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """Detect query intent"""
        query_lower = query.lower()
        
        scores = {intent: 0 for intent in QueryIntent}
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    scores[intent] += 1
        
        max_score = max(scores.values())
        
        if max_score == 0:
            return QueryIntent.TECHNICAL, 0.5
        
        primary_intent = max(scores, key=scores.get)
        total_matches = sum(scores.values())
        confidence = scores[primary_intent] / total_matches if total_matches > 0 else 0.5
        
        if sum(1 for s in scores.values() if s > 0) > 1 and confidence < 0.7:
            return QueryIntent.MIXED, 0.5
        
        return primary_intent, confidence
    
    def detect_language(self, query: str) -> str:
        """
        Detect query language with ENHANCED DETECTOR.
        
        IMPROVEMENT: Now handles Latin-script Macedonian!
        """
        language, confidence, debug = self.language_detector.detect_language(query)
        
        # Track Latin-Macedonian detections
        if debug.get('matched_words') and confidence > 0.7:
            if debug['cyrillic_ratio'] < 0.3:
                self.stats['latin_macedonian_detected'] += 1
        
        return language
    
    def route_query(self, query: str, n_results: int = 5) -> Dict:
        """
        Route query to appropriate search strategy.
        
        FIXES APPLIED:
        1. Fresh filter dict each call (no persistence bug)
        2. Enhanced language detection (Latin-Macedonian support)
        """
        # Detect intent and language
        intent, confidence = self.detect_intent(query)
        language = self.detect_language(query)  # Uses enhanced detector!
        
        # Update stats
        self.stats["total_queries"] += 1
        self.stats["by_intent"][intent] += 1
        self.stats["by_language"][language] += 1
        
        # CRITICAL: Create fresh filter dict for EACH query
        
        if intent == QueryIntent.SUPPORT:
            # Search ONLY support docs
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
            filter_dict = {
                "doc_type": {
                    "$in": ["lecture_slides", "supplementary_slides", "textbook"]
                }
            }
            results = self.vsm.search(query, n_results, filter_metadata=filter_dict)
            strategy = "Technical content search"
            
        else:  # MIXED
            # Search all documents
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
    
    def search_technical(self, query: str, require_code: bool = False, n_results: int = 5) -> Dict:
        """Search for technical content"""
        if require_code:
            filter_dict = {"has_code": "True"}
            return self.vsm.search(query, n_results, filter_metadata=filter_dict)
        else:
            filter_dict = {
                "doc_type": {
                    "$in": ["lecture_slides", "supplementary_slides", "textbook"]
                }
            }
            return self.vsm.search(query, n_results, filter_metadata=filter_dict)
    
    def search_support(self, query: str, n_results: int = 3) -> Dict:
        """Search support documents"""
        filter_dict = {
            "$or": [
                {"is_faq": "True"},
                {"is_admin": "True"}
            ]
        }
        return self.vsm.search(query, n_results, filter_metadata=filter_dict)
    
    def search_with_code(self, query: str, n_results: int = 5) -> Dict:
        """Search only documents containing code"""
        filter_dict = {"has_code": "True"}
        return self.vsm.search(query, n_results, filter_metadata=filter_dict)
    
    def hybrid_search(self, query: str, semantic_weight: float = 0.7, n_results: int = 5) -> Dict:
        """Hybrid search combining semantic + metadata"""
        semantic_results = self.route_query(query, n_results * 2)
        
        intent, _ = self.detect_intent(query)
        language = self.detect_language(query)
        
        for result in semantic_results["results"]:
            metadata = result["metadata"]
            metadata_score = 0.0
            
            if intent == QueryIntent.SUPPORT:
                if metadata.get("is_faq") == "True" or metadata.get("is_admin") == "True":
                    metadata_score += 0.3
            elif intent == QueryIntent.TECHNICAL:
                if metadata.get("doc_type") in ["lecture_slides", "supplementary_slides", "textbook"]:
                    metadata_score += 0.2
            
            if metadata.get("language") == language:
                metadata_score += 0.1
            
            if intent == QueryIntent.TECHNICAL and metadata.get("has_code") == "True":
                metadata_score += 0.15
            
            original_similarity = result["similarity"]
            result["hybrid_score"] = (semantic_weight * original_similarity) + ((1 - semantic_weight) * metadata_score)
            result["metadata_boost"] = metadata_score
        
        semantic_results["results"].sort(key=lambda x: x["hybrid_score"], reverse=True)
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
    print("Smart Retriever - UPDATED VERSION")
    print("✓ Fixed: Latin-script Macedonian detection")
    print("✓ Fixed: Intent confusion (filter persistence)")
    print("✓ Added: Language detection debugging")
