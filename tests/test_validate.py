"""Schema and reference validation (SRS MOD-7)."""
import pytest

import validate as V

S = {"type": "object", "properties": {
    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    "score": {"type": "integer", "minimum": 1, "maximum": 5},
    "claims": {"type": "array", "items": {"type": "object", "properties": {
        "text": {"type": "string"}, "source_ids": {"type": "array", "items": {"type": "string"}}, "assumption": {"type": "boolean"}},
        "required": ["text", "source_ids", "assumption"]}}},
    "required": ["confidence", "score", "claims"]}
OK = {"confidence": "low", "score": 3, "claims": [{"text": "a", "source_ids": ["S001"], "assumption": False}]}


def test_valid_passes():
    assert V.validate_output(OK, S, ["S001"])


@pytest.mark.parametrize("bad", [
    {**OK, "score": "3"},                       # wrong type
    {**OK, "confidence": "sure"},               # enum
    {**OK, "score": 9},                         # range
    {k: v for k, v in OK.items() if k != "score"},  # missing field
    {**OK, "claims": [{"text": "a", "source_ids": ["S999"], "assumption": False}]},  # unknown source
    {**OK, "claims": [{"text": "a", "source_ids": [], "assumption": False}]},        # unsourced, not ASSUMPTION
])
def test_invalid_rejected(bad):
    with pytest.raises(V.BadModelOutput):
        V.validate_output(bad, S, ["S001"])


def test_assumption_without_source_passes():
    V.validate_output({**OK, "claims": [{"text": "a", "source_ids": [], "assumption": True}]}, S, ["S001"])


def test_url_field_rejected():
    s = {"type": "object", "properties": {"url": {"type": "string"}}}
    with pytest.raises(V.BadModelOutput):
        V.validate_output({"url": "https://x"}, s, [])
