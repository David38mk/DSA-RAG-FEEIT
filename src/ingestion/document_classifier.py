"""
Document Classifier - Categorizes documents by type and purpose

Classifies into:
- lecture_slides: Main course material
- supplementary_slides: Optional/deep-dive topics  
- administrative: Course policies, grading, logistics
- faq: Q&A pairs
- textbook: Reference book

This enables intelligent query routing in the RAG system.
"""

import re
from typing import Dict, List
from pathlib import Path


class DocumentClassifier:
    """Classify documents by type and purpose"""
    
    def __init__(self):
        # Define classification rules
        self.filename_patterns = {
            "lecture_slides": [
                r"PSAA_Auditoriski_\d+\.pdf",
                r"Auditoriski.*\.pdf",
            ],
            "supplementary_slides": [
                r"\[PSAA\]\s*#\d+\s*-.*\.pdf",
                r"PSAA.*optional.*\.pdf",
            ],
            "faq": [
                r"(?i)(често|frequently|faq|прашања|questions)",
            ],
            "administrative": [
                r"(?i)(податоци|информации|syllabus|course.*info|план)",
            ],
            "textbook": [
                r"(?i)(data.*structures|algorithms|учебник|книга|book)",
            ]
        }
        
        self.content_patterns = {
            "faq": [
                r"(?i)(мејл|email|прашање|question|одговор|answer)",
                r"професорке",
                r"здраво.*поздрав",
            ],
            "administrative": [
                r"(?i)(организација.*настава|полагање|бодови|поени)",
                r"(?i)(услов|prerequisite|консултации|office.*hour)",
                r"(?i)(испит|exam|оценување|грејд)",
            ],
            "code_heavy": [
                r"(for|while|if)\s*\(",
                r"public\s+class",
                r"\{[^}]{20,}\}",
            ]
        }
    
    def classify_document(self, doc: Dict) -> Dict:
        """
        Classify a single document.
        
        Args:
            doc: Document dict with 'source', 'text'/'content', etc.
            
        Returns:
            Enhanced doc dict with classification metadata
        """
        filename = doc.get('source', '')
        text = doc.get('text') or doc.get('content', '')
        
        # Classify by filename first (most reliable)
        doc_type = self._classify_by_filename(filename)
        
        # If unclear, use content
        if doc_type == "unknown":
            doc_type = self._classify_by_content(text, filename)
        
        # Determine domain
        domain = self._determine_domain(doc_type, text)
        
        # Detect language
        language = self._detect_language(text, filename)
        
        # Assess content characteristics
        characteristics = self._analyze_characteristics(text)
        
        # Add classification metadata
        doc["classification"] = {
            "type": doc_type,
            "domain": domain,
            "language": language,
            **characteristics
        }
        
        # Add retrieval priority (higher = more relevant for typical queries)
        doc["retrieval_priority"] = self._get_retrieval_priority(doc_type)
        
        return doc
    
    def _classify_by_filename(self, filename: str) -> str:
        """Classify based on filename patterns"""
        for doc_type, patterns in self.filename_patterns.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    return doc_type
        
        return "unknown"
    
    def _classify_by_content(self, text: str, filename: str) -> str:
        """Classify based on content patterns"""
        # Check FAQ patterns
        faq_score = sum(
            bool(re.search(pattern, text))
            for pattern in self.content_patterns["faq"]
        )
        if faq_score >= 2:
            return "faq"
        
        # Check administrative patterns
        admin_score = sum(
            bool(re.search(pattern, text))
            for pattern in self.content_patterns["administrative"]
        )
        if admin_score >= 2:
            return "administrative"
        
        # Check if it's a textbook
        if len(text) > 2000 and "algorithm" in text.lower():
            return "textbook"
        
        # Default to slides if has typical slide length
        if 200 < len(text) < 2000:
            return "lecture_slides"
        
        return "unknown"
    
    def _determine_domain(self, doc_type: str, text: str) -> str:
        """Determine the domain/purpose of document"""
        domain_map = {
            "lecture_slides": "academic_content",
            "supplementary_slides": "academic_content",
            "textbook": "academic_reference",
            "administrative": "course_policy",
            "faq": "student_support",
        }
        
        return domain_map.get(doc_type, "general")
    
    def _detect_language(self, text: str, filename: str) -> str:
        """Detect document language"""
        # Check Cyrillic characters
        cyrillic_chars = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        
        total_alpha = cyrillic_chars + latin_chars
        
        if total_alpha == 0:
            return "unknown"
        
        cyrillic_ratio = cyrillic_chars / total_alpha
        
        # Threshold: >60% Cyrillic = Macedonian
        if cyrillic_ratio > 0.6:
            return "mk"
        elif cyrillic_ratio < 0.2:
            return "en"
        else:
            return "mixed"  # Mixed language document
    
    def _analyze_characteristics(self, text: str) -> Dict:
        """Analyze content characteristics"""
        return {
            "has_code": self._has_code(text),
            "has_math": self._has_math(text),
            "has_urls": self._has_urls(text),
            "has_lists": self._has_lists(text),
            "char_count": len(text),
            "word_count": len(text.split()),
        }
    
    def _has_code(self, text: str) -> bool:
        """Check if text contains code"""
        code_patterns = self.content_patterns["code_heavy"]
        return any(re.search(pattern, text) for pattern in code_patterns)
    
    def _has_math(self, text: str) -> bool:
        """Check if text contains mathematical notation"""
        math_patterns = [
            r'O\([^)]+\)',  # Big-O notation
            r'\d+\s*[+\-*/]\s*\d+',  # Math expressions
            r'[≤≥≠∈∉∪∩]',  # Math symbols
            r'\b(log|sqrt|sum|product)\b',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in math_patterns)
    
    def _has_urls(self, text: str) -> bool:
        """Check if text contains URLs"""
        return bool(re.search(r'https?://[^\s]+', text))
    
    def _has_lists(self, text: str) -> bool:
        """Check if text contains bullet points or numbered lists"""
        list_patterns = [
            r'\n\s*[•➢▪\-]\s+',  # Bullet points
            r'\n\s*\d+[\.)]\s+',  # Numbered lists
        ]
        return any(re.search(pattern, text) for pattern in list_patterns)
    
    def _get_retrieval_priority(self, doc_type: str) -> int:
        """
        Assign retrieval priority score.
        
        Higher priority = more likely to be relevant for queries
        1 = lowest, 5 = highest
        """
        priority_map = {
            "lecture_slides": 5,        # Primary course material
            "supplementary_slides": 4,   # Additional depth
            "textbook": 3,               # Reference material
            "faq": 5,                    # For admin/policy questions
            "administrative": 4,         # Course policies
            "unknown": 2,
        }
        
        return priority_map.get(doc_type, 2)
    
    def classify_batch(self, documents: List[Dict]) -> List[Dict]:
        """Classify multiple documents"""
        return [self.classify_document(doc) for doc in documents]
    
    def get_classification_report(self, documents: List[Dict]) -> Dict:
        """Generate classification statistics"""
        from collections import Counter
        
        types = Counter(d["classification"]["type"] for d in documents if "classification" in d)
        domains = Counter(d["classification"]["domain"] for d in documents if "classification" in d)
        languages = Counter(d["classification"]["language"] for d in documents if "classification" in d)
        
        code_docs = sum(1 for d in documents if d.get("classification", {}).get("has_code"))
        math_docs = sum(1 for d in documents if d.get("classification", {}).get("has_math"))
        
        return {
            "total_documents": len(documents),
            "by_type": dict(types),
            "by_domain": dict(domains),
            "by_language": dict(languages),
            "code_containing": code_docs,
            "math_containing": math_docs,
        }


def classify_document(doc: Dict) -> Dict:
    """Convenience function to classify single document"""
    classifier = DocumentClassifier()
    return classifier.classify_document(doc)


def classify_documents(docs: List[Dict]) -> List[Dict]:
    """Convenience function to classify multiple documents"""
    classifier = DocumentClassifier()
    return classifier.classify_batch(docs)


if __name__ == "__main__":
    print("Document Classifier")
    print("Use: classify_document(doc) or classify_documents(docs)")
    
    # Test samples
    test_docs = [
        {
            "source": "PSAA_Auditoriski_05.pdf",
            "text": "Бинарно дрво for(int i=0; i<n; i++) { ... }",
        },
        {
            "source": "Често поставувани прашања.docx",
            "text": "Мејл 1: Професорке, дали утре имаме лаб? Здраво, не. Поздрав.",
        },
        {
            "source": "Податоци_за_предметот.docx",
            "text": "Организација на настава. Полагање: 50 поени",
        }
    ]
    
    classifier = DocumentClassifier()
    
    for doc in test_docs:
        classified = classifier.classify_document(doc)
        print(f"\n{classified['source']}")
        print(f"  Type: {classified['classification']['type']}")
        print(f"  Domain: {classified['classification']['domain']}")
        print(f"  Language: {classified['classification']['language']}")
        print(f"  Priority: {classified['retrieval_priority']}")
