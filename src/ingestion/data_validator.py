"""
Data quality validation for extracted PDF content.

Validates:
- Text encoding (Cyrillic characters)
- Code block completeness
- Chunk size distribution
- Language detection reliability
"""

import re
from typing import List, Dict, Tuple
from collections import Counter


class DataValidator:
    """Validate extracted PDF data quality"""
    
    def __init__(self):
        self.warnings = []
        self.errors = []
    
    def validate_documents(self, documents: List[Dict]) -> Dict:
        """
        Run all validation checks on extracted documents.
        
        Returns:
            Dict with validation results and recommendations
        """
        if not documents:
            return {"error": "No documents to validate"}
        
        results = {
            "total_documents": len(documents),
            "validation_passed": True,
            "warnings": [],
            "errors": [],
            "checks": {}
        }
        
        # Run validation checks
        results["checks"]["encoding"] = self._check_encoding(documents)
        results["checks"]["completeness"] = self._check_completeness(documents)
        results["checks"]["code_quality"] = self._check_code_quality(documents)
        results["checks"]["size_distribution"] = self._check_size_distribution(documents)
        results["checks"]["duplicates"] = self._check_duplicates(documents)
        
        # Aggregate warnings and errors
        for check_name, check_result in results["checks"].items():
            if "warnings" in check_result:
                results["warnings"].extend(check_result["warnings"])
            if "errors" in check_result:
                results["errors"].extend(check_result["errors"])
        
        # Overall pass/fail
        results["validation_passed"] = len(results["errors"]) == 0
        
        return results
    
    def _check_encoding(self, documents: List[Dict]) -> Dict:
        """Check for encoding issues"""
        issues = []
        
        # Check Cyrillic rendering
        cyrillic_docs = 0
        mojibake_docs = 0
        
        for doc in documents:
            text = doc.get('text', '')
            
            # Count Cyrillic characters
            cyrillic_chars = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
            if cyrillic_chars > 10:
                cyrillic_docs += 1
            
            # Check for replacement characters (encoding failure)
            if '\ufffd' in text or '\uFFFD' in text:
                mojibake_docs += 1
                issues.append(f"Document {doc.get('source', 'unknown')} page/slide {doc.get('slide_number') or doc.get('page_number')} has encoding errors")
        
        result = {
            "cyrillic_documents": cyrillic_docs,
            "encoding_errors": mojibake_docs,
            "warnings": []
        }
        
        if mojibake_docs > 0:
            result["warnings"].append(f"{mojibake_docs} documents have encoding errors - check PDF extraction")
        
        return result
    
    def _check_completeness(self, documents: List[Dict]) -> Dict:
        """Check for empty or suspiciously short documents"""
        empty = 0
        very_short = 0
        short_docs = []
        
        for doc in documents:
            text = doc.get('text', '')
            char_count = len(text)
            
            if char_count == 0:
                empty += 1
            elif char_count < 50:
                very_short += 1
                short_docs.append({
                    "source": doc.get('source'),
                    "page": doc.get('slide_number') or doc.get('page_number'),
                    "chars": char_count,
                    "text": text[:100]
                })
        
        result = {
            "empty_documents": empty,
            "very_short_documents": very_short,
            "warnings": [],
            "errors": []
        }
        
        total = len(documents)
        empty_rate = (empty / total * 100) if total > 0 else 0
        
        if empty_rate > 10:
            result["errors"].append(f"{empty_rate:.1f}% of documents are empty - extraction likely failed")
        elif empty_rate > 2:
            result["warnings"].append(f"{empty_rate:.1f}% of documents are empty - some pages may be blank or image-only")
        
        if very_short > 0:
            result["warnings"].append(f"{very_short} documents are very short (<50 chars) - likely headers/footers")
            result["short_examples"] = short_docs[:5]  # Show first 5 examples
        
        return result
    
    def _check_code_quality(self, documents: List[Dict]) -> Dict:
        """Check code block integrity"""
        code_docs = [d for d in documents if d.get('has_code', False)]
        
        broken_code = 0
        incomplete_blocks = []
        
        for doc in code_docs:
            text = doc.get('text', '')
            
            # Check for unbalanced braces
            open_braces = text.count('{')
            close_braces = text.count('}')
            
            if open_braces != close_braces:
                broken_code += 1
                incomplete_blocks.append({
                    "source": doc.get('source'),
                    "page": doc.get('slide_number') or doc.get('page_number'),
                    "open": open_braces,
                    "close": close_braces,
                    "snippet": text[:200]
                })
            
            # Check for truncated loops/conditions
            truncated_patterns = [
                r'for\s*\([^)]*$',  # for( with no closing paren
                r'while\s*\([^)]*$',
                r'if\s*\([^)]*$',
            ]
            
            for pattern in truncated_patterns:
                if re.search(pattern, text):
                    broken_code += 1
                    break
        
        result = {
            "total_code_documents": len(code_docs),
            "broken_code_blocks": broken_code,
            "warnings": []
        }
        
        if broken_code > 0:
            result["warnings"].append(f"{broken_code} code blocks appear incomplete or broken")
            result["examples"] = incomplete_blocks[:3]
        
        return result
    
    def _check_size_distribution(self, documents: List[Dict]) -> Dict:
        """Analyze document size distribution"""
        sizes = [len(d.get('text', '')) for d in documents]
        
        if not sizes:
            return {"error": "No text to analyze"}
        
        avg_size = sum(sizes) / len(sizes)
        min_size = min(sizes)
        max_size = max(sizes)
        
        # Categorize by size
        tiny = sum(1 for s in sizes if s < 100)
        small = sum(1 for s in sizes if 100 <= s < 500)
        medium = sum(1 for s in sizes if 500 <= s < 1500)
        large = sum(1 for s in sizes if s >= 1500)
        
        result = {
            "avg_size": int(avg_size),
            "min_size": min_size,
            "max_size": max_size,
            "distribution": {
                "tiny (<100)": tiny,
                "small (100-500)": small,
                "medium (500-1500)": medium,
                "large (1500+)": large
            },
            "warnings": []
        }
        
        # Warnings
        if avg_size < 200:
            result["warnings"].append("Average document size is very small - may lose context during chunking")
        
        if tiny > len(sizes) * 0.2:
            result["warnings"].append(f"{tiny} documents are tiny (<100 chars) - consider filtering these out")
        
        return result
    
    def _check_duplicates(self, documents: List[Dict]) -> Dict:
        """Check for duplicate content"""
        # Simple hash-based duplicate detection
        text_hashes = [hash(d.get('text', '')) for d in documents]
        hash_counts = Counter(text_hashes)
        
        duplicates = sum(1 for count in hash_counts.values() if count > 1)
        duplicate_groups = sum(count - 1 for count in hash_counts.values() if count > 1)
        
        result = {
            "unique_documents": len(hash_counts),
            "duplicate_groups": duplicates,
            "total_duplicates": duplicate_groups,
            "warnings": []
        }
        
        if duplicate_groups > 0:
            dup_rate = (duplicate_groups / len(documents) * 100)
            if dup_rate > 5:
                result["warnings"].append(f"{duplicate_groups} duplicate documents found ({dup_rate:.1f}%) - check extraction logic")
        
        return result
    
    def print_report(self, validation_results: Dict):
        """Pretty print validation report"""
        print("\n" + "="*60)
        print(" DATA VALIDATION REPORT")
        print("="*60)
        
        total = validation_results.get("total_documents", 0)
        print(f"\nTotal Documents: {total}")
        print(f"Validation Status: {'✓ PASSED' if validation_results.get('validation_passed') else '✗ FAILED'}")
        
        # Errors
        errors = validation_results.get("errors", [])
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for error in errors:
                print(f"   - {error}")
        
        # Warnings
        warnings = validation_results.get("warnings", [])
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"   - {warning}")
        
        # Check details
        print(f"\n📊 CHECK DETAILS:")
        checks = validation_results.get("checks", {})
        
        if "encoding" in checks:
            enc = checks["encoding"]
            print(f"\n  Encoding:")
            print(f"    Cyrillic documents: {enc.get('cyrillic_documents', 0)}")
            print(f"    Encoding errors: {enc.get('encoding_errors', 0)}")
        
        if "completeness" in checks:
            comp = checks["completeness"]
            print(f"\n  Completeness:")
            print(f"    Empty: {comp.get('empty_documents', 0)}")
            print(f"    Very short: {comp.get('very_short_documents', 0)}")
        
        if "code_quality" in checks:
            code = checks["code_quality"]
            print(f"\n  Code Quality:")
            print(f"    Code documents: {code.get('total_code_documents', 0)}")
            print(f"    Broken blocks: {code.get('broken_code_blocks', 0)}")
        
        if "size_distribution" in checks:
            size = checks["size_distribution"]
            print(f"\n  Size Distribution:")
            print(f"    Average: {size.get('avg_size', 0)} chars")
            print(f"    Range: {size.get('min_size', 0)} - {size.get('max_size', 0)} chars")
            dist = size.get('distribution', {})
            for category, count in dist.items():
                print(f"    {category}: {count}")
        
        if "duplicates" in checks:
            dup = checks["duplicates"]
            print(f"\n  Duplicates:")
            print(f"    Unique: {dup.get('unique_documents', 0)}")
            print(f"    Duplicate groups: {dup.get('duplicate_groups', 0)}")
        
        print("\n" + "="*60)
        
        # Recommendations
        if errors or warnings:
            print("\n💡 RECOMMENDATIONS:")
            if any("encoding" in str(e).lower() for e in errors + warnings):
                print("   - Check PDF files for corruption")
                print("   - Try alternative PDF library (pdfplumber)")
            
            if any("empty" in str(e).lower() for e in errors + warnings):
                print("   - Some pages may be image-only - consider OCR")
                print("   - Check if PDFs are scanned documents")
            
            if any("code" in str(w).lower() for w in warnings):
                print("   - Code blocks may be split across pages")
                print("   - Review code extraction logic")


if __name__ == "__main__":
    print("Data Validator - Testing...")
    print("This is a library module. Import and use DataValidator class")
