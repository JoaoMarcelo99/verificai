import logging
import os
from typing import List

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from src.core.models import Chunk

load_dotenv()

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        collection_name: str,
        host: str = os.getenv("QDRANT_HOST", "localhost"),
        port: int = int(os.getenv("QDRANT_PORT", 6333)),
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        vector_size = self.model.get_sentence_embedding_dimension()
        if vector_size is None:
            raise ValueError(
                "Não foi possível determinar a dimensão do vetor de embeddings."
            )
        self.vector_size: int = int(vector_size)

        self._setup_collection()

    def _setup_collection(self):
        if not self.client.collection_exists(self.collection_name):
            try:
                self.create_collection(vector_size=self.vector_size)
            except Exception as e:
                raise Exception(f"Erro ao criar coleção no Qdrant: {e}")

    def create_collection(self, vector_size: int):
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def _generate_vectors(self, chunks: List[Chunk]) -> List[List[float]]:
        return self.model.encode([chunk.content for chunk in chunks]).tolist()

    def add_chunks(self, chunks: List[Chunk]):
        if not chunks:
            logger.info("Nenhum chunk novo para adicionar")
            return
        embeddings = self._generate_vectors(chunks)
        points = [
            PointStruct(
                id=chunk.id,
                vector=embedding,
                payload={
                    "content": chunk.content,
                    "page_numbers": chunk.page_numbers,
                    "filename": chunk.filename,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(self, query: List[float], top_k: int = 5):
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query,
            limit=top_k,
        )
        return results.points

    def list_documents(self) -> List[str]:
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            with_payload=["filename"],
            limit=10000,
        )

        filenames = {
            point.payload["filename"]
            for point in results
            if point.payload and "filename" in point.payload
        }

        return sorted(list(filenames))

    def clear_database(self):
        self.client.delete_collection(self.collection_name)
        self._setup_collection()
        return True

    def delete_file_points(self, filename: str):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="filename", match=models.MatchValue(value=filename)
                    )
                ]
            ),
        )

    def filter_chunks(self, chunks: List[Chunk], filename: str):
        all_ids = [c.id for c in chunks]
        logger.info(
            f"DEBUG: Verificando {len(all_ids)} IDs. Exemplo do primeiro: {all_ids[0] if all_ids else 'N/A'}"
        )
        existing_points = self.client.retrieve(
            collection_name=self.collection_name, ids=all_ids, with_payload=True
        )

        existing_ids = {str(p.id) for p in existing_points}
        logger.info(f"DEBUG: IDs encontrados no Qdrant: {len(existing_ids)}")
        new_chunks = [c for c in chunks if str(c.id) not in existing_ids]

        total = len(chunks)
        novos = len(new_chunks)
        existentes = total - novos

        if len(new_chunks) == 0:
            logger.warning(
                f"O conteúdo do arquivo {filename} já está totalmente contido no banco."
            )
        else:
            logger.info(
                f"{existentes}/{total} chunks encontrados no banco para o arquivo {filename}. Preparando {novos} chunks para subir."
            )
        return new_chunks
