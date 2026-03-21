"""
FAQ Parser - Extracts Question-Answer Pairs

Specifically designed for "Често поставувани прашања.docx"
Preserves Q&A structure for optimal RAG retrieval.

Structure expected:
Мејл 1
Q: [question text]
A: [answer text]

Мејл 2
Q: [question text]
A: [answer text]
"""

import re
from typing import List, Dict, Tuple, Optional


class FAQParser:
    """Parse FAQ documents into Q&A pairs"""
    
    def __init__(self):
        self.qa_pairs = []
    
    def parse_faq_document(self, content: str, source: str) -> List[Dict]:
        """
        Parse FAQ document into Q&A pairs.
        
        Args:
            content: Full document text
            source: Source filename
            
        Returns:
            List of Q&A pair dicts
        """
        # Split into email sections
        # Pattern: "Мејл N" or "N." or numbered sections
        sections = self._split_into_emails(content)
        
        qa_pairs = []
        
        for i, section in enumerate(sections, 1):
            pair = self._extract_qa_pair(section, source, i)
            if pair:
                qa_pairs.append(pair)
        
        return qa_pairs
    
    def _split_into_emails(self, content: str) -> List[str]:
        """Split document into individual email sections"""
        # Try multiple splitting strategies
        
        # Strategy 1: "Мејл N" pattern
        sections = re.split(r'\n\s*Мејл\s+\d+', content, flags=re.IGNORECASE)
        
        # Strategy 2: Numbered list "1.", "2.", etc at start of line
        if len(sections) <= 1:
            sections = re.split(r'\n\s*\d+\.\s+', content)
        
        # Strategy 3: Double newline separation (fallback)
        if len(sections) <= 1:
            sections = re.split(r'\n\n\n+', content)
        
        # Clean and filter
        sections = [s.strip() for s in sections if s.strip()]
        
        # Remove header/preamble (first section if very short)
        if sections and len(sections[0]) < 100:
            sections = sections[1:]
        
        return sections
    
    def _extract_qa_pair(self, section: str, source: str, pair_id: int) -> Optional[Dict]:
        """Extract question and answer from a section"""
        # Clean section
        section = section.strip()
        
        if len(section) < 20:  # Too short to be meaningful
            return None
        
        # Try to find question and answer
        question, answer = self._identify_qa(section)
        
        if not question or not answer:
            # If can't split, treat entire section as Q&A combined
            return {
                "type": "faq",
                "pair_id": pair_id,
                "question": self._extract_question_heuristic(section),
                "answer": section,  # Full section as answer
                "combined_text": section,
                "source": source,
                "char_count": len(section),
                "language": "mk"  # FAQ is in Macedonian
            }
        
        # Successfully extracted Q&A
        combined = f"Прашање: {question}\n\nОдговор: {answer}"
        
        return {
            "type": "faq",
            "pair_id": pair_id,
            "question": question,
            "answer": answer,
            "combined_text": combined,
            "source": source,
            "char_count": len(combined),
            "language": "mk"
        }
    
    def _identify_qa(self, text: str) -> Tuple[str, str]:
        """Identify question and answer in text"""
        # Strategy: Split at professor's greeting (more reliable)
        # Professor always starts with: Здраво, Поздрав,
        # Student may say: Ви благодарам, Со почит (these are NOT answers)
        
        # Find the FIRST occurrence of professor greeting
        professor_greeting_pattern = r'\n\s*(Здраво,|Поздрав,)'
        match = re.search(professor_greeting_pattern, text, re.IGNORECASE)
        
        if match:
            # Split at professor's greeting
            question = text[:match.start()].strip()
            answer = text[match.start():].strip()
            return question, answer
        
        # Fallback: Try to find answer section by common patterns
        # Look for lines that start responses
        lines = text.split('\n')
        split_index = -1
        
        for i, line in enumerate(lines):
            line_clean = line.strip().lower()
            # These patterns indicate START of professor's response
            if (line_clean.startswith('здраво') or 
                line_clean.startswith('поздрав') or
                (i > 0 and len(lines[i-1].strip()) < 10 and line_clean.startswith('за секоја'))):
                split_index = i
                break
        
        if split_index > 0:
            question = '\n'.join(lines[:split_index]).strip()
            answer = '\n'.join(lines[split_index:]).strip()
            return question, answer
        
        # Last resort: return empty answer (will be handled upstream)
        return text, ""
    
    def _extract_question_heuristic(self, text: str) -> str:
        """Extract most likely question from text"""
        # Find sentences ending with ?
        questions = re.findall(r'[^.!?]*\?', text)
        
        if questions:
            # Return first question
            return questions[0].strip()
        
        # Fallback: first sentence or paragraph
        sentences = re.split(r'[.!?]\s+', text)
        if sentences:
            return sentences[0].strip()
        
        # Last resort: first 200 chars
        return text[:200].strip() + "..."
    
    def create_searchable_variants(self, qa_pair: Dict) -> List[Dict]:
        """
        Create multiple search variants of Q&A pair.
        
        For better retrieval, we create:
        1. Question-only chunk (for question matching)
        2. Answer-only chunk (for answer content matching)
        3. Combined Q&A chunk (for full context)
        """
        base = {
            "type": "faq",
            "source": qa_pair["source"],
            "pair_id": qa_pair["pair_id"],
            "language": "mk"
        }
        
        variants = []
        
        # Variant 1: Question-focused
        variants.append({
            **base,
            "variant": "question",
            "text": f"Прашање: {qa_pair['question']}",
            "metadata": {"answer_ref": qa_pair["pair_id"]}
        })
        
        # Variant 2: Answer-focused
        variants.append({
            **base,
            "variant": "answer",
            "text": f"Одговор на прашање {qa_pair['pair_id']}: {qa_pair['answer']}",
            "metadata": {"question_ref": qa_pair["pair_id"]}
        })
        
        # Variant 3: Combined (best for most cases)
        variants.append({
            **base,
            "variant": "combined",
            "text": qa_pair["combined_text"],
            "metadata": {"complete_pair": True}
        })
        
        return variants


def parse_faq_file(file_path: str) -> List[Dict]:
    """
    Convenience function to parse FAQ file.
    
    Args:
        file_path: Path to FAQ DOCX file
        
    Returns:
        List of Q&A pair dicts
    """
    from .multi_format_extractor import MultiFormatExtractor
    from pathlib import Path
    
    extractor = MultiFormatExtractor()
    docs = extractor.extract_document(file_path)
    
    if not docs or docs[0].get('error'):
        return docs
    
    # Combine all sections
    full_text = '\n\n'.join(doc.get('content', doc.get('text', '')) for doc in docs)
    
    parser = FAQParser()
    qa_pairs = parser.parse_faq_document(full_text, Path(file_path).name)
    
    return qa_pairs


if __name__ == "__main__":
    print("FAQ Parser")
    print("Use: parse_faq_file('path/to/faq.docx')")
    
    # Test with sample text
    sample = """
    Мејл 1
    Професорке,
    Би сакала да Ве прашам дали утре ќе имаме лабораториски по ПСАА?
    
    Здраво,
    За секоја лабораториска вежба добивате соопштение.
    Поздрав, Бојана
    
    Мејл 2
    Би сакала да прашам дали ќе биде потребно повторно да ги обработувам лабораториските вежби?
    
    Здраво, Не треба.
    """
    
    parser = FAQParser()
    pairs = parser.parse_faq_document(sample, "test.docx")
    
    print(f"\nExtracted {len(pairs)} Q&A pairs:")
    for pair in pairs:
        print(f"\nQ: {pair['question'][:100]}...")
        print(f"A: {pair['answer'][:100]}...")
