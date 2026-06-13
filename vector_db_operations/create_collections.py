import os

from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

load_dotenv()

DEFAULT_PERSIST_DIR = "./chroma_db"


def _get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    model_name = os.getenv("EMBEDDING_MODEL")
    if not model_name:
        raise ValueError(
            "EMBEDDING_MODEL is not set. Add it to your .env file."
        )
    return SentenceTransformerEmbeddingFunction(model_name=model_name)


def _get_client(persist_directory: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=persist_directory)


# ---------------------------------------------------------------------------
# Collection-level operations
# ---------------------------------------------------------------------------

def create_collection(
    collection_name: str,
    persist_directory: str = DEFAULT_PERSIST_DIR,
) -> chromadb.Collection:
    """Create a new collection. Raises an error if it already exists."""
    client = _get_client(persist_directory)
    embedding_fn = _get_embedding_function()
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
    )
    print(f"Collection '{collection_name}' created.")
    return collection


def delete_collection(
    collection_name: str,
    persist_directory: str = DEFAULT_PERSIST_DIR,
) -> None:
    """Permanently delete an entire collection and all its data."""
    client = _get_client(persist_directory)
    client.delete_collection(name=collection_name)
    print(f"Collection '{collection_name}' deleted.")


# ---------------------------------------------------------------------------
# Document-level operations (each document is stored as one or more chunks)
# ---------------------------------------------------------------------------

def add_documents(
    collection_name: str,
    doc_name: str,
    chunks: list[str],
    persist_directory: str = DEFAULT_PERSIST_DIR,
) -> None:
    """
    Add a new document's text chunks to an existing collection.

    Each chunk is stored individually with an auto-generated ID of the form
    ``{doc_name}_chunk_{i}`` and a metadata field ``doc_name`` to allow later
    retrieval or deletion by document.

    Args:
        collection_name: Name of the target collection.
        doc_name:        Unique document name (use the filename, e.g. "lease_001.pdf").
        chunks:          List of text chunks to embed and store.
        persist_directory: Path where ChromaDB persists data.
    """
    client = _get_client(persist_directory)
    embedding_fn = _get_embedding_function()
    collection = client.get_collection(
        name=collection_name, embedding_function=embedding_fn
    )
    ids = [f"{doc_name}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_name": doc_name, "chunk_index": i} for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    print(f"Added {len(chunks)} chunk(s) for document '{doc_name}' to '{collection_name}'.")


def update_document(
    collection_name: str,
    doc_name: str,
    new_chunks: list[str],
    persist_directory: str = DEFAULT_PERSIST_DIR,
) -> None:
    """
    Replace all chunks for an existing document with a new set of chunks.

    This deletes all current embeddings/texts for ``doc_name`` and re-inserts
    them, which correctly handles chunk-count changes between versions.

    Args:
        collection_name: Name of the target collection.
        doc_name:        Document name (filename) whose chunks will be replaced.
        new_chunks:      New list of text chunks to store.
        persist_directory: Path where ChromaDB persists data.
    """
    delete_document(collection_name, doc_name, persist_directory)
    add_documents(collection_name, doc_name, new_chunks, persist_directory)
    print(f"Document '{doc_name}' updated in '{collection_name}'.")


def delete_document(
    collection_name: str,
    doc_name: str,
    persist_directory: str = DEFAULT_PERSIST_DIR,
) -> None:
    """
    Delete all chunks (embeddings and texts) for a single document.

    Args:
        collection_name: Name of the target collection.
        doc_name:        Document name (filename) to remove entirely.
        persist_directory: Path where ChromaDB persists data.
    """
    client = _get_client(persist_directory)
    embedding_fn = _get_embedding_function()
    collection = client.get_collection(
        name=collection_name, embedding_function=embedding_fn
    )
    collection.delete(where={"doc_name": doc_name})
    print(f"Deleted all chunks for document '{doc_name}' from '{collection_name}'.")


# ---------------------------------------------------------------------------
# Usage examples
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    COLLECTION = os.getenv("COLLECTION", "lease_docs")
    DB_PATH = os.getenv("LOCAL_VDB_PATH", "./chroma_db")

    # --- 1. Create a collection -------------------------------------------
    create_collection(COLLECTION, DB_PATH)

    # --- 2. Add a new document (3 chunks) ---------------------------------
    sample_chunks = [
        "The tenant agrees to pay rent on the first of each month.",
        "Late payments will incur a fee of 5% of the monthly rent.",
        "The lease term begins on 2024-01-01 and ends on 2024-12-31.",
    ]
    add_documents(COLLECTION, doc_name="lease_001.pdf", chunks=sample_chunks, persist_directory=DB_PATH)

    # --- 3. Add another document ------------------------------------------
    other_chunks = [
        "Pets are allowed with a refundable deposit of $500.",
        "No structural modifications may be made without written consent.",
    ]
    add_documents(COLLECTION, doc_name="lease_002.pdf", chunks=other_chunks, persist_directory=DB_PATH)

    # --- 4. Update an existing document (replace its chunks) --------------
    updated_chunks = [
        "The tenant agrees to pay rent on the first of each month.",
        "Late payments will incur a fee of 3% of the monthly rent.",  # updated rate
        "The lease term begins on 2024-01-01 and ends on 2025-12-31.",  # extended
        "Rent increases are capped at 2% per year.",  # new chunk
    ]
    update_document(COLLECTION, doc_name="lease_001.pdf", new_chunks=updated_chunks, persist_directory=DB_PATH)

    # --- 5. Delete a single document (all its chunks) --------------------
    delete_document(COLLECTION, doc_name="lease_002.pdf", persist_directory=DB_PATH)

    # --- 6. Delete the entire collection ---------------------------------
    delete_collection(COLLECTION, DB_PATH)
