"""
chunking.py
-----------
Split parsed PDF pages into overlapping chunks and attach metadata.

Pipeline:
    List[Document] -> RecursiveCharacterTextSplitter -> List[Document]
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", ", ", " ", ""])


class DocumentChunker:

    def __init__(self, config: ChunkConfig | None = None):
        self.config = config or ChunkConfig()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk(self, pages: list[Document], doc_id: str, filename: str) -> list[Document]:
        if not pages:
            raise ValueError("No pages to chunk.")

        logger.info("Chunking '%s' (%d pages)...", filename, len(pages))
        all_chunks: list[Document] = []

        for page_doc in pages:
            page_number = page_doc.metadata.get("page", 0) + 1
            page_chunks = self.splitter.split_documents([page_doc])

            for idx, chunk in enumerate(page_chunks):
                chunk.metadata.update({
                    "doc_id":      doc_id,
                    "filename":    filename,
                    "page":        page_number,
                    "chunk_index": idx,
                    "chunk_size":  len(chunk.page_content),
                    "char_start":  idx * (self.config.chunk_size - self.config.chunk_overlap),
                })
                all_chunks.append(chunk)

        logger.info("Generated %d chunks from '%s'.", len(all_chunks), filename)
        return all_chunks
