"""
judge.py
--------
LLM-as-a-Judge evaluation step.

Uses an open-source model (Llama 3 via Groq's free API) to rate each
generated summary on two dimensions:

  - Faithfulness (1-5): Does the summary stick to facts in the source?
                        Does it hallucinate anything?
  - Clarity     (1-5): Is it clear, concise and easy to read?

Why a separate (open-source) model as judge?
  Using a different model than the one that generated the summaries
  avoids self-evaluation bias — it is a neutral third-party check.
  This is the standard "LLM-as-a-Judge" pattern used in production
  AI evaluation pipelines (e.g. MT-Bench, RAGAS, LangSmith).

Groq is used because:
  - It provides free API access to open-source models (Llama 3, Mixtral)
  - Its API is OpenAI-compatible, so no new SDK is required
  - Response time is very fast (low latency inference)

If GROQ_API_KEY is not set, the step is skipped gracefully and
default neutral scores are assigned so the pipeline never crashes.
"""

import os
import time

import pandas as pd
from openai import OpenAI


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
JUDGE_MODEL = "llama-3.3-70b-versatile"   # free, strong reasoning model on Groq

# Score labels used in the newsletter output
SCORE_LABELS = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}


def _build_judge_client() -> OpenAI | None:
    """
    Returns a Groq-backed OpenAI client if GROQ_API_KEY is set,
    otherwise returns None (judge step will be skipped).
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("  GROQ_API_KEY not set — skipping LLM-as-a-Judge evaluation.")
        return None
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)


def _judge_summary(client: OpenAI, source: str, summary: str, title: str) -> dict:
    """
    Asks the judge model to score a single summary.
    Returns a dict with keys: faithfulness (int), clarity (int).
    """
    prompt = f"""You are an expert AI newsletter quality evaluator. Your job is to judge whether an AI-generated summary is accurate and well-written.

Article title: {title}

Original source text:
\"\"\"{source[:500]}\"\"\"

AI-generated summary:
\"\"\"{summary}\"\"\"

Score the summary on BOTH dimensions below. Use only integers 1-5.

Faithfulness (1-5):
  5 = every fact in the summary is present in the source, nothing invented
  3 = mostly faithful, minor liberties taken
  1 = significant hallucination or invented facts

Clarity (1-5):
  5 = extremely clear, concise, professional
  3 = readable but could be improved
  1 = confusing or poorly written

Reply in EXACTLY this format (no other text):
Faithfulness: X
Clarity: X"""

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=20,
    )

    text = response.choices[0].message.content.strip()
    faithfulness = int(text.split("Faithfulness:")[1].split("\n")[0].strip())
    clarity = int(text.split("Clarity:")[1].strip())
    return {"faithfulness": faithfulness, "clarity": clarity}


def judge_summaries(df: pd.DataFrame, delay_seconds: float = 0.3) -> pd.DataFrame:
    """
    Runs LLM-as-a-Judge evaluation over all rows.

    Adds three new columns to the DataFrame:
      - faithfulness_score  (int 1-5)
      - clarity_score       (int 1-5)
      - quality_label       (str, e.g. "⭐⭐⭐⭐ | Clarity: ⭐⭐⭐⭐⭐")

    If Groq is unavailable, assigns neutral scores (3) and continues.
    """
    client = _build_judge_client()

    faithfulness_scores = []
    clarity_scores = []
    total = len(df)

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        title = row.get("title", "")[:60]
        print(f"  Judging item {i}/{total}: {title}...")

        if client is None:
            # Graceful skip — neutral score
            faithfulness_scores.append(3)
            clarity_scores.append(3)
            continue

        try:
            scores = _judge_summary(
                client=client,
                source=str(row.get("short_summary", "")),
                summary=str(row.get("summary", "")),
                title=str(row.get("title", "")),
            )
            faithfulness_scores.append(scores["faithfulness"])
            clarity_scores.append(scores["clarity"])
        except Exception as exc:
            print(f"    Warning: judge call failed ({exc}). Assigning neutral score.")
            faithfulness_scores.append(3)
            clarity_scores.append(3)

        if i < total:
            time.sleep(delay_seconds)

    df = df.copy()
    df["faithfulness_score"] = faithfulness_scores
    df["clarity_score"] = clarity_scores

    # Human-readable quality label for newsletter rendering
    df["quality_label"] = df.apply(
        lambda r: (
            f"Faithfulness {SCORE_LABELS[r['faithfulness_score']]}  "
            f"Clarity {SCORE_LABELS[r['clarity_score']]}"
        ),
        axis=1,
    )

    avg_f = df["faithfulness_score"].mean()
    avg_c = df["clarity_score"].mean()
    print(f"\n  Judge results — Avg Faithfulness: {avg_f:.1f}/5 | Avg Clarity: {avg_c:.1f}/5")

    return df
