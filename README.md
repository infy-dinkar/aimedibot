# 🩺 MedRAG — Medical Knowledge Chatbot

A beginner-friendly **Retrieval-Augmented Generation (RAG)** chatbot built with:

- **Flask** — lightweight Python web server
- **PyMuPDF** — fast PDF text extraction
- **sentence-transformers** (`all-MiniLM-L6-v2`) — compact 384-dim embeddings (~90 MB)
- **Pinecone** — serverless vector database
- **Groq + LLaMA 3.1 8B Instant** — blazing-fast LLM inference

---

## 📁 Project Structure

```
medical-rag-chatbot/
├── app.py               # Flask backend (API + routes)
├── templates/
│   ├── index.html       # Chat UI
│   └── upload.html      # PDF upload UI
├── requirements.txt
├── render.yaml          # Render deployment config
├── .env.example
├── .gitignore
├── README.md
└── INSTRUCTIONS.md      # Hosting guide
```

---

## ⚙️ Prerequisites

- Python 3.10+ installed
- A **Pinecone** account → [pinecone.io](https://www.pinecone.io) (free tier works)
- A **Groq** account → [console.groq.com](https://console.groq.com) (free tier works)

---

## 🚀 Local Setup (Step by Step)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/medical-rag-chatbot.git
cd medical-rag-chatbot
```

### 2. Create a Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate it
# On macOS / Linux:
source venv/bin/activate

# On Windows:
venv/Scripts/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ First install downloads the `all-MiniLM-L6-v2` model (~90 MB). This only happens once; it's cached afterwards.

### 4. Set Up Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
PINECONE_API_KEY=your_pinecone_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

**Where to get these keys:**

| Key | Where to find |
|-----|--------------|
| `PINECONE_API_KEY` | [Pinecone Console](https://app.pinecone.io) → API Keys |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) → API Keys |

### 5. Run the App

```bash
python app.py
```

Open your browser at → **http://localhost:5000**

---

## 🖥️ How to Use

### Step 1 — Upload a Medical Book

1. Click **"Upload Book"** in the top-right corner (or go to `/upload-page`)
2. Drag & drop or browse to select a `.pdf` file (medical textbook, guidelines, etc.)
3. Click **"Ingest into Knowledge Base"**
4. Wait for the success message — the book is now chunked, embedded, and stored in Pinecone

> The Pinecone index `medical-chatbot` is created automatically on first upload.

### Step 2 — Chat

1. Go to the **Chat** page (home `/`)
2. Type your medical question
3. The chatbot retrieves the most relevant chunks from Pinecone and uses Groq's LLaMA 3.1 to answer

---

## 🧠 How RAG Works (For Beginners)

```
PDF → Extract Text → Split into Chunks → Embed each Chunk → Store in Pinecone
                                                                        ↓
User Query → Embed Query → Search Pinecone → Top 5 Chunks → LLaMA 3.1 → Answer
```

1. **Chunking**: Book text is split into 500-word overlapping windows
2. **Embedding**: Each chunk is converted to a 384-number vector using MiniLM
3. **Storage**: Vectors + original text stored in Pinecone with book name as metadata
4. **Retrieval**: Query is embedded → cosine similarity search → top 5 chunks returned
5. **Generation**: Chunks become context for LLaMA 3.1 → grounded, factual answer

---

## 📦 Dependency Size Breakdown

| Library | Approx Size |
|---------|------------|
| sentence-transformers + model | ~280 MB |
| PyMuPDF | ~15 MB |
| Flask + gunicorn | ~5 MB |
| pinecone | ~5 MB |
| groq | ~3 MB |
| **Total** | **~308 MB** |

Fits within Render's 512 MB free tier ✅

---

## 🛑 Troubleshooting

| Problem | Fix |
|---------|-----|
| PDF has no text (scanned) | Only text-based PDFs work; OCR not supported |
| Pinecone index not found | Check API key and region in Pinecone console |
| Empty answers | Upload a book first before chatting |
| Slow first response | Model loads on first request; subsequent ones are faster |

---

## 📄 License

MIT — free to use, modify, and deploy.
