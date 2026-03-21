# CRITICAL FIXES - STEP BY STEP GUIDE

## 🔴 PHASE A: Fix Critical Issues

**Time:** 20-30 minutes total
**What we're fixing:**
1. ChromaDB corruption
2. Intent confusion bug
3. Missing English textbook embeddings

---

## 📋 PREPARATION (2 minutes)

### Step 1: Stop Streamlit
```powershell
# Press Ctrl+C in the terminal running Streamlit
```

### Step 2: Copy Files to Project

```powershell
cd ~/DSA-RAG-FEEIT

# Copy the 3 new files
cp load_all_documents.py src/ingestion/
cp rebuild_vectorstore.py .
cp smart_retriever_fixed.py src/retrieval/smart_retriever.py
```

**IMPORTANT:** The last command REPLACES your current `smart_retriever.py` with the fixed version!

---

## 🔧 FIX 1: Rebuild VectorStore (15-20 minutes)

### Why This Fixes Everything:
- ✅ Deletes corrupted ChromaDB
- ✅ Loads English textbook (from data/raw/en/)
- ✅ Creates fresh, uncorrupted embeddings
- ✅ Merges FAQ + Admin into "support" category

### Run the Rebuild:

```powershell
# Make sure English textbook is in place
ls data/raw/en/
# Should see: Data-Structures-and-Algorithms-in-Java-6th-Edition.pdf

# If not, move it there:
# mv path/to/textbook.pdf data/raw/en/

# Run rebuild script
python rebuild_vectorstore.py
```

### What You'll See:

```
==============================================
REBUILD VECTORSTORE - COMPLETE RESET
==============================================

⚠️  This will:
  1. Delete existing vectorstore (if any)
  2. Load ALL documents (mk/ + en/)
  3. Create fresh embeddings
  4. Take 5-10 minutes

Continue? (yes/no): yes

==============================================
STEP 1: Deleting old vectorstore
==============================================

🗑️  Deleting: data\vectorstore
✓ Deleted

==============================================
STEP 2: Loading and chunking documents
==============================================

📁 Processing directory: data\raw\mk
----------------------------------------------------------------------

📄 Found 19 PDF files
  [1/19] Extracting: PSAA_Auditoriski_01.pdf
      ✓ Extracted 42 pages
  ...

📝 Found 2 DOCX files
  [1/2] FAQ Parsing: Често поставувани прашања.docx
      ✓ Extracted 14 Q&A pairs
  ...

📁 Processing directory: data\raw\en
----------------------------------------------------------------------

📄 Found 1 PDF files
  [1/1] Extracting: Data-Structures-and-Algorithms-in-Java-6th-Edition.pdf
      ✓ Extracted 738 pages

==============================================
EXTRACTION SUMMARY
==============================================

Total documents: 1565

By type:
  lecture_slides: 454
  supplementary_slides: 358
  textbook: 738  ← English book!
  faq: 14
  administrative: 1

By language:
  mk: 565
  en: 738  ← English!
  mixed: 250
  unknown: 12

By source:
  Macedonian (mk/): 827
  English (en/): 738  ← English book!

==============================================
CHUNKING DOCUMENTS
==============================================

✓ Created 980 optimized chunks

Chunks by type:
  lecture_chunk: 355
  supplementary_chunk: 180
  textbook_chunk: 420  ← English chunks!
  faq_chunk: 14
  admin_chunk: 1

==============================================
STEP 3: Creating embeddings (this takes time!)
==============================================

🔧 Initializing VectorStoreManager...
✓ Loaded intfloat/multilingual-e5-base

✓ Creating collection...
✓ Collection ready: dsa_rag_test

📥 Loading chunks into vectorstore...
   Processing 980 chunks in batches of 50...
   Estimated time: 2.5 minutes

Batches: 100%|████████████| 20/20 [02:24<00:00]
✓ Loaded 980 chunks successfully

==============================================
STEP 4: Validating
==============================================

✓ Vector store created successfully!

📊 Statistics:
   Collection: dsa_rag_test
   Total documents: 980
   Embeddings created: 980
   Storage location: data\vectorstore

==============================================
STEP 5: Test Query
==============================================

🔍 Testing: AVL дрва
   ✓ Top result: PSAA_Auditoriski_06.pdf
     Similarity: 0.728
     Language: mk

🔍 Testing: Big O notation
   ✓ Top result: Data-Structures-and-Algorithms-in-Java.pdf
     Similarity: 0.685
     Language: en

🔍 Testing: Колку поени треба?
   ✓ Top result: Често поставувани прашања.docx
     Similarity: 0.669
     Language: mk

==============================================
REBUILD COMPLETE!
==============================================

✅ Your vectorstore is ready with:
   • 980 chunks
   • Macedonian + English documents
   • Fresh embeddings
   • No corruption
```

---

## ✅ FIX 2: Fixed Retriever (Already Done!)

You already copied `smart_retriever_fixed.py` → `smart_retriever.py`

### What Was Fixed:

**Before (Buggy):**
```python
# Filter persisted between queries!
filter_metadata = {"is_faq": "True"}
results = self.vsm.search(query, n_results, filter_metadata)
# Now ALL future queries are filtered to FAQ only!
```

**After (Fixed):**
```python
# Fresh filter dict each query
filter_dict = {"is_faq": "True"}
results = self.vsm.search(query, n_results, filter_metadata=filter_dict)
# Next query gets its own filter
```

---

## 🧪 VERIFY FIXES WORK (5 minutes)

### Step 1: Start Streamlit

```powershell
streamlit run streamlit_app.py
```

### Step 2: Initialize System

Click "🔄 Иницијализирај Систем" button

Should see:
```
✓ Loaded intfloat/multilingual-e5-base
✓ Collection ready: dsa_rag_test
✅ Системот е спремен!
```

### Step 3: Test Different Query Types

**Test Sequence (Important!):**

1. **Technical Query:**
   ```
   Објасни AVL дрва
   ```
   Should get slides, NOT stuck on support docs

2. **Support Query:**
   ```
   Колку поени треба за полагање?
   ```
   Should get FAQ, NOT stuck on technical

3. **Technical Again:**
   ```
   What is Big O notation?
   ```
   Should get textbook + slides (proving English works!)

4. **Support Again:**
   ```
   Дали треба лаптоп?
   ```
   Should STILL get FAQ (proving bug is fixed!)

**If ALL 4 work correctly:** ✅ Bugs are FIXED!

**If queries get stuck:** ❌ Something went wrong - share error

---

## 📊 EXPECTED RESULTS

### Before Fixes:
```
❌ Technical query → Technical answer
❌ Support query → Support answer
❌ Technical query → STUCK returning support! (BUG)
❌ English textbook NOT in results
❌ ChromaDB crashes randomly
```

### After Fixes:
```
✅ Technical query → Technical answer
✅ Support query → Support answer
✅ Technical query → Technical answer (NO STUCK!)
✅ Support query → Support answer (NO STUCK!)
✅ English textbook appears in results
✅ ChromaDB stable, no crashes
```

---

## 🐛 TROUBLESHOOTING

### Problem: "No module named 'load_all_documents'"

**Solution:**
```powershell
# Make sure you copied to correct location
cp load_all_documents.py src/ingestion/
```

### Problem: "data/raw/en not found"

**Solution:**
```powershell
# Create directory and add textbook
mkdir data/raw/en
# Move your English textbook there
mv path/to/Data-Structures-textbook.pdf data/raw/en/
```

### Problem: Rebuild fails with import error

**Solution:**
```powershell
# Make sure you're in project root
cd ~/DSA-RAG-FEEIT

# Check file structure
ls src/ingestion/
# Should see: multi_format_extractor.py, faq_parser.py, etc.
```

### Problem: Still getting stuck on wrong intent

**Solution:**
```powershell
# Verify you replaced smart_retriever.py
ls src/retrieval/smart_retriever.py

# If not, copy again:
cp smart_retriever_fixed.py src/retrieval/smart_retriever.py

# Restart Streamlit
```

---

## ✅ SUCCESS CRITERIA

You'll know everything worked if:

- [ ] Rebuild script completes without errors
- [ ] 980+ chunks in vectorstore (was 370 before)
- [ ] English textbook shows in test queries
- [ ] Can alternate between technical and support queries
- [ ] No "stuck" behavior
- [ ] No ChromaDB crashes
- [ ] Streamlit initializes successfully

---

## ⏭️ NEXT STEPS

Once these 3 critical fixes work:

1. ✅ Test thoroughly (10+ queries alternating types)
2. 📸 Take screenshots of working system
3. 📊 Record metrics (query times, accuracy)
4. ➡️ Move to **PHASE B: UX Improvements**
   - Auto-initialize
   - Auto-language detection
   - Model selector dropdown

---

**Start with the rebuild script and let me know when it completes!** 🚀
