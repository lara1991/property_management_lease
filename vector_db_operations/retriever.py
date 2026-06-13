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

    # client = chromadb.PersistentClient(path=DEFAULT_PERSIST_DIR)
    # embedding_fn = _get_embedding_function()
    # collection = client.get_collection(
    #     name=COLLECTION_NAME, embedding_function=embedding_fn
    # )
    # results = collection.query(
    #     query_texts=[query],
    #     n_results=N_RESULTS,
    #     include=["documents", "metadatas", "distances"],
    # )

    # --- DUMMY DATA: remove when vector DB is ready ---
    _DUMMY_CHUNKS = [
        {
            "id": "chunk_001",
            "document": (
                "Section 1: Standard Multi-Family Units (Apt 400 - Apt 499). "
                "Target units: Apt 402, Apt 405, Apt 410. "
                "Income-to-Rent Ratio: applicant must demonstrate a verified gross monthly income of at least 3.0x "
                "the stated base rental price. "
                "Pet Policy: domesticated cats and dogs permitted up to a maximum of 25 lbs per animal. "
                "Large breeds or exotic pets require written manual exception forms. "
                "Occupancy Limit: maximum 2 residents per studio/1-bedroom configuration."
            ),
            "metadata": {"doc_name": "building_rules_and_eligibility.md", "chunk_index": 0, "section": "Apt 400-499"},
            "distance": 0.12,
        },
        {
            "id": "chunk_002",
            "document": (
                "Section 2: Residential Townhouse Clusters (Suite A - Suite Z). "
                "Target units: Townhouse Suite B, Townhouse Suite F. "
                "Income-to-Rent Ratio: baseline income requires a 2.5x multiplier relative to base rent. "
                "Pet Policy: medium/large breed animals allowed up to 75 lbs per animal due to private yard access. "
                "Occupancy Limit: maximum 4 residents per layout."
            ),
            "metadata": {"doc_name": "building_rules_and_eligibility.md", "chunk_index": 1, "section": "Townhouse Suite A-Z"},
            "distance": 0.18,
        },
        {
            "id": "chunk_003",
            "document": (
                "Section 3: Premium Studios (Studio 100 - Studio 150). "
                "Target units: Luxury Studio 101, Luxury Studio 102. "
                "Income-to-Rent Ratio: high density urban tiers mandate a 3.5x verified underwriting threshold. "
                "Pet Policy: STRICTLY NO PETS ALLOWED. Any declared animal is an automatic compliance violation. "
                "Co-Signer Rules: guarantors accepted only if personal credit score exceeds 720."
            ),
            "metadata": {"doc_name": "building_rules_and_eligibility.md", "chunk_index": 2, "section": "Premium Studios 100-150"},
            "distance": 0.25,
        },
    ]

    print(f"[TOOL CALLED] retrieve_from_knowledge_base | query: {query!r}")
    lines = []
    for i, c in enumerate(_DUMMY_CHUNKS, start=1):
        lines.append(f"[Result {i} | {c['metadata']['section']}]\n{c['document']}")
    return "\n\n".join(lines)


if __name__ == "__main__":
    QUERY = "What are the rules about late payment fees?"
    result = retrieve_from_knowledge_base(QUERY)
    print(result)
