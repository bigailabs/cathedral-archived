#!/usr/bin/env python3
"""Preflight a Cathedral regulatory intelligence artifact."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


SCHEMA_VERSION = "cathedral.regulatory_intelligence.artifact.v1"
BASELINE_VERSION = "cathedral.regulatory_intelligence.source_baseline.v1"
CARD_REGISTRY_VERSION = "cathedral.regulatory_intelligence.card_registry.v1"

REQUIRED_TEXT_FIELDS = {
    "title": 8,
    "summary": 60,
    "what_changed": 40,
    "why_it_matters": 40,
}

REQUIRED_ATTESTATIONS = {
    "not_legal_advice",
    "no_confidential_data",
    "citations_are_primary_sources",
    "no_uncited_material_claims",
    "does_not_count_self_usage_as_demand",
}

ELIGIBLE_SOURCE_TIERS = {
    "primary_law",
    "primary_regulator",
    "official_policy",
}


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def nested(data: dict, path: str):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def is_url(value: object, require_https: bool = True) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    if require_https and parsed.scheme != "https":
        return False
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc)


def load_sources(source_baseline: dict) -> dict[str, dict]:
    if source_baseline.get("schema_version") != BASELINE_VERSION:
        raise ValueError(f"source baseline schema_version must be {BASELINE_VERSION}")
    sources = source_baseline.get("sources")
    if not isinstance(sources, list):
        raise ValueError("source baseline must contain sources array")
    by_id: dict[str, dict] = {}
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("each source must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("each source must have source_id")
        by_id[source_id] = source
    return by_id


def load_cards(card_registry: dict) -> dict[str, dict]:
    if card_registry.get("schema_version") != CARD_REGISTRY_VERSION:
        raise ValueError(f"card registry schema_version must be {CARD_REGISTRY_VERSION}")
    cards = card_registry.get("cards")
    if not isinstance(cards, list):
        raise ValueError("card registry must contain cards array")
    by_id: dict[str, dict] = {}
    for card in cards:
        if not isinstance(card, dict):
            raise ValueError("each card must be an object")
        card_id = card.get("card_id")
        if not isinstance(card_id, str) or not card_id.strip():
            raise ValueError("each card must have card_id")
        by_id[card_id] = card
    return by_id


def score_artifact(artifact: dict, card: dict, sources_by_id: dict[str, dict]) -> tuple[int, dict[str, int]]:
    citations = artifact.get("citations") if isinstance(artifact.get("citations"), list) else []
    citation_ids = {c.get("source_id") for c in citations if isinstance(c, dict)}
    required_ids = set(card.get("required_source_ids", []))

    required_covered = len(required_ids & citation_ids)
    required_total = max(len(required_ids), 1)
    source_quality = round(30 * (required_covered / required_total))

    generated_at = parse_time(artifact.get("generated_at"))
    fresh_count = 0
    if generated_at is not None:
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            retrieved_at = parse_time(citation.get("retrieved_at"))
            if retrieved_at is None:
                continue
            age_seconds = (generated_at - retrieved_at).total_seconds()
            if 0 <= age_seconds <= 7 * 86400:
                fresh_count += 1
    freshness = round(20 * (fresh_count / max(len(citations), 1)))

    text = " ".join(
        str(artifact.get(field, ""))
        for field in ["summary", "what_changed", "why_it_matters"]
    )
    has_dates = any(char.isdigit() for char in text)
    specificity = 15 if len(text) >= 220 and has_dates else 9 if len(text) >= 160 else 4

    action_items = artifact.get("action_items")
    risks = artifact.get("risks")
    usefulness = 20
    if not isinstance(action_items, list) or len(action_items) < 2:
        usefulness -= 8
    if not isinstance(risks, list) or len(risks) < 1:
        usefulness -= 6
    if len(str(artifact.get("why_it_matters", ""))) < 80:
        usefulness -= 4
    usefulness = max(usefulness, 0)

    clarity = 15
    summary = str(artifact.get("summary", ""))
    if len(summary) > 700:
        clarity -= 5
    if "legal advice" not in " ".join(str(r) for r in risks).lower():
        clarity -= 4
    clarity = max(clarity, 0)

    parts = {
        "source_quality": source_quality,
        "freshness": freshness,
        "specificity": specificity,
        "usefulness": usefulness,
        "clarity": clarity,
    }
    return sum(parts.values()), parts


def validate_artifact(
    artifact: dict,
    source_baseline: dict,
    card_registry: dict,
) -> tuple[list[str], list[str], int, dict[str, int]]:
    failures: list[str] = []
    warnings: list[str] = []

    sources_by_id = load_sources(source_baseline)
    cards_by_id = load_cards(card_registry)

    if artifact.get("schema_version") != SCHEMA_VERSION:
        failures.append(f"schema_version must be {SCHEMA_VERSION}")

    card_id = artifact.get("card_id")
    card = cards_by_id.get(card_id)
    if not card:
        failures.append("card_id must exist in cards.seed.json")
        card = {}

    if card and artifact.get("jurisdiction_code") != card.get("jurisdiction_code"):
        failures.append("artifact jurisdiction_code must match assigned card")

    assigned_worker = card.get("assigned_worker_id")
    if assigned_worker and artifact.get("worker_id") != assigned_worker:
        failures.append("worker_id must match the assigned card worker")

    for field, minimum in REQUIRED_TEXT_FIELDS.items():
        value = artifact.get(field)
        if not isinstance(value, str) or len(value.strip()) < minimum:
            failures.append(f"{field} must be at least {minimum} characters")

    generated_at = parse_time(artifact.get("generated_at"))
    if generated_at is None:
        failures.append("generated_at must be a timezone-aware ISO timestamp")

    confidence = artifact.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        failures.append("confidence must be a number between 0 and 1")

    if artifact.get("no_legal_advice") is not True:
        failures.append("no_legal_advice must be true")

    if artifact.get("private_data_included") is not False:
        failures.append("private_data_included must be false")

    action_items = artifact.get("action_items")
    if not isinstance(action_items, list) or len(action_items) < 2:
        failures.append("action_items must contain at least two items")

    risks = artifact.get("risks")
    if not isinstance(risks, list) or len(risks) < 1:
        failures.append("risks must contain at least one item")

    citations = artifact.get("citations")
    if not isinstance(citations, list) or len(citations) < 1:
        failures.append("citations must contain at least one citation")
        citations = []

    required_ids = set(card.get("required_source_ids", []))
    cited_ids: set[str] = set()
    for index, citation in enumerate(citations):
        if not isinstance(citation, dict):
            failures.append(f"citations[{index}] must be an object")
            continue
        source_id = citation.get("source_id")
        source = sources_by_id.get(source_id)
        if not source:
            failures.append(f"citations[{index}].source_id is not in source baseline")
            continue
        cited_ids.add(source_id)
        if source.get("reliability_tier") not in ELIGIBLE_SOURCE_TIERS:
            failures.append(f"citations[{index}] must cite an eligible official source")
        if source.get("jurisdiction_code") != artifact.get("jurisdiction_code"):
            failures.append(f"citations[{index}] jurisdiction does not match artifact")
        if citation.get("url") != source.get("url"):
            failures.append(f"citations[{index}].url must match the source registry URL")
        retrieved_at = parse_time(citation.get("retrieved_at"))
        if retrieved_at is None:
            failures.append(f"citations[{index}].retrieved_at must be a timezone-aware ISO timestamp")
        elif generated_at is not None and retrieved_at > generated_at:
            failures.append(f"citations[{index}].retrieved_at must not be later than generated_at")
        note = citation.get("evidence_note")
        if not isinstance(note, str) or len(note.strip()) < 15:
            failures.append(f"citations[{index}].evidence_note must explain the evidence")

    missing_required = sorted(required_ids - cited_ids)
    if missing_required:
        failures.append(f"missing required source citations: {', '.join(missing_required)}")

    polaris = artifact.get("polaris")
    if not isinstance(polaris, dict):
        failures.append("polaris must be an object")
    else:
        if not is_url(polaris.get("worker_deploy_url")):
            failures.append("polaris.worker_deploy_url must be an https URL")
        if not isinstance(polaris.get("artifact_hash"), str) or not polaris["artifact_hash"].strip():
            failures.append("polaris.artifact_hash is required")
        if not isinstance(polaris.get("usage_attribution_path"), str) or not polaris["usage_attribution_path"].strip():
            failures.append("polaris.usage_attribution_path is required")

    attestations = artifact.get("disqualifier_attestations")
    if not isinstance(attestations, dict):
        failures.append("disqualifier_attestations must be an object")
    else:
        for key in sorted(REQUIRED_ATTESTATIONS):
            if attestations.get(key) is not True:
                failures.append(f"disqualifier_attestations.{key} must be true")

    score, score_parts = score_artifact(artifact, card, sources_by_id)
    if score < 75:
        warnings.append(f"score is {score}, below publish threshold 75")
    if failures:
        warnings.append("preflight failing means the artifact is ineligible for scoring")

    return failures, warnings, score, score_parts


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight a Cathedral regulatory intelligence artifact.")
    parser.add_argument(
        "artifact",
        type=Path,
        nargs="?",
        default=Path("examples/regulatory-intelligence/artifact.sample.json"),
        help="Path to artifact JSON",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=Path("examples/regulatory-intelligence/source-baseline.json"),
        help="Path to source baseline JSON",
    )
    parser.add_argument(
        "--cards",
        type=Path,
        default=Path("examples/regulatory-intelligence/cards.seed.json"),
        help="Path to card registry JSON",
    )
    parser.add_argument("--expect-fail", action="store_true", help="Exit 0 only when preflight fails")
    args = parser.parse_args()

    try:
        artifact = read_json(args.artifact)
        sources = read_json(args.sources)
        cards = read_json(args.cards)
        failures, warnings, score, score_parts = validate_artifact(artifact, sources, cards)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 0 if args.expect_fail else 2

    print("Cathedral regulatory intelligence preflight")
    print(f"artifact: {args.artifact.resolve()}")
    print(f"score: {score}")
    for key, value in score_parts.items():
        print(f"  {key}: {value}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  WARN {warning}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"  FAIL {failure}")
        return 0 if args.expect_fail else 1

    if args.expect_fail:
        print("\nFAIL expected preflight to fail, but it passed", file=sys.stderr)
        return 1

    print("\nPASS artifact is eligible for scoring intake")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
