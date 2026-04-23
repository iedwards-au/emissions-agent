import os
import json
import time
import requests
import anthropic
from prompts import CLASSIFY_PROPERTY_PROMPT

SCOPE3_API_URL = "https://api.scope3.com/v2/measure"
BATCH_SIZE = 50

#client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Tool schemas (passed to Claude) ──────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "check_carbon_score",
        "description": (
            "Look up carbon emissions for a single advertising property via the Scope3 API. "
            "Returns gCO2PM (grams of CO2 per 1000 impressions) and emissions breakdown. "
            "Use this for individual property lookups."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "string",
                    "description": "Domain, app bundle ID, or CTV app name (e.g. 'nytimes.com', 'com.spotify.music')"
                },
                "country": {
                    "type": "string",
                    "description": "ISO 2-letter country code (e.g. 'AU', 'US'). Defaults to 'US'."
                },
                "impressions": {
                    "type": "integer",
                    "description": "Number of impressions to model. Defaults to 1000."
                }
            },
            "required": ["inventory_id"]
        }
    },
    {
        "name": "score_inventory_list",
        "description": (
            "Score and rank a list of advertising properties by carbon emissions using the Scope3 API. "
            "Batches requests automatically. Returns properties ranked low to high gCO2PM. "
            "Flags any unmodelled properties separately. Use for bulk analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "properties": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "inventory_id": {"type": "string"},
                            "country": {"type": "string"},
                            "impressions": {"type": "integer"}
                        },
                        "required": ["inventory_id"]
                    },
                    "description": "List of properties to score"
                }
            },
            "required": ["properties"]
        }
    },
    {
        "name": "classify_property",
        "description": (
            "Classify advertising properties into content categories (News, Lifestyle, Sports, etc.). "
            "Uses Claude's knowledge. Use this before match_brief_to_inventory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "properties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of property IDs to classify"
                }
            },
            "required": ["properties"]
        }
    },
    {
        "name": "match_brief_to_inventory",
        "description": (
            "Given a campaign brief and a scored + classified inventory list, "
            "recommend the top matching properties based on content fit and low emissions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "brief": {
                    "type": "string",
                    "description": "The campaign brief text"
                },
                "scored_inventory": {
                    "type": "array",
                    "description": "List of scored properties from score_inventory_list",
                    "items": {"type": "object"}
                },
                "classified_inventory": {
                    "type": "array",
                    "description": "List of classified properties from classify_property",
                    "items": {"type": "object"}
                },
                "top_n": {
                    "type": "integer",
                    "description": "How many top properties to return. Defaults to 10."
                }
            },
            "required": ["brief", "scored_inventory", "classified_inventory"]
        }
    }
]

# ── Tool implementations ──────────────────────────────────────────────────────

def _call_scope3_api(rows: list, api_key: str) -> dict:
    """Raw Scope3 API call for a batch of rows."""
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json"
    }
    payload = {"rows": rows}
    response = requests.post(
        f"{SCOPE3_API_URL}?includeRows=true&fields=null",
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def check_carbon_score(inventory_id: str, country: str = "US", impressions: int = 1000) -> dict:
    api_key = os.getenv("SCOPE3_API_KEY")
    if not api_key:
        return {"error": "SCOPE3_API_KEY not set in environment"}

    try:
        result = _call_scope3_api([{
            "impressions": impressions,
            "utcDatetime": "2026-03-01",
            "inventoryId": inventory_id,
            "country": country
        }], api_key)

        rows = result.get("rows", [])
        if not rows:
            return {"inventory_id": inventory_id, "status": "no_data"}

        row = rows[0]
        if row.get("inventoryCoverage") == "missing":
            return {"inventory_id": inventory_id, "status": "unmodelled"}

        breakdown = result.get("totalEmissionsBreakdown", {}).get("totals", {})
        gco2pm = round(result.get("totalEmissions", 0), 2)
        percentile = row.get("internal", {}).get("benchmarkPercentile")

        return {
            "inventory_id": inventory_id,
            "status": "modelled",
            "gco2pm": gco2pm,
            "benchmark_percentile": percentile,
            "channel": row.get("internal", {}).get("channel"),
            "is_mfa": row.get("internal", {}).get("isMFA", False),
            "breakdown": {
                "ad_selection": round(breakdown.get("adSelection", 0), 2),
                "creative_delivery": round(breakdown.get("creativeDelivery", 0), 2),
                "media_distribution": round(breakdown.get("mediaDistribution", 0), 2),
                "tech_manipulation": round(breakdown.get("techManipulation", 0), 2),
            }
        }
    except requests.HTTPError as e:
        return {"inventory_id": inventory_id, "error": str(e)}


def score_inventory_list(properties: list) -> dict:
    api_key = os.getenv("SCOPE3_API_KEY")
    if not api_key:
        return {"error": "SCOPE3_API_KEY not set in environment"}

    total = len(properties)
    warnings = []
    if total > BATCH_SIZE:
        warnings.append(f"Large list detected ({total} properties). Processing in batches of {BATCH_SIZE}. This may take a moment.")

    modelled = []
    unmodelled = []
    errors = []

    # Process in batches
    for i in range(0, total, BATCH_SIZE):
        batch = properties[i:i + BATCH_SIZE]
        rows = [{
            "impressions": p.get("impressions", 1000),
            "utcDatetime": "2026-03-01",
            "inventoryId": p["inventory_id"],
            "country": p.get("country", "US")
        } for p in batch]

        try:
            result = _call_scope3_api(rows, api_key)
            api_rows = result.get("rows", [])

            for j, row in enumerate(api_rows):
                inv_id = batch[j]["inventory_id"]
                if row.get("inventoryCoverage") == "missing":
                    unmodelled.append({"inventory_id": inv_id})
                    continue

                breakdown = result.get("totalEmissionsBreakdown", {}).get("totals", {})
                gco2pm = round(row.get("totalEmissions", result.get("totalEmissions", 0)), 2)
                internal = row.get("internal", {})

                modelled.append({
                    "inventory_id": inv_id,
                    "gco2pm": gco2pm,
                    "benchmark_percentile": internal.get("benchmarkPercentile"),
                    "channel": internal.get("channel"),
                    "is_mfa": internal.get("isMFA", False),
                    "country": internal.get("countryRegionCountry"),
                    "breakdown": {
                        "ad_selection": round(breakdown.get("adSelection", 0), 2),
                        "creative_delivery": round(breakdown.get("creativeDelivery", 0), 2),
                        "media_distribution": round(breakdown.get("mediaDistribution", 0), 2),
                        "tech_manipulation": round(breakdown.get("techManipulation", 0), 2),
                    }
                })

            if i + BATCH_SIZE < total:
                time.sleep(0.5)  # gentle rate limiting between batches

        except requests.HTTPError as e:
            errors.append({"batch_start": i, "error": str(e)})

    # Sort modelled by gco2pm ascending
    modelled.sort(key=lambda x: x["gco2pm"])

    return {
        "total_submitted": total,
        "total_modelled": len(modelled),
        "total_unmodelled": len(unmodelled),
        "warnings": warnings,
        "ranked_inventory": modelled,
        "unmodelled_inventory": unmodelled,
        "errors": errors
    }


def classify_property(properties: list) -> list:
    """Use Claude to classify properties into content categories."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = CLASSIFY_PROPERTY_PROMPT.format(properties="\n".join(properties))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def match_brief_to_inventory(brief, scored_inventory, classified_inventory, top_n=10):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    """Merge scores + classifications and pick the best matches for a brief."""
    # Build lookup from classifications
    category_map = {item["property"]: item for item in classified_inventory}

    # Merge
    merged = []
    for item in scored_inventory:
        inv_id = item["inventory_id"]
        classification = category_map.get(inv_id, {})
        merged.append({
            **item,
            "category": classification.get("category", "Unknown"),
            "description": classification.get("description", "")
        })

    # Ask Claude to pick the best matches
    prompt = f"""Campaign brief: "{brief}"

Here is scored and classified inventory (sorted low to high emissions):
{json.dumps(merged, indent=2)}

Select the top {top_n} properties that best match this brief. Prioritise:
1. Content/category fit with the brief
2. Low gCO2PM emissions
3. Exclude any MFA (made-for-advertising) properties

Respond ONLY with a valid JSON array of the top {top_n} properties, no preamble. Include all original fields plus a "reason" field explaining the match."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ── Tool dispatcher ───────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Route a tool call to the correct implementation and return JSON string."""
    if tool_name == "check_carbon_score":
        result = check_carbon_score(**tool_input)
    elif tool_name == "score_inventory_list":
        result = score_inventory_list(tool_input["properties"])
    elif tool_name == "classify_property":
        result = classify_property(tool_input["properties"])
    elif tool_name == "match_brief_to_inventory":
        result = match_brief_to_inventory(**tool_input)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)
