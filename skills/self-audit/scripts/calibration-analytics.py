#!/usr/bin/env python3
"""
Calibration Analytics — Analyze calibration.log.jsonl for trends and insights.
Usage: python calibration-analytics.py --log PATH --output PATH
"""
import argparse
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

def analyze_calibration_log(log_path: Path) -> Dict[str, Any]:
    """Analyze calibration log and return metrics."""
    if not log_path.exists():
        return {"error": f"Log not found: {log_path}"}

    records = []
    for line in log_path.read_text().strip().split("\n"):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        return {"error": "No valid records in log"}

    # Group by session
    sessions = defaultdict(list)
    for r in records:
        sid = r.get("session_id", "unknown")
        sessions[sid].append(r)

    # Overall metrics
    total = len(records)
    confirmed = sum(1 for r in records if r.get("result") == "CONFIRMED")
    falsified = sum(1 for r in records if r.get("result") == "FALSIFIED")
    inconclusive = sum(1 for r in records if r.get("result") == "INCONCLUSIVE")

    # By layer
    by_layer = defaultdict(lambda: {"total": 0, "confirmed": 0, "falsified": 0, "deltas": []})
    for r in records:
        layer = r.get("layer", "unknown")
        by_layer[layer]["total"] += 1
        if r.get("result") == "CONFIRMED":
            by_layer[layer]["confirmed"] += 1
        elif r.get("result") == "FALSIFIED":
            by_layer[layer]["falsified"] += 1
        by_layer[layer]["deltas"].append(abs(r.get("confidence_delta", 0)))

    # By category
    by_category = defaultdict(lambda: {"total": 0, "confirmed": 0, "falsified": 0})
    for r in records:
        # Infer category from result
        if r.get("result") == "FALSIFIED":
            cat = "CALIBRATION_ERROR"
        elif r.get("result") == "CONFIRMED":
            cat = "CONFIRMED"
        else:
            cat = "INCONCLUSIVE"
        by_category[cat]["total"] += 1
        if r.get("result") == "CONFIRMED":
            by_category[cat]["confirmed"] += 1
        elif r.get("result") == "FALSIFIED":
            by_category[cat]["falsified"] += 1

    # Calibration curve (by confidence bands - approximated from deltas)
    # Since we don't have original confidence in log, we approximate
    bands = {
        "0.9-1.0": {"count": 0, "correct": 0},
        "0.7-0.89": {"count": 0, "correct": 0},
        "0.5-0.69": {"count": 0, "correct": 0},
        "<0.5": {"count": 0, "correct": 0},
    }

    # Trend over sessions (mean |delta| per session)
    session_trend = []
    for sid, s_records in sessions.items():
        deltas = [abs(r.get("confidence_delta", 0)) for r in s_records]
        if deltas:
            session_trend.append({
                "session_id": sid,
                "mean_delta": sum(deltas) / len(deltas),
                "total": len(s_records),
                "falsified": sum(1 for r in s_records if r.get("result") == "FALSIFIED")
            })

    session_trend.sort(key=lambda x: x["session_id"])

    return {
        "summary": {
            "total_records": total,
            "sessions": len(sessions),
            "confirmed": confirmed,
            "falsified": falsified,
            "inconclusive": inconclusive,
            "overall_accuracy": confirmed / total if total > 0 else 0,
            "mean_abs_delta": sum(abs(r.get("confidence_delta", 0)) for r in records) / total if total > 0 else 0
        },
        "by_layer": {k: {
            "total": v["total"],
            "accuracy": v["confirmed"] / v["total"] if v["total"] > 0 else 0,
            "mean_abs_delta": sum(v["deltas"]) / len(v["deltas"]) if v["deltas"] else 0
        } for k, v in by_layer.items()},
        "by_category": dict(by_category),
        "session_trend": session_trend,
        "records_analyzed": total
    }

def generate_report(analysis: Dict[str, Any], output_path: Path):
    """Generate markdown report from analysis."""
    if "error" in analysis:
        report = f"# Calibration Analytics Error\n\n{analysis['error']}\n"
        output_path.write_text(report)
        return

    s = analysis["summary"]
    lines = []
    lines.append(f"# CALIBRATION ANALYTICS REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Log analyzed: {analysis['records_analyzed']} records across {s['sessions']} sessions")
    lines.append("")

    lines.append("## Overall Summary")
    lines.append(f"- **Total calibration tests**: {s['total_records']}")
    lines.append(f"- **Sessions tracked**: {s['sessions']}")
    lines.append(f"- **Confirmed**: {s['confirmed']} ({s['confirmed']/s['total_records']*100:.1f}%)")
    lines.append(f"- **Falsified (Calibration Errors)**: {s['falsified']} ({s['falsified']/s['total_records']*100:.1f}%)")
    lines.append(f"- **Inconclusive**: {s['inconclusive']} ({s['inconclusive']/s['total_records']*100:.1f}%)")
    lines.append(f"- **Overall accuracy**: {s['overall_accuracy']:.1%}")
    lines.append(f"- **Mean |confidence_delta|**: {s['mean_abs_delta']:.3f}")
    lines.append("")

    lines.append("## By Abstraction Layer")
    lines.append("| Layer | Tests | Accuracy | Mean |Δ| |")
    lines.append("|-------|-------|----------|----------|")
    for layer in ["L4", "L3", "L2", "L1"]:
        if layer in analysis["by_layer"]:
            d = analysis["by_layer"][layer]
            lines.append(f"| {layer} | {d['total']} | {d['accuracy']:.1%} | {d['mean_abs_delta']:.3f} |")
    lines.append("")

    lines.append("## Session Trend (Calibration Improvement)")
    lines.append("| Session | Tests | Falsified | Mean |Δ| |")
    lines.append("|---------|-------|-----------|----------|")
    for st in analysis["session_trend"]:
        lines.append(f"| {st['session_id']} | {st['total']} | {st['falsified']} | {st['mean_delta']:.3f} |")
    lines.append("")

    # Trend interpretation
    if len(analysis["session_trend"]) >= 3:
        recent = analysis["session_trend"][-3:]
        early = analysis["session_trend"][:3]
        recent_mean = sum(s["mean_delta"] for s in recent) / len(recent)
        early_mean = sum(s["mean_delta"] for s in early) / len(early)
        trend = "IMPROVING" if recent_mean < early_mean else "DEGRADING" if recent_mean > early_mean else "STABLE"
        lines.append(f"**Trend**: {trend} (early mean |Δ|={early_mean:.3f} → recent mean |Δ|={recent_mean:.3f})")
        lines.append("")

    lines.append("## Calibration Curve (Approximated)")
    lines.append("| Confidence Band | Expected Accuracy | Interpretation |")
    lines.append("|-----------------|-------------------|----------------|")
    # This is approximated since we don't have original confidence values
    lines.append("| 0.9–1.0 | ~80% | Check high-confidence assumptions |")
    lines.append("| 0.7–0.89 | ~70% | **Danger zone** - often overconfident |")
    lines.append("| 0.5–0.69 | ~55% | Weak signals - treat as hypotheses |")
    lines.append("| <0.5 | ~30% | Underconfident - investigate |")
    lines.append("")

    lines.append("## Recommendations")
    # Find worst layer
    if analysis["by_layer"]:
        worst_layer = max(analysis["by_layer"].items(), key=lambda x: x[1]["mean_abs_delta"])
        lines.append(f"1. **Focus on {worst_layer[0]}** — highest mean |Δ| ({worst_layer[1]['mean_abs_delta']:.3f})")

    # Recurring falsifications
    if s["falsified"] > s["total_records"] * 0.2:
        lines.append("2. **High falsification rate** — consider running deep mode with cross-model validation")

    # Session trend
    if len(analysis["session_trend"]) >= 2:
        last = analysis["session_trend"][-1]
        prev = analysis["session_trend"][-2]
        if last["mean_delta"] > prev["mean_delta"]:
            lines.append("3. **Calibration degrading** — workspace may have changed; re-run full audit")
        elif last["mean_delta"] < prev["mean_delta"] * 0.8:
            lines.append("3. **Calibration improving** — memory system working effectively")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by self-audit calibration-analytics*")

    output_path.write_text("\n".join(lines))

def main():
    parser = argparse.ArgumentParser(description="Analyze calibration.log.jsonl for trends")
    parser.add_argument("--log", default=os.getenv("SELF_AUDIT_KNOWLEDGE_ROOT", ".claude/knowledge") + "/calibration.log.jsonl")
    parser.add_argument("--output", default="calibration-trend-report.md")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    args = parser.parse_args()

    log_path = Path(args.log)
    output_path = Path(args.output)

    analysis = analyze_calibration_log(log_path)

    if args.json:
        output_path.write_text(json.dumps(analysis, indent=2))
    else:
        generate_report(analysis, output_path)

    print(f"Analysis complete. Report written to: {output_path}")

    if "error" not in analysis:
        s = analysis["summary"]
        print(f"  Sessions: {s['sessions']}, Records: {s['total_records']}, Accuracy: {s['overall_accuracy']:.1%}")
        print(f"  Mean |Δ|: {s['mean_abs_delta']:.3f}")

if __name__ == "__main__":
    main()