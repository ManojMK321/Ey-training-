"""
parser.py
---------
Load a PDF from disk and convert it into LangChain Documents.

Pipeline:
    PDF File -> PyPDFLoader -> List[Document]
"""
from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Loads a PDF using LangChain's PyPDFLoader.
    Returns one Document per page with metadata: page, source.
    """

    def parse(self, pdf_path: str | Path) -> list[Document]:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("Loading PDF: %s", pdf_path.name)
        pages = PyPDFLoader(str(pdf_path)).load()
        logger.info("Parsed '%s' into %d page(s).", pdf_path.name, len(pages))
        return pages
