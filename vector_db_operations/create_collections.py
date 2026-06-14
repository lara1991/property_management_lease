import os
import re
from pathlib import Path

from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from markitdown import MarkItDown

load_dotenv()

DEFAULT_PERSIST_DIR = "./chroma_db"

_md_converter = MarkItDown()


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
# Text extraction
# ---------------------------------------------------------------------------

def _extract_pdf(file_path: str) -> str:
    """Extract plain text from a PDF using MarkItDown."""
    return _md_converter.convert(file_path).text_content


def _extract_md(file_path: str) -> str:
    """Read a Markdown file as-is (plain text, no conversion needed)."""
    return Path(file_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Chunking strategies
# ---------------------------------------------------------------------------

def _chunk_md(text: str, doc_name: str) -> list[dict]:
    """
    Split a Markdown document into one chunk per ``##`` section.

    The document title (first ``#`` heading) is prepended to every chunk so
    that each chunk carries full context when retrieved in isolation.
    """
    # Capture the h1 title to use as a prefix in every chunk
    title_match = re.match(r"^#\s+(.+)", text, re.MULTILINE)
    title_prefix = f"# {title_match.group(1).strip()}\n\n" if title_match else ""

    # Split on lines that start a new ## (or deeper) section
    raw_sections = re.split(r"(?=\n## )", text)

    chunks = []
    for i, section in enumerate(raw_sections):
        section = section.strip()
        if not section or section.startswith("# "):
            # Skip the h1 preamble — it will be included via title_prefix
            continue
        first_line = section.split("\n", 1)[0].strip()
        heading = re.sub(r"^#+\s*", "", first_line)
        chunks.append({
            "text": title_prefix + section,
            "chunk_index": i,
            "doc_name": doc_name,
            "heading": heading,
        })
    return chunks


def _chunk_text(text: str, doc_name: str, max_chars: int = 600, overlap_paras: int = 1) -> list[dict]:
    """
    Split plain text (e.g. from a PDF) into chunks of at most ``max_chars``
    characters, grouping by paragraph.  The last ``overlap_paras`` paragraphs
    of each chunk are carried over to the next to preserve context at
    boundaries.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunks.append({
                "text": "\n\n".join(current),
                "chunk_index": len(chunks),
                "doc_name": doc_name,
                "heading": "",
            })
            current = current[-overlap_paras:] + [para]
            current_len = sum(len(p) for p in current)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append({
            "text": "\n\n".join(current),
            "chunk_index": len(chunks),
            "doc_name": doc_name,
            "heading": "",
        })
    return chunks


# ---------------------------------------------------------------------------
# Load + chunk from a path (file or directory)
# ---------------------------------------------------------------------------

def load_and_chunk_from_path(
    path: str,
    max_chars_pdf: int = 3000,
) -> dict[str, list[str]]:
    """
    Walk ``path`` (a single file or a directory), extract text from all
    ``.md`` and ``.pdf`` files found, chunk each document, and return a
    mapping of ``doc_name -> list[chunk_text]`` ready to pass directly to
    :func:`add_documents`.

    Strategy:
    - ``.md``  → split on ``##`` section headings (semantic chunks)
    - ``.pdf`` → split on paragraphs with a ``max_chars_pdf`` character limit

    Args:
        path:          Path to a file or directory to scan recursively.
        max_chars_pdf: Max characters per chunk for PDF documents.

    Returns:
        Dict mapping each document filename to its list of text chunks.
    """
    p = Path(path)
    if p.is_file():
        files = [p]
    else:
        files = sorted(p.glob("**/*.pdf")) + sorted(p.glob("**/*.md"))

    result: dict[str, list[str]] = {}
    for file in files:
        suffix = file.suffix.lower()
        doc_name = file.name
        try:
            if suffix == ".pdf":
                text = _extract_pdf(str(file))
                chunks = _chunk_text(text, doc_name, max_chars=max_chars_pdf)
            elif suffix == ".md":
                text = _extract_md(str(file))
                chunks = _chunk_md(text, doc_name)
            else:
                continue
        except Exception as e:
            print(f"  [WARN] Could not process '{file.name}': {e}")
            continue

        result[doc_name] = [c["text"] for c in chunks]
        print(f"  Loaded '{doc_name}': {len(result[doc_name])} chunk(s)")

    return result


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
    DB_PATH = os.getenv("LOCAL_VDB_PATH", "./local_vdb")
    KB_PATH = os.getenv("KNOWLEDGE_BASE_DOCS_DIR", "./knowledge_base_docs")

    # ── 1. Get or create the collection ────────────────────────────────────
    client = _get_client(DB_PATH)
    embedding_fn = _get_embedding_function()
    col = client.get_or_create_collection(
        name=COLLECTION, embedding_function=embedding_fn
    )
    print(f"Collection '{COLLECTION}' ready — existing chunk count: {col.count()}")

    # ── 2. Load, chunk and ingest all knowledge-base documents ─────────────
    print(f"\nLoading documents from: {KB_PATH}")
    doc_chunks = load_and_chunk_from_path(KB_PATH)

    for doc_name, chunks in doc_chunks.items():
        # Replace any existing version of this doc so re-runs are idempotent
        try:
            delete_document(COLLECTION, doc_name=doc_name, persist_directory=DB_PATH)
        except Exception:
            pass  # doc didn't exist yet
        add_documents(COLLECTION, doc_name=doc_name, chunks=chunks, persist_directory=DB_PATH)

    print(f"\nTotal chunks in collection after ingestion: {col.count()}")

    # ── 3. Sanity-check: run a few test queries directly via ChromaDB ───────
    test_queries = [
        "pet weight limit Apt 402",
        "income to rent ratio requirement townhouse",
        "credit score threshold for approval",
    ]
    print("\n── Sanity queries ──────────────────────────────────────────────")
    for query in test_queries:
        results = col.query(
            query_texts=[query],
            n_results=1,
            include=["documents", "metadatas", "distances"],
        )
        doc = results["documents"][0][0]
        meta = results["metadatas"][0][0]
        dist = results["distances"][0][0]
        preview = doc[:120].replace("\n", " ")
        print(f"\nQuery : {query!r}")
        print(f"  doc : {meta.get('doc_name')}  chunk {meta.get('chunk_index')}  dist={dist:.4f}")
        print(f"  text: {preview}...")

