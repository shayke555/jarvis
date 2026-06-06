import uuid
from pathlib import Path

import chromadb


class ChromaStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(
            name="jarvis_memory",
            metadata={"hnsw:space": "cosine"},
        )

    def add_memory(
        self, text: str, metadata: dict, memory_id: str | None = None
    ) -> str:
        if memory_id is None:
            memory_id = str(uuid.uuid4())

        self.collection.add(
            ids=[memory_id],
            documents=[text],
            metadatas=[metadata],
        )

        return memory_id

    def search_memories(self, query: str, n_results: int = 5) -> list[dict]:
        current_count = self.collection.count()
        actual_n_results = min(n_results, current_count)

        if actual_n_results == 0:
            return []

        result = self.collection.query(
            query_texts=[query],
            n_results=actual_n_results,
            include=["documents", "metadatas", "distances"],
        )

        memories = []
        for i in range(len(result["ids"][0])):
            memories.append(
                {
                    "id": result["ids"][0][i],
                    "text": result["documents"][0][i],
                    "metadata": result["metadatas"][0][i],
                    "distance": result["distances"][0][i],
                }
            )

        return memories

    def delete_memory(self, memory_id: str) -> None:
        self.collection.delete(ids=[memory_id])

    def count(self) -> int:
        return self.collection.count()
