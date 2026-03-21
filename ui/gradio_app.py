"""
Gradio Chat Interface for DSA RAG System

Alternative to Streamlit with easy sharing capabilities.

Run: python gradio_app.py
"""

import gradio as gr
import os

# Initialize pipeline
pipeline = None

def initialize_pipeline(use_groq: bool = True):
    """Initialize RAG pipeline"""
    global pipeline
    
    try:
        from src.vectorstore.vector_store_manager import VectorStoreManager
        from src.retrieval.smart_retriever import SmartRetriever
        from src.llm.rag_pipeline import RAGPipeline
        
        if use_groq:
            from src.llm.groq_generator import GroqGenerator
            generator = GroqGenerator()
        else:
            from src.llm.mistral_generator import MockGenerator
            generator = MockGenerator()
        
        vsm = VectorStoreManager()
        vsm.create_collection(reset=False)
        
        retriever = SmartRetriever(vsm)
        pipeline = RAGPipeline(retriever, generator)
        
        return "✅ Системот е иницијализиран и спремен!"
        
    except Exception as e:
        return f"❌ Грешка: {str(e)}"


def chat(message, history, language, n_results):
    """Process chat message"""
    global pipeline
    
    if pipeline is None:
        return "⚠️ Прво иницијализирај го системот!"
    
    try:
        lang_code = "mk" if language == "Македонски" else "en"
        
        response = pipeline.query(
            message,
            n_results=int(n_results),
            language=lang_code,
            use_hybrid=True
        )
        
        # Format response with sources
        answer = response["answer"]
        
        if response.get("sources"):
            answer += "\n\n📚 **Извори:**\n"
            for source in response["sources"][:3]:
                answer += f"- {source}\n"
        
        answer += f"\n\n⚡ *Време: {response['total_time_ms']}ms*"
        
        return answer
        
    except Exception as e:
        return f"❌ Грешка: {str(e)}"


# Create Gradio interface
with gr.Blocks(
    theme=gr.themes.Soft(),
    title="DSA RAG Асистент"
) as demo:
    
    gr.Markdown("""
    # 🤖 DSA RAG Асистент
    
    Прашај за податочни структури, алгоритми, испити, лабораториски и сè од ПСАА курсот!
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            # Chat interface
            chatbot = gr.Chatbot(
                label="Разговор",
                height=500,
                show_copy_button=True
            )
            
            msg = gr.Textbox(
                label="Твоето прашање",
                placeholder="Напиши го твоето прашање овде...",
                lines=2
            )
            
            with gr.Row():
                submit = gr.Button("📤 Испрати", variant="primary")
                clear = gr.Button("🗑️ Исчисти")
        
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Поставки")
            
            # Language
            language = gr.Radio(
                ["Македонски", "English"],
                value="Македонски",
                label="Јазик"
            )
            
            # Number of results
            n_results = gr.Slider(
                minimum=1,
                maximum=10,
                value=5,
                step=1,
                label="Број на извори"
            )
            
            gr.Markdown("### 🔧 Иницијализација")
            
            init_btn = gr.Button("🚀 Иницијализирај Систем")
            init_status = gr.Textbox(
                label="Статус",
                interactive=False
            )
            
            gr.Markdown("""
            ### 📖 Помош
            
            **Примери:**
            - Објасни AVL дрва
            - What is Big O?
            - Колку поени за полагање?
            - Quicksort complexity?
            """)
    
    # Event handlers
    def respond(message, chat_history, language, n_results):
        response = chat(message, chat_history, language, n_results)
        chat_history.append((message, response))
        return "", chat_history
    
    submit.click(
        respond,
        inputs=[msg, chatbot, language, n_results],
        outputs=[msg, chatbot]
    )
    
    msg.submit(
        respond,
        inputs=[msg, chatbot, language, n_results],
        outputs=[msg, chatbot]
    )
    
    clear.click(lambda: None, None, chatbot, queue=False)
    
    init_btn.click(
        lambda: initialize_pipeline(use_groq=True),
        outputs=init_status
    )
    
    gr.Markdown("""
    ---
    🎓 **ФЕИТ - Податочни Структури и Анализа на Алгоритми**  
    Изработено од: Давид (Дипломска работа)
    """)


if __name__ == "__main__":
    # Check for Groq API key
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  GROQ_API_KEY not set. Will use Mock generator.")
        print("Set with: $env:GROQ_API_KEY='your-key'")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # Set to True to get public URL
        show_error=True
    )
