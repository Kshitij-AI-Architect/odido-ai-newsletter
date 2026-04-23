"""
load_data.py
------------
Loads the zenml/llmops-database dataset from Hugging Face and returns
a clean pandas DataFrame with only the columns we need.
"""

import pandas as pd
from datasets import load_dataset


DATASET_NAME = "zenml/llmops-database"

COLUMNS_NEEDED = [
    "created_at",
    "title",
    "industry",
    "year",
    "source_url",
    "company",
    "short_summary",
    "full_summary",
    "application_tags",
    "tools_tags",
    "techniques_tags",
    "extra_tags",
    "webflow_url",
]


def load_llmops_data() -> pd.DataFrame:
    """
    Downloads the dataset from Hugging Face and returns a DataFrame.
    Only the columns defined in COLUMNS_NEEDED are kept (if they exist).
    """
    print(f"Loading dataset: {DATASET_NAME}")
    dataset = load_dataset(DATASET_NAME, split="train")
    df = dataset.to_pandas()

    # Keep only columns that actually exist in the dataset
    available = [col for col in COLUMNS_NEEDED if col in df.columns]
    df = df[available].copy()

    # Normalise the created_at column to timezone-aware UTC datetime
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")

    # Drop rows where we have no date or no title
    df = df.dropna(subset=["created_at", "title"])
    df = df.reset_index(drop=True)

    print(f"Loaded {len(df)} records.")
    return df
