
import re


def verify_citations(answer: str, citations: list[dict]) -> dict:
    """Check that an AI answer references valid retrieved citations."""

    valid_ids = {str(citation["id"]) for citation in citations}

    # Find references such as [1], [2], and [3].
    referenced_ids = set(re.findall(r"\[(\d+)\]", answer))

    invalid_ids = sorted(referenced_ids - valid_ids)
    used_ids = sorted(referenced_ids & valid_ids, key=int)

    # A substantive answer must cite at least one retrieved passage.
    verified = bool(used_ids) and not invalid_ids

    return {
        "verified": verified,
        "used_citations": [int(value) for value in used_ids],
        "invalid_citations": [int(value) for value in invalid_ids],
    }