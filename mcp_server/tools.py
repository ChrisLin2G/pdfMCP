"""
PDF MCP Server Tools
Extract text from PDF files using OCRmyPDF
"""

import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from fastmcp import FastMCP
import fitz  # PyMuPDF

from mcp_server.settings import settings

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("pdf-mcp")


def _run_ocrmypdf(input_path: Path, output_path: Path, force_ocr: bool = False) -> tuple[bool, str]:
    """
    Run OCRmyPDF on a PDF file.
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output OCR'd PDF
        force_ocr: Force OCR even if PDF already has text
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        cmd = [
            "ocrmypdf",
            "-l", settings.ocrmypdf_language,
            "--output-type", "pdf",
        ]
        
        if force_ocr:
            cmd.append("--force-ocr")
        elif settings.ocrmypdf_skip_text:
            cmd.append("--skip-text")
        
        cmd.extend([str(input_path), str(output_path)])
        
        logger.info(f"Running OCRmyPDF: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return True, "OCR completed successfully"
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"OCRmyPDF failed: {error_msg}")
            return False, f"OCR failed: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, "OCR timeout after 5 minutes"
    except FileNotFoundError:
        return False, "OCRmyPDF not found. Please install: pip install ocrmypdf"
    except Exception as e:
        logger.error(f"OCRmyPDF error: {e}")
        return False, f"OCR error: {str(e)}"


def _extract_text_from_pdf(pdf_path: Path, start_page: Optional[int] = None, 
                          end_page: Optional[int] = None) -> tuple[bool, str]:
    """
    Extract text from a PDF file with structure detection (headings, paragraphs, tables).
    
    Args:
        pdf_path: Path to PDF file
        start_page: First page to extract (1-indexed, None = first page)
        end_page: Last page to extract (1-indexed, None = last page)
        
    Returns:
        Tuple of (success: bool, text_or_error: str)
    """
    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        
        # Validate and adjust page numbers (convert to 0-indexed)
        first_page = 0 if start_page is None else max(0, start_page - 1)
        last_page = total_pages if end_page is None else min(total_pages, end_page)
        
        if first_page >= total_pages:
            doc.close()
            return False, f"Start page {start_page} exceeds total pages ({total_pages})"
        
        if first_page >= last_page:
            doc.close()
            return False, f"Start page must be less than or equal to end page"
        
        # Extract text with structure from specified pages
        text_parts = []
        text_parts.append(f"PDF Text Extraction with Structure (Pages {first_page + 1}-{last_page} of {total_pages}):\n")
        text_parts.append("=" * 80 + "\n\n")
        
        for page_num in range(first_page, last_page):
            page = doc[page_num]
            text_parts.append(f"--- Page {page_num + 1} ---\n\n")
            
            # Try to find tables using PyMuPDF
            tables = page.find_tables()
            
            # Get text blocks with font information
            blocks = page.get_text("dict")["blocks"]
            
            if not blocks and not tables:
                text_parts.append("[No text content detected]\n\n")
                continue
            
            # If tables are found, extract them
            if tables:
                for table_idx, table in enumerate(tables.tables):
                    text_parts.append(f"**Table {table_idx + 1}:**\n\n")
                    
                    # Extract table data
                    try:
                        table_data = table.extract()
                        
                        if table_data and len(table_data) > 0:
                            # Find column widths
                            col_count = max(len(row) for row in table_data)
                            col_widths = [max(len(str(row[i] if i < len(row) else "")) for row in table_data) for i in range(col_count)]
                            col_widths = [max(w, 3) for w in col_widths]  # Minimum width of 3
                            
                            # Format as markdown table
                            for row_idx, row in enumerate(table_data):
                                # Pad row to column count
                                padded_row = [str(row[i] if i < len(row) else "") for i in range(col_count)]
                                
                                # Format row
                                row_text = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(padded_row)) + " |"
                                text_parts.append(row_text + "\n")
                                
                                # Add separator after first row (header)
                                if row_idx == 0:
                                    separator = "|" + "|".join(["-" * (w + 2) for w in col_widths]) + "|"
                                    text_parts.append(separator + "\n")
                            
                            text_parts.append("\n")
                    except Exception as e:
                        logger.warning(f"Failed to extract table {table_idx + 1}: {e}")
                        text_parts.append(f"[Table extraction failed]\n\n")
            
            # Analyze font sizes to determine heading levels
            font_sizes = []
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_sizes.append(span["size"])
            
            if not font_sizes and not tables:
                text_parts.append("[No text content detected]\n\n")
                continue
            
            # Calculate average font size for body text
            avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
            
            # Process blocks (skip table regions if tables were detected)
            for block in blocks:
                if block["type"] == 0:  # Text block
                    if "lines" not in block:
                        continue
                    
                    # Skip blocks that are within table regions
                    if tables:
                        block_bbox = fitz.Rect(block["bbox"])
                        skip_block = False
                        for table in tables.tables:
                            table_bbox = table.bbox
                            if block_bbox.intersects(table_bbox):
                                skip_block = True
                                break
                        if skip_block:
                            continue
                    
                    block_text = []
                    block_font_size = 0
                    is_bold = False
                    
                    for line in block["lines"]:
                        line_text = []
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                line_text.append(text)
                                # Track font info for first span in block
                                if not block_font_size:
                                    block_font_size = span["size"]
                                    is_bold = "bold" in span["font"].lower()
                        
                        if line_text:
                            block_text.append(" ".join(line_text))
                    
                    if block_text:
                        full_block_text = " ".join(block_text)
                        
                        # Determine if this is a heading based on font size
                        if block_font_size > avg_font_size * 1.3:
                            # Large heading
                            text_parts.append(f"# {full_block_text}\n\n")
                        elif block_font_size > avg_font_size * 1.1 or is_bold:
                            # Medium heading or bold text
                            text_parts.append(f"## {full_block_text}\n\n")
                        else:
                            # Regular paragraph
                            text_parts.append(f"{full_block_text}\n\n")
            
            text_parts.append("\n")
        
        doc.close()
        full_text = "".join(text_parts)
        
        if len(full_text) < 200:  # Very little text found
            return False, "Very little or no text found in PDF. The PDF may need OCR processing."
        
        return True, full_text
        
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return False, f"Text extraction error: {str(e)}"


@mcp.tool
async def health_check() -> str:
    """
    Verify PDF MCP server and OCRmyPDF installation.
    
    Returns: "✅ PDF MCP server is healthy" or "❌ [error message]"
    """
    try:
        # Check OCRmyPDF installation
        result = subprocess.run(
            ["ocrmypdf", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            return f"✅ PDF MCP server is healthy. OCRmyPDF version: {version}"
        else:
            return "❌ OCRmyPDF is installed but not working correctly"
            
    except FileNotFoundError:
        return "❌ OCRmyPDF not found. Install with: pip install ocrmypdf"
    except subprocess.TimeoutExpired:
        return "❌ OCRmyPDF check timeout"
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return f"❌ Health check failed: {str(e)}"


async def _extract_text_from_pdf_internal(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    run_ocr: bool = True,
    force_ocr: bool = False
) -> str:
    """
    Extract text from a PDF file, optionally running OCR first.
    
    Args:
        pdf_path: Absolute path to the PDF file
        start_page: First page to extract (1-indexed, optional)
        end_page: Last page to extract (1-indexed, optional)
        run_ocr: Whether to run OCRmyPDF first (default: True)
        force_ocr: Force OCR even if PDF already has text (default: False)
        
    Returns: Extracted text or error message
    
    Examples:
        - Extract all pages with OCR: extract_text_from_pdf("/path/to/file.pdf")
        - Extract pages 1-5: extract_text_from_pdf("/path/to/file.pdf", start_page=1, end_page=5)
        - Extract page 10 only: extract_text_from_pdf("/path/to/file.pdf", start_page=10, end_page=10)
        - Extract without OCR: extract_text_from_pdf("/path/to/file.pdf", run_ocr=False)
        - Force OCR: extract_text_from_pdf("/path/to/file.pdf", force_ocr=True)
    """
    try:
        input_path = Path(pdf_path)
        
        # Validate input file
        if not input_path.exists():
            return f"❌ File not found: {pdf_path}"
        
        if not input_path.is_file():
            return f"❌ Not a file: {pdf_path}"
        
        if input_path.suffix.lower() != ".pdf":
            return f"❌ Not a PDF file: {pdf_path}"
        
        # Determine which PDF to extract from
        pdf_to_extract = input_path
        
        # Run OCR if requested
        if run_ocr:
            logger.info(f"Running OCR on {input_path}")
            
            # Create temporary output file for OCR
            temp_dir = settings.ensure_temp_dir()
            ocr_output = temp_dir / f"ocr_{input_path.name}"
            
            success, message = _run_ocrmypdf(input_path, ocr_output, force_ocr)
            
            if not success:
                # Check if OCR failed because PDF already has text (only if not forcing OCR)
                if not force_ocr and ("already has text" in message or "PriorOcrFoundError" in message):
                    logger.info(f"PDF already has text, skipping OCR and extracting directly")
                    # Continue with original PDF without OCR
                    pdf_to_extract = input_path
                else:
                    return f"❌ OCR failed: {message}\nTry with run_ocr=False to extract existing text."
            else:
                logger.info(f"OCR completed: {message}")
                pdf_to_extract = ocr_output
        
        # Extract text from PDF
        logger.info(f"Extracting text from {pdf_to_extract}")
        success, result = _extract_text_from_pdf(pdf_to_extract, start_page, end_page)
        
        # Clean up temporary OCR file
        if run_ocr and pdf_to_extract != input_path:
            try:
                pdf_to_extract.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {e}")
        
        if success:
            return result
        else:
            return f"❌ {result}"
            
    except Exception as e:
        logger.error(f"Unexpected error in extract_text_from_pdf: {e}")
        return f"❌ Unexpected error: {str(e)}"


@mcp.tool
async def extract_text_from_pdf(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None
) -> str:
    """
    Extract text from a PDF file without running OCR.
    
    This extracts existing searchable text from PDFs. Use this for PDFs that already
    have text embedded (most modern PDFs, datasheets, manuals). This is fast.
    
    Args:
        pdf_path: Absolute path to the PDF file
        start_page: First page to extract (1-indexed, optional)
        end_page: Last page to extract (1-indexed, optional)
        
    Returns: Extracted text or error message
    
    Examples:
        - Extract all pages: extract_text_from_pdf("/path/to/file.pdf")
        - Extract pages 1-5: extract_text_from_pdf("/path/to/file.pdf", start_page=1, end_page=5)
        - Extract page 10 only: extract_text_from_pdf("/path/to/file.pdf", start_page=10, end_page=10)
    """
    return await _extract_text_from_pdf_internal(pdf_path, start_page, end_page, run_ocr=False)


@mcp.tool
async def extract_text_with_ocr(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    force_ocr: bool = False
) -> str:
    """
    Extract text from a PDF file with OCR processing.
    
    This runs OCRmyPDF first to add/improve text recognition. Use this for:
    - Scanned documents without text
    - PDFs with poor quality or incorrect text
    - When you want to force re-OCR with modern recognition
    
    This is slower than extract_text_from_pdf but handles image-based PDFs.
    
    Args:
        pdf_path: Absolute path to the PDF file
        start_page: First page to extract (1-indexed, optional)
        end_page: Last page to extract (1-indexed, optional)
        force_ocr: Force OCR even if PDF already has text (default: False)
        
    Returns: Extracted text or error message
    
    Examples:
        - OCR and extract: extract_text_with_ocr("/path/to/scanned.pdf")
        - Force re-OCR: extract_text_with_ocr("/path/to/file.pdf", force_ocr=True)
    """
    return await _extract_text_from_pdf_internal(pdf_path, start_page, end_page, run_ocr=True, force_ocr=force_ocr)

