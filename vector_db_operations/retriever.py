import os
from dataclasses import dataclass

from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

load_dotenv(".env")

DEFAULT_PERSIST_DIR = os.getenv("LOCAL_VDB_PATH")
COLLECTION_NAME = os.getenv("COLLECTION")
N_RESULTS = int(os.getenv("N_RESULTS", 3))  


@dataclass
class RetrievalResult:
    ids: list[str]
    documents: list[str]
    metadatas: list[dict]
    distances: list[float]


def _get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    model_name = os.getenv("EMBEDDING_MODEL")
    if not model_name:
        raise ValueError(
            "EMBEDDING_MODEL is not set. Add it to your .env file."
        )
    return SentenceTransformerEmbeddingFunction(model_name=model_name)

client = chromadb.PersistentClient(path=DEFAULT_PERSIST_DIR)
embedding_fn = _get_embedding_function()
collection = client.get_collection(
    name=COLLECTION_NAME, embedding_function=embedding_fn
)

def retrieve_from_knowledge_base(
    query: str,
) -> RetrievalResult:
    """
    Retrieve the most relevant text chunks and their embeddings for a query.

    The query is embedded with the same model used at indexing time (loaded
    from the ``EMBEDDING_MODEL`` environment variable).  ChromaDB ranks
    results by cosine distance; lower distance means higher relevance.

    Args:
        query: Natural-language query string.

    Returns:
        A :class:`RetrievalResult` with parallel lists of ids, documents,
        metadatas, and distances for each returned chunk.
    """

    results = collection.query(
        query_texts=[query],
        n_results=N_RESULTS,
        include=["documents", "metadatas", "distances"],
    )

    # collection.query returns lists-of-lists (one per query); unwrap the single query
    return RetrievalResult(
        ids=results["ids"][0],
        documents=results["documents"][0],
        metadatas=results["metadatas"][0],
        distances=results["distances"][0],
    )


if __name__ == "__main__":
    COLLECTION = "lease_docs"
    QUERY = "What are the rules about late payment fees?"

    result = retrieve_from_knowledge_base(QUERY)

    print(f"Top {len(result.documents)} results for: '{QUERY}'\n")
    for rank, (doc, meta, dist) in enumerate(
        zip(result.documents, result.metadatas, result.distances), start=1
    ):
        print(f"[{rank}] distance={dist:.4f}  doc_name={meta.get('doc_name')}  chunk={meta.get('chunk_index')}")
        print(f"    {doc}\n")
