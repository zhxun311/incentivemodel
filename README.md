# Datadon Incentive Scorer Prototype

This repository hosts a prototype that routes Datadon's incentive scoring spec to the OpenAI Responses API. The scorer is optimized for **receipts, bills, invoices, order histories, and financial documents**, but also handles general text data.

The scorer can process:
- **PDFs** (receipts, invoices, statements)
- **Images** (receipt photos, scanned documents)
- **Documents** (Word, Excel, PowerPoint, etc.)
- **Text/JSON payloads** (preprocessed data)

It converts files to markdown text using [MarkItDown](https://github.com/microsoft/markitdown) and submits them to the LLM with the scoring specification, returning a strict JSON reply with points, band, and feedback.

## Getting Started

1. Create and activate a Python 3.11+ environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Tesseract OCR (for image text extraction):
   ```bash
   # Ubuntu/Debian/WSL
   sudo apt-get update && sudo apt-get install tesseract-ocr

   # macOS
   brew install tesseract

   # Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   ```
4. Configure your OpenAI credentials:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```
   The `.env` file should contain:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

## Usage

### Option 1: Web Interface (Recommended) 🌐

The easiest way to use the scorer is through the **web interface**:

```bash
# Start the Flask web app
python app.py
```

Then open your browser to **http://localhost:5000**

**Features:**
- 📤 **Drag & drop** or click to upload receipt images
- 🎯 **Instant scoring** with real-time feedback
- 📊 **Beautiful UI** showing points, band, reason, and encouragement
- 📱 **Mobile-friendly** responsive design
- 🖼️ **Image-only** - supports JPG, PNG, WEBP, GIF, BMP, TIFF
- 📁 **Batch upload** - Score multiple receipts at once (Ctrl/Cmd + Click to select)
- 💾 **Auto-save** - Images saved to `examples/`, JSON output to `output/`
- 🔄 **Bulk upload bonus** - Higher scores for batches ≥10 images

### Option 2: Command Line Interface

## Scoring Files

The `incentive_scorer.py` module supports multiple input types:

### Score a PDF Receipt
```bash
python incentive_scorer.py receipt.pdf
```

### Score an Image (JPG, PNG, etc.)
```bash
python incentive_scorer.py receipt_photo.jpg
```

### Score Other Documents (Word, Excel, etc.)
```bash
python incentive_scorer.py invoice.docx
python incentive_scorer.py expenses.xlsx
```

### Score a JSON Payload (Legacy Format)
```bash
python incentive_scorer.py examples/sample_payload.json
```

### Output Saving

By default, results are **automatically saved** to the `output/` directory:

```bash
# Saves to output/receipt_scored.json
python incentive_scorer.py receipt.jpg

# Custom output directory
python incentive_scorer.py receipt.jpg -o results

# Print only, don't save file
python incentive_scorer.py receipt.jpg --no-save
```

### Advanced Options
```bash
# Use a different model
python incentive_scorer.py receipt.pdf --model gpt-4o

# Specify batch context for bulk upload bonus
python incentive_scorer.py receipt.pdf --batch-size 25 --batch-position 3

# Custom file ID
python incentive_scorer.py receipt.pdf --file-id "receipt_001"
```

### Output Format

The scorer returns a JSON object with:
- **Score details**: points (0-100), band, reason, encouragement, tip
- **Extracted text**: Full OCR/converted text from the file

```json
{
  "schema_version": "1.4",
  "points": 90,
  "band": "premium",
  "reason": "Itemized receipt with prices, total, date, merchant",
  "encouragement": "Excellent! 🌟",
  "tip": null,
  "extracted_text": "Store Name: ICA nära\nDate: 2025-10-14\n..."
}
```

## Programmatic Usage

### Score a File Directly
```python
from incentive_scorer import IncentiveScorer

scorer = IncentiveScorer(model="gpt-5-nano")

# Score a PDF receipt
result = scorer.score_file(
    file_path="receipt.pdf",
    file_id="receipt_001",
    batch_context={"total_files_in_batch": 25, "file_position": 3}
)
print(result.as_dict())
# Output: {"schema_version": "1.4", "points": 92, "band": "premium", ...}
```

### Score a Text Payload (Legacy)
```python
from incentive_scorer import IncentiveScorer

payload = {
    "file_id": "f1",
    "normalized_text": "Costco receipt: chicken breast $24.99, spinach $4.49, milk $5.99, total $38.47 - paid with Visa ending 1234",
    "batch_context": {"total_files_in_batch": 12, "file_position": 2},
}

scorer = IncentiveScorer(model="gpt-5-nano")
result = scorer.score(payload)
print(result.as_dict())
```

### Convert File to Text Only
```python
from incentive_scorer import convert_file_to_text

# Extract text from any supported file format
text = convert_file_to_text("receipt.pdf")
print(text)  # Markdown-formatted text content
```

## Tests

A lightweight pytest suite validates the prompt construction and data model:

```bash
pytest
```

## Supported File Formats

Via [MarkItDown](https://github.com/microsoft/markitdown), the scorer supports:
- **PDF** documents
- **Images** (JPG, PNG, WEBP, GIF, BMP, TIFF) - **LLM-based extraction with automatic image enhancement**
- **Microsoft Office** (Word, Excel, PowerPoint)
- **Text formats** (CSV, JSON, XML, TXT, Markdown)
- **HTML** files
- **EPUB** documents
- **ZIP** archives (processes contents)
- And more!

### Image Enhancement

For receipt images, the scorer automatically applies preprocessing to improve OCR accuracy:
- **Contrast enhancement** (1.5x) - Makes text stand out
- **Sharpness enhancement** (2x) - Clearer edges
- **Brightness adjustment** (+10%) - Compensates for poor lighting
- **Unsharp mask filter** - Additional clarity

This works for **all languages** (Swedish, Chinese, English, etc.) and significantly improves text extraction quality.

## Model Configuration

The default model is `gpt-5-nano` (optimized for speed and cost). You can override it:

```bash
python incentive_scorer.py receipt.pdf --model gpt-4o
```

Or programmatically:
```python
scorer = IncentiveScorer(model="gpt-4o")
```

## Scoring Optimization

The scoring system is now **optimized for financial documents**:
- **Premium (70-100)**: Itemized receipts, complete invoices, detailed bills
- **Good (50-69)**: Receipts with basic details (amount + merchant + date)
- **Basic (30-49)**: Partial transaction info
- **Minimal (10-29)**: Vague financial references
- **Zero (0-9)**: No useful content

**Bulk upload bonus**: Files uploaded in batches ≥10 receive +5 to +10 point boosts.

## Key Features

- ✅ **Financial Document Optimized** - System prompt tuned for receipts, bills, invoices (Version 1.4)
- ✅ **Multi-language Support** - Works with Swedish, Chinese, English, and all languages
- ✅ **LLM-based OCR** - Uses `gpt-5-nano` for accurate text extraction from images
- ✅ **Automatic Image Enhancement** - Preprocessing for better OCR quality
- ✅ **Auto-save Results** - Outputs saved to `output/` directory by default
- ✅ **Extracted Text Included** - Full OCR text saved alongside scores
- ✅ **Bulk Upload Bonus** - Higher scores for batch uploads (≥10 files)
- ✅ **Multiple Format Support** - PDFs, images, Office documents, and more

## Notes

- Responses are requested in JSON mode to ease downstream parsing.
- Error handling surfaces invalid JSON responses for quick inspection.
- Image conversion uses LLM-based extraction for superior accuracy over traditional OCR.
- The scorer processes WEBP images by converting them to PNG automatically.
