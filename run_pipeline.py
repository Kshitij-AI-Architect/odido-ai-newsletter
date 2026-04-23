"""
run_pipeline.py
---------------
Main entry point for the Odido AI Newsletter pipeline.

Steps
-----
1. load_data      – Download & clean the Hugging Face dataset
2. select_items   – Filter to the current week, deduplicate, score
3. categorize     – Assign each item to a newsletter section
4. summarize      – Generate concise summaries via Azure OpenAI
5. render         – Build and write the Markdown newsletter

Usage
-----
    python run_pipeline.py [--lookback-days N] [--output newsletter.md]

Environment variables required (set in .env or CI secrets):
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_DEPLOYMENT
    AZURE_OPENAI_API_VERSION  (optional, default: 2024-02-01)
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file for local development (no-op in CI where secrets are injected)
load_dotenv()

from src.load_data import load_llmops_data
from src.validate_data import validate_dataframe
from src.select_items import select_weekly_items
from src.categorize import categorize_items
from src.summarize import summarize_items
from src.judge import judge_summaries
from src.render_newsletter import render_newsletter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Odido AI Newsletter Generator")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="How many days back to look for fresh articles (default: 7)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="newsletter.md",
        help="Output file path for the newsletter (default: newsletter.md)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("  Odido AI Newsletter Pipeline")
    print("=" * 60)

    # Step 1 – Ingest
    print("\n[Step 1/5] Loading dataset from Hugging Face...")
    df = load_llmops_data()

    # Step 1b – Validate schema (data contract check)
    print("\n[Step 1b/5] Validating dataset schema...")
    df = validate_dataframe(df)

    # Step 2 – Filter & score
    print(f"\n[Step 2/5] Selecting items from the last {args.lookback_days} days...")
    df = select_weekly_items(df, lookback_days=args.lookback_days)

    if df.empty:
        print("\nNo new items found for this period. Newsletter not generated.")
        sys.exit(0)

    # Step 3 – Categorise
    print("\n[Step 3/5] Categorising items into sections...")
    df = categorize_items(df)

    # Step 4 – Summarise
    print("\n[Step 4/5] Generating summaries with Azure OpenAI...")
    df = summarize_items(df)

    # Step 4b – LLM-as-a-Judge evaluation (open-source Llama 3 via Groq)
    print("\n[Step 4b/5] Running LLM-as-a-Judge quality evaluation...")
    df = judge_summaries(df)

    # Step 5 – Render
    print(f"\n[Step 5/5] Rendering newsletter to '{args.output}'...")
    render_newsletter(df, output_path=args.output)

    print("\n" + "=" * 60)
    print(f"  Done! Newsletter saved to: {Path(args.output).resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
