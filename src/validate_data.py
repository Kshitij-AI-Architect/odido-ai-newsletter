"""
validate_data.py
----------------
Validates every row of the incoming dataset against a defined schema
using Pydantic before it enters the pipeline.

Why this matters:
  The dataset comes from an external source (Hugging Face). If the dataset
  owner renames a column, changes a data type, or introduces bad rows,
  the pipeline would silently produce empty or wrong summaries without this check.

  Pydantic lets us define exactly what a valid article row looks like.
  Any row that does not match is logged and skipped — the pipeline
  continues cleanly with only valid data.

This is called a "data contract" — a formal agreement between the data
source and the pipeline about what the data should look like.
"""

from typing import Optional

import pandas as pd
from pydantic import BaseModel, field_validator


class ArticleRow(BaseModel):
    """
    Defines what a valid article row must contain.
    Optional fields are allowed to be empty or missing — only
    title and created_at are strictly required.
    """

    title: str
    created_at: str
    company: Optional[str] = ""
    industry: Optional[str] = ""
    short_summary: Optional[str] = ""
    source_url: Optional[str] = ""
    webflow_url: Optional[str] = ""
    application_tags: Optional[str] = ""
    tools_tags: Optional[str] = ""
    techniques_tags: Optional[str] = ""

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Title is the most important field — reject blank titles."""
        if not v.strip():
            raise ValueError("title is empty or whitespace only")
        return v.strip()

    @field_validator("created_at")
    @classmethod
    def created_at_must_not_be_empty(cls, v: str) -> str:
        """Without a date we cannot filter by week."""
        if not v.strip():
            raise ValueError("created_at is empty")
        return v.strip()


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Runs every row through the ArticleRow schema.

    - Rows that pass validation are kept.
    - Rows that fail are logged with the reason and skipped.
    - The cleaned DataFrame (valid rows only) is returned.

    This ensures the rest of the pipeline only ever sees clean,
    well-formed data — regardless of what changed upstream.
    """
    valid_rows = []
    invalid_count = 0

    for _, row in df.iterrows():
        try:
            # Convert row to dict, replace NaN with empty string for optional fields
            row_dict = {
                k: ("" if pd.isna(v) else str(v))
                for k, v in row.items()
            }
            ArticleRow(**row_dict)
            valid_rows.append(row)
        except Exception as exc:
            invalid_count += 1
            title_preview = str(row.get("title", "unknown"))[:50]
            print(f"  [Validation] Skipping row '{title_preview}': {exc}")

    result = pd.DataFrame(valid_rows).reset_index(drop=True)
    print(
        f"Validation complete: {len(result)} valid rows kept, "
        f"{invalid_count} invalid rows skipped."
    )
    return result
