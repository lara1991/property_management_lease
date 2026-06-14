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


_embedding_fn: SentenceTransformerEmbeddingFunction | None = None


def _get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        model_name = os.getenv("EMBEDDING_MODEL")
        if not model_name:
            raise ValueError(
                "EMBEDDING_MODEL is not set. Add it to your .env file."
            )
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=model_name)
    return _embedding_fn

def retrieve_from_knowledge_base(
    query: str,
) -> str:
    """
    Search the Apex Property Management policy knowledge base and return
    relevant policy text for the given query.

    Use targeted queries that mention the specific unit type and policy
    aspect you need, e.g. "income ratio requirement Apt 402" or
    "pet weight limit Townhouse Suite". Call this tool multiple times
    with different queries if you need policy on more than one topic.

    Args:
        query: Natural-language query describing the policy to look up.

    Returns:
        Relevant policy excerpts as plain text, ranked by relevance.
    """

    client = chromadb.PersistentClient(path=DEFAULT_PERSIST_DIR)
    embedding_fn = _get_embedding_function()
    collection = client.get_collection(
        name=COLLECTION_NAME, embedding_function=embedding_fn
    )
    results = collection.query(
        query_texts=[query],
        n_results=N_RESULTS,
        include=["documents", "metadatas", "distances"],
    )

    print(f"[TOOL CALLED] retrieve_from_knowledge_base | query: {query!r}")

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    lines = []
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), start=1):
        label = f"{meta.get('doc_name')}  chunk {meta.get('chunk_index')}  dist={dist:.4f}"
        lines.append(f"[Result {i} | {label}]\n{doc}")
    return "\n\n".join(lines)


if __name__ == "__main__":
    QUERY = "What are the rules about late payment fees?"
    result = retrieve_from_knowledge_base(QUERY)
    print(result)
