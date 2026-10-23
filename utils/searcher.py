# utils/searcher.py
import os, logging
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

def get_oai_client():
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2024-02-01"
    )

def get_search_client():
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name="rag-index",
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"])
    )

def search_documents(question: str, top_k: int = 5) -> list[dict]:
    """
    Embeds the question and does hybrid search
    (vector + keyword) against AI Search.
    Returns top_k most relevant chunks.
    """
    oai    = get_oai_client()
    search = get_search_client()
    deploy = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]

    # 1. Embed the question
    logging.info(f"Embedding question: {question[:60]}...")
    response  = oai.embeddings.create(model=deploy, input=question)
    q_vector  = response.data[0].embedding

    # 2. Build vector query
    vector_query = VectorizedQuery(
        vector=q_vector,
        k_nearest_neighbors=top_k,
        fields="embedding"
    )

    # 3. Hybrid search (vector + full-text keyword)
    results = search.search(
        search_text=question,        # keyword search
        vector_queries=[vector_query], # vector search
        select=["content", "source", "page"],
        top=top_k
    )

    chunks = []
    for r in results:
        chunks.append({
            "content": r["content"],
            "source":  r["source"],
            "page":    r.get("page", 0),
            "score":   r["@search.score"]
        })
        logging.info(f"  Found chunk from '{r['source']}' score={r['@search.score']:.3f}")

    return chunks