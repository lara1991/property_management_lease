import os
from dataclasses import dataclass

from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

load_dotenv()

DEFAULT_PERSIST_DIR = "./chroma_db"


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


def retrieve(
    query: str,
    collection_name: str,
    n_results: int = 5,
    persist_directory: str = DEFAULT_PERSIST_DIR,
) -> RetrievalResult:
    """
    Retrieve the most relevant text chunks and their embeddings for a query.

    The query is embedded with the same model used at indexing time (loaded
    from the ``EMBEDDING_MODEL`` environment variable).  ChromaDB ranks
    results by cosine distance; lower distance means higher relevance.

    Args:
        query:            Natural-language query string.
        collection_name:  Name of the ChromaDB collection to search.
        n_results:        Maximum number of chunks to return.
        persist_directory: Path where ChromaDB persists data.

    Returns:
        A :class:`RetrievalResult` with parallel lists of ids, documents,
        metadatas, and distances for each returned chunk.
    """
    client = chromadb.PersistentClient(path=persist_directory)
    embedding_fn = _get_embedding_function()
    collection = client.get_collection(
        name=collection_name, embedding_function=embedding_fn
    )

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
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
    DB_PATH = "./chroma_db"
    QUERY = "What are the rules about late payment fees?"

    result = retrieve(QUERY, collection_name=COLLECTION, n_results=3, persist_directory=DB_PATH)

    print(f"Top {len(result.documents)} results for: '{QUERY}'\n")
    for rank, (doc, meta, dist) in enumerate(
        zip(result.documents, result.metadatas, result.distances), start=1
    ):
        print(f"[{rank}] distance={dist:.4f}  doc_name={meta.get('doc_name')}  chunk={meta.get('chunk_index')}")
        print(f"    {doc}\n")
