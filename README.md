# RAG Chatbot

A document question-answering application built with Azure Functions, Azure Blob Storage, Azure AI Document Intelligence, Azure AI Search, Azure OpenAI embeddings, and Groq.

The application allows users to upload documents, index their contents, and ask questions grounded in the uploaded documents.

## Live Application

https://salmon-hill-0a0d9ea00.7.azurestaticapps.net/

## Features

- Upload documents through an HTTP endpoint.
- Store uploaded files in Azure Blob Storage.
- Automatically process uploaded files through an Azure Blob trigger.
- Extract text from supported document formats.
- Split extracted text into overlapping chunks.
- Generate embeddings using Azure OpenAI.
- Store document chunks and embeddings in an Azure AI Search index.
- Perform hybrid search using vector similarity and keyword search.
- Generate answers using Groq chat completions.
- Include source document names in query responses.
- Support optional conversation history when asking questions.
- Provide a browser-based frontend for uploading documents and asking questions.

## Supported File Types

The extractor supports the following file types:

- PDF
- JPG
- JPEG
- PNG
- BMP
- TIFF
- TIF
- HEIF
- DOCX
- PPTX
- XLSX
- XLS
- TXT
- Markdown
- CSV
- JSON
- XML
- HTML
- Python files
- JavaScript files

For PDF and image files, text extraction uses Azure AI Document Intelligence. DOCX, PPTX, and spreadsheet files are processed using Python libraries. Plain-text formats are decoded as UTF-8.

## Architecture

The application uses the following flow:

1. A document is uploaded through the `/api/upload` endpoint.
2. The file is stored in the `documents` Azure Blob Storage container.
3. The Blob Storage trigger starts document ingestion.
4. Text is extracted from the uploaded file.
5. The extracted text is divided into chunks of 1,000 characters with 100 characters of overlap.
6. Azure OpenAI generates an embedding for each chunk.
7. The chunks and embeddings are uploaded to the `rag-index` Azure AI Search index.
8. A question is submitted through the `/api/ask` endpoint.
9. The question is embedded using Azure OpenAI.
10. Azure AI Search performs hybrid vector and keyword search.
11. The retrieved chunks are sent to Groq.
12. Groq generates an answer using the retrieved document context.

## Project Structure

```text
rag-chatbot/
├── function_app.py
├── host.json
├── requirements.txt
├── frontend/
│   └── index.html
└── utils/
    ├── answerer.py
    ├── chunker.py
    ├── embedder.py
    ├── extractor.py
    └── searcher.py
```

### Main Components

- `function_app.py`
  - Defines the Azure Functions application.
  - Handles document uploads.
  - Handles user questions.
  - Runs Blob Storage-triggered ingestion.

- `utils/extractor.py`
  - Extracts text from supported file types.
  - Uses Azure AI Document Intelligence for PDFs and images.

- `utils/chunker.py`
  - Splits extracted text into overlapping chunks.
  - Attempts to preserve sentence boundaries.

- `utils/embedder.py`
  - Creates Azure OpenAI embeddings.
  - Uploads chunks and embeddings to Azure AI Search.

- `utils/searcher.py`
  - Creates an embedding for each question.
  - Performs hybrid vector and keyword search.

- `utils/answerer.py`
  - Sends retrieved context and the question to Groq.
  - Uses the configured Groq model to generate the response.

- `frontend/index.html`
  - Provides the upload interface and chat interface.
  - Sends requests to the local Azure Functions host or the configured deployed Functions endpoint.

## API Endpoints

The Azure Functions host exposes the following endpoints under the `/api` prefix.

### Upload a Document

```http
POST /api/upload?filename=document.pdf
```

Send the file contents as the request body.

Example using `curl`:

```bash
curl -X POST \
  "http://localhost:7071/api/upload?filename=document.pdf" \
  --data-binary "@document.pdf"
```

Successful response:

```json
{
  "message": "'document.pdf' uploaded successfully. Indexing started..."
}
```

Indexing runs asynchronously after the file is uploaded to Blob Storage.

### Ask a Question

```http
POST /api/ask
Content-Type: application/json
```

Request body:

```json
{
  "question": "What is this document about?",
  "history": []
}
```

The `history` field is optional and contains previous messages:

```json
{
  "question": "Can you explain that in more detail?",
  "history": [
    {
      "role": "user",
      "content": "What is this document about?"
    },
    {
      "role": "assistant",
      "content": "The document describes..."
    }
  ]
}
```

Successful response:

```json
{
  "answer": "Generated answer based on the uploaded documents.",
  "sources": [
    "document.pdf"
  ],
  "chunks_used": 5
}
```

If no matching documents are found, the endpoint returns an answer explaining that documents should be uploaded first.

## Required Configuration

The Azure Functions application requires the following environment variables:

```text
AzureWebJobsStorage
FUNCTIONS_WORKER_RUNTIME
AZURE_STORAGE_CONNECTION_STRING
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_KEY
AZURE_OPENAI_EMBED_DEPLOYMENT
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
AZURE_DOCUMENT_INTELLIGENCE_KEY
GROQ_API_KEY
```

The application also reads the optional variable below:

```text
GROQ_MODEL
```

If `GROQ_MODEL` is not provided, the application uses:

```text
llama-3.3-70b-versatile
```

Do not commit real credentials or connection strings. For local development, configure these values in `local.settings.json` or through the environment, and keep that file out of version control.

## Azure AI Search Index

The application expects an Azure AI Search index named:

```text
rag-index
```

Indexed documents are written with these fields:

- `id`
- `content`
- `source`
- `page`
- `embedding`

The search implementation expects the vector field to be named:

```text
embedding
```

The index must be configured to support both full-text search and vector search.

## Local Development

### Prerequisites

- Python
- Azure Functions Core Tools
- An Azure Storage account
- An Azure AI Search service
- An Azure OpenAI resource with an embedding deployment
- An Azure AI Document Intelligence resource
- A Groq API key

### Install Dependencies

From the project directory:

```bash
pip install -r requirements.txt
```

### Configure Local Settings

Create or update `local.settings.json` with the required application settings.

Use placeholders or local secret management for credentials. Do not commit real keys to the repository.

### Start the Functions Application

```bash
func start
```

The local API is available at:

```text
http://localhost:7071/api
```

The frontend is configured to use this local API when opened from a localhost address.

## Frontend

The frontend is located at:

```text
frontend/index.html
```

It provides:

- Document upload through file selection or drag and drop.
- A list of uploaded files for the current browser session.
- A chat interface for asking questions.
- Display of retrieved source document names.
- Conversation history sent with subsequent questions.
- A button to clear the current chat.

The frontend currently uses the local Functions endpoint for localhost environments and a configured Azure Functions URL for non-local environments.

## Error Responses

Invalid JSON requests return:

```json
{
  "error": "Invalid JSON body"
}
```

Missing questions return:

```json
{
  "error": "Field 'question' is required"
}
```

Upload requests without a filename return:

```json
{
  "error": "filename query param required"
}
```

Upload requests without file data return:

```json
{
  "error": "No file data in body"
}
```

## Dependencies

The project uses:

- Azure Functions
- Azure Blob Storage
- Azure AI Search
- Azure AI Document Intelligence
- Azure OpenAI
- OpenAI-compatible Groq API
- `python-docx`
- `python-pptx`
- `openpyxl`

## Current Limitations

- Uploaded documents are indexed asynchronously after upload.
- The frontend document list only represents files uploaded during the current browser session.
- The application depends on an Azure AI Search index named `rag-index`.
- Authentication for the upload and question endpoints is configured as anonymous in the Azure Functions code.
- Query answers are limited to the content returned from the document search results.
```

The project’s local settings file contains credential values. Those credentials should be rotated and the file should remain excluded from version control.