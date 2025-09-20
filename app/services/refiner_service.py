"""
Walmart Content Refiner Service v3.0
Author: Tushar Tripathi

This module handles the AI-powered content refinement for Walmart compliance.
Version 3.0 features improved violation handling with post-processing fixes.
"""

import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from app.models import ProductInput, ProductOutput
from app.services import validator
from app.config import get_settings, get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configure Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    logger.warning("No Gemini API key found. Using fallback mode.")
    model = None

# Advanced system prompt for high-quality content generation
SYSTEM_PROMPT = """You are a Walmart Content Compliance Expert. 
You MUST produce JSON output that passes every single Walmart hard rule.

Before outputting, **count** words, characters, and bullets. 
If any rule is violated, FIX IT and regenerate silently until the JSON is valid. 
Never return explanations, only valid JSON.

RULES:
- Title ≤150 chars, must include Brand
- Bullets: exactly 8, each ≤85 chars, HTML <li>text</li>
- Description: 120–160 words, must include Brand + ALL keywords
- Meta title ≤70 chars, Meta description ≤160 chars
- Forbidden words: perfect, premium, cosplay, weapon, knife, UV, exceptional, outstanding, remarkable, superior, excellent, amazing, fantastic, incredible, wonderful, brilliant, magnificent, spectacular, extraordinary, phenomenal
- Instead use: great, reliable, durable, efficient, innovative, quality, effective, dependable, sturdy, robust, consistent, trustworthy
- No medical claims (cure, heal, treat, prevent, remedy, diagnose)

OUTPUT (valid JSON only):
{
  "title": "...",
  "bullets": ["<li>...</li>", "<li>...</li>", ...8 total...],
  "description": "...",
  "meta_title": "...",
  "meta_description": "..."
}

⚠️ IMPORTANT: If any rule fails (missing keyword, wrong count, banned word), regenerate until ALL are satisfied."""

def call_gemini_advanced(input_data: ProductInput, violations: List[str] = None, attempt: int = 1) -> Dict[str, Any]:
    """
    Call Gemini API with advanced prompting for high-quality content generation
    
    Author: Tushar Tripathi
    Version: 3.0
    """
    if not model:
        logger.error("Gemini model not available")
        return {}
    
    try:
        # Build concise user prompt to save tokens
        attributes_text = ""
        if isinstance(input_data.attributes, dict):
            attributes_text = ", ".join([f"{k}: {v}" for k, v in input_data.attributes.items()])
        elif isinstance(input_data.attributes, str):
            attributes_text = input_data.attributes
        
        user_prompt = f"""
        PRODUCT DATA:
        Brand: {input_data.brand}
        Type: {input_data.product_type}
        Keywords: {attributes_text}

        {f"🚨 VIOLATIONS FOUND IN PREVIOUS ATTEMPT:" if violations else ""}
        {f"❌ These violations were detected: {', '.join(violations)}" if violations else ""}
        
        {f"🔧 POST-PROCESSING FIXES APPLIED:" if violations else ""}
        {f"• Banned words were replaced with safe alternatives" if violations else ""}
        {f"• Word counts were adjusted to meet requirements" if violations else ""}
        {f"• Missing keywords were added to the description" if violations else ""}

        {f"📝 YOUR TASK:" if violations else "TASK:"}
        {f"Take the corrected content and make it sound completely natural and engaging while maintaining 100% compliance." if violations else "Create Walmart-compliant content that passes ALL rules."}
        {f"DO NOT reintroduce any banned words or violate any rules again." if violations else ""}
        {f"Make the content flow naturally while keeping all the fixes intact." if violations else ""}

        RULES (must follow):
        - Title ≤150 chars with brand name
        - Exactly 8 bullets, each ≤85 chars, HTML format
        - Description 120-160 words with brand name + ALL keywords
        - Meta title ≤70 chars, meta description ≤160 chars
        - NO banned words: perfect, premium, cosplay, weapon, knife, UV, exceptional, outstanding, remarkable, superior, excellent, amazing, fantastic, incredible, wonderful, brilliant, magnificent, spectacular, extraordinary, phenomenal
        - USE alternatives: great, reliable, durable, efficient, innovative, quality, effective, dependable, sturdy, robust, consistent, trustworthy
        - No medical claims: cure, heal, treat, prevent, remedy, diagnose

        {f"⚠️  CRITICAL: Do not repeat the violations: {', '.join(violations)}" if violations else ""}

        Return ONLY valid JSON.
        """

        
        print(f"🤖 Calling Gemini for {input_data.brand} (attempt {attempt})")
        
        response = model.generate_content(
            SYSTEM_PROMPT + "\n\n" + user_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=1.0 if attempt > 1 else 0.3,  # Maximum temperature for retries to encourage creativity
                max_output_tokens=1200,
                top_p=1.0 if attempt > 1 else 0.8,  # Maximum top_p for retries
                top_k=100 if attempt > 1 else 40  # Maximum top_k for retries
            )
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to find JSON in the response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        
        # Parse JSON
        try:
            result = json.loads(response_text)
            
            # Convert bullets from list to string if needed
            if isinstance(result.get("bullets"), list):
                result["bullets"] = "".join(result["bullets"])
            
            print(f"✅ Successfully generated content for {input_data.brand} (attempt {attempt})")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed (attempt {attempt}): {e}")
            print(f"📝 Response text: {response_text[:500]}...")
            return {}
            
    except Exception as e:
        print(f"💥 Gemini API call failed (attempt {attempt}): {e}")
        return {}

def apply_post_processing_fixes(result: dict, input_data: ProductInput, violations: list) -> dict:
    """
    Apply post-processing fixes to reduce violations
    
    Author: Tushar Tripathi
    Version: 3.0
    """
    print(f"🔧 Applying post-processing fixes for {len(violations)} violations...")
    
    fixed_result = result.copy()
    
    # Fix banned words
    banned_words = {
        "perfect": "excellent", "premium": "high-quality", "superior": "outstanding", 
        "exceptional": "remarkable", "cosplay": "costume", "weapon": "tool", 
        "knife": "blade", "uv": "protective", "UV": "protective",
        "outstanding": "great", "remarkable": "reliable", "superior": "durable",
        "excellent": "efficient", "amazing": "innovative", "fantastic": "quality",
        "incredible": "effective", "wonderful": "dependable", "brilliant": "sturdy",
        "magnificent": "robust", "spectacular": "consistent", "extraordinary": "trustworthy",
        "phenomenal": "reliable"
    }
    
    for field in ["title", "description", "meta_title", "meta_description"]:
        if field in fixed_result and fixed_result[field]:
            text = fixed_result[field]
            for banned, replacement in banned_words.items():
                import re
                pattern = r'\b' + re.escape(banned) + r'\b'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            fixed_result[field] = text
    
    # Fix word count in description
    if "description" in fixed_result and fixed_result["description"]:
        desc = fixed_result["description"]
        word_count = len(desc.split())
        
        if word_count < 120:
            # Add more content to reach 120 words
            attributes_text = ""
            if isinstance(input_data.attributes, dict):
                attributes_text = ", ".join([f"{k}: {v}" for k, v in input_data.attributes.items()])
            elif isinstance(input_data.attributes, str):
                attributes_text = input_data.attributes
            
            # Add keyword-rich content
            additions = [
                f" This {input_data.product_type.lower()} features {attributes_text} for reliable performance.",
                f" The {input_data.brand} brand ensures quality construction and user satisfaction.",
                f" Customers appreciate the innovative design and attention to detail.",
                f" This product is designed for everyday use and provides consistent results.",
                f" The durable construction makes it suitable for long-term use."
            ]
            
            for addition in additions:
                if len(desc.split()) >= 120:
                    break
                desc += addition
            
            fixed_result["description"] = desc
            
        elif word_count > 160:
            # Trim to 160 words
            words = desc.split()
            fixed_result["description"] = " ".join(words[:160])
    
    # Fix keyword integration
    if "description" in fixed_result and fixed_result["description"]:
        desc = fixed_result["description"]
        attributes_text = ""
        if isinstance(input_data.attributes, dict):
            attributes_text = ", ".join([f"{k}: {v}" for k, v in input_data.attributes.items()])
        elif isinstance(input_data.attributes, str):
            attributes_text = input_data.attributes
        
        # Check if keywords are present
        missing_keywords = []
        if isinstance(input_data.attributes, dict):
            for key, value in input_data.attributes.items():
                if value.lower() not in desc.lower():
                    missing_keywords.append(value)
        elif isinstance(input_data.attributes, str):
            for keyword in input_data.attributes.split(", "):
                if keyword.lower() not in desc.lower():
                    missing_keywords.append(keyword)
        
        # Add missing keywords
        if missing_keywords:
            keyword_text = ", ".join(missing_keywords)
            desc += f" This product features {keyword_text} for enhanced performance."
            fixed_result["description"] = desc
    
    # Fix meta description length
    if "meta_description" in fixed_result and fixed_result["meta_description"]:
        meta_desc = fixed_result["meta_description"]
        if len(meta_desc) > 160:
            fixed_result["meta_description"] = meta_desc[:157] + "..."
    
    print(f"✅ Post-processing fixes applied!")
    return fixed_result


def refine_with_retries(input_data, max_attempts=3):
    """Clean retry logic that finds the best result"""
    best_output = None
    fewest_violations = float("inf")
    best_violations = []

    for attempt in range(1, max_attempts + 1):
        print(f"🔄 Attempt {attempt}/{max_attempts} for {input_data.brand}")
        
        # Generate content (no violation feedback, let Gemini try fresh)
        draft = call_gemini_advanced(input_data, violations=None, attempt=attempt)

        if not draft:
            print(f"❌ Failed to generate content on attempt {attempt}")
            continue

        # Validate the generated content
        violations = validator.validate_product_output(
            draft, 
            input_keywords=list((input_data.attributes or {}).values()), 
            brand=input_data.brand
        )

        print(f"📊 Attempt {attempt} violations: {violations}")

        # Save lowest violation output
        if len(violations) < fewest_violations:
            best_output = draft
            fewest_violations = len(violations)
            best_violations = violations
            print(f"🏆 New best result with {len(violations)} violations")

        # Stop if fully clean
        if not violations:
            print(f"🎉 Perfect content generated on attempt {attempt}")
            break

    # Final post-processing patch
    if best_output:
        print(f"🔧 Applying post-processing fixes...")
        fixed = apply_post_processing_fixes(best_output, input_data, best_violations)
        return fixed, best_violations
    return None, ["Failed after all attempts"]


def refine_product(input_data: ProductInput) -> ProductOutput:
    """
    Refine product content using iterative Gemini AI with post-processing fixes
    
    Author: Tushar Tripathi
    Version: 3.0 - Improved violation handling with post-processing
    """
    print(f"🚀 Starting refinement for {input_data.brand} {input_data.product_type}")
    
    best_result = None
    best_violations = []
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        print(f"🔄 Attempt {attempt}/{max_attempts} for {input_data.brand}")
        
        # Generate content with Gemini
        if attempt == 1:
            # First attempt: generate fresh content
            draft = call_gemini_advanced(input_data, violations=None, attempt=attempt)
        else:
            # Subsequent attempts: use post-processed content as input
            draft = call_gemini_advanced(input_data, violations=best_violations, attempt=attempt)
        
        if not draft:
            print(f"❌ Failed to generate content on attempt {attempt}")
            continue
        
        # Validate the generated content
        current_violations = validator.validate_product_output(
            draft, 
            input_keywords=list((input_data.attributes or {}).values()), 
            brand=input_data.brand
        )
        
        print(f"📊 Attempt {attempt} violations: {current_violations}")
        
        # Apply post-processing fixes
        if current_violations:
            print(f"🔧 Applying post-processing fixes for {len(current_violations)} violations...")
            fixed_draft = apply_post_processing_fixes(draft, input_data, current_violations)
            
            # Re-validate after fixes
            remaining_violations = validator.validate_product_output(
                fixed_draft, 
                input_keywords=list((input_data.attributes or {}).values()), 
                brand=input_data.brand
            )
            print(f"📊 After fixes, remaining violations: {remaining_violations}")
            
            # Use fixed content for next iteration
            draft = fixed_draft
            current_violations = remaining_violations
        
        # Save best result
        if attempt == 1 or len(current_violations) < len(best_violations):
            best_result = draft
            best_violations = current_violations
            print(f"🏆 New best result with {len(best_violations)} violations")
        
        # If no violations, we're done
        if not current_violations:
            print(f"🎉 Perfect content generated on attempt {attempt}")
            break
    
    # Return the best result we found
    if best_result:
        # Ensure bullets are in correct format (HTML string)
        bullets = best_result.get("bullets", [])
        if isinstance(bullets, list):
            bullets = "".join(bullets)
        
        result = ProductOutput(
            title=best_result.get("title", f"{input_data.brand} {input_data.product_type}"),
            bullets=bullets,
            description=best_result.get("description", f"{input_data.brand} {input_data.product_type} - Product description."),
            meta_title=best_result.get("meta_title", f"{input_data.brand} {input_data.product_type}"),
            meta_description=best_result.get("meta_description", f"{input_data.brand} {input_data.product_type} - Product description."),
            violations=best_violations
        )
        print(f"✅ Returning best result with {len(best_violations)} violations")
        return result
    else:
        print(f"💥 Failed to generate any content after all attempts")
        return ProductOutput(
            title=f"{input_data.brand} {input_data.product_type}",
            bullets="<li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li><li>Product feature</li>",
            description=f"{input_data.brand} {input_data.product_type} - Product description.",
            meta_title=f"{input_data.brand} {input_data.product_type}",
            meta_description=f"{input_data.brand} {input_data.product_type} - Product description.",
            violations=["Failed to generate content after all attempts"]
        )

def fix_output_violations(output_dict: Dict[str, Any], violations: List[str], brand: str) -> Dict[str, Any]:
    """Fix specific violations in existing output using advanced Gemini prompting"""
    if not model:
        logger.error("Gemini model not available for fixing violations")
        return output_dict
    
    try:
        fix_prompt = f"""
You have an existing product output with specific violations. Please fix ONLY the specified violations while keeping everything else exactly the same.

CURRENT OUTPUT:
{json.dumps(output_dict, indent=2)}

VIOLATIONS TO FIX: {', '.join(violations)}

Brand: {brand}

INSTRUCTIONS:
1. Fix ONLY the specified violations
2. Keep all other content unchanged
3. Maintain the same structure and format
4. Ensure the fix sounds natural and engaging
5. Follow all compliance rules

Return the corrected JSON with the same structure, fixing only the specified violations.
"""
        
        logger.info(f"Fixing violations for {brand}: {violations}")
        
        response = model.generate_content(
            fix_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=800,
                top_p=0.7,
                top_k=30
            )
        )
        
        response_text = response.text.strip()
        
        # Extract JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                response_text = response_text[json_start:json_end].strip()
        
        try:
            fixed_output = json.loads(response_text)
            
            # Convert bullets from list to string if needed
            if isinstance(fixed_output.get("bullets"), list):
                fixed_output["bullets"] = "".join(fixed_output["bullets"])
            
            logger.info(f"Successfully fixed violations for {brand}")
            return fixed_output
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for fix: {e}")
            return output_dict
            
    except Exception as e:
        logger.error(f"Failed to fix violations for {brand}: {e}")
        return output_dict