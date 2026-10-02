#!/usr/bin/env python3
"""Run a local Cathedral regulatory intelligence e2e simulation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from preflight import read_json, validate_artifact


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "regulatory-intelligence"
TARGET = ROOT / "target" / "regulatory-intelligence"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_markdown(path: Path, report: dict) -> None:
    lines = [
        "# Cathedral Regulatory Intelligence E2E",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Result",
        "",
        f"- status: {report['status']}",
        f"- card: {report['card']['card_id']}",
        f"- worker: {report['worker']['worker_id']}",
        f"- score: {report['score']['total']}",
        f"- reputation before: {report['reputation']['before']}",
        f"- reputation after: {report['reputation']['after']}",
        "",
        "## Events",
        "",
    ]
    for event in report["events"]:
        lines.append(f"- {event['type']}: {event['detail']}")
    lines.extend(
        [
            "",
            "## Score parts",
            "",
        ]
    )
    for key, value in report["score"]["parts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Production gaps",
            "",
        ]
    )
    for gap in report["production_gaps"]:
        lines.append(f"- {gap}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    source_baseline = read_json(EXAMPLES / "source-baseline.json")
    card_registry = read_json(EXAMPLES / "cards.seed.json")
    worker = read_json(EXAMPLES / "worker.sample.json")
    job = read_json(EXAMPLES / "job.sample.json")
    artifact = read_json(EXAMPLES / "artifact.sample.json")
    invalid_artifact = read_json(EXAMPLES / "artifact.invalid.json")

    failures, warnings, score, score_parts = validate_artifact(artifact, source_baseline, card_registry)
    invalid_failures, _, _, _ = validate_artifact(invalid_artifact, source_baseline, card_registry)

    cards_by_id = {card["card_id"]: card for card in card_registry["cards"]}
    card = cards_by_id[job["card_id"]]

    events = [
        {
            "type": "worker_registered",
            "detail": f"{worker['worker_id']} registered as a Hermes regulatory worker",
        },
        {
            "type": "card_assigned",
            "detail": f"{card['card_id']} assigned to {worker['worker_id']}",
        },
        {
            "type": "job_created",
            "detail": f"{job['job_id']} created for {card['country']} {card['topic']}",
        },
        {
            "type": "artifact_submitted",
            "detail": f"{artifact['artifact_id']} submitted with {len(artifact['citations'])} citations",
        },
        {
            "type": "artifact_scored",
            "detail": f"validator score {score}",
        },
    ]

    reputation_before = float(worker["reputation_score"])
    reputation_after = round((reputation_before * 0.8) + (score * 0.2), 2)
    status = "pass" if not failures and invalid_failures else "fail"

    report = {
        "schema_version": "cathedral.regulatory_intelligence.e2e_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "events": events,
        "worker": {
            "worker_id": worker["worker_id"],
            "runtime": worker["runtime"],
            "category": worker["category"],
        },
        "card": {
            "card_id": card["card_id"],
            "country": card["country"],
            "topic": card["topic"],
            "required_source_ids": card["required_source_ids"],
        },
        "artifact": {
            "artifact_id": artifact["artifact_id"],
            "citation_count": len(artifact["citations"]),
            "no_legal_advice": artifact["no_legal_advice"],
            "polaris_worker_deploy_url": artifact["polaris"]["worker_deploy_url"],
        },
        "score": {
            "total": score,
            "parts": score_parts,
            "warnings": warnings,
            "failures": failures,
        },
        "invalid_fixture": {
            "expected_failures": len(invalid_failures),
            "passed_negative_test": bool(invalid_failures),
        },
        "reputation": {
            "before": reputation_before,
            "after": reputation_after,
        },
        "production_gaps": [
            "Replace stub Polaris worker URL with a real Hermes deployment link.",
            "Sign Polaris worker and usage events before rewards consume them.",
            "Add live source fetch and diff checks before public reward weighting.",
            "Connect published cards to downstream usage attribution.",
        ],
    }

    write_json(TARGET / "e2e-report.json", report)
    write_markdown(TARGET / "e2e-report.md", report)

    print("Cathedral regulatory intelligence e2e")
    print(f"status: {status}")
    print(f"score: {score}")
    print(f"worker: {worker['worker_id']}")
    print(f"card: {card['card_id']}")
    print(f"report: {TARGET / 'e2e-report.json'}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"  FAIL {failure}")
        return 1
    if not invalid_failures:
        print("\nFAIL invalid fixture unexpectedly passed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
