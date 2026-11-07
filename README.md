# 🚀 Generative AI Learning & News Agent

An autonomous Python agent powered by **Google Gemini (`google-genai`)** that pulls the latest Generative AI research papers, official lab announcements, community engineering discussions, and live web news—then synthesizes them into a structured **Daily Learning Digest**.

## ✨ Features

1. **Multi-Source GenAI Collectors** (`src/genai_agent/collectors/`):
   - 📄 **Research Papers**: Trending papers from **Hugging Face Daily Papers** (ranked by community upvotes) + latest **arXiv (`cs.CL` / `cs.AI`)** preprints matching your learning focus.
   - 🏢 **AI Lab & Engineering Blogs**: Official RSS/Atom feeds from **OpenAI News**, **Google AI Blog**, **Google DeepMind**, **Hugging Face Blog**, **Simon Willison**, **Lilian Weng**, and **LangChain**.
   - 🛠️ **Community & Engineering Pulse**: Top AI stories from **Hacker News** (via Algolia API) and hot discussions from **Reddit** (`r/LocalLLaMA`, `r/MachineLearning`).
   - 🌐 **Web Search & Grounding**: Live **Google News RSS** + **Gemini Google Search Grounding** (`google_search` tool) for breaking releases in the last 48 hours.

2. **Learning-First Synthesis** (`src/genai_agent/agent.py`):
   - **⚡ Executive TL;DR**: Top 3 breakthroughs of the day.
   - **🧠 Concept of the Day (Technical Deep-Dive)**: Picks the most educational architecture, post-training technique, or agentic pattern from today's feed and explains *what problem it solves*, *how it works intuitively*, and *how to apply it in practice*.
   - **📄 Research Papers Spotlight**: Curated top papers with core ideas and takeaways.
   - **🏢 AI Lab Announcements & 🛠️ Community Pulse**: High-signal updates and discussions.
   - **🎯 15-Minute Learning Challenge**: A concrete hands-on mini-exercise or architectural reflection prompt.

3. **Multi-Channel Delivery** (`src/genai_agent/notifiers/`):
   - 📁 **Local Markdown Archive**: Saves dated digests to `digests/YYYY-MM-DD_genai_digest.md` and `digests/latest.md`.
   - ✈️ **Telegram Bot Notification**: Automatically chunks long digests cleanly and delivers them to your Telegram chat.
   - 📧 **Email Digest**: Renders a styled HTML + plaintext email and sends via **SMTP** (e.g. Gmail App Password) or **Resend API**.

---

## 🛠️ Quick Start

### 1. Create a Virtual Environment & Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure `.env`

Copy `.env.example` to `.env` and add your Gemini API key (and optional Telegram / Email credentials):

```bash
cp .env.example .env
```

Minimal `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
LEARNING_FOCUS_TOPICS=LLMs, AI Agents, RAG, Multimodal AI, Reasoning Models, Post-Training & RLHF, Inference Optimization
```

### 3. Run the Agent

```bash
# Full run: Pulls all sources, synthesizes with Gemini + Google Search grounding, saves to digests/, and sends configured notifications
genai-agent

# Customize learning focus topics on the fly
genai-agent --topics "Agentic Workflows, MCP, Speculative Decoding, Multimodal"

# Run in Autonomous Function-Calling Mode (Gemini decides which collector tools to invoke)
genai-agent --agentic-tools

# Collect-only mode (fetches all live sources & saves Markdown without needing a Gemini API key)
genai-agent --collect-only
```

---

## 📬 Configuring Notifications

### Telegram Bot Setup
1. Message **[@BotFather](https://t.me/BotFather)** on Telegram and run `/newbot` to get your `TELEGRAM_BOT_TOKEN`.
2. Send a message to your new bot, then open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your browser to find your `chat.id`.
3. Set in `.env`:
   ```ini
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_CHAT_ID=987654321
   ```

### Email Setup (Gmail SMTP or Resend)
- **Gmail SMTP**: Create a [Google App Password](https://myaccount.google.com/apppasswords) and configure in `.env`:
  ```ini
  EMAIL_ENABLED=true
  EMAIL_PROVIDER=smtp
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USERNAME=you@gmail.com
  SMTP_PASSWORD=abcd efgh ijkl mnop
  EMAIL_FROM=you@gmail.com
  EMAIL_TO=you@gmail.com
  ```
- **Resend API**: Set `EMAIL_PROVIDER=resend` and `RESEND_API_KEY=re_...`.
