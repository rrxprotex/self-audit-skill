#!/usr/bin/env python3
"""
Validate Assumptions — Standalone assumption tester.
Usage: python validate-assumptions.py --assumptions PATH --workspace PATH --output PATH
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class AssumptionValidator:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

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
                    "verification_method": "none",
                    "session_id": "standalone-validation"
                })
                continue

            result = self._test_assumption(assumption)
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

    def _test_convention(self, assumption: Dict) -> Dict:
        """Test convention assumption via grep/pattern search."""
        statement = assumption["statement"]

        # Extract pattern keywords from statement
        keywords = self._extract_keywords(statement)

        matches = []
        exceptions = []

        for keyword in keywords:
            # Search for pattern
            try:
                result = subprocess.run(
                    ["rg", keyword, "--type", "py", "--type", "js", "--type", "ts", "--type", "go", "--type", "rs", "."],
                    cwd=self.workspace, capture_output=True, text=True, timeout=30
                )
                if result.stdout.strip():
                    matches.extend(result.stdout.strip().split("\n"))
            except:
                pass

        if matches:
            return {
                "assumption_id": assumption["id"],
                "timestamp": datetime.now().isoformat(),
                "prediction": statement,
                "actual": f"Pattern found in {len(matches)} locations",
                "evidence": matches[:10],
                "result": "CONFIRMED",
                "confidence_delta": 0.1,
                "new_status": "WORKSPACE_CONVENTION",
                "layer": assumption.get("layer", "L2"),
                "verification_method": "grep",
                "session_id": "standalone-validation"
            }
        else:
            return {
                "assumption_id": assumption["id"],
                "timestamp": datetime.now().isoformat(),
                "prediction": statement,
                "actual": "Pattern not found in workspace",
                "evidence": [],
                "result": "FALSIFIED",
                "confidence_delta": -assumption.get("confidence", 0.7),
                "new_status": "CALIBRATION_ERROR",
                "layer": assumption.get("layer", "L2"),
                "verification_method": "grep",
                "session_id": "standalone-validation"
            }

    def _test_behavioral(self, assumption: Dict) -> Dict:
        """Test behavioral assumption - would run actual code."""
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": "Behavioral test requires code execution - not implemented in standalone validator",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": "UNVERIFIED_PATTERN",
            "layer": assumption.get("layer", "L2"),
            "verification_method": "code_execution",
            "session_id": "standalone-validation"
        }

    def _test_invariant(self, assumption: Dict) -> Dict:
        """Test invariant - search for counterexamples."""
        statement = assumption["statement"]
        falsifier = assumption.get("falsifier", "")

        # Search for falsifier pattern
        keywords = self._extract_keywords(falsifier) if falsifier else self._extract_keywords(statement)

        counterexamples = []
        for keyword in keywords:
            try:
                result = subprocess.run(
                    ["rg", keyword, "."],
                    cwd=self.workspace, capture_output=True, text=True, timeout=30
                )
                if result.stdout.strip():
                    counterexamples.extend(result.stdout.strip().split("\n"))
            except:
                pass

        if counterexamples:
            return {
                "assumption_id": assumption["id"],
                "timestamp": datetime.now().isoformat(),
                "prediction": statement,
                "actual": f"Counterexamples found: {len(counterexamples)}",
                "evidence": counterexamples[:10],
                "result": "FALSIFIED",
                "confidence_delta": -assumption.get("confidence", 0.8),
                "new_status": "CALIBRATION_ERROR",
                "layer": assumption.get("layer", "L3"),
                "verification_method": "grep",
                "session_id": "standalone-validation"
            }
        else:
            return {
                "assumption_id": assumption["id"],
                "timestamp": datetime.now().isoformat(),
                "prediction": statement,
                "actual": "No counterexamples found",
                "evidence": [],
                "result": "CONFIRMED",
                "confidence_delta": 0.1,
                "new_status": "FACT",
                "layer": assumption.get("layer", "L3"),
                "verification_method": "grep",
                "session_id": "standalone-validation"
            }

    def _test_delegation(self, assumption: Dict) -> Dict:
        """Test delegation assumption - check library usage."""
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": "Delegation test requires package analysis - not implemented in standalone validator",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": "UNVERIFIED_PATTERN",
            "layer": assumption.get("layer", "L2"),
            "verification_method": "package_analysis",
            "session_id": "standalone-validation"
        }

    def _test_architectural(self, assumption: Dict) -> Dict:
        """Test architectural assumption via import graph analysis."""
        statement = assumption["statement"].lower()

        # Check for clean architecture indicators
        if "clean architecture" in statement or "layered architecture" in statement:
            # Look for layer separation
            layer_dirs = ["domain", "application", "infrastructure", "presentation", "core", "runtime", "system"]
            found_layers = []

            for layer in layer_dirs:
                if (self.workspace / layer).exists() or (self.workspace / "src" / layer).exists():
                    found_layers.append(layer)

            if len(found_layers) >= 3 and "domain" in found_layers:
                return {
                    "assumption_id": assumption["id"],
                    "timestamp": datetime.now().isoformat(),
                    "prediction": assumption["statement"],
                    "actual": f"Found layer directories: {', '.join(found_layers)}",
                    "evidence": [f"{layer}/" for layer in found_layers],
                    "result": "CONFIRMED",
                    "confidence_delta": 0.1,
                    "new_status": "WORKSPACE_CONVENTION",
                    "layer": assumption.get("layer", "L3"),
                    "verification_method": "import_graph_analysis",
                    "session_id": "standalone-validation"
                }
            else:
                # Check for modular monolith pattern
                core_dirs = ["core", "songlab_core", "app_core"]
                found_core = [d for d in core_dirs if (self.workspace / d).exists() or (self.workspace / "src" / d).exists()]

                if found_core:
                    return {
                        "assumption_id": assumption["id"],
                        "timestamp": datetime.now().isoformat(),
                        "prediction": assumption["statement"],
                        "actual": f"Found modular monolith pattern with core: {', '.join(found_core)}",
                        "evidence": [f"{d}/" for d in found_core],
                        "result": "FALSIFIED",
                        "confidence_delta": -0.7,
                        "new_status": "CALIBRATION_ERROR",
                        "layer": assumption.get("layer", "L3"),
                        "verification_method": "import_graph_analysis",
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
            "verification_method": "import_graph_analysis",
            "session_id": "standalone-validation"
        }

    def _test_domain(self, assumption: Dict) -> Dict:
        """Test domain assumption - check docs/memory."""
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": "Domain test requires domain docs - not implemented in standalone validator",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": "DOMAIN_GAP",
            "layer": assumption.get("layer", "L4"),
            "verification_method": "doc_crossref",
            "session_id": "standalone-validation"
        }

    def _test_generic(self, assumption: Dict) -> Dict:
        """Generic test fallback."""
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": "Generic test - not implemented",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "confidence_delta": 0.0,
            "new_status": "UNVERIFIED_PATTERN",
            "layer": assumption.get("layer", "L2"),
            "verification_method": "none",
            "session_id": "standalone-validation"
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract search keywords from statement."""
        import re
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

    print(f"Loaded {len(assumptions)} assumptions from {assumptions_path}")
    print(f"Testing against workspace: {workspace}")

    # Validate
    validator = AssumptionValidator(workspace)
    results = validator.validate(assumptions)

    # Write results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
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