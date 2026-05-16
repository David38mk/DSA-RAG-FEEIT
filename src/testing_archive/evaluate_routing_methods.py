"""
Routing Method Evaluation - Phase 6

Compares three routing methods:
1. Rule-based only (Phase 4)
2. LLM-based only (Phase 6)
3. Hybrid (Phase 6 - recommended)

Evaluates on accuracy, latency, and real-world performance.

For DSA-RAG-FEEIT thesis project - Phase 6 Evaluation
"""

import time
import json
from typing import List, Dict, Tuple


# Test dataset with ground truth
TEST_QUERIES = [
    # TECHNICAL queries (ground truth: TECHNICAL)
    ("Објасни AVL дрва", "mk", "TECHNICAL", "Clear DSA concept"),
    ("Како работи quicksort алгоритам?", "mk", "TECHNICAL", "Algorithm explanation"),
    ("Што е Big O нотација?", "mk", "TECHNICAL", "Complexity analysis"),
    ("Објасни hash табели", "mk", "TECHNICAL", "Data structure"),
    ("Кажи ми за binary search", "mk", "TECHNICAL", "Algorithm"),
    ("What is a binary tree?", "en", "TECHNICAL", "Data structure (English)"),
    ("Explain dynamic programming", "en", "TECHNICAL", "Algorithm technique"),
    ("How does merge sort work?", "en", "TECHNICAL", "Sorting algorithm"),
    ("Објасни рекурзија", "mk", "TECHNICAL", "Programming concept"),
    ("Што е граф податочна структура?", "mk", "TECHNICAL", "Graph definition"),
    
    # SUPPORT queries (ground truth: SUPPORT)
    ("Колку поени треба за полагање?", "mk", "SUPPORT", "Grading requirement"),
    ("Дали ќе имаме лаб утре?", "mk", "SUPPORT", "Lab schedule"),
    ("Кога е испитот?", "mk", "SUPPORT", "Exam date"),
    ("Како се бодува проектот?", "mk", "SUPPORT", "Project grading"),
    ("Кои се условите за потпис?", "mk", "SUPPORT", "Signature requirements"),
    ("What are the exam dates?", "en", "SUPPORT", "Exam schedule (English)"),
    ("How many points do I need to pass?", "en", "SUPPORT", "Passing grade"),
    ("Are labs mandatory?", "en", "SUPPORT", "Lab requirement"),
    ("Дали треба лаптоп на лаб?", "mk", "SUPPORT", "Lab equipment"),
    ("Колку лабораториски има?", "mk", "SUPPORT", "Lab count"),
    
    # AMBIGUOUS queries (could be either - test LLM advantage)
    ("Објасни како даположам", "mk", "SUPPORT", "Ambiguous: passing procedure"),
    ("Што треба да знам за испитот?", "mk", "SUPPORT", "Ambiguous: exam preparation"),
    ("Кои теми треба да учам?", "mk", "SUPPORT", "Ambiguous: study topics"),
    ("Како да се подготвам за испит?", "mk", "SUPPORT", "Ambiguous: exam prep"),
    ("Објасни ми за вежбите", "mk", "SUPPORT", "Ambiguous: exercises/labs"),
    
    # TECHNICAL but tricky (test pattern matching limits)
    ("Зошто се важни дрвата во програмирање?", "mk", "TECHNICAL", "Tricky: why trees important"),
    ("Која е разликата помеѓу stack и queue?", "mk", "TECHNICAL", "Tricky: comparison"),
    ("Кога да користам hash табела наместо низа?", "mk", "TECHNICAL", "Tricky: when to use"),
    ("Дали binary search е подобар од linear?", "mk", "TECHNICAL", "Tricky: comparison"),
    ("Како да избeрам алгоритам за сортирање?", "mk", "TECHNICAL", "Tricky: algorithm selection"),
]


def evaluate_rule_based(test_queries: List[Tuple]) -> Dict:
    """Evaluate rule-based classification only"""
    
    print("\n" + "="*70)
    print("EVALUATING: RULE-BASED CLASSIFICATION")
    print("="*70)
    
    try:
        # Import rule-based detector
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        
        from src.retrieval.smart_retriever_v2 import SmartRetriever
        
        # Mock VSM for evaluation
        class MockVSM:
            def search(self, *args, **kwargs):
                return {"results": []}
        
        retriever = SmartRetriever(MockVSM())
        
    except ImportError as e:
        print(f"Error importing SmartRetriever: {e}")
        return {"error": str(e)}
    
    results = {
        "correct": 0,
        "total": len(test_queries),
        "by_category": {"TECHNICAL": {"correct": 0, "total": 0}, 
                        "SUPPORT": {"correct": 0, "total": 0}},
        "latencies": [],
        "errors": []
    }
    
    for query, lang, ground_truth, description in test_queries:
        try:
            start = time.perf_counter()
            intent, confidence = retriever.detect_intent(query)
            latency_ms = (time.perf_counter() - start) * 1000
            
            predicted = intent.value.upper()
            correct = (predicted == ground_truth)
            
            results["latencies"].append(latency_ms)
            results["by_category"][ground_truth]["total"] += 1
            
            if correct:
                results["correct"] += 1
                results["by_category"][ground_truth]["correct"] += 1
                status = "✓"
            else:
                status = "✗"
            
            print(f"{status} {description[:40]:40} | Predicted: {predicted:10} | Truth: {ground_truth:10} | {latency_ms:.1f}ms")
            
        except Exception as e:
            results["errors"].append(str(e))
            print(f"✗ Error on query: {query[:40]} - {e}")
    
    # Calculate metrics
    results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0
    results["avg_latency_ms"] = sum(results["latencies"]) / len(results["latencies"]) if results["latencies"] else 0
    
    for category in results["by_category"]:
        cat = results["by_category"][category]
        cat["accuracy"] = cat["correct"] / cat["total"] if cat["total"] > 0 else 0
    
    return results


def evaluate_llm_based(test_queries: List[Tuple]) -> Dict:
    """Evaluate LLM-based classification only"""
    
    print("\n" + "="*70)
    print("EVALUATING: LLM-BASED CLASSIFICATION")
    print("="*70)
    
    try:
        from src.retrieval.llm_intent_classifier import LLMIntentClassifier
        
        classifier = LLMIntentClassifier()
        
    except ImportError as e:
        print(f"Error importing LLMIntentClassifier: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Error initializing LLM classifier: {e}")
        print("Make sure GROQ_API_KEY is set")
        return {"error": str(e)}
    
    results = {
        "correct": 0,
        "total": len(test_queries),
        "by_category": {"TECHNICAL": {"correct": 0, "total": 0}, 
                        "SUPPORT": {"correct": 0, "total": 0}},
        "latencies": [],
        "errors": []
    }
    
    for query, lang, ground_truth, description in test_queries:
        try:
            result = classifier.classify(query, lang)
            
            predicted = result["intent"]
            latency_ms = result["latency_ms"]
            correct = (predicted == ground_truth)
            
            results["latencies"].append(latency_ms)
            results["by_category"][ground_truth]["total"] += 1
            
            if correct:
                results["correct"] += 1
                results["by_category"][ground_truth]["correct"] += 1
                status = "✓"
            else:
                status = "✗"
            
            print(f"{status} {description[:40]:40} | Predicted: {predicted:10} | Truth: {ground_truth:10} | {latency_ms:.0f}ms")
            print(f"   Reasoning: {result['reasoning'][:70]}")
            
        except Exception as e:
            results["errors"].append(str(e))
            print(f"✗ Error on query: {query[:40]} - {e}")
    
    # Calculate metrics
    results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0
    results["avg_latency_ms"] = sum(results["latencies"]) / len(results["latencies"]) if results["latencies"] else 0
    
    for category in results["by_category"]:
        cat = results["by_category"][category]
        cat["accuracy"] = cat["correct"] / cat["total"] if cat["total"] > 0 else 0
    
    return results


def evaluate_hybrid(test_queries: List[Tuple]) -> Dict:
    """Evaluate hybrid (rule + LLM) classification"""
    
    print("\n" + "="*70)
    print("EVALUATING: HYBRID CLASSIFICATION (RECOMMENDED)")
    print("="*70)
    
    try:
        from src.retrieval.hybrid_smart_retriever import HybridSmartRetriever
        
        # Mock VSM
        class MockVSM:
            def search(self, *args, **kwargs):
                return {"results": []}
        
        retriever = HybridSmartRetriever(MockVSM(), use_llm=True, llm_confidence_threshold=0.8)
        
    except ImportError as e:
        print(f"Error importing HybridSmartRetriever: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Error initializing hybrid retriever: {e}")
        return {"error": str(e)}
    
    results = {
        "correct": 0,
        "total": len(test_queries),
        "by_category": {"TECHNICAL": {"correct": 0, "total": 0}, 
                        "SUPPORT": {"correct": 0, "total": 0}},
        "by_method": {"rules_only": 0, "llm_fallback": 0},
        "latencies": [],
        "errors": []
    }
    
    for query, lang, ground_truth, description in test_queries:
        try:
            intent, confidence, debug = retriever.detect_intent_hybrid(query, lang)
            
            predicted = intent.value.upper()
            latency_ms = debug.get("latency_ms", 0)
            method = debug.get("method", "unknown")
            correct = (predicted == ground_truth)
            
            results["latencies"].append(latency_ms)
            results["by_category"][ground_truth]["total"] += 1
            results["by_method"][method] = results["by_method"].get(method, 0) + 1
            
            if correct:
                results["correct"] += 1
                results["by_category"][ground_truth]["correct"] += 1
                status = "✓"
            else:
                status = "✗"
            
            print(f"{status} {description[:40]:40} | Predicted: {predicted:10} | Method: {method:15} | {latency_ms:.0f}ms")
            
        except Exception as e:
            results["errors"].append(str(e))
            print(f"✗ Error on query: {query[:40]} - {e}")
    
    # Calculate metrics
    results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0
    results["avg_latency_ms"] = sum(results["latencies"]) / len(results["latencies"]) if results["latencies"] else 0
    
    for category in results["by_category"]:
        cat = results["by_category"][category]
        cat["accuracy"] = cat["correct"] / cat["total"] if cat["total"] > 0 else 0
    
    return results


def print_comparison(rule_results: Dict, llm_results: Dict, hybrid_results: Dict):
    """Print comparison table"""
    
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    
    print(f"\n{'Metric':<30} {'Rule-Based':<15} {'LLM-Based':<15} {'Hybrid':<15}")
    print("-" * 70)
    
    # Overall accuracy
    rule_acc = rule_results.get("accuracy", 0) * 100
    llm_acc = llm_results.get("accuracy", 0) * 100
    hybrid_acc = hybrid_results.get("accuracy", 0) * 100
    
    print(f"{'Overall Accuracy':<30} {rule_acc:>14.1f}% {llm_acc:>14.1f}% {hybrid_acc:>14.1f}%")
    
    # Category accuracy
    for category in ["TECHNICAL", "SUPPORT"]:
        rule_cat_acc = rule_results.get("by_category", {}).get(category, {}).get("accuracy", 0) * 100
        llm_cat_acc = llm_results.get("by_category", {}).get(category, {}).get("accuracy", 0) * 100
        hybrid_cat_acc = hybrid_results.get("by_category", {}).get(category, {}).get("accuracy", 0) * 100
        
        print(f"{category + ' Accuracy':<30} {rule_cat_acc:>14.1f}% {llm_cat_acc:>14.1f}% {hybrid_cat_acc:>14.1f}%")
    
    # Latency
    rule_lat = rule_results.get("avg_latency_ms", 0)
    llm_lat = llm_results.get("avg_latency_ms", 0)
    hybrid_lat = hybrid_results.get("avg_latency_ms", 0)
    
    print(f"{'Average Latency':<30} {rule_lat:>13.0f}ms {llm_lat:>13.0f}ms {hybrid_lat:>13.0f}ms")
    
    # Hybrid method breakdown
    if "by_method" in hybrid_results:
        print(f"\n{'Hybrid Method Usage:':<30}")
        for method, count in hybrid_results["by_method"].items():
            pct = (count / hybrid_results["total"] * 100) if hybrid_results["total"] > 0 else 0
            print(f"  {method:<28} {count:>3} ({pct:>5.1f}%)")
    
    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)
    
    # Determine best method
    if hybrid_acc >= max(rule_acc, llm_acc) and hybrid_lat < llm_lat:
        print("✓ HYBRID method recommended:")
        print(f"  - Best accuracy ({hybrid_acc:.1f}%)")
        print(f"  - Balanced latency ({hybrid_lat:.0f}ms)")
        print(f"  - {hybrid_results['by_method'].get('rules_only', 0)} queries used fast path")
    elif llm_acc > rule_acc and (llm_acc - rule_acc) > 5:
        print("✓ LLM method recommended:")
        print(f"  - Significantly better accuracy (+{llm_acc - rule_acc:.1f}%)")
        print(f"  - Latency acceptable ({llm_lat:.0f}ms)")
    else:
        print("✓ Rule-based sufficient:")
        print(f"  - Good accuracy ({rule_acc:.1f}%)")
        print(f"  - Fastest latency ({rule_lat:.0f}ms)")
    
    print("="*70)


def save_results(rule_results, llm_results, hybrid_results, filename="evaluation_results.json"):
    """Save results to JSON file"""
    
    results = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_queries_count": len(TEST_QUERIES),
        "rule_based": rule_results,
        "llm_based": llm_results,
        "hybrid": hybrid_results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {filename}")


def run_evaluation():
    """Run complete evaluation"""
    
    print("\n" + "="*70)
    print("PHASE 6 ROUTING METHOD EVALUATION")
    print("="*70)
    print(f"Test queries: {len(TEST_QUERIES)}")
    print(f"  TECHNICAL: {sum(1 for q in TEST_QUERIES if q[2] == 'TECHNICAL')}")
    print(f"  SUPPORT: {sum(1 for q in TEST_QUERIES if q[2] == 'SUPPORT')}")
    
    # Evaluate all three methods
    rule_results = evaluate_rule_based(TEST_QUERIES)
    
    print("\n" + "="*70)
    input("Press Enter to continue with LLM evaluation (will make API calls)...")
    
    llm_results = evaluate_llm_based(TEST_QUERIES)
    hybrid_results = evaluate_hybrid(TEST_QUERIES)
    
    # Print comparison
    print_comparison(rule_results, llm_results, hybrid_results)
    
    # Save results
    save_results(rule_results, llm_results, hybrid_results)
    
    return rule_results, llm_results, hybrid_results


if __name__ == "__main__":
    run_evaluation()
