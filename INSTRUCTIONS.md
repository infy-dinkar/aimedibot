# 🚀 Hosting on Render (Free Tier) — Step-by-Step Guide

This guide walks you through deploying **MedRAG** on [Render.com](https://render.com) for free.

---

## ✅ Pre-Deployment Checklist

- [ ] Code pushed to a **GitHub repository** (public or private)
- [ ] `PINECONE_API_KEY` ready
- [ ] `GROQ_API_KEY` ready
- [ ] `render.yaml` is in the root of the repo (already included)

---

## 📋 Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit — MedRAG chatbot"
git remote add origin https://github.com/YOUR_USERNAME/medical-rag-chatbot.git
git branch -M main
git push -u origin main
```

---

## 📋 Step 2 — Create a Render Account

1. Go to [render.com](https://render.com) and sign up (free)
2. Connect your **GitHub account** when prompted

---

## 📋 Step 3 — Create a New Web Service

1. From your Render dashboard, click **"New +"** → **"Web Service"**
2. Select **"Build and deploy from a Git repository"**
3. Find and select your `medical-rag-chatbot` repo → click **"Connect"**

---

## 📋 Step 4 — Configure the Service

Fill in these settings:

| Field | Value |
|-------|-------|
| **Name** | `medical-rag-chatbot` (or any name you like) |
| **Region** | Oregon (US West) — or closest to you |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT` |
| **Instance Type** | **Free** |

> ⚠️ **Important**: Use `--workers 1` to stay within 512 MB RAM on the free tier.

---

## 📋 Step 5 — Add Environment Variables

Scroll down to **"Environment Variables"** and add:

| Key | Value |
|-----|-------|
| `PINECONE_API_KEY` | `your_actual_pinecone_api_key` |
| `GROQ_API_KEY` | `your_actual_groq_api_key` |

Click **"Add Environment Variable"** for each one.

---

## 📋 Step 6 — Deploy

Click **"Create Web Service"**.

Render will:
1. Pull your code from GitHub
2. Run `pip install -r requirements.txt` (this takes 3–5 minutes the first time)
3. Start the app with gunicorn

You'll see a live build log. When you see `==> Your service is live 🎉`, you're done!

Your app will be live at:
```
https://medical-rag-chatbot.onrender.com
```
(or whatever name you chose)

---

## ⚠️ Free Tier Limitations

| Limitation | Detail |
|-----------|--------|
| **RAM** | 512 MB — our app uses ~310 MB ✅ |
| **Sleep after inactivity** | App sleeps after 15 min of no traffic |
| **Cold start** | First request after sleep takes ~30–60 sec (model reload) |
| **Bandwidth** | 100 GB/month |
| **Build minutes** | 500 min/month |

### How to handle cold starts
- The free tier spins down after 15 minutes of inactivity
- Add a note on your demo page warning users about the first-load delay
- Or use a free uptime service like [UptimeRobot](https://uptimerobot.com) to ping your app every 14 minutes (keeps it awake)

---

## 🔄 Automatic Deploys

Render auto-deploys whenever you push to the `main` branch. Just:

```bash
git add .
git commit -m "Update something"
git push
```

Render picks it up automatically within a minute.

---

## 🐛 Checking Logs

If something goes wrong:
1. Go to your Render dashboard
2. Click on your service
3. Click **"Logs"** tab on the left
4. Look for any red `ERROR` lines

Common issues:
- `ModuleNotFoundError` → check `requirements.txt`
- `Invalid API key` → double-check environment variables in Render dashboard
- `Memory exceeded` → your app is too heavy; ensure only 1 gunicorn worker

---

## 🧪 Testing Your Deployed App

1. Open `https://your-app-name.onrender.com/upload-page`
2. Upload a sample medical PDF (e.g., a public domain medical textbook)
3. Go to `https://your-app-name.onrender.com/`
4. Ask a question related to the book

---

## 💡 Pro Tips for Your Demo

- Upload 2–3 medical PDFs to show rich responses
- Use the suggestion chips on the chat page to quickly demo it
- The sources shown below each answer prove RAG is working
- Share the URL and people can immediately start chatting

---

## 📚 Useful Free Resources for Medical PDFs

- [OpenStax Anatomy & Physiology](https://openstax.org/details/books/anatomy-and-physiology-2e) — free, open license
- [NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/books/) — free medical textbooks
- [WHO Publications](https://www.who.int/publications) — free health guidelines
