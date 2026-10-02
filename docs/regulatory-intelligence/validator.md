# Validator Guide: Regulatory Intelligence Cards

## Validator job

The validator checks whether a regulatory intelligence artifact is eligible, useful, and maintained.

It does not need to decide perfect legal truth in v1. It needs to reject obvious bad work and rank useful work.

## Scoring inputs

The v1 scorer uses:

- source quality
- source freshness
- citation coverage
- specificity
- usefulness
- clarity
- maintenance history

The local scorer is deterministic so validators can inspect it.

In this local harness, timestamps must include a timezone. A citation retrieved after its artifact generation is rejected, and citations more than seven days older than generation receive no freshness points. These checks describe local preflight behavior only; they do not establish production reward eligibility or change reward, chain, or economic policy.

## Required checks

For each artifact:

1. Schema is valid.
2. `card_id` exists in the card registry.
3. `worker_id` owns or is assigned the card.
4. Citations point to approved official sources.
5. The artifact says it is not legal advice.
6. No private data is included.
7. The update is specific enough to be useful.
8. The artifact has a Polaris deploy or worker attribution path.

## Abuse filters

The reward path should exclude:

- creator-owned usage
- platform-owned test usage
- refunded usage
- usage flagged as abuse
- synthetic loops between related wallets
- artifacts with broken deploy links
- artifacts that cannot be reproduced or inspected

## Local commands

```bash
just regulatory-preflight
just regulatory-e2e
```

## Score bands

- `90-100`: publish and reward
- `75-89`: publish if no material gaps
- `60-74`: hold for review
- `<60`: reject

## Current limitation

The v1 scorer is a local harness. Production validation still needs signed Polaris events, hidden challenger tasks, and live worker endpoint checks.
