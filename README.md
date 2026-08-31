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

The comparative-equivalence principle binds both the overall outcome and the
criterion-level decision vector.

Validators must agree on:

- the same overall verdict
- the same satisfied criterion count
- the same total criterion count
- the same substantive status for every criterion at the same zero-based index

`SATISFIED`, `PARTIALLY_SATISFIED`, `UNSATISFIED`, and `UNVERIFIABLE` are
distinct criterion outcomes.

Two adjudications are not materially equivalent when they produce the same
overall verdict but disagree about the substantive status of any individual
criterion.

The four overall outcomes are also distinct:

- `COMPLETED`
- `PARTIALLY_COMPLETED`
- `NOT_COMPLETED`
- `INSUFFICIENT_EVIDENCE`

Differences in explanatory prose, evidence classification, findings, or exact
evidence references may be acceptable only when they do not change any
criterion status or the overall verdict.

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

Evidence submission is restricted to the address that created the milestone.

This prevents another caller from attaching evidence to a milestone before its
creator submits the intended evidence set.

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
criterion-level evaluation.

The stored adjudication includes:

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

## Studionet live verification

The corrected criterion-bound MilestoneJudge contract has completed a full
end-to-end lifecycle on GenLayer Studionet.

This deployment incorporates the criterion-level consensus hardening and
creator-only evidence submission rule documented above.

### Deployment

Contract:

`0x7ba4372E06A158684817aD48c5Cd1e7d3329c6e5`

Deployment transaction:

`0x0ba684c37be6b85d94c8138b0bb17ebd4a4c4dd3b6b107f6823930f7f25499f9`

Deployed source commit:

`c2c7f634101d901e1c0dff03c9ee2451fe3e0147`

Deployed source SHA256:

`2e6161422c1cf202241a6601843970d8ad6301c1aba715490d17a7d023afdd67`

The deployment reached:

- consensus result: `MAJORITY_AGREE`
- transaction status: `ACCEPTED`
- consensus rounds: 1

### Live milestone

Milestone ID:

`milestonejudge-live-013`

The milestone was created specifically to verify the corrected consensus and
evidence-submission behavior.

Acceptance criteria:

1. The contract binds validator equivalence to the same substantive status for
   every criterion index.
2. Evidence submission is restricted to the milestone creator.
3. The corrected contract is documented and covered by passing tests.

Create transaction:

`0xff59d27ad0b4e0227bc4e163d55ca6f267fa39a730200dd65ae78f5c2a02f04b`

Evidence submission transaction:

`0xcd999889c0c7fb8a69a5c23053761848d8ac7074973b05e33ab27a4ad6731edc`

Adjudication transaction:

`0xe6b2f4ff99726f1394309f18ec43f65795b54ec9a5a616e9df3f1c6ebb1143e7`

The complete lifecycle was persisted:

`CREATED` → `EVIDENCE_SUBMITTED` → `ADJUDICATED`

### Live adjudication result

The adjudication completed with GenLayer validator consensus:

- consensus result: `MAJORITY_AGREE`
- transaction status: `ACCEPTED`
- consensus rounds: 1
- final round: 3 `AGREE`, 2 `IDLE`
- stored milestone status: `ADJUDICATED`
- accessible evidence: 3 / 3
- satisfied criteria: 3 / 3
- stored verdict: `COMPLETED`

The persisted criterion-level decision vector is:

1. Criterion 0: `SATISFIED`
2. Criterion 1: `SATISFIED`
3. Criterion 2: `SATISFIED`

This is significant because validator equivalence for the corrected contract
does not bind only to the coarse overall verdict.

The comparative-equivalence rule requires the same substantive status at every
criterion index. An adjudication that agrees on `COMPLETED`,
`PARTIALLY_COMPLETED`, `NOT_COMPLETED`, or `INSUFFICIENT_EVIDENCE` at the
overall level but disagrees on an individual criterion status is not considered
materially equivalent.

The live adjudication therefore exercises the corrected criterion-bound
consensus path rather than only demonstrating milestone lifecycle persistence.

### Creator-only evidence submission

The live milestone was created by:

`0x1068298d7eaEf43dC3333C6D5Af7417096905b29`

Evidence was submitted through the creator-authorized path.

The deployed contract rejects `submit_evidence` when the caller does not match
the milestone creator, while permitting the creator to submit the intended
evidence set.

### Immutable evidence used

The live adjudication used repository files pinned to the exact deployed source
commit:

`c2c7f634101d901e1c0dff03c9ee2451fe3e0147`

The submitted evidence consisted of:

- `contracts/milestone_judge.py`
- `test/test_milestone_judge.py`
- `README.md`

All three evidence sources were accessible during adjudication.

The source contract directly evidenced the criterion-bound comparative
equivalence rule and creator-only evidence restriction. The test suite and
documentation provided additional evidence for those behaviors and the passing
test coverage.

Pinning the evidence to the deployed commit prevents later changes to `main`
from altering the material evaluated during this live run.

## Previous Studionet verification

An earlier deployment at:

`0xe2c3004038181A2A4d9fa5F22214A9FD8875bD69`

completed a full live lifecycle for `milestonejudge-live-012` and reached
`MAJORITY_AGREE` / `ACCEPTED`.

That version demonstrated nondeterministic evidence evaluation and comparative
validator equivalence, but its equivalence principle did not bind consensus
strictly enough to the substantive status of every individual criterion.

The current deployment supersedes that verification for the corrected
criterion-bound implementation.

The earlier run remains useful historical evidence of the contract's
development, but `milestonejudge-live-013` is the canonical live verification
for the current implementation.

## Tests

The repository includes tests covering:

- contract validation
- milestone lifecycle behavior
- creator-only evidence submission
- evidence normalization
- malformed model output
- criterion-result validation
- snapshot ordering
- persistent storage declarations
- comparative equivalence
- criterion-level consensus binding

The corrected contract passes:

- 37 automated tests
- Python compilation
- GenVM lint and validation

The live Studionet deployment and adjudication described above use the corrected
contract source pinned to commit:

`c2c7f634101d901e1c0dff03c9ee2451fe3e0147`

## Scope

MilestoneJudge is deliberately narrow.

It contributes a reusable Intelligent Contract primitive for evidence-backed
milestone adjudication.

Applications and protocols can build interfaces, payment systems, grant
workflows, bounty systems, or governance processes around the contract without
those product-specific components being part of this repository.

This separation keeps the contribution focused on GenLayer-native Intelligent
Contract functionality.