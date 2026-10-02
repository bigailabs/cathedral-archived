# Polaris Contract for Cathedral Regulatory Intelligence

Cathedral depends on Polaris for runtime, identity, and usage evidence.

This work unit follows the canonical [Polaris Agent Identifier Contract](../polaris-agent-contract.md). Miners submit Polaris agent, deployment, run, or artifact identifiers. Cathedral pulls signed Polaris records for verification. Miner IP addresses are not proof for this work unit.

## Polaris owns

- Hermes worker deployment
- worker endpoint
- runtime health
- inference usage
- storage
- logs and traces
- usage ledger
- credit spend attribution
- deploy links

## Cathedral owns

- worker registry
- card registry
- job assignment
- artifact intake
- scoring
- reputation
- public feed
- reward feed

## Worker endpoint contract

A Hermes worker should expose:

```text
GET  /healthz
GET  /manifest
POST /jobs
```

### `GET /manifest`

```json
{
  "worker_id": "polaris_worker_reg_eu_ai_act_001",
  "runtime": "hermes",
  "category": "regulatory_intelligence",
  "capabilities": ["research", "summarize", "cite_sources"],
  "config_version": "v1.0.0"
}
```

### `POST /jobs`

```json
{
  "job_id": "job_reg_eu_ai_act_2026_05_10",
  "card_id": "eu_ai_act_watch",
  "objective": "Update the EU AI Act watch card from approved official sources.",
  "source_ids": ["eu_ai_act_eurlex", "eu_ai_act_commission"]
}
```

The worker returns or posts an artifact matching:

```text
examples/regulatory-intelligence/artifact.sample.json
```

## Polaris events Cathedral needs

```json
{
  "event_type": "worker_registered",
  "worker_id": "polaris_worker_reg_eu_ai_act_001",
  "wallet": "5F...",
  "runtime": "hermes",
  "deploy_url": "https://polaris.computer/deployments/...",
  "timestamp": "2026-05-10T00:00:00Z"
}
```

```json
{
  "event_type": "artifact_used",
  "artifact_id": "artifact_eu_ai_act_2026_05_10",
  "worker_id": "polaris_worker_reg_eu_ai_act_001",
  "credits_spent": 0.18,
  "consumer_wallet": "5G...",
  "excluded": false,
  "exclude_reason": null,
  "timestamp": "2026-05-10T00:00:00Z"
}
```

## Signing requirement

Production events should be signed by Polaris and include:

- event id
- timestamp
- worker id
- wallet id
- artifact hash
- deployment id
- signature

The local e2e harness stubs this for now.
