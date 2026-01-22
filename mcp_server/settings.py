"""
Settings and Configuration for PDF MCP Server
"""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PDF MCP Server settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Logging settings
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # PDF processing settings
    pdf_temp_dir: str = Field(
        default="/tmp/pdf_mcp",
        alias="PDF_TEMP_DIR",
        description="Directory for temporary OCR files"
    )
    
    # OCRmyPDF settings
    ocrmypdf_language: str = Field(
        default="eng",
        alias="OCRMYPDF_LANGUAGE",
        description="Language for OCR (eng, deu, fra, etc.)"
    )
    
    ocrmypdf_skip_text: bool = Field(
        default=False,
        alias="OCRMYPDF_SKIP_TEXT",
        description="Skip OCR if PDF already has text"
    )
    
    def ensure_temp_dir(self) -> Path:
        """Ensure temporary directory exists"""
        temp_path = Path(self.pdf_temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path


# Global settings instance
settings = Settings()
