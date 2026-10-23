# utils/embedder.py
import os, logging
from openai import AzureOpenAI
from azure.search.documents import SearchClient
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

def embed_and_index(chunks: list[str], source: str):
    oai    = get_oai_client()
    search = get_search_client()
    deploy = os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]

    docs = []
    for i, chunk in enumerate(chunks):
        # Generate embedding for this chunk
        response = oai.embeddings.create(model=deploy, input=chunk)
        embedding = response.data[0].embedding

        # Build the search document
        safe_source = source.replace("/", "_").replace(".", "_")
        docs.append({
            "id":        f"{safe_source}-chunk-{i}",
            "content":   chunk,
            "source":    source,
            "page":      i,
            "embedding": embedding
        })

    # Batch upload to AI Search (max 1000 per call)
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        search.upload_documents(batch)
        logging.info(f"Uploaded batch {i//batch_size + 1}: {len(batch)} chunks")