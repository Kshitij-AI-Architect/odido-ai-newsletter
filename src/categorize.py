"""
categorize.py
-------------
Assigns each item to one of three newsletter sections using simple
keyword rules.  No ML model needed – this is intentionally transparent
and easy to explain.

Sections:
  - Research Highlights  – academic / benchmark / model paper content
  - Industry News        – company announcements, products, partnerships
  - Cool Use Cases       – applied AI, product demos, real-world deployments
"""

import pandas as pd


# Keywords that map to each section (checked against title + use_case + tags)
SECTION_KEYWORDS = {
    "Research Highlights": [
        "paper", "research", "study", "benchmark", "evaluation", "model",
        "arxiv", "dataset", "training", "fine-tun", "rlhf", "reasoning",
        "alignment", "preprint", "experiment",
    ],
    "Industry News": [
        "launch", "release", "partnership", "funding", "raises", "acqui",
        "announce", "product", "company", "startup", "investment", "enterprise",
        "api", "platform", "service",
    ],
    "Cool Use Cases": [
        "agent", "automat", "deploy", "application", "workflow", "use case",
        "solution", "integrat", "tool", "assistant", "copilot", "chatbot",
        "demo", "real-world", "production",
    ],
}

DEFAULT_SECTION = "Industry News"


def _assign_section(row: pd.Series) -> str:
    text = " ".join(
        str(row.get(col, "")).lower()
        for col in ["title", "short_summary", "application_tags", "tools_tags", "techniques_tags", "industry"]
    )

    scores: dict[str, int] = {section: 0 for section in SECTION_KEYWORDS}
    for section, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[section] += 1

    best_section = max(scores, key=lambda s: scores[s])
    # If nothing matched, use the default
    if scores[best_section] == 0:
        return DEFAULT_SECTION
    return best_section


def categorize_items(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'section' column to the DataFrame and returns items
    grouped so the newsletter can render them section by section.
    """
    df = df.copy()
    df["section"] = df.apply(_assign_section, axis=1)

    section_counts = df["section"].value_counts().to_dict()
    print(f"Categorization complete: {section_counts}")
    return df
