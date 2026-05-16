import time
from typing import Dict, Optional

class RAGPipeline:
    """End-to-end RAG system with performance tracking"""

    def __init__(self, vector_store_manager, retriever, generator, logger=None):
        self.vsm = vector_store_manager
        self.retriever = retriever
        self.generator = generator
        self.logger = logger
        self.stats = {"total_queries": 0, "successful": 0, "failed": 0}

    def query(self,
              question: str,
              n_results: int = 15,
              use_routing: bool = True,
              language: str = "mk",
              use_hybrid: bool = True,
              conversation_memory=None) -> Dict:
        """
        Process query end-to-end.
        Parameters match the calls from streamlit_app.py
        """
        start_total = time.perf_counter()
        self.stats["total_queries"] += 1
        query_id: Optional[str] = None

        try:
            # 1. Retrieval Phase
            start_retrieval = time.perf_counter()

            if use_routing:
                if use_hybrid and hasattr(self.retriever, "hybrid_search"):
                    results = self.retriever.hybrid_search(question, n_results=n_results)
                else:
                    results = self.retriever.route_query(question, n_results)
            else:
                # Fallback to direct search if routing is off
                results = self.vsm.search(question, n_results)

            retrieval_time = int((time.perf_counter() - start_retrieval) * 1000)

            # Log the query now that routing metadata is known
            routing = results.get("routing", {}) if isinstance(results, dict) else {}
            if self.logger:
                query_id = self.logger.log_query(
                    question=question,
                    language=language,
                    intent=routing.get("intent"),
                    intent_confidence=routing.get("intent_confidence"),
                    routing_method=routing.get("classification_method"),
                    n_results=n_results,
                )

            # 2. Generation Phase
            start_gen = time.perf_counter()

            history_text = ""
            if conversation_memory is not None and hasattr(conversation_memory, "format_for_prompt"):
                history_text = conversation_memory.format_for_prompt(language=language)

            answer_data = self.generator.generate(
                question,
                results["results"],
                language=language,
                max_tokens=4096,  # raised from 2048: detailed DSA answers (Big O proofs, full Java implementations) routinely exceed 2048 tokens
                conversation_history=history_text,
            )

            gen_time = int((time.perf_counter() - start_gen) * 1000)
            total_time = int((time.perf_counter() - start_total) * 1000)

            self.stats["successful"] += 1

            if self.logger and query_id:
                self.logger.log_response(
                    query_id=query_id,
                    answer=answer_data["answer"],
                    sources=answer_data["sources"],
                    model=answer_data.get("model"),
                    success=True,
                )
                self.logger.log_metrics(
                    query_id=query_id,
                    retrieval_time_ms=retrieval_time,
                    generation_time_ms=gen_time,
                    total_time_ms=total_time,
                )

            if conversation_memory is not None and hasattr(conversation_memory, "add_turn"):
                conversation_memory.add_turn(
                    query=question,
                    answer=answer_data["answer"],
                    language=language,
                )

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
            total_time = int((time.perf_counter() - start_total) * 1000)
            if self.logger:
                if not query_id:
                    query_id = self.logger.log_query(
                        question=question,
                        language=language,
                        n_results=n_results,
                    )
                self.logger.log_response(
                    query_id=query_id,
                    answer=None,
                    sources=[],
                    success=False,
                    error=str(e),
                )
                self.logger.log_metrics(
                    query_id=query_id,
                    total_time_ms=total_time,
                )
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "sources": [],
                "success": False,
                "error": str(e),
                "retrieval_time_ms": 0,
                "total_time_ms": total_time,
            }
    
    def get_stats(self) -> Dict:
        """Return stats for Streamlit UI"""
        gen_stats = self.generator.get_stats() if hasattr(self.generator, 'get_stats') else {}
        return {
            "total_queries": self.stats.get("total_queries", 0),
            "by_language": gen_stats.get("by_language", {"mk": 0, "en": 0})
        }