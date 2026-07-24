"""T09 guardrail invariants: only single read-only SELECT ever passes."""
from __future__ import annotations

import pytest

from backend.nl2sql import guardrails
from backend.nl2sql.guardrails import GuardrailError


def test_select_gets_auto_limit():
    out = guardrails.sanitize("SELECT * FROM vw_case_360")
    assert "LIMIT 500" in out.upper()


def test_existing_limit_preserved():
    out = guardrails.sanitize("SELECT * FROM vw_case_360 LIMIT 10")
    assert "LIMIT 10" in out.upper()
    assert "500" not in out


def test_strips_fences_and_semicolons():
    out = guardrails.sanitize("```sql\nSELECT COUNT(*) FROM vw_case_360;\n```")
    assert out.upper().startswith("SELECT")


@pytest.mark.parametrize("bad", [
    "DELETE FROM CaseMaster",
    "UPDATE CaseMaster SET BriefFacts='x'",
    "INSERT INTO AuditLog VALUES (1)",
    "DROP TABLE CaseMaster",
    "CREATE TABLE hack (id INT)",
    "ALTER TABLE CaseMaster ADD COLUMN x INT",
])
def test_rejects_non_select(bad):
    with pytest.raises(GuardrailError):
        guardrails.sanitize(bad)


def test_rejects_multiple_statements():
    with pytest.raises(GuardrailError):
        guardrails.sanitize("SELECT 1 FROM vw_case_360; DROP TABLE CaseMaster")


def test_rejects_unknown_table():
    with pytest.raises(GuardrailError):
        guardrails.sanitize("SELECT * FROM secret_table")


def test_is_read_only_helper():
    assert guardrails.is_read_only("SELECT 1 FROM vw_case_360")
    assert not guardrails.is_read_only("DELETE FROM CaseMaster")
