import ast
import importlib.util
import sys
import types
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[1] / "contracts" / "milestone_judge.py"


def _load_contract():
    genlayer = types.ModuleType("genlayer")
    gl = types.ModuleType("genlayer.gl")

    class UserError(Exception):
        pass

    class TreeMap(dict):
        @classmethod
        def __class_getitem__(cls, _item):
            return cls

        def contains(self, key):
            return key in self

    def identity(value=None):
        return value if value is not None else (lambda fn: fn)

    genlayer.allow_storage = identity
    genlayer.TreeMap = TreeMap
    genlayer.DynArray = list
    genlayer.u32 = int
    gl.Contract = type("Contract", (), {})
    gl.public = types.SimpleNamespace(write=identity, view=identity)
    gl.vm = types.SimpleNamespace(UserError=UserError)
    gl.message = types.SimpleNamespace(sender_address="0xsender")
    genlayer.gl = gl
    sys.modules["genlayer"] = genlayer
    spec = importlib.util.spec_from_file_location("milestone_judge_contract", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = _load_contract()


@pytest.mark.parametrize("criteria", [[], ["x"] * 6])
def test_criteria_limits(criteria):
    with pytest.raises(Exception, match="between 1 and 5"):
        m._validate_criteria(criteria)


def test_empty_criterion_is_rejected():
    with pytest.raises(Exception, match="non-empty"):
        m._validate_criteria([" "])


def test_empty_milestone_fields_are_rejected_by_source_contract():
    source = SOURCE.read_text()
    assert "Milestone ID must not be empty" in source
    assert "Title must not be empty" in source
    assert "Description must not be empty" in source


def test_invalid_and_duplicate_evidence_urls_are_rejected():
    with pytest.raises(Exception, match=r"public HTTP\(S\)"):
        m._validate_urls(["ftp://example.com/file"])
    with pytest.raises(Exception, match="unique"):
        m._validate_urls(["https://example.com/a", "https://example.com/a"])
    with pytest.raises(Exception, match="between 1 and 5"):
        m._validate_urls(["https://example.com/" for _ in range(6)])


def test_malformed_normalized_evidence_is_rejected():
    with pytest.raises(Exception, match="missing required fields"):
        m._normalize_item("https://example.com", {"accessible": True}, 1)


@pytest.mark.parametrize("field, value", [
    ("accessible", "yes"),
    ("supports_completion", "yes"),
    ("relevant_criteria", [9]),
    ("evidence_type", "INVALID"),
])
def test_normalized_evidence_material_fields_are_validated(field, value):
    item = {
        "url": "https://example.com", "accessible": True, "relevant_criteria": [0],
        "supports_completion": True, "evidence_type": "DOCUMENTATION", "finding": "found",
    }
    item[field] = value
    with pytest.raises(Exception):
        m._normalize_item("https://example.com", item, 1)


def test_inaccessible_evidence_cannot_support_completion_or_be_referenced():
    item = {
        "url": "https://example.com", "accessible": False, "relevant_criteria": [],
        "supports_completion": True, "evidence_type": "INACCESSIBLE", "finding": "unavailable",
    }
    with pytest.raises(Exception, match="Inaccessible"):
        m._normalize_item("https://example.com", item, 1)
    inaccessible = [{**item, "supports_completion": False}]
    with pytest.raises(Exception, match="inaccessible evidence"):
        m._normalize_criterion(0, {"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": [0]}, inaccessible)


def test_malformed_criterion_result_is_rejected():
    with pytest.raises(Exception, match="invalid status"):
        m._normalize_criterion(0, {"criterion_index": 0, "status": "BAD", "evidence_refs": []}, [])
    with pytest.raises(Exception, match="invalid evidence_refs"):
        m._normalize_criterion(0, {"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": [2]}, [])


def test_criterion_indexes_and_references_are_exact():
    evidence = [{
        "url": "https://example.com", "accessible": True, "relevant_criteria": [0],
        "supports_completion": True, "evidence_type": "TEST", "finding": "found",
    }]
    assert m._normalize_criterion(0, {
        "criterion_index": 0, "status": m.SATISFIED, "evidence_refs": [0]
    }, evidence)["criterion_index"] == 0
    with pytest.raises(Exception, match="invalid criterion_index"):
        m._normalize_criterion(1, {"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": [0]}, evidence)
    with pytest.raises(Exception, match="require evidence"):
        m._normalize_criterion(0, {"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": []}, evidence)


def test_indexes_are_canonicalized_to_sorted_unique_values():
    item = {
        "accessible": True,
        "relevant_criteria": [2, 0, 2, 1, 0],
        "supports_completion": True,
        "evidence_type": "CODE",
        "finding": "  implementation found  ",
    }
    normalized = m._normalize_item("https://example.com", item, 3)

    assert normalized["relevant_criteria"] == [0, 1, 2]
    assert normalized["finding"] == "implementation found"


def test_boolean_indexes_are_rejected():
    item = {
        "accessible": True,
        "relevant_criteria": [True],
        "supports_completion": True,
        "evidence_type": "CODE",
        "finding": "found",
    }
    with pytest.raises(Exception, match="invalid indexes"):
        m._normalize_item("https://example.com", item, 2)

    evidence = [{
        "url": "https://example.com",
        "accessible": True,
        "relevant_criteria": [0],
        "supports_completion": True,
        "evidence_type": "CODE",
        "finding": "found",
    }]
    with pytest.raises(Exception, match="invalid evidence_refs"):
        m._normalize_criterion(
            0,
            {"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": [True]},
            evidence,
        )

    with pytest.raises(Exception, match="invalid criterion_index"):
        m._normalize_criterion(
            0,
            {"criterion_index": False, "status": m.SATISFIED, "evidence_refs": [0]},
            evidence,
        )


def test_inaccessible_evidence_type_invariants_are_enforced():
    inaccessible_wrong_type = {
        "accessible": False,
        "relevant_criteria": [],
        "supports_completion": False,
        "evidence_type": "OTHER",
        "finding": "unavailable",
    }
    with pytest.raises(Exception, match="must use INACCESSIBLE"):
        m._normalize_item("https://example.com", inaccessible_wrong_type, 1)

    accessible_wrong_type = {
        "accessible": True,
        "relevant_criteria": [0],
        "supports_completion": False,
        "evidence_type": "INACCESSIBLE",
        "finding": "available",
    }
    with pytest.raises(Exception, match="cannot use INACCESSIBLE"):
        m._normalize_item("https://example.com", accessible_wrong_type, 1)


def test_criterion_evidence_refs_are_canonicalized():
    evidence = [
        {
            "url": "https://example.com/0",
            "accessible": True,
            "relevant_criteria": [0],
            "supports_completion": True,
            "evidence_type": "CODE",
            "finding": "one",
        },
        {
            "url": "https://example.com/1",
            "accessible": True,
            "relevant_criteria": [0],
            "supports_completion": True,
            "evidence_type": "TEST",
            "finding": "two",
        },
    ]

    result = m._normalize_criterion(
        0,
        {
            "criterion_index": 0,
            "status": m.SATISFIED,
            "evidence_refs": [1, 0, 1],
        },
        evidence,
    )

    assert result["evidence_refs"] == [0, 1]


def test_prompts_define_zero_based_indexes_and_allowed_values():
    source = SOURCE.read_text()

    assert "Criteria use ZERO-BASED indexes" in source
    assert "unique ZERO-BASED integer criterion indexes" in source
    assert "DOCUMENTATION, CODE, TEST, DEPLOYMENT, DESIGN, OTHER, INACCESSIBLE" in source
    assert "Normalized evidence uses ZERO-BASED evidence indexes" in source
    assert "unique ZERO-BASED integer evidence indexes" in source


def test_evaluation_structure_binds_counts_statuses_verdict_and_all_nonprose_material():
    snapshot = {"acceptance_criteria": ["criterion"], "evidence_urls": ["https://example.com"]}
    evidence = [{
        "url": "https://example.com", "accessible": True, "relevant_criteria": [0],
        "supports_completion": True, "evidence_type": "DOCUMENTATION", "finding": "one",
    }]
    result = {
        "verdict": m.COMPLETED, "satisfied_criteria_count": 1, "total_criteria_count": 1,
        "accessible_evidence_count": 1, "total_evidence_count": 1,
        "criterion_statuses": [m.SATISFIED], "reason": "leader prose",
        "normalized_evidence": evidence,
        "criterion_results": [{"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": [0]}],
    }
    m._validate_evaluation(result, snapshot)
    alternate = {**result, "reason": "validator prose", "normalized_evidence": [{**evidence[0], "finding": "different prose"}]}
    m._validate_evaluation(alternate, snapshot)
    with pytest.raises(Exception, match="Verdict"):
        m._validate_evaluation({**result, "verdict": m.NOT_COMPLETED}, snapshot)


def test_verdict_mapping_is_deterministic_without_numeric_score():
    assert m._deterministic_verdict([m.SATISFIED, m.SATISFIED], 1) == m.COMPLETED
    assert m._deterministic_verdict([m.SATISFIED, m.UNSATISFIED], 1) == m.PARTIALLY_COMPLETED
    assert m._deterministic_verdict([m.UNSATISFIED], 1) == m.NOT_COMPLETED
    assert m._deterministic_verdict([m.UNVERIFIABLE], 0) == m.INSUFFICIENT_EVIDENCE


def test_material_consensus_rejects_verdict_status_and_count_disagreement():
    evidence = {
        "url": "https://example.com/release",
        "accessible": True,
        "relevant_criteria": [0],
        "supports_completion": True,
        "evidence_type": "DEPLOYMENT",
        "finding": "A public release is available.",
    }
    base = {
        "verdict": m.COMPLETED,
        "satisfied_criteria_count": 1,
        "total_criteria_count": 1,
        "accessible_evidence_count": 1,
        "total_evidence_count": 1,
        "criterion_statuses": [m.SATISFIED],
        "reason": "The release satisfies the criterion.",
        "normalized_evidence": [evidence],
        "criterion_results": [{
            "criterion_index": 0,
            "status": m.SATISFIED,
            "evidence_refs": [0],
        }],
    }

    def changed(**changes):
        result = {**base, "normalized_evidence": [dict(evidence)],
                  "criterion_results": [dict(base["criterion_results"][0])]}
        result.update(changes)
        return result

    assert m._material(base) != m._material({**base, "verdict": m.NOT_COMPLETED})
    assert m._material(base) != m._material(changed(satisfied_criteria_count=0))
    assert m._material(base) != m._material(changed(total_criteria_count=2))
    assert m._material(base) != m._material(changed(accessible_evidence_count=0))
    assert m._material(base) != m._material(changed(total_evidence_count=0))
    assert m._material(base) != m._material({**base, "criterion_statuses": [m.UNSATISFIED]})
    assert m._material(base) != m._material(changed(
        normalized_evidence=[{**evidence, "accessible": False}]
    ))
    assert m._material(base) != m._material(changed(
        normalized_evidence=[{**evidence, "relevant_criteria": []}]
    ))
    assert m._material(base) != m._material(changed(
        normalized_evidence=[{**evidence, "supports_completion": False}]
    ))
    assert m._material(base) != m._material(changed(
        normalized_evidence=[{**evidence, "evidence_type": "TEST"}]
    ))
    assert m._material(base) != m._material(changed(
        criterion_results=[{"criterion_index": 0, "status": m.SATISFIED, "evidence_refs": []}]
    ))
    assert m._material(base) == m._material(changed(reason="Different reason prose."))
    assert m._material(base) == m._material(changed(
        normalized_evidence=[{**evidence, "finding": "Different finding prose."}]
    ))


def test_contract_surface_and_lifecycle_invariants():
    tree = ast.parse(SOURCE.read_text())
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert {
        "create_milestone", "submit_evidence", "adjudicate_milestone", "get_milestone",
        "get_adjudication", "milestone_exists", "adjudication_exists",
    } <= methods
    source = SOURCE.read_text()
    assert "status != CREATED" in source
    assert "status != EVIDENCE_SUBMITTED" in source
    assert "already been adjudicated" in source
    assert "challenge_decision" not in source
    assert "score" not in source.lower()


def test_lifecycle_rejects_missing_duplicate_and_resubmitted_operations():
    contract = m.MilestoneJudge()
    # The real GenVM creates these from class annotations; the lightweight unit stub does not.
    class Map(dict):
        def contains(self, key):
            return key in self

    contract.milestones = Map()
    contract.adjudications = Map()
    with pytest.raises(Exception, match="does not exist"):
        contract.submit_evidence("missing", ["https://example.com"])
    with pytest.raises(Exception, match="does not exist"):
        contract.adjudicate_milestone("missing")
    with pytest.raises(Exception, match="does not exist"):
        contract.get_adjudication("missing")
    contract.create_milestone("m1", "Title", "Description", ["Criterion"])
    with pytest.raises(Exception, match="already exists"):
        contract.create_milestone("m1", "Title", "Description", ["Criterion"])
    with pytest.raises(Exception, match="submitted evidence"):
        contract.adjudicate_milestone("m1")
    contract.submit_evidence("m1", ["https://example.com"])
    with pytest.raises(Exception, match="CREATED"):
        contract.submit_evidence("m1", ["https://example.com/other"])


def test_storage_snapshot_precedes_nondeterministic_callbacks():
    source = SOURCE.read_text()
    snapshot_at = source.index("snapshot = {")
    nondet_at = source.index("gl.vm.run_nondet")
    assert snapshot_at < nondet_at
    assert '"acceptance_criteria": list(milestone.acceptance_criteria)' in source
    assert '"evidence_urls": list(milestone.evidence_urls)' in source


def test_contract_source_integrity_guard():
    assert SOURCE.stat().st_size > 0
    assert len(SOURCE.read_text().splitlines()) >= 250
    assert "class MilestoneJudge(gl.Contract):" in SOURCE.read_text()



def test_treemap_membership_uses_python_membership_operator():
    source = Path("contracts/milestone_judge.py").read_text()

    assert ".contains(" not in source
    assert "milestone_id in self.milestones" in source
    assert "milestone_id not in self.milestones" in source
    assert "milestone_id in self.adjudications" in source
    assert "milestone_id not in self.adjudications" in source


def test_storage_descriptors_are_not_manually_initialized():
    source = SOURCE.read_text()
    assert "def __init__(self):\n        pass" in source
    assert "self.milestones = TreeMap()" not in source
    assert "self.adjudications = TreeMap()" not in source
    assert "DynArray[" in source


def test_sender_address_is_converted_to_string_before_storage():
    source = Path("contracts/milestone_judge.py").read_text()

    assert "str(gl.message.sender_address)" in source
    assert "milestone_id, gl.message.sender_address," not in source

def test_normalized_evidence_url_is_deterministic_not_model_supplied():
    source = Path("contracts/milestone_judge.py").read_text()

    for field in (
        "accessible",
        "relevant_criteria",
        "supports_completion",
        "evidence_type",
        "finding",
    ):
        assert f'"{field}"' in source

    assert '"url": url' in source
    assert 'raw["url"]' not in source
