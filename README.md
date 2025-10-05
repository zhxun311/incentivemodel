# Datadon Incentive Scorer Prototype

This repository hosts a simple prototype that routes Datadon's incentive scoring spec to the OpenAI Responses API. The scorer submits user payloads (text data + batch context) to the LLM with the exact system instructions provided in the spec and expects a strict JSON reply describing the awarded points, band, and feedback.

## Getting Started

1. Create and activate a Python 3.11 environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your OpenAI credentials (standard `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`). A `.env` file can be used when combined with `python-dotenv`.

## Scoring a Payload

The `incentive_scorer.py` module exposes a CLI wrapper:

```bash
python incentive_scorer.py examples/sample_payload.json
```

The script prints the LLM's JSON response to stdout. Override the model with `--model` if needed (e.g., `gpt-4.1` for higher quality).

## Programmatic Usage

```python
from incentive_scorer import IncentiveScorer

payload = {
    "file_id": "f1",
    "normalized_text": "Costco receipt: chicken breast $24.99, spinach $4.49, milk $5.99, total $38.47 - paid with Visa ending 1234",
    "batch_context": {"total_files_in_batch": 12, "file_position": 2},
}

scorer = IncentiveScorer(model="gpt-4.1")
result = scorer.score(payload)
print(result.as_dict())
```

## Tests

A lightweight pytest suite validates the prompt construction and data model:

```bash
pytest
```

## Notes

- The system prompt is the original spec, unchanged.
- Responses are requested in JSON mode to ease downstream parsing.
- Error handling surfaces invalid JSON responses for quick inspection.
