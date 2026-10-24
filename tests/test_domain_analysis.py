"""Unit tests for the domain-adaptive analysis engine (schema, validators,
candidate nomination, depth control). Stdlib unittest — no pytest, no repo
writes. Plan tests A, B, C, D, F, H."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                        / "skills" / "self-audit" / "scripts"))
import domain_analysis as da  # noqa: E402


class TestDomainAdaptation(unittest.TestCase):
    """Test A: different subjects get structurally different models; depth
    control never injects domain-specific categories."""

    def test_domain_adaptation_two_structures(self):
        code_model = {
            "subject": "config-loading conventions",
            "concepts": [
                {"name": "loader", "definition": "reads config from disk",
                 "distinguishes": [{"criterion": "reads files", "vs_concept": "validator"}],
                 "status": "ESTABLISHED"},
                {"name": "validator", "definition": "checks config shape",
                 "distinguishes": [{"criterion": "checks shape", "vs_concept": "loader"}],
                 "status": "PROPOSED"},
            ],
            "coverage_notes": "error-handling area unclassified",
        }
        notes_model = {
            "subject": "research note taxonomy",
            "concepts": [
                {"name": "observation", "definition": "raw recorded fact",
                 "distinguishes": [], "status": "PROPOSED"},
                {"name": "interpretation", "definition": "meaning assigned to observations",
                 "distinguishes": [{"criterion": "adds meaning", "vs_concept": "observation"}],
                 "status": "PROPOSED"},
            ],
            "coverage_notes": ["sources unverified", "timeline unclassified"],
        }
        errors, warnings = da.validate_domain_model(code_model)
        self.assertEqual((errors, warnings), ([], []))
        errors, warnings = da.validate_domain_model(notes_model)
        self.assertEqual((errors, warnings), ([], []))
        # Depth control is structural: same output keys regardless of domain
        for complexity in da.COMPLEXITY_VALUES:
            d = da.analysis_depth("standard", "medium", complexity)
            self.assertEqual(set(d.keys()), {
                "task_resolution", "domain_model", "layered_analysis",
                "pattern_discovery", "blind_spot_search", "max_layers"})
            dumped = str(d)
            for domain_word in ("loader", "validator", "observation", "interpretation"):
                self.assertNotIn(domain_word, dumped)


class TestConceptDistinction(unittest.TestCase):
    """Test B: distinguish criteria validation + collision warnings."""

    def test_distinguishes_requires_criterion_and_neighbor(self):
        model = {"subject": "s", "concepts": [
            {"name": "alpha", "definition": "d", "status": "PROPOSED",
             "distinguishes": [{"criterion": "only"}]},
        ]}
        errors, _ = da.validate_domain_model(model)
        self.assertTrue(any("criterion" in e and "vs_concept" in e for e in errors))

    def test_name_collision_warns_on_different_definitions(self):
        model = {"subject": "s", "concepts": [
            {"name": "alpha", "definition": "one", "status": "PROPOSED"},
            {"name": "alpha", "definition": "two", "status": "PROPOSED"},
        ]}
        errors, warnings = da.validate_domain_model(model)
        self.assertEqual(errors, [])
        self.assertTrue(any("collision" in w for w in warnings))

    def test_proposed_status_required(self):
        model = {"subject": "s", "concepts": [
            {"name": "alpha", "definition": "one", "status": "ESTABLISHED_FACT"},
        ]}
        errors, _ = da.validate_domain_model(model)
        self.assertTrue(any("PROPOSED" in e for e in errors))


class TestMultiSourcePattern(unittest.TestCase):
    """Test C: independent sources, content dedupe, VERIFIED gating."""

    def test_distinct_source_count_dedupes_copies(self):
        refs = ["a.py", "b.py"]
        contents = {"a.py": "same content here", "b.py": "same  content here!"}
        self.assertEqual(da.distinct_source_count(refs, contents), 1)

    def test_distinct_source_count_counts_different_content(self):
        refs = ["a.py", "b.py"]
        contents = {"a.py": "alpha content", "b.py": "beta content"}
        self.assertEqual(da.distinct_source_count(refs, contents), 2)

    def test_distinct_source_count_without_contents_is_unique_strings(self):
        self.assertEqual(da.distinct_source_count(["a.py", "b.py"]), 2)
        self.assertEqual(da.distinct_source_count(["a.py", "a.py"]), 1)

    def test_verified_gate_requires_run_and_evidence(self):
        findings = [
            {"id": "FIND-001", "statement": "alpha", "category_path": "alpha.beta",
             "layer": "L1", "evidence_status": "OBSERVED", "source_refs": ["f1"],
             "confidence_band": "HIGH"},
            {"id": "FIND-002", "statement": "beta", "category_path": "alpha.beta",
             "layer": "L1", "evidence_status": "OBSERVED", "source_refs": ["f2"],
             "confidence_band": "HIGH"},
        ]
        base_pattern = {
            "id": "PAT-001", "statement": "p",
            "member_finding_ids": ["FIND-001", "FIND-002"],
            "source_refs": ["f1", "f2"], "status": "VERIFIED",
            "independence": {"distinct_sources": 2},
        }
        report = {"schema_version": "1", "subject": "s",
                  "findings": findings, "patterns": [dict(base_pattern)]}
        # Two sources + resolvable members but no check run -> rejected
        errs = da.validate_analysis_report(report)
        self.assertTrue(any("verification_status='RUN'" in e for e in errs))
        # With RUN + cited evidence -> accepted
        good = dict(base_pattern)
        good["verification_status"] = "RUN"
        good["verification_evidence"] = ["rg 'alpha|beta' src/ -> 4 matches"]
        report["patterns"] = [good]
        self.assertEqual(da.validate_analysis_report(report), [])

    def test_verified_requires_two_independent_sources(self):
        findings = [
            {"id": "FIND-001", "statement": "alpha", "category_path": "alpha.beta",
             "layer": "L1", "evidence_status": "OBSERVED", "source_refs": ["same"],
             "confidence_band": "HIGH"},
            {"id": "FIND-002", "statement": "beta", "category_path": "alpha.beta",
             "layer": "L1", "evidence_status": "OBSERVED", "source_refs": ["same"],
             "confidence_band": "HIGH"},
        ]
        pattern = {"id": "PAT-001", "statement": "p",
                   "member_finding_ids": ["FIND-001", "FIND-002"],
                   "source_refs": ["same"], "status": "VERIFIED",
                   "verification_status": "RUN",
                   "verification_evidence": ["cmd"],
                   "independence": {"distinct_sources": 1}}
        report = {"schema_version": "1", "subject": "s",
                  "findings": findings, "patterns": [pattern]}
        errs = da.validate_analysis_report(report)
        self.assertTrue(any("VERIFIED requires >= 2" in e for e in errs))


class TestFalsePatternRisk(unittest.TestCase):
    """Test D: lexical nomination never promotes beyond CANDIDATE."""

    def test_nomination_is_candidate_only(self):
        findings = [
            {"id": "FIND-001", "statement": "All config files are loaded via the shared helper module"},
            {"id": "FIND-002", "statement": "All config files are loaded via the shared helper module"},
            {"id": "FIND-003", "statement": "Database migration uses a different mechanism entirely"},
        ]
        candidates = da.nominate_pattern_candidates(findings)
        self.assertTrue(candidates)
        for c in candidates:
            self.assertEqual(c["status"], "CANDIDATE")
            self.assertIn("lexical_signal", c)
            self.assertEqual(c["verification_status"] if "verification_status" in c else "NOT_RUN", "NOT_RUN")
        # Similar statements group together; the different one is not merged in
        for c in candidates:
            if "FIND-003" in c["member_finding_ids"]:
                self.assertNotIn("FIND-001", c["member_finding_ids"])

    def test_single_occurrence_never_a_pattern(self):
        findings = [{"id": "FIND-001", "statement": "All config files are loaded via the shared helper module"}]
        self.assertEqual(da.nominate_pattern_candidates(findings), [])


class TestEvidenceAndUncertainty(unittest.TestCase):
    """Test F: evidence scope and uncertainty_reason requirements."""

    def test_empty_refs_require_evidence_scope(self):
        f = {"id": "FIND-001", "statement": "s", "category_path": "alpha.beta", "layer": "L1",
             "evidence_status": "OBSERVED", "source_refs": [], "confidence_band": "HIGH"}
        errs = da.validate_finding(f)
        self.assertTrue(any("evidence_scope" in e for e in errs))
        f["evidence_scope"] = "searched docs/ only"
        self.assertEqual(da.validate_finding(f), [])

    def test_non_observed_requires_uncertainty_reason(self):
        f = {"id": "FIND-001", "statement": "s", "category_path": "alpha.beta", "layer": "L1",
             "evidence_status": "HYPOTHESIS", "source_refs": ["f"], "confidence_band": "LOW"}
        errs = da.validate_finding(f)
        self.assertTrue(any("uncertainty_reason" in e for e in errs))
        f["uncertainty_reason"] = "not yet checked"
        self.assertEqual(da.validate_finding(f), [])


class TestDepthSelection(unittest.TestCase):
    """Test H: depth rules per mode/stakes/complexity."""

    def test_quick_stays_cheap(self):
        d = da.analysis_depth("quick", "medium", "SIMPLE")
        self.assertFalse(d["domain_model"])
        self.assertFalse(d["pattern_discovery"])
        self.assertTrue(d["blind_spot_search"])
        self.assertTrue(d["task_resolution"])

    def test_deep_enables_everything(self):
        d = da.analysis_depth("deep", "medium", "MULTISTEP")
        for k in ("task_resolution", "domain_model", "layered_analysis",
                  "pattern_discovery", "blind_spot_search"):
            self.assertTrue(d[k])
        self.assertEqual(d["max_layers"], 10)

    def test_high_stakes_upgrades_quick_domain_model_only(self):
        d = da.analysis_depth("quick", "high", "UNCERTAIN")
        self.assertTrue(d["domain_model"])
        self.assertFalse(d["pattern_discovery"])

    def test_simple_complexity_never_upgrades(self):
        d = da.analysis_depth("standard", "high", "SIMPLE")
        self.assertEqual(d["max_layers"], 6)

    def test_uncertain_upgrades_standard_depth(self):
        d = da.analysis_depth("standard", "medium", "UNCERTAIN")
        self.assertEqual(d["max_layers"], 10)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            da.analysis_depth("extreme", "medium", "SIMPLE")
        with self.assertRaises(ValueError):
            da.analysis_depth("quick", "maybe", "SIMPLE")
        with self.assertRaises(ValueError):
            da.analysis_depth("quick", "medium", "COMPLEX")


class TestTaskResolution(unittest.TestCase):
    def test_stated_outcome_required(self):
        self.assertTrue(any("stated_outcome" in e
                            for e in da.validate_task_resolution({"complexity": "SIMPLE"})))

    def test_inference_must_be_labeled(self):
        tr = {"stated_outcome": "x", "complexity": "SIMPLE",
              "inferred_purpose": {"purpose": "guess"}}
        errs = da.validate_task_resolution(tr)
        self.assertTrue(any("INFERENCE" in e for e in errs))
        tr["inferred_purpose"] = {"purpose": "guess", "labeled_as": "INFERENCE"}
        self.assertEqual(da.validate_task_resolution(tr), [])


if __name__ == "__main__":
    unittest.main()