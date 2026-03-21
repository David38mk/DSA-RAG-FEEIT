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
import time
import re
from pathlib import Path

# Page config
st.set_page_config(
    page_title="DSA RAG Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1.2rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
        border-left: 6px solid;
        color: #1e1e1e !important; /* Force dark text for readability */
    }
    /* User: Deep Blue/Teal background */
    .user-message {
        background-color: #bbdefb; 
        border-left-color: #0d47a1;
    }
    /* Assistant: Soft Sage background */
    .assistant-message {
        background-color: #dcedc8;
        border-left-color: #33691e;
    }
    /* Source box: Warm amber */
    .source-box {
        background-color: #ffe0b2;
        padding: 0.6rem;
        border-radius: 0.4rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
        border: 1px solid #ffb74d;
        color: #424242 !important;
    }
    /* Metrics: Light Grey/Cool background */
    .metric-box {
        background-color: #f5f5f5;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin-top: 0.5rem;
        font-size: 0.85rem;
        color: #616161 !important;
        border: 1px solid #e0e0e0;
    }
    /* Make bold text inside messages pop */
    .chat-message strong {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []


def detect_language(text: str) -> str:
    """Auto-detect language from query text"""
    cyrillic = len(re.findall(r'[а-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
    total_letters = len(re.findall(r'[a-zA-Zа-яА-ЯЃЅЈЉЊЌЏѓѕјљњќџ]', text))
    
    if total_letters == 0:
        return "mk"  # Default
    
    cyrillic_ratio = cyrillic / total_letters
    return "mk" if cyrillic_ratio > 0.3 else "en"


@st.cache_resource
def initialize_pipeline(model_choice: str):
    """
    Initialize RAG pipeline with caching.
    
    AUTO-INITIALIZES on app load!
    """
    try:
        from src.vectorstore.vector_store_manager import VectorStoreManager
        from src.retrieval.smart_retriever_v2 import SmartRetriever
        from src.retrieval.hybrid_smart_retriever import HybridSmartRetriever
        from src.llm.rag_pipeline import RAGPipeline
        from src.llm.groq_generator import GroqGenerator
        
        # Model configurations
        model_configs = {
            "Llama 3.3 70B (Best)": "llama-3.3-70b-versatile",
            "Llama 3.1 8B (Fast)": "llama-3.1-8b-instant",
            "Mixtral 8x7B (Alternative)": "mixtral-8x7b-32768", 
            "Gemma 2 9B (Lightweight)": "gemma2-9b-it"
        }
        
        model_name = model_configs.get(model_choice, "llama-3.3-70b-versatile")
        
        # Load vector store (existing embeddings)
        vsm = VectorStoreManager(collection_name="dsa_rag_test")
        vsm.create_collection(reset=False)
        
        # Setup retriever
        # retriever = SmartRetriever(vsm)
        retriever = HybridSmartRetriever(vsm)

        # Initialize generator
        generator = GroqGenerator(model_name=model_name)
        
        # Create pipeline
        pipeline = RAGPipeline(vsm, retriever, generator)
        
        return pipeline, model_name, None
        
    except Exception as e:
        import traceback
        return None, None, f"{str(e)}\n{traceback.format_exc()}"


def format_message(role: str, content: str, metadata: dict = None):
    """Format chat message with styling"""
    css_class = "user-message" if role == "user" else "assistant-message"
    icon = "👤" if role == "user" else "🤖"
    
    html = f"""
    <div class="chat-message {css_class}">
        <strong>{icon} {"Вие" if role == "user" else "Асистент"}:</strong><br>
        {content}
    """
    
    if metadata and role == "assistant":
        # Add sources
        if metadata.get("sources"):
            html += '<div class="source-box"><strong>📚 Извори:</strong><br>'
            for source in metadata["sources"][:5]:
                html += f"• {source}<br>"
            html += "</div>"
        
        # Add metrics
        if metadata.get("retrieval_time_ms"):
            html += f"""
            <div class="metric-box">
                ⚡ {metadata['retrieval_time_ms']}ms (барање) + 
                {metadata.get('generation_time_ms', 0)}ms (генерирање) = 
                {metadata['total_time_ms']}ms вкупно
            </div>
            """
    
    html += "</div>"
    return html


# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Поставки")
    
    # Model selection
    st.markdown("### 🤖 LLM Модел")
    model_choice = st.selectbox(
        "Избери модел:",
        [
            "Llama 3.3 70B (Best)",
            "Llama 3.1 8B (Fast)",
            "Mixtral 8x7B (Alternative)",  # ← ADD THIS
            "Gemma 2 9B (Lightweight)"
        ],
        index=0,
        help="Поголем модел = подобар квалитет, помала брзина"
    )
    
    # Number of sources
    n_results = st.slider(
        "Број на извори",
        min_value=1,
        max_value=10,
        value=5,
        help="Колку документи да се користат за одговорот"
    )
    
    # Hybrid search
    use_hybrid = st.checkbox(
        "Хибридно пребарување",
        value=True,
        help="Комбинира семантичко + метаподаци"
    )
    
    # Clear chat
    if st.button("🗑️ Исчисти Разговор"):
        st.session_state.messages = []
        st.rerun()
    
    # Auto-initialize pipeline
    with st.spinner("Иницијализирам систем..."):
        pipeline, active_model, error = initialize_pipeline(model_choice)
    
    if error:
        st.error("❌ Грешка при иницијализација")
        st.text(error)
        if "GROQ_API_KEY" in error:
            st.info("""
            Подеси го GROQ_API_KEY:
            ```
            $env:GROQ_API_KEY='твој-клуч'
            ```
            Зема бесплатен клуч: https://console.groq.com/
            """)
        pipeline = None
    else:
        st.success("✅ Систем спремен")
        if active_model:
            st.info(f"🤖 Активен модел: `{active_model}`")
    
    # Stats
    if pipeline:
        st.markdown("### 📊 Статистики")
        stats = pipeline.get_stats()
        st.metric("Вкупно прашања", stats.get("total_queries", 0))
        
        by_lang = stats.get("by_language", {})
        if by_lang:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Македонски", by_lang.get("mk", 0))
            with col2:
                st.metric("English", by_lang.get("en", 0))


# Main area
st.markdown('<h1 class="main-header">🤖 DSA RAG Асистент</h1>', unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; color: #666; margin-bottom: 2rem;'>
Прашај за податочни структури, алгоритми, испити, лабораториски и сè од ПСАА курсот!<br>
<small>Системот автоматски препознава јазик (македонски/англиски)</small>
</div>
""", unsafe_allow_html=True)

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
if prompt := st.chat_input("Напиши го твоето прашање..."):
    if not pipeline:
        st.error("⚠️ Системот не е иницијализиран! Провери го GROQ_API_KEY.")
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
        with st.spinner("Размислувам..."):
            try:
                response = pipeline.query(
                    prompt,
                    n_results=n_results,
                    language=detected_lang,  # Auto-detected!
                    use_hybrid=use_hybrid
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
<div style='text-align: center; color: #999; font-size: 0.9rem;'>
🎓 Факултет за Електротехника и Информациски Технологии (ФЕИТ)<br>
Податочни Структури и Анализа на Алгоритми (ПСАА)<br>
Изработено од: Давид (Дипломска работа)
</div>
""", unsafe_allow_html=True)
