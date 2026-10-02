from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "regulatory-intelligence"))

import preflight  # noqa: E402


def sample_inputs() -> tuple[dict, dict, dict]:
    example_root = ROOT / "examples" / "regulatory-intelligence"
    return (
        preflight.read_json(example_root / "artifact.sample.json"),
        preflight.read_json(example_root / "source-baseline.json"),
        preflight.read_json(example_root / "cards.seed.json"),
    )


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 1, tzinfo=tz or timezone.utc)


class PreflightTimestampTests(unittest.TestCase):
    def test_chronological_freshness_boundaries(self) -> None:
        artifact = {
            "generated_at": "2026-01-08T00:00:00Z",
            "citations": [{"source_id": "source", "retrieved_at": "2026-01-08T00:00:00Z"}],
            "risks": ["not legal advice"],
        }
        card = {"required_source_ids": ["source"]}

        self.assertEqual(preflight.score_artifact(artifact, card, {})[1]["freshness"], 20)
        artifact["citations"][0]["retrieved_at"] = "2026-01-01T00:00:00Z"
        self.assertEqual(preflight.score_artifact(artifact, card, {})[1]["freshness"], 20)
        artifact["citations"][0]["retrieved_at"] = "2025-12-31T00:00:00Z"
        self.assertEqual(preflight.score_artifact(artifact, card, {})[1]["freshness"], 0)

    def test_future_citation_is_rejected_and_not_fresh(self) -> None:
        artifact, sources, cards = sample_inputs()
        artifact["generated_at"] = "2026-01-01T00:00:00Z"
        artifact["citations"][0]["retrieved_at"] = "2026-01-02T00:00:00Z"

        failures, _, _, parts = preflight.validate_artifact(artifact, sources, cards)

        self.assertTrue(any("must not be later than generated_at" in item for item in failures))
        self.assertEqual(parts["freshness"], 0)

    def test_naive_timestamps_are_rejected_without_comparison_crash(self) -> None:
        artifact, sources, cards = sample_inputs()
        artifact["generated_at"] = "2026-01-01T00:00:00"
        artifact["citations"][0]["retrieved_at"] = "2026-01-01T00:00:00"

        failures, _, _, parts = preflight.validate_artifact(artifact, sources, cards)

        self.assertTrue(any("timezone-aware" in item for item in failures))
        self.assertEqual(parts["freshness"], 0)

    def test_missing_or_invalid_generation_time_gets_no_clock_fallback_credit(self) -> None:
        for invalid_time in (None, "not-a-time"):
            with self.subTest(generated_at=invalid_time):
                artifact = {
                    "generated_at": invalid_time,
                    "citations": [{"source_id": "source", "retrieved_at": "2026-01-01T00:00:00Z"}],
                    "risks": ["not legal advice"],
                }
                with patch.object(preflight, "datetime", FrozenDateTime):
                    parts = preflight.score_artifact(artifact, {"required_source_ids": ["source"]}, {})[1]
                self.assertEqual(parts["freshness"], 0)


if __name__ == "__main__":
    unittest.main()
