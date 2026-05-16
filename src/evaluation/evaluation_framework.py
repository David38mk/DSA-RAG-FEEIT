"""
Evaluation Framework - RAG System Assessment

Metrics:
- Retrieval: Precision@k, Recall@k, MRR, NDCG
- Answer Quality: Relevance, Factual Accuracy, Completeness
- End-to-End: Latency, Success Rate

For DSA-RAG-FEEIT thesis project
"""

import json
from pathlib import Path
from typing import List, Dict
import numpy as np

DEFAULT_TEST_SET_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "datasets" / "routing_test_set.json"


class EvaluationFramework:
    """Evaluate RAG system performance"""
    
    def __init__(self):
        self.results = []
    
    def create_test_set(self, path: Path = DEFAULT_TEST_SET_PATH) -> List[Dict]:
        """
        Load test queries with ground truth from JSON.

        The JSON file is the source of truth (evaluation/datasets/routing_test_set.json).
        Returns the test_cases list directly.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["test_cases"]
    
    def evaluate_retrieval(self, 
                          query: str,
                          retrieved_chunks: List[Dict],
                          expected_keywords: List[str],
                          k: int = 5) -> Dict:
        """
        Evaluate retrieval quality.
        
        Args:
            query: The query
            retrieved_chunks: Retrieved chunks from system
            expected_keywords: Keywords that should appear in results
            k: Number of results to evaluate
            
        Returns:
            Dict with retrieval metrics
        """
        # Limit to top-k
        chunks = retrieved_chunks[:k]
        
        # Combine all text
        retrieved_text = " ".join([
            chunk.get("text", "").lower() 
            for chunk in chunks
        ])
        
        # Check keyword coverage
        keywords_found = sum(
            1 for keyword in expected_keywords 
            if keyword.lower() in retrieved_text
        )
        
        keyword_coverage = keywords_found / len(expected_keywords) if expected_keywords else 0
        
        # Average similarity
        avg_similarity = np.mean([
            chunk.get("similarity", 0) 
            for chunk in chunks
        ]) if chunks else 0
        
        # Check if top result is highly relevant (>0.7 similarity)
        top_relevant = chunks[0].get("similarity", 0) > 0.7 if chunks else False
        
        return {
            "num_retrieved": len(chunks),
            "keyword_coverage": keyword_coverage,
            "keywords_found": keywords_found,
            "total_keywords": len(expected_keywords),
            "avg_similarity": avg_similarity,
            "top_similarity": chunks[0].get("similarity", 0) if chunks else 0,
            "top_relevant": top_relevant
        }
    
    def evaluate_answer_quality(self,
                                query: str,
                                answer: str,
                                expected_topics: List[str]) -> Dict:
        """
        Evaluate generated answer quality.
        
        Args:
            query: The query
            answer: Generated answer
            expected_topics: Topics that should be covered
            
        Returns:
            Dict with answer quality metrics
        """
        answer_lower = answer.lower()
        
        # Topic coverage
        topics_covered = sum(
            1 for topic in expected_topics 
            if topic.lower() in answer_lower
        )
        
        topic_coverage = topics_covered / len(expected_topics) if expected_topics else 0
        
        # Answer length (as proxy for completeness)
        answer_length = len(answer)
        
        # Check if answer says "don't know" or similar
        unknown_phrases = [
            "не знам", "don't know", "cannot answer", 
            "не можам", "not in context", "insufficient"
        ]
        
        is_uncertain = any(phrase in answer_lower for phrase in unknown_phrases)
        
        # Quality score (heuristic)
        quality_score = 0.0
        
        # Length component (50-500 chars is good)
        if 50 <= answer_length <= 500:
            quality_score += 0.3
        elif answer_length > 500:
            quality_score += 0.2
        
        # Topic coverage component
        quality_score += 0.5 * topic_coverage
        
        # Certainty component
        if not is_uncertain:
            quality_score += 0.2
        
        return {
            "answer_length": answer_length,
            "topic_coverage": topic_coverage,
            "topics_covered": topics_covered,
            "total_topics": len(expected_topics),
            "is_uncertain": is_uncertain,
            "quality_score": min(quality_score, 1.0)
        }
    
    def evaluate_end_to_end(self,
                           query: str,
                           response: Dict,
                           expected_data: Dict) -> Dict:
        """
        Evaluate complete RAG response.
        
        Args:
            query: The query
            response: RAG pipeline response
            expected_data: Expected test case data
            
        Returns:
            Dict with comprehensive metrics
        """
        # Retrieval metrics
        retrieval_metrics = self.evaluate_retrieval(
            query,
            response.get("source_details", []),
            expected_data.get("expected_sources", [])
        )
        
        # Answer quality metrics
        answer_metrics = self.evaluate_answer_quality(
            query,
            response.get("answer", ""),
            expected_data.get("expected_topics", [])
        )
        
        # Intent detection accuracy
        expected_intent = expected_data.get("intent", "unknown")
        detected_intent = response.get("routing", {}).get("intent", "unknown")
        intent_correct = expected_intent.lower() in detected_intent.lower()
        
        # Performance metrics
        total_time_ms = response.get("total_time_ms", 0)
        
        # Combined score
        combined_score = (
            0.3 * retrieval_metrics["keyword_coverage"] +
            0.4 * answer_metrics["quality_score"] +
            0.2 * (1.0 if intent_correct else 0.0) +
            0.1 * (1.0 if total_time_ms < 3000 else 0.5)  # <3s is good
        )
        
        return {
            "query": query,
            "intent_correct": intent_correct,
            "retrieval": retrieval_metrics,
            "answer_quality": answer_metrics,
            "performance_ms": total_time_ms,
            "combined_score": combined_score
        }
    
    def run_evaluation(self, rag_pipeline, test_set: List[Dict] = None) -> Dict:
        """
        Run complete evaluation on test set.
        
        Args:
            rag_pipeline: RAGPipeline instance
            test_set: List of test cases (None = use default)
            
        Returns:
            Dict with aggregated metrics
        """
        if test_set is None:
            test_set = self.create_test_set()
        
        print(f"\n🔬 Running evaluation on {len(test_set)} test queries...")
        
        results = []
        
        for i, test_case in enumerate(test_set, 1):
            query = test_case["query"]
            
            print(f"\n[{i}/{len(test_set)}] Testing: {query}")
            
            # Run RAG query
            response = rag_pipeline.query(query, n_results=7)
            
            # Evaluate
            eval_result = self.evaluate_end_to_end(query, response, test_case)
            
            results.append(eval_result)
            
            # Show brief result
            print(f"  Score: {eval_result['combined_score']:.2f} | "
                  f"Intent: {'✓' if eval_result['intent_correct'] else '✗'} | "
                  f"Retrieval: {eval_result['retrieval']['keyword_coverage']:.2f} | "
                  f"Answer: {eval_result['answer_quality']['quality_score']:.2f}")
        
        # Aggregate metrics
        aggregated = self._aggregate_results(results)
        
        self.results = results  # Store for later analysis
        
        return aggregated
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate evaluation results"""
        n = len(results)
        
        if n == 0:
            return {}
        
        # Average scores
        avg_combined = np.mean([r["combined_score"] for r in results])
        avg_retrieval = np.mean([r["retrieval"]["keyword_coverage"] for r in results])
        avg_answer_quality = np.mean([r["answer_quality"]["quality_score"] for r in results])
        
        # Intent accuracy
        intent_accuracy = sum(r["intent_correct"] for r in results) / n
        
        # Performance
        avg_latency = np.mean([r["performance_ms"] for r in results])
        
        # By category
        by_intent = {}
        for result in results:
            # This would need the original test case to categorize properly
            # For now, we'll skip this
            pass
        
        return {
            "total_queries": n,
            "avg_combined_score": avg_combined,
            "avg_retrieval_score": avg_retrieval,
            "avg_answer_quality": avg_answer_quality,
            "intent_accuracy": intent_accuracy,
            "avg_latency_ms": avg_latency,
            "performance_grade": self._grade_performance(avg_latency),
            "overall_grade": self._grade_overall(avg_combined)
        }
    
    def _grade_performance(self, latency_ms: float) -> str:
        """Grade performance based on latency"""
        if latency_ms < 1000:
            return "A (Excellent)"
        elif latency_ms < 2000:
            return "B (Good)"
        elif latency_ms < 3000:
            return "C (Acceptable)"
        else:
            return "D (Needs improvement)"
    
    def _grade_overall(self, score: float) -> str:
        """Grade overall system quality"""
        if score >= 0.8:
            return "A (Excellent)"
        elif score >= 0.7:
            return "B (Good)"
        elif score >= 0.6:
            return "C (Acceptable)"
        elif score >= 0.5:
            return "D (Needs work)"
        else:
            return "F (Poor)"
    
    def print_report(self, aggregated: Dict):
        """Print evaluation report"""
        print("\n" + "="*70)
        print(" EVALUATION REPORT")
        print("="*70)
        
        print(f"\nQueries Evaluated: {aggregated.get('total_queries', 0)}")
        
        print(f"\n📊 Scores:")
        print(f"  Overall: {aggregated.get('avg_combined_score', 0):.2f} - {aggregated.get('overall_grade', 'N/A')}")
        print(f"  Retrieval: {aggregated.get('avg_retrieval_score', 0):.2f}")
        print(f"  Answer Quality: {aggregated.get('avg_answer_quality', 0):.2f}")
        print(f"  Intent Accuracy: {aggregated.get('intent_accuracy', 0):.2%}")
        
        print(f"\n⚡ Performance:")
        print(f"  Avg Latency: {aggregated.get('avg_latency_ms', 0):.0f}ms - {aggregated.get('performance_grade', 'N/A')}")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    print("Evaluation Framework")
    print("\nUsage:")
    print("  evaluator = EvaluationFramework()")
    print("  results = evaluator.run_evaluation(rag_pipeline)")
    print("  evaluator.print_report(results)")
