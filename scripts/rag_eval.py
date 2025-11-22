from __future__ import annotations

"""
Lightweight RAG evaluation script using a golden set of queries and keyword checks.

Usage:
  python scripts/rag_eval.py --golden eval/golden.jsonl --min-score 0.0
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List
import asyncio


async def _run_query(query: str) -> str:
    # call pipeline directly
    from src.rag.rag_pipeline import RAGPipeline
    from src.rag.prompt_templates import PromptType

    pipe = RAGPipeline()
    out = await pipe.process_query(query=query, query_type=PromptType.GENERAL_CHAT, user_context={})
    if out.get("success"):
        return str(out.get("response", ""))
    return ""


def score_response(resp: str, expected_keywords: List[str]) -> float:
    if not expected_keywords:
        return 1.0
    resp_lower = resp.lower()
    hits = sum(1 for k in expected_keywords if k.lower() in resp_lower)
    return hits / max(1, len(expected_keywords))


async def evaluate(golden_path: Path, min_score: float) -> float:
    items: List[Dict[str, Any]] = []
    with golden_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    if not items:
        print("No golden items; passing by default.")
        return 1.0

    scores: List[float] = []
    for it in items:
        q = str(it.get("query", "")).strip()
        if not q:
            continue
        expected = it.get("expected_keywords", []) or []
        resp = await _run_query(q)
        s = score_response(resp, expected)
        scores.append(s)
        print(json.dumps({"query": q, "score": s}, ensure_ascii=False))

    avg = sum(scores) / max(1, len(scores))
    print(json.dumps({"avg": avg, "min_score": min_score}, ensure_ascii=False))
    return avg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", type=str, default="eval/golden.jsonl")
    ap.add_argument("--min-score", type=float, default=0.0)
    args = ap.parse_args()

    golden = Path(args.golden)
    if not golden.exists():
        print(f"Golden set not found: {golden}")
        return 0
    avg = asyncio.run(evaluate(golden, args.min_score))
    return 0 if avg >= args.min_score else 1


if __name__ == "__main__":
    raise SystemExit(main())


