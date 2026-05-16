# Save as quick_test.py
import sys
sys.path.append('src')

from ingestion.pdf_slides_parser import extract_pdf_slides

# Test one slide file
slides = extract_pdf_slides("data/raw/mk/PSAA_Auditoriski_09.pdf")

if slides:
    print("=== FIRST SLIDE ===")
    print(slides[0][:500])
    print(f"\n... ({len(slides[0])} chars total)")
    
    print("\n=== SLIDE 5 ===")
    if len(slides) > 4:
        print(slides[4][:500])
else:
    print("ERROR: No slides extracted!")