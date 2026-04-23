# Odido AI Newsletter Generator

An automated pipeline that reads AI/LLM articles from Hugging Face, picks the most relevant ones, summarises them using Azure OpenAI (GPT-4o), rates the quality using an open-source AI judge (Llama 3 via Groq), and produces a polished weekly newsletter in Markdown — all automatically, every Monday.

---

## How It Works

```
Hugging Face Dataset  (1,479 AI/LLM articles)
        │
        ▼
  1. load_data.py         ← Download and clean the dataset
        │
        ▼
  2. select_items.py      ← Filter to recent articles, remove duplicates, score relevance
        │
        ▼
  3. categorize.py        ← Sort into 3 sections: Research / Industry News / Cool Use Cases
        │
        ▼
  4. summarize.py         ← Generate 2-sentence summaries using Azure OpenAI (GPT-4o)
        │
        ▼
  4b. judge.py            ← Rate each summary for Faithfulness & Clarity using Llama 3 (Groq)
        │
        ▼
  5. render_newsletter.py ← Build and save newsletter.md with all content and scores
```

---

## Project Structure

```
odido-ai-newsletter/
├── src/
│   ├── load_data.py           # Step 1 – Download HuggingFace dataset
│   ├── select_items.py        # Step 2 – Filter, deduplicate, score
│   ├── categorize.py          # Step 3 – Assign articles to sections
│   ├── summarize.py           # Step 4 – Azure OpenAI summarisation
│   ├── judge.py               # Step 4b – LLM-as-a-Judge quality scoring (Groq + Llama 3)
│   └── render_newsletter.py   # Step 5 – Write newsletter.md
├── .github/
│   └── workflows/
│       └── weekly_newsletter.yml   # Runs automatically every Monday
├── index.html                 # Browser frontend to view the newsletter
├── run_pipeline.py            # Main entry point — runs all steps
├── newsletter.md              # Latest generated newsletter
├── requirements.txt           # Python dependencies
├── .env.example               # Template for credentials
└── README.md
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Kshitij-AI-Architect/odido-ai-newsletter.git
cd odido-ai-newsletter
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate        # Windows
source .venv/bin/activate       # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up credentials

```bash
copy .env.example .env
```

Open `.env` and fill in your values:

```env
# Azure OpenAI — used to generate summaries (GPT-4o)
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2023-12-01-preview

# Groq — used to run the LLM-as-a-Judge (Llama 3, free at console.groq.com)
GROQ_API_KEY=your-groq-key
```

### 5. Run the pipeline

```powershell
python run_pipeline.py --lookback-days 90 --output newsletter.md
```

### 6. View in browser

```powershell
python -m http.server 8080
```

Open: `http://localhost:8080`

---

## GitHub Actions (Automated Weekly Run)

The workflow runs **every Monday at 08:00 UTC** automatically.

### One-time setup:
1. Push repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_OPENAI_API_VERSION`
   - `GROQ_API_KEY`
4. Go to **Settings → Actions → General → Workflow permissions** → set to **Read and write**

To trigger manually: **Actions tab → Weekly AI Newsletter → Run workflow**

---

## LLM-as-a-Judge (Quality Evaluation)

Each generated summary is independently scored by **Llama 3** (an open-source model running on Groq's free API) on two dimensions:

| Score | What it means |
|---|---|
| **Faithfulness (1-5)** | Does the summary stick to facts in the source? No hallucination? |
| **Clarity (1-5)** | Is it easy to read, concise, and professional? |

Scores appear in `newsletter.md` and as badges in the browser frontend.

Using a **different model as judge** (Llama 3) than the one that generated summaries (GPT-4o) avoids self-evaluation bias. This is the standard **LLM-as-a-Judge** pattern used in production AI evaluation.

---

## Design Decisions

| Decision | Why |
|---|---|
| One file per pipeline step | Clean separation — easy to read, test, and explain |
| Rule-based scoring & categorisation | Fully transparent, no black-box ML, easy to tune |
| One LLM call per article | Predictable cost, easy to debug |
| Azure OpenAI for summarisation | Enterprise-grade, data stays within tenant |
| Groq + Llama 3 as judge | Free, open-source, independent model — avoids self-evaluation bias |
| GitHub Actions cron | Zero infrastructure, runs automatically every Monday |
| Markdown output | Works on GitHub, easy to share in email or Slack |

---

## Requirements

- Python 3.11+
- Azure OpenAI deployment (GPT-4o or GPT-3.5)
- Groq API key — free at [console.groq.com](https://console.groq.com)
- No Hugging Face token needed (public dataset)
