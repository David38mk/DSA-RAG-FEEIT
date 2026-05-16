"""
Streamlit Chat Interface - IMPROVED VERSION

Phase B Improvements:
- Auto-initialization (no button click)
- Auto-language detection (query-based)
- Model selector dropdown (choose LLM)
- Cleaner UI
- Better error handling

Run: streamlit run streamlit_app_v2.py
"""

import streamlit as st
import re

from src.llm.conversation_memory import ConversationMemory

# Page config
st.set_page_config(
    page_title="ПСАА Асистент — ФЕИТ",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS — slate dark academic theme
st.markdown("""
<style>
    /* ── Page and sidebar background ── */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] { background-color: #1e293b !important; }

    [data-testid="stSidebar"] { background-color: #162032 !important; }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p { color: #cbd5e1 !important; }

    /* ── Global text ── */
    .stMarkdown, p, div { color: #e2e8f0; }

    /* ── Header ── */
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f1f5f9;
        text-align: center;
        margin-bottom: 0.25rem;
        letter-spacing: -0.5px;
    }
    .main-subheader {
        text-align: center;
        color: #94a3b8;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }

    /* ── Chat messages ── */
    .chat-message {
        padding: 1rem 1.2rem;
        border-radius: 0.5rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid;
        color: #f1f5f9 !important;
        line-height: 1.65;
    }
    .user-message {
        background-color: #2d3f55;
        border-left-color: #38bdf8;
    }
    .assistant-message {
        background-color: #334155;
        border-left-color: #60a5fa;
        box-shadow: 0 1px 4px rgba(0,0,0,0.25);
    }

    /* ── Message label ── */
    .msg-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #94a3b8;
        margin-bottom: 0.4rem;
        display: block;
    }

    /* ── Sources ── */
    .source-box {
        background-color: #253650;
        padding: 0.6rem 0.8rem;
        border-radius: 0.35rem;
        margin-top: 0.75rem;
        font-size: 0.875rem;
        border: 1px solid #374f6b;
        color: #cbd5e1 !important;
    }
    .source-box strong { color: #38bdf8 !important; }

    /* ── Metrics ── */
    .metric-box {
        background-color: transparent;
        padding: 0.3rem 0;
        margin-top: 0.4rem;
        font-size: 0.78rem;
        color: #64748b !important;
        border-top: 1px solid #374f6b;
    }

    /* ── Bold text in messages ── */
    .chat-message strong { color: #93c5fd !important; }

    /* ── Code blocks ── */
    .chat-message code, .chat-message pre {
        background-color: #0f172a !important;
        color: #e2e8f0 !important;
        border-radius: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_memory" not in st.session_state:
    st.session_state.conversation_memory = ConversationMemory(max_turns=10)


def detect_language(text: str) -> str:
    """
    Detect query language using the enhanced detector (handles Latin-script MK).
    Falls back to Cyrillic-ratio heuristic if the module is unavailable.
    """
    try:
        from src.retrieval.enhanced_language_detector import EnhancedLanguageDetector
        lang, _, _ = EnhancedLanguageDetector().detect_language(text)
        return lang
    except Exception:
        cyrillic = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
        total_letters = len(re.findall(r'[a-zA-Zа-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
        if total_letters == 0:
            return "mk"
        return "mk" if cyrillic / total_letters > 0.3 else "en"


@st.cache_resource
def initialize_pipeline(model_choice: str):
    """
    Initialize RAG pipeline with caching.
    
    AUTO-INITIALIZES on app load!
    """
    try:
        from pathlib import Path
        from src.vectorstore.vector_store_manager import VectorStoreManager
        from src.retrieval.hybrid_smart_retriever import HybridSmartRetriever
        from src.llm.rag_pipeline import RAGPipeline
        from src.llm.groq_generator import GroqGenerator
        from src.llm.gemini_generator import GeminiGenerator
        from src.llm.openai_compatible_generator import OpenAICompatibleGenerator
        from src.telemetry.query_logger import QueryLogger

        def _read_key(filename):
            p = Path(r"D:\\API_KEYS") / filename
            return p.read_text().strip() if p.exists() else None

        # --- Generator factory ---
        label = model_choice
        if model_choice.startswith("Gemini"):
            api_key = _read_key("GEMINI_API_KEY.txt")
            generator = GeminiGenerator(model_name="gemini-2.5-flash", api_key=api_key)
        elif model_choice.startswith("OpenRouter"):
            model_map = {
                "OpenRouter / Llama 3.2 3B (Fast, Free)": "meta-llama/llama-3.2-3b-instruct:free",
                "OpenRouter / Llama 3.3 70B (Free, Slow)": "meta-llama/llama-3.3-70b-instruct:free",
            }
            api_key = _read_key("OPENROUTER_API_KEY.txt")
            generator = OpenAICompatibleGenerator.for_openrouter(
                model_name=model_map.get(model_choice, "meta-llama/llama-3.2-3b-instruct:free"),
                api_key=api_key,
            )
        else:
            groq_models = {
                "Llama 3.3 70B (Best)": "llama-3.3-70b-versatile",
                "Llama 3.1 8B (Fast)": "llama-3.1-8b-instant",
                "Mixtral 8x7B (Alternative)": "mixtral-8x7b-32768",
            }
            model_name = groq_models.get(model_choice, "llama-3.3-70b-versatile")
            generator = GroqGenerator(model_name=model_name)

        vsm = VectorStoreManager(collection_name="dsa_rag_test")
        vsm.create_collection(reset=False)
        retriever = HybridSmartRetriever(vsm)

        logger = QueryLogger(db_path="data/logs/queries.db", app_version="phase7-dev")
        logger.start_session(metadata={"ui": "streamlit_v2", "model": label})

        pipeline = RAGPipeline(vsm, retriever, generator, logger=logger)
        return pipeline, label, None
        
    except Exception as e:
        import traceback
        return None, None, f"{str(e)}\n{traceback.format_exc()}"


def _close_unclosed_fences(text: str) -> str:
    """Close any unclosed triple-backtick code fences so they don't swallow HTML."""
    if text.count("```") % 2 != 0:
        text += "\n```"
    return text


def format_message(role: str, content: str, metadata: dict = None):
    """Format chat message with styling"""
    css_class = "user-message" if role == "user" else "assistant-message"
    label = "Студент" if role == "user" else "Асистент"

    safe_content = _close_unclosed_fences(content)

    html = f"""
    <div class="chat-message {css_class}">
        <span class="msg-label">{label}</span>
        {safe_content}
    """
    
    if metadata and role == "assistant":
        # Add sources
        if metadata.get("sources"):
            html += '<div class="source-box"><strong>Извори</strong><br>'
            for source in metadata["sources"][:5]:
                html += f"• {source}<br>"
            html += "</div>"

        if metadata.get("retrieval_time_ms"):
            html += f"""
            <div class="metric-box">
                {metadata['retrieval_time_ms']}ms барање &nbsp;·&nbsp;
                {metadata.get('generation_time_ms', 0)}ms генерирање &nbsp;·&nbsp;
                {metadata['total_time_ms']}ms вкупно
            </div>
            """
    
    html += "</div>"
    return html


# Sidebar
with st.sidebar:
    st.markdown("### Поставки")

    st.markdown("**Јазичен модел**")
    model_choice = st.selectbox(
        "Избери модел / провајдер:",
        [
            # Groq (free tier, fast)
            "Llama 3.3 70B (Best)",
            "Llama 3.1 8B (Fast)",
            "Mixtral 8x7B (Alternative)",
            # Google Gemini (free tier)
            "Gemini 2.5 Flash (Google)",
            # OpenRouter free models
            "OpenRouter / Llama 3.2 3B (Fast, Free)",
            "OpenRouter / Llama 3.3 70B (Free, Slow)",
        ],
        index=0,
        help="Groq: побрзо / Gemini: 1M токени/ден / OpenRouter: повеќе модели"
    )
    
    # Hybrid search
    use_hybrid = st.checkbox(
        "Хибридно пребарување",
        value=True,
        help="Комбинира семантичко пребарување со метаподаточно зајакнување"
    )

    if st.button("Исчисти разговор"):
        st.session_state.messages = []
        st.session_state.conversation_memory.clear()
        st.rerun()
    
    # Auto-initialize pipeline
    with st.spinner("Иницијализирам систем..."):
        pipeline, active_model, error = initialize_pipeline(model_choice)
    
    if error:
        st.error("Грешка при иницијализација")
        st.text(error)
        pipeline = None
    else:
        st.success("Системот е подготвен")
        if active_model:
            st.caption(f"Активен модел: {active_model}")

    if pipeline:
        st.markdown("---")
        st.markdown("**Статистики за сесијата**")
        stats = pipeline.get_stats()
        st.metric("Прашања", stats.get("total_queries", 0))
        by_lang = stats.get("by_language", {})
        if by_lang:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("МК", by_lang.get("mk", 0))
            with col2:
                st.metric("EN", by_lang.get("en", 0))


# Main area
st.markdown('<h1 class="main-header">Виртуелен Асистент за ПСАА</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="main-subheader">Факултет за Електротехника и Информациски Технологии — '
    'Податочни Структури и Анализа на Алгоритми</p>',
    unsafe_allow_html=True,
)

# Display chat history
for message in st.session_state.messages:
    st.markdown(
        format_message(
            message["role"],
            message["content"],
            message.get("metadata")
        ),
        unsafe_allow_html=True
    )

# Chat input
if prompt := st.chat_input("Постави прашање за курсот..."):
    if not pipeline:
        st.error("Системот не е иницијализиран. Провери ги поставките за API клуч.")
    else:
        # Auto-detect language from query
        detected_lang = detect_language(prompt)
        
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        st.markdown(
            format_message("user", prompt),
            unsafe_allow_html=True
        )
        
        # Generate response
        with st.spinner("Барам одговор..."):
            try:
                response = pipeline.query(
                    prompt,
                    n_results=7,
                    language=detected_lang,
                    use_hybrid=use_hybrid,
                    conversation_memory=st.session_state.conversation_memory,
                )
                
                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "metadata": response
                })
                
                # Display assistant message
                st.markdown(
                    format_message(
                        "assistant",
                        response["answer"],
                        response
                    ),
                    unsafe_allow_html=True
                )
                
            except Exception as e:
                error_msg = f"Грешка: {str(e)}"
                st.error(error_msg)
                
                # Add error to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "metadata": None
                })

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #94a3b8; font-size: 0.82rem;'>
Факултет за Електротехника и Информациски Технологии (ФЕИТ) &nbsp;·&nbsp;
Податочни Структури и Анализа на Алгоритми (ПСАА) &nbsp;·&nbsp;
Дипломска работа
</div>
""", unsafe_allow_html=True)
