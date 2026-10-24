#!/usr/bin/env python3
"""
Validate Assumptions — Standalone assumption tester.
Usage: python validate-assumptions.py --assumptions PATH --workspace PATH --output PATH
"""
import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class AssumptionValidator:
    def __init__(self, workspace: Path, concepts: Optional[List[Dict]] = None):
        self.workspace = workspace.resolve()
        # Domain layer (v1.3): optional concept names for lexical
        # confusion nomination (CANDIDATE_CONFUSION only — never evidence).
        self.concepts = concepts or []

    def _concept_confusions(self, statement: str) -> List[Dict]:
        """Lexical nomination of possibly-confusable concepts: concepts
        whose names share a token with the statement. A name overlap is a
        CANDIDATE_CONFUSION — it never upgrades or downgrades the record's
        epistemic status; distinction requires the criterion check, not
        name similarity."""
        if not self.concepts:
            return []
        tokens = {t.lower() for t in re.split(r"[^A-Za-z0-9]+", statement) if len(t) >= 3}
        confusions = []
        for concept in self.concepts:
            name = str(concept.get("name", ""))
            # Concept names are often hyphen/underscore slugs — split into
            # sub-tokens so "config-format-convention" overlaps "config".
            name_tokens = {t.lower() for t in re.split(r"[^A-Za-z0-9]+", name) if len(t) >= 3}
            if name_tokens and (name_tokens & tokens):
                confusions.append({
                    "kind": "CANDIDATE_CONFUSION",
                    "concept": name,
                    "note": "lexical nomination only — name overlap is not a "
                            "distinction; check the concept's criteria",
                })
        return confusions[:5]

    def validate(self, assumptions: List[Dict]) -> List[Dict]:
        """Run validation tests for each assumption."""
        results = []

        for assumption in assumptions:
            if not assumption.get("testable", False):
                results.append({
                    "assumption_id": assumption["id"],
                    "timestamp": datetime.now().isoformat(),
                    "prediction": assumption["statement"],
                    "actual": "Not testable - skipped",
                    "evidence": [],
                    "result": "SKIPPED",
                    "confidence_delta": 0.0,
                    "new_status": assumption.get("epistemic_status", "ASSUMED_FACT"),
                    "layer": assumption.get("layer", "L2"),
                    "check_status": "SKIPPED",
                    "verification_method": "none",
                    "search_scope": None,
                    "commands_ran": [],
                    "commands_assumed": [],
                    "session_id": "standalone-validation",
                    "possible_confusions": self._concept_confusions(assumption.get("statement", ""))
                })
                continue

            result = self._test_assumption(assumption)
            # Domain layer (v1.3): lexical confusion nomination on every
            # record when concepts are provided; never affects the outcome.
            if self.concepts:
                result["possible_confusions"] = self._concept_confusions(
                    assumption.get("statement", ""))
            results.append(result)

        return results

    def _test_assumption(self, assumption: Dict) -> Dict:
        """Test a single assumption against workspace evidence."""
        a_type = assumption.get("type", "CONVENTION")
        statement = assumption.get("statement", "")
        layer = assumption.get("layer", "L2")

        # Dispatch to type-specific test
        if a_type == "CONVENTION":
            return self._test_convention(assumption)
        elif a_type == "BEHAVIORAL":
            return self._test_behavioral(assumption)
        elif a_type == "INVARIANT":
            return self._test_invariant(assumption)
        elif a_type == "DELEGATION":
            return self._test_delegation(assumption)
        elif a_type == "ARCHITECTURAL":
            return self._test_architectural(assumption)
        elif a_type == "DOMAIN":
            return self._test_domain(assumption)
        else:
            return self._test_generic(assumption)

    # Scoped search is pure Python — no external tool dependency, so the
    # validator behaves identically in every harness. A missing tool must never
    # masquerade as project evidence (§4, Anti-Pattern #11).
    _SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__", "dist",
                  "build", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache"}
    _TEXT_SUFFIXES = {".py", ".js", ".ts", ".go", ".rs", ".java", ".md", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}

    def _search_scope(self) -> Dict:
        """Recorded scope for every search below (§4: searches state their scope)."""
        return {
            "paths": ["."],
            "ignore_rules": "default (skips .git/.claude/node_modules/__pycache__/dist/build/venv)",
            "case_sensitive": False,
            "file_types": sorted(self._TEXT_SUFFIXES),
        }

    def _search_files(self, keyword: str) -> List[str]:
        """Case-insensitive content search; returns real `path:line` hits."""
        hits: List[str] = []
        try:
            for f in sorted(self.workspace.rglob("*")):
                if not f.is_file() or f.suffix not in self._TEXT_SUFFIXES:
                    continue
                if any(part in self._SKIP_DIRS for part in f.relative_to(self.workspace).parts):
                    continue
                if f.stat().st_size > 1_000_000:
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if keyword.lower() in line.lower():
                        hits.append(f"{f.relative_to(self.workspace).as_posix()}:{i}")
                        if len(hits) >= 20:
                            return hits
        except OSError:
            # Environment constraint, not project evidence: report as blocked upstream
            raise
        return hits

    def _blocked_record(self, assumption: Dict, method: str, block_reason: str,
                        unblock_condition: str, new_status: str = "UNVERIFIED_PATTERN") -> Dict:
        """Honest BLOCKED record: the check could not run (environment constraint)."""
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": "check not executed",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": new_status,
            "layer": assumption.get("layer", "L2"),
            "check_status": "BLOCKED",
            "block_reason": block_reason,
            "unblock_condition": unblock_condition,
            "inconclusive_reason": "check could not run; no project evidence gathered",
            "verification_method": method,
            "search_scope": None,
            "commands_ran": [],
            "commands_assumed": [],
            "session_id": "standalone-validation"
        }

    def _test_convention(self, assumption: Dict) -> Dict:
        """Test convention assumption via scoped pattern search.

        Negative-search discipline (§4): a null search is INCONCLUSIVE — absence
        of keyword matches is not falsification. Only positive observations
        confirm or falsify.
        """
        statement = assumption["statement"]
        keywords = self._extract_keywords(statement)

        matches = []
        try:
            for keyword in keywords:
                matches.extend(self._search_files(keyword))
        except OSError as e:
            return self._blocked_record(
                assumption, "static_analysis",
                f"workspace scan failed: {e.__class__.__name__}",
                "grant read access to the workspace tree and rerun")

        if matches:
            stated = float(assumption.get("confidence", 0.7))
            return {
                "assumption_id": assumption["id"],
                "timestamp": datetime.now().isoformat(),
                "prediction": statement,
                "actual": f"Pattern found in {len(matches)} scoped locations",
                "evidence": matches[:10],
                "result": "CONFIRMED",
                "confidence_delta": round(1.0 - stated, 2),
                "new_status": "WORKSPACE_CONVENTION",
                "layer": assumption.get("layer", "L2"),
                "check_status": "RAN",
                "verification_method": "static_analysis",
                "search_scope": self._search_scope(),
                "commands_ran": [],
                "commands_assumed": [],
                "session_id": "standalone-validation"
            }
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": statement,
            "actual": f"No matches for keywords {keywords} in scoped source files",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": "UNVERIFIED_PATTERN",
            "layer": assumption.get("layer", "L2"),
            "check_status": "RAN",
            "inconclusive_reason": "scoped search found no matches; absence is not falsification",
            "claim_wording": f"not found in scope ({', '.join(keywords)})",
            "verification_method": "static_analysis",
            "search_scope": self._search_scope(),
            "commands_ran": [],
            "commands_assumed": [],
            "session_id": "standalone-validation"
        }

    def _test_behavioral(self, assumption: Dict) -> Dict:
        """Behavioral tests require code execution — never auto-run here (§4 probe
        safety), so the check is honestly BLOCKED, not faked."""
        return self._blocked_record(
            assumption, "code_execution",
            "behavioral check requires executing workspace code; the standalone validator never auto-runs it (probe safety)",
            "run the behavior in a sandboxed test, or hand the claim to an agent harness that can execute tests with user approval")

    def _test_invariant(self, assumption: Dict) -> Dict:
        """Test invariant - search for counterexamples."""
        statement = assumption["statement"]
        falsifier = assumption.get("falsifier", "")

        # Search for falsifier pattern
        keywords = self._extract_keywords(falsifier) if falsifier else self._extract_keywords(statement)

        counterexamples = []
        try:
            for keyword in keywords:
                counterexamples.extend(self._search_files(keyword))
        except OSError as e:
            return self._blocked_record(
                assumption, "static_analysis",
                f"workspace scan failed: {e.__class__.__name__}",
                "grant read access to the workspace tree and rerun")

        if counterexamples:
            stated = float(assumption.get("confidence", 0.8))
            return {
                "assumption_id": assumption["id"],
                "timestamp": datetime.now().isoformat(),
                "prediction": statement,
                "actual": f"Counterexamples found: {len(counterexamples)}",
                "evidence": counterexamples[:10],
                "result": "FALSIFIED",
                "confidence_delta": round(0.0 - stated, 2),
                "new_status": "CALIBRATION_ERROR",
                "layer": assumption.get("layer", "L3"),
                "check_status": "RAN",
                "corrected_belief": f"invariant violated by {len(counterexamples)} counterexample(s) in scope; see evidence",
                "verification_method": "static_analysis",
                "search_scope": self._search_scope(),
                "commands_ran": [],
                "commands_assumed": [],
                "session_id": "standalone-validation"
            }
        # Null-cap (§4): a null counterexample search with a recorded scope is
        # scoped CONFIRMED — worded as 'no counterexamples in <scope>', capped at
        # WORKSPACE_CONVENTION. Never automatic FACT at 1.0.
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": statement,
            "actual": f"No counterexamples for {keywords} in scoped source files",
            "evidence": [],
            "result": "CONFIRMED",
            "confidence_delta": 0.05,
            "new_status": "WORKSPACE_CONVENTION",
            "layer": assumption.get("layer", "L3"),
            "check_status": "RAN",
            "claim_wording": f"no counterexamples in <workspace, scoped source files> for {keywords}",
            "verification_method": "static_analysis",
            "search_scope": self._search_scope(),
            "commands_ran": [],
            "commands_assumed": [],
            "session_id": "standalone-validation"
        }

    def _test_delegation(self, assumption: Dict) -> Dict:
        """Delegation claims need package/import analysis — BLOCKED here, honestly."""
        return self._blocked_record(
            assumption, "static_analysis",
            "delegation test requires package/import analysis - not implemented in the standalone validator",
            "run package introspection (import graph, dependency manifest check) or verify in an agent harness")

    def _test_architectural(self, assumption: Dict) -> Dict:
        """Test architectural assumption via import graph analysis."""
        statement = assumption["statement"].lower()

        # Check for clean architecture indicators (complete bounded directory
        # inventory — a closed-set observation, not a fuzzy text search)
        if "clean architecture" in statement or "layered architecture" in statement:
            # Look for layer separation
            layer_dirs = ["domain", "application", "infrastructure", "presentation", "core", "runtime", "system"]
            found_layers = []

            for layer in layer_dirs:
                if (self.workspace / layer).exists() or (self.workspace / "src" / layer).exists():
                    found_layers.append(layer)

            if len(found_layers) >= 3 and "domain" in found_layers:
                stated = float(assumption.get("confidence", 0.8))
                return {
                    "assumption_id": assumption["id"],
                    "timestamp": datetime.now().isoformat(),
                    "prediction": assumption["statement"],
                    "actual": f"Found layer directories: {', '.join(found_layers)}",
                    "evidence": [f"{layer}/" for layer in found_layers],
                    "result": "CONFIRMED",
                    "confidence_delta": round(1.0 - stated, 2),
                    "new_status": "WORKSPACE_CONVENTION",
                    "layer": assumption.get("layer", "L3"),
                    "check_status": "RAN",
                    "verification_method": "static_analysis",
                    "search_scope": self._search_scope(),
                    "commands_ran": [],
                    "commands_assumed": [],
                    "session_id": "standalone-validation"
                }
            else:
                # Check for modular monolith pattern (positive contradicting evidence)
                core_dirs = ["core", "app_core", "shared_core"]
                found_core = [d for d in core_dirs if (self.workspace / d).exists() or (self.workspace / "src" / d).exists()]

                if found_core:
                    stated = float(assumption.get("confidence", 0.8))
                    return {
                        "assumption_id": assumption["id"],
                        "timestamp": datetime.now().isoformat(),
                        "prediction": assumption["statement"],
                        "actual": f"Found modular monolith pattern with core: {', '.join(found_core)}",
                        "evidence": [f"{d}/" for d in found_core],
                        "result": "FALSIFIED",
                        "confidence_delta": round(0.0 - stated, 2),
                        "new_status": "CALIBRATION_ERROR",
                        "layer": assumption.get("layer", "L3"),
                        "check_status": "RAN",
                        "corrected_belief": f"workspace is a modular monolith with core dir(s) {', '.join(found_core)}, not clean/layered architecture",
                        "verification_method": "static_analysis",
                        "search_scope": self._search_scope(),
                        "commands_ran": [],
                        "commands_assumed": [],
                        "session_id": "standalone-validation"
                    }

        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": "Architectural pattern inconclusive - requires full import graph",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": "UNVERIFIED_PATTERN",
            "layer": assumption.get("layer", "L3"),
            "check_status": "BLOCKED",
            "block_reason": "full import-graph analysis not implemented in the standalone validator",
            "unblock_condition": "run import-graph analysis or verify in an agent harness",
            "inconclusive_reason": "no layer/core directory evidence either way; absence is not falsification",
            "verification_method": "static_analysis",
            "search_scope": self._search_scope(),
            "commands_ran": [],
            "commands_assumed": [],
            "session_id": "standalone-validation"
        }

    def _test_domain(self, assumption: Dict) -> Dict:
        """Domain claims need doc/memory cross-reference — BLOCKED here, honestly."""
        return self._blocked_record(
            assumption, "doc_test_crossref",
            "domain test requires domain docs or memory cross-reference - not implemented in the standalone validator",
            "provide domain docs in the workspace or run the check in an agent harness with memory access",
            new_status="DOMAIN_GAP")

    def _test_generic(self, assumption: Dict) -> Dict:
        """Generic fallback — no validator exists for this type; say so."""
        return self._blocked_record(
            assumption, "static_analysis",
            f"no standalone validator implements assumption type '{assumption.get('type', 'UNSPECIFIED')}'",
            "implement a validator for this type or hand the claim to agent-level verification")

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract search keywords from statement."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)
        # Filter common words, keep technical terms
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "all", "any", "some", "every", "each", "this", "that", "these", "those", "in", "on", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "out", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "not", "no", "nor", "but", "or", "yet", "so", "than", "too", "very", "just", "now", "also"}
        keywords = [w for w in words if len(w) > 3 and w.lower() not in stopwords]
        return list(set(keywords))[:5]  # Max 5 keywords

def main():
    parser = argparse.ArgumentParser(description="Validate assumptions against workspace")
    parser.add_argument("--assumptions", required=True, help="Path to assumptions.json")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument("--output", required=True, help="Output calibration log path")
    parser.add_argument("--append", action="store_true",
                        help="Append to --output instead of truncating (use when "
                             "targeting the append-only calibration.log.jsonl)")
    parser.add_argument("--concepts", default=None,
                        help="Optional domain-model JSON (concept list or model object) "
                             "for lexical CANDIDATE_CONFUSION nomination")
    args = parser.parse_args()

    assumptions_path = Path(args.assumptions)
    workspace = Path(args.workspace).resolve()
    output_path = Path(args.output)

    if not assumptions_path.exists():
        print(f"Error: Assumptions file not found: {assumptions_path}")
        sys.exit(1)

    if not workspace.exists():
        print(f"Error: Workspace not found: {workspace}")
        sys.exit(1)

    # Load assumptions
    with open(assumptions_path) as f:
        assumptions = json.load(f)

    # Domain layer (v1.3): optional concepts for lexical confusion nomination
    concepts: Optional[List[Dict]] = None
    if args.concepts:
        concepts_path = Path(args.concepts)
        if not concepts_path.exists():
            print(f"Error: Concepts file not found: {concepts_path}")
            sys.exit(1)
        with open(concepts_path) as f:
            concepts_data = json.load(f)
        if isinstance(concepts_data, dict):
            concepts = concepts_data.get("concepts", [])
        elif isinstance(concepts_data, list):
            concepts = concepts_data
        else:
            print("Error: --concepts must be a domain-model object or concept list")
            sys.exit(1)

    print(f"Loaded {len(assumptions)} assumptions from {assumptions_path}")
    print(f"Testing against workspace: {workspace}")

    # Validate
    validator = AssumptionValidator(workspace, concepts=concepts)
    results = validator.validate(assumptions)

    # Write results (--append preserves prior records; default keeps the
    # historical truncating behavior for backward compatibility)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with open(output_path, mode) as f:
        for result in results:
            f.write(json.dumps(result) + "\n")

    # Summary
    confirmed = sum(1 for r in results if r["result"] == "CONFIRMED")
    falsified = sum(1 for r in results if r["result"] == "FALSIFIED")
    inconclusive = sum(1 for r in results if r["result"] == "INCONCLUSIVE")
    skipped = sum(1 for r in results if r["result"] == "SKIPPED")

    print(f"\nResults written to: {output_path}")
    print(f"  Confirmed: {confirmed}")
    print(f"  Falsified: {falsified}")
    print(f"  Inconclusive: {inconclusive}")
    print(f"  Skipped: {skipped}")

if __name__ == "__main__":
    main()