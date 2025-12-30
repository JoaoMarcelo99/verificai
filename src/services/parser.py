import hashlib
import logging
import re
import time
from typing import List

import fitz

from src.core.models import Chunk, RawPage

logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self, file_name: str, file_content: bytes):
        self.file_content = file_content
        self.file_name = file_name

    def extract_rawpages(self) -> List[RawPage]:
        raw_pages = []
        try:
            with fitz.open(stream=self.file_content, filetype="pdf") as document:
                for page_number, page in enumerate(document):
                    content = page.get_text("text")
                    cleaned_content = self._sanitize_text(content)
                    if cleaned_content.strip():
                        raw_pages.append(
                            RawPage(
                                content=cleaned_content,
                                page_number=page_number + 1,
                                filename=self.file_name,
                            )
                        )

                    # Ele está reclamndo porque page.get_text pode ser um dicionário. Se estender os tipos para alem de PDF terá que mudar

                return raw_pages

        except Exception as e:
            raise Exception(f"Erro extraindo texto: {e}")

    def _sanitize_text(self, text: str) -> str:
        # Remove múltiplos espaços em branco e quebras de linha extras
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s.,!?;:()\-áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]", r"", text)
        return text.strip()


class ChunkProcessor:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        if overlap >= chunk_size:
            raise ValueError("O overlap deve ser menor que o tamanho do chunk.")
        self.chunk_size = chunk_size
        self.overlap = overlap
        logger.info(f"ChunkProcessor configurado: Size={chunk_size}, Overlap={overlap}")

    def create_chunks(self, raw_pages: List[RawPage], filename: str) -> List[Chunk]:
        start_time = time.time()
        logger.info(
            f"Iniciando processamento do arquivo: {filename} ({len(raw_pages)} páginas)"
        )
        full_text = ""
        page_map = []
        for raw_page in raw_pages:
            page_map.append((len(full_text), raw_page.page_number))
            full_text += raw_page.content + " "

        content_length = len(full_text)
        start = 0
        step = self.chunk_size - self.overlap
        all_chunks = []

        while start < content_length:
            end = min(start + self.chunk_size, content_length)
            chunk_content = full_text[start:end]

            if chunk_content.strip():
                chunk_id = hashlib.md5(chunk_content.encode()).hexdigest()
                current_pages = []
                for i in range(len(page_map)):
                    page_start, page_num = page_map[i]
                    next_page_start = (
                        page_map[i + 1][0] if i + 1 < len(page_map) else content_length
                    )
                    if start < next_page_start and page_start < end:
                        current_pages.append(page_num)

                chunk = Chunk(
                    id=chunk_id,
                    content=chunk_content.strip(),
                    page_numbers=current_pages,
                    filename=filename,
                )
                all_chunks.append(chunk)

                start += step

            if end >= content_length:
                break

        execution_time = time.time() - start_time
        logger.info(
            f"Processamento concluído: {len(all_chunks)} chunks gerados em {execution_time:.2f}s"
        )
        return all_chunks
