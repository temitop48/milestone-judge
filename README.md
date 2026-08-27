# MilestoneJudge

MilestoneJudge is a contract-only GenLayer Intelligent Contract for deciding
whether an explicit milestone is complete. It evaluates 1–5 acceptance
criteria against 1–5 unique public HTTP(S) evidence URLs.

The leader normalizes evidence one URL at a time and evaluates each criterion.
The validator independently repeats that substantive evaluation from a storage
snapshot. Consensus requires exact agreement on the verdict, all evidence and
criterion counts, and every criterion status. Explanation and finding prose are
non-material and may differ.

Verdicts are computed deterministically from normalized criterion statuses:
`COMPLETED`, `PARTIALLY_COMPLETED`, `NOT_COMPLETED`, or
`INSUFFICIENT_EVIDENCE`. The lifecycle is `CREATED` → `EVIDENCE_SUBMITTED` →
`ADJUDICATED`; `FINAL` is reserved for a future explicit finalization flow.

## Core calls

Use `create_milestone`, `submit_evidence`, and `adjudicate_milestone`, then
read results with `get_milestone` and `get_adjudication`. Existence checks are
available through `milestone_exists` and `adjudication_exists`.

No frontend, wallet UI, challenge flow, deployment, or token/reward logic is
included.
