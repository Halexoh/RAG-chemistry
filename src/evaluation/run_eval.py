"""Runs every case in testset.py through the full RAG pipeline and scores it.

No LLM-as-judge here on purpose: it would add another model's own
correctness as a dependency of the evaluation itself. These metrics are
deliberately simpler and fully deterministic (keyword/book/citation
matching), at the cost of being approximate rather than a true measure
of answer quality. Good enough to catch regressions; not a substitute
for reading the actual answers (see docs/07-evaluacion.md).
"""

import json
import time
from datetime import datetime
from pathlib import Path

from src.evaluation.metrics import book_hit, citation_is_valid, extract_citations, is_refusal, keyword_hit
from src.evaluation.testset import TEST_CASES
from src.generation.answer import answer_question

RESULTS_DIR = Path("eval/results")


def evaluate_case(case: dict) -> dict:
    t0 = time.time()
    result = answer_question(case["query"])
    elapsed = time.time() - t0

    sources = result["sources"]
    answer = result["answer"]
    citations = extract_citations(answer)

    record = {
        "query": case["query"],
        "in_domain": case["in_domain"],
        "answer": answer,
        "n_sources": len(sources),
        "n_citations": len(citations),
        "is_refusal": is_refusal(answer),
        "elapsed_seconds": round(elapsed, 2),
    }

    if case["in_domain"]:
        record["keyword_hit"] = keyword_hit(sources, case["expected_keywords"])
        if "expected_book" in case:
            record["book_hit"] = book_hit(sources, case["expected_book"])
        record["all_citations_valid"] = (
            all(citation_is_valid(c, sources) for c in citations) if citations else False
        )
    else:
        record["fabricated_citation"] = len(citations) > 0

    return record


def summarize(records: list[dict]) -> dict:
    in_domain = [r for r in records if r["in_domain"]]
    out_domain = [r for r in records if not r["in_domain"]]

    def rate(items, key):
        relevant = [i for i in items if key in i]
        return round(sum(1 for i in relevant if i[key]) / len(relevant), 2) if relevant else None

    return {
        "n_in_domain": len(in_domain),
        "n_out_of_domain": len(out_domain),
        "keyword_hit_rate": rate(in_domain, "keyword_hit"),
        "book_hit_rate": rate(in_domain, "book_hit"),
        "citation_validity_rate": rate(in_domain, "all_citations_valid"),
        "out_of_domain_refusal_rate": rate(out_domain, "is_refusal"),
        "out_of_domain_fabricated_citation_rate": rate(out_domain, "fabricated_citation"),
        "avg_latency_seconds": round(sum(r["elapsed_seconds"] for r in records) / len(records), 2),
    }


def main():
    records = [evaluate_case(case) for case in TEST_CASES]
    summary = summarize(records)

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()
