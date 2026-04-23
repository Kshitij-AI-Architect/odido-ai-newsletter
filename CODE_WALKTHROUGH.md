# Code Walkthrough — Odido AI Newsletter Pipeline

This document explains every file and every meaningful line of code in the project,
written so you can walk through it confidently in your interview.

---

## Table of Contents

1. [Project Overview & Big Picture](#1-project-overview--big-picture)
2. [Folder Structure](#2-folder-structure)
3. [How Data Flows Through the Pipeline](#3-how-data-flows-through-the-pipeline)
4. [File-by-File Code Explanation](#4-file-by-file-code-explanation)
   - [run_pipeline.py — The Conductor](#run_pipelinepy--the-conductor)
   - [src/load_data.py — Step 1: Ingest](#srcload_datapy--step-1-ingest)
   - [src/select_items.py — Step 2: Filter & Score](#srcselect_itemspy--step-2-filter--score)
   - [src/categorize.py — Step 3: Categorise](#srccategorizepy--step-3-categorise)
   - [src/summarize.py — Step 4: Summarise with AI](#srcsummarizepy--step-4-summarise-with-ai)
   - [src/render_newsletter.py — Step 5: Render](#srcrender_newsletterpy--step-5-render)
   - [index.html — The Frontend](#indexhtml--the-frontend)
   - [.github/workflows/weekly_newsletter.yml — Automation](#githubworkflowsweekly_newsletteryml--automation)
   - [requirements.txt & .env — Config Files](#requirementstxt--env--config-files)
5. [Key Design Decisions](#5-key-design-decisions)
6. [How to Run the Application](#6-how-to-run-the-application)

---

## 1. Project Overview & Big Picture

The problem: Odido's tech team needs to stay up to date with fast-moving AI news,
but reading dozens of sources every week is expensive in time. The solution is to
automate this entirely.

The pipeline does four things automatically every week:
1. **Downloads** a curated AI/LLM dataset from Hugging Face (1,479 articles)
2. **Filters** it to only this week's fresh articles and picks the top 15
3. **Summarises** each article using Azure OpenAI (GPT-4o) into 2 clear sentences
4. **Renders** a polished Markdown newsletter and displays it in a web frontend

The whole thing runs on a **weekly schedule via GitHub Actions** with no manual work needed.

---

## 2. Folder Structure

```
Odido/
│
├── run_pipeline.py              ← Main entry point — runs all 5 steps in order
│
├── src/                         ← One file per pipeline step
│   ├── __init__.py              ← Marks src/ as a Python package
│   ├── load_data.py             ← Step 1: Download & clean dataset
│   ├── select_items.py          ← Step 2: Filter, deduplicate, score
│   ├── categorize.py            ← Step 3: Assign section labels
│   ├── summarize.py             ← Step 4: Call Azure OpenAI per article
│   └── render_newsletter.py     ← Step 5: Write newsletter.md
│
├── .github/
│   └── workflows/
│       └── weekly_newsletter.yml ← GitHub Actions cron job (every Monday)
│
├── index.html                   ← Browser frontend to view the newsletter
├── newsletter.md                ← The generated output (updated weekly)
├── requirements.txt             ← Python package dependencies
├── .env                         ← Your local secrets (never committed to git)
├── .env.example                 ← Template showing what .env should contain
├── .gitignore                   ← Tells git to ignore .env, .venv, etc.
└── README.md                    ← Setup and run instructions
```

Why this structure? Each step of the pipeline is its own file. This makes the code
**easy to read, easy to test, and easy to explain** — if something breaks you know
exactly which file to look at.

---

## 3. How Data Flows Through the Pipeline

```
Hugging Face Dataset (online)
        │
        │  load_dataset("zenml/llmops-database")
        ▼
   pandas DataFrame                   ← 1,479 rows, all columns
        │
        │  filter by date + deduplicate + score
        ▼
   pandas DataFrame                   ← top 15 rows only
        │
        │  keyword-based section assignment
        ▼
   pandas DataFrame                   ← top 15 rows + "section" column
        │
        │  Azure OpenAI GPT-4o call per row
        ▼
   pandas DataFrame                   ← top 15 rows + "summary" column
        │
        │  Markdown string builder
        ▼
   newsletter.md                      ← final output file
        │
        │  Python HTTP server
        ▼
   index.html in browser              ← rendered newsletter UI
```

The data structure used throughout is a **pandas DataFrame** — think of it as a
spreadsheet in memory. Each row is one article, each column is a field like title,
company, date, summary, section.

---

## 4. File-by-File Code Explanation

---

### `run_pipeline.py` — The Conductor

This is the only file you run. It imports and calls all five modules in order.
Think of it as the table of contents that connects everything.

```python
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
```
- `argparse` — lets you pass command-line flags like `--lookback-days 90`
- `sys` — used to exit cleanly if there are no articles found
- `pathlib.Path` — a modern, cross-platform way to work with file paths
- `dotenv.load_dotenv()` — reads the `.env` file and injects the secrets as
  environment variables, so the code can access your API key without it being
  hardcoded anywhere in the source

```python
load_dotenv()
```
This one line is called **before** any imports from `src/` because those modules
read environment variables at call time. Putting it here at the top ensures the
variables are available when needed.

```python
from src.load_data import load_llmops_data
from src.select_items import select_weekly_items
from src.categorize import categorize_items
from src.summarize import summarize_items
from src.render_newsletter import render_newsletter
```
These five imports bring in one function from each step module. The `src.` prefix
works because `src/__init__.py` exists, making `src/` a Python package.

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Odido AI Newsletter Generator")
    parser.add_argument("--lookback-days", type=int, default=7, ...)
    parser.add_argument("--output", type=str, default="newsletter.md", ...)
    return parser.parse_args()
```
This function sets up two optional flags:
- `--lookback-days` controls how far back to look for articles (default 7 days)
- `--output` controls where to save the newsletter file (default: newsletter.md)

These make the pipeline flexible without changing the code.

```python
def main() -> None:
    args = parse_args()
    df = load_llmops_data()                          # Step 1
    df = select_weekly_items(df, args.lookback_days) # Step 2
    if df.empty:
        sys.exit(0)                                  # Stop if no articles found
    df = categorize_items(df)                        # Step 3
    df = summarize_items(df)                         # Step 4
    render_newsletter(df, output_path=args.output)   # Step 5
```
The `main()` function is the entire pipeline in 6 lines. Notice each step receives
the DataFrame from the previous step and returns an enriched version. This is called
a **linear data pipeline** — data flows one direction with no loops.

```python
if __name__ == "__main__":
    main()
```
This is a Python idiom that means: "only run `main()` if this file was called
directly (e.g. `python run_pipeline.py`), not if it was imported by another module."

---

### `src/load_data.py` — Step 1: Ingest

**Purpose:** Connect to Hugging Face, download the dataset, and return a clean DataFrame.

```python
from datasets import load_dataset
```
`datasets` is Hugging Face's official Python library. It handles downloading,
caching, and formatting the dataset automatically. No API key needed for public datasets.

```python
DATASET_NAME = "zenml/llmops-database"
```
A constant at the top of the file. If the dataset is ever moved or renamed, you
change it in one place only.

```python
COLUMNS_NEEDED = [
    "created_at", "title", "industry", "year", "source_url",
    "company", "short_summary", "full_summary",
    "application_tags", "tools_tags", "techniques_tags", "extra_tags", "webflow_url",
]
```
The dataset has many columns. We only keep what we need. This makes the DataFrame
smaller and faster to work with, and makes the code explicit about what it uses.

```python
def load_llmops_data() -> pd.DataFrame:
    dataset = load_dataset(DATASET_NAME, split="train")
    df = dataset.to_pandas()
```
`load_dataset` downloads the dataset from Hugging Face (or uses a local cache if
already downloaded). `split="train"` means we want the training split — this
particular dataset only has one split. `.to_pandas()` converts the Hugging Face
format into a pandas DataFrame, which is easier to work with.

```python
    available = [col for col in COLUMNS_NEEDED if col in df.columns]
    df = df[available].copy()
```
A **list comprehension** that checks which columns in our wanted list actually exist
in the dataset. This prevents crashes if the dataset is updated and a column is
renamed or removed. `.copy()` creates an independent copy so we don't accidentally
modify the original dataset object.

```python
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
```
Converts the `created_at` column from a raw string like `"2026-01-15T10:30:00"`
into a proper Python datetime object with timezone info (UTC). `errors="coerce"`
means: if a date string is malformed, set it to `NaT` (Not a Time) instead of
crashing.

```python
    df = df.dropna(subset=["created_at", "title"])
    df = df.reset_index(drop=True)
```
Removes any row that is missing a date or a title — those rows are useless for a
newsletter. `reset_index` re-numbers the rows from 0 after deletions.

---

### `src/select_items.py` — Step 2: Filter & Score

**Purpose:** Narrow 1,479 articles down to the 15 most relevant ones for this week.

This file has three responsibilities: **time filtering**, **deduplication**, and **scoring**.

#### Time Filtering

```python
cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
weekly = df[df["created_at"] >= cutoff].copy()
```
Gets the current UTC time and subtracts `lookback_days` (e.g. 90 days) to get
a cutoff date. Then filters the DataFrame to only keep rows where `created_at`
is on or after that cutoff. This is the core "freshness" filter.

#### Deduplication

```python
weekly["_title_norm"] = weekly["title"].str.lower().str.strip()
weekly = weekly.drop_duplicates(subset=["_title_norm"])
```
Creates a temporary helper column with the title lowercased and whitespace removed.
Then drops rows with duplicate normalised titles. This handles cases where the same
story is in the dataset twice with slightly different capitalisation.

```python
if "source_url" in weekly.columns:
    weekly = weekly.drop_duplicates(subset=["source_url"])
```
A second deduplication pass by URL. If two entries point to the same article,
only keep the first one.

```python
weekly = weekly.drop(columns=["_title_norm"])
```
Cleans up the temporary helper column — it was only needed for deduplication.

#### Relevance Scoring

```python
HIGH_INTEREST_TERMS = ["agent", "rag", "fine-tun", "benchmark", ...]
TOP_SOURCES = ["openai", "google", "anthropic", "meta", ...]
```
Two curated lists at the top of the file. These are the signals we look for.
They can be updated anytime to tune what the newsletter prioritises.

```python
def _relevance_score(row: pd.Series) -> int:
    score = 0
    text = " ".join(str(row.get(col, "")).lower() for col in [...])
```
Combines all text fields (title, summary, tags) into one long lowercase string.
This makes it easy to search for keywords across all fields at once with a single `in` check.

```python
    if _is_recent(row["created_at"], days=2):
        score += 2
```
Articles published in the last 48 hours get a +2 bonus. Breaking news matters more.

```python
    for term in HIGH_INTEREST_TERMS:
        if term in text:
            score += 1
            break  # count at most once
```
If any high-interest keyword is found anywhere in the article text, add +1.
The `break` is important — it prevents double-counting if multiple keywords match.

```python
    for source in TOP_SOURCES:
        if source in company or source in text:
            score += 1
            break
```
Same pattern for well-known companies. If OpenAI, Google, Meta etc. are mentioned,
the article is more likely to be significant.

```python
weekly["relevance_score"] = weekly.apply(_relevance_score, axis=1)
weekly = weekly.sort_values("relevance_score", ascending=False)
top = weekly.head(MAX_ITEMS).reset_index(drop=True)
```
`apply(_relevance_score, axis=1)` calls the scoring function once per row and
stores the result in a new column. Then we sort by score (highest first) and take
the top 15. This is the entire selection logic — transparent and tunable.

---

### `src/categorize.py` — Step 3: Categorise

**Purpose:** Assign each article to one of three newsletter sections.

```python
SECTION_KEYWORDS = {
    "Research Highlights": ["paper", "research", "benchmark", "evaluation", ...],
    "Industry News":       ["launch", "release", "partnership", "funding", ...],
    "Cool Use Cases":      ["agent", "automat", "deploy", "application", ...],
}
```
A dictionary where each key is a section name and each value is a list of keywords
that signal that section. This is the "brain" of the categoriser — fully transparent
and easy to extend.

```python
def _assign_section(row: pd.Series) -> str:
    text = " ".join(str(row.get(col, "")).lower() for col in [...])
    scores: dict[str, int] = {section: 0 for section in SECTION_KEYWORDS}
    for section, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[section] += 1
```
For each section, counts how many of its keywords appear in the article text.
The section with the **most keyword matches wins**. This is called a
**competitive scoring approach** — simple but effective.

```python
    best_section = max(scores, key=lambda s: scores[s])
    if scores[best_section] == 0:
        return DEFAULT_SECTION
    return best_section
```
`max(..., key=...)` finds the section with the highest count. If nothing matched
at all (count is 0), fall back to "Industry News" as the default.

```python
def categorize_items(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["section"] = df.apply(_assign_section, axis=1)
    return df
```
Applies `_assign_section` to every row and stores the result in a new `section`
column. The rest of the pipeline uses this column to group articles.

---

### `src/summarize.py` — Step 4: Summarise with AI

**Purpose:** Call Azure OpenAI once per article to generate a 2-sentence,
newsletter-ready summary.

```python
from openai import AzureOpenAI
```
The official OpenAI Python SDK. It works with both standard OpenAI and Azure OpenAI
— you just configure it differently.

```python
def _build_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
```
Creates the API client using credentials from environment variables. Credentials
are **never** hardcoded in the source — they come from `.env` locally and from
GitHub Secrets in CI. `os.environ["KEY"]` raises an error if the key is missing
(fast failure), while `os.environ.get("KEY", default)` returns a default value.

#### The Prompt

```python
prompt = f"""You are writing a concise entry for a weekly AI newsletter aimed at Odido's tech team.

Article details:
- Title: {row.get("title", "N/A")}
- Company: {row.get("company", "N/A")}
- Industry: {row.get("industry", "N/A")}
- Tags: {tags}
- Summary: {short_summary}

Write exactly 2 short sentences:
1. What this is about (plain, clear language).
2. Why it could matter for a tech team working on AI products.

Do not use bullet points. Do not add a title. Output only the two sentences."""
```
This is the heart of the LLM usage. Key prompt design decisions:
- **Role**: "You are writing..." sets the context for the model
- **Structured input**: We provide title, company, industry, tags, and summary
- **Explicit output format**: "exactly 2 short sentences" gives the model a clear constraint
- **Negative constraints**: "Do not use bullet points" prevents unwanted formatting
- **Audience**: "Odido's tech team" makes summaries relevant, not generic

```python
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()
```
- `temperature=0.4` — lower temperature means less creative / more consistent output.
  Good for factual summaries.
- `max_tokens=120` — caps the response length. Two sentences should never need more.
- `response.choices[0].message.content` — the actual text the model returned.

```python
def summarize_items(df: pd.DataFrame, delay_seconds: float = 0.5) -> pd.DataFrame:
    ...
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        try:
            summary = _summarize_item(client, row, deployment)
        except Exception as exc:
            summary = str(row.get("title", ""))   # fallback to title
        summaries.append(summary)
        if i < total:
            time.sleep(delay_seconds)
```
Loops through every row. Two important patterns here:
- `try/except` — if the API call fails for one article (network error, rate limit),
  we don't crash the whole pipeline. We use the title as a fallback and continue.
- `time.sleep(delay_seconds)` — a 0.5-second pause between calls to avoid hitting
  the API rate limit. Simple and effective without needing a complex retry library.

---

### `src/render_newsletter.py` — Step 5: Render

**Purpose:** Take the enriched DataFrame and write a formatted Markdown file.

This module also makes two more LLM calls — one for the intro paragraph and one
for the closing note. These are generated fresh each week based on the actual
articles selected.

```python
SECTION_ORDER = ["Research Highlights", "Industry News", "Cool Use Cases"]
```
Defines the order sections appear in the newsletter. Research first, then news,
then use cases. This is a deliberate editorial decision.

```python
    now = datetime.now(timezone.utc)
    week_label = now.strftime("Week of %B %d, %Y")
```
Gets the current date and formats it as a human-readable label like
"Week of April 23, 2026". This appears in the newsletter title.

```python
    lines = []
    lines.append(f"# Odido AI Newsletter — {week_label}\n")
    ...
    markdown = "\n".join(lines)
```
Builds the Markdown document by appending strings to a list, then joining them
at the end. This is more efficient than string concatenation in a loop and keeps
the structure easy to read.

```python
    for section in SECTION_ORDER:
        section_df = df[df["section"] == section]
        if section_df.empty:
            continue
```
Filters the DataFrame to only rows belonging to this section. If a section has
no articles this week, `continue` skips it entirely — the newsletter automatically
adapts to the available content.

```python
        url = row.get("webflow_url", "") or row.get("source_url", "")
        title_md = f"[{title}]({url})" if url else title
```
Prefers the `webflow_url` (the ZenML article page) over the raw `source_url`.
The `or` operator returns the second value if the first is empty. If we have a
URL, the title becomes a Markdown hyperlink `[title](url)`.

```python
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(markdown, encoding="utf-8")
```
`Path.write_text()` is a clean one-liner to write a file. `mkdir(parents=True,
exist_ok=True)` ensures the output folder exists without crashing if it already does.

---

### `index.html` — The Frontend

**Purpose:** A single HTML page that reads `newsletter.md` and renders it as a
beautiful Odido-branded web page.

#### Why a single HTML file?

No framework, no build step, no server-side code. You open one file in a browser
(served by Python's built-in HTTP server) and it works. This is the simplest
possible frontend.

#### Technology choices

- **Vanilla HTML + CSS** — no React, no Vue. Simple and explainable.
- **Inline JavaScript** — all logic is in the `<script>` tag at the bottom.
- **`fetch("newsletter.md")`** — the browser fetches the Markdown file and the
  JavaScript parses it into structured data.
- **No markdown library** — we wrote a custom lightweight parser that extracts
  exactly what we need: title, intro, sections, articles, closing.

#### Odido Brand Colors

```css
:root {
    --odido-magenta: #E2007A;   /* Odido's primary brand pink */
    --odido-purple:  #3D0050;   /* Deep purple used in gradients */
    --odido-light:   #FFF0F7;   /* Very light pink for backgrounds */
}
```
CSS custom properties (variables) defined at the `:root` level. Used everywhere
in the stylesheet so the brand colours are consistent and easy to update.

#### How the JavaScript works

```javascript
async function loadNewsletter() {
    const res = await fetch("newsletter.md");
    return res.text();
}
```
`fetch()` is the browser's built-in HTTP client. `async/await` makes the
asynchronous call read like synchronous code — wait for the file, then continue.

```javascript
function parseNewsletter(md) { ... }
```
A custom Markdown parser that reads the file line by line and extracts:
- H1 (`# ...`) → newsletter title and date
- H2 (`## ...`) → section names or intro/closing markers
- H3 (`### ...`) → individual article titles (with optional links)
- Italic lines → article metadata (company + date)
- Other lines → article summary text

```javascript
function renderNewsletter(data) {
    let html = "";
    for (const section of data.sections) { ... }
    container.innerHTML = html;
}
```
Builds an HTML string from the parsed data and injects it into the page with
`innerHTML`. Each article becomes a `<div class="article-card">` with hover effects.

```javascript
loadNewsletter()
    .then(md => renderNewsletter(parseNewsletter(md)))
    .catch(err => { ... });
```
The boot sequence: load → parse → render. If anything fails, display a clear error
message on screen.

---

### `.github/workflows/weekly_newsletter.yml` — Automation

**Purpose:** Run the pipeline automatically every Monday without any manual work.

```yaml
on:
  schedule:
    - cron: "0 8 * * 1"
```
This is a **cron expression** — a standard Unix format for scheduling.
- `0` = minute 0
- `8` = hour 8 (UTC)
- `*` = any day of month
- `*` = any month
- `1` = Monday (1=Mon, 2=Tue, ... 7=Sun)

Translation: "Run at 08:00 UTC every Monday" — which is 10:00 Amsterdam time.

```yaml
  workflow_dispatch:
    inputs:
      lookback_days:
        description: "How many days back to look for articles"
        default: "7"
```
`workflow_dispatch` adds a "Run workflow" button in the GitHub Actions UI. This
lets you trigger it manually anytime — useful for testing or generating a newsletter
on demand.

```yaml
jobs:
  generate-newsletter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: pip install -r requirements.txt
```
GitHub spins up a fresh Ubuntu virtual machine. It then:
1. Checks out the code from the repository
2. Installs Python 3.11 (with pip caching to speed up future runs)
3. Installs all dependencies from `requirements.txt`

```yaml
      - name: Run newsletter pipeline
        env:
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          ...
        run: python run_pipeline.py --lookback-days 90 --output newsletter.md
```
The `env:` block injects the GitHub repository secrets as environment variables.
`${{ secrets.SECRET_NAME }}` is GitHub Actions syntax for reading a secret.
The pipeline never sees the raw credentials — GitHub handles the injection securely.

```yaml
      - name: Commit and push newsletter
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add newsletter.md
          git diff --cached --quiet || git commit -m "chore: weekly newsletter $(date +'%Y-%m-%d')"
          git push
```
After the pipeline runs, the bot commits the new `newsletter.md` back to the
repository automatically. `git diff --cached --quiet || git commit ...` means:
"if there are changes staged, commit them — otherwise do nothing." This prevents
an empty commit when the newsletter hasn't changed.

---

### `requirements.txt` & `.env` — Config Files

#### `requirements.txt`
```
datasets>=2.19.0      # Hugging Face data loading
pandas>=2.2.0         # DataFrame operations
openai>=1.30.0        # Azure OpenAI API client
python-dotenv>=1.0.0  # Load .env file into environment variables
```
Four dependencies. Deliberately minimal — no heavy ML frameworks, no web server,
no database. Every dependency has a direct purpose.

#### `.env` (local only, never committed)
```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2023-12-01-preview
```
Secrets live here locally. The `.gitignore` file ensures `.env` is never pushed
to GitHub. In GitHub Actions, these same values are stored as repository Secrets
and injected at runtime.

---

## 5. Key Design Decisions

These are the "why" answers — the ones interviewers love.

| Decision | Why |
|---|---|
| **One file per pipeline step** | Separation of concerns. Each module has one job. Easy to test and explain. |
| **pandas DataFrame throughout** | Consistent data structure across all steps. No conversions needed between modules. |
| **Rule-based scoring & categorisation** | No black box. Every decision is explainable. Easy to tune by editing keyword lists. |
| **One LLM call per article** | Predictable cost and token usage. Easy to debug individual outputs. |
| **Fallback on LLM failure** | The pipeline never crashes because of one bad API call. Resilient by design. |
| **`time.sleep()` between calls** | Respects rate limits without a complex retry library. Simple and sufficient. |
| **`load_dotenv()` for secrets** | Credentials never hardcoded. Works locally via `.env`, works in CI via Secrets. |
| **Single HTML file frontend** | No build step, no framework, no complexity. Serves directly from Python's HTTP server. |
| **GitHub Actions cron** | Zero infrastructure. No server to maintain. Runs on GitHub's machines for free. |
| **`git diff --cached --quiet || git commit`** | Idempotent — the bot only commits when there is actually new content. |

---

## 6. How to Run the Application

### First-time setup (do this once)

```powershell
# 1. Go to the project folder
cd c:\Users\himan\OneDrive\Desktop\Odido

# 2. Create the virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\activate

# 4. Install dependencies (all packages go inside .venv, not your system Python)
pip install -r requirements.txt

# 5. Copy the credentials template and fill in your values
copy .env.example .env
# Then open .env and add your Azure OpenAI key, endpoint, and deployment name
```

### Run the pipeline (generate a new newsletter)

```powershell
# Make sure the virtual environment is active (you'll see (.venv) in the prompt)
.\.venv\Scripts\activate

# Run with 90-day lookback (recommended for this dataset)
python run_pipeline.py --lookback-days 90 --output newsletter.md
```

You will see output like:
```
============================================================
  Odido AI Newsletter Pipeline
============================================================

[Step 1/5] Loading dataset from Hugging Face...
Loaded 1479 records.

[Step 2/5] Selecting items from the last 90 days...
Items published in last 90 days: 54
After deduplication: 53 items
Selected top 15 items for the newsletter.

[Step 3/5] Categorising items into sections...
Categorization complete: {'Cool Use Cases': 10, 'Industry News': 4, 'Research Highlights': 1}

[Step 4/5] Generating summaries with Azure OpenAI...
  Summarising item 1/15: ...
  ...

[Step 5/5] Rendering newsletter to 'newsletter.md'...
Done! Newsletter saved to: C:\Users\himan\OneDrive\Desktop\Odido\newsletter.md
```

### View the newsletter in the browser (frontend)

```powershell
# In the same terminal (venv still active), start the local web server
python -m http.server 8080
```

Then open your browser and go to:
```
http://localhost:8080
```

You will see the Odido-branded newsletter UI with all articles rendered in cards.

To stop the server, press `Ctrl + C` in the terminal.

### Run with custom options

```powershell
# Look back 14 days instead of 90
python run_pipeline.py --lookback-days 14

# Save the newsletter to a different file
python run_pipeline.py --output archive/newsletter-2026-04-23.md

# Both at once
python run_pipeline.py --lookback-days 30 --output my-newsletter.md
```

### What happens automatically in GitHub Actions (once repo is set up)

1. Every Monday at 08:00 UTC, GitHub spins up a virtual machine
2. It installs Python and all dependencies
3. It runs `python run_pipeline.py --lookback-days 90`
4. It commits the updated `newsletter.md` back to the repository
5. You wake up Monday morning to a fresh newsletter already in the repo

No manual work needed after the initial setup.

---

*This document was generated for the Odido AI Newsletter assignment — April 2026.*
