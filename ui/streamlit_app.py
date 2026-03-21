"""
Streamlit Chat Interface for DSA RAG System

Beautiful, production-ready chat UI with:
- Message history
- Source citations
- Performance metrics
- Language selection
- Chat export

Run: streamlit run streamlit_app.py
"""

import streamlit as st
import time
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

if "pipeline" not in st.session_state:
    st.session_state.pipeline = None

if "initialized" not in st.session_state:
    st.session_state.initialized = False


def initialize_rag_pipeline(use_groq: bool = True):
    """Initialize RAG pipeline with correct arguments and collection"""
    try:
        from src.vectorstore.vector_store_manager import VectorStoreManager
        from src.retrieval.smart_retriever_fixed import SmartRetriever
        from src.llm.rag_pipeline import RAGPipeline
        
        # 1. Force the correct collection name where your data lives
        vsm = VectorStoreManager(collection_name="dsa_rag_test")
        vsm.create_collection(reset=False)
        
        # 2. Setup retriever
        retriever = SmartRetriever(vsm)
        
        # 3. Initialize generator
        if use_groq:
            from src.llm.groq_generator import GroqGenerator
            generator = GroqGenerator()
        else:
            # Note: Ensure you have a MockGenerator or MistralGenerator ready
            from src.llm.mistral_generator import MistralGenerator
            generator = MistralGenerator(mode="local")
        
        # 4. FIX: Pass all THREE required arguments in the correct order
        # Order: (VectorStoreManager, SmartRetriever, Generator)
        pipeline = RAGPipeline(vsm, retriever, generator)
        
        return pipeline, None
        
    except Exception as e:
        import traceback
        return None, f"{str(e)}\n{traceback.format_exc()}"


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
            for source in metadata["sources"][:10]:
                html += f"• {source}<br>"
            html += "</div>"
        
        # Add metrics
        if metadata.get("retrieval_time_ms"):
            html += f"""
            <div class="metric-box">
                ⚡ Време: {metadata['retrieval_time_ms']}ms (барање) + 
                {metadata.get('generation_time_ms', 0)}ms (генерирање) = 
                {metadata['total_time_ms']}ms вкупно
            </div>
            """
    
    html += "</div>"
    return html


# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Поставки")
    
    # Language selection
    language = st.selectbox(
        "Јазик / Language",
        ["Македонски", "English"],
        index=0
    )
    lang_code = "mk" if language == "Македонски" else "en"
    
    # Number of results
    n_results = st.slider(
        "Број на извори",
        min_value=1,
        max_value=10,
        value=5,
        help="Колку документи да се користат за одговорот"
    )
    
    # Use hybrid search
    use_hybrid = st.checkbox(
        "Хибридно пребарување",
        value=True,
        help="Комбинира семантичко + метаподаци"
    )
    
    # Generator selection
    st.markdown("### 🤖 LLM Модел")
    use_groq = st.radio(
        "Избери генератор:",
        ["Groq (брз & бесплатен)", "Mock (тестирање)"],
        index=0
    ) == "Groq (брз & бесплатен)"
    
    # Initialize button
    if st.button("🔄 Иницијализирај Систем"):
        with st.spinner("Иницијализирам..."):
            pipeline, error = initialize_rag_pipeline(use_groq)
            if error:
                st.error(f"Грешка: {error}")
                if "GROQ_API_KEY" in error:
                    st.info("Подеси го GROQ_API_KEY:\n```\n$env:GROQ_API_KEY='твој-клуч'\n```")
            else:
                st.session_state.pipeline = pipeline
                st.session_state.initialized = True
                st.success("✅ Системот е спремен!")
    
    # Clear chat
    if st.button("🗑️ Исчисти Разговор"):
        st.session_state.messages = []
        st.rerun()
    
    # Stats
    if st.session_state.pipeline:
        st.markdown("### 📊 Статистики")
        stats = st.session_state.pipeline.get_stats()
        st.metric("Вкупно прашања", stats["total_queries"])
        if stats["by_language"]:
            for lang, count in stats["by_language"].items():
                st.metric(f"На {lang}", count)


# Main area
st.markdown('<h1 class="main-header">🤖 DSA RAG Асистент</h1>', unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; color: #666; margin-bottom: 2rem;'>
Прашај за податочни структури, алгоритми, испити, лабораториски и сè од ПСАА курсот!
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
    if not st.session_state.initialized:
        st.error("⚠️ Прво иницијализирај го системот од sidebar!")
    else:
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
                response = st.session_state.pipeline.query(
                    prompt,
                    n_results=n_results,
                    language=lang_code,
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
                st.error(f"Грешка: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #999; font-size: 0.9rem;'>
🎓 Факултет за Електротехника и Информациски Технологии (ФЕИТ)<br>
Податочни Структури и Анализа на Алгоритми (ПСАА)<br>
Изработено од: Давид (Дипломска работа)
</div>
""", unsafe_allow_html=True)
