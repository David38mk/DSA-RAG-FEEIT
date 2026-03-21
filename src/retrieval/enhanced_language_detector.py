"""
Enhanced Language Detector - Fixes Latin-Script Macedonian Bug

BUG IDENTIFIED:
Query: "Dali ke imame lab?" (Macedonian words, Latin alphabet)
Current behavior: Detects as "en" (0% Cyrillic)
Routes to: English technical documents
Result: Misses Macedonian FAQ docs

ROOT CAUSE:
Language detection only counts Cyrillic characters, ignoring word patterns.
Latin-script Macedonian (transliterated) looks like English to the detector.

SOLUTION:
Hybrid detection combining:
1. Cyrillic ratio (existing method)
2. Macedonian word patterns (new method)
3. Combined confidence scoring

For DSA-RAG-FEEIT thesis project
"""

import re
from typing import Tuple


class EnhancedLanguageDetector:
    """
    Enhanced language detection with Latin-script Macedonian support
    """
    
    def __init__(self):
        """Initialize with Macedonian word patterns"""
        
        # Common Macedonian words (both Cyrillic and Latin transliterations)
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
            'ke': r'\b(ќе|ke|kje)\b',  # will
            'ima': r'\b(има|ima)\b',   # has/have
            'imame': r'\b(имаме|imame)\b',
            'treba': r'\b(треба|treba)\b',  # need
            'moze': r'\b(може|moze|mozhe)\b',  # can
            'mozam': r'\b(можам|mozam|mozham)\b',
            
            # Course-specific terms
            'lab': r'\b(лаб|lab)\b',
            'ispit': r'\b(испит|ispit)\b',
            'vezhba': r'\b(вежба|vezhba|vezhbi|вежби)\b',
            'poeni': r'\b(поени|poeni)\b',
            'polaganje': r'\b(полагање|polaganje|polaganje)\b',
            'predmet': r'\b(предмет|predmet)\b',
            'proekt': r'\b(проект|proekt)\b',
            
            # Politeness
            'profesorke': r'\b(професорке|profesorke)\b',
            'blagodaram': r'\b(благодарам|blagodaram)\b',
            'izvinete': r'\b(извинете|izvinete)\b',
            'pochituvana': r'\b(почитувана|pochituvana)\b',
            
            # Common particles
            'li': r'\b(ли|li)\b',
            'na': r'\b(на|na)\b',
            'od': r'\b(од|od)\b',
            'vo': r'\b(во|vo)\b',
            'za': r'\b(за|za)\b',
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {
            word: re.compile(pattern, re.IGNORECASE) 
            for word, pattern in self.macedonian_patterns.items()
        }
    
    def detect_language(self, text: str) -> Tuple[str, float, dict]:
        """
        Detect language with confidence score and debug info.
        
        Args:
            text: Query text
            
        Returns:
            (language, confidence, debug_info)
            language: 'mk', 'en', or 'mixed'
            confidence: 0.0-1.0
            debug_info: {
                'cyrillic_ratio': float,
                'macedonian_words': int,
                'method': 'cyrillic' | 'word_patterns' | 'combined'
            }
        """
        text_lower = text.lower()
        
        # METHOD 1: Cyrillic character ratio (existing)
        cyrillic = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
        latin = len(re.findall(r'[a-zA-Z]', text))
        total_letters = cyrillic + latin
        
        cyrillic_ratio = cyrillic / total_letters if total_letters > 0 else 0.0
        
        # METHOD 2: Macedonian word pattern matching (new)
        macedonian_word_count = 0
        matched_words = []
        
        for word, pattern in self.compiled_patterns.items():
            if pattern.search(text_lower):
                macedonian_word_count += 1
                matched_words.append(word)
        
        # DECISION LOGIC
        debug_info = {
            'cyrillic_ratio': cyrillic_ratio,
            'macedonian_words': macedonian_word_count,
            'matched_words': matched_words,
            'total_letters': total_letters
        }
        
        # HIGH CONFIDENCE MACEDONIAN (Cyrillic text)
        if cyrillic_ratio > 0.7:
            debug_info['method'] = 'cyrillic'
            return 'mk', 0.95, debug_info
        
        # HIGH CONFIDENCE ENGLISH (No Cyrillic, no MK words)
        if cyrillic_ratio < 0.1 and macedonian_word_count == 0:
            debug_info['method'] = 'no_macedonian_indicators'
            return 'en', 0.90, debug_info
        
        # LATIN-SCRIPT MACEDONIAN DETECTED (KEY FIX!)
        if cyrillic_ratio < 0.3 and macedonian_word_count >= 2:
            # Latin alphabet but Macedonian words detected
            confidence = min(0.70 + (macedonian_word_count * 0.05), 0.95)
            debug_info['method'] = 'latin_macedonian_words'
            return 'mk', confidence, debug_info
        
        # MIXED CYRILLIC + LATIN
        if 0.3 <= cyrillic_ratio <= 0.7:
            debug_info['method'] = 'mixed_script'
            return 'mixed', 0.60, debug_info
        
        # AMBIGUOUS - Single MK word
        if macedonian_word_count == 1:
            # Weak Macedonian signal
            debug_info['method'] = 'weak_macedonian_signal'
            return 'mk', 0.55, debug_info
        
        # DEFAULT to Macedonian (conservative for Macedonian university)
        debug_info['method'] = 'default_macedonian'
        return 'mk', 0.50, debug_info
    
    def detect_language_simple(self, text: str) -> str:
        """
        Simple version for backward compatibility.
        Returns only language code.
        """
        language, _, _ = self.detect_language(text)
        return language


def test_detector():
    """Test cases demonstrating the fix"""
    detector = EnhancedLanguageDetector()
    
    test_cases = [
        # Latin-script Macedonian (THE BUG)
        ("Dali ke imame lab?", "mk", "Latin MK - question words"),
        ("Kolku poeni treba za polaganje?", "mk", "Latin MK - course terms"),
        ("Ke ima ispit?", "mk", "Latin MK - will + exam"),
        ("Moze li da se zapishi vezhba?", "mk", "Latin MK - can + exercise"),
        
        # Cyrillic Macedonian (should still work)
        ("Дали ќе имаме лаб?", "mk", "Cyrillic MK"),
        ("Колку поени треба?", "mk", "Cyrillic MK"),
        
        # English (should not be confused)
        ("What is Big O notation?", "en", "Pure English"),
        ("Explain binary search", "en", "Pure English"),
        
        # Mixed (code examples)
        ("Објасни binary search", "mixed", "Cyrillic + English term"),
        ("AVL дрво rotation", "mixed", "English + Cyrillic"),
    ]
    
    print("=" * 70)
    print("ENHANCED LANGUAGE DETECTOR - TEST RESULTS")
    print("=" * 70)
    
    correct = 0
    total = len(test_cases)
    
    for query, expected, description in test_cases:
        detected, confidence, debug = detector.detect_language(query)
        
        status = "✓" if detected == expected else "✗"
        if detected == expected:
            correct += 1
        
        print(f"\n{status} {description}")
        print(f"   Query: '{query}'")
        print(f"   Expected: {expected} | Detected: {detected} (confidence: {confidence:.2f})")
        print(f"   Method: {debug['method']}")
        if debug['matched_words']:
            print(f"   Matched MK words: {', '.join(debug['matched_words'][:5])}")
    
    print("\n" + "=" * 70)
    print(f"ACCURACY: {correct}/{total} ({correct/total*100:.1f}%)")
    print("=" * 70)


if __name__ == "__main__":
    test_detector()
