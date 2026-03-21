"""
Smart Chunker - Type-Aware Document Chunking

Handles different document types with appropriate strategies:
- Lecture slides: Merge related pages, preserve code blocks
- FAQ: Keep Q&A pairs intact
- Administrative: Section-based chunking
- Textbook: Paragraph-aware chunking

For DSA-RAG-FEEIT thesis project
"""

from typing import List, Dict, Optional
import re


class SmartChunker:
    """Intelligent chunking based on document type"""
    
    def __init__(self, 
                 target_chunk_size: int = 1000,
                 max_chunk_size: int = 1500,
                 min_chunk_size: int = 300):
        """
        Initialize chunker with size constraints.
        
        Args:
            target_chunk_size: Ideal chunk size in characters
            max_chunk_size: Maximum allowed chunk size
            min_chunk_size: Minimum chunk size (merge if smaller)
        """
        self.target_size = target_chunk_size
        self.max_size = max_chunk_size
        self.min_size = min_chunk_size
        
        self.stats = {
            "chunks_created": 0,
            "code_blocks_preserved": 0,
            "pages_merged": 0,
            "qa_pairs_kept": 0
        }
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Chunk documents based on their classification.
        
        Args:
            documents: List of classified documents from Phase 1
            
        Returns:
            List of optimized chunks with metadata
        """
        chunks = []
        
        # Group documents by type and source
        grouped = self._group_by_source_and_type(documents)
        
        for (source, doc_type), docs in grouped.items():
            if doc_type == "lecture_slides":
                chunks.extend(self._chunk_lecture_slides(docs, source))
            elif doc_type == "supplementary_slides":
                chunks.extend(self._chunk_supplementary_slides(docs, source))
            elif doc_type == "faq":
                chunks.extend(self._chunk_faq(docs, source))
            elif doc_type == "administrative":
                chunks.extend(self._chunk_administrative(docs, source))
            elif doc_type == "textbook":
                chunks.extend(self._chunk_textbook(docs, source))
            else:
                # Unknown type - use generic chunking
                chunks.extend(self._chunk_generic(docs, source))
        
        # Add chunk IDs and indices
        for i, chunk in enumerate(chunks):
            chunk["chunk_id"] = f"chunk_{i:04d}"
            chunk["chunk_index"] = i
        
        self.stats["chunks_created"] = len(chunks)
        
        return chunks
    
    def _group_by_source_and_type(self, documents: List[Dict]) -> Dict:
        """Group documents by source file and type"""
        from collections import defaultdict
        
        grouped = defaultdict(list)
        
        for doc in documents:
            source = doc.get('source', 'unknown')
            doc_type = doc.get('classification', {}).get('type', 'unknown')
            
            key = (source, doc_type)
            grouped[key].append(doc)
        
        return dict(grouped)
    
    def _chunk_lecture_slides(self, pages: List[Dict], source: str) -> List[Dict]:
        """
        Chunk lecture slides with code-awareness.
        
        Strategy:
        1. Merge consecutive pages if they form a logical unit
        2. Preserve complete code blocks
        3. Keep problem + solution together
        """
        # Sort by page number
        pages = sorted(pages, key=lambda p: p.get('page_number', 0))
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for i, page in enumerate(pages):
            text = page.get('text', '')
            page_size = len(text)
            
            # Check if this page should merge with current chunk
            should_merge = self._should_merge_pages(
                current_chunk, 
                page, 
                current_size + page_size
            )
            
            if should_merge and current_size + page_size <= self.max_size:
                # Merge with current chunk
                current_chunk.append(page)
                current_size += page_size
                self.stats["pages_merged"] += 1
            else:
                # Finalize current chunk
                if current_chunk:
                    chunk = self._create_slide_chunk(current_chunk, source)
                    chunks.append(chunk)
                
                # Start new chunk
                current_chunk = [page]
                current_size = page_size
        
        # Add final chunk
        if current_chunk:
            chunk = self._create_slide_chunk(current_chunk, source)
            chunks.append(chunk)
        
        return chunks
    
    def _should_merge_pages(self, current_chunk: List[Dict], 
                           next_page: Dict, 
                           combined_size: int) -> bool:
        """
        Decide if next page should merge with current chunk.
        
        Merge if:
        - Current chunk has incomplete code block
        - Next page continues the topic
        - Combined size is reasonable
        """
        if not current_chunk:
            return False
        
        if combined_size > self.max_size:
            return False
        
        last_page = current_chunk[-1]
        last_text = last_page.get('text', '')
        next_text = next_page.get('text', '')
        
        # Rule 1: If last page has incomplete code block, merge
        if self._has_incomplete_code(last_text):
            return True
        
        # Rule 2: If next page starts with code and last had problem, merge
        if self._starts_with_code(next_text) and self._looks_like_problem(last_text):
            return True
        
        # Rule 3: If both are very short, merge
        if len(last_text) < self.min_size and len(next_text) < self.min_size:
            return True
        
        # Rule 4: If current chunk is tiny, merge
        if combined_size < self.min_size * 1.5:
            return True
        
        # Rule 5: Check if next page continues same topic
        if self._continues_topic(last_text, next_text):
            return True
        
        return False
    
    def _has_incomplete_code(self, text: str) -> bool:
        """Check if text has incomplete code block"""
        # Unbalanced braces
        open_braces = text.count('{')
        close_braces = text.count('}')
        
        if open_braces != close_braces:
            return True
        
        # Incomplete method signature
        if re.search(r'(public|private|static)\s+\w+\s*\([^)]*$', text):
            return True
        
        # Code that looks truncated
        if re.search(r'for\s*\([^)]*$', text):
            return True
        
        return False
    
    def _starts_with_code(self, text: str) -> bool:
        """Check if text starts with code"""
        # Remove leading whitespace
        text = text.lstrip()
        
        code_starters = [
            r'^(public|private|protected|static)',
            r'^\w+\s+\w+\s*\(',  # method signature
            r'^\{',  # opening brace
            r'^for\s*\(',
            r'^while\s*\(',
            r'^if\s*\(',
        ]
        
        return any(re.match(pattern, text) for pattern in code_starters)
    
    def _looks_like_problem(self, text: str) -> bool:
        """Check if text looks like a problem description"""
        problem_indicators = [
            r'задача',
            r'problem',
            r'решение',
            r'solution',
            r'најдете',
            r'find',
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in problem_indicators)
    
    def _continues_topic(self, text1: str, text2: str) -> bool:
        """Check if text2 continues the topic from text1"""
        # Extract key terms from first text
        terms1 = set(re.findall(r'\b[А-Яа-яA-Za-z]{4,}\b', text1.lower()))
        terms2 = set(re.findall(r'\b[А-Яа-яA-Za-z]{4,}\b', text2.lower()))
        
        # Calculate overlap
        if not terms1 or not terms2:
            return False
        
        overlap = len(terms1 & terms2)
        overlap_ratio = overlap / min(len(terms1), len(terms2))
        
        # If >30% term overlap, likely same topic
        return overlap_ratio > 0.3
    
    def _create_slide_chunk(self, pages: List[Dict], source: str) -> Dict:
        """Create chunk from merged pages"""
        # Combine text
        texts = [p.get('text', '') for p in pages]
        combined_text = '\n\n'.join(texts)
        
        # Gather metadata
        page_numbers = [p.get('page_number') for p in pages]
        has_code = any(p.get('has_code') for p in pages)
        
        # Get classification from first page
        classification = pages[0].get('classification', {})
        
        # Track if code was preserved
        if has_code:
            if not self._has_incomplete_code(combined_text):
                self.stats["code_blocks_preserved"] += 1
        
        return {
            "text": combined_text,
            "source": source,
            "type": "lecture_chunk",
            "pages": page_numbers,
            "page_count": len(pages),
            "classification": classification,
            "metadata": {
                "has_code": has_code,
                "char_count": len(combined_text),
                "pages_merged": len(pages) > 1,
                "complete_code": has_code and not self._has_incomplete_code(combined_text)
            }
        }
    
    def _chunk_supplementary_slides(self, pages: List[Dict], source: str) -> List[Dict]:
        """Chunk supplementary slides (similar to lecture slides)"""
        return self._chunk_lecture_slides(pages, source)
    
    def _chunk_faq(self, qa_pairs: List[Dict], source: str) -> List[Dict]:
        """
        Chunk FAQ documents - keep Q&A pairs intact.
        
        Each Q&A pair becomes one chunk.
        """
        chunks = []
        
        for pair in qa_pairs:
            # Use combined text (Question + Answer)
            text = pair.get('combined_text', pair.get('text', ''))
            
            chunk = {
                "text": text,
                "source": source,
                "type": "faq_chunk",
                "classification": pair.get('classification', {}),
                "metadata": {
                    "question": pair.get('question', ''),
                    "answer": pair.get('answer', ''),
                    "pair_id": pair.get('pair_id'),
                    "char_count": len(text),
                    "is_qa_pair": True
                }
            }
            
            chunks.append(chunk)
            self.stats["qa_pairs_kept"] += 1
        
        return chunks
    
    def _chunk_administrative(self, sections: List[Dict], source: str) -> List[Dict]:
        """
        Chunk administrative documents by sections.
        
        Keep header + content together.
        """
        chunks = []
        
        for section in sections:
            header = section.get('header', '')
            content = section.get('content', section.get('text', ''))
            
            # Combine header with content if header exists
            if header:
                text = f"{header}\n\n{content}"
            else:
                text = content
            
            chunk = {
                "text": text,
                "source": source,
                "type": "admin_chunk",
                "classification": section.get('classification', {}),
                "metadata": {
                    "section_header": header,
                    "char_count": len(text)
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_textbook(self, pages: List[Dict], source: str) -> List[Dict]:
        """
        Chunk textbook pages.
        
        Use sliding window with paragraph awareness.
        """
        # For textbook, use simpler strategy
        # Just return pages as-is for now (can enhance later)
        chunks = []
        
        for page in pages:
            text = page.get('text', '')
            
            if len(text) < self.min_size:
                continue  # Skip very short pages
            
            chunk = {
                "text": text,
                "source": source,
                "type": "textbook_chunk",
                "page_number": page.get('page_number'),
                "classification": page.get('classification', {}),
                "metadata": {
                    "char_count": len(text),
                    "has_code": page.get('has_code', False)
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_generic(self, documents: List[Dict], source: str) -> List[Dict]:
        """Generic chunking for unknown types"""
        return self._chunk_textbook(documents, source)
    
    def get_stats(self) -> Dict:
        """Get chunking statistics"""
        return self.stats.copy()


if __name__ == "__main__":
    print("Smart Chunker - Phase 2")
    print("Use: SmartChunker().chunk_documents(documents)")
