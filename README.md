# Odido AI Newsletter Generator

An automated pipeline that ingests the [zenml/llmops-database](https://huggingface.co/datasets/zenml/llmops-database) dataset from Hugging Face, selects the most relevant AI/LLM articles from the past week, summarises them using Azure OpenAI, and renders a polished **Markdown newsletter** — automatically, every Monday via GitHub Actions.

---

## How It Works

```
Hugging Face Dataset
        │
        ▼
  1. load_data.py       ← Download & clean the dataset
        │
        ▼
  2. select_items.py    ← Filter to last 7 days, deduplicate, score relevance
        │
        ▼
  3. categorize.py      ← Assign each item to a section (Research / Industry / Use Cases)
        │
        ▼
  4. summarize.py       ← Generate 2-sentence summaries via Azure OpenAI
        │
        ▼
  5. render_newsletter.py ← Build and write newsletter.md
```

Each step is a self-contained Python module. The pipeline is wired together in `run_pipeline.py`.

---

## Project Structure

```
odido-ai-newsletter/
├── src/
│   ├── load_data.py          # Step 1 – Ingest HuggingFace dataset
│   ├── select_items.py       # Step 2 – Filter, dedup, score
│   ├── categorize.py         # Step 3 – Rule-based section assignment
│   ├── summarize.py          # Step 4 – Azure OpenAI summarisation
│   └── render_newsletter.py  # Step 5 – Markdown rendering
├── .github/
│   └── workflows/
│       └── weekly_newsletter.yml  # Scheduled GitHub Actions job
├── run_pipeline.py           # Main entry point
├── newsletter.md             # Sample generated newsletter
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup (Local)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/odido-ai-newsletter.git
cd odido-ai-newsletter
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your Azure OpenAI credentials:

```env
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-01
```

### 5. Run the pipeline

```bash
python run_pipeline.py
```

The newsletter is saved to `newsletter.md` in the project root.

**Optional flags:**

```bash
# Look back 14 days instead of 7
python run_pipeline.py --lookback-days 14

# Save output to a custom path
python run_pipeline.py --output output/week-42.md
```

---

## Automated Weekly Run (GitHub Actions)

The workflow in `.github/workflows/weekly_newsletter.yml` runs **every Monday at 08:00 UTC**.

### Setup Steps

1. Push this repository to GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Add the following repository secrets:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_OPENAI_API_VERSION`
4. The pipeline runs automatically each Monday and commits the updated `newsletter.md` back to the repository.

You can also trigger it manually from the **Actions** tab using the **"Run workflow"** button.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **Rule-based scoring** | Simple, transparent, easy to explain — no black-box ML |
| **Rule-based categorisation** | Fast, zero cost, instantly tunable via keyword lists |
| **One LLM call per article** | Predictable token usage, easy to debug individual outputs |
| **Azure OpenAI** | Enterprise-grade, no data leaves the tenant |
| **Markdown output** | Portable, renders on GitHub, easy to copy into email/Slack |
| **GitHub Actions cron** | Zero infrastructure needed for scheduling |

---

## Sample Newsletter

See [`newsletter.md`](newsletter.md) for a sample output generated from the dataset.

---

## Requirements

- Python 3.11+
- Azure OpenAI resource with a deployed chat model (e.g., `gpt-4o`, `gpt-35-turbo`)
- Hugging Face `datasets` library (downloads dataset automatically, no token needed)
