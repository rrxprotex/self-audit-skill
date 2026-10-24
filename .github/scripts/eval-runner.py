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

            # Create minimal test project structure (case-specific for the
            # domain-layer case: the planned neutral inventory-management
            # fixture; shared fixture for the rest)
            if case_name == "case-domain-layer":
                self._create_domain_layer_workspace(workspace)
            else:
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

    def _create_domain_layer_workspace(self, workspace: Path):
        """Neutral inventory-management fixture for the domain-layer case.

        Deliberate properties (plan: Test C/D/E inputs):
        - two files repeat the same config-loading idiom (a candidate
          pattern over genuinely different content);
        - one file uses a superficially similar but differently-caused
          idiom (must not merge into the pattern);
        - docs claim a check (`verify_reservation_limits()`) that no code
          defines (blind-spot discovery);
        - two files have identical content (must count as ONE source).
        """
        src = workspace / "src"
        src.mkdir()
        (src / "orders.py").write_text(
            "# Inventory management: order intake\n"
            "import json\n"
            "def load_orders(path):\n"
            "    # shared loader idiom (occurrence 1)\n"
            "    with open(path) as f:\n"
            "        return json.load(f) if path.endswith('.json') else {}\n"
            "def reserve(item, qty):\n"
            "    return {'item': item, 'qty': qty, 'status': 'reserved'}\n")
        (src / "reservations.py").write_text(
            "# Inventory management: reservations\n"
            "import json\n"
            "def load_reservations(path):\n"
            "    # shared loader idiom (occurrence 2, different file/content)\n"
            "    with open(path) as f:\n"
            "        return json.load(f) if path.endswith('.json') else {}\n"
            "def hold(item, qty):\n"
            "    return {'item': item, 'qty': qty, 'status': 'hold'}\n")
        (src / "migration.py").write_text(
            "# Inventory management: one-off data migration\n"
            "import pickle\n"
            "def read_legacy(path):\n"
            "    # superficially similar loader call, different mechanism/cause\n"
            "    with open(path) as f:\n"
            "        return pickle.load(f) if path.endswith('.pkl') else {}\n")

        # Two identical-content files (copies — not independent sources)
        catalog_text = (
            "# Inventory catalog\n"
            "CATEGORIES = ['hardware', 'software', 'services']\n"
            "def category_path(name):\n"
            "    return '/'.join(['catalog', name])\n")
        (src / "catalog.py").write_text(catalog_text)
        (src / "catalog_backup.py").write_text(catalog_text)

        # Docs claim a check that exists nowhere in code
        docs = workspace / "docs"
        docs.mkdir()
        (docs / "operations.md").write_text(
            "# Inventory operations\n"
            "Order intake follows the shared loader idiom in both modules.\n"
            "Every order passes the check `verify_reservation_limits()` before it "
            "is stored.\n"
            "Reservations and holds are different mechanisms: a hold does not "
            "expire, a reservation does.\n")

        # Config + data files
        (workspace / "config.json").write_text('{"catalog": "main", "limits": {}}')
        (workspace / "legacy.pkl.example").write_text("example placeholder")

        # .claude for memory
        claude_dir = workspace / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.local.json").write_text("{}")

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
                      "calibration-trend-report.md", "cross-model-validation.log.jsonl",
                      "analysis-findings.json", "domain-model.md"]:
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
                # Honest semantics (v1.3): missing/empty log fails UNLESS the
                # calibration report carries the visible NOT_RUN marker. A log
                # co-existing with the NOT_RUN marker is a contradiction (stale
                # log from a prior run) and fails outright.
                log = artifacts.get("cross-model-validation.log.jsonl", [])
                report_text = artifacts.get("calibration-report.md", "")
                has_marker = "NOT_RUN:" in report_text
                if isinstance(log, list) and len(log) > 0:
                    if has_marker:
                        passed = False
                        details = ("stale cross-model log present while report claims "
                                   "NOT_RUN — contradiction")
                    else:
                        required = ["blind_spot_id", "reviewer", "command", "exit_code", "verdict", "notes",
                                    "additional_blind_spots", "timestamp"]
                        valid = all(all(f in r for f in required) for r in log)
                        # Any PARSED verdict from a successful run counts
                        # (CONFIRMED|REFUTED|PARTIAL|ADDITIONAL_FINDING) — a
                        # reviewer that REFUTES is a real review, not a
                        # failure. Non-zero-exit/UNPARSED records are honest
                        # noise: excluded from counts, never a failure here.
                        allowed = {"CONFIRMED", "REFUTED", "PARTIAL", "ADDITIONAL_FINDING"}
                        parsed = [r for r in log if isinstance(r, dict)
                                  and r.get("exit_code") == 0
                                  and r.get("verdict") in allowed]
                        reviewers = set(r.get("reviewer") for r in parsed)
                        passed = valid and len(parsed) >= 1 and len(reviewers) >= 1
                        details = (f"Records: {len(log)}, Valid: {valid}, "
                                   f"Parsed reviews: {len(parsed)}, "
                                   f"Reviewers: {len(reviewers)}, "
                                   f"Verdicts: {[r.get('verdict') for r in parsed]}")
                elif has_marker:
                    # Not-run is a valid, visible state — but it must be visible
                    passed = True
                    details = "No log; calibration report carries NOT_RUN marker"
                else:
                    passed = False
                    details = "cross-model log missing/empty and no NOT_RUN marker in report"

            elif "trend-analysis" in grader_name:
                trend = artifacts.get("calibration-trend-report.md", "")
                passed = len(trend) > 100 and "Overall Calibration" in trend and "By Layer" in trend
                details = f"Has trend report: {passed}"

            elif "domain-layer-valid" in grader_name:
                # Domain layer (v1.3): schema validity of analysis-findings.json
                findings = artifacts.get("analysis-findings.json", {})
                if not isinstance(findings, dict) or findings.get("error"):
                    passed = False
                    details = "analysis-findings.json missing or unparseable"
                else:
                    problems = []
                    if findings.get("schema_version") != "1":
                        problems.append("schema_version != 1")
                    tr = findings.get("task_resolution", {})
                    if not (isinstance(tr, dict) and str(tr.get("stated_outcome", "")).strip()):
                        problems.append("task_resolution.stated_outcome missing")
                    dm = findings.get("domain_model", {})
                    if not (isinstance(dm, dict) and isinstance(dm.get("concepts"), list) and dm["concepts"]):
                        problems.append("domain_model.concepts empty")
                    # Required finding fields (inline: runner stays standalone)
                    import re as _re
                    for f in findings.get("findings", []):
                        if not all(k in f for k in ("id", "statement", "category_path", "layer",
                                                    "evidence_status", "source_refs", "confidence_band")):
                            problems.append(f"finding {f.get('id')} missing required fields")
                            continue
                        if not _re.match(r"^FIND-\d{3,}$", str(f["id"])):
                            problems.append(f"finding id invalid: {f['id']}")
                        if f["layer"] not in ("L1", "L2", "L3", "L4"):
                            problems.append(f"finding {f['id']} bad layer")
                        if f["evidence_status"] not in ("OBSERVED", "CANDIDATE", "INFERRED",
                                                        "HYPOTHESIS", "UNVERIFIED_CLAIM"):
                            problems.append(f"finding {f['id']} bad evidence_status")
                        if f["confidence_band"] not in ("HIGH", "MEDIUM", "LOW"):
                            problems.append(f"finding {f['id']} bad confidence_band")
                        if not isinstance(f["source_refs"], list):
                            problems.append(f"finding {f['id']} source_refs not a list")
                    for p in findings.get("patterns", []):
                        if p.get("status") != "CANDIDATE":
                            problems.append(f"pattern {p.get('id')} not CANDIDATE (no agent to promote)")
                    # Fixture dedupe rule: identical-content copies are ONE
                    # source — distinct_sources must not exceed the unique
                    # content count of the pattern's source refs.
                    import hashlib as _hashlib
                    for p in findings.get("patterns", []):
                        contents = {}
                        for ref in p.get("source_refs", []):
                            try:
                                rp = (workspace / str(ref))
                                if rp.is_file():
                                    contents[ref] = rp.read_text(encoding="utf-8", errors="ignore")
                            except OSError:
                                pass
                        if contents:
                            unique = {_hashlib.sha256(c.lower().encode("utf-8")).hexdigest()[:16]
                                      for c in contents.values()}
                            indep = p.get("independence", {}).get("distinct_sources", 99)
                            if indep > len(unique):
                                problems.append(
                                    f"pattern {p.get('id')} distinct_sources {indep} "
                                    f"exceeds unique content count {len(unique)}")
                    bsc = findings.get("blind_spot_candidates", [])
                    if not bsc:
                        problems.append("blind_spot_candidates empty")
                    for b in bsc:
                        if not str(b.get("why_it_matters", "")).strip() or \
                                not str(b.get("smallest_useful_check", "")).strip():
                            problems.append(f"bsx {b.get('id')} missing why_it_matters/smallest_useful_check")
                    if findings.get("validation_errors"):
                        problems.append("validation_errors present in report")
                    passed = not problems
                    details = "; ".join(problems[:5]) if problems else "all checks passed"

            elif "depth-control" in grader_name:
                # Quick depth: domain model and patterns must be absent keys
                findings = artifacts.get("analysis-findings.json", {})
                if not isinstance(findings, dict) or findings.get("error"):
                    passed = False
                    details = "analysis-findings.json missing in quick mode"
                else:
                    has_dm = "domain_model" in findings
                    has_pat = "patterns" in findings
                    passed = not has_dm and not has_pat
                    details = f"domain_model key: {has_dm}, patterns key: {has_pat} (both must be absent)"

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
            cases_to_run = ["case-quick-mode", "case-deep-mode", "case-domain-layer"]
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
                        choices=["case-quick-mode", "case-deep-mode", "case-domain-layer",
                                 "quick-mode", "deep-mode", "domain-layer", "all"],
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