"""
SDD Quality Gate Validator.

Usage:
    uv run python spec/quality_gates.py check --phase brainstorm --feature my-feature
    uv run python spec/quality_gates.py validate --feature my-feature
"""
import argparse
import json
import os
import sys
from pathlib import Path

SPEC_DIR = Path(__file__).parent

def check_brainstorm_gate(feature: str) -> dict:
    doc_path = SPEC_DIR / "brainstorm" / feature / "BRAINSTORM.md"
    if not doc_path.exists():
        return {"passed": False, "errors": ["BRAINSTORM.md not found"]}
    content = doc_path.read_text()
    checks = {
        "3+ approaches compared": content.count("## Approach") >= 3,
        "3+ questions answered": content.count("## Question") >= 3,
        "YAGNI filter applied": "out of scope" in content.lower(),
        "Success criteria defined": "success" in content.lower() or "criteria" in content.lower(),
    }
    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "errors": [k for k, v in checks.items() if not v]}

def check_define_gate(feature: str) -> dict:
    doc_path = SPEC_DIR / "define" / feature / "DEFINE.md"
    if not doc_path.exists():
        return {"passed": False, "errors": ["DEFINE.md not found"]}
    content = doc_path.read_text()
    score = 0
    criteria = ["problem scope", "success metric", "stakeholders", "constraints", "dependencies"]
    for c in criteria:
        if c in content.lower():
            score += 3
    passed = score >= 12
    return {"passed": passed, "clarity_score": score, "errors": [] if passed else [f"Score {score}/15 < 12"]}

def check_design_gate(feature: str) -> dict:
    doc_path = SPEC_DIR / "design" / feature / "DESIGN.md"
    if not doc_path.exists():
        return {"passed": False, "errors": ["DESIGN.md not found"]}
    content = doc_path.read_text()
    checks = {
        "file manifest present": "## File Manifest" in content or "file manifest" in content.lower(),
        "ADRs documented": "adr" in content.lower(),
        "schema design present": "schema" in content.lower() or "## Schema" in content,
        "data flow diagram": "flow" in content.lower() or "data flow" in content.lower(),
    }
    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "errors": [k for k, v in checks.items() if not v]}

def check_build_gate(feature: str) -> dict:
    errors = []
    if not os.path.exists("pyproject.toml"):
        errors.append("pyproject.toml not found")
    if os.system("uv run ruff check . --quiet") != 0:
        errors.append("Ruff lint failed")
    if os.system("uv run pytest tests/ -q --tb=short") != 0:
        errors.append("Tests failed")
    return {"passed": len(errors) == 0, "errors": errors}

def run_validation(feature: str) -> dict:
    results = {
        "spec_completeness": check_design_gate(feature),
        "code_quality": check_build_gate(feature),
    }
    score = 0
    if results["spec_completeness"]["passed"]:
        score += 30
    if results["code_quality"]["passed"]:
        score += 70
    passed = score >= 90
    return {
        "feature": feature,
        "score": score,
        "passed": passed,
        "details": results,
        "errors": [e for r in results.values() if isinstance(r, dict) for e in r.get("errors", [])]
    }

def main():
    parser = argparse.ArgumentParser(description="SDD Quality Gate Validator")
    sub = parser.add_subparsers(dest="command")

    check_p = sub.add_parser("check")
    check_p.add_argument("--phase", required=True, choices=["brainstorm", "define", "design", "build"])
    check_p.add_argument("--feature", required=True)

    validate_p = sub.add_parser("validate")
    validate_p.add_argument("--feature", required=True)

    args = parser.parse_args()

    if args.command == "check":
        gates = {
            "brainstorm": check_brainstorm_gate,
            "define": check_define_gate,
            "design": check_design_gate,
            "build": check_build_gate,
        }
        result = gates[args.phase](args.feature)
    elif args.command == "validate":
        result = run_validation(args.feature)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("passed") else 1)

if __name__ == "__main__":
    main()
