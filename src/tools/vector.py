from qdrant_client import QdrantClient
from src.core.config import settings

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)

    def search(self, collection_name: str, query_vector: list, limit: int = 5):
        """Standardized semantic search."""
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )

    def upsert(self, collection_name: str, points: list):
        """Standardized ingestion."""
        return self.client.upsert(
            collection_name=collection_name,
            points=points
        )
