"""Probe real database opportunities directly with the specified MLX checkpoint."""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laya.questions import get_laya_seo_questions
from laya.decision import LAYA_PROMPT_VERSION


def distribution(values):
    values = sorted(values)
    return {"min": values[0], "median": statistics.median(values), "p90": values[int((len(values)-1)*0.9)], "max": values[-1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/seo.db")
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.count <= 500:
        parser.error("Probes are restricted to 1..500 existing candidates")
    with sqlite3.connect(Path(args.db).resolve().as_uri()+"?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute("SELECT * FROM opportunities ORDER BY type, opportunity_id LIMIT 500")]
        # Evenly sample the existing opportunity population, preserving real evidence.
        rows = [rows[i*len(rows)//args.count] for i in range(args.count)]
        candidates = []
        for opp in rows:
            urls = json.loads(opp["sample_urls_json"] or "[]")[:5]
            pages = [dict(p) for u in urls for p in conn.execute("SELECT * FROM pages WHERE crawl_id=? AND url=?", (opp["run_id"], u))]
            words = [int(p["word_count"] or 0) for p in pages]
            hashes = [p["content_hash"] for p in pages if p["content_hash"]]
            canonical = {"indexable": sum(bool(p["is_indexable"]) for p in pages), "non_indexable": sum(not bool(p["is_indexable"]) for p in pages), "canonical_statuses": dict(Counter(p["canonical_status"] or "unknown" for p in pages))}
            candidates.append({"cluster_id": "opportunity:"+opp["opportunity_id"], "issue": opp["observation"], "category": opp["type"], "severity": opp["opportunity_tier"].lower(), "template": opp["implementation_location"], "affected_urls_count": opp["affected_urls_count"], "canonical_indexability": canonical, "content_metrics": {"pages": len(pages), "min_words": min(words or [0]), "avg_words": round(sum(words)/max(len(words),1),1), "unique_content_hashes": len(set(hashes)), "duplicate_content_pages": len(hashes)-len(set(hashes))}, "link_metrics": {"avg_internal_links": round(sum(p["internal_links_count"] or 0 for p in pages)/max(len(pages),1),1)}, "evidence_refs": [opp["hypothesis"]], "root_cause": opp["observation"]})
    from laya.analyzer import LayaSEOAnalyzer
    backend = LayaSEOAnalyzer.get_singleton().get_backend()
    agent = backend._agent
    questions = get_laya_seo_questions()
    records = []
    for i, candidate in enumerate(candidates, 1):
        response = backend.predict({"message": json.dumps(candidate, sort_keys=True), "prompt_version": LAYA_PROMPT_VERSION}, questions)
        if set(response["answers"]) != set(questions):
            raise RuntimeError("Missing required model heads")
        records.append({"candidate": candidate, "answers": response["answers"]})
        if i % 20 == 0:
            print(f"Real MLX predictions: {i}/{len(candidates)}", flush=True)
    summary = {}
    for head in questions:
        answers = [r["answers"][head] for r in records]
        summary[head] = {"classes": dict(Counter(a["choice"] for a in answers)), "entropy_confidence": distribution([a["confidence"] for a in answers]), "chosen_probability": distribution([a["probabilities"][a["choice"]] for a in answers])}
    result = {"model": "aac6fef/laya-mlx", "checkpoint": str(agent.model_dir), "versions": {p: importlib.metadata.version(p) for p in ("laya-mlx", "mlx", "numpy")}, "prompt_version": LAYA_PROMPT_VERSION, "count": len(records), "temperature_raw": agent.temperature_raw, "temperature_by_options_raw": agent.temperature_by_options_raw, "temperature_by_options": agent.temperature_by_options, "summary": summary, "records": records}
    output = Path("reports/laya_probe.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
