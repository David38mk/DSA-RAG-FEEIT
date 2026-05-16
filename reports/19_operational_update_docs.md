# UPDATING DOCUMENTS & MODELS - QUICK GUIDE

## 📝 PART 1: UPDATE FAQ & COURSE INFO

### Step 1: Edit Your DOCX Files

**Location:**
```
data/raw/mk/Често поставувани прашања.docx
data/raw/mk/Podatoci_za_predmetot.docx
```

**How to Edit FAQ:**

Open `Често поставувани прашања.docx` and add new Q&A pairs in this format:

```
Мејл 15

Студент:
Професорке, дали можам да користам ChatGPT за домашни?

Одговор:
Здраво,
Не, домашните задачи мора да бидат изработени самостојно.
Поздрав,
Бојана
```

**How to Edit Course Info:**

Open `Podatoci_za_predmetot.docx` and add:
- New course policies
- Updated grading criteria
- Office hours
- Contact information
- Any administrative details

**Save files when done.**

---

### Step 2: Rebuild Vector Store

```powershell
cd ~/DSA-RAG-FEEIT

# Run rebuild script
python rebuild_vectorstore.py

# Type: yes when prompted
```

**What happens:**
```
1. Deletes old vectorstore
2. Loads UPDATED FAQ (now with your new Q&A pairs)
3. Loads UPDATED course info
4. Chunks everything fresh
5. Creates new embeddings
6. Takes ~5-10 minutes
```

**That's it!** Your new FAQ questions will be searchable.

---

### Step 3: Test New Content

```powershell
streamlit run streamlit_app.py
```

Ask your new FAQ question - it should appear in results!

---

## 🔧 PART 2: FIX DEPRECATED GROQ MODELS

### Current Working Models (March 2026):

| Model Name | Model ID | Status | Speed | Quality |
|------------|----------|--------|-------|---------|
| ✅ Llama 3.3 70B | `llama-3.3-70b-versatile` | Working | Medium | Best |
| ✅ Llama 3.1 8B | `llama-3.1-8b-instant` | Working | Fastest | Good |
| ❌ Llama 3.1 70B | `llama-3.1-70b-versatile` | **DEPRECATED** | - | - |
| ✅ Mixtral 8x7B | `mixtral-8x7b-32768` | Working | Fast | Great |
| ✅ Gemma 2 9B | `gemma2-9b-it` | Working | Fast | Good |

### Updated Model Dropdown:

**Old (had deprecated models):**
```python
[
    "Llama 3.3 70B (Best Quality)",
    "Llama 3.1 70B (Fast)",        # ← DEPRECATED!
    "Llama 3.1 8B (Fastest)",
    "Gemma 2 9B (Lightweight)"
]
```

**New (all working):**
```python
[
    "Llama 3.3 70B (Best)",
    "Llama 3.1 8B (Fast)",
    "Mixtral 8x7B (Alternative)",   # ← NEW
    "Gemma 2 9B (Lightweight)"
]
```

---

### Apply the Fix:

```powershell
# Copy updated app
cp streamlit_app_updated.py streamlit_app.py

# Restart Streamlit
# (Ctrl+C to stop, then)
streamlit run streamlit_app.py
```

**Now dropdown shows only working models!**

---

## 📊 MODEL COMPARISON (Updated)

Test same query with each model:

| Model | Speed | Quality | Recommendation |
|-------|-------|---------|----------------|
| **Llama 3.3 70B** | 700ms | ⭐⭐⭐⭐⭐ | Best for thesis demos |
| **Llama 3.1 8B** | 300ms | ⭐⭐⭐ | Fast testing |
| **Mixtral 8x7B** | 500ms | ⭐⭐⭐⭐ | Good alternative |
| **Gemma 2 9B** | 350ms | ⭐⭐⭐ | Lightweight option |

---

## ✅ COMPLETE WORKFLOW

### Updating FAQ + Fixing Models (10 minutes):

```powershell
# 1. Edit DOCX files (5 min)
# Open and edit:
data/raw/mk/Често поставувани прашања.docx
data/raw/mk/Podatoci_za_predmetot.docx
# Save changes

# 2. Copy updated app (30 sec)
cp streamlit_app_updated.py streamlit_app.py

# 3. Rebuild vectorstore (5-10 min)
python rebuild_vectorstore.py
# Type: yes

# 4. Test (2 min)
streamlit run streamlit_app.py
# Ask new FAQ question
# Try different models
```

---

## 🧪 TESTING CHECKLIST

After updates:

### Test New FAQ Content:
```
Ask one of your new FAQ questions
Expected: Answer from your updated FAQ file
```

### Test Models:
```
Select "Llama 3.3 70B" → Ask "Објасни AVL дрва"
  Expected: ~700ms, detailed answer

Select "Llama 3.1 8B" → Ask same question
  Expected: ~300ms, good answer

Select "Mixtral 8x7B" → Ask same question
  Expected: ~500ms, great answer

Select "Gemma 2 9B" → Ask same question
  Expected: ~350ms, good answer
```

### Verify No Errors:
- [ ] No "model decommissioned" errors
- [ ] All 4 models work
- [ ] FAQ content appears in search results
- [ ] Course info appears when asked about policies

---

## 📝 WHAT CHANGES WHEN YOU UPDATE DOCS

### Before Rebuild:
```
FAQ: 14 Q&A pairs
Course info: 1 section
Total chunks: 1100
```

### After Adding Content + Rebuild:
```
FAQ: 20 Q&A pairs (you added 6 new ones)
Course info: 1 section (with updated content)
Total chunks: 1106 (6 more)
```

**Your system automatically:**
- ✅ Parses new Q&A pairs
- ✅ Chunks them intelligently
- ✅ Creates embeddings
- ✅ Makes them searchable

**No code changes needed!**

---

## 🎯 SUMMARY

### To Update Documents:
1. Edit DOCX files in `data/raw/mk/`
2. Run `python rebuild_vectorstore.py`
3. Done! New content searchable

### To Fix Models:
1. Copy `streamlit_app_updated.py` → `streamlit_app.py`
2. Restart Streamlit
3. Done! All models work

### Time Required:
- Edit docs: 5-10 minutes
- Rebuild: 5-10 minutes
- Test: 2-5 minutes
- **Total: 15-25 minutes**

---

## 📞 NEED HELP?

### Problem: Rebuild fails

**Check:**
```powershell
# Make sure files exist
ls data/raw/mk/*.docx

# Should see:
# Често поставувани прашања.docx
# Podatoci_za_predmetot.docx
```

### Problem: New FAQ not appearing

**Verify:**
1. Did you save the DOCX file?
2. Did rebuild complete successfully?
3. Is the Q&A format correct? (Мејл X, Студент:, Одговор:)

### Problem: Model still says "decommissioned"

**Fix:**
```powershell
# Make sure you copied updated app
cp streamlit_app_updated.py streamlit_app.py

# Clear Streamlit cache
# Press 'C' in terminal while Streamlit running
# OR restart: Ctrl+C then streamlit run streamlit_app.py
```

---

**Edit your docs and run the rebuild!** 🚀
