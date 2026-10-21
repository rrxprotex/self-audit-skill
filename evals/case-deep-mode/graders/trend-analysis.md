# Grader: Trend Analysis

## Purpose
Verify that deep mode performs historical trend analysis on calibration.log and produces a valid trend report.

## Pass Criteria
1. `.claude/knowledge/calibration-trend-report.md` exists and is valid markdown
2. Report contains:
   - Sessions analyzed count
   - Overall calibration metrics (mean |Δ|, overconfidence rate, underconfidence rate)
   - By-layer analysis table
   - Persistent weak spots identified
   - New improvements noted
   - Recommendations section
3. If ≥3 sessions in log, trend direction (IMPROVING/DEGRADING/STABLE) computed
4. Calibration-report.md updated with "Cross-Model Validation" and "Calibration Trend" sections

## Fail Criteria
- File missing or not markdown
- Missing required sections
- No trend analysis when ≥3 sessions exist
- Metrics not computed from actual log data

## Evaluation Method
```python
import os

# Check trend report exists
assert os.path.exists('.claude/knowledge/calibration-trend-report.md'), "Trend report missing"

content = open('.claude/knowledge/calibration-trend-report.md').read()

required_sections = [
    "Sessions Analyzed",
    "Overall Calibration",
    "By Layer",
    "Persistent Weak Spots",
    "Recommendations"
]

for section in required_sections:
    assert section in content, f"Missing section: {section}"

# Check calibration report updated
report = open('.claude/knowledge/calibration-report.md').read()
assert "Cross-Model Validation" in report, "Cross-model section missing from report"
assert "Calibration Trend" in report, "Trend section missing from report"

print("Trend analysis valid")
```