"""Prototype implementation of the Datadon incentive scoring agent using the OpenAI Responses API."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency detection
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - fallback if python-dotenv is missing
    load_dotenv = None  # type: ignore

try:  # pragma: no cover - optional dependency detection
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover - fallback when OpenAI SDK is absent
    OpenAI = None  # type: ignore

try:  # pragma: no cover - optional dependency detection
    from markitdown import MarkItDown  # type: ignore
except ImportError:  # pragma: no cover - fallback when markitdown is missing
    MarkItDown = None  # type: ignore

if load_dotenv is not None:
    load_dotenv()


SYSTEM_SPEC = """System Specification for LLM Scorer Agent
Agent Identity
Role: Content Quality Scorer for Datadon Incentive System
 Version: 1.4 (Receipt & Financial Document Optimized)
 Objective: Assign fair, encouraging scores (0-100) to user-uploaded receipts, bills, invoices, order histories, and financial documents based on information value

Scoring Instructions
You are evaluating user-uploaded financial and transactional data (receipts, bills, invoices, order histories, purchase records, bank statements, etc.). Your goal is to reward information density while encouraging users to upload more financial data.

PRIMARY USE CASE: Receipts, Bills, Invoices, and Order Histories
This scorer is optimized for financial documents. Give PREMIUM scores to well-structured financial data.

Primary Scoring Criteria:
Information Value (0-100 points)

FINANCIAL DOCUMENTS (Priority scoring):
✅ Receipts with itemized list + prices + total + date + merchant: 85-100 (PREMIUM)
✅ Bills/invoices with account info + amounts + due dates + service details: 80-95 (PREMIUM)
✅ Order histories with multiple items + prices + order numbers + dates: 75-90 (PREMIUM)
✅ Bank statements with transactions + dates + amounts + balances: 80-95 (PREMIUM)
✅ Simple receipt with total + merchant + date (but no itemization): 60-75 (GOOD)
✅ Partial receipt with amount + merchant (missing details): 40-55 (BASIC)

GENERAL DATA (Standard scoring):
✅ Specific, verifiable details: dates, amounts, names, locations, IDs, transactions, measurements
✅ Structured/list-like data: multiple items, sequences, timestamped entries
✅ Standalone usability: useful without additional context

Reward Patterns:
✅ Itemized receipts/bills (multiple line items with prices): 80-100 (PREMIUM)
✅ Complete financial documents (receipt/invoice/statement): 70-100 (PREMIUM)
✅ Partial financial data (amount + merchant, missing some details): 50-69 (GOOD)
✅ Minimal transaction info (just total or just merchant): 30-49 (BASIC)
❌ Vague/generic ("bought stuff"): 10-29 (MINIMAL)
❌ Empty/nonsense: 0-9 (ZERO)
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
  "schema_version": "1.4",
  "points": 85,
  "band": "premium",
  "reason": "Specific meeting details with names, time, decisions, and numbers",
  "encouragement": "Excellent! This kind of detailed tracking is exactly what we're looking for 🌟",
  "tip": null
}

Required Fields:
schema_version (string): Always "1.4"


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
Example 1: Premium Receipt (92 points)
Input:
"Costco receipt: chicken breast $24.99, spinach $4.49, milk $5.99, total $38.47 - paid with Visa ending 1234 - Date: 2024-03-15"

Output:
{
  "schema_version": "1.4",
  "points": 92,
  "band": "premium",
  "reason": "Itemized receipt with prices, total, payment method, and date",
  "encouragement": "Perfect! This level of detail is exactly what we need 🌟",
  "tip": null
}

Example 2: Good (62 points)
Input:
"Gym session: 45min cardio, 20min weights, felt good, burned ~400 cals"

Output:
{
  "schema_version": "1.4",
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
  "schema_version": "1.4",
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
  "schema_version": "1.4",
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
  "schema_version": "1.4",
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


def enhance_receipt_image(image_path: str) -> str:
    """
    Enhance receipt image quality for better OCR/LLM extraction.

    Applies contrast enhancement, sharpening, and brightness adjustment.
    Returns path to enhanced temporary image file.

    Args:
        image_path: Path to the original image

    Returns:
        Path to enhanced temporary image file
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError:
        # If PIL not available, return original
        return image_path

    try:
        img = Image.open(image_path)

        # Convert to RGB if needed (handles RGBA, grayscale, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 1. Increase contrast (makes text stand out more)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  # 1.5x contrast

        # 2. Increase sharpness (makes edges clearer)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)  # 2x sharpness

        # 3. Adjust brightness slightly (compensate for dark receipts)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)  # 10% brighter

        # 4. Apply unsharp mask for additional clarity
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

        # Save to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_path = temp_file.name
        temp_file.close()
        img.save(temp_path, 'PNG', quality=95)

        return temp_path
    except Exception as e:
        # If enhancement fails, return original
        print(f"Warning: Image enhancement failed: {e}")
        return image_path


def convert_file_to_text(file_path: str, use_llm_for_images: bool = True, enhance_images: bool = True) -> str:
    """
    Convert a file (PDF, image, document) to markdown text using MarkItDown.

    For images (JPG, PNG, WEBP), uses LLM-based extraction with gpt-5-nano for better accuracy.
    For other files (PDF, DOCX, etc.), uses standard MarkItDown conversion.

    Args:
        file_path: Path to the file to convert
        use_llm_for_images: Whether to use LLM for image OCR (default True)

    Returns:
        Extracted text content as markdown

    Raises:
        RuntimeError: If MarkItDown is not installed or conversion fails
    """
    if MarkItDown is None:
        raise RuntimeError(
            "MarkItDown is required for file conversion. Install it with 'pip install markitdown[all]'."
        )

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check if it's an image file
    file_extension = Path(file_path).suffix.lower()
    is_image = file_extension in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']

    try:
        # For images, use LLM-based extraction with a receipt-specific prompt
        if is_image and use_llm_for_images:
            if OpenAI is None:
                raise RuntimeError("OpenAI SDK is required for LLM-based image extraction.")

            actual_file_path = file_path
            temp_files_to_cleanup = []

            # Step 1: Enhance image quality if requested
            if enhance_images:
                enhanced_path = enhance_receipt_image(file_path)
                if enhanced_path != file_path:
                    temp_files_to_cleanup.append(enhanced_path)
                actual_file_path = enhanced_path

            # Step 2: For .webp files, convert to PNG since MarkItDown may not support webp
            if file_extension == '.webp':
                try:
                    from PIL import Image
                    img = Image.open(actual_file_path)
                    # Create a temporary PNG file
                    import tempfile
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    temp_path = temp_file.name
                    temp_file.close()
                    img.save(temp_path, 'PNG')
                    temp_files_to_cleanup.append(temp_path)
                    actual_file_path = temp_path
                except Exception as e:
                    raise RuntimeError(f"Failed to convert WEBP to PNG: {e}")

            client = OpenAI()

            # Custom prompt for extracting structured receipt data
            receipt_prompt = (
                "Extract all text from this receipt/bill/invoice image. "
                "Format the output as structured data with these fields (if present): "
                "Store Name, Location/Address, Date, Items (with individual prices), "
                "Subtotal, Discounts (if any), Tax/VAT, Total Price, Currency, Payment Method. "
                "Preserve all numbers exactly as shown. Output in a clear, readable format."
            )

            md = MarkItDown(llm_client=client, llm_model="gpt-5-nano", llm_prompt=receipt_prompt)
            result = md.convert(actual_file_path)

            # Clean up temporary files
            for temp_file in temp_files_to_cleanup:
                try:
                    os.unlink(temp_file)
                except:
                    pass

            return result.text_content
        else:
            # For PDFs and other documents, use standard MarkItDown
            md = MarkItDown()

        result = md.convert(file_path)
        return result.text_content
    except Exception as exc:
        raise RuntimeError(f"Failed to convert file {file_path}: {exc}") from exc


@dataclass
class ScoredOutput:
    schema_version: str
    points: int
    band: str
    reason: str
    encouragement: str
    tip: Optional[str]
    extracted_text: Optional[str] = None  # OCR/extracted text from images/PDFs

    @classmethod
    def from_response(cls, payload: Dict[str, Any], extracted_text: Optional[str] = None) -> "ScoredOutput":
        return cls(
            schema_version=payload["schema_version"],
            points=int(payload["points"]),
            band=payload["band"],
            reason=payload["reason"],
            encouragement=payload["encouragement"],
            tip=payload.get("tip"),
            extracted_text=extracted_text,
        )

    def as_dict(self, include_extracted_text: bool = True) -> Dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "points": self.points,
            "band": self.band,
            "reason": self.reason,
            "encouragement": self.encouragement,
            "tip": self.tip,
        }
        if include_extracted_text and self.extracted_text is not None:
            result["extracted_text"] = self.extracted_text
        return result


class IncentiveScorer:
    """Client wrapper that sends scoring prompts to the OpenAI Responses API."""

    def __init__(self, client: Optional[OpenAI] = None, model: str = "gpt-5-nano") -> None:
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

    def score_file(
        self,
        file_path: str,
        file_id: Optional[str] = None,
        batch_context: Optional[Dict[str, int]] = None,
    ) -> ScoredOutput:
        """
        Score a file (PDF, image, document) by converting it to text first.

        Args:
            file_path: Path to the file to score
            file_id: Optional file ID (defaults to filename)
            batch_context: Optional batch context info

        Returns:
            ScoredOutput with the scoring results (includes extracted_text field)
        """
        # Convert file to text using MarkItDown
        normalized_text = convert_file_to_text(file_path)

        # Generate default file_id if not provided
        if file_id is None:
            file_id = Path(file_path).name

        # Create payload
        payload = {
            "file_id": file_id,
            "normalized_text": normalized_text,
            "batch_context": batch_context or {"total_files_in_batch": 1, "file_position": 1},
        }

        # Score using the standard method
        result = self.score(payload)

        # Add extracted text to the result
        result.extracted_text = normalized_text

        return result


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Score a file or JSON payload using the Datadon incentive scorer.",
        epilog="Examples:\n"
        "  Score a JSON payload: python incentive_scorer.py examples/sample_payload.json\n"
        "  Score a PDF receipt:  python incentive_scorer.py receipt.pdf\n"
        "  Score an image:       python incentive_scorer.py receipt.jpg\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_file",
        help="Path to a JSON payload file, PDF, image, or other document to score.",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-nano",
        help="Overrides the default model (defaults to gpt-5-nano).",
    )
    parser.add_argument(
        "--file-id",
        help="Optional file ID (defaults to the filename).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Total number of files in batch (for bulk upload bonus).",
    )
    parser.add_argument(
        "--batch-position",
        type=int,
        help="Position of this file in the batch.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="Directory to save output JSON files (defaults to 'output').",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save output to file, only print to stdout.",
    )
    args = parser.parse_args()

    scorer = IncentiveScorer(model=args.model)

    try:
        # Detect if input is a JSON payload or a file to convert
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"Error: File not found: {args.input_file}", file=sys.stderr)
            raise SystemExit(1)

        # Check if it's a JSON file with a payload structure
        is_json_payload = False
        if input_path.suffix.lower() == ".json":
            try:
                with open(args.input_file, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                    # Check if it has the expected payload structure
                    if "normalized_text" in payload and "file_id" in payload:
                        is_json_payload = True
                        scored = scorer.score(payload)
            except (json.JSONDecodeError, KeyError):
                # Not a valid JSON payload, treat as file to convert
                is_json_payload = False

        if not is_json_payload:
            # It's a file to convert (PDF, image, etc.)
            batch_context = None
            if args.batch_size is not None:
                batch_context = {
                    "total_files_in_batch": args.batch_size,
                    "file_position": args.batch_position or 1,
                }
            scored = scorer.score_file(
                file_path=args.input_file,
                file_id=args.file_id,
                batch_context=batch_context,
            )

    except Exception as exc:  # pragma: no cover - surface helpful error context
        print(f"Error while scoring: {exc}", file=sys.stderr)
        raise SystemExit(1)

    # Prepare output
    output_json = json.dumps(scored.as_dict(), ensure_ascii=False, indent=2)

    # Print to stdout
    print(output_json)

    # Save to file unless --no-save is specified
    if not args.no_save:
        try:
            # Create output directory if it doesn't exist
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename based on input filename
            input_filename = Path(args.input_file).stem  # filename without extension
            output_filename = f"{input_filename}_scored.json"
            output_path = output_dir / output_filename

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_json)

            print(f"\n✓ Output saved to: {output_path}", file=sys.stderr)
        except Exception as e:
            print(f"\n⚠ Warning: Failed to save output file: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
