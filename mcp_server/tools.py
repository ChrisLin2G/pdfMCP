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
from pypdf import PdfReader

from mcp_server.settings import settings

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("pdf-mcp")


def _run_ocrmypdf(input_path: Path, output_path: Path) -> tuple[bool, str]:
    """
    Run OCRmyPDF on a PDF file.
    
    Args:
        input_path: Path to input PDF
        output_path: Path to output OCR'd PDF
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        cmd = [
            "ocrmypdf",
            "-l", settings.ocrmypdf_language,
            "--output-type", "pdf",
        ]
        
        if settings.ocrmypdf_skip_text:
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
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to PDF file
        start_page: First page to extract (1-indexed, None = first page)
        end_page: Last page to extract (1-indexed, None = last page)
        
    Returns:
        Tuple of (success: bool, text_or_error: str)
    """
    try:
        reader = PdfReader(str(pdf_path))
        total_pages = len(reader.pages)
        
        # Validate and adjust page numbers (convert to 0-indexed)
        first_page = 0 if start_page is None else max(0, start_page - 1)
        last_page = total_pages if end_page is None else min(total_pages, end_page)
        
        if first_page >= total_pages:
            return False, f"Start page {start_page} exceeds total pages ({total_pages})"
        
        if first_page >= last_page:
            return False, f"Start page must be less than or equal to end page"
        
        # Extract text from specified pages
        text_parts = []
        text_parts.append(f"PDF Text Extraction (Pages {first_page + 1}-{last_page} of {total_pages}):\n")
        text_parts.append("=" * 80 + "\n\n")
        
        for page_num in range(first_page, last_page):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            
            if page_text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n")
                text_parts.append(page_text)
                text_parts.append("\n\n")
            else:
                text_parts.append(f"--- Page {page_num + 1} ---\n")
                text_parts.append("[No text content detected]\n\n")
        
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
    run_ocr: bool = True
) -> str:
    """
    Extract text from a PDF file, optionally running OCR first.
    
    Args:
        pdf_path: Absolute path to the PDF file
        start_page: First page to extract (1-indexed, optional)
        end_page: Last page to extract (1-indexed, optional)
        run_ocr: Whether to run OCRmyPDF first (default: True)
        
    Returns: Extracted text or error message
    
    Examples:
        - Extract all pages with OCR: extract_text_from_pdf("/path/to/file.pdf")
        - Extract pages 1-5: extract_text_from_pdf("/path/to/file.pdf", start_page=1, end_page=5)
        - Extract page 10 only: extract_text_from_pdf("/path/to/file.pdf", start_page=10, end_page=10)
        - Extract without OCR: extract_text_from_pdf("/path/to/file.pdf", run_ocr=False)
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
            
            success, message = _run_ocrmypdf(input_path, ocr_output)
            
            if not success:
                # Check if OCR failed because PDF already has text
                if "already has text" in message or "PriorOcrFoundError" in message:
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
    end_page: Optional[int] = None,
    run_ocr: bool = True
) -> str:
    """
    Extract text from a PDF file, optionally running OCR first.
    
    Args:
        pdf_path: Absolute path to the PDF file
        start_page: First page to extract (1-indexed, optional)
        end_page: Last page to extract (1-indexed, optional)
        run_ocr: Whether to run OCRmyPDF first (default: True)
        
    Returns: Extracted text or error message
    
    Examples:
        - Extract all pages with OCR: extract_text_from_pdf("/path/to/file.pdf")
        - Extract pages 1-5: extract_text_from_pdf("/path/to/file.pdf", start_page=1, end_page=5)
        - Extract page 10 only: extract_text_from_pdf("/path/to/file.pdf", start_page=10, end_page=10)
        - Extract without OCR: extract_text_from_pdf("/path/to/file.pdf", run_ocr=False)
    """
    return await _extract_text_from_pdf_internal(pdf_path, start_page, end_page, run_ocr)


@mcp.tool
async def extract_text_without_ocr(
    pdf_path: str,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None
) -> str:
    """
    Extract text from a PDF file without running OCR (for PDFs that already have text).
    
    This is a convenience tool that calls extract_text_from_pdf with run_ocr=False.
    Use this when you know the PDF already contains searchable text.
    
    Args:
        pdf_path: Absolute path to the PDF file
        start_page: First page to extract (1-indexed, optional)
        end_page: Last page to extract (1-indexed, optional)
        
    Returns: Extracted text or error message
    """
    return await _extract_text_from_pdf_internal(pdf_path, start_page, end_page, run_ocr=False)
