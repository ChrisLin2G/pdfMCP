# PDF MCP Server

**MCP (Model Context Protocol) server for PDF text extraction using OCRmyPDF**

Provides AI assistants with the ability to extract text from PDF files, with optional OCR processing and page range selection.

## Features

- ✅ **OCR Support** - Automatic OCR using OCRmyPDF for scanned documents
- ✅ **FastMCP based** - Same framework as JiraMcp and PolarionMcp
- ✅ **Page Range Selection** - Extract specific pages or page ranges
- ✅ **Flexible Processing** - Can skip OCR for PDFs with existing text
- ✅ **Three tools available:**
  - `health_check` - Test OCRmyPDF installation
  - `extract_text_from_pdf` - Extract text with optional OCR
  - `extract_text_without_ocr` - Extract existing text only

## Installation

### Prerequisites

- Python 3.12+
- OCRmyPDF and its dependencies (Tesseract OCR, Ghostscript)

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ocrmypdf tesseract-ocr tesseract-ocr-eng
```

**For additional languages:**
```bash
# German
sudo apt-get install tesseract-ocr-deu
# French
sudo apt-get install tesseract-ocr-fra
```

### Setup

1. **Create virtual environment:**
   ```bash
   cd /path/to/pdfMcp
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

3. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults are usually fine)
   ```

4. **Test the installation:**
   ```bash
   python3 -c "from mcp_server.tools import mcp; import asyncio; asyncio.run(mcp.run())"
   ```

## Configuration for VS Code

Add to your `.vscode/mcp.json`:

```json
{
  "servers": {
    "pdf": {
      "type": "stdio",
      "command": "bash",
      "args": [
        "-c",
        "cd ${workspaceFolder}/mcp-servers/pdfMcp && source .venv/bin/activate && exec python3 -c 'from mcp_server.tools import mcp; mcp.run()'"
      ],
      "envFile": "${workspaceFolder}/mcp-servers/pdfMcp/.env"
    }
  }
}
```

Or with multiple servers:

```json
{
  "servers": {
    "polarion": {
      ...existing polarion config...
    },
    "jira": {
      ...existing jira config...
    },
    "pdf": {
      "type": "stdio",
      "command": "bash",
      "args": [
        "-c",
        "cd ${workspaceFolder}/mcp-servers/pdfMcp && source .venv/bin/activate && exec python3 -c 'from mcp_server.tools import mcp; mcp.run()'"
      ],
      "envFile": "${workspaceFolder}/mcp-servers/pdfMcp/.env"
    }
  }
}
```

## Usage Examples

### Basic Usage

**Extract all pages with OCR:**
```
Extract text from /path/to/document.pdf
```

**Extract specific pages:**
```
Extract pages 5-10 from /path/to/document.pdf
```

**Extract without OCR (faster for text-based PDFs):**
```
Extract text from /path/to/document.pdf without OCR
```

### Tool Calls

#### health_check
```python
# Verify OCRmyPDF installation
health_check()
# Returns: "✅ PDF MCP server is healthy. OCRmyPDF version: 16.0.0"
```

#### extract_text_from_pdf
```python
# Extract all pages with OCR
extract_text_from_pdf(
    pdf_path="/home/user/document.pdf"
)

# Extract pages 1-5 with OCR
extract_text_from_pdf(
    pdf_path="/home/user/document.pdf",
    start_page=1,
    end_page=5
)

# Extract page 10 only
extract_text_from_pdf(
    pdf_path="/home/user/document.pdf",
    start_page=10,
    end_page=10
)

# Extract without OCR (for text-based PDFs)
extract_text_from_pdf(
    pdf_path="/home/user/document.pdf",
    run_ocr=False
)
```

#### extract_text_without_ocr
```python
# Convenience tool for text-based PDFs
extract_text_without_ocr(
    pdf_path="/home/user/document.pdf"
)

# With page range
extract_text_without_ocr(
    pdf_path="/home/user/document.pdf",
    start_page=5,
    end_page=15
)
```

## How It Works

1. **OCR Processing** (if enabled):
   - Takes input PDF file
   - Runs OCRmyPDF to create searchable PDF
   - Stores temporary OCR'd PDF in configured temp directory

2. **Text Extraction**:
   - Uses pypdf to extract text from PDF
   - Processes specified page range (or all pages)
   - Returns formatted text with page numbers

3. **Cleanup**:
   - Automatically removes temporary OCR files
   - Only keeps original PDF unchanged

## Configuration Options

Environment variables (in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PDF_TEMP_DIR` | `/tmp/pdf_mcp` | Directory for temporary OCR files |
| `OCRMYPDF_LANGUAGE` | `eng` | OCR language code (eng, deu, fra, etc.) |
| `OCRMYPDF_SKIP_TEXT` | `false` | Skip OCR if PDF already has text |

## Troubleshooting

### OCRmyPDF not found
```bash
# Install OCRmyPDF and dependencies
pip install ocrmypdf
# Install system dependencies (see Prerequisites)
```

### OCR timeout
- Large PDFs may take several minutes to process
- Default timeout is 5 minutes
- Consider using `run_ocr=False` for text-based PDFs

### No text extracted
- PDF may be a scanned image - ensure OCR is enabled (`run_ocr=True`)
- Check OCR language setting matches PDF language
- Verify PDF is not corrupted or password-protected

### Memory issues with large PDFs
- Process specific page ranges instead of entire document
- Increase system memory available to Python process

## Performance Tips

1. **Use `run_ocr=False` for text-based PDFs** - Much faster
2. **Extract specific page ranges** - Reduces processing time
3. **Configure `OCRMYPDF_SKIP_TEXT=true`** - Skips OCR for pages with existing text
4. **Use appropriate OCR language** - Improves accuracy and speed

## Development

### Running tests
```bash
source .venv/bin/activate
pytest
```

### Debug mode
```bash
# Set in .env
LOG_LEVEL=DEBUG
```
