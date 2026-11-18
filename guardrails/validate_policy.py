#!/usr/bin/env python3
"""
Policy-as-code guardrail for Intune configuration-as-code repo.

Walks every JSON file under the given path(s) and rejects any policy
that violates a baseline security rule. This is the "admission control"
layer that runs in CI, before IntuneCD ever gets a chance to apply
anything to a live tenant - the Gatekeeper/OPA equivalent in the
Kubernetes-GitOps analogy.

Exit code 0 = all policies pass. Exit code 1 = at least one violation found.
"""
import json
import sys
from pathlib import Path

RULES = []


def rule(description):
    def wrap(fn):
        RULES.append((description, fn))
        return fn
    return wrap


@rule("BitLocker must not be disabled on any Windows compliance policy")
def no_disabling_bitlocker(doc, path):
    if doc.get("@odata.type") == "#microsoft.graph.windows10CompliancePolicy":
        if doc.get("bitLockerEnabled") is False:
            return f"{path}: bitLockerEnabled is explicitly false"
    return None


@rule("Compliance policies must not set a zero-hour grace period with block action removed")
def must_have_scheduled_action(doc, path):
    if doc.get("@odata.type") == "#microsoft.graph.windows10CompliancePolicy":
        actions = doc.get("scheduledActionsForRule") or []
        if not actions:
            return f"{path}: no scheduledActionsForRule defined - noncompliant devices would never be actioned"
    return None


@rule("Every policy/profile must carry at least one group assignment")
def must_have_assignment(doc, path):
    if "assignments" in doc or doc.get("@odata.type", "").startswith("#microsoft.graph."):
        assignments = doc.get("assignments")
        if assignments is not None and len(assignments) == 0:
            return f"{path}: assignments present but empty - policy would be orphaned"
    return None


def main(paths):
    violations = []
    checked = 0

    for base in paths:
        for file in sorted(Path(base).rglob("*.json")):
            try:
                doc = json.loads(file.read_text())
            except json.JSONDecodeError as e:
                violations.append(f"{file}: invalid JSON - {e}")
                continue

            checked += 1
            for description, fn in RULES:
                result = fn(doc, file)
                if result:
                    violations.append(f"[{description}] {result}")

    print(f"Checked {checked} policy file(s) against {len(RULES)} guardrail rule(s).")

    if violations:
        print("\nGUARDRAIL FAILED:\n")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("All policies pass guardrail checks.")
    return 0


if __name__ == "__main__":
    paths = sys.argv[1:] or ["intune"]
    sys.exit(main(paths))
