import time
from typing import Dict, List

class RAGPipeline:
    """End-to-end RAG system with performance tracking"""
    
    def __init__(self, vector_store_manager, retriever, generator):
        self.vsm = vector_store_manager
        self.retriever = retriever
        self.generator = generator
        self.stats = {"total_queries": 0, "successful": 0, "failed": 0}
    
    def query(self, 
              question: str, 
              n_results: int = 15, 
              use_routing: bool = True, 
              language: str = "mk", 
              use_hybrid: bool = True) -> Dict:
        """
        Process query end-to-end.
        Parameters match the calls from streamlit_app.py
        """
        start_total = time.perf_counter()
        self.stats["total_queries"] += 1
        
        try:
            # 1. Retrieval Phase
            start_retrieval = time.perf_counter()
            
            if use_routing:
                results = self.retriever.route_query(question, n_results)
            else:
                # Fallback to direct search if routing is off
                results = self.vsm.search(question, n_results)
            
            retrieval_time = int((time.perf_counter() - start_retrieval) * 1000)
            
            # 2. Generation Phase
            start_gen = time.perf_counter()
            
            # Pass the language to the generator
            answer_data = self.generator.generate(
                question, 
                results["results"], 
                language=language
            )
            
            gen_time = int((time.perf_counter() - start_gen) * 1000)
            total_time = int((time.perf_counter() - start_total) * 1000)
            
            self.stats["successful"] += 1
            
            # Return full dictionary expected by format_message in Streamlit
            return {
                "question": question,
                "answer": answer_data["answer"],
                "sources": answer_data["sources"],
                "retrieval_count": len(results["results"]),
                "retrieval_time_ms": retrieval_time,
                "generation_time_ms": gen_time,
                "total_time_ms": total_time,
                "success": True
            }
            
        except Exception as e:
            self.stats["failed"] += 1
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "sources": [],
                "success": False,
                "error": str(e),
                "retrieval_time_ms": 0,
                "total_time_ms": 0
            }
    
    def get_stats(self) -> Dict:
        """Return stats for Streamlit UI"""
        gen_stats = self.generator.get_stats() if hasattr(self.generator, 'get_stats') else {}
        return {
            "total_queries": self.stats.get("total_queries", 0),
            "by_language": gen_stats.get("by_language", {"mk": 0, "en": 0})
        }