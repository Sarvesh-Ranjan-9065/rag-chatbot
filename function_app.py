# function_app.py
import azure.functions as func
import logging, json
import os

from azure.storage.blob import BlobServiceClient
from utils.extractor import extract_text
from utils.chunker import chunk_text
from utils.embedder import embed_and_index
from utils.searcher import search_documents
from utils.answerer import get_answer

app = func.FunctionApp()

# ── EXISTING: Blob trigger (ingestion) ────────────────────────────
@app.blob_trigger(
    arg_name="myblob",
    path="documents/{name}",
    connection="AZURE_STORAGE_CONNECTION_STRING"
)
def ingest_document(myblob: func.InputStream):
    filename = myblob.name.split("/")[-1]
    logging.info(f"⚡ Triggered: {filename} ({myblob.length} bytes)")
    blob_data = myblob.read()
    text      = extract_text(blob_data, filename)
    if not text.strip():
        logging.warning(f"⚠️  No text extracted from {filename}")
        return
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    embed_and_index(chunks, source=filename)
    logging.info(f"✅ Indexed {len(chunks)} chunks from '{filename}'")


# ── NEW: HTTP trigger (query) ──────────────────────────────────────
@app.route(route="ask", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def ask_question(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("📥 Query request received")

    # Parse request body
    try:
        body     = req.get_json()
        question = body.get("question", "").strip()
        history  = body.get("history", [])  # optional chat history
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    if not question:
        return func.HttpResponse(
            json.dumps({"error": "Field 'question' is required"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        # 1. Search for relevant chunks
        chunks = search_documents(question, top_k=5)

        if not chunks:
            return func.HttpResponse(
                json.dumps({
                    "answer":  "No relevant documents found. Please upload some documents first.",
                    "sources": [],
                    "chunks_used": 0
                }),
                mimetype="application/json"
            )

        # 2. Get grounded answer from Groq
        answer = get_answer(question, chunks, history)

        # 3. Build sources list (deduplicated)
        sources = list({c["source"] for c in chunks})

        return func.HttpResponse(
            json.dumps({
                "answer":      answer,
                "sources":     sources,
                "chunks_used": len(chunks)
            }),
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Query failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="upload", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def upload_document(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("📤 Upload request received")

    try:
        filename = req.params.get("filename")
        if not filename:
            return func.HttpResponse(
                json.dumps({"error": "filename query param required"}),
                status_code=400,
                mimetype="application/json"
            )

        file_data = req.get_body()
        if not file_data:
            return func.HttpResponse(
                json.dumps({"error": "No file data in body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Upload to Blob Storage -> triggers ingest_document automatically
        blob_service = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        blob_client = blob_service.get_blob_client(
            container="documents", blob=filename
        )
        blob_client.upload_blob(file_data, overwrite=True)

        logging.info(f"✅ Uploaded '{filename}' to blob storage")
        return func.HttpResponse(
            json.dumps({"message": f"'{filename}' uploaded successfully. Indexing started..."}),
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
# ── END OF FILE ───────────────────────────────────────────────
@app.route(route="groq_test", auth_level=func.AuthLevel.ANONYMOUS)
def groq_test(req: func.HttpRequest) -> func.HttpResponse:

    import os
    import requests
    import logging

    try:
        api_key = os.getenv("GROQ_API_KEY", "").strip()

        logging.info(f"GROQ key exists: {bool(api_key)}")
        logging.info(f"Key prefix: {api_key[:8]}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello"
                }
            ]
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        logging.info(f"Status: {response.status_code}")
        logging.info(f"Response: {response.text}")

        return func.HttpResponse(
            response.text,
            status_code=response.status_code,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(str(e), status_code=500)