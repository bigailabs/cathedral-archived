# Polaris Agent Identifier Contract

Status: v0.1 draft

This contract defines how Cathedral scores Polaris-hosted agent work without using miner IP addresses as the product interface.

## Core rule

Miners submit agent identifiers to Cathedral. Cathedral pulls evidence from Polaris.

The miner does not submit an IP address as proof. The miner submits a claim that points to a Polaris agent, deployment, artifact, or run. Cathedral then asks Polaris for signed records that prove what happened.

On-chain axon IP and port may still exist for Bittensor validator plumbing. They are not the contract for ModelFactory, regulatory intelligence cards, or other Polaris-hosted work units.

## Why this replaces IP-first flow

The old compute-miner path needed validators to discover miner hosts and connect to them directly. That is useful for raw compute validation, but it is the wrong primitive for Polaris-hosted agent work.

For agent work, Polaris already owns:

- runtime identity
- deployment identity
- agent health
- run records
- traces
- artifact hashes
- usage ledger
- credit spend attribution
- abuse flags

Cathedral should consume those records instead of trying to infer product state from subnet IPs.

## Identifiers

| Identifier | Owner | Meaning |
| --- | --- | --- |
| `polaris_agent_id` | Polaris | Stable identity for a worker or agent profile. Example: `agt_reg_eu_ai_act_001`. |
| `polaris_deployment_id` | Polaris | Runtime deployment that runs the agent. Can change across upgrades. |
| `polaris_run_id` | Polaris | One execution, job, card refresh, eval, or task attempt. |
| `polaris_artifact_id` | Polaris | Output asset: model, LoRA, router, card, eval report, dataset, or deployable harness. |
| `cathedral_claim_id` | Cathedral | Submission record created when a miner asks Cathedral to score Polaris work. |
| `miner_hotkey` | Bittensor | Miner identity for reward attribution. |
| `owner_wallet` | Polaris and Cathedral | Wallet or account that controls the agent or artifact. |

## Miner claim

A miner submits this to Cathedral:

```json
{
  "schema_version": "cathedral.polaris_agent_claim.v1",
  "claim_id": "claim_2026_05_10_001",
  "work_unit": "regulatory_intelligence_card",
  "miner_hotkey": "5F...",
  "owner_wallet": "5F...",
  "polaris_agent_id": "agt_reg_eu_ai_act_001",
  "polaris_deployment_id": "dep_01HX...",
  "polaris_artifact_id": "art_eu_ai_act_2026_05_10",
  "declared_capabilities": ["research", "summarize", "cite_sources"],
  "submitted_at": "2026-05-10T00:00:00Z",
  "miner_signature": "0x..."
}
```

The claim is not enough to receive rewards. It only tells Cathedral what to verify.

## Cathedral pull flow

1. Miner submits a claim with Polaris identifiers.
2. Cathedral checks claim shape and miner identity.
3. Cathedral calls Polaris for the agent manifest.
4. Cathedral checks ownership and work-unit eligibility.
5. Cathedral pulls run records, artifact records, and usage records.
6. Cathedral verifies signatures, hashes, and abuse flags.
7. Cathedral scores the work unit.
8. Cathedral emits reward weights from verified evidence.

## Required Polaris endpoints

Polaris should expose a Cathedral-scoped API surface:

```text
GET /api/cathedral/v1/agents/{polaris_agent_id}/manifest
GET /api/cathedral/v1/agents/{polaris_agent_id}/health
GET /api/cathedral/v1/agents/{polaris_agent_id}/runs?cursor=...
GET /api/cathedral/v1/runs/{polaris_run_id}
GET /api/cathedral/v1/artifacts/{polaris_artifact_id}
GET /api/cathedral/v1/artifacts/{polaris_artifact_id}/usage?cursor=...
GET /api/cathedral/v1/events?cursor=...
GET /.well-known/polaris/cathedral-jwks.json
```

Optional helper:

```text
POST /api/cathedral/v1/claims/verify
```

`claims/verify` can return a single verification bundle, but Cathedral must still be able to pull records independently.

## Agent manifest

```json
{
  "schema_version": "polaris.cathedral.agent_manifest.v1",
  "polaris_agent_id": "agt_reg_eu_ai_act_001",
  "polaris_deployment_id": "dep_01HX...",
  "runtime": "hermes",
  "work_unit": "regulatory_intelligence_card",
  "owner_wallet": "5F...",
  "miner_hotkey": "5F...",
  "status": "running",
  "created_at": "2026-05-10T00:00:00Z",
  "updated_at": "2026-05-10T00:30:00Z",
  "capabilities": ["research", "summarize", "cite_sources"],
  "config_version": "v1.0.3",
  "deployment_url": "https://polaris.computer/computer/agents/agt_reg_eu_ai_act_001",
  "proof_url": "https://polaris.computer/proof/dep_01HX...",
  "latest_artifact_ids": ["art_eu_ai_act_2026_05_10"],
  "signature": {
    "issuer": "polaris",
    "key_id": "polaris-cathedral-2026-05",
    "alg": "Ed25519",
    "value": "..."
  }
}
```

## Artifact record

```json
{
  "schema_version": "polaris.cathedral.artifact.v1",
  "polaris_artifact_id": "art_eu_ai_act_2026_05_10",
  "polaris_agent_id": "agt_reg_eu_ai_act_001",
  "polaris_run_id": "run_01HX...",
  "work_unit": "regulatory_intelligence_card",
  "artifact_type": "regulatory_card",
  "artifact_hash": "sha256:...",
  "content_url": "https://api.polaris.computer/api/cathedral/v1/artifacts/art_eu_ai_act_2026_05_10/content",
  "eval_report_url": "https://api.polaris.computer/api/cathedral/v1/artifacts/art_eu_ai_act_2026_05_10/eval",
  "created_at": "2026-05-10T00:30:00Z",
  "signature": {
    "issuer": "polaris",
    "key_id": "polaris-cathedral-2026-05",
    "alg": "Ed25519",
    "value": "..."
  }
}
```

## Usage record

```json
{
  "schema_version": "polaris.cathedral.usage.v1",
  "usage_id": "use_01HX...",
  "polaris_artifact_id": "art_eu_ai_act_2026_05_10",
  "polaris_agent_id": "agt_reg_eu_ai_act_001",
  "consumer_wallet": "5G...",
  "credits_spent": 0.18,
  "started_at": "2026-05-10T01:00:00Z",
  "ended_at": "2026-05-10T01:08:00Z",
  "excluded_from_rewards": false,
  "exclude_reason": null,
  "signature": {
    "issuer": "polaris",
    "key_id": "polaris-cathedral-2026-05",
    "alg": "Ed25519",
    "value": "..."
  }
}
```

Excluded usage must include a reason:

- `creator_owned`
- `platform_owned`
- `refunded`
- `abuse_flagged`
- `test_usage`
- `self_loop`

## Signed event envelope

Polaris events consumed by Cathedral should use one envelope:

```json
{
  "schema_version": "polaris.cathedral.event.v1",
  "event_id": "evt_01HX...",
  "event_type": "artifact_used",
  "occurred_at": "2026-05-10T01:08:00Z",
  "subject": {
    "polaris_agent_id": "agt_reg_eu_ai_act_001",
    "polaris_artifact_id": "art_eu_ai_act_2026_05_10",
    "miner_hotkey": "5F..."
  },
  "payload_hash": "sha256:...",
  "payload": {},
  "signature": {
    "issuer": "polaris",
    "key_id": "polaris-cathedral-2026-05",
    "alg": "Ed25519",
    "value": "..."
  }
}
```

Cathedral validates the signature before using the event for scoring.

## Cathedral validation rules

A claim is eligible only if:

1. The claim matches the JSON schema.
2. The miner hotkey is registered or explicitly allowed for the work unit.
3. Polaris returns a signed manifest for `polaris_agent_id`.
4. The manifest owner matches the claim owner or an allowed delegation.
5. The agent runtime is eligible for the work unit.
6. The artifact hash matches the content Polaris serves.
7. The run record proves the artifact came from the claimed deployment.
8. The usage records exclude self-usage, platform-owned usage, refunded usage, test usage, and abuse-flagged usage.
9. The artifact remains deployable or maintained for ongoing rewards.

## What Cathedral must not trust

- self-reported miner IP
- screenshots
- frontend-only URLs without signed backend records
- public benchmark claims without hidden or Cathedral-controlled evals
- creator-owned usage
- platform-owned usage
- unsigned Polaris event JSON

## Versioning

This contract uses explicit schema versions. Breaking changes require a new schema version and a transition window.

Current versions:

- `cathedral.polaris_agent_claim.v1`
- `polaris.cathedral.agent_manifest.v1`
- `polaris.cathedral.artifact.v1`
- `polaris.cathedral.usage.v1`
- `polaris.cathedral.event.v1`

