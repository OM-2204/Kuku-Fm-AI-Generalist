"""Cost-controlled OpenAI evaluation for the heuristic shortlist.

The heuristic score is preserved. The LLM evaluates only the top N candidates,
returns schema-constrained JSON, and a deterministic hybrid score is calculated.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
DEFAULT_MAX_CANDIDATES = 10
DEFAULT_MAX_INPUT_CHARS = 12_000
DEFAULT_MAX_OUTPUT_TOKENS = 900
DEFAULT_RUN_BUDGET_USD = 0.25
# Standard text pricing per 1M tokens. Override via env if model pricing changes.
DEFAULT_INPUT_USD_PER_M = float(os.getenv("OPENAI_INPUT_USD_PER_M", "0.05"))
DEFAULT_OUTPUT_USD_PER_M = float(os.getenv("OPENAI_OUTPUT_USD_PER_M", "0.25"))

SCHEMA = {
    "type": "object",
    "properties": {
        "hook_score": {"type": "integer", "minimum": 0, "maximum": 10},
        "emotional_intensity": {"type": "integer", "minimum": 0, "maximum": 10},
        "conflict_tension": {"type": "integer", "minimum": 0, "maximum": 10},
        "cliffhanger_score": {"type": "integer", "minimum": 0, "maximum": 10},
        "standalone_clarity": {"type": "integer", "minimum": 0, "maximum": 10},
        "llm_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "hook_explanation": {"type": "string", "maxLength": 300},
        "cliffhanger_explanation": {"type": "string", "maxLength": 300},
        "why_it_works": {"type": "string", "maxLength": 500},
        "weaknesses": {"type": "array", "items": {"type": "string", "maxLength": 180}},
        "recommendation": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    },
    "required": ["hook_score", "emotional_intensity", "conflict_tension", "cliffhanger_score", "standalone_clarity", "llm_score", "hook_explanation", "cliffhanger_explanation", "why_it_works", "weaknesses", "recommendation"],
    "additionalProperties": False
}


def _candidate_payload(candidate: dict[str, Any], max_chars: int) -> dict[str, Any]:
    excerpt = str(candidate.get("context_excerpt") or "")[:max_chars]
    return {
        "episode": candidate.get("episode", "Unknown"),
        "episode_logline": str(candidate.get("episode_logline", ""))[:1000],
        "start": candidate.get("start"),
        "end": candidate.get("end"),
        "duration_seconds": candidate.get("duration_seconds"),
        "heuristic_score": candidate.get("score"),
        "current_hook": str(candidate.get("hook", ""))[:500],
        "current_cliffhanger": str(candidate.get("cliffhanger", ""))[:500],
        "screenplay_excerpt": excerpt,
    }


def estimate_cost(input_chars: int, output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> float:
    # Conservative rough estimate: ~4 characters per token plus prompt overhead.
    input_tokens = int(input_chars / 4) + 700
    return (input_tokens * DEFAULT_INPUT_USD_PER_M + output_tokens * DEFAULT_OUTPUT_USD_PER_M) / 1_000_000


def hybrid_score(heuristic_score: float, llm_score: float, heuristic_weight: float = 0.4) -> float:
    return round(heuristic_weight * float(heuristic_score) + (1 - heuristic_weight) * float(llm_score), 2)


def _extract_json(response: Any) -> dict[str, Any]:
    # Responses API SDK exposes output_text. Keep a defensive fallback for SDK variations.
    raw = getattr(response, "output_text", None)
    if not raw:
        raise ValueError("OpenAI returned no output_text (possibly refusal or incomplete response).")
    status = getattr(response, "status", None)
    if status and status != "completed":
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None) if details else None
        raise ValueError(f"OpenAI response was not completed (status={status}, reason={reason}).")
    parsed = json.loads(raw)
    required = SCHEMA["required"]
    missing = [key for key in required if key not in parsed]
    if missing:
        raise ValueError(f"Structured response missing fields: {missing}")
    for key in ("hook_score", "emotional_intensity", "conflict_tension", "cliffhanger_score", "standalone_clarity", "llm_score"):
        if not isinstance(parsed[key], int) or not 0 <= parsed[key] <= (100 if key == "llm_score" else 10):
            raise ValueError(f"Invalid score returned for {key}")
    return parsed


def evaluate_one(client: Any, candidate: dict[str, Any], model: str = DEFAULT_MODEL,
                 max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
                 max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> tuple[dict[str, Any], dict[str, int]]:
    payload = _candidate_payload(candidate, max_input_chars)
    instructions = (
        "You are a short-form drama promo editor. Evaluate only evidence in the supplied screenplay excerpt. "
        "A strong promo is 20-60 seconds, understandable to a new viewer, opens with an immediate hook "
        "within roughly 3 seconds, builds emotion/conflict, and ends on an unresolved beat. Do not invent "
        "events or dialogue. If the excerpt does not prove a point, score conservatively and mention the gap. "
        "Score each dimension from 0 to 10. llm_score must equal the rounded sum of the five dimension scores "
        "multiplied by 2. Return concise, actionable explanations."
    )
    request = {
        "model": model,
        "instructions": instructions,
        "input": json.dumps(payload, ensure_ascii=False),
        "max_output_tokens": max_output_tokens,
        "text": {"format": {"type": "json_schema", "name": "promo_candidate_review", "strict": True, "schema": SCHEMA}},
    }
    try:
        response = client.responses.create(**request)
        parsed = _extract_json(response)
    except (ValueError, json.JSONDecodeError) as first_error:
        # One bounded retry for incomplete/truncated output; no unbounded retry loop.
        retry_request = dict(request)
        retry_request["max_output_tokens"] = min(max_output_tokens * 2, 1800)
        try:
            response = client.responses.create(**retry_request)
            parsed = _extract_json(response)
        except Exception as retry_error:
            raise ValueError(f"Structured output failed after one retry. First attempt: {first_error}; retry: {retry_error}") from retry_error
    usage = getattr(response, "usage", None)
    usage_data = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    return parsed, usage_data


def evaluate_top_candidates(candidates: list[dict[str, Any]], output_dir: str | Path,
                            api_key: str | None = None, top_n: int = DEFAULT_MAX_CANDIDATES,
                            model: str = DEFAULT_MODEL, run_budget_usd: float = DEFAULT_RUN_BUDGET_USD,
                            heuristic_weight: float = 0.4, max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
                            max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
                            sleep_seconds: float = 0.15) -> dict[str, Any]:
    """Evaluate top candidates. Failures are recorded; heuristic ranking remains usable."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your local .env file or Streamlit secrets.")
    if not candidates:
        raise ValueError("No heuristic candidates available. Run the promo finder first.")
    if not 1 <= int(top_n) <= 10:
        raise ValueError("Cost-control limit: this prototype allows 1–10 LLM candidates per run.")
    shortlist = sorted(candidates, key=lambda x: float(x.get("score", 0)), reverse=True)[:top_n]
    estimated = sum(estimate_cost(len(json.dumps(_candidate_payload(c, max_input_chars), ensure_ascii=False)), max_output_tokens) for c in shortlist)
    if estimated > run_budget_usd:
        raise ValueError(f"Estimated run cost ${estimated:.5f} exceeds the configured ${run_budget_usd:.2f} budget. Reduce candidates/context or raise the local limit deliberately.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI SDK is not installed. Run: pip install -r requirements.txt") from exc

    client = OpenAI(api_key=key, timeout=45.0, max_retries=1)
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    cache_path = output / "openai_eval_cache.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except Exception:
        cache = {}

    results = []
    total_input = total_output = calls = cache_hits = 0
    failures = []
    for index, candidate in enumerate(shortlist, 1):
        payload = _candidate_payload(candidate, max_input_chars)
        fingerprint = hashlib.sha256((model + json.dumps(payload, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()
        try:
            was_cached = fingerprint in cache
            if was_cached:
                evaluation = cache[fingerprint]["evaluation"]
                usage = cache[fingerprint].get("usage", {"input_tokens": 0, "output_tokens": 0})
                cache_hits += 1
            else:
                evaluation, usage = evaluate_one(client, candidate, model, max_input_chars, max_output_tokens)
                calls += 1
                total_input += usage["input_tokens"]; total_output += usage["output_tokens"]
                cache[fingerprint] = {"evaluation": evaluation, "usage": usage, "cached_at": time.time()}
                cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
                if sleep_seconds and index < len(shortlist): time.sleep(sleep_seconds)
            row = dict(candidate)
            row.update({f"llm_{k}": v for k, v in evaluation.items()})
            row["llm_score"] = evaluation["llm_score"]
            row["hybrid_score"] = hybrid_score(candidate.get("score", 0), evaluation["llm_score"], heuristic_weight)
            row["heuristic_rank"] = None
            row["llm_rank"] = None
            row["hybrid_rank"] = None
            row["llm_status"] = "cached" if was_cached else "evaluated"
            results.append(row)
        except Exception as exc:
            failures.append({"episode": candidate.get("episode"), "start": candidate.get("start"), "error": f"{type(exc).__name__}: {exc}"})
            row = dict(candidate)
            row.update({"llm_score": None, "hybrid_score": None, "fallback_heuristic_score": float(candidate.get("score", 0)), "llm_status": "failed", "llm_error": str(exc)})
            results.append(row)

    # Preserve baseline ordering for every row and show LLM/hybrid comparisons for successful rows.
    for rank, row in enumerate(sorted(results, key=lambda x: float(x.get("score", 0)), reverse=True), 1): row["heuristic_rank"] = rank
    successful = [row for row in results if row.get("llm_score") is not None]
    failed_rows = [row for row in results if row.get("llm_score") is None]
    for rank, row in enumerate(sorted(successful, key=lambda x: float(x.get("llm_score", 0)), reverse=True), 1): row["llm_rank"] = rank
    for row in failed_rows: row["llm_rank"] = None
    for rank, row in enumerate(sorted(successful, key=lambda x: float(x.get("hybrid_score", 0)), reverse=True), 1): row["hybrid_rank"] = rank
    for row in failed_rows: row["hybrid_rank"] = None
    # Successful hybrid evaluations appear first; failures are shown separately as heuristic-only fallbacks.
    results = sorted(successful, key=lambda x: float(x.get("hybrid_score", 0)), reverse=True) + sorted(failed_rows, key=lambda x: float(x.get("score", 0)), reverse=True)

    cost = (total_input * DEFAULT_INPUT_USD_PER_M + total_output * DEFAULT_OUTPUT_USD_PER_M) / 1_000_000
    report = {
        "model": model, "ranking_method": "hybrid", "heuristic_weight": heuristic_weight,
        "llm_weight": round(1 - heuristic_weight, 2), "requested_candidates": top_n,
        "evaluated_candidates": calls, "cache_hits": cache_hits, "failed_candidates": len(failures),
        "estimated_cost_before_run_usd": round(estimated, 6), "actual_usage_cost_usd": round(cost, 6),
        "input_tokens": total_input, "output_tokens": total_output,
        "budget_limit_usd": run_budget_usd, "failures": failures,
        "results": results,
        "note": "Heuristic scores and ranks are preserved. Failed LLM rows are excluded from hybrid ranking and shown separately with a heuristic-only fallback score."
    }
    (output / "promo_llm_comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    import csv
    fields = ["hybrid_rank", "heuristic_rank", "llm_rank", "episode", "start", "end", "duration_seconds", "score", "llm_score", "hybrid_score", "recommendation", "hook", "cliffhanger", "why_it_works", "llm_why_it_works", "llm_status", "fallback_heuristic_score", "llm_error"]
    with (output / "promo_llm_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(results)
    return report
