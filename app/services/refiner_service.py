import os
import json
import google.generativeai as genai
from typing import List, Dict, Any
from app.models import ProductInput, ProductOutput
from app.services import validator
from app.config import get_settings, get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configure Gemini with multiple model fallbacks
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
    available_models = [
        "gemini-1.5-pro",
        "gemini-pro",
    ]
    model = None
    for model_name in available_models:
        try:
            model = genai.GenerativeModel(model_name)
            logger.info(f"Using Gemini model: {model_name}")
            break
        except Exception as e:
            logger.warning(f"Failed to load {model_name}: {e}")
            continue

    if not model:
        logger.error("No Gemini models available")
else:
    logger.warning("No Gemini API key found. Using fallback mode.")
    model = None

# Ultra-optimized Walmart compliance prompt
WALMART_PROMPT = """
You are a Walmart Content Refiner. You MUST generate 100% compliant content on the FIRST attempt with ZERO violations.

Strict Walmart rules:
- Title ≤ 150 chars, must include brand + product type, no banned words.
- Bullets: exactly 8 <li> items, each ≤ 85 chars, HTML <li> tags required, no banned words.
- Description: 120–160 words, must mention brand, no banned words.
- Meta Title: ≤ 70 chars, includes brand/product, no banned words.
- Meta Description: ≤ 160 chars, must summarize, no banned words.
- ABSOLUTELY NO medical claims: cure, treat, diagnose, prevent.
- DO NOT include “cosplay, weapon, knife, uv, premium, perfect”.

Output Format: Return ONLY this JSON (no explanation, no markdown):
{
  "title": "...",
  "bullets": "<li>...</li><li>...</li> ... 8 items total ...",
  "description": "...",
  "meta_title": "...",
  "meta_description": "..."
}

Example:
{
  "title": "BrandCo Stainless Steel Kitchen Blender 500W",
  "bullets": "<li>Powerful 500W motor</li><li>Durable stainless steel blades</li><li>Easy one-touch operation</li><li>Compact space-saving design</li><li>Dishwasher-safe parts</li><li>Multi-speed settings</li><li>Ideal for smoothies</li><li>2-year warranty</li>",
  "description": "BrandCo Kitchen Blender is designed for effortless blending... (120–160 words).",
  "meta_title": "BrandCo Stainless Steel Kitchen Blender 500W",
  "meta_description": "Powerful BrandCo 500W stainless steel blender with durable blades, compact design, and 2-year warranty."
}
"""

def call_gemini(input_data: ProductInput, previous_violations: List[str] = None) -> Dict[str, Any]:
    """Call Gemini with strict Walmart compliance"""
    if not model:
        logger.error("Gemini model not available")
        return {}

    try:
        attributes_text = ""
        if isinstance(input_data.attributes, dict):
            attributes_text = ", ".join([f"{k}: {v}" for k, v in input_data.attributes.items()])
        elif isinstance(input_data.attributes, str):
            attributes_text = input_data.attributes

        # Violation feedback if retries
        violation_feedback = ""
        if previous_violations:
            violation_feedback = "\nPREVIOUS ATTEMPT VIOLATIONS TO FIX:\n" + "\n".join(
                [f"- {v}" for v in previous_violations]
            ) + "\nCRITICAL: Fix ALL of the above in this attempt."

        user_prompt = f"""
🎯 PRODUCT TO REFINE:
- Brand: {input_data.brand}
- Product Type: {input_data.product_type}
- Attributes: {attributes_text}
- Current Description: {input_data.current_description}
- Current Bullets: {json.dumps(input_data.current_bullets)}

{violation_feedback}
"""

        logger.info(f"Calling Gemini for {input_data.brand}")

        try:
            response = model.generate_content(
                "Return ONLY valid JSON.\n\n" + WALMART_PROMPT + "\n\n" + user_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,        # deterministic
                    max_output_tokens=1800,
                    top_p=1.0,
                    top_k=1,
                ),
            )
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return None

        # Extract JSON
        response_text = response.text.strip()
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        try:
            result = json.loads(response_text)
            logger.info(f"Successfully generated content for {input_data.brand}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response text: {response_text[:300]}...")
            return {}

    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return {}

def refine_product(input_data: ProductInput) -> ProductOutput:
    """Refine product content with strict Walmart compliance and return the best attempt"""
    logger.info(f"Refining {input_data.brand} {input_data.product_type}")

    max_retries = 3
    attempt_history = []  # store (draft, violations) for each attempt
    violations = []

    for attempt in range(max_retries):
        logger.info(f"Attempt {attempt + 1} for {input_data.brand}")

        draft = call_gemini(input_data, violations if attempt > 0 else None)

        if not draft:
            logger.error(f"Failed to generate content on attempt {attempt + 1}")
            attempt_history.append((
                None,
                ["Failed to generate content"]
            ))
            continue

        # Validate
        violations = validator.validate_product_output(
            draft,
            input_keywords=list((input_data.attributes or {}).values()),
            brand=input_data.brand
        )

        # Extra strict word count check
        if "description" in draft:
            word_count = len(draft["description"].split())
            if word_count < 120 or word_count > 160:
                violations.append(f"Description length {word_count} words, must be 120–160")

        # Save this attempt
        attempt_history.append((draft, violations.copy()))

        if not violations:
            logger.info(f"✅ 100% compliance achieved for {input_data.brand} after {attempt + 1} attempts")
            return ProductOutput(
                title=draft.get("title", f"{input_data.brand} {input_data.product_type}"),
                bullets=draft.get("bullets", "".join(["<li>Product feature</li>" for _ in range(8)])),
                description=draft.get("description", f"{input_data.brand} {input_data.product_type} - Product description."),
                meta_title=draft.get("meta_title", f"{input_data.brand} {input_data.product_type}"),
                meta_description=draft.get("meta_description", f"{input_data.brand} {input_data.product_type} - Product description."),
                violations=[]
            )

        logger.warning(f"❌ Violations found for {input_data.brand} (attempt {attempt + 1}): {violations}")

    # If no perfect attempt, pick the one with minimum violations
    best_draft, best_violations = min(
        attempt_history,
        key=lambda x: len(x[1]) if x[0] else float("inf")
    )

    if not best_draft:
        logger.error("All attempts failed to generate usable content")
        return ProductOutput(
            title=f"{input_data.brand} {input_data.product_type}",
            bullets="".join(["<li>Product feature</li>" for _ in range(8)]),
            description=f"{input_data.brand} {input_data.product_type} - Product description.",
            meta_title=f"{input_data.brand} {input_data.product_type}",
            meta_description=f"{input_data.brand} {input_data.product_type} - Product description.",
            violations=["All attempts failed"]
        )

    logger.info(f"⚠️ Returning best attempt with {len(best_violations)} violations")
    return ProductOutput(
        title=best_draft.get("title", f"{input_data.brand} {input_data.product_type}"),
        bullets=best_draft.get("bullets", "".join(["<li>Product feature</li>" for _ in range(8)])),
        description=best_draft.get("description", f"{input_data.brand} {input_data.product_type} - Product description."),
        meta_title=best_draft.get("meta_title", f"{input_data.brand} {input_data.product_type}"),
        meta_description=best_draft.get("meta_description", f"{input_data.brand} {input_data.product_type} - Product description."),
        violations=best_violations
    )
