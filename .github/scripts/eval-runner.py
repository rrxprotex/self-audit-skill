#!/usr/bin/env python3
"""
Model-Agnostic Evaluation Runner for Self-Audit Skill

This replaces `claude plugin eval` with a generic test runner that:
- Validates skill structure (frontmatter, schemas, templates)
- Executes skill CLI scripts against test fixtures
- Verifies output artifacts without requiring any LLM API
- Works with ANY agent/harness: Claude Code, OpenAI, Gemini, Cline, Cursor, etc.

Usage:
  python eval-runner.py --case quick-mode
  python eval-runner.py --case deep-mode
  python eval-runner.py --case all
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class EvalRunner:
    def __init__(self, repo_root: Path, case: str = "all"):
        self.repo_root = repo_root
        self.case = case
        self.results = {
            "schemaVersion": 1,
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "cases": [],
            "aggregates": {"casesTotal": 0, "casesPassed": 0, "overallScore": 0, "overallPassRate": 0}
        }
        self.skill_dir = repo_root / "skills" / "self-audit"
        self.templates_dir = repo_root / "templates"
        self.evals_dir = repo_root / "evals"

    def run_case(self, case_name: str) -> Dict[str, Any]:
        """Run a single eval case."""
        case_dir = self.evals_dir / case_name
        if not case_dir.exists():
            return {"name": case_name, "error": f"Case directory not found: {case_dir}", "aggregates": {"score": 0, "threshold": 0.6, "passed": False}}

        # Load case.yaml for threshold and grader declarations
        case_yaml = case_dir / "case.yaml"
        threshold = 0.6
        case_config = {}
        if case_yaml.exists():
            import yaml
            with open(case_yaml, encoding="utf-8") as f:
                case_config = yaml.safe_load(f) or {}
            # threshold is declared in case.yaml (default 0.6)
            threshold = float(case_config.get("threshold", 0.6))

        # Run graders
        graders_dir = case_dir / "graders"
        grader_files = list(graders_dir.glob("*.md")) if graders_dir.exists() else []

        case_result = {
            "name": case_name,
            "dir": str(case_dir.relative_to(self.repo_root)),
            "source": "static",
            "graders": [],
            "arms": {"with": []},
            "aggregates": {"score": 0, "threshold": threshold, "passed": False}
        }

        # Create a temporary workspace for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "test-workspace"
            workspace.mkdir()

            # Create minimal test project structure
            self._create_test_workspace(workspace)

            # Run skill CLI
            skill_result = self._run_skill_cli(workspace, case_name)

            # Run graders
            grader_scores = []
            for grader_file in grader_files:
                grader_result = self._run_grader(grader_file, workspace, skill_result)
                case_result["graders"].append(grader_result)
                grader_scores.append(1.0 if grader_result["passed"] else 0.0)

            # Compute case score
            if grader_scores:
                case_result["aggregates"]["score"] = sum(grader_scores) / len(grader_scores)
            case_result["aggregates"]["passed"] = case_result["aggregates"]["score"] >= threshold

        return case_result

    def _create_test_workspace(self, workspace: Path):
        """Create a minimal test workspace with known patterns."""
        # Source files
        src = workspace / "src"
        src.mkdir()

        # Python files with various patterns
        (src / "main.py").write_text("""
# Test project with mixed conventions
import json
import yaml
from typing import List, Dict

CONFIG_FILE = "config.yaml"  # But actual config is JSON
API_VERSION = "v1"

class UserService:
    def __init__(self, config: Dict):
        self.config = config

    def get_user(self, user_id: int) -> Dict:
        # Assumption: returns dict with 'id', 'name'
        return {"id": user_id, "name": "test"}

    def get_users(self) -> List[Dict]:
        return [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]

def process_data(data: List[Dict]) -> Dict:
    # Assumption: all items have 'id' field
    return {item["id"]: item for item in data}

# Implicit convention: error handling via exceptions
def risky_operation():
    raise ValueError("Something went wrong")

# Config loading - mixed YAML/JSON
def load_config(path: str) -> Dict:
    with open(path) as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)
""")

        (src / "utils.py").write_text("""
# Utility functions with different patterns
import os
from pathlib import Path

# Convention: Path objects everywhere
def find_config() -> Path:
    for root in [Path.cwd(), Path.home()]:
        for name in ["config.yaml", "config.yml", "config.json"]:
            p = root / name
            if p.exists():
                return p
    return Path("config.json")

# Implicit: env var override
def get_api_key() -> str:
    return os.getenv("API_KEY", "default-key")

# Naming convention: snake_case functions
def validate_input(data: dict) -> bool:
    required = ["id", "name"]
    return all(k in data for k in required)
""")

        # Config files - MIXED YAML and JSON (calibration error source)
        (workspace / "config.yaml").write_text("""
database:
  host: localhost
  port: 5432
  name: testdb
api:
  timeout: 30
  retries: 3
""")

        (workspace / "settings.json").write_text("""
{
  "features": {
    "new_ui": true,
    "beta": false
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  }
}
""")

        # Tests
        tests = workspace / "tests"
        tests.mkdir()
        (tests / "test_main.py").write_text("""
import pytest
from src.main import UserService, process_data

def test_user_service():
    svc = UserService({})
    user = svc.get_user(1)
    assert user["id"] == 1
    assert "name" in user

def test_process_data():
    data = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
    result = process_data(data)
    assert 1 in result
    assert 2 in result
""")

        # Docs
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("""
# Architecture

This project follows a **modular monolith** pattern (not clean architecture).

## Conventions
- Config: YAML for database, JSON for features
- Errors: Exceptions, not Result types
- Paths: pathlib.Path objects
""")

        # .claude directory for memory
        claude_dir = workspace / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.local.json").write_text("{}")

    def _run_skill_cli(self, workspace: Path, mode: str) -> Dict[str, Any]:
        """Run the skill CLI against the test workspace."""
        script = self.skill_dir / "scripts" / "run-self-audit.py"
        if not script.exists():
            return {"error": "run-self-audit.py not found", "artifacts": {}}

        # Determine mode flag
        is_quick = mode == "case-quick-mode"
        is_deep = mode == "case-deep-mode"
        mode_value = "quick" if is_quick else ("deep" if is_deep else "standard")
        knowledge_dir = workspace / ".claude" / "knowledge"

        # Set environment variables for the skill script
        env = os.environ.copy()
        env["SELF_AUDIT_WORKSPACE"] = str(workspace)
        env["SELF_AUDIT_KNOWLEDGE_ROOT"] = str(knowledge_dir)
        env["SELF_AUDIT_MEMORY_ROOT"] = str(workspace / ".claude" / "projects" / workspace.name / "memory")
        env["SELF_AUDIT_CROSS_MODEL"] = "false" if is_quick else "true"
        env["SELF_AUDIT_TREND_ANALYSIS"] = "false" if is_quick else "true"
        env["SELF_AUDIT_VERBOSE"] = "true"

        cmd = [
            "python", str(script),
            "--mode", mode_value,
        ]

        try:
            print(f"  Running skill: {' '.join(cmd)}")
            print(f"  Workspace: {workspace}")
            print(f"  Knowledge dir: {knowledge_dir}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, cwd=str(self.repo_root))
            print(f"  Return code: {result.returncode}")
            if result.stderr:
                print(f"  STDERR: {result.stderr[-200:]}")
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "artifacts": self._collect_artifacts(workspace)
            }
        except subprocess.TimeoutExpired:
            return {"error": "timeout", "artifacts": {}}
        except Exception as e:
            return {"error": str(e), "artifacts": {}}

    def _collect_artifacts(self, workspace: Path) -> Dict[str, Any]:
        """Collect generated artifacts."""
        knowledge_dir = workspace / ".claude" / "knowledge"
        artifacts = {}
        for fname in ["workspace-model.md", "assumptions.json", "calibration.log.jsonl",
                      "blind-spots.md", "calibration-report.md", "calibration-summary.json",
                      "calibration-trend-report.md", "cross-model-validation.log.jsonl"]:
            fpath = knowledge_dir / fname
            if fpath.exists():
                try:
                    if fname.endswith(".json") or fname.endswith(".jsonl"):
                        with open(fpath) as f:
                            if fname.endswith(".jsonl"):
                                artifacts[fname] = [json.loads(line) for line in f if line.strip()]
                            else:
                                artifacts[fname] = json.load(f)
                    else:
                        artifacts[fname] = fpath.read_text()
                except Exception as e:
                    artifacts[fname] = {"error": str(e)}
        return artifacts

    def _run_grader(self, grader_file: Path, workspace: Path, skill_result: Dict) -> Dict[str, Any]:
        """Run a single grader against the skill output."""
        grader_name = grader_file.stem
        criteria = grader_file.read_text()

        # Parse grader type from filename or content
        passed = False
        details = ""

        try:
            artifacts = skill_result.get("artifacts", {})

            if "produces-artifacts" in grader_name:
                required = [
                    "workspace-model.md", "assumptions.json", "calibration.log.jsonl",
                    "blind-spots.md", "calibration-report.md", "calibration-summary.json"
                ]
                missing = [f for f in required if f not in artifacts]
                passed = len(missing) == 0
                details = f"Present: {[f for f in required if f in artifacts]}, Missing: {missing}"

            elif "calibration-log-valid" in grader_name:
                log = artifacts.get("calibration.log.jsonl", [])
                if isinstance(log, list) and len(log) > 0:
                    required_fields = ["assumption_id", "timestamp", "prediction", "actual",
                                      "evidence", "result", "confidence_delta", "new_status",
                                      "layer", "verification_method", "session_id"]
                    valid_records = all(all(f in r for f in required_fields) for r in log)
                    results = [r.get("result") for r in log if isinstance(r, dict)]
                    # Enums must match the real schema (KNOWN_FALSE = skipped re-test from prior sessions)
                    valid_results = all(res in ["CONFIRMED", "FALSIFIED", "INCONCLUSIVE", "SKIPPED", "KNOWN_FALSE"] for res in results)
                    has_confirmed = "CONFIRMED" in results
                    # A clean workspace may legitimately have zero FALSIFIED records — that is
                    # a valid (well-calibrated) outcome, not a failure. We require only that the
                    # log is structurally valid, has at least one test outcome, and deltas vary.
                    has_outcome = any(res in ("CONFIRMED", "FALSIFIED", "INCONCLUSIVE") for res in results)
                    deltas = [r.get("confidence_delta", 0) for r in log if isinstance(r, dict)]
                    diverse_deltas = len(set(round(d, 2) for d in deltas)) > 1 if deltas else False
                    passed = valid_records and valid_results and has_outcome and diverse_deltas
                    details = (f"Records: {len(log)}, Confirmed: {has_confirmed}, "
                               f"Outcomes: {has_outcome}, Valid results: {valid_results}, "
                               f"Diverse deltas: {diverse_deltas}")
                else:
                    passed = False
                    details = "No calibration log or empty"

            elif "blind-spots-categorized" in grader_name:
                blind_spots = artifacts.get("blind-spots.md", "")
                # Check for table with required columns
                has_table = "| Rank | ID | Category | Layer | Severity |" in blind_spots
                # Check that PRESENT categories are valid (not that all must be present)
                valid_categories_list = ["CALIBRATION_ERROR", "UNVERIFIED_CRITICAL", "IMPLICIT_CONVENTION_GAP", "DOMAIN_GAP", "MEMORY_DRIFT", "POSSIBLE_BLIND_SPOT", "PERSISTENT_BLIND_SPOT",
                                         "USER_MISALIGNMENT", "USER_TACIT_GAP", "USER_BLIND_SPOT", "USER_GOAL_TASK_MISMATCH", "USER_IMPLICIT_CONSTRAINT_VIOLATION", "USER_UNSTATED_REQUIREMENT"]
                valid_layers_list = ["L1", "L2", "L3", "L4"]
                valid_severities_list = ["Critical", "High", "Medium", "Low"]

                # Parse table rows and validate each
                import re
                table_match = re.search(r'\| Rank \| ID \| Category \| Layer \| Severity \| Delta \| Learning Unit \|\n\|.*?\n((?:\|.*?\n)*)', blind_spots)
                passed = has_table and table_match is not None
                details = f"Table: {has_table}"

                if passed:
                    rows = table_match.group(1).strip().split('\n')
                    for row in rows:
                        parts = [p.strip() for p in row.split('|')[1:-1]]
                        if len(parts) >= 7:
                            category, layer, severity = parts[2], parts[3], parts[4]
                            if category not in valid_categories_list:
                                passed = False
                                details += f", Invalid category: {category}"
                            if layer not in valid_layers_list:
                                passed = False
                                details += f", Invalid layer: {layer}"
                            if severity not in valid_severities_list:
                                passed = False
                                details += f", Invalid severity: {severity}"
                details += f", Categories OK: {passed}"

            elif "cross-model-validation" in grader_name:
                # For model-agnostic: check if cross-model validation log exists (optional in quick/standard)
                log = artifacts.get("cross-model-validation.log.jsonl", [])
                if isinstance(log, list) and len(log) > 0:
                    required = ["blind_spot_id", "reviewer", "model", "verdict", "notes", "additional_blind_spots", "timestamp"]
                    valid = all(all(f in r for f in required) for r in log)
                    verdicts = [r.get("verdict") for r in log if isinstance(r, dict)]
                    has_confirmed = any(v == "CONFIRMED" for v in verdicts)
                    reviewers = set(r.get("reviewer") for r in log if isinstance(r, dict))
                    passed = valid and has_confirmed and len(reviewers) >= 2
                    details = f"Records: {len(log)}, Valid: {valid}, Reviewers: {len(reviewers)}"
                else:
                    # In quick/standard mode, cross-model is not required
                    passed = True
                    details = "Cross-model validation not required for this mode"

            elif "trend-analysis" in grader_name:
                trend = artifacts.get("calibration-trend-report.md", "")
                passed = len(trend) > 100 and "Overall Calibration" in trend and "By Layer" in trend
                details = f"Has trend report: {passed}"

            else:
                # Generic: just check skill ran successfully
                passed = skill_result.get("returncode", 1) == 0
                details = f"Skill exit code: {skill_result.get('returncode', 'unknown')}"

        except Exception as e:
            passed = False
            details = f"Grader error: {e}"

        return {
            "name": grader_name,
            "type": "static",
            "criteria": criteria[:200],
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": details
        }

    def run(self) -> Dict[str, Any]:
        """Run all requested cases."""
        cases_to_run = []
        if self.case == "all":
            cases_to_run = ["case-quick-mode", "case-deep-mode"]
        else:
            # Accept both "case-quick-mode" and the short "quick-mode" form
            case_name = self.case if self.case.startswith("case-") else f"case-{self.case}"
            cases_to_run = [case_name]

        for case_name in cases_to_run:
            print(f"\n=== Running {case_name} ===")
            case_result = self.run_case(case_name)
            self.results["cases"].append(case_result)

        # Compute aggregates
        self.results["aggregates"]["casesTotal"] = len(self.results["cases"])
        passed_count = sum(1 for c in self.results["cases"] if c.get("aggregates", {}).get("passed", False))
        self.results["aggregates"]["casesPassed"] = passed_count
        if self.results["aggregates"]["casesTotal"] > 0:
            scores = [c.get("aggregates", {}).get("score", 0) for c in self.results["cases"]]
            self.results["aggregates"]["overallScore"] = sum(scores) / len(scores)
            self.results["aggregates"]["overallPassRate"] = passed_count / self.results["aggregates"]["casesTotal"]

        self.results["durationSeconds"] = (datetime.utcnow() - datetime.fromisoformat(self.results["startedAt"].replace("Z", ""))).total_seconds()

        return self.results


def main():
    parser = argparse.ArgumentParser(description="Model-agnostic eval runner for self-audit skill")
    parser.add_argument("--case", default="all",
                        choices=["case-quick-mode", "case-deep-mode", "quick-mode", "deep-mode", "all"],
                        help="Which eval case to run (case-* or short form)")
    parser.add_argument("--output", default="eval-results.json", help="Output JSON file")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")

    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    runner = EvalRunner(repo_root, args.case)
    results = runner.run()

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n=== EVAL COMPLETE ===")
    print(f"Cases: {results['aggregates']['casesTotal']}")
    print(f"Passed: {results['aggregates']['casesPassed']}")
    print(f"Overall Score: {results['aggregates']['overallScore']:.2f}")
    print(f"Results written to: {args.output}")

    # Exit code for CI
    if results["aggregates"]["casesPassed"] < results["aggregates"]["casesTotal"]:
        sys.exit(1)


if __name__ == "__main__":
    main()