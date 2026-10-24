"""Integration tests for run-self-audit.py: domain layer artifacts (E, G,
H), backward compatibility (I), simulation-vs-real honesty (J), and eval
grader honesty. Stdlib unittest, temp-dir isolated — NEVER writes in the
repo. Plan tests E, G, I, J."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "skills" / "self-audit" / "scripts" / "run-self-audit.py"
sys.path.insert(0, str(REPO_ROOT / "skills" / "self-audit" / "scripts"))
import domain_analysis as da  # noqa: E402


def run_audit(workspace: Path, mode: str, extra_env=None):
    env = dict(os.environ)
    env["SELF_AUDIT_WORKSPACE"] = str(workspace)
    env["SELF_AUDIT_KNOWLEDGE_ROOT"] = str(workspace / ".claude" / "knowledge")
    env["SELF_AUDIT_MEMORY_ROOT"] = str(workspace / ".claude" / "projects" / "ws" / "memory")
    env.pop("SELF_AUDIT_EXTERNAL_REVIEWERS", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, str(SCRIPT), "--mode", mode],
                          capture_output=True, text=True, env=env, timeout=300)


def make_workspace(with_docs_no_tests=True):
    ws = Path(tempfile.mkdtemp()) / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "src/main.py").write_text(
        'import json\nCONFIG_FILE="config.yaml"\ndef load_config(p):\n'
        '    with open(p) as f:\n        return json.load(f)\n')
    (ws / "settings.json").write_text('{"features": {}}')
    if with_docs_no_tests:
        (ws / "docs").mkdir()
        (ws / "docs/architecture.md").write_text(
            '# Arch\nThis project follows a modular monolith pattern.\n'
            'All modules use the shared config loader.\n')
    return ws


class TestMultiSourceDedupe(unittest.TestCase):
    """Test C proof on the REAL runner path: identical-content files are
    ONE source inside `_phase_2_5_pattern_candidates` (not just the pure
    helper)."""

    def test_runner_pattern_candidates_dedupe_copies(self):
        ws = make_workspace()
        (ws / "src/catalog.py").write_text("CATEGORIES = ['a', 'b']\n")
        (ws / "src/catalog_backup.py").write_text("CATEGORIES = ['a', 'b']\n")
        (ws / "src/other.py").write_text("CATEGORIES = ['z', 'y']\n")
        os.environ["SELF_AUDIT_WORKSPACE"] = str(ws)
        os.environ["SELF_AUDIT_KNOWLEDGE_ROOT"] = str(ws / ".claude/knowledge")
        os.environ["SELF_AUDIT_MEMORY_ROOT"] = str(ws / ".claude/projects/ws/memory")
        try:
            spec = importlib.util.spec_from_file_location(
                "run_self_audit", SCRIPT)
            rsa = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rsa)
            cli = rsa.SelfAuditCLI()
            calibration_log = [
                {"assumption_id": "ASSUME-001", "result": "CONFIRMED",
                 "prediction": "All catalog entries are loaded via the shared catalog helper",
                 "evidence": ["src/catalog.py"]},
                {"assumption_id": "ASSUME-002", "result": "CONFIRMED",
                 "prediction": "All catalog entries are loaded via the shared catalog helper",
                 "evidence": ["src/catalog_backup.py"]},
                {"assumption_id": "ASSUME-003", "result": "FALSIFIED",
                 "prediction": "All catalog entries are loaded via the shared catalog helper",
                 "evidence": ["src/other.py"]},
            ]
            candidates = cli._phase_2_5_pattern_candidates(calibration_log)
            self.assertTrue(candidates)
            c = candidates[0]
            self.assertEqual(c["status"], "CANDIDATE")
            # three refs, but catalog.py + catalog_backup.py are identical
            # content -> the copies collapse to one source
            self.assertEqual(c["independence"]["distinct_sources"], 2,
                             c["independence"])
        finally:
            for k in ("SELF_AUDIT_WORKSPACE", "SELF_AUDIT_KNOWLEDGE_ROOT",
                      "SELF_AUDIT_MEMORY_ROOT"):
                os.environ.pop(k, None)

    def test_path_line_refs_resolve_and_dedupe(self):
        """Regression (path:line refs): `docs/a.md:12` must resolve to
        docs/a.md for reading; two different line refs of the same file are
        ONE source; identical duplicate files also collapse to one."""
        ws = make_workspace()
        (ws / "docs/notes.md").write_text("Shared loader idiom documented.\n")
        (ws / "docs/notes_backup.md").write_text("Shared loader idiom documented.\n")
        os.environ["SELF_AUDIT_WORKSPACE"] = str(ws)
        os.environ["SELF_AUDIT_KNOWLEDGE_ROOT"] = str(ws / ".claude/knowledge")
        os.environ["SELF_AUDIT_MEMORY_ROOT"] = str(ws / ".claude/projects/ws/memory")
        try:
            spec = importlib.util.spec_from_file_location(
                "run_self_audit_line", SCRIPT)
            rsa = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rsa)
            cli = rsa.SelfAuditCLI()
            # same-file different line refs + identical duplicate file
            refs = ["docs/notes.md:1", "docs/notes.md:2", "docs/notes_backup.md:1"]
            contents = cli._evidence_contents(refs)
            # all three resolve to readable content
            self.assertEqual(len(contents), 3, contents)
            # distinct source count collapses: notes.md (any line) + identical
            # backup = ONE source
            self.assertEqual(da.distinct_source_count(refs, contents), 1,
                             "same-file line refs + identical copies must count as one source")
            # and with different content they count separately
            (ws / "docs/notes_backup.md").write_text("Different content entirely.\n")
            contents2 = cli._evidence_contents(refs)
            self.assertEqual(da.distinct_source_count(refs, contents2), 2)
        finally:
            for k in ("SELF_AUDIT_WORKSPACE", "SELF_AUDIT_KNOWLEDGE_ROOT",
                      "SELF_AUDIT_MEMORY_ROOT"):
                os.environ.pop(k, None)


class TestBlindSpotDiscovery(unittest.TestCase):
    """Test E: a check claimed by docs but absent in code yields a
    blind-spot candidate with why_it_matters + smallest_useful_check."""

    def test_missing_check_produces_candidate(self):
        ws = Path(tempfile.mkdtemp()) / "ws"
        (ws / "src").mkdir(parents=True)
        (ws / "docs").mkdir()
        (ws / "src/main.py").write_text("def work():\n    return 1\n")
        (ws / "docs/manual.md").write_text(
            "# Manual\nEvery load passes the validation `validate_items()` "
            "gate before it is stored.\n")
        r = run_audit(ws, "standard")
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        findings = json.loads((ws / ".claude/knowledge/analysis-findings.json").read_text())
        candidates = findings["blind_spot_candidates"]
        self.assertTrue(candidates)
        for b in candidates:
            self.assertTrue(str(b.get("why_it_matters", "")).strip())
            self.assertTrue(str(b.get("smallest_useful_check", "")).strip())
        # the missing-check candidate names the claimed symbol
        self.assertTrue(any("validate_items" in b["description"] or "validate_items"
                            in b["smallest_useful_check"] for b in candidates),
                        [b["description"] for b in candidates])


class TestTaskComplexityMeasurement(unittest.TestCase):
    """Regression: complexity's UNCERTAIN signal counts unresolved checks
    (total − CONFIRMED − FALSIFIED), not a miscounted subset — a fully
    measured session must not be labeled UNCERTAIN."""

    def test_measured_session_is_not_uncertain(self):
        ws = make_workspace()
        os.environ["SELF_AUDIT_WORKSPACE"] = str(ws)
        os.environ["SELF_AUDIT_KNOWLEDGE_ROOT"] = str(ws / ".claude/knowledge")
        os.environ["SELF_AUDIT_MEMORY_ROOT"] = str(ws / ".claude/projects/ws/memory")
        try:
            spec = importlib.util.spec_from_file_location("run_self_audit_cx", SCRIPT)
            rsa = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rsa)
            cli = rsa.SelfAuditCLI()
            measured = {"conventions": [{"pattern": "a"}, {"pattern": "b"}, {"pattern": "c"}],
                        "structure": {"test_dirs": []},
                        "calibration_history": [
                            {"total_assumptions": 7, "confirmed_count": 5, "falsified_count": 2}]}
            self.assertEqual(cli._task_complexity(measured), "MULTISTEP",
                             "7/7 measured checks are not uncertain")
            unresolved = {"conventions": [{"pattern": "a"}, {"pattern": "b"}, {"pattern": "c"}],
                          "structure": {"test_dirs": []},
                          "calibration_history": [
                              {"total_assumptions": 10, "confirmed_count": 3, "falsified_count": 4}]}
            self.assertEqual(cli._task_complexity(unresolved), "UNCERTAIN",
                             "3/10 unresolved checks exceeds the 20% threshold")
            # Boundary: exactly 20% unresolved is NOT >0.2 — stays non-uncertain
            at_threshold = {"conventions": [{"pattern": "a"}, {"pattern": "b"}, {"pattern": "c"}],
                            "structure": {"test_dirs": []},
                            "calibration_history": [
                                {"total_assumptions": 10, "confirmed_count": 4, "falsified_count": 4}]}
            self.assertEqual(cli._task_complexity(at_threshold), "MULTISTEP",
                             "exactly 20% unresolved is at the threshold, not over it")
        finally:
            for k in ("SELF_AUDIT_WORKSPACE", "SELF_AUDIT_KNOWLEDGE_ROOT",
                      "SELF_AUDIT_MEMORY_ROOT"):
                os.environ.pop(k, None)


class TestScopeAccessLimits(unittest.TestCase):
    """Test G: access limits are real and name the CLI's ingestion limits."""

    def test_plan_target_records_no_ingestion(self):
        ws = make_workspace()
        r = run_audit(ws, "standard", {"SELF_AUDIT_TARGET": "plan"})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        findings = json.loads((ws / ".claude/knowledge/analysis-findings.json").read_text())
        limits = " ".join(findings["task_resolution"]["access_limits"])
        self.assertIn("no CLI-side content ingestion", limits)
        self.assertIn("plan", limits)
        # only actually-set env overrides are recorded
        overrides = findings["task_resolution"]["resource_scope"]["env_overrides"]
        self.assertIn("SELF_AUDIT_TARGET", overrides)
        self.assertNotIn("SELF_AUDIT_STAKES", overrides)


class TestBackwardCompat(unittest.TestCase):
    """Test I: existing artifacts keep their v1.2.1 key sets; append-only
    log preserved; domain-layer kill-switch works."""

    V121_SUMMARY_KEYS = {"skill", "mode", "target", "stakes", "workspace",
                        "session_id", "timestamp", "assumptions_tested",
                        "confirmed", "falsified", "inconclusive", "blind_spots",
                        "learning_units", "top_blind_spots", "recommended_preload"}

    def test_quick_artifacts_and_keys(self):
        ws = make_workspace()
        r = run_audit(ws, "quick")
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        kn = ws / ".claude/knowledge"
        for f in ("assumptions.json", "calibration.log.jsonl", "blind-spots.md",
                  "calibration-report.md", "calibration-summary.json"):
            self.assertTrue((kn / f).exists(), f)
        summary = json.loads((kn / "calibration-summary.json").read_text())
        self.assertTrue(self.V121_SUMMARY_KEYS.issubset(summary.keys()),
                        sorted(self.V121_SUMMARY_KEYS - summary.keys()))
        # quick depth: no domain model / patterns keys
        findings = json.loads((kn / "analysis-findings.json").read_text())
        self.assertNotIn("domain_model", findings)
        self.assertNotIn("patterns", findings)
        self.assertIn("task_resolution", findings)
        self.assertIn("blind_spot_candidates", findings)

    def test_log_is_append_only_across_runs(self):
        ws = make_workspace()
        run_audit(ws, "quick")
        log = ws / ".claude/knowledge/calibration.log.jsonl"
        n1 = len(log.read_text().splitlines())
        run_audit(ws, "quick")
        n2 = len(log.read_text().splitlines())
        self.assertGreater(n2, n1)

    def test_domain_layer_kill_switch(self):
        ws = make_workspace()
        r = run_audit(ws, "quick", {"SELF_AUDIT_DOMAIN_LAYER": "false"})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.assertFalse((ws / ".claude/knowledge/analysis-findings.json").exists())
        summary = json.loads((ws / ".claude/knowledge/calibration-summary.json").read_text())
        self.assertFalse(summary.get("domain_layer"))


class TestNoFakeVerification(unittest.TestCase):
    """Test J: no reviewer configured -> NOT_RUN, no log; real reviewer ->
    parseable verdict bound to its blind spot; failing reviewer -> error
    record, not counted. Stale logs never survive a NOT_RUN run."""

    OK_CMD = ('python -c "import json,sys; p=json.load(sys.stdin); '
              "print(json.dumps({'verdict':'CONFIRMED','notes':'reviewed '+p['blind_spot_id']}))\"")
    FAIL_CMD = 'python -c "import sys; sys.exit(2)"'

    def test_unconfigured_is_not_run(self):
        ws = make_workspace()
        r = run_audit(ws, "deep")
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        kn = ws / ".claude/knowledge"
        self.assertFalse((kn / "cross-model-validation.log.jsonl").exists())
        report = (kn / "calibration-report.md").read_text()
        self.assertIn("NOT_RUN: no external reviewer command configured", report)

    def test_reviewer_receives_payload_and_binds_verdict(self):
        ws = make_workspace()
        r = run_audit(ws, "deep", {
            "SELF_AUDIT_EXTERNAL_REVIEWERS": json.dumps(
                [{"name": "r1", "command": self.OK_CMD}])})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        log = ws / ".claude/knowledge/cross-model-validation.log.jsonl"
        self.assertTrue(log.exists())
        records = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertGreaterEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["verdict"], "CONFIRMED")
        self.assertEqual(rec["exit_code"], 0)
        # the verdict is bound to the blind spot via the received payload
        self.assertIn(rec["blind_spot_id"], rec["notes"])

    def test_failing_reviewer_not_counted(self):
        ws = make_workspace()
        r = run_audit(ws, "deep", {
            "SELF_AUDIT_EXTERNAL_REVIEWERS": json.dumps(
                [{"name": "broken", "command": self.FAIL_CMD}])})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        log = ws / ".claude/knowledge/cross-model-validation.log.jsonl"
        records = [json.loads(line) for line in log.read_text().splitlines()]
        rec = records[0]
        self.assertEqual(rec["verdict"], "UNPARSED")
        self.assertEqual(rec["exit_code"], 2)
        report = (ws / ".claude/knowledge/calibration-report.md").read_text()
        self.assertIn("Reviewers with parseable verdicts: 0", report)

    def test_valid_verdict_then_nonzero_exit_never_counts(self):
        """Regression: a command that prints a valid CONFIRMED JSON verdict
        and THEN exits 2 is a failed review — the verdict must be recorded
        UNPARSED (stdout excerpt preserved) and never counted."""
        ws = make_workspace()
        sneaky = ("python -c \"import sys,json;"
                  "sys.stdout.write(json.dumps({'verdict':'CONFIRMED'}));"
                  "sys.exit(2)\"")
        r = run_audit(ws, "deep", {
            "SELF_AUDIT_EXTERNAL_REVIEWERS": json.dumps(
                [{"name": "sneaky", "command": sneaky}])})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        log = ws / ".claude/knowledge/cross-model-validation.log.jsonl"
        self.assertTrue(log.exists(), "the failed review is still recorded")
        records = [json.loads(line) for line in log.read_text().splitlines()]
        rec = records[0]
        self.assertEqual(rec["exit_code"], 2)
        self.assertEqual(rec["verdict"], "UNPARSED",
                         "valid JSON from a failing command must not count")
        self.assertTrue(rec["stdout_excerpt"], "output is preserved for inspection")
        report = (ws / ".claude/knowledge/calibration-report.md").read_text()
        self.assertIn("Reviewers with parseable verdicts: 0", report)
        self.assertRegex(report, r"Unparseable/failed reviewer records: [1-9]")

    def test_stale_log_removed_on_not_run(self):
        ws = make_workspace()
        run_audit(ws, "deep", {
            "SELF_AUDIT_EXTERNAL_REVIEWERS": json.dumps(
                [{"name": "r1", "command": self.OK_CMD}])})
        log = ws / ".claude/knowledge/cross-model-validation.log.jsonl"
        if log.exists():  # reviewer had blind spots to review this run
            run_audit(ws, "deep")
            self.assertFalse(log.exists(),
                             "stale cross-model log must not survive a NOT_RUN run")


class TestGraderHonesty(unittest.TestCase):
    """Eval grader must reject stale/fabricated cross-model evidence."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "eval_runner", REPO_ROOT / ".github/scripts/eval-runner.py")
        er = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(er)
        cls.runner = er.EvalRunner(REPO_ROOT)
        cls.grader = REPO_ROOT / "evals/case-deep-mode/graders/cross-model-validation.md"

    def test_stale_log_with_marker_is_contradiction(self):
        artifacts = {
            "cross-model-validation.log.jsonl": [
                {"blind_spot_id": "BS-001", "reviewer": "r", "command": "c",
                 "verdict": "CONFIRMED", "notes": "n", "additional_blind_spots": [],
                 "timestamp": "t"}],
            "calibration-report.md":
                "## Cross-Model Validation\n- NOT_RUN: no external reviewer "
                "command configured (set SELF_AUDIT_EXTERNAL_REVIEWERS; see docs)\n",
        }
        res = self.runner._run_grader(self.grader, Path("."), {"returncode": 0, "artifacts": artifacts})
        self.assertFalse(res["passed"])

    def test_clean_not_run_passes_fabricated_empty_fails(self):
        clean = {
            "cross-model-validation.log.jsonl": [],
            "calibration-report.md":
                "## Cross-Model Validation\n- NOT_RUN: explicitly disabled "
                "(via --no-cross-model or SELF_AUDIT_CROSS_MODEL=false) "
                "— no reviews exist for this run\n",
        }
        res = self.runner._run_grader(self.grader, Path("."), {"returncode": 0, "artifacts": clean})
        self.assertTrue(res["passed"], res)
        fabricated = {
            "cross-model-validation.log.jsonl": [],
            "calibration-report.md": "no marker anywhere",
        }
        res = self.runner._run_grader(self.grader, Path("."), {"returncode": 0, "artifacts": fabricated})
        self.assertFalse(res["passed"], res)

    def test_grader_rejects_valid_verdict_from_failing_command(self):
        """A CONFIRMED verdict from a non-zero-exit reviewer must not pass."""
        artifacts = {
            "cross-model-validation.log.jsonl": [
                {"blind_spot_id": "BS-001", "reviewer": "sneaky", "command": "c",
                 "exit_code": 2, "verdict": "CONFIRMED", "notes": "n",
                 "additional_blind_spots": [], "timestamp": "t"}],
            "calibration-report.md":
                "## Cross-Model Validation\n- Reviewers with parseable verdicts: 0\n",
        }
        res = self.runner._run_grader(self.grader, Path("."), {"returncode": 0, "artifacts": artifacts})
        self.assertFalse(res["passed"], res)
        self.assertIn("Parsed reviews: 0", res["details"])

    def test_grader_accepts_refuted_review(self):
        """A real REFUTED/PARTIAL review (exit 0) is a valid review —
        the grader must not require CONFIRMED."""
        for verdict in ("REFUTED", "PARTIAL", "ADDITIONAL_FINDING"):
            artifacts = {
                "cross-model-validation.log.jsonl": [
                    {"blind_spot_id": "BS-001", "reviewer": "r1", "command": "c",
                     "exit_code": 0, "verdict": verdict, "notes": "n",
                     "additional_blind_spots": [], "timestamp": "t"}],
                "calibration-report.md":
                    "## Cross-Model Validation\n- Reviewers with parseable verdicts: 1\n",
            }
            res = self.runner._run_grader(self.grader, Path("."), {"returncode": 0, "artifacts": artifacts})
            self.assertTrue(res["passed"], f"{verdict} must count as a review: {res}")

    def test_grader_mixed_records_with_one_real_review_passes(self):
        """One real review + honest UNPARSED noise from a failed reviewer
        is a valid outcome — the failed record is noise, not a failure."""
        artifacts = {
            "cross-model-validation.log.jsonl": [
                {"blind_spot_id": "BS-001", "reviewer": "r1", "command": "c",
                 "exit_code": 0, "verdict": "REFUTED", "notes": "n",
                 "additional_blind_spots": [], "timestamp": "t"},
                {"blind_spot_id": "BS-002", "reviewer": "broken", "command": "c2",
                 "exit_code": 2, "verdict": "UNPARSED", "notes": "",
                 "additional_blind_spots": [], "timestamp": "t"}],
            "calibration-report.md":
                "## Cross-Model Validation\n- Reviewers with parseable verdicts: 1\n",
        }
        res = self.runner._run_grader(self.grader, Path("."), {"returncode": 0, "artifacts": artifacts})
        self.assertTrue(res["passed"], res)


if __name__ == "__main__":
    unittest.main()