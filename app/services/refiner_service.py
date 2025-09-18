from typing import Dict, List, Any
import os
import time
import json
from app.models import ProductInput, ProductOutput
from app.services import validator
from app.config import get_settings, get_logger


SYSTEM_PROMPT = """
You are a product content refiner for Walmart listings. Produce compliant, helpful, and concise copy.
Hard rules:
- Avoid banned words: cosplay, weapon, knife, UV, premium, perfect (case-insensitive)
- Exactly 8 bullets, each ≤ 85 characters
- Description length 120–160 words
- Include brand in title and description
- Preserve and naturally insert given attributes/keywords
- No medical claims
Return only JSON following the provided schema.
"""

USER_PROMPT_TEMPLATE = """
Generate refined content for the following product.
Brand: {brand}
Product Type: {product_type}
Attributes (JSON): {attributes}
Current Description: {current_description}
Current Bullets: {current_bullets}

JSON schema:
{
  "title": "...",
  "bullets": ["...", "...", "...", "...", "...", "...", "...", "..."],
  "description": "...",
  "meta_title": "...",
  "meta_description": "...",
  "violations": []
}
"""


def call_llm(messages: List[Dict[str, str]]) -> str:
    # Minimal OpenAI Chat Completions call; replace as needed
    from openai import OpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def _parse_llm_json(raw_text: str) -> Dict[str, Any]:
    raw = raw_text.strip()
    # Strip code fences if present
    if raw.startswith("```"):
        raw = raw.strip("`")
        # Remove possible language tag first line
        if "\n" in raw:
            raw = "\n".join(raw.splitlines()[1:])
    return json.loads(raw)


def refine_product(input_data: ProductInput) -> ProductOutput:
    logger = get_logger()
    settings = get_settings()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                brand=input_data.brand,
                product_type=input_data.product_type,
                attributes=json.dumps(input_data.attributes, ensure_ascii=False),
                current_description=input_data.current_description,
                current_bullets="; ".join(input_data.current_bullets),
            ),
        },
    ]

    raw_text = ""
    data: Dict[str, Any] | None = None
    try:
        raw_text = call_llm(messages)
        data = _parse_llm_json(raw_text)
    except Exception as e:
        logger.warning("First parse attempt failed: %s", e)
        # Try a second time instructing strict JSON
        messages2 = messages + [{"role": "system", "content": "Return only valid JSON."}]
        time.sleep(0.5)
        try:
            raw_text = call_llm(messages2)
            data = _parse_llm_json(raw_text)
        except Exception as e2:
            logger.error("Second parse failed: %s", e2)
            # Best-effort fallback
            data = {
                "title": input_data.brand + " " + input_data.product_type,
                "bullets": input_data.current_bullets[:8] + [""] * max(0, 8 - len(input_data.current_bullets)),
                "description": input_data.current_description,
                "meta_title": (input_data.brand + " " + input_data.product_type)[:70],
                "meta_description": input_data.current_description[:160],
                "violations": ["Invalid JSON output"],
            }

    # Normalize and validate
    output = ProductOutput(**{
        "title": data.get("title", "").strip(),
        "bullets": [str(b).strip() for b in (data.get("bullets") or [])][:8],
        "description": data.get("description", "").strip(),
        "meta_title": data.get("meta_title", "").strip(),
        "meta_description": data.get("meta_description", "").strip(),
        "violations": list(data.get("violations") or []),
    })

    # Combine keywords from attributes
    keywords: List[str] = []
    for k, v in (input_data.attributes or {}).items():
        if isinstance(v, (str, int, float)):
            keywords.append(str(v))
        elif isinstance(v, list):
            keywords.extend([str(x) for x in v])
        elif isinstance(v, dict):
            keywords.extend([str(x) for x in v.values()])

    violations = validator.validate_product_output(output.dict(), keywords, input_data.brand)
    output.violations = violations
    return output
