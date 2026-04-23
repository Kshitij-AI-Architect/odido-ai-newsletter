"""
summarize.py
------------
Uses Azure OpenAI to generate concise, newsletter-friendly summaries
for each article.  One API call per article keeps the logic simple
and the prompts easy to inspect.
"""

import os
import time

import pandas as pd
from openai import AzureOpenAI


def _build_client() -> AzureOpenAI:
    """Initialise the Azure OpenAI client from environment variables."""
    return AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )


def _summarize_item(client: AzureOpenAI, row: pd.Series, deployment: str) -> str:
    """
    Sends a single article to Azure OpenAI and returns a two-sentence summary:
    - Line 1: What happened / what it is.
    - Line 2: Why it matters for an AI team like Odido's.
    """
    short_summary = str(row.get("short_summary", ""))[:600]
    tags = ", ".join(filter(None, [
        str(row.get("application_tags", "")),
        str(row.get("tools_tags", "")),
        str(row.get("techniques_tags", "")),
    ]))[:300]

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

    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()


def summarize_items(df: pd.DataFrame, delay_seconds: float = 0.5) -> pd.DataFrame:
    """
    Iterates over all selected items, calls Azure OpenAI for each,
    and stores the result in a new 'summary' column.

    `delay_seconds` adds a small pause between API calls to respect
    rate limits without needing a full retry library.
    """
    client = _build_client()
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    summaries = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        print(f"  Summarising item {i}/{total}: {row['title'][:60]}...")
        try:
            summary = _summarize_item(client, row, deployment)
        except Exception as exc:
            print(f"    Warning: API call failed ({exc}). Using title as fallback.")
            summary = str(row.get("title", ""))
        summaries.append(summary)
        if i < total:
            time.sleep(delay_seconds)

    df = df.copy()
    df["summary"] = summaries
    return df
