# utils/answerer.py
import logging
import os

from openai import OpenAI

def get_answer(question: str, chunks: list[dict], history: list[dict] = []) -> str:
    """
    Sends the question + retrieved context to Groq.
    Returns a grounded answer with source citations.
    """
    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Build context block from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}: {chunk['source']}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Build conversation history string
    history_text = ""
    if history:
        history_text = "\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in history[-6:]  # last 3 exchanges
        ])
        history_text = f"\nConversation so far:\n{history_text}\n"

    # Final prompt
    prompt = f"""You are RAG Chatbot, an intelligent document assistant built on Microsoft Azure 
(Azure Functions, Azure AI Search, Azure OpenAI, Groq LLaMA).

Rules:
- For greetings or questions about yourself → respond naturally and briefly
- For ANY factual/knowledge question → answer ONLY using the context below
- If the answer isn't in the context → say "I couldn't find that in the uploaded documents"
- Always cite which source document you used
{history_text}
Context from documents:
{context}

Question: {question}

Answer:"""

    logging.info("Sending to Groq...")
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""