# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

"""MilestoneJudge: consensus-backed milestone and evidence adjudication."""

from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse

from genlayer import *


CREATED = "CREATED"
EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
ADJUDICATED = "ADJUDICATED"
FINAL = "FINAL"

SATISFIED = "SATISFIED"
PARTIALLY_SATISFIED = "PARTIALLY_SATISFIED"
UNSATISFIED = "UNSATISFIED"
UNVERIFIABLE = "UNVERIFIABLE"

COMPLETED = "COMPLETED"
PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
NOT_COMPLETED = "NOT_COMPLETED"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

EVIDENCE_TYPES = ("DOCUMENTATION", "CODE", "TEST", "DEPLOYMENT", "DESIGN", "OTHER", "INACCESSIBLE")


@allow_storage
@dataclass
class Milestone:
    milestone_id: str
    creator: str
    title: str
    description: str
    acceptance_criteria: DynArray[str]
    evidence_urls: DynArray[str]
    status: str


@allow_storage
@dataclass
class NormalizedEvidence:
    url: str
    accessible: bool
    relevant_criteria: DynArray[u32]
    supports_completion: bool
    evidence_type: str
    finding: str


@allow_storage
@dataclass
class CriterionResult:
    criterion_index: u32
    status: str
    evidence_refs: DynArray[u32]


@allow_storage
@dataclass
class Adjudication:
    milestone_id: str
    verdict: str
    satisfied_criteria_count: u32
    total_criteria_count: u32
    accessible_evidence_count: u32
    total_evidence_count: u32
    criterion_statuses: DynArray[str]
    reason: str
    normalized_evidence: DynArray[NormalizedEvidence]
    criterion_results: DynArray[CriterionResult]


def _error(message: str) -> None:
    raise gl.vm.UserError(message)


def _valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _validate_criteria(criteria: List[str]) -> None:
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 5:
        _error("Acceptance criteria must contain between 1 and 5 items")
    if any(not isinstance(item, str) or not item.strip() for item in criteria):
        _error("Acceptance criteria must be non-empty strings")


def _validate_urls(urls: List[str]) -> None:
    if not isinstance(urls, list) or not 1 <= len(urls) <= 5:
        _error("Evidence must contain between 1 and 5 URLs")
    normalized = []
    for url in urls:
        if not isinstance(url, str) or not _valid_url(url):
            _error("Evidence URLs must be public HTTP(S) URLs")
        canonical = url.strip()
        if canonical in normalized:
            _error("Evidence URLs must be unique")
        normalized.append(canonical)


def _status_is_valid(status: str) -> bool:
    return status in (SATISFIED, PARTIALLY_SATISFIED, UNSATISFIED, UNVERIFIABLE)


def _canonical_indexes(values: Any, upper_bound: int, error_message: str) -> List[int]:
    """Validate and canonicalize zero-based integer indexes."""
    if not isinstance(values, list):
        _error(error_message)

    indexes = []
    for value in values:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or value >= upper_bound
        ):
            _error(error_message)
        if value not in indexes:
            indexes.append(value)

    indexes.sort()
    return indexes


def _normalize_item(
    url: str,
    raw: Dict[str, Any],
    criterion_count: int,
    *,
    accessible: bool,
) -> Dict[str, Any]:
    """Validate and canonicalize one independently produced evidence result."""
    if not isinstance(raw, dict):
        _error("Normalized evidence must be a JSON object")

    supports_completion = raw.get("supports_completion", False)
    evidence_type = raw.get("evidence_type", "OTHER")
    finding = raw.get("finding", "")

    if not isinstance(accessible, bool):
        _error("Evidence accessible must be boolean")
    if not isinstance(supports_completion, bool):
        _error("Evidence supports_completion must be boolean")
    if not isinstance(evidence_type, str) or evidence_type not in EVIDENCE_TYPES:
        _error("Evidence type is invalid")
    if not isinstance(finding, str):
        _error("Evidence finding must be a string")

    relevant_criteria = _canonical_indexes(
        raw.get("relevant_criteria", []),
        criterion_count,
        "Evidence relevant_criteria contains invalid indexes",
    )

    if not accessible:
        if supports_completion or relevant_criteria:
            _error("Inaccessible evidence cannot support completion")
        if evidence_type != "INACCESSIBLE":
            _error("Inaccessible evidence must use INACCESSIBLE evidence type")
    elif evidence_type == "INACCESSIBLE":
        _error("Accessible evidence cannot use INACCESSIBLE evidence type")

    return {
        "url": url,
        "accessible": accessible,
        "relevant_criteria": relevant_criteria,
        "supports_completion": supports_completion,
        "evidence_type": evidence_type,
        "finding": finding.strip(),
    }


def _normalize_criterion(index: int, raw: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        _error("Criterion result must be a JSON object")

    criterion_index = raw.get("criterion_index")
    if (
        not isinstance(criterion_index, int)
        or isinstance(criterion_index, bool)
        or criterion_index != index
    ):
        _error("Criterion result has an invalid criterion_index")

    status = raw.get("status")
    if not isinstance(status, str) or not _status_is_valid(status):
        _error("Criterion result has an invalid status")

    refs = _canonical_indexes(
        raw.get("evidence_refs"),
        len(evidence),
        "Criterion result contains invalid evidence_refs",
    )

    for ref in refs:
        if not evidence[ref]["accessible"]:
            _error("Criterion result references inaccessible evidence")
        if index not in evidence[ref]["relevant_criteria"]:
            _error("Criterion result references evidence unrelated to the criterion")

    if status in (SATISFIED, PARTIALLY_SATISFIED) and not refs:
        _error("Satisfied or partially satisfied criteria require evidence references")

    return {
        "criterion_index": index,
        "status": status,
        "evidence_refs": refs,
    }


def _deterministic_verdict(statuses: List[str], accessible_count: int) -> str:
    if accessible_count == 0:
        return INSUFFICIENT_EVIDENCE
    satisfied = statuses.count(SATISFIED)
    partial = statuses.count(PARTIALLY_SATISFIED)
    if satisfied == len(statuses):
        return COMPLETED
    if satisfied or partial:
        return PARTIALLY_COMPLETED
    return NOT_COMPLETED


def _evaluate_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Nondeterministic evaluation. It reads only the supplied snapshot."""
    normalized = []
    for url in snapshot["evidence_urls"]:
        try:
            page = gl.nondet.web.render(url, mode="text")
        except Exception:
            normalized.append(_normalize_item(
                url,
                {
                    "relevant_criteria": [],
                    "supports_completion": False,
                    "evidence_type": "INACCESSIBLE",
                    "finding": "Evidence could not be accessed.",
                },
                len(snapshot["acceptance_criteria"]),
                accessible=False,
            ))
            continue
        prompt = (
            "Classify this milestone evidence. Return ONLY one JSON object and do not invent facts.\n"
            "Criteria use ZERO-BASED indexes 0 through "
            + str(len(snapshot["acceptance_criteria"]) - 1) + ".\n"
            "Criteria: " + repr(snapshot["acceptance_criteria"]) + "\n"
            "Evidence URL: " + url + "\nPage: " + str(page) + "\n"
            "Return these semantic fields when available; omitted fields use the conservative defaults described below:\n"
            "- relevant_criteria: list of unique ZERO-BASED integer criterion indexes; use [] if none\n"
            "- supports_completion: boolean; if omitted the contract conservatively treats it as false\n"
            "- evidence_type: exactly one of DOCUMENTATION, CODE, TEST, DEPLOYMENT, DESIGN, OTHER, INACCESSIBLE; "
            "if omitted the contract conservatively treats it as OTHER\n"
            "- finding: string; optional explanatory text\n"
            "The page has already been fetched successfully, so do NOT return an accessible field. "
            "Do not use INACCESSIBLE as the evidence_type."
        )
        raw = gl.nondet.exec_prompt(prompt, response_format="json")
        normalized.append(
            _normalize_item(
                url,
                raw,
                len(snapshot["acceptance_criteria"]),
                accessible=True,
            )
        )

    criterion_results = []
    for index, criterion in enumerate(snapshot["acceptance_criteria"]):
        prompt = (
            "Evaluate exactly one milestone acceptance criterion. Return ONLY one JSON object.\n"
            "Criterion index: " + str(index) + "\nCriterion: " + criterion + "\n"
            "Normalized evidence uses ZERO-BASED evidence indexes:\n" + repr(normalized) + "\n"
            "The JSON object MUST contain:\n"
            "- criterion_index: exactly " + str(index) + "\n"
            "- status: exactly one of SATISFIED, PARTIALLY_SATISFIED, UNSATISFIED, UNVERIFIABLE\n"
            "- evidence_refs: list of unique ZERO-BASED integer evidence indexes\n"
            "Every evidence_refs entry MUST reference accessible evidence whose relevant_criteria "
            "contains criterion index " + str(index) + ".\n"
            "SATISFIED or PARTIALLY_SATISFIED MUST have at least one evidence reference. "
            "Use [] when no qualifying evidence supports the criterion."
        )
        raw = gl.nondet.exec_prompt(prompt, response_format="json")
        criterion_results.append(_normalize_criterion(index, raw, normalized))

    statuses = [result["status"] for result in criterion_results]
    accessible_count = sum(1 for item in normalized if item["accessible"])
    return {
        "verdict": _deterministic_verdict(statuses, accessible_count),
        "satisfied_criteria_count": statuses.count(SATISFIED),
        "total_criteria_count": len(statuses),
        "accessible_evidence_count": accessible_count,
        "total_evidence_count": len(normalized),
        "criterion_statuses": statuses,
        "reason": "Adjudication derived from independently normalized evidence and criterion statuses.",
        "normalized_evidence": normalized,
        "criterion_results": criterion_results,
    }


def _validate_evaluation(result: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
    required = (
        "verdict", "satisfied_criteria_count", "total_criteria_count",
        "accessible_evidence_count", "total_evidence_count", "criterion_statuses",
        "reason", "normalized_evidence", "criterion_results",
    )
    if not isinstance(result, dict) or any(key not in result for key in required):
        _error("Malformed adjudication result")
    if (
        not isinstance(result["reason"], str)
        or not isinstance(result["normalized_evidence"], list)
        or not isinstance(result["criterion_results"], list)
        or not isinstance(result["criterion_statuses"], list)
    ):
        _error("Malformed adjudication result")
    if len(result["normalized_evidence"]) != len(snapshot["evidence_urls"]):
        _error("Malformed adjudication result")
    if len(result["criterion_results"]) != len(snapshot["acceptance_criteria"]):
        _error("Malformed adjudication result")
    if len(result["criterion_statuses"]) != len(snapshot["acceptance_criteria"]):
        _error("Malformed adjudication result")
    count_fields = (
        "satisfied_criteria_count", "total_criteria_count",
        "accessible_evidence_count", "total_evidence_count",
    )
    if any(not isinstance(result[field], int) or isinstance(result[field], bool) for field in count_fields):
        _error("Malformed adjudication result")
    normalized = []
    for url, item in zip(snapshot["evidence_urls"], result["normalized_evidence"]):
        if not isinstance(item, dict) or not isinstance(item.get("accessible"), bool):
            _error("Malformed adjudication result")
        normalized.append(
            _normalize_item(
                url,
                item,
                len(snapshot["acceptance_criteria"]),
                accessible=item["accessible"],
            )
        )
    criterion_results = []
    for index, item in enumerate(result["criterion_results"]):
        criterion_results.append(_normalize_criterion(index, item, normalized))
    statuses = [item["status"] for item in criterion_results]
    if result["criterion_statuses"] != statuses:
        _error("Criterion statuses do not match criterion results")
    accessible_count = sum(1 for item in normalized if item["accessible"])
    if result["accessible_evidence_count"] != accessible_count:
        _error("Accessible evidence count does not match normalized evidence")
    if result["total_evidence_count"] != len(normalized):
        _error("Total evidence count does not match normalized evidence")
    if result["total_criteria_count"] != len(statuses):
        _error("Total criterion count does not match criterion results")
    if result["satisfied_criteria_count"] != statuses.count(SATISFIED):
        _error("Satisfied criterion count does not match criterion results")
    if result["verdict"] != _deterministic_verdict(statuses, accessible_count):
        _error("Verdict is not the deterministic result of criterion statuses")


def _material(result: Dict[str, Any]) -> tuple:
    """Return only consensus-material adjudication outcomes.

    Independent validators may reasonably differ on evidence classification,
    criterion relevance, or supporting evidence references while still
    agreeing on whether each acceptance criterion is satisfied. Those
    intermediate interpretations remain validated and persisted, but they are
    not part of equivalence consensus.
    """
    return (
        result["verdict"],
        result["satisfied_criteria_count"],
        result["total_criteria_count"],
        result["accessible_evidence_count"],
        result["total_evidence_count"],
        tuple(result["criterion_statuses"]),
    )


class MilestoneJudge(gl.Contract):
    milestones: TreeMap[str, Milestone]
    adjudications: TreeMap[str, Adjudication]

    def __init__(self):
        pass

    @gl.public.write
    def create_milestone(self, milestone_id: str, title: str, description: str, acceptance_criteria: List[str]) -> None:
        if not isinstance(milestone_id, str) or not milestone_id.strip():
            _error("Milestone ID must not be empty")
        if not isinstance(title, str) or not title.strip():
            _error("Title must not be empty")
        if not isinstance(description, str) or not description.strip():
            _error("Description must not be empty")
        if milestone_id in self.milestones:
            _error("Milestone already exists")
        _validate_criteria(acceptance_criteria)
        self.milestones[milestone_id] = Milestone(
            milestone_id, str(gl.message.sender_address), title.strip(), description.strip(),
            acceptance_criteria, [], CREATED,
        )

    @gl.public.write
    def submit_evidence(self, milestone_id: str, evidence_urls: List[str]) -> None:
        if milestone_id not in self.milestones:
            _error("Milestone does not exist")
        milestone = self.milestones[milestone_id]
        if milestone.status != CREATED:
            _error("Evidence can only be submitted for a CREATED milestone")
        _validate_urls(evidence_urls)
        milestone.evidence_urls = [url.strip() for url in evidence_urls]
        milestone.status = EVIDENCE_SUBMITTED
        self.milestones[milestone_id] = milestone

    @gl.public.write
    def adjudicate_milestone(self, milestone_id: str) -> None:
        if milestone_id not in self.milestones:
            _error("Milestone does not exist")
        milestone = self.milestones[milestone_id]
        if milestone.status != EVIDENCE_SUBMITTED:
            _error("Milestone must have submitted evidence")
        if milestone_id in self.adjudications:
            _error("Milestone has already been adjudicated")
        snapshot = {
            "milestone_id": milestone.milestone_id,
            "title": milestone.title,
            "description": milestone.description,
            "acceptance_criteria": list(milestone.acceptance_criteria),
            "evidence_urls": list(milestone.evidence_urls),
        }

        def evaluate():
            result = _evaluate_snapshot(snapshot)
            _validate_evaluation(result, snapshot)
            return result

        result = gl.eq_principle.prompt_comparative(
            evaluate,
            principle=(
                "Determine whether the two milestone adjudications are materially equivalent. "
                "The overall verdict must represent the same milestone completion outcome. "
                "Criterion conclusions must be substantively consistent with that overall outcome. "
                "Differences in explanatory text, evidence_type, relevant_criteria, "
                "supports_completion, finding text, or exact evidence_refs are acceptable "
                "when they do not change the substantive milestone completion decision. "
                "COMPLETED, PARTIALLY_COMPLETED, NOT_COMPLETED, and INSUFFICIENT_EVIDENCE "
                "are distinct outcomes and must not be treated as equivalent."
            ),
        )
        _validate_evaluation(result, snapshot)
        self.adjudications[milestone_id] = Adjudication(
            milestone_id=milestone_id,
            verdict=result["verdict"],
            satisfied_criteria_count=result["satisfied_criteria_count"],
            total_criteria_count=result["total_criteria_count"],
            accessible_evidence_count=result["accessible_evidence_count"],
            total_evidence_count=result["total_evidence_count"],
            criterion_statuses=result["criterion_statuses"],
            reason=result["reason"],
            normalized_evidence=[NormalizedEvidence(**item) for item in result["normalized_evidence"]],
            criterion_results=[CriterionResult(**item) for item in result["criterion_results"]],
        )
        milestone.status = ADJUDICATED
        self.milestones[milestone_id] = milestone

    @gl.public.view
    def get_milestone(self, milestone_id: str) -> Milestone:
        if milestone_id not in self.milestones:
            _error("Milestone does not exist")
        return self.milestones[milestone_id]

    @gl.public.view
    def get_adjudication(self, milestone_id: str) -> Adjudication:
        if milestone_id not in self.adjudications:
            _error("Adjudication does not exist")
        return self.adjudications[milestone_id]

    @gl.public.view
    def milestone_exists(self, milestone_id: str) -> bool:
        return milestone_id in self.milestones

    @gl.public.view
    def adjudication_exists(self, milestone_id: str) -> bool:
        return milestone_id in self.adjudications
