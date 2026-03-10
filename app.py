import os
import io
from pypdf import PdfReader
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from groq import Groq

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY")
INDEX_NAME       = "medical-chatbot"
EMBED_MODEL      = "multilingual-e5-large"  # Pinecone hosted — no local download
EMBED_DIM        = 1024                      # dimension for multilingual-e5-large
CHUNK_SIZE       = 500
CHUNK_OVERLAP    = 50

# Lazy singletons
_pc    = None
_index = None


def get_pc():
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
    return _pc


def get_index():
    global _index
    if _index is None:
        pc = get_pc()
        existing = [i.name for i in pc.list_indexes()]
        if INDEX_NAME not in existing:
            pc.create_index(
                name=INDEX_NAME,
                dimension=EMBED_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        _index = pc.Index(INDEX_NAME)
    return _index


def embed(texts, input_type):
    """Call Pinecone's hosted embedding API — zero local model needed."""
    pc = get_pc()
    result = pc.inference.embed(
        model=EMBED_MODEL,
        inputs=texts,
        parameters={"input_type": input_type, "truncate": "END"},
    )
    return [item["values"] for item in result]


def extract_text_from_pdf(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


# ── Routes ───────────────────────────────────────────────────────────────────

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

    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500

    if not raw_text.strip():
        return jsonify({"error": "PDF appears to be empty or scanned without text"}), 400

    chunks = chunk_text(raw_text)

    # Embed in batches of 96 (Pinecone inference limit)
    all_embeddings = []
    for i in range(0, len(chunks), 96):
        batch = chunks[i: i + 96]
        all_embeddings.extend(embed(batch, input_type="passage"))

    # Upsert to Pinecone in batches of 100
    index = get_index()
    vectors = [
        {
            "id": f"{book_name}_chunk_{i}",
            "values": emb,
            "metadata": {"text": chunk, "source": book_name},
        }
        for i, (chunk, emb) in enumerate(zip(chunks, all_embeddings))
    ]

    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i: i + 100])

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
    query_emb = embed([user_query], input_type="query")[0]

    # Retrieve from Pinecone
    index = get_index()
    results = index.query(vector=query_emb, top_k=5, include_metadata=True)

    context_chunks = [
        m["metadata"]["text"]
        for m in results["matches"]
        if m.get("metadata", {}).get("text")
    ]

    context_text = (
        "\n\n---\n\n".join(context_chunks)
        if context_chunks
        else "No relevant context found in the knowledge base."
    )

    system_prompt = (
        "You are a helpful medical knowledge assistant. "
        "Answer the user's question using ONLY the context provided below. "
        "If the answer is not in the context, say you don't have enough information. "
        "Be clear, concise, and beginner-friendly.\n\n"
        f"CONTEXT:\n{context_text}"
    )

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

    answer  = response.choices[0].message.content
    sources = list({m["metadata"].get("source", "unknown") for m in results["matches"]})

    return jsonify({"answer": answer, "sources": sources})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)