# Code Walkthrough — Odido AI Newsletter Pipeline

This document explains the entire codebase in plain, simple language.
No jargon. Written so anyone can understand it and explain it confidently.

---

## The Big Idea (in one paragraph)

Every week, there are hundreds of AI news articles published across the internet.
Reading all of them is impossible. So we built a pipeline that does it automatically —
it downloads a curated list of AI articles, picks the best 15, asks an AI to summarise
each one in 2 sentences, asks a second AI to check the quality, and then produces a
neat newsletter file. All of this runs automatically every Monday.

---

## The 6 Files That Make It Work

```
run_pipeline.py          ← Start here. This runs everything in order.
src/load_data.py         ← Step 1: Download the articles
src/select_items.py      ← Step 2: Pick the best ones
src/categorize.py        ← Step 3: Sort them into categories
src/summarize.py         ← Step 4: Summarise each article with AI
src/judge.py             ← Step 4b: A second AI checks the quality
src/render_newsletter.py ← Step 5: Write the final newsletter file
```

---

## File 1: `run_pipeline.py` — The Boss

Think of this file as the manager that tells each worker what to do and in what order.
It does not do any work itself — it just calls the other files one by one.

```python
load_dotenv()
```
This reads your `.env` file and loads your API keys into memory so the rest of the
code can use them. Without this line, the code would not know your Azure OpenAI key.

```python
df = load_llmops_data()
df = select_weekly_items(df, lookback_days=args.lookback_days)
df = categorize_items(df)
df = summarize_items(df)
df = judge_summaries(df)
render_newsletter(df, output_path=args.output)
```
Each line calls one step of the pipeline and passes the result to the next step.
`df` stands for DataFrame — think of it as a spreadsheet that travels through the
pipeline and gets richer at each step.

```python
parser.add_argument("--lookback-days", type=int, default=7)
parser.add_argument("--output", type=str, default="newsletter.md")
```
These lines let you customise the pipeline from the terminal without changing the code.
For example: `python run_pipeline.py --lookback-days 90` looks back 90 days instead of 7.

---

## File 2: `src/load_data.py` — Download the Articles

This file connects to Hugging Face (a website that hosts AI datasets) and downloads
a list of 1,479 AI/LLM articles.

```python
dataset = load_dataset("zenml/llmops-database", split="train")
df = dataset.to_pandas()
```
`load_dataset` downloads the data from the internet (or uses a local cache if already
downloaded). `.to_pandas()` converts it into a spreadsheet-like structure we can
filter and sort.

```python
available = [col for col in COLUMNS_NEEDED if col in df.columns]
df = df[available].copy()
```
The dataset has many columns. We only keep the ones we actually use — like title,
company, date, and summary. This keeps things clean and simple.

```python
df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df = df.dropna(subset=["created_at", "title"])
```
We convert the date column into a proper date format so we can filter by date later.
Any row with a missing date or title is removed — those rows are useless for a newsletter.

---

## File 3: `src/select_items.py` — Pick the Best Articles

We have 1,479 articles but only want the 15 best ones for this week. This file
does three things: filters by date, removes duplicates, and scores each article.

### Step A — Filter by date
```python
cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
weekly = df[df["created_at"] >= cutoff].copy()
```
This calculates a cutoff date (e.g. 90 days ago) and keeps only articles published
after that date. Everything older is ignored.

### Step B — Remove duplicates
```python
weekly["_title_norm"] = weekly["title"].str.lower().str.strip()
weekly = weekly.drop_duplicates(subset=["_title_norm"])
weekly = weekly.drop_duplicates(subset=["source_url"])
```
Sometimes the same story appears twice with slightly different titles or from the same URL.
We normalise (lowercase + trim) the title and remove exact URL matches to avoid
the same article appearing twice in the newsletter.

### Step C — Score each article
```python
HIGH_INTEREST_TERMS = ["agent", "rag", "benchmark", "llm", "gpt", ...]
TOP_SOURCES = ["openai", "google", "anthropic", "meta", ...]
```
We give each article a relevance score (like rating it out of 5):
- +2 if it was published in the last 48 hours (very fresh)
- +1 if the title or text contains a high-interest AI keyword
- +1 if it comes from a well-known AI company

Then we sort by score and pick the top 15. This is fully transparent — you can
see exactly why any article was picked or rejected.

---

## File 4: `src/categorize.py` — Sort into Sections

The newsletter has 3 sections. This file decides which section each article belongs to.

```python
SECTION_KEYWORDS = {
    "Research Highlights": ["paper", "benchmark", "evaluation", "training", ...],
    "Industry News":       ["launch", "release", "funding", "partnership", ...],
    "Cool Use Cases":      ["agent", "deploy", "application", "workflow", ...],
}
```
These are keyword lists — like labels for each category. For each article, we count
how many keywords from each section appear in the text. The section with the most
matches wins.

```python
best_section = max(scores, key=lambda s: scores[s])
```
This picks the section with the highest keyword count. If nothing matched at all,
the article goes into "Industry News" as the default.

No AI is used here — just simple word matching. This is intentional — it is fast,
free, and easy to explain and adjust.

---

## File 5: `src/summarize.py` — AI Writes the Summaries

This is where Azure OpenAI (GPT-4o) is used. For each article, we send a prompt
to the model and get back a 2-sentence summary.

```python
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    ...
)
```
This creates a connection to Azure OpenAI using the credentials from our `.env` file.
The API key is never hardcoded in the source code — it comes from environment variables.

### The Prompt
```
You are writing a concise entry for a weekly AI newsletter aimed at Odido's tech team.

Article details:
- Title: ...
- Company: ...
- Tags: ...
- Summary: ...

Write exactly 2 short sentences:
1. What this is about (plain, clear language).
2. Why it could matter for a tech team working on AI products.
```
The prompt tells the model who it is, what it is doing, what input it has, and
exactly what format to output. The more specific the instructions, the better
and more consistent the output.

```python
temperature=0.4,
max_tokens=120,
```
- `temperature=0.4` — lower means less creative, more consistent and factual. Good for summaries.
- `max_tokens=120` — hard cap on response length. Two sentences should never need more.

```python
try:
    summary = _summarize_item(client, row, deployment)
except Exception as exc:
    summary = str(row.get("title", ""))
```
If the API call fails for any article (e.g. network error), we do not crash the
whole pipeline. We simply use the article title as a fallback and move on.

```python
time.sleep(delay_seconds)
```
A small pause between API calls to avoid hitting Groq's or Azure's rate limits.
Simple and effective — no complex retry library needed.

---

## File 6: `src/judge.py` — A Second AI Checks the Quality

This is the LLM-as-a-Judge step. After GPT-4o writes the summaries, a completely
different AI model (Llama 3, running on Groq's free platform) reads each summary
and scores it.

### Why use a different model as judge?
If you ask GPT-4o to rate its own output, it tends to give itself high scores.
Using a separate model (Llama 3) as the judge removes this bias. It is like having
a second person proofread your work instead of proofreading it yourself.

```python
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
JUDGE_MODEL = "llama-3.3-70b-versatile"
```
Groq is a platform that runs open-source AI models for free. We point the standard
OpenAI SDK to Groq's URL — no new library needed, just a different endpoint.

### The Judge Prompt
```
Score the summary on BOTH dimensions:

Faithfulness (1-5):
  5 = every fact in the summary is from the source, nothing invented
  1 = significant hallucination or invented facts

Clarity (1-5):
  5 = extremely clear, concise, professional
  1 = confusing or poorly written

Reply in EXACTLY this format:
Faithfulness: X
Clarity: X
```
We ask for a very strict, rigid output format so we can parse the scores reliably.
`temperature=0` means the model gives the same answer every time for the same input
— no randomness, pure evaluation.

```python
api_key = os.environ.get("GROQ_API_KEY", "")
if not api_key:
    print("GROQ_API_KEY not set — skipping judge step.")
    return None
```
If the Groq key is not set, the judge step is silently skipped. The rest of the
pipeline continues normally. This means the app never crashes because of a missing key.

---

## File 7: `src/render_newsletter.py` — Write the Newsletter

This file takes everything we have built up in the spreadsheet and turns it into
a formatted Markdown document.

```python
week_label = now.strftime("Week of %B %d, %Y")
```
Gets the current date and formats it as a human-readable label like "Week of April 23, 2026".

```python
intro = _generate_intro(client, deployment, week_label, df["title"].tolist())
closing = _generate_closing(client, deployment)
```
Two more GPT-4o calls — one to write a short intro paragraph based on this week's
article titles, and one to write a warm closing note. These make the newsletter feel
hand-written, not robotic.

```python
for section in SECTION_ORDER:
    section_df = df[df["section"] == section]
    if section_df.empty:
        continue
```
Loops through each section. If a section has no articles this week, it is skipped
automatically — the newsletter adapts to whatever content is available.

```python
quality_label = row.get("quality_label", "")
if quality_label:
    lines.append(f"> 🤖 **AI Judge:** {quality_label}\n")
```
If judge scores exist, they are added under each article as a blockquote line.
This shows up in both the Markdown file and the browser frontend.

```python
output_file.write_text(markdown, encoding="utf-8")
```
Saves the final newsletter as a `.md` file. One clean line — done.

---

## The GitHub Actions Workflow — Automatic Weekly Run

```yaml
on:
  schedule:
    - cron: "0 8 * * 1"
```
This is a cron expression — a standard way to schedule jobs. It means: run every
Monday at 08:00 UTC (10:00 Amsterdam time). No server needed — GitHub runs it
on their own machines.

```yaml
LOOKBACK_DAYS: ${{ github.event.inputs.lookback_days || 90 }}
```
When run automatically (scheduled), this defaults to 90 days. When triggered
manually from GitHub's UI, you can type a different number.

```yaml
git add newsletter.md
git diff --cached --quiet || git commit -m "newsletter: weekly update $(date)"
git push
```
After the pipeline runs, the updated `newsletter.md` is committed back to the
repository automatically. The `||` means "only commit if there are actually changes"
— so no empty commits are created.

---

## The Frontend — `index.html`

A single HTML file that reads `newsletter.md` from the same folder and displays
it as a beautiful web page in Odido's brand colours (magenta and purple).

No framework, no build step. Just HTML, CSS, and plain JavaScript.

```javascript
async function loadNewsletter() {
    const res = await fetch("newsletter.md");
    return res.text();
}
```
The browser fetches the Markdown file, just like loading any web page. Then
JavaScript parses it line by line and builds HTML cards for each article.

Each article card shows:
- Title (as a clickable link)
- Company and date
- AI-generated summary
- AI Judge scores (if available) as a small badge at the bottom

---

## How to Run It (Quick Reference)

```powershell
# 1. Activate the virtual environment
cd c:\Users\himan\OneDrive\Desktop\Odido
.\.venv\Scripts\activate

# 2. Generate the newsletter
python run_pipeline.py --lookback-days 90 --output newsletter.md

# 3. View it in the browser (open a new terminal tab)
python -m http.server 8080
# Then open: http://localhost:8080
```

---

## Credentials Needed

| Key | What it does | Where to get it |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | Calls GPT-4o for summaries + intro/closing | Azure Portal |
| `AZURE_OPENAI_ENDPOINT` | Points to your Azure resource | Azure Portal |
| `AZURE_OPENAI_DEPLOYMENT` | Name of your deployed model (e.g. gpt-4o) | Azure Portal |
| `AZURE_OPENAI_API_VERSION` | API version string | Azure docs |
| `GROQ_API_KEY` | Calls Llama 3 for quality scoring (free) | console.groq.com |

---

*Written for the Odido AI Newsletter assignment — April 2026.*
