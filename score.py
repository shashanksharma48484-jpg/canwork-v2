"""
Score each occupation across 5 dimensions using an LLM via Perplexity/OpenRouter.

Dimensions:
  1. AI Displacement Risk     (0-10)
  2. Newcomer Accessibility   (0-10)
  3. Skill Transferability    (0-10) — universal cross-industry mobility
  4. Labour Market Demand     (0-10) — Canadian hiring demand 2024-2030
  5. Income Potential         (0-10) — salary range + growth trajectory

Results cached incrementally to scores_canada.json.

Usage:
    uv run python score.py
    uv run python score.py --model sonar
    uv run python score.py --start 0 --end 10 --force
"""

import argparse
import json
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "sonar"
OUTPUT_FILE = "scores_canada.json"

SYSTEM_PROMPT = """\
You are an expert Canadian labour market analyst with deep knowledge of:
- AI and automation trends affecting occupations
- Canadian immigration and credential recognition systems
- Cross-industry skill transferability
- Statistics Canada and Job Bank labour market data
- Canadian salary benchmarks and occupation demand forecasts

You will be given a description of a Canadian NOC 2021 occupation.

Rate the occupation on EXACTLY these 5 dimensions, each from 0 to 10:

---

1. **ai_risk** — AI & Automation Displacement Risk
How likely is AI/automation to significantly reduce employment or reshape this 
occupation by 2030? Consider whether core tasks are digital, routine, or 
require physical presence.
- 0-2: Physical/hands-on work, AI has minimal impact (roofer, plumber)
- 3-5: Mix of physical and knowledge work, AI assists but doesn\'t replace (nurse, police)
- 6-7: Predominantly knowledge work, AI tools already transforming productivity (accountant, manager)
- 8-9: Fully digital/desk work, core tasks are being automated (data analyst, translator)
- 10: Fully routine digital work, AI can do most of it today (data entry clerk)

2. **newcomer_score** — Newcomer Accessibility in Canada
How accessible is this occupation for skilled newcomers to Canada with foreign 
credentials and experience?
- 0-2: Heavily regulated, requires Canadian licensing or re-certification (doctor, lawyer)
- 3-5: Moderate barriers, bridging programs exist (engineer, nurse, accountant)
- 6-8: Low barriers, skills transfer internationally, high demand (IT, finance, analyst)
- 9-10: No licensing needed, universal skills, very high demand (web developer, data entry)

3. **transferability_score** — Cross-Industry Skill Transferability
How broadly do the core skills of this occupation transfer across different 
industries and roles in Canada? Not specific to any one background.
- 0-2: Highly specialized, skills apply only in this specific field (nuclear technician)
- 3-5: Moderate transferability, skills useful in related fields
- 6-8: Broadly transferable skills — communication, analysis, project management, tech
- 9-10: Universal skills applicable in almost any industry (project manager, data analyst)

4. **demand_score** — Canadian Labour Market Demand (2024–2030)
How strong is hiring demand for this occupation in Canada right now and over 
the next 5 years? Consider: Job Bank shortage flags, Express Entry draws, 
immigration pathways, industry growth, and regional demand.
- 0-2: Declining occupation, few job postings, shrinking sector
- 3-5: Stable but not growing, average demand
- 6-8: Growing demand, frequent job postings, some shortage designation
- 9-10: Critical shortage, high volume job postings, strong Express Entry/PNP pathways

5. **income_score** — Income Potential in Canada
Rate the income potential (salary range and growth trajectory) for this 
occupation in Canada relative to median Canadian income (~$62K/year).
- 0-2: Well below median, limited growth (< $35K/year)
- 3-5: Near median income ($35K–$65K/year)
- 6-8: Above median, good growth trajectory ($65K–$110K/year)
- 9-10: High income, strong upside (> $110K/year, bonuses, equity)

---

Respond with ONLY a JSON object in this exact format, no other text:
{
  "ai_risk": <0-10>,
  "newcomer_score": <0-10>,
  "transferability_score": <0-10>,
  "demand_score": <0-10>,
  "income_score": <0-10>,
  "ai_rationale": "<2 sentences on AI displacement factors>",
  "newcomer_rationale": "<2 sentences on credential barriers and accessibility>",
  "transferability_rationale": "<2 sentences on which skills transfer and where>",
  "demand_rationale": "<2 sentences on Canadian demand drivers and outlook>",
  "income_rationale": "<2 sentences on typical salary range and growth>"
}
"""


def score_occupation(client, text, model):
    """Send one occupation to the LLM and get all 5 scores in one call."""

    if "sonar" in model.lower() or "perplexity" in model.lower():
        api_url = "https://api.perplexity.ai/chat/completions"
        api_key = os.environ["PERPLEXITY_API_KEY"]
    else:
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        api_key = os.environ["OPENROUTER_API_KEY"]

    response = client.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    return json.loads(content)


def compute_opportunity_score(result):
    """
    Composite Opportunity Score — weighted, no extra API call needed.
    Higher = better opportunity overall.
    Formula: high demand + high income + high transferability + high newcomer - high ai_risk
    """
    weights = {
        "demand_score":          0.30,
        "income_score":          0.25,
        "transferability_score": 0.20,
        "newcomer_score":        0.15,
        "ai_risk":              -0.10,  # negative — high AI risk reduces opportunity
    }
    score = sum(result.get(k, 5) * w for k, w in weights.items())
    # Normalize to 0-10
    return round(max(0, min(10, score)), 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--force", action="store_true",
                        help="Re-score even if already cached")
    args = parser.parse_args()

    with open("occupations_canada.json") as f:
        occupations = json.load(f)

    subset = occupations[args.start:args.end]

    # Load existing scores
    scores = {}
    if os.path.exists(OUTPUT_FILE) and not args.force:
        with open(OUTPUT_FILE) as f:
            for entry in json.load(f):
                scores[entry["slug"]] = entry

    already = sum(1 for occ in subset if occ["slug"] in scores)
    print(f"Scoring {len(subset)} occupations with {args.model}")
    print(f"Already cached: {already}, To score: {len(subset) - already}")

    errors = []
    client = httpx.Client()

    for i, occ in enumerate(subset):
        slug = occ["slug"]

        if slug in scores and not args.force:
            continue

        md_path = f"pages_canada/{slug}.md"
        if not os.path.exists(md_path):
            print(f"  [{i+1}] SKIP {slug} (no markdown)")
            continue

        with open(md_path, encoding="utf-8") as f:
            text = f.read()

        print(f"  [{i+1}/{len(subset)}] {occ['title']}...", end=" ", flush=True)

        try:
            result = score_occupation(client, text, args.model)
            opp = compute_opportunity_score(result)
            scores[slug] = {
                "slug": slug,
                "title": occ["title"],
                "opportunity_score": opp,
                **result,
            }
            print(f"ai={result['ai_risk']} newcomer={result['newcomer_score']} "
                  f"transfer={result['transferability_score']} "
                  f"demand={result['demand_score']} income={result['income_score']} "
                  f"opp={opp}")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append(slug)

        # Incremental save
        with open(OUTPUT_FILE, "w") as f:
            json.dump(list(scores.values()), f, indent=2)

        if i < len(subset) - 1:
            time.sleep(args.delay)

    client.close()

    scored = [s for s in scores.values() if "ai_risk" in s]
    print(f"\nDone. Scored {len(scored)} occupations, {len(errors)} errors.")
    if errors:
        print(f"Errors: {errors[:10]}")

    if scored:
        for dim in ["ai_risk", "newcomer_score", "transferability_score", "demand_score", "income_score", "opportunity_score"]:
            vals = [s[dim] for s in scored if dim in s]
            if vals:
                print(f"  Avg {dim}: {sum(vals)/len(vals):.1f}")


if __name__ == "__main__":
    main()
