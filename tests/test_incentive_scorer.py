import json

import incentive_scorer


def test_scored_output_round_trip():
    payload = {
        "schema_version": "1.3",
        "points": 75,
        "band": "premium",
        "reason": "Structured detail entry",
        "encouragement": "Excellent!",
        "tip": None,
    }

    scored = incentive_scorer.ScoredOutput.from_response(payload)
    assert scored.as_dict() == payload


def test_build_input_includes_spec_and_payload():
    class Dummy:
        responses = None

    scorer = incentive_scorer.IncentiveScorer(client=Dummy())
    payload = {"normalized_text": "Example", "batch_context": {"total_files_in_batch": 1}}

    request_payload = scorer._build_input(payload)
    assert request_payload[0]["role"] == "system"
    assert request_payload[0]["content"][0]["type"] == "input_text"
    assert incentive_scorer.SYSTEM_SPEC in request_payload[0]["content"][0]["text"]

    user_content = request_payload[1]["content"][0]["text"]
    assert json.loads(user_content) == payload
