"""Unit tests for Discovery stable ID generation."""

from __future__ import annotations

from oryxenai.agents.discovery.ids import (
    answer_snapshot_hash,
    brief_hash,
    conflict_id,
    fact_id,
    operation_idempotency_key,
    question_id,
    source_snapshot_id,
)


class TestFactId:
    def test_stable_id_same_input(self):
        id1 = fact_id("skill", "skill", "Python", ["resume_text"])
        id2 = fact_id("skill", "skill", "Python", ["resume_text"])
        assert id1 == id2

    def test_different_category_different_id(self):
        id1 = fact_id("skill", "skill", "Python", ["resume_text"])
        id2 = fact_id("identity", "skill", "Python", ["resume_text"])
        assert id1 != id2

    def test_different_value_different_id(self):
        id1 = fact_id("skill", "skill", "Python", ["resume_text"])
        id2 = fact_id("skill", "skill", "Java", ["resume_text"])
        assert id1 != id2

    def test_id_format(self):
        fid = fact_id("skill", "skill", "Python", ["resume_text"])
        assert fid.startswith("fact-")
        assert len(fid) > 5

    def test_normalizes_value_for_id(self):
        id1 = fact_id("skill", "skill", "Python", ["resume_text"])
        id2 = fact_id("skill", "skill", "python", ["resume_text"])
        assert id1 == id2


class TestConflictId:
    def test_stable_id(self):
        id1 = conflict_id("end_date", ["2019-01", "2019-02"])
        id2 = conflict_id("end_date", ["2019-01", "2019-02"])
        assert id1 == id2

    def test_order_independent(self):
        id1 = conflict_id("end_date", ["2020", "2019"])
        id2 = conflict_id("end_date", ["2019", "2020"])
        assert id1 == id2


class TestQuestionId:
    def test_stable_id(self):
        id1 = question_id("audience", ["f1", "f2"])
        id2 = question_id("audience", ["f1", "f2"])
        assert id1 == id2

    def test_version_affects_id(self):
        id1 = question_id("audience", ["f1"], version=1)
        id2 = question_id("audience", ["f1"], version=2)
        assert id1 != id2

    def test_id_format(self):
        qid = question_id("audience", [])
        assert qid.startswith("q-")


class TestOperationIdempotencyKey:
    def test_stable_key(self):
        k1 = operation_idempotency_key("sess-1", "prepare_questions", "hash1")
        k2 = operation_idempotency_key("sess-1", "prepare_questions", "hash1")
        assert k1 == k2

    def test_different_operation(self):
        k1 = operation_idempotency_key("sess-1", "prepare_questions", "hash1")
        k2 = operation_idempotency_key("sess-1", "build_brief", "hash1")
        assert k1 != k2


class TestAnswerSnapshotHash:
    def test_same_answers_same_hash(self):
        h1 = answer_snapshot_hash({"q1": {"mode": "answered", "value": "x"}})
        h2 = answer_snapshot_hash({"q1": {"mode": "answered", "value": "x"}})
        assert h1 == h2

    def test_different_answers_different_hash(self):
        h1 = answer_snapshot_hash({"q1": {"mode": "answered", "value": "x"}})
        h2 = answer_snapshot_hash({"q1": {"mode": "answered", "value": "y"}})
        assert h1 != h2


class TestBriefHash:
    def test_same_brief_same_hash(self):
        from oryxenai.agents.discovery.schemas import DiscoveryBrief

        b1 = DiscoveryBrief(schema_version=2, output_language="en")
        b2 = DiscoveryBrief(schema_version=2, output_language="en")
        assert brief_hash(b1) == brief_hash(b2)

    def test_different_brief_different_hash(self):
        from oryxenai.agents.discovery.schemas import DiscoveryBrief

        b1 = DiscoveryBrief(schema_version=2, output_language="en")
        b2 = DiscoveryBrief(schema_version=2, output_language="de")
        assert brief_hash(b1) != brief_hash(b2)


class TestSourceSnapshotId:
    def test_stable_id(self):
        id1 = source_snapshot_id("sess-1", "hash123")
        id2 = source_snapshot_id("sess-1", "hash123")
        assert id1 == id2
