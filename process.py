"""
Process scraped HTML files into Markdown.

Reads from html_canada/<code>.html, writes to pages_canada/<code>.md.

Usage:
    uv run python process.py              # process all HTML files
    uv run python process.py --force      # re-process even if .md exists
"""

import argparse
import json
import os
from parse_detail import parse_statcan_page


def main():
    parser = argparse.ArgumentParser(description="Convert HTML to Markdown")
    parser.add_argument("--force", action="store_true", help="Re-process even if .md exists")
    args = parser.parse_args()

    os.makedirs("pages_canada", exist_ok=True)

    # Load master list for ordering/metadata
    with open("occupations_canada.json") as f:
        occupations = json.load(f)

    processed = 0
    skipped = 0
    missing = 0

    for occ in occupations:
        slug = occ["slug"]
        html_path = f"html_canada/{occ['code']}.html"
        md_path = f"pages_canada/{slug}.md"

        if not os.path.exists(html_path):
            missing += 1
            continue

        if not args.force and os.path.exists(md_path):
            skipped += 1
            continue

        md = parse_statcan_page(html_path)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        processed += 1

    total_html = len([f for f in os.listdir("html_canada") if f.endswith(".html")])
    total_md = len([f for f in os.listdir("pages_canada") if f.endswith(".md")])
    print(f"Processed: {processed}, Skipped (cached): {skipped}, Missing HTML: {missing}")
    print(f"Total: {total_html} HTML files, {total_md} Markdown files")


if __name__ == "__main__":
    main()