import os
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from groq import Groq

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30MB max upload

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
INDEX_NAME = "medical-chatbot"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # tiny & fast, 384-dim
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Lazy-load heavy objects once
_embed_model = None
_pinecone_index = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = [i.name for i in pc.list_indexes()]
        if INDEX_NAME not in existing:
            pc.create_index(
                name=INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        _pinecone_index = pc.Index(INDEX_NAME)
    return _pinecone_index


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload-page")
def upload_page():
    return render_template("upload.html")


@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted"}), 400

    pdf_bytes = file.read()
    book_name = file.filename.replace(".pdf", "").replace(" ", "_")

    # Extract text
    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500

    if not raw_text.strip():
        return jsonify({"error": "PDF appears to be empty or scanned without text"}), 400

    # Chunk
    chunks = chunk_text(raw_text)

    # Embed
    model = get_embed_model()
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    # Upsert to Pinecone
    index = get_pinecone_index()
    vectors = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        vectors.append({
            "id": f"{book_name}_chunk_{i}",
            "values": emb,
            "metadata": {"text": chunk, "source": book_name},
        })

    # Batch upsert (100 at a time)
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i: i + batch_size])

    return jsonify({
        "message": f"Successfully ingested '{file.filename}'",
        "chunks_indexed": len(chunks),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_query = data.get("query", "").strip()
    if not user_query:
        return jsonify({"error": "Empty query"}), 400

    # Embed query
    model = get_embed_model()
    query_emb = model.encode([user_query]).tolist()[0]

    # Retrieve from Pinecone
    index = get_pinecone_index()
    results = index.query(vector=query_emb, top_k=5, include_metadata=True)

    context_chunks = [
        match["metadata"]["text"]
        for match in results["matches"]
        if match.get("metadata", {}).get("text")
    ]

    if not context_chunks:
        context_text = "No relevant context found in the knowledge base."
    else:
        context_text = "\n\n---\n\n".join(context_chunks)

    # Build prompt
    system_prompt = (
        "You are a helpful medical knowledge assistant. "
        "Answer the user's question using ONLY the context provided below. "
        "If the answer is not in the context, say you don't have enough information. "
        "Be clear, concise, and beginner-friendly.\n\n"
        f"CONTEXT:\n{context_text}"
    )

    # Groq inference
    groq_client = Groq(api_key=GROQ_API_KEY)
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        max_tokens=1024,
        temperature=0.3,
    )

    answer = response.choices[0].message.content
    sources = list({m["metadata"].get("source", "unknown") for m in results["matches"]})

    return jsonify({"answer": answer, "sources": sources})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
