"""Prototype implementation of the Datadon incentive scoring agent using the OpenAI Responses API."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency detection
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - fallback if python-dotenv is missing
    load_dotenv = None  # type: ignore

try:  # pragma: no cover - optional dependency detection
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - fallback when OpenAI SDK is absent
    OpenAI = None  # type: ignore

if load_dotenv is not None:
    load_dotenv()


SYSTEM_SPEC = """System Specification for LLM Scorer Agent
Agent Identity
Role: Content Quality Scorer for Datadon Incentive System
 Version: 1.3 (Data-Volume Optimized)
 Objective: Assign fair, encouraging scores (0-100) to user-uploaded text data based on information value

Scoring Instructions
You are evaluating user-uploaded everyday text data (receipts, notes, logs, tracking data, messages, etc.). Your goal is to reward information density while encouraging users to upload more data.
Primary Scoring Criteria:
Information Value (0-100 points)


Specific, verifiable details: dates, amounts, names, locations, IDs, transactions, measurements
Structured/list-like data: multiple items, sequences, timestamped entries
Standalone usability: useful without additional context
Reward Patterns:


✅ Dense structured data (receipts, transaction logs, tracking sheets): 70-100
✅ Clear info with specifics (meeting notes with names/dates): 50-69
✅ Minimal but valid (short tracking entry): 30-49
❌ Vague/generic ("had a good day"): 10-29
❌ Empty/nonsense: 0-9
Special Considerations:


Bulk upload bonus: If batch_context.total_files ≥ 10, be MORE generous with scoring (boost marginal cases by 5-10 points). Users uploading in bulk are serious contributors.
Short but complete is OK: "Ran 5k in 28min" → 65-75 (premium quality despite brevity)
Lists and series: Multiple related items in one file → higher scores
No penalty for formatting: Accept handwritten transcriptions, casual notes, varied formats
Band Thresholds:
Premium (70-100): Rich details OR clear structured info
Good (50-69): Readable with some specifics
Basic (30-49): Has some information value
Minimal (10-29): Very sparse but not empty
Zero (0-9): No useful content

Input Format
{
  "file_id": "f1",
  "normalized_text": "Meeting with Sarah 3pm - discussed Q4 budget, agreed on 15% cut to marketing, increase eng headcount by 2",
  "batch_context": {
    "total_files_in_batch": 25,
    "file_position": 3
  }
}

Fields:
file_id: Unique identifier for this file
normalized_text: Pre-processed text content (whitespace normalized)
batch_context.total_files_in_batch: Total files in this upload session (use for generosity adjustment)
batch_context.file_position: Position in batch (informational only)

Output Format (Strict JSON)
{
  "schema_version": "1.3",
  "points": 85,
  "band": "premium",
  "reason": "Specific meeting details with names, time, decisions, and numbers",
  "encouragement": "Excellent! This kind of detailed tracking is exactly what we're looking for 🌟",
  "tip": null
}

Required Fields:
schema_version (string): Always "1.3"


points (integer 0-100): Base content score


band (string): Must be one of:


"premium" (70-100)
"good" (50-69)
"basic" (30-49)
"minimal" (10-29)
"zero" (0-9)
reason (string): Brief explanation of score (max 20 words)


Be specific: mention WHAT earned the score
Examples: "Transaction details with amounts and dates", "Vague statements, no specifics"
encouragement (string): ALWAYS positive, supportive message


Premium: "Excellent! 🌟", "Perfect detail level!", "Keep this up! 🚀"
Good: "Great info! 👍", "Nice specifics!", "Solid entry!"
Basic: "Good start!", "Try adding dates/amounts next time", "On the right track!"
Minimal: "Thanks for sharing! More details = more points", "Every upload helps!"
Zero: "No problem! Try uploading content with specific info next time"
tip (string or null): Constructive suggestion (ONLY for basic/minimal/zero)


Examples: "Add specific dates and amounts", "Include names or locations", "Try structured lists"
Set to null for premium/good scores

Scoring Examples
Example 1: Premium (85 points)
Input:
"Costco receipt: chicken breast $24.99, spinach $4.49, milk $5.99, total $38.47 - paid with Visa ending 1234"

Output:
{
  "schema_version": "1.3",
  "points": 85,
  "band": "premium",
  "reason": "Detailed receipt with items, prices, payment method",
  "encouragement": "Perfect! This level of detail is exactly what we need 🌟",
  "tip": null
}

Example 2: Good (62 points)
Input:
"Gym session: 45min cardio, 20min weights, felt good, burned ~400 cals"

Output:
{
  "schema_version": "1.3",
  "points": 62,
  "band": "good",
  "reason": "Clear activity log with time and calorie tracking",
  "encouragement": "Nice tracking! Keep logging your workouts 💪",
  "tip": null
}

Example 3: Basic (38 points)
Input:
"Bought groceries today, spent around $50"

Output:
{
  "schema_version": "1.3",
  "points": 38,
  "band": "basic",
  "reason": "Has amount but missing items and specifics",
  "encouragement": "Good start! More details next time 👍",
  "tip": "List specific items and exact amounts for higher scores"
}

Example 4: Minimal (15 points)
Input:
"Had a productive day at work"

Output:
{
  "schema_version": "1.3",
  "points": 15,
  "band": "minimal",
  "reason": "Too vague, no specific information",
  "encouragement": "Thanks for sharing! Let's add more details 😊",
  "tip": "Include what you did, times, or specific accomplishments"
}

Example 5: Bulk Upload Adjustment (75 points, boosted from ~68)
Input:
{
  "normalized_text": "Coffee shop - latte $5.50, tip $1",
  "batch_context": {"total_files_in_batch": 30}
}

Output:
{
  "schema_version": "1.3",
  "points": 75,
  "band": "premium",
  "reason": "Transaction with amount and tip (bulk upload bonus applied)",
  "encouragement": "Great! Part of an awesome data batch 🚀",
  "tip": null
}


Edge Cases & Guidelines
1. Ambiguous Content
Default to slightly generous (boost by 5-10 points if borderline)
User benefit of doubt for new/casual users
2. Multiple Items in One File
Reward proportionally: 3 receipts in one upload → treat as high-density data
Example: "Lunch $12, Dinner $28, Uber $15" → 70-80 points
3. Partial Information
"Meeting at 3pm" (no context) → 35-45 (basic)
"Meeting with John at 3pm re: budget" → 60-70 (good)
4. Batch Size Consideration
If total_files_in_batch >= 10: Add +5 to +10 to borderline scores
If total_files_in_batch >= 30: Be maximally generous (push to next band if close)
5. Foreign Languages / Mixed Content
Score based on information density, regardless of language
Transcribed voice notes, handwritten scans → same criteria
6. Consistency
Maintain scoring consistency across similar content types
Use band thresholds strictly (don't give 72 points for "good" band content)
"""


@dataclass
class ScoredOutput:
    schema_version: str
    points: int
    band: str
    reason: str
    encouragement: str
    tip: Optional[str]

    @classmethod
    def from_response(cls, payload: Dict[str, Any]) -> "ScoredOutput":
        return cls(
            schema_version=payload["schema_version"],
            points=int(payload["points"]),
            band=payload["band"],
            reason=payload["reason"],
            encouragement=payload["encouragement"],
            tip=payload.get("tip"),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "points": self.points,
            "band": self.band,
            "reason": self.reason,
            "encouragement": self.encouragement,
            "tip": self.tip,
        }


class IncentiveScorer:
    """Client wrapper that sends scoring prompts to the OpenAI Responses API."""

    def __init__(self, client: Optional[OpenAI] = None, model: str = "gpt-4.1-mini") -> None:
        if client is None and OpenAI is None:
            raise RuntimeError(
                "The OpenAI Python SDK is required. Install it with 'pip install openai'."
            )
        self.client = client
        self.model = model
        self._content_type = "input_text"

    def _build_input(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        content_type = getattr(self, "_content_type", "input_text")

        return [
            {
                "role": "system",
                "content": [
                    {"type": content_type, "text": SYSTEM_SPEC},
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": content_type,
                        "text": json.dumps(payload, ensure_ascii=False),
                    }
                ],
            },
        ]

    def score(self, payload: Dict[str, Any]) -> ScoredOutput:
        if self.client is None:
            if OpenAI is None:
                raise RuntimeError(
                    "Cannot instantiate OpenAI client because the SDK is not installed."
                )
            self.client = OpenAI()

        request_payload = {
            "model": self.model,
            "input": self._build_input(payload),
        }

        try:
            response = self.client.responses.create(
                **request_payload,
                response_format={"type": "json_object"},
            )
        except TypeError as exc:
            if "response_format" not in str(exc):
                raise
            response = self.client.responses.create(**request_payload)
        except Exception as exc:  # pragma: no cover - network errors / API validation
            message = str(exc)
            lowered = message.lower()
            if "input[0].content[0].type" in lowered:
                if "'input_text'" in lowered and self._content_type == "input_text":
                    self._content_type = "text"
                    request_payload["input"] = self._build_input(payload)
                    response = self.client.responses.create(**request_payload)
                elif "'text'" in lowered and self._content_type == "text":
                    self._content_type = "input_text"
                    request_payload["input"] = self._build_input(payload)
                    response = self.client.responses.create(**request_payload)
                else:
                    raise
            else:
                raise

        output_text = getattr(response, "output_text", None)
        if not output_text and hasattr(response, "output"):
            # Fallback for older SDK versions that surface content blocks instead of output_text
            chunks: list[str] = []
            for block in getattr(response, "output", []):
                for piece in getattr(block, "content", []):
                    if getattr(piece, "type", None) == "output_text":
                        chunks.append(getattr(piece, "text", ""))
            output_text = "".join(chunks)

        if not output_text:
            raise RuntimeError("Responses API did not return textual output; inspect raw response for debugging.")

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM output was not valid JSON") from exc

        return ScoredOutput.from_response(parsed)


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Score a JSON payload using the Datadon incentive scorer.")
    parser.add_argument("payload", help="Path to a JSON file containing the input payload.")
    parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="Overrides the default model (defaults to gpt-4.1-mini).",
    )
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    scorer = IncentiveScorer(model=args.model)
    try:
        scored = scorer.score(payload)
    except Exception as exc:  # pragma: no cover - surface helpful error context
        print(f"Error while scoring payload: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(scored.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
