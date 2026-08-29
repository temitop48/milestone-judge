# MilestoneJudge

MilestoneJudge is a contract-only GenLayer Intelligent Contract for adjudicating
whether an explicit milestone or deliverable has been completed against
verifiable acceptance criteria.

It is designed as reusable adjudication infrastructure for grants, bounties,
DAO deliverables, freelance milestones, hackathon deliverables, and other
workflows where completion should be evaluated from public evidence rather than
asserted by a single party.

MilestoneJudge evaluates 1–5 acceptance criteria against 1–5 unique public
HTTP(S) evidence URLs and persists the resulting adjudication on GenLayer.

## Why GenLayer

Milestone adjudication is not always reducible to deterministic smart-contract
logic. Evidence may consist of source code, documentation, tests, research,
integrations, or other public material that requires interpretation.

MilestoneJudge uses GenLayer's nondeterministic execution and validator
consensus to perform that interpretation inside an Intelligent Contract.

During adjudication:

1. A storage snapshot of the milestone and submitted evidence is created before
   nondeterministic evaluation.
2. Each public evidence URL is rendered and normalized independently.
3. Each acceptance criterion is evaluated against the accessible evidence.
4. The resulting adjudication is structurally validated.
5. GenLayer comparative equivalence is used so validators independently perform
   the substantive evaluation and determine whether their adjudications are
   materially equivalent.

The comparative-equivalence principle treats the four substantive outcomes as
distinct:

- `COMPLETED`
- `PARTIALLY_COMPLETED`
- `NOT_COMPLETED`
- `INSUFFICIENT_EVIDENCE`

Differences in explanatory prose or intermediate evidence classifications may
be acceptable when they do not change the substantive milestone completion
decision.

## Persistent GenLayer storage

MilestoneJudge stores contract state using GenLayer-compatible persistent
storage types.

The contract maintains:

- `TreeMap[str, Milestone]` for milestones
- `TreeMap[str, Adjudication]` for adjudication results
- `DynArray` fields for acceptance criteria, evidence URLs, normalized evidence,
  criterion results, criterion statuses, and evidence references

This allows milestone creation, evidence submission, adjudication, and the
resulting decision to remain queryable from contract state.

## Lifecycle

A milestone follows this lifecycle:

`CREATED` → `EVIDENCE_SUBMITTED` → `ADJUDICATED`

`FINAL` is reserved for a future explicit finalization flow and is not exposed
as a current public workflow.

## Contract interface

### Write methods

- `create_milestone`
- `submit_evidence`
- `adjudicate_milestone`

### View methods

- `get_milestone`
- `get_adjudication`
- `milestone_exists`
- `adjudication_exists`

MilestoneJudge intentionally contains no frontend, browser utility, wallet UI,
token/reward mechanism, deployment service, or challenge/review workflow.

The repository is focused exclusively on the reusable GenLayer Intelligent
Contract, its tests, and its documentation.

## Evidence model

Each milestone accepts between 1 and 5 unique public HTTP(S) evidence URLs.

During adjudication, evidence is independently rendered and normalized before
criterion-level evaluation. The stored adjudication includes:

- overall verdict
- satisfied criterion count
- total criterion count
- accessible evidence count
- total evidence count
- criterion statuses
- criterion-level evidence references
- normalized evidence metadata

This preserves both the final outcome and the structured evidence assessment
that produced it.

## Studionet verification

MilestoneJudge has completed a full live lifecycle on GenLayer Studionet.

### Deployment

Contract:

`0xe2c3004038181A2A4d9fa5F22214A9FD8875bD69`

Deployment transaction:

`0x48f4a5da2cf8af18869ede054bb9478daf0455b036eca349526e90818832b907`

### Live milestone

Milestone ID:

`milestonejudge-live-012`

Evidence submission transaction:

`0x45820da7636cc6f44a370c5c46603453b73d83d0f80a492de1795f2e26273d8f`

Adjudication transaction:

`0x59ad786c50146d3cca78e9e3fad7456520b6969d4a1d4d6e35509c377a990b7c`

The adjudication transaction completed with GenLayer validator consensus:

- consensus result: `MAJORITY_AGREE`
- transaction status: `ACCEPTED`
- final round votes: 3 `AGREE`, 2 `DISAGREE`
- stored milestone status: `ADJUDICATED`
- accessible evidence: 3 / 3
- satisfied criteria: 2 / 3
- stored verdict: `PARTIALLY_COMPLETED`

The partial result is intentionally preserved as live evidence of the
adjudication behavior. The contract did not automatically approve its own
milestone; the submitted evidence was evaluated and a validator-backed
substantive result was persisted.

### Immutable evidence used

The live adjudication used repository files pinned to commit:

`30ea62062c12bd2c6fc5a00464fdccd46de56e52`

The submitted evidence consisted of:

- `contracts/milestone_judge.py`
- `test/test_milestone_judge.py`
- `README.md`

The immutable commit preserves the exact contract, tests, and documentation
that were evaluated during the live Studionet run.

## Tests

The repository includes tests covering contract validation, milestone
lifecycle behavior, evidence normalization, malformed model output,
criterion-result validation, snapshot ordering, storage declarations, and
comparative-equivalence integration.

The frozen contract version used for the live Studionet deployment passed
35 tests together with Python compilation and GenVM lint validation.

## Scope

MilestoneJudge is deliberately narrow.

It contributes a reusable Intelligent Contract primitive for evidence-backed
milestone adjudication. Applications and protocols can build interfaces,
payment systems, grant workflows, bounty systems, or governance processes
around the contract without those product-specific components being part of
this repository.

This separation keeps the contribution focused on GenLayer-native Intelligent
Contract functionality.
