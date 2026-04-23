"""
select_items.py
---------------
Filters the full dataset down to the most relevant items for the current
week, removes duplicates, and assigns a simple relevance score so we can
pick the best articles to include in the newsletter.
"""

from datetime import datetime, timezone, timedelta

import pandas as pd


# Buzzwords that signal high relevance for an AI/LLM newsletter
HIGH_INTEREST_TERMS = [
    "agent", "agents", "rag", "fine-tun", "benchmark", "release",
    "open-source", "multimodal", "llm", "gpt", "claude", "gemini",
    "mistral", "reasoning", "evaluation", "tool use", "autonomous",
]

# Top companies/sources that carry extra signal
TOP_SOURCES = [
    "openai", "google", "anthropic", "meta", "microsoft", "mistral",
    "hugging face", "deepmind", "nvidia", "cohere", "amazon",
]

# Maximum number of items to include in the newsletter
MAX_ITEMS = 15


def _is_recent(dt: pd.Timestamp, days: int) -> bool:
    now = datetime.now(timezone.utc)
    return (now - dt).days <= days


def _relevance_score(row: pd.Series) -> int:
    """
    Simple additive scoring – easy to explain and easy to tune.
    Max possible score is ~6.
    """
    score = 0
    text = " ".join(
        str(row.get(col, "")).lower()
        for col in ["title", "short_summary", "application_tags", "tools_tags", "techniques_tags"]
    )
    company = str(row.get("company", "")).lower()

    # Recency bonus: published in last 48 hours
    if _is_recent(row["created_at"], days=2):
        score += 2

    # High-interest keyword present in title / content
    for term in HIGH_INTEREST_TERMS:
        if term in text:
            score += 1
            break  # count at most once

    # Comes from a well-known AI company
    for source in TOP_SOURCES:
        if source in company or source in text:
            score += 1
            break

    return score


def select_weekly_items(df: pd.DataFrame, lookback_days: int = 7) -> pd.DataFrame:
    """
    1. Filters to items published within `lookback_days`.
    2. Deduplicates by normalised title and source_url.
    3. Scores each item for relevance.
    4. Returns the top MAX_ITEMS rows, sorted by score descending.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    weekly = df[df["created_at"] >= cutoff].copy()
    print(f"Items published in last {lookback_days} days: {len(weekly)}")

    # --- Deduplication ---
    # Normalise title (lowercase, strip whitespace)
    weekly["_title_norm"] = weekly["title"].str.lower().str.strip()
    weekly = weekly.drop_duplicates(subset=["_title_norm"])

    # Deduplicate by source URL if the column exists
    if "source_url" in weekly.columns:
        weekly = weekly.drop_duplicates(subset=["source_url"])

    weekly = weekly.drop(columns=["_title_norm"])
    print(f"After deduplication: {len(weekly)} items")

    if weekly.empty:
        print("No items found for this period.")
        return weekly

    # --- Scoring ---
    weekly["relevance_score"] = weekly.apply(_relevance_score, axis=1).astype(int)
    weekly = weekly.sort_values("relevance_score", ascending=False)

    top = weekly.head(MAX_ITEMS).reset_index(drop=True)
    print(f"Selected top {len(top)} items for the newsletter.")
    return top
