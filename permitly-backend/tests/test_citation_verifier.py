
from citation_verifier import verify_citations


def test_valid_citations():
    citations = [{"id": 1}, {"id": 2}]
    result = verify_citations("A bond is required [1][2].", citations)

    assert result["verified"] is True
    assert result["used_citations"] == [1, 2]
    assert result["invalid_citations"] == []


def test_fabricated_citation():
    citations = [{"id": 1}, {"id": 2}]
    result = verify_citations("A bond is required [5].", citations)

    assert result["verified"] is False
    assert result["invalid_citations"] == [5]


def test_missing_citations():
    citations = [{"id": 1}, {"id": 2}]
    result = verify_citations("A bond is required.", citations)

    assert result["verified"] is False
    assert result["used_citations"] == []


def test_mixed_valid_and_invalid_citations():
    citations = [{"id": 1}, {"id": 2}]
    result = verify_citations("A bond is required [1][9].", citations)

    assert result["verified"] is False
    assert result["used_citations"] == [1]
    assert result["invalid_citations"] == [9]