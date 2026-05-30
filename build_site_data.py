"""
Build site/data.json from occupations_canada.json and scores_canada.json.
v2 — supports 5-dimension scoring + opportunity_score composite.

Usage:
    uv run python build_site_data.py
"""

import json
import os
from collections import Counter
from datetime import date

OCCUPATIONS_FILE = "occupations_canada.json"
SCORES_FILE = "scores_canada.json"
OUTPUT_FILE = "site/data.json"

TEER_LABELS = {
    "0": "Management",
    "1": "University degree",
    "2": "College diploma / apprenticeship (2+ years)",
    "3": "College diploma / apprenticeship (< 2 years)",
    "4": "High school diploma",
    "5": "No formal education",
}

CATEGORY_LABELS = {
    "0": "Legislative & Senior Management",
    "1": "Business, Finance & Administration",
    "2": "Natural & Applied Sciences",
    "3": "Health Occupations",
    "4": "Education, Law & Social Services",
    "5": "Arts, Culture & Recreation",
    "6": "Sales & Service",
    "7": "Trades, Transport & Equipment",
    "8": "Natural Resources & Agriculture",
    "9": "Manufacturing & Utilities",
}

def get_teer(code):
    return code[1] if len(code) >= 2 else "?"

def get_category(code):
    return code[0] if len(code) >= 1 else "?"

def main():
    os.makedirs("site", exist_ok=True)

    with open(OCCUPATIONS_FILE, encoding="utf-8") as f:
        occupations = json.load(f)

    scores = {}
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, encoding="utf-8") as f:
            for entry in json.load(f):
                scores[entry["slug"]] = entry
    else:
        print(f"Warning: {SCORES_FILE} not found.")

    print(f"Loaded {len(occupations)} occupations, {len(scores)} scores")

    nodes = []
    missing_scores = 0

    for occ in occupations:
        slug = occ["slug"]
        code = occ.get("code", "")
        s = scores.get(slug, {})

        if not s:
            missing_scores += 1

        teer = get_teer(code)
        category = get_category(code)

        node = {
            "slug": slug,
            "title": occ["title"],
            "code": code,
            "url": occ.get("url", ""),
            "teer": teer,
            "teer_label": TEER_LABELS.get(teer, "Unknown"),
            "category": category,
            "category_label": CATEGORY_LABELS.get(category, "Unknown"),

            # 5 core scores (default -1 = not scored yet)
            "ai_risk":               s.get("ai_risk", -1),
            "newcomer_score":        s.get("newcomer_score", -1),
            "transferability_score": s.get("transferability_score", -1),
            "demand_score":          s.get("demand_score", -1),
            "income_score":          s.get("income_score", -1),
            "opportunity_score":     s.get("opportunity_score", -1),

            # Rationales
            "ai_rationale":               s.get("ai_rationale", ""),
            "newcomer_rationale":         s.get("newcomer_rationale", ""),
            "transferability_rationale":  s.get("transferability_rationale", ""),
            "demand_rationale":           s.get("demand_rationale", ""),
            "income_rationale":           s.get("income_rationale", ""),
        }
        nodes.append(node)

    # Top 20 opportunity scores for "Best Bets" feature
    scored_nodes = [n for n in nodes if n["opportunity_score"] >= 0]
    top20 = sorted(scored_nodes, key=lambda x: x["opportunity_score"], reverse=True)[:20]

    output = {
        "meta": {
            "title": "CanWork Visualizer",
            "subtitle": "Explore 508 Canadian NOC 2021 occupations across 5 dimensions: AI Risk, Newcomer Access, Skill Transferability, Labour Demand & Income Potential",
            "total_occupations": len(nodes),
            "scored_occupations": len(scores),
            "source": "Statistics Canada NOC 2021 v1.0",
            "scoring_model": "sonar (Perplexity AI)",
            "last_scored": str(date.today()),
            "dimensions": {
                "ai_risk":               "AI & Automation Displacement Risk (0=safe, 10=high risk)",
                "newcomer_score":        "Newcomer Accessibility in Canada (0=hard, 10=easy)",
                "transferability_score": "Cross-Industry Skill Transferability (0=specialized, 10=universal)",
                "demand_score":          "Canadian Labour Market Demand 2024-2030 (0=declining, 10=critical shortage)",
                "income_score":          "Income Potential in Canada (0=low, 10=high)",
                "opportunity_score":     "Composite Opportunity Score — weighted: demand+income+transferability+newcomer-ai_risk",
            }
        },
        "top20": [{"slug": n["slug"], "title": n["title"], "opportunity_score": n["opportunity_score"]} for n in top20],
        "nodes": nodes,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Built {OUTPUT_FILE} with {len(nodes)} nodes")
    print(f"Missing scores: {missing_scores}")
    print(f"\nCategory breakdown:")
    cats = Counter(n["category_label"] for n in nodes)
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")

    if scored_nodes:
        print(f"\nTop 5 Opportunity Scores:")
        for n in top20[:5]:
            print(f"  {n['title']}: {n['opportunity_score']}")

if __name__ == "__main__":
    main()
